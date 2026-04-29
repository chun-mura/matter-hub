"""Shared helpers for the Matter Hub webapp (HTML or JSON)."""

from matter_hub.config import get_db_path
from matter_hub.db import Database
from matter_hub.importer import x_summarize_button_disabled_without_bearer

PAGE_SIZE = 50


def web_db() -> Database:
    return Database(get_db_path())


def parse_tags(tags: str) -> list[str]:
    return [t for t in (tags or "").split(",") if t.strip()]


def annotate_x_summarize_lock(articles: list[dict]) -> None:
    for row in articles:
        row["x_summarize_disabled"] = x_summarize_button_disabled_without_bearer(row)


def article_summary_row(db: Database, article_id: str) -> dict | None:
    row = db.conn.execute(
        """SELECT id, source, url, title, note,
                  summary, summary_model, summary_created_at, summary_source_url
           FROM articles WHERE id = ?""",
        (article_id,),
    ).fetchone()
    return dict(row) if row else None
