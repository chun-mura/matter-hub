# Matter Hub

Matter (web.getmatter.com) に保存した記事をローカルで検索・タグ管理するCLIツール。

## セットアップ

```bash
# インストール（プロジェクトディレクトリ内で実行）
cd /path/to/matter-hub
uv venv && uv pip install -e .

# または、グローバルインストール（どのディレクトリからでも使える）
uv tool install /path/to/matter-hub
```

## 使い方

> **Note:** プロジェクト内のvenvにインストールした場合は、全コマンドの前に `uv run` を付けるか、
> プロジェクトディレクトリで `source .venv/bin/activate` を実行してください。
> `uv tool install` でグローバルインストールした場合は `matter-hub` をそのまま使えます。

```bash
# 認証（MatterアプリでQRコードをスキャン）
# Profile > Settings > Connected Accounts > Obsidian > Scan QR Code
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
matter-hub list            # 最新20件
matter-hub list --all      # 全件
matter-hub list --json     # JSON形式で出力

# タグ管理
matter-hub tags                           # タグ一覧（記事数付き）
matter-hub tag add <article_id> "タグ名"  # タグ追加
matter-hub tag remove <article_id> "タグ名"  # タグ削除

# 分析
matter-hub stats           # 興味の傾向（著者別、月別）
```

## データ保存先

- 設定（認証トークン）: `~/.matter-hub/config.json`
- データベース（SQLite）: `~/.matter-hub/matter-hub.db`
