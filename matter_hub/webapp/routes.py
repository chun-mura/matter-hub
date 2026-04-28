from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse

from matter_hub.config import get_db_path
from matter_hub.db import Database
from matter_hub.importer import x_summarize_button_disabled_without_bearer
from matter_hub.webapp.summarize_runner import runner as summarize_runner
from matter_hub.webapp.sync_runner import runner as sync_runner

router = APIRouter()

PAGE_SIZE = 50


def _db() -> Database:
    return Database(get_db_path())


def _parse_tags(tags: str) -> list[str]:
    return [t for t in (tags or "").split(",") if t.strip()]


def _render_summary_panel(request: Request, article: dict, error: str | None, summary_open: bool) -> HTMLResponse:
    templates = request.app.state.templates
    a = dict(article)
    a["x_summarize_disabled"] = x_summarize_button_disabled_without_bearer(a)
    return templates.TemplateResponse(
        request,
        "_article_summary_panel.html",
        {
            "a": a,
            "error": error,
            "summary_open": summary_open,
        },
    )


def _annotate_x_summarize_lock(articles: list[dict]) -> None:
    for row in articles:
        row["x_summarize_disabled"] = x_summarize_button_disabled_without_bearer(row)


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    q: str = "",
    tags: str = "",
    view: str = "active",
) -> HTMLResponse:
    tag_list = _parse_tags(tags)
    db = _db()
    try:
        tag_pairs = db.list_tags_filtered(view=view)
        rows, total = db.list_articles_filtered(
            q=q or None, tags=tag_list, view=view, limit=PAGE_SIZE, offset=0
        )
    finally:
        db.close()
    _annotate_x_summarize_lock(rows)
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "articles": rows,
            "total": total,
            "tags_with_counts": tag_pairs,
            "view": view,
            "q": q,
            "selected_tags": tag_list,
            "page": 1,
            "has_more": total > PAGE_SIZE,
            "sync": sync_runner.snapshot(),
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
    _annotate_x_summarize_lock(rows)
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


@router.get("/tags", response_class=HTMLResponse)
def tags_partial(
    request: Request,
    view: str = "active",
    tags: str = "",
) -> HTMLResponse:
    selected = _parse_tags(tags)
    db = _db()
    try:
        pairs = db.list_tags_filtered(view=view)
    finally:
        db.close()
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "_tag_filter.html",
        {
            "tags_with_counts": pairs,
            "selected_tags": selected,
            "view": view,
        },
    )


@router.post("/articles/{article_id}/delete")
def delete_article(article_id: str) -> HTMLResponse:
    db = _db()
    try:
        ok = db.set_deleted(article_id, True)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return HTMLResponse(content="", status_code=200)


@router.post("/articles/{article_id}/restore")
def restore_article(article_id: str) -> HTMLResponse:
    db = _db()
    try:
        ok = db.set_deleted(article_id, False)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return HTMLResponse(content="", status_code=200)


@router.post("/articles/{article_id}/archive")
def archive_article(article_id: str) -> HTMLResponse:
    db = _db()
    try:
        ok = db.set_library_state(article_id, 2)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return HTMLResponse(content="", status_code=200)


@router.post("/articles/{article_id}/unarchive")
def unarchive_article(article_id: str) -> HTMLResponse:
    db = _db()
    try:
        ok = db.set_library_state(article_id, 1)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return HTMLResponse(content="", status_code=200)


@router.get("/articles/{article_id}/summary", response_class=HTMLResponse)
def article_summary(request: Request, article_id: str) -> HTMLResponse:
    db = _db()
    try:
        row = db.conn.execute(
            """SELECT id, source, url, title, note,
                      summary, summary_model, summary_created_at, summary_source_url
               FROM articles WHERE id = ?""",
            (article_id,),
        ).fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404)
    return _render_summary_panel(request, dict(row), error=None, summary_open=True)


@router.post("/articles/{article_id}/summary/close", response_class=HTMLResponse)
def close_article_summary(request: Request, article_id: str) -> HTMLResponse:
    db = _db()
    try:
        row = db.conn.execute(
            """SELECT id, source, url, title, note,
                      summary, summary_model, summary_created_at, summary_source_url
               FROM articles WHERE id = ?""",
            (article_id,),
        ).fetchone()
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404)
    return _render_summary_panel(request, dict(row), error=None, summary_open=False)


@router.post("/articles/{article_id}/summarize", response_class=HTMLResponse)
def summarize_article(request: Request, article_id: str) -> HTMLResponse:
    db = _db()
    try:
        row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404)
        article = dict(row)
    finally:
        db.close()

    if x_summarize_button_disabled_without_bearer(article):
        return _render_summary_panel(
            request,
            article,
            error="環境変数が未登録のため要約生成は使用できません（X_BEARER_TOKEN または TWITTER_BEARER_TOKEN を設定してください）",
            summary_open=False,
        )

    outcome = summarize_runner.start(article_id)
    if outcome == "busy":
        return _render_summary_panel(
            request,
            article,
            error="別の記事の要約が実行中です。完了してから再度お試しください。",
            summary_open=False,
        )

    snap = summarize_runner.snapshot_for(article_id)
    if not snap:
        return _render_summary_panel(
            request,
            article,
            error="要約の開始に失敗しました",
            summary_open=False,
        )

    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "_article_summary_progress.html",
        {"a": article, "job": snap},
    )


@router.get("/articles/{article_id}/summarize/status", response_class=HTMLResponse)
def summarize_article_status(request: Request, article_id: str) -> HTMLResponse:
    snap = summarize_runner.snapshot_for(article_id)
    if snap is None:
        return HTMLResponse(f'<div id="summarize-progress-{article_id}"></div>')

    templates = request.app.state.templates
    if snap["status"] == "running":
        art = snap["article"] if snap["article"] is not None else {"id": article_id}
        return templates.TemplateResponse(
            request,
            "_article_summary_progress.html",
            {"a": art, "job": snap},
        )

    art = snap["article"] if snap["article"] is not None else None
    if not art or not art.get("id"):
        db = _db()
        try:
            row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            art = dict(row) if row else {"id": article_id}
        finally:
            db.close()

    return _render_summary_panel(
        request,
        art,
        error=snap["error"] if snap["status"] == "error" else None,
        summary_open=(snap["status"] == "ok"),
    )


def _sync_response(request: Request) -> HTMLResponse:
    templates = request.app.state.templates
    return templates.TemplateResponse(
        request,
        "_sync_status.html",
        {"sync": sync_runner.snapshot()},
    )


@router.get("/sync", response_class=HTMLResponse)
def sync_status(request: Request) -> HTMLResponse:
    return _sync_response(request)


@router.post("/sync", response_class=HTMLResponse)
def sync_start(request: Request) -> HTMLResponse:
    sync_runner.start(tag=True, embed=True, translate_titles=True, retranslate_all=False)
    return _sync_response(request)
