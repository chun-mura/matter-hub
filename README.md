# Matter Hub

Matter (web.getmatter.com) に保存した記事をローカルで検索・タグ管理するCLIツール。

## セットアップ

```bash
# インストール
uv venv && uv pip install -e .

# 認証（MatterアプリでQRコードをスキャン）
matter-hub auth

# 記事を同期
matter-hub sync

# AI自動タグ付け付きで同期（要 ANTHROPIC_API_KEY）
export ANTHROPIC_API_KEY=sk-ant-...
matter-hub sync --tag
```

## コマンド

```bash
# 検索
matter-hub search "キーワード"
matter-hub search --tag "AI"
matter-hub search --author "名前"
matter-hub search --after 2025-01-01

# 一覧
matter-hub list
matter-hub list --all
matter-hub list --json

# タグ管理
matter-hub tags
matter-hub tag add <article_id> "タグ名"
matter-hub tag remove <article_id> "タグ名"

# 分析
matter-hub stats
```

## データ保存先

- 設定: `~/.matter-hub/config.json`
- データベース: `~/.matter-hub/matter-hub.db`
