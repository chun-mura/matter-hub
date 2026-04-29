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

## Webapp（FastAPI + React）

ブラウザから検索・タグフィルター・アーカイブ閲覧・削除・要約・同期ができるローカルWebアプリ。**API（バックエンド）と Vite（フロント）でポートが分かれます。**

### ローカル開発（二重起動）

1. **API（既定ポート 8000）**

```bash
uv run uvicorn matter_hub.webapp.main:app --host 127.0.0.1 --port 8000 --reload
```

2. **フロント（既定ポート 5173）** — Node.js 20 以上が必要です。

```bash
cd frontend
cp .env.example .env   # 初回のみ（中身は空でも可）
npm install
npm run dev
```

ブラウザで `http://localhost:5173` や `http://100.79.172.93:5173` など Vite の URL を開きます。

**推奨（開発）:** `VITE_API_BASE_URL` は**設定しない**（空）。フロントは **`/api/...` へ相対 fetch** し、Vite の **`server.proxy`** が Node 側でバックエンドへ転送します。ブラウザから見ると常に Vite と同一オリジンなので **CORS は不要**です。転送先は `VITE_API_PROXY_TARGET`（未設定時は `http://127.0.0.1:8000`）。API が `8001` なら `.env` に `VITE_API_PROXY_TARGET=http://127.0.0.1:8001` を書いてください。

**注意:** `http://100.79.172.93:5173` でページを開いているのに `fetch('http://localhost:8001/api/...')` すると、`localhost` は**そのブラウザを動かしている PC** を指します。API サーバー上の Matter Hub には届きません。別 PC のブラウザでは **localhost は使わない**か、上記のように **プロキシ＋相対 `/api`** にしてください。

**直 fetch（別オリジン）を使う場合:** `VITE_API_BASE_URL=http://...` を設定すると、ブラウザが直接 API にアクセスします。そのときは API 側の CORS が必要です。

- **既定（開発・API 側）:** `MATTER_HUB_CORS_STRICT` を付けない限り、Vite 常用ポート **5173 / 4173** で多くの `Origin` を正規表現で許可します。
- **`MATTER_HUB_CORS_ORIGINS`** — カンマ区切りの完全一致。
- **`MATTER_HUB_CORS_ORIGIN_REGEX`** — 設定すると既定の広い正規表現の代わりに使われます。
- **`MATTER_HUB_CORS_STRICT=1`** — 本番向け。上記の広い正規表現を無効にします。

API を更新したら **uvicorn を再起動**してください。

本番で単一ポートにまとめる場合は、リバースプロキシ（例: nginx）で `/` を静的ビルド（`frontend/dist`）、`/api` を uvicorn に振り分ける構成が一般的です。

### Docker Compose（API + フロント）

```bash
docker compose up -d
```

- API（ホストから直接叩く場合）: `http://localhost:8001`
- フロント: `http://localhost:5173`（コンテナ内で `npm install` のあと Vite dev）。Compose では **`VITE_API_PROXY_TARGET=http://api:8000`** のため、ブラウザは **`/api` を Vite 経由**で API に届けます（`VITE_API_BASE_URL` は不要）。

```bash
docker compose down
```

- DBファイル (`data/matter-hub.db`) はCLIとコンテナで共有される。
- 検索はFTS5 trigram。タグフィルターはAND。
- `active` (Matterで保存中) / `archived` (Matterでアーカイブ済) / `trend` / `trash` (ローカル削除) を切替。
- `trash` で `restore` すると復元。`active`/`archived` で `delete` するとローカルで非表示、次のsyncでも再importされない。
