from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from matter_hub.config import get_db_path
from matter_hub.db import Database

router = APIRouter()


def _db() -> Database:
    return Database(get_db_path())


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    db = _db()
    try:
        tags = db.list_tags_filtered(view="active")
        rows, total = db.list_articles_filtered(q=None, tags=[], view="active", limit=50, offset=0)
    finally:
        db.close()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "articles": rows,
            "total": total,
            "tags_with_counts": tags,
            "view": "active",
            "q": "",
            "selected_tags": [],
            "page": 1,
            "has_more": total > 50,
        },
    )
