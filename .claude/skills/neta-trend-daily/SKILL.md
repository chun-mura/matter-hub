---
name: neta-trend-daily
description: "IT技術トレンド収集 — はてブIT・HackerNews・Reddit・Zenn・Qiitaから人気記事を収集し、matter-hub DBに保存する"
---

# IT技術トレンド収集

はてなブックマークIT人気エントリー、Hacker News、Reddit、Zenn、Qiitaの人気記事を収集し、matter-hub DBに保存しつつ `data/trends/YYYYMMDD-trend.md` にレポートを出力する。

## 実行手順

### 0. 興味領域

IT技術学習全般を対象とする。特定分野に限定せず、以下を広くカバーする:

- バックエンド（Go, Rust, Python, Java, etc.）
- フロントエンド（React, Vue, Next.js, etc.）
- インフラ/クラウド（AWS, GCP, Kubernetes, Docker）
- AI/ML（LLM, 生成AI, MLOps）
- セキュリティ（脆弱性, 攻撃手法, 防御策）
- データベース/データエンジニアリング
- DevOps/SRE
- OSS/開発ツール
- アーキテクチャ/設計パターン
- キャリア/エンジニア文化

### 1. トレンド情報の収集

以下のサイトから最新のトレンド情報を取得:

**はてブIT（日本市場）**
- https://b.hatena.ne.jp/hotentry/it
- https://b.hatena.ne.jp/hotentry/it/%E3%83%97%E3%83%AD%E3%82%B0%E3%83%A9%E3%83%9F%E3%83%B3%E3%82%B0
- https://b.hatena.ne.jp/hotentry/it/AI%E3%83%BB%E6%A9%9F%E6%A2%B0%E5%AD%A6%E7%BF%92
- https://b.hatena.ne.jp/hotentry/it/%E3%81%AF%E3%81%A6%E3%81%AA%E3%83%96%E3%83%AD%E3%82%B0%EF%BC%88%E3%83%86%E3%82%AF%E3%83%8E%E3%83%AD%E3%82%B8%E3%83%BC%EF%BC%89
- https://b.hatena.ne.jp/hotentry/it/%E3%82%BB%E3%82%AD%E3%83%A5%E3%83%AA%E3%83%86%E3%82%A3%E6%8A%80%E8%A1%93
- https://b.hatena.ne.jp/hotentry/it/%E3%82%A8%E3%83%B3%E3%82%B8%E3%83%8B%E3%82%A2
- 各エントリーの**タイトル、元記事URL、ブックマーク数**を必ず取得すること
- はてブのエントリーページURLではなく、リンク先の元記事URLを抽出

**Hacker News（グローバル）**
- https://news.ycombinator.com/
- 各記事の**タイトル、HNコメントページURL（`https://news.ycombinator.com/item?id=XXXXX`形式）、ポイント数**を取得
- **元記事URLではなくHNのコメントページURLを使用すること**（コメントも確認できるようにするため）
- **タイトルは日本語に翻訳して出力**

**Zenn（日本語技術記事）**
- Bashツールで以下を実行:
```bash
curl -s "https://zenn.dev/api/articles?order=daily&count=20" | jq -r '.articles[] | "\(.title)|\(.liked_count)|\(.path)"'
```
- データ構造:
  - `title`: タイトル
  - `liked_count`: いいね数
  - `path`: パス（`https://zenn.dev` + path で完全URL）
- 各記事の**タイトル、URL（`https://zenn.dev` + path）、いいね数**を取得

**Qiita（日本語技術記事）**
- Bashツールで以下を実行:
```bash
curl -s "https://qiita.com/api/v2/items?page=1&per_page=20&query=stocks%3A%3E10+created%3A%3E$(date -v-1d +%Y-%m-%d)" | jq -r '.[] | "\(.title)|\(.likes_count)|\(.url)"'
```
- 各記事の**タイトル、URL、いいね数**を取得

**Reddit（13サブレッド）**
- **重要**: WebFetchツールはreddit.comをブロックするため、**Bashツールでcurlコマンドを使用**すること
- 各サブレッドから `/hot.json?t=day&limit=10` で上位10件を取得
- **old.reddit.com**を使用（www.reddit.comではない）
- User-Agentヘッダーを設定: `"User-Agent: neta-trend-collector/1.0 (trend analysis tool)"`
- 各記事の**タイトル、Redditコメントページの完全URL、投票数（ups）、コメント数**を取得
- **タイトルは日本語に翻訳して出力**

取得例（Bashツールで実行）:
```bash
curl -s -H "User-Agent: neta-trend-collector/1.0 (trend analysis tool)" \
  "https://old.reddit.com/r/programming/hot.json?t=day&limit=10" | \
  jq -r '.data.children[] | "\(.data.title)|\(.data.ups)|\(.data.num_comments)|https://www.reddit.com\(.data.permalink)"'
```

対象サブレッド:

セキュリティ系:
- r/netsec
- r/cybersecurity

AI系:
- r/OpenAI
- r/LocalLLaMA
- r/ClaudeCode

コア技術系:
- r/programming
- r/golang
- r/rust
- r/devops

Web開発系:
- r/webdev
- r/javascript

OSS系:
- r/opensource

インフラ/クラウド系:
- r/kubernetes

### 2. 分析

収集した情報を以下の観点で分析:

**興味度の定義**:
- ★★★: IT学習に直結する実践的・技術的な内容（チュートリアル、ベストプラクティス、新機能解説、アーキテクチャ事例）
- ★★: IT知識として有用（技術トレンド全般、ツール紹介、エンジニアリング文化）
- ★: 一般的なIT/技術ニュース

**各ソースの評価ポイント**:
- はてブIT: 日本のエンジニアに刺さりやすい話題、ブクマ数が高い記事
- Hacker News: グローバル技術トレンド、ポイント数が高い記事
- Zenn/Qiita: 日本語の実践的な技術記事、いいね数が高い記事
- Reddit: 投票数・コメント数による反応評価、議論が活発なトピック

### 3. DB保存

注目トピック（★★以上）の記事をmatter-hub DBにインポートする。

Bashツールで以下を実行:
```bash
# はてブの記事
matter-hub import url "https://example.com/article1" --source hatena --tag "トレンド"

# Hacker Newsの記事（HNコメントページURLを保存）
matter-hub import url "https://news.ycombinator.com/item?id=XXXXX" --source hackernews --tag "トレンド"

# Zennの記事
matter-hub import url "https://zenn.dev/user/articles/slug" --source zenn --tag "トレンド"

# Qiitaの記事
matter-hub import url "https://qiita.com/user/items/xxxxx" --source qiita --tag "トレンド"

# Redditの記事
matter-hub import url "https://www.reddit.com/r/programming/comments/..." --source reddit --tag "トレンド"
```

複数URLをまとめてインポートできる:
```bash
matter-hub import url "URL1" "URL2" "URL3" --source hatena --tag "トレンド"
```

### 4. レポート出力

**まず「トレンド収集完了。」というメッセージを返してから、結果を `data/trends/YYYYMMDD-trend.md` に保存。**

以下のフォーマットで出力:

```markdown
# ITトレンド: YYYY-MM-DD

## はてブIT（日本市場）

### 注目トピック

| タイトル | ブクマ数 | 興味度 | カテゴリ | メモ |
|---------|---------|--------|---------|------|
| [タイトル](元記事URL) | XXX users | ★★★/★★/★ | AI/インフラ/開発等 | 学習ポイント |

### 全エントリー

1. [タイトル](元記事URL) (XXX users) - 概要
2. ...

## Hacker News（グローバル）

### 注目トピック

| タイトル | ポイント | 興味度 | カテゴリ | メモ |
|---------|---------|--------|---------|------|
| [タイトル](HNコメントページURL) | XXXpt | ★★★/★★/★ | AI/Security/Dev等 | 学習ポイント |

### 全エントリー

1. [タイトル](HNコメントページURL) (XXXpt) - 概要
2. ...

## Zenn（日本語技術記事）

### 注目トピック

| タイトル | いいね数 | 興味度 | カテゴリ | メモ |
|---------|---------|--------|---------|------|
| [タイトル](URL) | XXX | ★★★/★★/★ | AI/Go/React等 | 学習ポイント |

### 全エントリー

1. [タイトル](URL) (XXX likes) - 概要
2. ...

## Qiita（日本語技術記事）

### 注目トピック

| タイトル | いいね数 | 興味度 | カテゴリ | メモ |
|---------|---------|--------|---------|------|
| [タイトル](URL) | XXX | ★★★/★★/★ | AI/Docker/AWS等 | 学習ポイント |

### 全エントリー

1. [タイトル](URL) (XXX likes) - 概要
2. ...

## Reddit（13サブレッド）

### 注目トピック

| タイトル | 投票数 | コメント数 | 興味度 | カテゴリ | サブレッド | メモ |
|---------|--------|-----------|--------|---------|-----------|------|
| [タイトル](RedditコメントページURL) | XXX ups | XXX | ★★★/★★/★ | Security/AI/OSS等 | r/subreddit | 学習ポイント |

### カテゴリ別エントリー

#### セキュリティ系
1. [タイトル](RedditコメントページURL) (XXX ups, XXX comments) - r/netsec - 概要

#### AI系
1. [タイトル](RedditコメントページURL) (XXX ups, XXX comments) - r/OpenAI - 概要

#### コア技術系
1. [タイトル](RedditコメントページURL) (XXX ups, XXX comments) - r/programming - 概要

#### Web開発系
1. [タイトル](RedditコメントページURL) (XXX ups, XXX comments) - r/webdev - 概要

#### OSS/インフラ系
1. [タイトル](RedditコメントページURL) (XXX ups, XXX comments) - r/opensource - 概要
```

## 注意事項

- WebFetchツールを使用して情報を取得（Reddit/Zenn/QiitaはBashツールでcurlを使用）
- **すべての記事にURLリンクを必ず含める（リンクなしは不可）**
- **はてブは元記事のURLを必ず取得**（はてブページURLではなく）
- **Hacker NewsはHNコメントページURL（`item?id=`形式）を使用**（元記事URLではなく）
- **Hacker News/Redditのタイトルは日本語に翻訳**
- Reddit APIレート制限に注意（1分あたり60リクエスト程度）
- 出力ファイルのYYYYMMDDは実行日の日付を使用
- ★★以上の記事は必ず `matter-hub import url` でDB保存する
- data/trends/ ディレクトリがなければ作成する
