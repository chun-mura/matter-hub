# セマンティック検索の設計

## 概要

Ollamaのembeddingモデル（nomic-embed-text）を使い、記事の意味的な類似度で検索できる機能を追加する。
現在のFTS検索はキーワード完全一致のため、「コードレビューのコスト削減」のような曖昧なクエリではヒットしない。
embeddingベクトルのコサイン類似度を使うことで、意味的に近い記事を返せるようになる。

## アーキテクチャ

```
記事 → タイトル+著者+タグ連結テキスト → Ollama nomic-embed-text → 768次元ベクトル → SQLiteにBLOB保存
検索 → クエリをembedding → 全ベクトルとコサイン類似度計算 → 上位N件返却
```

## CLIインターフェース

- `matter-hub sync --embed` — 同期後にembedding未生成の記事のembeddingを生成
- `matter-hub sync --tag --embed` — タグ付け+embedding両方
- `matter-hub search --semantic "コードレビューのコスト削減"` — セマンティック検索
- `matter-hub search "コードレビュー"` — 従来のFTS検索（変更なし）

`search --semantic` 実行時にembedding未生成の記事があれば自動生成する（初回は遅い）。
`sync --embed` で事前生成も可能。

## データ構造

`articles` テーブルに `embedding` カラム（BLOB）を追加。
768次元のfloat32配列を `numpy.ndarray.tobytes()` でバイト列として保存。

## embedding入力テキスト

```
タイトル: {title}
著者: {author}
タグ: {tag1}, {tag2}, ...
ハイライト: {highlight1} / {highlight2} / ...
```

記事本文はMatter APIから取得できないため、タイトル・著者・タグ・ハイライトを連結。
タイトルは短いが意味が凝縮されており、embeddingモデルとの相性は良い。

## 変更対象ファイル

| ファイル | 変更内容 |
|---------|---------|
| `tagger.py` → `ollama.py` にリネーム | Ollama関連をまとめる。既存のタグ付け + 新規embedding生成関数 |
| `db.py` | `embedding` BLOBカラム追加、保存・取得・未生成記事一覧メソッド追加 |
| `cli.py` | `sync --embed` フラグ追加、`search --semantic` フラグ追加 |
| `pyproject.toml` | `numpy` を依存に追加 |
| テスト各種 | リネームに合わせた更新、新機能のテスト追加 |

## 依存追加

- `numpy` — コサイン類似度計算用。86件程度のデータなので `sqlite-vec` は不要。

## Ollamaモデル

- `nomic-embed-text` — 768次元、軽量で日本語も対応
- 未インストール時は `ollama pull nomic-embed-text` を案内
