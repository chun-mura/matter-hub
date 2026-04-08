# セマンティック検索 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ollamaのembeddingモデルを使い、記事の意味的な類似度で曖昧検索できるようにする

**Architecture:** Ollama `nomic-embed-text` でembeddingベクトルを生成し、SQLiteにBLOBとして保存。検索時はクエリもembeddingに変換し、numpyでコサイン類似度を計算して上位記事を返す。

**Tech Stack:** Ollama (nomic-embed-text), numpy, SQLite (BLOB), httpx

---

## ファイル構成

| ファイル | 操作 | 責務 |
|---------|------|------|
| `matter_hub/ollama.py` | 新規作成 | Ollama API呼び出し（タグ付け + embedding生成） |
| `matter_hub/tagger.py` | 削除 | `ollama.py` に統合 |
| `matter_hub/db.py` | 修正 | embeddingカラム追加、保存・取得・セマンティック検索メソッド |
| `matter_hub/cli.py` | 修正 | `sync --embed`、`search --semantic` 追加、import先変更 |
| `pyproject.toml` | 修正 | `numpy` 依存追加 |
| `tests/test_ollama.py` | 新規作成 | ollama.py のテスト |
| `tests/test_tagger.py` | 削除 | `test_ollama.py` に統合 |
| `tests/test_db.py` | 修正 | embedding関連テスト追加 |
| `tests/test_cli.py` | 修正 | `--semantic`、`--embed` のテスト追加 |

---

### Task 1: tagger.py → ollama.py リネーム

**Files:**
- Create: `matter_hub/ollama.py`
- Delete: `matter_hub/tagger.py`
- Create: `tests/test_ollama.py`
- Delete: `tests/test_tagger.py`
- Modify: `matter_hub/cli.py:156` (import先変更)

- [ ] **Step 1: `matter_hub/ollama.py` を作成**

`tagger.py` の内容をそのままコピーして `ollama.py` に配置。モジュールdocstringだけ変更。

```python
"""Ollama integration for auto-tagging and embedding generation."""

import json
import re

import httpx


def build_prompt(article: dict, highlights: list[dict], existing_tags: list[str]) -> str:
    # 既存コードそのまま
    ...


def parse_tags_response(text: str) -> list[str]:
    # 既存コードそのまま
    ...


def tag_article_ollama(
    article: dict,
    highlights: list[dict],
    existing_tags: list[str],
    model: str = "gemma3:4b",
    base_url: str = "http://localhost:11434",
) -> list[str]:
    # 既存コードそのまま
    ...
```

- [ ] **Step 2: `tests/test_ollama.py` を作成**

`tests/test_tagger.py` の内容をコピーし、importを `matter_hub.ollama` に変更。

```python
from matter_hub.ollama import build_prompt, parse_tags_response, tag_article_ollama

# 全テスト関数は既存のまま
```

- [ ] **Step 3: `cli.py` のimportを変更**

```python
# 変更前
from matter_hub.tagger import tag_article_ollama

# 変更後
from matter_hub.ollama import tag_article_ollama
```

- [ ] **Step 4: 旧ファイル削除**

```bash
rm matter_hub/tagger.py tests/test_tagger.py
```

- [ ] **Step 5: テスト実行**

Run: `uv run pytest -v`
Expected: 全テストPASS

- [ ] **Step 6: コミット**

```bash
git add matter_hub/ollama.py tests/test_ollama.py matter_hub/cli.py pyproject.toml
git rm matter_hub/tagger.py tests/test_tagger.py
git commit -m "refactor: rename tagger.py to ollama.py"
```

---

### Task 2: numpy 依存追加

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: pyproject.toml に numpy 追加**

```toml
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "numpy>=1.26",
    "qrcode>=7.4",
    "rich>=13.0",
]
```

- [ ] **Step 2: インストール確認**

Run: `uv sync`
Expected: numpy がインストールされる

- [ ] **Step 3: コミット**

```bash
git add pyproject.toml uv.lock
git commit -m "build: add numpy dependency for semantic search"
```

---

### Task 3: DB に embedding 保存機能を追加

**Files:**
- Modify: `matter_hub/db.py`
- Modify: `tests/test_db.py`

- [ ] **Step 1: テストを書く — `test_db.py` に embedding テスト追加**

```python
import numpy as np


def test_save_and_get_embedding(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    embedding = np.random.rand(768).astype(np.float32)
    db.save_embedding("art1", embedding.tobytes())
    result = db.get_embedding("art1")
    assert result is not None
    recovered = np.frombuffer(result, dtype=np.float32)
    np.testing.assert_array_almost_equal(embedding, recovered)
    db.close()


def test_articles_without_embedding(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Has embedding", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "No embedding", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    embedding = np.random.rand(768).astype(np.float32)
    db.save_embedding("art1", embedding.tobytes())
    without = db.articles_without_embedding()
    assert len(without) == 1
    assert without[0]["id"] == "art2"
    db.close()


def test_get_all_embeddings(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "A1", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "A2", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    emb1 = np.random.rand(768).astype(np.float32)
    emb2 = np.random.rand(768).astype(np.float32)
    db.save_embedding("art1", emb1.tobytes())
    db.save_embedding("art2", emb2.tobytes())
    results = db.get_all_embeddings()
    assert len(results) == 2
    assert results[0]["id"] in ("art1", "art2")
    assert len(np.frombuffer(results[0]["embedding"], dtype=np.float32)) == 768
    db.close()
```

- [ ] **Step 2: テスト実行して失敗確認**

Run: `uv run pytest tests/test_db.py::test_save_and_get_embedding -v`
Expected: FAIL — `save_embedding` メソッドが存在しない

- [ ] **Step 3: db.py に embedding カラムとメソッド追加**

`_init_tables` に追加:

```python
# _init_tables の末尾、conn.commit() の前に追加
cur.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        article_id TEXT PRIMARY KEY REFERENCES articles(id),
        embedding BLOB NOT NULL
    )
""")
```

メソッド追加:

```python
def save_embedding(self, article_id: str, embedding: bytes) -> None:
    self.conn.execute(
        """INSERT INTO embeddings (article_id, embedding) VALUES (?, ?)
           ON CONFLICT(article_id) DO UPDATE SET embedding=excluded.embedding""",
        (article_id, embedding),
    )
    self.conn.commit()

def get_embedding(self, article_id: str) -> bytes | None:
    row = self.conn.execute(
        "SELECT embedding FROM embeddings WHERE article_id = ?",
        (article_id,),
    ).fetchone()
    return row["embedding"] if row else None

def articles_without_embedding(self) -> list[dict]:
    rows = self.conn.execute(
        """SELECT a.* FROM articles a
           WHERE a.id NOT IN (SELECT article_id FROM embeddings)""",
    ).fetchall()
    return [dict(r) for r in rows]

def get_all_embeddings(self) -> list[dict]:
    rows = self.conn.execute(
        "SELECT article_id as id, embedding FROM embeddings",
    ).fetchall()
    return [{"id": r["id"], "embedding": r["embedding"]} for r in rows]
```

- [ ] **Step 4: テスト実行して全パス確認**

Run: `uv run pytest tests/test_db.py -v`
Expected: 全テストPASS（既存テストも含む）

- [ ] **Step 5: コミット**

```bash
git add matter_hub/db.py tests/test_db.py
git commit -m "feat: add embedding storage to database"
```

---

### Task 4: ollama.py に embedding 生成関数を追加

**Files:**
- Modify: `matter_hub/ollama.py`
- Modify: `tests/test_ollama.py`

- [ ] **Step 1: テストを書く**

`tests/test_ollama.py` に追加:

```python
from matter_hub.ollama import build_embedding_text, generate_embedding


def test_build_embedding_text():
    article = {"title": "LLM入門", "author": "Alice", "url": "https://example.com"}
    tags = ["AI", "機械学習"]
    highlights = [{"text": "transformers are key"}]
    text = build_embedding_text(article, tags, highlights)
    assert "LLM入門" in text
    assert "Alice" in text
    assert "AI" in text
    assert "transformers are key" in text


def test_build_embedding_text_minimal():
    article = {"title": "Test", "author": None, "url": "https://example.com"}
    text = build_embedding_text(article, [], [])
    assert "Test" in text
    assert "著者" not in text


def test_generate_embedding(httpx_mock):
    fake_embedding = [0.1] * 768
    httpx_mock.add_response(
        url="http://localhost:11434/api/embed",
        json={"embeddings": [fake_embedding]},
    )
    result = generate_embedding("test text")
    assert len(result) == 768
    assert result[0] == 0.1
```

- [ ] **Step 2: テスト実行して失敗確認**

Run: `uv run pytest tests/test_ollama.py::test_build_embedding_text -v`
Expected: FAIL — `build_embedding_text` が存在しない

- [ ] **Step 3: ollama.py に関数追加**

```python
def build_embedding_text(article: dict, tags: list[str], highlights: list[dict]) -> str:
    parts = [f"タイトル: {article['title']}"]
    if article.get("author"):
        parts.append(f"著者: {article['author']}")
    if tags:
        parts.append(f"タグ: {', '.join(tags)}")
    if highlights:
        hl_texts = [h["text"] for h in highlights]
        parts.append(f"ハイライト: {' / '.join(hl_texts)}")
    return "\n".join(parts)


def generate_embedding(
    text: str,
    model: str = "nomic-embed-text",
    base_url: str = "http://localhost:11434",
) -> list[float]:
    resp = httpx.post(
        f"{base_url}/api/embed",
        json={"model": model, "input": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embeddings"][0]
```

- [ ] **Step 4: テスト実行**

Run: `uv run pytest tests/test_ollama.py -v`
Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add matter_hub/ollama.py tests/test_ollama.py
git commit -m "feat: add embedding generation via Ollama"
```

---

### Task 5: CLI に `sync --embed` を追加

**Files:**
- Modify: `matter_hub/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: テストを書く**

`tests/test_cli.py` に追加:

```python
def test_sync_with_embed(tmp_path):
    runner = CliRunner()

    sample_entry = {
        "id": "art1",
        "content": {
            "title": "Test Article",
            "url": "https://example.com",
            "author": {"any_name": "Alice"},
            "publisher": {"any_name": "Tech"},
            "publication_date": "2025-01-01",
            "tags": [{"name": "tech", "created_date": "2025-01-01"}],
            "my_annotations": [],
            "my_note": None,
            "library": {"library_state": 1},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [sample_entry]

    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path), \
         patch("matter_hub.cli._ensure_ollama", return_value=True), \
         patch("matter_hub.ollama.generate_embedding", return_value=[0.1] * 768):
        result = runner.invoke(cli, ["sync", "--embed"])

    assert result.exit_code == 0
    assert "embedding" in result.output.lower() or "Embedding" in result.output

    db = Database(db_path)
    emb = db.get_embedding("art1")
    assert emb is not None
    db.close()
```

- [ ] **Step 2: テスト実行して失敗確認**

Run: `uv run pytest tests/test_cli.py::test_sync_with_embed -v`
Expected: FAIL

- [ ] **Step 3: cli.py に `--embed` フラグと `_run_embed` 関数を追加**

`sync` コマンドに `--embed` オプション追加:

```python
@cli.command()
@click.option("--tag", is_flag=True, help="同期後にOllamaで自動タグ付けを実行")
@click.option("--embed", is_flag=True, help="同期後にembeddingを生成")
@click.option("--model", default="gemma3:4b", help="Ollamaモデル名（デフォルト: gemma3:4b）")
def sync(tag, embed, model):
    """Matter APIから記事を同期"""
    # ... 既存の同期ロジック ...

    if tag:
        _run_auto_tag(db, ollama_model=model)

    if embed:
        _run_embed(db)

    db.close()
```

`_run_embed` 関数:

```python
def _run_embed(db: Database):
    import numpy as np
    from matter_hub.ollama import build_embedding_text, generate_embedding

    if not _ensure_ollama():
        return

    articles = db.articles_without_embedding()
    if not articles:
        console.print("[green]Embedding生成対象の記事はありません[/green]")
        return

    console.print(f"[yellow]{len(articles)} 件の記事のEmbeddingを生成中...[/yellow]")

    for article in articles:
        tags = [t["name"] for t in db.get_tags(article["id"])]
        highlights = db.get_highlights(article["id"])
        text = build_embedding_text(article, tags, highlights)
        try:
            embedding = generate_embedding(text)
            embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()
            db.save_embedding(article["id"], embedding_bytes)
            console.print(f"  {article['title'][:50]}... → OK")
        except Exception as e:
            console.print(f"  [red]{article['title'][:50]}... → エラー: {e}[/red]")

    console.print("[green]Embedding生成完了[/green]")
```

- [ ] **Step 4: テスト実行**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add matter_hub/cli.py tests/test_cli.py
git commit -m "feat: add sync --embed flag for embedding generation"
```

---

### Task 6: CLI に `search --semantic` を追加

**Files:**
- Modify: `matter_hub/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: テストを書く**

`tests/test_cli.py` に追加:

```python
import numpy as np


def _seed_db_with_embeddings(db_path):
    """Helper to create a seeded DB with embeddings."""
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Machine Learning入門", "url": "https://ml.example.com",
        "author": "Alice", "publisher": "TechBlog",
        "published_date": "2025-01-15", "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "a2", "title": "料理レシピ集", "url": "https://cook.example.com",
        "author": "Bob", "publisher": "FoodBlog",
        "published_date": "2025-02-10", "note": None, "library_state": 1,
    })
    # a1 has embedding close to query, a2 has different embedding
    emb1 = np.ones(768, dtype=np.float32)
    emb2 = -np.ones(768, dtype=np.float32)
    db.save_embedding("a1", emb1.tobytes())
    db.save_embedding("a2", emb2.tobytes())
    db.close()
    return db_path


def test_search_semantic(tmp_path):
    runner = CliRunner()
    db_path = _seed_db_with_embeddings(tmp_path / "test.db")

    query_emb = np.ones(768, dtype=np.float32) * 0.9

    with patch("matter_hub.cli.get_db_path", return_value=db_path), \
         patch("matter_hub.cli._ensure_ollama", return_value=True), \
         patch("matter_hub.ollama.generate_embedding", return_value=query_emb.tolist()):
        result = runner.invoke(cli, ["search", "--semantic", "機械学習について"])

    assert result.exit_code == 0
    # a1 should appear first (similar direction), a2 last (opposite direction)
    assert "Machine Learning入門" in result.output
```

- [ ] **Step 2: テスト実行して失敗確認**

Run: `uv run pytest tests/test_cli.py::test_search_semantic -v`
Expected: FAIL

- [ ] **Step 3: cli.py の `search` コマンドに `--semantic` 追加**

```python
@cli.command()
@click.argument("query", default="")
@click.option("--tag", "tag_filter", default=None, help="タグで絞り込み")
@click.option("--author", default=None, help="著者で絞り込み")
@click.option("--after", default=None, help="指定日以降の記事 (YYYY-MM-DD)")
@click.option("--semantic", is_flag=True, help="セマンティック検索（意味的な類似度で検索）")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def search(query, tag_filter, author, after, semantic, as_json):
    """記事を検索"""
    db = get_db()

    if semantic:
        articles = _semantic_search(db, query)
    elif tag_filter:
        articles = db.search_by_tag(tag_filter)
    elif query:
        articles = db.search(query)
    else:
        articles = db.list_articles()

    if author:
        articles = [a for a in articles if a.get("author") and author.lower() in a["author"].lower()]
    if after:
        articles = [a for a in articles if a.get("published_date") and a["published_date"] >= after]

    if as_json:
        import json
        click.echo(json.dumps(articles, ensure_ascii=False, indent=2))
    else:
        _print_articles_table(articles)

    db.close()
```

`_semantic_search` 関数:

```python
def _semantic_search(db: Database, query: str, top_n: int = 10) -> list[dict]:
    import numpy as np
    from matter_hub.ollama import generate_embedding

    # embedding未生成の記事があれば自動生成
    without = db.articles_without_embedding()
    if without:
        console.print(f"[yellow]{len(without)} 件の記事のEmbeddingを生成中...[/yellow]")
        _run_embed(db)

    if not _ensure_ollama():
        return []

    # クエリのembedding生成
    query_emb = np.array(generate_embedding(query), dtype=np.float32)

    # 全embeddingを取得してコサイン類似度計算
    all_emb = db.get_all_embeddings()
    if not all_emb:
        console.print("[yellow]Embeddingが生成されていません。`matter-hub sync --embed` を実行してください。[/yellow]")
        return []

    scored = []
    for row in all_emb:
        emb = np.frombuffer(row["embedding"], dtype=np.float32)
        similarity = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
        scored.append((row["id"], float(similarity)))

    scored.sort(key=lambda x: x[1], reverse=True)
    top_ids = [s[0] for s in scored[:top_n]]

    # 記事情報を取得して類似度順で返す
    articles = []
    for article_id in top_ids:
        row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if row:
            articles.append(dict(row))

    return articles
```

- [ ] **Step 4: テスト実行**

Run: `uv run pytest tests/test_cli.py -v`
Expected: 全テストPASS

- [ ] **Step 5: コミット**

```bash
git add matter_hub/cli.py tests/test_cli.py
git commit -m "feat: add semantic search with --semantic flag"
```

---

### Task 7: help コマンドを更新

**Files:**
- Modify: `matter_hub/cli.py`

- [ ] **Step 1: `help_cmd` のコマンド一覧にセマンティック検索を追記**

```python
commands = [
    ("auth",       "QRコード認証でMatterにログイン"),
    ("sync",       "Matter APIから記事を同期（--tag/--embed）"),
    ("list",       "記事一覧を表示"),
    ("search",     "キーワード・タグ・著者・日付で記事を検索（--semantic対応）"),
    ("tags",       "タグ一覧を表示（記事数付き）"),
    ("tag add",    "記事にタグを手動追加"),
    ("tag remove", "記事からタグを削除"),
    ("stats",      "興味の傾向を分析"),
    ("help",       "このヘルプを表示"),
]
```

- [ ] **Step 2: テスト実行**

Run: `uv run pytest -v`
Expected: 全テストPASS

- [ ] **Step 3: コミット**

```bash
git add matter_hub/cli.py
git commit -m "docs: update help command with semantic search info"
```
