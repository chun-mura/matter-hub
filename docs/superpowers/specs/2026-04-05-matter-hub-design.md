# Matter Hub - 設計ドキュメント

## 概要

Matter (web.getmatter.com) に保存した記事をAPIで取得し、SQLiteに保存、CLIで検索・タグ管理・興味分析を行うツール。

## 背景

- Matterには公式APIが公開されていないが、内部APIが存在する
- 公式Obsidianプラグインのソースコードおよびコミュニティの調査により、全記事取得可能なエンドポイントが判明
- Matter単体ではタイトル検索やタグ付けが弱いため、CLIツールで補完する

## 要件

- Matter APIから全記事（ハイライト有無に関係なく）を取得
- SQLiteに保存し、全文検索・タグ管理を提供
- Claude API（Haiku）で自動タグ付け
- CLIで検索・フィルタ・分析コマンドを提供

## アーキテクチャ

```
Matter API  →  Sync Script  →  SQLite DB  →  CLI Commands
                                    ↑
                              Claude API (自動タグ付け)
```

### ファイル構成

```
matter-hub/
├── matter_hub/
│   ├── __init__.py
│   ├── cli.py          # CLIエントリポイント
│   ├── api.py          # Matter API クライアント
│   ├── db.py           # SQLite操作
│   ├── tagger.py       # Claude API 自動タグ付け
│   └── config.py       # 設定管理
├── pyproject.toml
├── README.md
└── .env                # APIキー等（gitignore対象）
```

## データ取得（Matter API）

### ベースURL

```
https://api.getmatter.app/api/v11/
```

### 認証フロー

1. `POST qr_login/trigger/` → `session_token` 取得
2. ターミナルにQRコードをASCII表示（`qrcode` ライブラリ）
3. ユーザーがMatterアプリでスキャン
4. `POST qr_login/exchange/` をポーリング（1秒間隔、最大600回） → `access_token` + `refresh_token` 取得
5. トークンは `~/.matter-hub/config.json` に保存、次回以降は再利用
6. トークン期限切れ時は `POST token/refresh/` で自動更新

### 記事取得エンドポイント

```
GET library_items/updates_feed/
Authorization: Bearer <access_token>
```

- `updates_feed` は全記事を返す（`highlights_feed` はハイライト付きのみ）
- レスポンスの `next` フィールドでページネーション
- `library_state === 3`（削除済み）はスキップ

### 発見済みエンドポイント一覧

| エンドポイント | メソッド | 用途 |
|---|---|---|
| `library_items/updates_feed/` | GET | 全記事取得 |
| `library_items/highlights_feed/` | GET | ハイライト付き記事のみ |
| `save/` | POST | URLを保存 |
| `qr_login/trigger/` | POST | QR認証開始 |
| `qr_login/exchange/` | POST | トークン交換 |
| `token/refresh/` | POST | トークンリフレッシュ |

### 取得データ

- `content.title` - 記事タイトル
- `content.url` - 元URL
- `content.author.any_name` - 著者名
- `content.publisher.any_name` - 出版社名
- `content.publication_date` - 公開日
- `content.tags[]` - タグ（`name`, `created_date`）
- `content.my_annotations[]` - ハイライト（`text`, `note`, `created_date`）
- `content.my_note.note` - 記事レベルのノート
- `content.library.library_state` - 状態（3=削除済み）

## データベース（SQLite）

### テーブル設計

```sql
-- 記事テーブル
CREATE TABLE articles (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  url TEXT NOT NULL,
  author TEXT,
  publisher TEXT,
  published_date TEXT,
  note TEXT,
  library_state INTEGER,
  synced_at TEXT
);

-- タグテーブル（Matter由来 + AI生成を区別）
CREATE TABLE tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id TEXT REFERENCES articles(id),
  name TEXT NOT NULL,
  source TEXT NOT NULL  -- 'matter' or 'ai'
);

-- ハイライトテーブル
CREATE TABLE highlights (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  article_id TEXT REFERENCES articles(id),
  text TEXT NOT NULL,
  note TEXT,
  created_date TEXT
);

-- 全文検索用（FTS5）
CREATE VIRTUAL TABLE articles_fts USING fts5(
  title, author, publisher, note,
  content='articles',
  content_rowid='rowid'
);
```

### 設計ポイント

- タグは `source` カラムでMatter由来（`matter`）とAI生成（`ai`）を区別
- FTS5で高速な全文検索（タイトル、著者、出版社、ノートを対象）
- 同期は差分更新（`synced_at` で管理）

## CLIコマンド

```bash
# 初期設定・認証
matter-hub auth              # QRコード表示 → Matterアプリでスキャン → トークン保存

# 同期
matter-hub sync              # Matter APIから全記事を取得・DB更新
matter-hub sync --tag        # 同期 + 未タグ記事をClaude APIで自動タグ付け

# 検索
matter-hub search "キーワード"            # タイトル・著者・ノートを全文検索
matter-hub search --tag "AI"              # タグで絞り込み
matter-hub search --author "名前"         # 著者で絞り込み
matter-hub search --after 2025-01-01      # 日付で絞り込み（フィルタ組み合わせ可）

# タグ管理
matter-hub tags                           # 全タグ一覧（記事数付き）
matter-hub tag add <article_id> "タグ"    # 手動タグ追加
matter-hub tag remove <article_id> "タグ"

# 分析
matter-hub stats                          # 興味の傾向（タグ別集計、著者別、月別保存数）

# 一覧
matter-hub list                           # 最新記事一覧（デフォルト20件）
matter-hub list --all                     # 全件
```

### 出力形式

- デフォルト: テーブル表示
- `--json` フラグ: JSON出力（パイプ連携用）

## 自動タグ付け（Claude API）

### 仕組み

- `sync --tag` 時に、`source='ai'` のタグがない記事を対象にする
- 記事のタイトル・URL・著者・出版社・ハイライトをプロンプトに含めて送信
- Claude Haiku（安価で十分な精度）で3〜5個のタグを生成
- 生成されたタグは `source='ai'` として保存

### プロンプト

```
以下の記事に3〜5個の日本語タグをつけてください。
タグは短く（1〜3語）、カテゴリとして再利用しやすいものにしてください。
既存タグ一覧: {existing_tags}
できるだけ既存タグを再利用してください。
JSON配列で返してください。

タイトル: {title}
URL: {url}
著者: {author}
出版社: {publisher}
ハイライト: {highlights}
```

### タグの正規化

- 表記ゆれ防止のため、既存タグ一覧をプロンプトに含めて再利用を促す

### コスト

- Haiku使用で1記事あたり約0.01円以下
- 数十件なら全件タグ付けしても数円程度

## 技術スタック

- **言語**: Python 3.11+
- **CLI**: `click` ライブラリ
- **DB**: SQLite（標準ライブラリ `sqlite3`）+ FTS5
- **HTTP**: `httpx`（async対応）
- **QRコード**: `qrcode` ライブラリ（ASCII表示）
- **テーブル表示**: `rich` ライブラリ
- **AI**: `anthropic` SDK（Claude Haiku）
- **設定**: `~/.matter-hub/config.json`（トークン保存）
- **DB保存先**: `~/.matter-hub/matter-hub.db`

## 参考情報

- [getmatterapp/obsidian-matter](https://github.com/getmatterapp/obsidian-matter) - 公式Obsidianプラグイン（APIソース）
- [obsidian-matter #56](https://github.com/getmatterapp/obsidian-matter/issues/56) - `updates_feed` エンドポイントの発見
- [MacStories: Reverse-Engineering the Matter API](https://www.macstories.net/stories/macstories-starter-pack-reverse-engineering-the-matter-api-and-my-save-to-matter-shortcut/) - `/save/` エンドポイントの発見
