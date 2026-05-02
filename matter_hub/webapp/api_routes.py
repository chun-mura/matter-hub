"""JSON API for the React frontend."""

from __future__ import annotations

import os

from fastapi import APIRouter, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from matter_hub.importer import x_summarize_button_disabled_without_bearer
from matter_hub.webapp.helpers import (
    PAGE_SIZE,
    annotate_x_summarize_lock,
    article_summary_row,
    parse_tags,
    web_db,
)
from matter_hub.webapp.summarize_runner import runner as summarize_runner
from matter_hub.webapp.sync_runner import runner as sync_runner

router = APIRouter(prefix="/api", tags=["api"])


class SummaryBody(BaseModel):
    summary: str


def _cors_origins() -> list[str]:
    raw = os.environ.get(
        "MATTER_HUB_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [o.strip() for o in raw.split(",") if o.strip()]


# Vite の dev / preview でよく使うポート。LAN・Tailscale の IP/ホストで開いても CORS 通るよう既定で許可する。
_DEFAULT_DEV_CORS_ORIGIN_REGEX = (
    r"^https?://(localhost|127\.0\.0\.1|\d{1,3}(\.\d{1,3}){3}|[\w.-]+):(5173|4173)$"
)


def _cors_origin_regex() -> str | None:
    """
    ``Origin`` ヘッダにマッチしたら CORS 許可（応答には実際の Origin が echo される）。

    - **既定（開発向け）:** 上記の広めの正規表現を使い、``http://100.x.x.x:5173`` のような
      Vite も許可する。本番で絞るときは ``MATTER_HUB_CORS_STRICT=1`` にし、
      ``MATTER_HUB_CORS_ORIGINS`` / ``MATTER_HUB_CORS_ORIGIN_REGEX`` のみを使う。
    - ``MATTER_HUB_CORS_ORIGIN_REGEX`` が設定されていれば（strict でない限り）それを優先。
    """
    strict = os.environ.get("MATTER_HUB_CORS_STRICT", "").strip().lower() in ("1", "true", "yes")
    env_re = os.environ.get("MATTER_HUB_CORS_ORIGIN_REGEX", "").strip()
    if strict:
        return env_re or None
    if env_re:
        return env_re
    return _DEFAULT_DEV_CORS_ORIGIN_REGEX


def _json(data: object) -> JSONResponse:
    return JSONResponse(content=jsonable_encoder(data))


def _summary_panel(article: dict, error: str | None, summary_open: bool) -> dict:
    a = dict(article)
    a["x_summarize_disabled"] = x_summarize_button_disabled_without_bearer(a)
    return {
        "article": a,
        "error": error,
        "summary_open": summary_open,
    }


@router.get("/bootstrap")
def api_bootstrap(
    q: str = "",
    tags: str = "",
    view: str = "active",
) -> JSONResponse:
    tag_list = parse_tags(tags)
    db = web_db()
    try:
        tag_pairs = db.list_tags_filtered(view=view)
        rows, total = db.list_articles_filtered(
            q=q or None, tags=tag_list, view=view, limit=PAGE_SIZE, offset=0
        )
    finally:
        db.close()
    annotate_x_summarize_lock(rows)
    tags_json = [{"name": n, "count": c} for n, c in tag_pairs]
    return _json(
        {
            "articles": rows,
            "total": total,
            "page": 1,
            "has_more": total > PAGE_SIZE,
            "tags": tags_json,
            "selected_tags": tag_list,
            "view": view,
            "q": q,
            "sync": sync_runner.snapshot(),
        }
    )


@router.get("/articles")
def api_articles(
    q: str = "",
    tags: str = "",
    view: str = "active",
    page: int = Query(1, ge=1),
) -> JSONResponse:
    tag_list = parse_tags(tags)
    offset = (page - 1) * PAGE_SIZE
    db = web_db()
    try:
        rows, total = db.list_articles_filtered(
            q=q or None, tags=tag_list, view=view, limit=PAGE_SIZE, offset=offset
        )
    finally:
        db.close()
    annotate_x_summarize_lock(rows)
    return _json(
        {
            "articles": rows,
            "total": total,
            "view": view,
            "q": q,
            "selected_tags": tag_list,
            "page": page,
            "has_more": offset + len(rows) < total,
        }
    )


@router.get("/tags")
def api_tags(
    view: str = "active",
    tags: str = "",
) -> JSONResponse:
    selected = parse_tags(tags)
    db = web_db()
    try:
        pairs = db.list_tags_filtered(view=view)
    finally:
        db.close()
    tags_json = [{"name": n, "count": c} for n, c in pairs]
    return _json(
        {
            "tags": tags_json,
            "selected_tags": selected,
            "view": view,
        }
    )


@router.get("/sync")
def api_sync_get() -> JSONResponse:
    return _json(sync_runner.snapshot())


@router.post("/sync")
def api_sync_post() -> JSONResponse:
    sync_runner.start(tag=True, embed=True, translate_titles=True, retranslate_all=False)
    return _json(sync_runner.snapshot())


@router.post("/articles/{article_id}/delete")
def api_delete_article(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        ok = db.set_deleted(article_id, True)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return _json({"ok": True})


@router.post("/articles/{article_id}/restore")
def api_restore_article(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        ok = db.set_deleted(article_id, False)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return _json({"ok": True})


@router.post("/articles/{article_id}/archive")
def api_archive_article(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        ok = db.set_library_state(article_id, 2)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return _json({"ok": True})


@router.post("/articles/{article_id}/unarchive")
def api_unarchive_article(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        ok = db.set_library_state(article_id, 1)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return _json({"ok": True})


@router.get("/articles/{article_id}/summary")
def api_article_summary(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        row = article_summary_row(db, article_id)
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404)
    return _json(_summary_panel(row, error=None, summary_open=True))


@router.post("/articles/{article_id}/summary/close")
def api_close_article_summary(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        row = article_summary_row(db, article_id)
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=404)
    return _json(_summary_panel(row, error=None, summary_open=False))


@router.put("/articles/{article_id}/summary")
def api_update_summary_manual(article_id: str, body: SummaryBody) -> JSONResponse:
    db = web_db()
    try:
        row_check = db.conn.execute("SELECT id FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row_check:
            raise HTTPException(status_code=404)
        db.update_article_summary(article_id, body.summary.strip(), "manual")
        row = article_summary_row(db, article_id)
    finally:
        db.close()
    if not row:
        raise HTTPException(status_code=500)
    return _json(_summary_panel(row, error=None, summary_open=True))


@router.delete("/articles/{article_id}/summary")
def api_delete_summary(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        ok = db.clear_article_summary(article_id)
    finally:
        db.close()
    if not ok:
        raise HTTPException(status_code=404)
    return _json({"ok": True})


@router.post("/articles/{article_id}/summarize")
def api_summarize_article(article_id: str) -> JSONResponse:
    db = web_db()
    try:
        row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404)
        article = dict(row)
    finally:
        db.close()

    if x_summarize_button_disabled_without_bearer(article):
        return _json(
            {
                "outcome": "config_error",
                "panel": _summary_panel(
                    article,
                    error=(
                        "環境変数が未登録のため要約生成は使用できません"
                        "（X_BEARER_TOKEN または TWITTER_BEARER_TOKEN を設定してください）"
                    ),
                    summary_open=False,
                ),
            }
        )

    outcome = summarize_runner.start(article_id)
    if outcome == "busy":
        return _json(
            {
                "outcome": "busy",
                "panel": _summary_panel(
                    article,
                    error="別の記事の要約が実行中です。完了してから再度お試しください。",
                    summary_open=False,
                ),
            }
        )

    snap = summarize_runner.snapshot_for(article_id)
    if not snap:
        return _json(
            {
                "outcome": "start_failed",
                "panel": _summary_panel(article, error="要約の開始に失敗しました", summary_open=False),
            }
        )

    return _json(
        {
            "outcome": "started",
            "article": article,
            "job": snap,
        }
    )


def _summarize_status_payload(article_id: str) -> dict:
    snap = summarize_runner.snapshot_for(article_id)
    if snap is None:
        return {"job": None, "summary_panel": None}

    if snap["status"] == "running":
        return {"job": snap, "summary_panel": None}

    art = snap["article"] if snap["article"] is not None else None
    if not art or not art.get("id"):
        db = web_db()
        try:
            row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
            art = dict(row) if row else {"id": article_id}
        finally:
            db.close()

    panel = _summary_panel(
        art,
        error=snap["error"] if snap["status"] == "error" else None,
        summary_open=(snap["status"] == "ok"),
    )
    return {"job": snap, "summary_panel": panel}


@router.get("/articles/{article_id}/summarize/status")
def api_summarize_article_status(article_id: str) -> JSONResponse:
    return _json(_summarize_status_payload(article_id))
