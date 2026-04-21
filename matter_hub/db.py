"""SQLite database for storing and querying Matter articles."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

# Matter library_state: 0 = library, 1 = queue, 2 = archived, 3 = deleted (sync hard-removes).
# "archived" means only explicitly archived (state=2); NULL/0/1 are treated as active.
# Articles tagged "トレンド" are scoped to the trend view only and hidden from active/archived.
_TREND_TAG = "トレンド"
_HAS_TREND_TAG = (
    f"EXISTS (SELECT 1 FROM tags tt WHERE tt.article_id = a.id AND tt.name = '{_TREND_TAG}')"
)
_VIEW_CLAUSES = {
    "active":   f"a.deleted = 0 AND (a.library_state IS NULL OR a.library_state != 2) AND NOT {_HAS_TREND_TAG}",
    "archived": f"a.deleted = 0 AND a.library_state = 2 AND NOT {_HAS_TREND_TAG}",
    "trend":    f"a.deleted = 0 AND {_HAS_TREND_TAG}",
    "trash":    "a.deleted = 1",
}


def _view_clause(view: str) -> str:
    return _VIEW_CLAUSES.get(view, _VIEW_CLAUSES["active"])


class Database:
    def __init__(self, db_path: Path):
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._migrate()
        self._init_tables()

    def _migrate(self):
        """スキーマのマイグレーション。"""
        cur = self.conn.cursor()

        # FTS: trigram 未対応、または title_ja 列未対応なら再作成
        row = cur.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='articles_fts'"
        ).fetchone()
        fts_sql = row[0] if row and row[0] else ""
        fts_outdated = bool(fts_sql) and (
            "trigram" not in fts_sql or "title_ja" not in fts_sql
        )
        if fts_outdated:
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

        # articlesテーブルにsourceカラムを追加（テーブルが既に存在する場合のみ）
        table_exists = cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='articles'"
        ).fetchone()
        if table_exists:
            columns = [r[1] for r in cur.execute("PRAGMA table_info(articles)").fetchall()]
            if "source" not in columns:
                cur.execute("ALTER TABLE articles ADD COLUMN source TEXT DEFAULT 'matter'")
                self.conn.commit()
            if "deleted" not in columns:
                cur.execute("ALTER TABLE articles ADD COLUMN deleted INTEGER DEFAULT 0")
                self.conn.commit()
            if "title_ja" not in columns:
                cur.execute("ALTER TABLE articles ADD COLUMN title_ja TEXT")
                self.conn.commit()
            if "title_ja_from" not in columns:
                cur.execute("ALTER TABLE articles ADD COLUMN title_ja_from TEXT")
                self.conn.commit()
            if "created_at" not in columns:
                cur.execute("ALTER TABLE articles ADD COLUMN created_at TEXT")
                cur.execute(
                    "UPDATE articles SET created_at = COALESCE(synced_at, ?) WHERE created_at IS NULL",
                    (datetime.now(timezone.utc).isoformat(),),
                )
                self.conn.commit()
            if "queue_order" not in columns:
                cur.execute("ALTER TABLE articles ADD COLUMN queue_order INTEGER")
                self.conn.commit()

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
                queue_order INTEGER,
                source TEXT DEFAULT 'matter',
                deleted INTEGER DEFAULT 0,
                title_ja TEXT,
                title_ja_from TEXT,
                created_at TEXT,
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
                title, title_ja, author, publisher, note,
                content='articles', content_rowid='rowid',
                tokenize='trigram'
            );

            CREATE TRIGGER IF NOT EXISTS articles_ai AFTER INSERT ON articles BEGIN
                INSERT INTO articles_fts(rowid, title, title_ja, author, publisher, note)
                VALUES (new.rowid, new.title, new.title_ja, new.author, new.publisher, new.note);
            END;

            CREATE TRIGGER IF NOT EXISTS articles_ad AFTER DELETE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, title_ja, author, publisher, note)
                VALUES ('delete', old.rowid, old.title, old.title_ja, old.author, old.publisher, old.note);
            END;

            CREATE TRIGGER IF NOT EXISTS articles_au AFTER UPDATE ON articles BEGIN
                INSERT INTO articles_fts(articles_fts, rowid, title, title_ja, author, publisher, note)
                VALUES ('delete', old.rowid, old.title, old.title_ja, old.author, old.publisher, old.note);
                INSERT INTO articles_fts(rowid, title, title_ja, author, publisher, note)
                VALUES (new.rowid, new.title, new.title_ja, new.author, new.publisher, new.note);
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
                INSERT INTO articles_fts(rowid, title, title_ja, author, publisher, note)
                SELECT rowid, title, title_ja, author, publisher, note FROM articles
            """)
            self.conn.commit()
            self._needs_fts_rebuild = False

    def upsert_article(self, article: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        source = article.get("source", "matter")
        aid = article["id"]
        existing = self.conn.execute(
            "SELECT title, title_ja, title_ja_from, created_at FROM articles WHERE id = ?",
            (aid,),
        ).fetchone()

        merged = {**article, "source": source, "synced_at": now, "created_at": now}
        merged.setdefault("title_ja", None)
        merged.setdefault("title_ja_from", None)
        merged.setdefault("queue_order", None)

        if existing:
            merged["created_at"] = existing["created_at"] or now
            if existing["title"] != article["title"]:
                merged["title_ja"] = None
                merged["title_ja_from"] = None
            else:
                if "title_ja" not in article:
                    merged["title_ja"] = existing["title_ja"]
                if "title_ja_from" not in article:
                    merged["title_ja_from"] = existing["title_ja_from"]

        self.conn.execute(
            """INSERT INTO articles (
                   id, title, url, author, publisher, published_date, note, library_state, queue_order,
                   source, created_at, synced_at, title_ja, title_ja_from
               )
               VALUES (
                   :id, :title, :url, :author, :publisher, :published_date, :note, :library_state, :queue_order,
                   :source, :created_at, :synced_at, :title_ja, :title_ja_from
               )
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title, url=excluded.url, author=excluded.author,
                 publisher=excluded.publisher, published_date=excluded.published_date,
                 note=excluded.note, library_state=excluded.library_state,
                 queue_order=excluded.queue_order,
                 source=excluded.source, synced_at=excluded.synced_at,
                 title_ja=excluded.title_ja, title_ja_from=excluded.title_ja_from""",
            merged,
        )
        self.conn.commit()

    def update_title_translation(self, article_id: str, title_ja: str, title_ja_from: str) -> bool:
        cur = self.conn.execute(
            "UPDATE articles SET title_ja = ?, title_ja_from = ? WHERE id = ?",
            (title_ja, title_ja_from, article_id),
        )
        self.conn.commit()
        return cur.rowcount > 0

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

    def search(self, query: str, source: str | None = None) -> list[dict]:
        if not query.strip():
            return self.list_articles(source=source)
        if source:
            rows = self.conn.execute(
                """SELECT a.* FROM articles a
                   JOIN articles_fts f ON a.rowid = f.rowid
                   WHERE articles_fts MATCH ? AND a.source = ?
                   ORDER BY rank""",
                (query, source),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT a.* FROM articles a
                   JOIN articles_fts f ON a.rowid = f.rowid
                   WHERE articles_fts MATCH ?
                   ORDER BY rank""",
                (query,),
            ).fetchall()
        return [dict(r) for r in rows]

    def search_by_tag(self, tag_name: str, source: str | None = None) -> list[dict]:
        if source:
            rows = self.conn.execute(
                """SELECT a.* FROM articles a
                   JOIN tags t ON a.id = t.article_id
                   WHERE t.name = ? AND a.source = ?
                   ORDER BY a.queue_order DESC, a.created_at DESC, a.synced_at DESC""",
                (tag_name, source),
            ).fetchall()
        else:
            rows = self.conn.execute(
                """SELECT a.* FROM articles a
                   JOIN tags t ON a.id = t.article_id
                   WHERE t.name = ?
                   ORDER BY a.queue_order DESC, a.created_at DESC, a.synced_at DESC""",
                (tag_name,),
            ).fetchall()
        return [dict(r) for r in rows]

    def list_articles(self, limit: int | None = None, source: str | None = None) -> list[dict]:
        params = []
        sql = "SELECT * FROM articles"
        if source:
            sql += " WHERE source = ?"
            params.append(source)
        sql += " ORDER BY queue_order DESC, created_at DESC, synced_at DESC"
        if limit:
            sql += f" LIMIT {limit}"
        rows = self.conn.execute(sql, params).fetchall()
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

    def set_deleted(self, article_id: str, flag: bool) -> bool:
        row = self.conn.execute(
            "SELECT id FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        if not row:
            return False
        self.conn.execute(
            "UPDATE articles SET deleted = ? WHERE id = ?",
            (1 if flag else 0, article_id),
        )
        self.conn.commit()
        return True

    def set_library_state(self, article_id: str, state: int) -> bool:
        row = self.conn.execute(
            "SELECT id FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        if not row:
            return False
        self.conn.execute(
            "UPDATE articles SET library_state = ? WHERE id = ?",
            (state, article_id),
        )
        self.conn.commit()
        return True

    def list_articles_filtered(
        self,
        q: str | None,
        tags: list[str],
        view: str,
        limit: int,
        offset: int,
    ) -> tuple[list[dict], int]:
        view_sql = _view_clause(view)

        joins: list[str] = []
        where = [view_sql]
        params: list = []

        # Order matters: SQLite binds placeholders positionally as they appear
        # in the assembled SQL. Tag JOIN placeholders come first, then the FTS
        # MATCH placeholder in WHERE, then LIMIT/OFFSET appended at the bottom.
        group_having = ""
        if tags:
            placeholders = ",".join(["?"] * len(tags))
            joins.append(f"JOIN tags t ON a.id = t.article_id AND t.name IN ({placeholders})")
            params.extend(tags)
            group_having = f" GROUP BY a.id HAVING COUNT(DISTINCT t.name) = {len(tags)}"

        if q and q.strip():
            joins.append("JOIN articles_fts f ON a.rowid = f.rowid")
            where.append("articles_fts MATCH ?")
            params.append(q)

        join_sql = " ".join(joins)
        where_sql = " AND ".join(where)

        count_sql = (
            f"SELECT COUNT(*) FROM (SELECT a.id FROM articles a {join_sql} "
            f"WHERE {where_sql}{group_having})"
        )
        try:
            total = self.conn.execute(count_sql, params).fetchone()[0]
        except sqlite3.OperationalError:
            return self.list_articles_filtered(q=None, tags=tags, view=view, limit=limit, offset=offset)

        list_sql = (
            f"SELECT a.* FROM articles a {join_sql} "
            f"WHERE {where_sql}{group_having} "
            f"ORDER BY a.queue_order DESC, a.created_at DESC, a.synced_at DESC LIMIT ? OFFSET ?"
        )
        rows = self.conn.execute(list_sql, [*params, limit, offset]).fetchall()
        return [dict(r) for r in rows], total

    def list_tags_filtered(self, view: str) -> list[tuple[str, int]]:
        view_sql = _view_clause(view)
        rows = self.conn.execute(
            f"SELECT t.name, COUNT(DISTINCT a.id) AS cnt "
            f"FROM tags t JOIN articles a ON a.id = t.article_id "
            f"WHERE {view_sql} "
            f"GROUP BY t.name ORDER BY cnt DESC, t.name ASC"
        ).fetchall()
        return [(r["name"], r["cnt"]) for r in rows]

    def is_deleted(self, article_id: str) -> bool:
        row = self.conn.execute(
            "SELECT deleted FROM articles WHERE id = ?", (article_id,)
        ).fetchone()
        return bool(row and row["deleted"])

    def close(self):
        self.conn.close()
