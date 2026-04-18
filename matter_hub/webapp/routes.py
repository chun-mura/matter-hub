from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from matter_hub.config import get_db_path
from matter_hub.db import Database

router = APIRouter()

PAGE_SIZE = 50


def _db() -> Database:
    return Database(get_db_path())


def _parse_tags(tags: str) -> list[str]:
    return [t for t in (tags or "").split(",") if t.strip()]


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


@router.get("/articles", response_class=HTMLResponse)
def articles(
    request: Request,
    q: str = "",
    tags: str = "",
    view: str = "active",
    page: int = Query(1, ge=1),
) -> HTMLResponse:
    tag_list = _parse_tags(tags)
    offset = (page - 1) * PAGE_SIZE
    db = _db()
    try:
        rows, total = db.list_articles_filtered(
            q=q or None, tags=tag_list, view=view, limit=PAGE_SIZE, offset=offset
        )
    finally:
        db.close()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "_article_list.html",
        {
            "articles": rows,
            "total": total,
            "view": view,
            "q": q,
            "selected_tags": tag_list,
            "page": page,
            "has_more": offset + len(rows) < total,
        },
    )
