"""SQLite database for storing and querying Matter articles."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


class Database:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self._migrate_fts_trigram()
        self._init_tables()

    def _migrate_fts_trigram(self):
        """既存のFTSテーブルがtrigram以外なら再作成する。"""
        cur = self.conn.cursor()
        row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='articles_fts'"
        ).fetchone()
        if row and "trigram" not in row[0]:
            cur.executescript("""
                DROP TRIGGER IF EXISTS articles_ai;
                DROP TRIGGER IF EXISTS articles_ad;
                DROP TRIGGER IF EXISTS articles_au;
                DROP TABLE IF EXISTS articles_fts;
            """)
            self.conn.commit()
            self._needs_fts_rebuild = True
        else:
            self._needs_fts_rebuild = False

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
                content='articles', content_rowid='rowid',
                tokenize='trigram'
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
        cur.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                article_id TEXT PRIMARY KEY REFERENCES articles(id),
                embedding BLOB NOT NULL
            )
        """)
        self.conn.commit()

        if self._needs_fts_rebuild:
            self.conn.execute("""
                INSERT INTO articles_fts(rowid, title, author, publisher, note)
                SELECT rowid, title, author, publisher, note FROM articles
            """)
            self.conn.commit()
            self._needs_fts_rebuild = False

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

    def delete_article(self, article_id: str) -> bool:
        """記事と関連データ（タグ、ハイライト、embedding）を削除。削除した場合Trueを返す。"""
        row = self.conn.execute("SELECT id FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row:
            return False
        self.conn.execute("DELETE FROM tags WHERE article_id = ?", (article_id,))
        self.conn.execute("DELETE FROM highlights WHERE article_id = ?", (article_id,))
        self.conn.execute("DELETE FROM embeddings WHERE article_id = ?", (article_id,))
        self.conn.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        self.conn.commit()
        return True

    def clear_highlights(self, article_id: str) -> None:
        self.conn.execute("DELETE FROM highlights WHERE article_id = ?", (article_id,))
        self.conn.commit()

    def clear_matter_tags(self, article_id: str) -> None:
        self.conn.execute("DELETE FROM tags WHERE article_id = ? AND source = 'matter'", (article_id,))
        self.conn.commit()

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

    def close(self):
        self.conn.close()
