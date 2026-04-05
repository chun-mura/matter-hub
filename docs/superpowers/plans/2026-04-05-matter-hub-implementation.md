# Matter Hub Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python CLI tool that syncs articles from Matter's internal API into a local SQLite database, with full-text search, tag management, and Claude-powered auto-tagging.

**Architecture:** Python CLI using `click` for commands, `httpx` for Matter API requests, `sqlite3` + FTS5 for storage/search, `anthropic` SDK for auto-tagging, and `rich` for terminal output. Config and DB stored in `~/.matter-hub/`.

**Tech Stack:** Python 3.11+, click, httpx, qrcode, rich, anthropic SDK, SQLite FTS5, uv (package management)

---

## File Structure

```
matter-hub/
├── matter_hub/
│   ├── __init__.py       # Package init, version
│   ├── cli.py            # Click CLI entry point and all commands
│   ├── api.py            # Matter API client (auth, sync)
│   ├── db.py             # SQLite schema, CRUD, FTS queries
│   ├── tagger.py         # Claude API auto-tagging
│   └── config.py         # Config file read/write (~/.matter-hub/)
├── tests/
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_db.py
│   ├── test_api.py
│   ├── test_tagger.py
│   └── test_cli.py
├── pyproject.toml        # Project metadata, dependencies, CLI entry point
├── .gitignore
└── .env.example          # Example env file
```

---

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `.env.example`
- Create: `matter_hub/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "matter-hub"
version = "0.1.0"
description = "CLI tool to sync, search, and tag Matter articles"
requires-python = ">=3.11"
dependencies = [
    "click>=8.1",
    "httpx>=0.27",
    "qrcode>=7.4",
    "rich>=13.0",
    "anthropic>=0.40",
]

[project.scripts]
matter-hub = "matter_hub.cli:cli"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[dependency-groups]
dev = [
    "pytest>=8.0",
    "pytest-httpx>=0.35",
]
```

- [ ] **Step 2: Create .gitignore**

```
__pycache__/
*.pyc
.env
*.db
.venv/
dist/
*.egg-info/
.pytest_cache/
```

- [ ] **Step 3: Create .env.example**

```
ANTHROPIC_API_KEY=sk-ant-...
```

- [ ] **Step 4: Create matter_hub/__init__.py**

```python
"""Matter Hub - CLI tool to sync, search, and tag Matter articles."""

__version__ = "0.1.0"
```

- [ ] **Step 5: Create tests/__init__.py**

Empty file.

- [ ] **Step 6: Install project with dev dependencies**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv venv && uv pip install -e ".[dev]"`

Note: `uv venv` creates `.venv/` in the project root. All subsequent commands assume this venv is active. Use `source .venv/bin/activate` or prefix commands with `uv run`.

Expected: Successful install with all dependencies

- [ ] **Step 7: Verify installation**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run matter-hub --help`

Expected: Click shows help (will error since cli.py doesn't exist yet — that's fine, just verify the package installs)

- [ ] **Step 8: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add pyproject.toml .gitignore .env.example matter_hub/__init__.py tests/__init__.py
git commit -m "chore: scaffold project with pyproject.toml and dependencies"
```

---

### Task 2: Config module

**Files:**
- Create: `matter_hub/config.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write failing tests for config**

```python
# tests/test_config.py
import json
from pathlib import Path

from matter_hub.config import load_config, save_config, get_db_path


def test_load_config_returns_empty_when_no_file(tmp_path):
    config = load_config(tmp_path / "config.json")
    assert config == {}


def test_save_and_load_config(tmp_path):
    config_path = tmp_path / "config.json"
    data = {"access_token": "abc123", "refresh_token": "def456"}
    save_config(data, config_path)
    loaded = load_config(config_path)
    assert loaded == data


def test_save_config_creates_parent_dirs(tmp_path):
    config_path = tmp_path / "subdir" / "config.json"
    save_config({"key": "value"}, config_path)
    assert config_path.exists()


def test_get_db_path():
    db_path = get_db_path()
    assert db_path.name == "matter-hub.db"
    assert ".matter-hub" in str(db_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_config.py -v`

Expected: FAIL with `ModuleNotFoundError` or `ImportError`

- [ ] **Step 3: Implement config module**

```python
# matter_hub/config.py
"""Configuration management for Matter Hub.

Stores config (tokens) in ~/.matter-hub/config.json.
Stores database in ~/.matter-hub/matter-hub.db.
"""

import json
from pathlib import Path

DEFAULT_DIR = Path.home() / ".matter-hub"
DEFAULT_CONFIG_PATH = DEFAULT_DIR / "config.json"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_config(data: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def get_db_path() -> Path:
    return DEFAULT_DIR / "matter-hub.db"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_config.py -v`

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/config.py tests/test_config.py
git commit -m "feat: add config module for token and path management"
```

---

### Task 3: Database module

**Files:**
- Create: `matter_hub/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Write failing tests for database**

```python
# tests/test_db.py
from matter_hub.db import Database


def test_init_creates_tables(tmp_path):
    db = Database(tmp_path / "test.db")
    # Verify tables exist by inserting and querying
    db.upsert_article({
        "id": "art1",
        "title": "Test Article",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 1,
    })
    articles = db.search("")
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article"
    db.close()


def test_upsert_article_updates_existing(tmp_path):
    db = Database(tmp_path / "test.db")
    article = {
        "id": "art1",
        "title": "Original",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 1,
    }
    db.upsert_article(article)
    article["title"] = "Updated"
    db.upsert_article(article)
    articles = db.list_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Updated"
    db.close()


def test_add_and_query_tags(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "matter")
    db.add_tag("art1", "Python", "ai")
    tags = db.get_tags("art1")
    assert len(tags) == 2
    assert {"name": "AI", "source": "matter"} in tags
    db.close()


def test_add_and_query_highlights(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_highlight("art1", "important text", "my note", "2025-01-01")
    highlights = db.get_highlights("art1")
    assert len(highlights) == 1
    assert highlights[0]["text"] == "important text"
    db.close()


def test_fts_search(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Machine Learning Guide",
        "url": "https://example.com", "author": "Alice",
        "publisher": "TechBlog", "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "Cooking Recipes",
        "url": "https://example.com/cook", "author": "Bob",
        "publisher": "FoodBlog", "published_date": None,
        "note": None, "library_state": 1,
    })
    results = db.search("Machine")
    assert len(results) == 1
    assert results[0]["id"] == "art1"
    db.close()


def test_search_by_tag(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Article 1", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "Article 2", "url": "https://example.com/2",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    results = db.search_by_tag("AI")
    assert len(results) == 1
    assert results[0]["id"] == "art1"
    db.close()


def test_list_all_tags_with_counts(tmp_path):
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
    db.add_tag("art1", "AI", "ai")
    db.add_tag("art2", "AI", "ai")
    db.add_tag("art1", "Python", "ai")
    tag_counts = db.list_tags()
    assert tag_counts == [("AI", 2), ("Python", 1)]
    db.close()


def test_remove_tag(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    db.remove_tag("art1", "AI")
    tags = db.get_tags("art1")
    assert len(tags) == 0
    db.close()


def test_articles_without_ai_tags(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Tagged", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "Untagged", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    untagged = db.articles_without_ai_tags()
    assert len(untagged) == 1
    assert untagged[0]["id"] == "art2"
    db.close()


def test_stats(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "A1", "url": "https://a.com",
        "author": "Alice", "publisher": "TechBlog",
        "published_date": "2025-01-15", "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "A2", "url": "https://b.com",
        "author": "Alice", "publisher": "FoodBlog",
        "published_date": "2025-02-10", "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    db.add_tag("art2", "AI", "ai")
    stats = db.get_stats()
    assert stats["total_articles"] == 2
    assert stats["total_tags"] == 1
    assert ("Alice", 2) in stats["top_authors"]
    db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_db.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement database module**

```python
# matter_hub/db.py
"""SQLite database for storing and querying Matter articles."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Database:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS articles (
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

            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT NOT NULL REFERENCES articles(id),
                name TEXT NOT NULL,
                source TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS highlights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id TEXT NOT NULL REFERENCES articles(id),
                text TEXT NOT NULL,
                note TEXT,
                created_date TEXT
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS articles_fts USING fts5(
                title, author, publisher, note,
                content='articles', content_rowid='rowid'
            );

            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, author, publisher, note)
                VALUES (new.rowid, new.title, new.author, new.publisher, new.note);
            END;

            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, author, publisher, note)
                VALUES ('delete', old.rowid, old.title, old.author, old.publisher, old.note);
            END;

            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, author, publisher, note)
                VALUES ('delete', old.rowid, old.title, old.author, old.publisher, old.note);
                INSERT INTO articles_fts(rowid, title, author, publisher, note)
                VALUES (new.rowid, new.title, new.author, new.publisher, new.note);
            END;
        """)
        self.conn.commit()

    def upsert_article(self, article: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            """INSERT INTO articles (id, title, url, author, publisher, published_date, note, library_state, synced_at)
               VALUES (:id, :title, :url, :author, :publisher, :published_date, :note, :library_state, :synced_at)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, url=excluded.url, author=excluded.author,
                 publisher=excluded.publisher, published_date=excluded.published_date,
                 note=excluded.note, library_state=excluded.library_state, synced_at=excluded.synced_at""",
            {**article, "synced_at": now},
        )
        self.conn.commit()

    def add_tag(self, article_id: str, name: str, source: str) -> None:
        existing = self.conn.execute(
            "SELECT id FROM tags WHERE article_id = ? AND name = ? AND source = ?",
            (article_id, name, source),
        ).fetchone()
        if existing:
            return
        self.conn.execute(
            "INSERT INTO tags (article_id, name, source) VALUES (?, ?, ?)",
            (article_id, name, source),
        )
        self.conn.commit()

    def remove_tag(self, article_id: str, name: str) -> None:
        self.conn.execute(
            "DELETE FROM tags WHERE article_id = ? AND name = ?",
            (article_id, name),
        )
        self.conn.commit()

    def get_tags(self, article_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT name, source FROM tags WHERE article_id = ?",
            (article_id,),
        ).fetchall()
        return [{"name": r["name"], "source": r["source"]} for r in rows]

    def add_highlight(self, article_id: str, text: str, note: str | None, created_date: str | None) -> None:
        self.conn.execute(
            "INSERT INTO highlights (article_id, text, note, created_date) VALUES (?, ?, ?, ?)",
            (article_id, text, note, created_date),
        )
        self.conn.commit()

    def get_highlights(self, article_id: str) -> list[dict]:
        rows = self.conn.execute(
            "SELECT text, note, created_date FROM highlights WHERE article_id = ?",
            (article_id,),
        ).fetchall()
        return [{"text": r["text"], "note": r["note"], "created_date": r["created_date"]} for r in rows]

    def search(self, query: str) -> list[dict]:
        if not query.strip():
            return self.list_articles()
        rows = self.conn.execute(
            """SELECT a.* FROM articles a
               JOIN articles_fts f ON a.rowid = f.rowid
               WHERE articles_fts MATCH ?
               ORDER BY rank""",
            (query,),
        ).fetchall()
        return [dict(r) for r in rows]

    def search_by_tag(self, tag_name: str) -> list[dict]:
        rows = self.conn.execute(
            """SELECT a.* FROM articles a
               JOIN tags t ON a.id = t.article_id
               WHERE t.name = ?
               ORDER BY a.published_date DESC""",
            (tag_name,),
        ).fetchall()
        return [dict(r) for r in rows]

    def list_articles(self, limit: int | None = None) -> list[dict]:
        sql = "SELECT * FROM articles ORDER BY synced_at DESC"
        if limit:
            sql += f" LIMIT {limit}"
        rows = self.conn.execute(sql).fetchall()
        return [dict(r) for r in rows]

    def list_tags(self) -> list[tuple[str, int]]:
        rows = self.conn.execute(
            "SELECT name, COUNT(*) as cnt FROM tags GROUP BY name ORDER BY cnt DESC",
        ).fetchall()
        return [(r["name"], r["cnt"]) for r in rows]

    def articles_without_ai_tags(self) -> list[dict]:
        rows = self.conn.execute(
            """SELECT a.* FROM articles a
               WHERE a.id NOT IN (
                   SELECT article_id FROM tags WHERE source = 'ai'
               )""",
        ).fetchall()
        return [dict(r) for r in rows]

    def get_all_tag_names(self) -> list[str]:
        rows = self.conn.execute("SELECT DISTINCT name FROM tags").fetchall()
        return [r["name"] for r in rows]

    def get_stats(self) -> dict:
        total = self.conn.execute("SELECT COUNT(*) as c FROM articles").fetchone()["c"]
        tag_count = self.conn.execute("SELECT COUNT(DISTINCT name) as c FROM tags").fetchone()["c"]
        authors = self.conn.execute(
            "SELECT author, COUNT(*) as c FROM articles WHERE author IS NOT NULL GROUP BY author ORDER BY c DESC LIMIT 10"
        ).fetchall()
        monthly = self.conn.execute(
            "SELECT substr(published_date, 1, 7) as month, COUNT(*) as c FROM articles WHERE published_date IS NOT NULL GROUP BY month ORDER BY month DESC LIMIT 12"
        ).fetchall()
        return {
            "total_articles": total,
            "total_tags": tag_count,
            "top_authors": [(r["author"], r["c"]) for r in authors],
            "monthly": [(r["month"], r["c"]) for r in monthly],
        }

    def clear_highlights(self, article_id: str) -> None:
        self.conn.execute("DELETE FROM highlights WHERE article_id = ?", (article_id,))
        self.conn.commit()

    def clear_matter_tags(self, article_id: str) -> None:
        self.conn.execute("DELETE FROM tags WHERE article_id = ? AND source = 'matter'", (article_id,))
        self.conn.commit()

    def close(self):
        self.conn.close()
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_db.py -v`

Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/db.py tests/test_db.py
git commit -m "feat: add SQLite database module with FTS5 search"
```

---

### Task 4: Matter API client

**Files:**
- Create: `matter_hub/api.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Write failing tests for API client**

```python
# tests/test_api.py
import json
import httpx
import pytest

from matter_hub.api import MatterClient, parse_feed_entry

SAMPLE_FEED_ENTRY = {
    "id": "entry1",
    "content": {
        "title": "Test Article",
        "url": "https://example.com/article",
        "author": {"any_name": "Alice"},
        "publisher": {"any_name": "TechBlog"},
        "publication_date": "2025-01-15",
        "tags": [
            {"name": "tech", "created_date": "2025-01-15"}
        ],
        "my_annotations": [
            {"text": "highlighted text", "note": "my note", "created_date": "2025-01-16", "word_start": 0, "word_end": 10}
        ],
        "my_note": {"note": "article note"},
        "library": {"library_state": 1},
    },
    "annotations": [],
}

SAMPLE_DELETED_ENTRY = {
    "id": "entry2",
    "content": {
        "title": "Deleted",
        "url": "https://example.com/deleted",
        "author": {"any_name": None},
        "publisher": {"any_name": None},
        "publication_date": None,
        "tags": [],
        "my_annotations": [],
        "my_note": {"note": ""},
        "library": {"library_state": 3},
    },
    "annotations": [],
}


def test_parse_feed_entry():
    result = parse_feed_entry(SAMPLE_FEED_ENTRY)
    assert result["article"]["id"] == "entry1"
    assert result["article"]["title"] == "Test Article"
    assert result["article"]["author"] == "Alice"
    assert result["article"]["publisher"] == "TechBlog"
    assert result["article"]["url"] == "https://example.com/article"
    assert result["article"]["library_state"] == 1
    assert result["article"]["note"] == "article note"
    assert len(result["tags"]) == 1
    assert result["tags"][0]["name"] == "tech"
    assert len(result["highlights"]) == 1
    assert result["highlights"][0]["text"] == "highlighted text"


def test_parse_feed_entry_deleted():
    result = parse_feed_entry(SAMPLE_DELETED_ENTRY)
    assert result["article"]["library_state"] == 3


def test_parse_feed_entry_null_fields():
    entry = {
        "id": "entry3",
        "content": {
            "title": "Minimal",
            "url": "https://example.com",
            "author": None,
            "publisher": None,
            "publication_date": None,
            "tags": [],
            "my_annotations": [],
            "my_note": None,
            "library": None,
        },
        "annotations": [],
    }
    result = parse_feed_entry(entry)
    assert result["article"]["author"] is None
    assert result["article"]["publisher"] is None
    assert result["article"]["library_state"] is None
    assert result["article"]["note"] is None


def test_trigger_qr_login(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/qr_login/trigger/",
        json={"session_token": "test_session_123"},
    )
    client = MatterClient()
    token = client.trigger_qr_login()
    assert token == "test_session_123"


def test_exchange_token_success(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/qr_login/exchange/",
        json={"access_token": "acc_123", "refresh_token": "ref_456"},
    )
    client = MatterClient()
    result = client.exchange_token("session_123")
    assert result == {"access_token": "acc_123", "refresh_token": "ref_456"}


def test_exchange_token_pending(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/qr_login/exchange/",
        status_code=408,
    )
    client = MatterClient()
    result = client.exchange_token("session_123")
    assert result is None


def test_fetch_updates_feed(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/library_items/updates_feed/",
        json={"feed": [SAMPLE_FEED_ENTRY], "next": None},
    )
    client = MatterClient(access_token="test_token")
    entries = client.fetch_all_articles()
    assert len(entries) == 1
    assert entries[0]["id"] == "entry1"


def test_fetch_updates_feed_pagination(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/library_items/updates_feed/",
        json={
            "feed": [SAMPLE_FEED_ENTRY],
            "next": "https://api.getmatter.app/api/v11/library_items/updates_feed/?page=2",
        },
    )
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/library_items/updates_feed/?page=2",
        json={"feed": [SAMPLE_DELETED_ENTRY], "next": None},
    )
    client = MatterClient(access_token="test_token")
    entries = client.fetch_all_articles()
    assert len(entries) == 2


def test_refresh_token(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/token/refresh/",
        json={"access_token": "new_acc", "refresh_token": "new_ref"},
    )
    client = MatterClient(access_token="old", refresh_token="old_ref")
    result = client.refresh_access_token()
    assert result["access_token"] == "new_acc"
    assert client.access_token == "new_acc"
    assert client.refresh_token == "new_ref"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_api.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement API client**

```python
# matter_hub/api.py
"""Matter API client for authentication and article fetching."""

import httpx

BASE_URL = "https://api.getmatter.app/api/v11"


def parse_feed_entry(entry: dict) -> dict:
    content = entry["content"]
    author_obj = content.get("author")
    publisher_obj = content.get("publisher")
    library_obj = content.get("library")
    note_obj = content.get("my_note")

    article = {
        "id": entry["id"],
        "title": content["title"],
        "url": content["url"],
        "author": author_obj["any_name"] if author_obj else None,
        "publisher": publisher_obj["any_name"] if publisher_obj else None,
        "published_date": content.get("publication_date"),
        "note": note_obj.get("note") if note_obj else None,
        "library_state": library_obj["library_state"] if library_obj else None,
    }

    tags = [
        {"name": t["name"], "created_date": t.get("created_date")}
        for t in (content.get("tags") or [])
    ]

    highlights = [
        {
            "text": a["text"],
            "note": a.get("note"),
            "created_date": a.get("created_date"),
        }
        for a in (content.get("my_annotations") or [])
    ]

    return {"article": article, "tags": tags, "highlights": highlights}


class MatterClient:
    def __init__(self, access_token: str | None = None, refresh_token: str | None = None):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.http = httpx.Client(timeout=30)

    def _headers(self) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers

    def trigger_qr_login(self) -> str:
        resp = self.http.post(
            f"{BASE_URL}/qr_login/trigger/",
            json={"client_type": "integration"},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        return resp.json()["session_token"]

    def exchange_token(self, session_token: str) -> dict | None:
        resp = self.http.post(
            f"{BASE_URL}/qr_login/exchange/",
            json={"session_token": session_token},
            headers={"Content-Type": "application/json"},
        )
        if resp.status_code == 408:
            return None
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    def refresh_access_token(self) -> dict:
        resp = self.http.post(
            f"{BASE_URL}/token/refresh/",
            json={"refresh_token": self.refresh_token},
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        return data

    def fetch_all_articles(self) -> list[dict]:
        url = f"{BASE_URL}/library_items/updates_feed/"
        all_entries = []
        while url:
            resp = self.http.get(url, headers=self._headers())
            resp.raise_for_status()
            data = resp.json()
            all_entries.extend(data.get("feed", []))
            url = data.get("next")
        return all_entries
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_api.py -v`

Expected: 10 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/api.py tests/test_api.py
git commit -m "feat: add Matter API client with auth and article fetching"
```

---

### Task 5: Auto-tagger module

**Files:**
- Create: `matter_hub/tagger.py`
- Create: `tests/test_tagger.py`

- [ ] **Step 1: Write failing tests for tagger**

```python
# tests/test_tagger.py
from unittest.mock import MagicMock, patch

from matter_hub.tagger import build_prompt, parse_tags_response, tag_article


def test_build_prompt():
    article = {
        "title": "Introduction to LLMs",
        "url": "https://example.com/llm",
        "author": "Alice",
        "publisher": "AI Blog",
    }
    highlights = [{"text": "transformers are key", "note": None}]
    existing_tags = ["AI", "機械学習"]
    prompt = build_prompt(article, highlights, existing_tags)
    assert "Introduction to LLMs" in prompt
    assert "Alice" in prompt
    assert "transformers are key" in prompt
    assert "AI" in prompt
    assert "機械学習" in prompt


def test_build_prompt_no_highlights():
    article = {
        "title": "Test",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
    }
    prompt = build_prompt(article, [], [])
    assert "Test" in prompt


def test_parse_tags_response_json_array():
    assert parse_tags_response('["AI", "機械学習", "LLM"]') == ["AI", "機械学習", "LLM"]


def test_parse_tags_response_with_markdown():
    assert parse_tags_response('```json\n["AI", "LLM"]\n```') == ["AI", "LLM"]


def test_parse_tags_response_invalid():
    assert parse_tags_response("not json at all") == []


def test_tag_article():
    mock_client = MagicMock()
    mock_client.messages.create.return_value = MagicMock(
        content=[MagicMock(text='["AI", "自然言語処理", "LLM"]')]
    )
    article = {
        "title": "NLP Guide",
        "url": "https://example.com",
        "author": "Bob",
        "publisher": "Tech",
    }
    tags = tag_article(mock_client, article, [], ["AI", "Python"])
    assert len(tags) == 3
    assert "AI" in tags
    mock_client.messages.create.assert_called_once()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_tagger.py -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement tagger module**

```python
# matter_hub/tagger.py
"""Claude API auto-tagging for articles."""

import json
import re

import anthropic


def build_prompt(article: dict, highlights: list[dict], existing_tags: list[str]) -> str:
    parts = [
        "以下の記事に3〜5個の日本語タグをつけてください。",
        "タグは短く（1〜3語）、カテゴリとして再利用しやすいものにしてください。",
    ]
    if existing_tags:
        parts.append(f"既存タグ一覧: {', '.join(existing_tags)}")
        parts.append("できるだけ既存タグを再利用してください。")
    parts.append("JSON配列で返してください。例: [\"AI\", \"Web開発\"]")
    parts.append("")
    parts.append(f"タイトル: {article['title']}")
    parts.append(f"URL: {article['url']}")
    if article.get("author"):
        parts.append(f"著者: {article['author']}")
    if article.get("publisher"):
        parts.append(f"出版社: {article['publisher']}")
    if highlights:
        hl_texts = [h["text"] for h in highlights]
        parts.append(f"ハイライト: {' / '.join(hl_texts)}")
    return "\n".join(parts)


def parse_tags_response(text: str) -> list[str]:
    cleaned = re.sub(r"```json\s*", "", text)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.strip()
    try:
        result = json.loads(cleaned)
        if isinstance(result, list) and all(isinstance(t, str) for t in result):
            return result
    except (json.JSONDecodeError, TypeError):
        pass
    return []


def tag_article(
    client: anthropic.Anthropic,
    article: dict,
    highlights: list[dict],
    existing_tags: list[str],
) -> list[str]:
    prompt = build_prompt(article, highlights, existing_tags)
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return parse_tags_response(response.content[0].text)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_tagger.py -v`

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/tagger.py tests/test_tagger.py
git commit -m "feat: add Claude API auto-tagger for articles"
```

---

### Task 6: CLI - auth command

**Files:**
- Create: `matter_hub/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for auth command**

```python
# tests/test_cli.py
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from matter_hub.cli import cli


def test_auth_displays_qr_and_saves_token():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.trigger_qr_login.return_value = "session_123"
    mock_client.exchange_token.side_effect = [None, {"access_token": "acc", "refresh_token": "ref"}]

    with patch("matter_hub.cli.MatterClient", return_value=mock_client), \
         patch("matter_hub.cli.save_config") as mock_save, \
         patch("matter_hub.cli.qrcode") as mock_qr, \
         patch("matter_hub.cli.time") as mock_time:
        result = runner.invoke(cli, ["auth"])

    assert result.exit_code == 0
    assert "認証成功" in result.output
    mock_save.assert_called_once()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_cli.py::test_auth_displays_qr_and_saves_token -v`

Expected: FAIL with `ImportError`

- [ ] **Step 3: Implement CLI with auth command**

```python
# matter_hub/cli.py
"""CLI entry point for Matter Hub."""

import os
import sys
import time

import click
import qrcode
from rich.console import Console
from rich.table import Table

from matter_hub.api import MatterClient, parse_feed_entry
from matter_hub.config import load_config, save_config, get_db_path
from matter_hub.db import Database

console = Console()


def get_client_from_config() -> MatterClient:
    config = load_config()
    access_token = config.get("access_token")
    refresh_token = config.get("refresh_token")
    if not access_token:
        console.print("[red]未認証です。先に `matter-hub auth` を実行してください。[/red]")
        sys.exit(1)
    return MatterClient(access_token=access_token, refresh_token=refresh_token)


def get_db() -> Database:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Database(db_path)


@click.group()
def cli():
    """Matter Hub - Matter記事の検索・タグ管理CLI"""
    pass


@cli.command()
def auth():
    """QRコード認証でMatterにログイン"""
    client = MatterClient()
    session_token = client.trigger_qr_login()

    console.print("\n[bold]MatterアプリでこのQRコードをスキャンしてください:[/bold]")
    console.print("[dim]Profile > Settings > Connected Accounts > Obsidian > Scan QR Code[/dim]\n")

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(session_token)
    qr.make(fit=True)
    qr.print_ascii(invert=True)

    console.print("\n[yellow]スキャン待機中...[/yellow]")

    for _ in range(600):
        result = client.exchange_token(session_token)
        if result:
            save_config({
                "access_token": result["access_token"],
                "refresh_token": result["refresh_token"],
            })
            console.print("[green]認証成功！トークンを保存しました。[/green]")
            return
        time.sleep(1)

    console.print("[red]タイムアウト: 10分以内にスキャンされませんでした。[/red]")
    sys.exit(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_cli.py::test_auth_displays_qr_and_saves_token -v`

Expected: 1 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/cli.py tests/test_cli.py
git commit -m "feat: add CLI with auth command"
```

---

### Task 7: CLI - sync command

**Files:**
- Modify: `matter_hub/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for sync command**

Append to `tests/test_cli.py`:

```python
def test_sync_fetches_and_stores_articles(tmp_path):
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
            "my_annotations": [{"text": "highlight", "note": None, "created_date": "2025-01-02", "word_start": 0, "word_end": 5}],
            "my_note": {"note": "a note"},
            "library": {"library_state": 1},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [sample_entry]

    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["sync"])

    assert result.exit_code == 0
    assert "1 件の記事を同期しました" in result.output

    db = Database(db_path)
    articles = db.list_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article"
    tags = db.get_tags("art1")
    assert len(tags) == 1
    highlights = db.get_highlights("art1")
    assert len(highlights) == 1
    db.close()


def test_sync_skips_deleted_articles(tmp_path):
    runner = CliRunner()

    deleted_entry = {
        "id": "art_del",
        "content": {
            "title": "Deleted",
            "url": "https://example.com/del",
            "author": None,
            "publisher": None,
            "publication_date": None,
            "tags": [],
            "my_annotations": [],
            "my_note": None,
            "library": {"library_state": 3},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [deleted_entry]

    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["sync"])

    assert result.exit_code == 0
    db = Database(db_path)
    articles = db.list_articles()
    assert len(articles) == 0
    db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_cli.py::test_sync_fetches_and_stores_articles tests/test_cli.py::test_sync_skips_deleted_articles -v`

Expected: FAIL (sync command not defined)

- [ ] **Step 3: Add sync command to cli.py**

Append to `matter_hub/cli.py`:

```python
@cli.command()
@click.option("--tag", is_flag=True, help="同期後にAI自動タグ付けを実行")
def sync(tag):
    """Matter APIから記事を同期"""
    client = get_client_from_config()

    try:
        entries = client.fetch_all_articles()
    except Exception as e:
        # Try token refresh
        config = load_config()
        if config.get("refresh_token"):
            try:
                client.refresh_token = config["refresh_token"]
                new_tokens = client.refresh_access_token()
                save_config({
                    "access_token": new_tokens["access_token"],
                    "refresh_token": new_tokens["refresh_token"],
                })
                entries = client.fetch_all_articles()
            except Exception:
                console.print("[red]トークンの更新に失敗しました。`matter-hub auth` で再認証してください。[/red]")
                sys.exit(1)
        else:
            raise

    db = get_db()
    count = 0

    for entry in entries:
        parsed = parse_feed_entry(entry)
        article = parsed["article"]

        if article.get("library_state") == 3:
            continue

        db.upsert_article(article)

        db.clear_matter_tags(article["id"])
        for t in parsed["tags"]:
            db.add_tag(article["id"], t["name"], "matter")

        db.clear_highlights(article["id"])
        for h in parsed["highlights"]:
            db.add_highlight(article["id"], h["text"], h.get("note"), h.get("created_date"))

        count += 1

    console.print(f"[green]{count} 件の記事を同期しました[/green]")

    if tag:
        _run_auto_tag(db)

    db.close()


def _run_auto_tag(db: Database):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        console.print("[red]ANTHROPIC_API_KEY が設定されていません。.env ファイルを確認してください。[/red]")
        return

    import anthropic
    from matter_hub.tagger import tag_article

    client = anthropic.Anthropic(api_key=api_key)
    articles = db.articles_without_ai_tags()
    existing_tags = db.get_all_tag_names()

    console.print(f"[yellow]{len(articles)} 件の記事にタグ付け中...[/yellow]")

    for article in articles:
        highlights = db.get_highlights(article["id"])
        tags = tag_article(client, article, highlights, existing_tags)
        for tag_name in tags:
            db.add_tag(article["id"], tag_name, "ai")
            if tag_name not in existing_tags:
                existing_tags.append(tag_name)
        console.print(f"  {article['title'][:40]}... → {', '.join(tags)}")

    console.print(f"[green]タグ付け完了[/green]")
```

- [ ] **Step 4: Add import for get_db_path to cli.py**

Update the import line at the top of `cli.py`:

```python
from matter_hub.config import load_config, save_config, get_db_path
```

Note: This import is already present in the Step 3 code for Task 6. The `get_db` helper also already uses `get_db_path`. Ensure the `get_db_path` function can be patched in tests by importing it as `matter_hub.cli.get_db_path`. Update the `get_db` function:

```python
def get_db() -> Database:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return Database(db_path)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_cli.py -v`

Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/cli.py tests/test_cli.py
git commit -m "feat: add sync command with auto-tag support"
```

---

### Task 8: CLI - search, list, tags, tag, stats commands

**Files:**
- Modify: `matter_hub/cli.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write failing tests for remaining commands**

Append to `tests/test_cli.py`:

```python
def _seed_db(db_path):
    """Helper to create a seeded DB for CLI tests."""
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Machine Learning入門", "url": "https://ml.example.com",
        "author": "Alice", "publisher": "TechBlog",
        "published_date": "2025-01-15", "note": "good article", "library_state": 1,
    })
    db.upsert_article({
        "id": "a2", "title": "料理レシピ集", "url": "https://cook.example.com",
        "author": "Bob", "publisher": "FoodBlog",
        "published_date": "2025-02-10", "note": None, "library_state": 1,
    })
    db.add_tag("a1", "AI", "ai")
    db.add_tag("a1", "機械学習", "ai")
    db.add_tag("a2", "料理", "ai")
    db.add_highlight("a1", "transformers are powerful", "note1", "2025-01-16")
    db.close()
    return db_path


def test_search_keyword(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["search", "Machine"])
    assert result.exit_code == 0
    assert "Machine Learning入門" in result.output
    assert "料理レシピ集" not in result.output


def test_search_by_tag_flag(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["search", "--tag", "AI"])
    assert result.exit_code == 0
    assert "Machine Learning入門" in result.output


def test_list_default(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Machine Learning入門" in result.output
    assert "料理レシピ集" in result.output


def test_list_json_output(tmp_path):
    import json as json_mod
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0
    data = json_mod.loads(result.output)
    assert len(data) == 2


def test_tags_list(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["tags"])
    assert result.exit_code == 0
    assert "AI" in result.output


def test_tag_add(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["tag", "add", "a2", "健康"])
    assert result.exit_code == 0
    db = Database(db_path)
    tags = db.get_tags("a2")
    assert any(t["name"] == "健康" for t in tags)
    db.close()


def test_tag_remove(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["tag", "remove", "a1", "AI"])
    assert result.exit_code == 0
    db = Database(db_path)
    tags = db.get_tags("a1")
    assert not any(t["name"] == "AI" for t in tags)
    db.close()


def test_stats(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["stats"])
    assert result.exit_code == 0
    assert "2" in result.output  # total articles
    assert "Alice" in result.output
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_cli.py::test_search_keyword tests/test_cli.py::test_list_default tests/test_cli.py::test_tags_list tests/test_cli.py::test_stats -v`

Expected: FAIL (commands not defined)

- [ ] **Step 3: Add remaining commands to cli.py**

Append to `matter_hub/cli.py`:

```python
@cli.command()
@click.argument("query", default="")
@click.option("--tag", "tag_filter", default=None, help="タグで絞り込み")
@click.option("--author", default=None, help="著者で絞り込み")
@click.option("--after", default=None, help="指定日以降の記事 (YYYY-MM-DD)")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def search(query, tag_filter, author, after, as_json):
    """記事を検索"""
    db = get_db()

    if tag_filter:
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


@cli.command(name="list")
@click.option("--all", "show_all", is_flag=True, help="全件表示")
@click.option("--json", "as_json", is_flag=True, help="JSON形式で出力")
def list_cmd(show_all, as_json):
    """記事一覧を表示"""
    db = get_db()
    limit = None if show_all else 20
    articles = db.list_articles(limit=limit)

    if as_json:
        import json
        click.echo(json.dumps(articles, ensure_ascii=False, indent=2))
    else:
        _print_articles_table(articles)

    db.close()


@cli.command()
def tags():
    """タグ一覧を表示（記事数付き）"""
    db = get_db()
    tag_list = db.list_tags()

    table = Table(title="タグ一覧")
    table.add_column("タグ", style="cyan")
    table.add_column("記事数", justify="right", style="green")

    for name, count in tag_list:
        table.add_row(name, str(count))

    console.print(table)
    db.close()


@cli.group()
def tag():
    """タグの追加・削除"""
    pass


@tag.command(name="add")
@click.argument("article_id")
@click.argument("tag_name")
def tag_add(article_id, tag_name):
    """記事にタグを追加"""
    db = get_db()
    db.add_tag(article_id, tag_name, "manual")
    console.print(f"[green]タグ '{tag_name}' を追加しました[/green]")
    db.close()


@tag.command(name="remove")
@click.argument("article_id")
@click.argument("tag_name")
def tag_remove(article_id, tag_name):
    """記事からタグを削除"""
    db = get_db()
    db.remove_tag(article_id, tag_name)
    console.print(f"[yellow]タグ '{tag_name}' を削除しました[/yellow]")
    db.close()


@cli.command()
def stats():
    """興味の傾向を分析"""
    db = get_db()
    s = db.get_stats()

    console.print(f"\n[bold]記事数:[/bold] {s['total_articles']}")
    console.print(f"[bold]タグ数:[/bold] {s['total_tags']}")

    if s["top_authors"]:
        console.print("\n[bold]著者別（上位10件）:[/bold]")
        table = Table()
        table.add_column("著者", style="cyan")
        table.add_column("記事数", justify="right", style="green")
        for author, count in s["top_authors"]:
            table.add_row(author, str(count))
        console.print(table)

    if s["monthly"]:
        console.print("\n[bold]月別保存数:[/bold]")
        table = Table()
        table.add_column("月", style="cyan")
        table.add_column("記事数", justify="right", style="green")
        for month, count in s["monthly"]:
            table.add_row(month, str(count))
        console.print(table)

    db.close()


def _print_articles_table(articles: list[dict]):
    if not articles:
        console.print("[yellow]記事が見つかりませんでした[/yellow]")
        return

    table = Table()
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("タイトル", style="cyan", max_width=50)
    table.add_column("著者", style="green", max_width=20)
    table.add_column("日付", style="yellow", max_width=12)

    for a in articles:
        table.add_row(
            a["id"][:8],
            a["title"][:50],
            a.get("author") or "-",
            a.get("published_date") or "-",
        )

    console.print(table)
```

- [ ] **Step 4: Run all tests to verify they pass**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest tests/test_cli.py -v`

Expected: 11 passed

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add matter_hub/cli.py tests/test_cli.py
git commit -m "feat: add search, list, tags, tag, stats CLI commands"
```

---

### Task 9: Final integration test and README

**Files:**
- Modify: `tests/test_cli.py`
- Create: `README.md`

- [ ] **Step 1: Write integration test**

Append to `tests/test_cli.py`:

```python
def test_full_workflow(tmp_path):
    """Integration test: sync → search → tag → stats"""
    runner = CliRunner()

    sample_entry = {
        "id": "int1",
        "content": {
            "title": "LLM入門ガイド",
            "url": "https://example.com/llm",
            "author": {"any_name": "太郎"},
            "publisher": {"any_name": "AI Weekly"},
            "publication_date": "2025-03-01",
            "tags": [{"name": "AI", "created_date": "2025-03-01"}],
            "my_annotations": [],
            "my_note": {"note": "great intro"},
            "library": {"library_state": 1},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [sample_entry]
    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path):
        # Sync
        result = runner.invoke(cli, ["sync"])
        assert result.exit_code == 0

        # Search
        result = runner.invoke(cli, ["search", "LLM"])
        assert "LLM入門ガイド" in result.output

        # Tag add
        result = runner.invoke(cli, ["tag", "add", "int1", "機械学習"])
        assert result.exit_code == 0

        # Tags list
        result = runner.invoke(cli, ["tags"])
        assert "AI" in result.output
        assert "機械学習" in result.output

        # Stats
        result = runner.invoke(cli, ["stats"])
        assert "太郎" in result.output
```

- [ ] **Step 2: Run full test suite**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest -v`

Expected: All tests pass

- [ ] **Step 3: Create README.md**

```markdown
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

# AI自動タグ付け付きで同期（要 ANTHROPIC_API_KEY��
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
```

- [ ] **Step 4: Run full test suite one final time**

Run: `cd /Users/nakamurakohki/workspace/private_dev/matter-hub && uv run pytest -v`

Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
cd /Users/nakamurakohki/workspace/private_dev/matter-hub
git add tests/test_cli.py README.md
git commit -m "feat: add integration test and README"
```
