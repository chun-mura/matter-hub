# Matter Hub

Matter (web.getmatter.com) に保存した記事をローカルで検索・タグ管理するCLIツール。

## セットアップ

```bash
# プロジェクトディレクトリに移動
cd /path/to/matter-hub

# インストール
uv venv && uv pip install -e .
```

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
