# Matter Hub

Matter (web.getmatter.com) に保存した記事をローカルで検索・タグ管理するCLIツール。

# Matter API

https://docs.getmatter.com/api を利用して、記事の取得・検索・タグ付けを行います。Ollamaを使ったAI自動タグ付けや、埋め込み生成による意味的な類似検索もサポートしています。

## セットアップ

```bash
# プロジェクトディレクトリに移動
cd /path/to/matter-hub

# インストール
uv venv && uv pip install -e .
```

## Ollamaでのモデルインストール

`sync --tag`（自動タグ付け）や `sync --embed`（埋め込み生成）、意味的な類似検索を使う場合は、[Ollama](https://ollama.com/) をインストールし、次のモデルを取得してください。

1. **Ollama を起動する**  
   macOS ではメニューバーの Ollama アプリを起動するか、ターミナルで `ollama serve` を実行します。

2. **必要なモデルをダウンロードする**（別ターミナルで実行可）

```bash
# 自動タグ付け（デフォルトの --model と一致）
ollama pull gemma3:4b

# 埋め込み生成・類似検索（デフォルトの embedding モデル）
ollama pull nomic-embed-text
```

- タグ付けだけなら `gemma3:4b` のみで構いません。`--model` で別モデルを指定した場合は、その名前で `ollama pull <モデル名>` してください。
- 埋め込み・類似検索を使う場合は `nomic-embed-text` が必要です。

3. **確認**（任意）

```bash
ollama list
```

別ホストの Ollama を使う場合は環境変数 `OLLAMA_BASE_URL`（例: `http://localhost:11434`）を設定します。

## 使い方

```bash
# 認証（MatterアプリでQRコードをスキャン）
# Profile > Settings > Connected Accounts > Obsidian > Scan QR Code
uv run matter-hub auth

# 記事を同期
uv run matter-hub sync

# AI自動タグ付け付きで同期（Ollama使用、要Ollamaインストール）
uv run matter-hub sync --tag

# モデル指定
uv run matter-hub sync --tag --model gemma3:4b
```

## コマンド

```bash
# 検索
uv run matter-hub search "キーワード"
uv run matter-hub search --tag "AI"
uv run matter-hub search --author "名前"
uv run matter-hub search --after 2025-01-01

# 一覧
uv run matter-hub list            # 最新20件
uv run matter-hub list --all      # 全件
uv run matter-hub list --json     # JSON形式で出力

# タグ管理
uv run matter-hub tags                           # タグ一覧（記事数付き）
uv run matter-hub tag add <article_id> "タグ名"  # タグ追加
uv run matter-hub tag remove <article_id> "タグ名"  # タグ削除

# 分析
uv run matter-hub stats           # 興味の傾向（著者別、月別）
```

## データ保存先

- 設定（認証トークン）: `~/.matter-hub/config.json`
- データベース（SQLite）: `data/matter-hub.db`（プロジェクト内、gitignore対象）

## Webapp (Docker)

ブラウザから検索・タグフィルター・アーカイブ閲覧・削除ができるローカルWebアプリ。

```bash
# 起動
docker compose up -d

# http://localhost:8000 を開く

# 停止
docker compose down
```

- DBファイル (`data/matter-hub.db`) はCLIとコンテナで共有される。
- 検索はFTS5 trigram。タグフィルターはAND。
- `active` (Matterで保存中) / `archived` (Matterでアーカイブ済) / `trash` (ローカル削除) を切替。
- `trash` で `restore` すると復元。`active`/`archived` で `delete` するとローカルで非表示、次のsyncでも再importされない。
