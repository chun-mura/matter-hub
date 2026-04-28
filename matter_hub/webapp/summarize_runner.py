"""Background article summarization with live log lines for the webapp."""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Literal

from matter_hub.config import get_db_path
from matter_hub.db import Database
from matter_hub.importer import (
    fetch_article_content_text,
    x_summarize_button_disabled_without_bearer,
)
from matter_hub.ollama import summarize_article_ollama
from matter_hub.sync import ensure_ollama_noninteractive

Status = Literal["idle", "running", "ok", "error"]

_LOG_MAX = 100


def _format_log_line(msg: str, level: str = "info") -> str:
    ts = datetime.now().strftime("%H:%M:%S")
    tag = f"[{level.upper()}] " if level in {"warn", "error"} else ""
    return f"[{ts}] {tag}{msg}"


class SummarizeRunner:
    """At most one summarization job at a time (matches single-user webapp usage)."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._article_id: str | None = None
        self._article: dict | None = None
        self._status: Status = "idle"
        self._log: deque[str] = deque(maxlen=_LOG_MAX)
        self._started_at: datetime | None = None
        self._finished_at: datetime | None = None
        self._error: str | None = None

    def snapshot_for(self, article_id: str) -> dict | None:
        """Return job state for this article, or None if this article has no active/recent job."""
        with self._lock:
            if self._article_id != article_id:
                return None
            return {
                "status": self._status,
                "log": list(self._log),
                "started_at": self._started_at.isoformat() if self._started_at else None,
                "finished_at": self._finished_at.isoformat() if self._finished_at else None,
                "article": dict(self._article) if self._article else None,
                "error": self._error,
            }

    def start(self, article_id: str) -> Literal["started", "busy", "same"]:
        """
        Start summarization in a background thread.
        Returns ``same`` if this article is already being summarized (re-show progress UI).
        """
        with self._lock:
            if self._status == "running":
                if self._article_id == article_id:
                    return "same"
                return "busy"
            self._status = "running"
            self._article_id = article_id
            self._article = None
            self._log.clear()
            self._started_at = datetime.now()
            self._finished_at = None
            self._error = None

        def _append(msg: str, level: str = "info") -> None:
            line = _format_log_line(msg, level)
            with self._lock:
                self._log.append(line)

        def _worker() -> None:
            db_path = get_db_path()
            try:
                db = Database(db_path)
                try:
                    row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
                    if not row:
                        _append("記事が見つかりません", level="error")
                        with self._lock:
                            self._article = {"id": article_id}
                            self._error = "記事が見つかりません"
                            self._status = "error"
                        return
                    article = dict(row)
                    with self._lock:
                        self._article = article

                    if x_summarize_button_disabled_without_bearer(article):
                        msg = (
                            "環境変数が未登録のため要約生成は使用できません"
                            "（X_BEARER_TOKEN または TWITTER_BEARER_TOKEN を設定してください）"
                        )
                        _append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return

                    _append("Ollama の接続を確認しています…")
                    if not ensure_ollama_noninteractive(log=_append, auto_start=True):
                        msg = "Ollamaに接続できません"
                        _append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return

                    _append("本文を取得しています…")
                    extracted = fetch_article_content_text(article["url"])
                    if not extracted:
                        fallback = [article.get("title") or "", article.get("note") or ""]
                        extracted = "\n".join([x for x in fallback if x]).strip()
                    if not extracted:
                        msg = "本文を抽出できませんでした"
                        _append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return

                    _append("要約を生成しています（モデル処理中）…")
                    summary = summarize_article_ollama(
                        article, extracted, model="gemma3:4b", log=_append
                    )
                    if not summary:
                        msg = "要約の生成に失敗しました"
                        _append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return

                    db.update_article_summary(
                        article_id=article_id,
                        summary=summary,
                        model="gemma3:4b",
                        source_url=article["url"],
                    )
                    row_done = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
                    article = dict(row_done) if row_done else article
                    with self._lock:
                        self._article = article
                        self._status = "ok"
                    _append("要約を保存しました")
                finally:
                    db.close()
            except Exception as e:
                _append(f"エラー: {e}", level="error")
                with self._lock:
                    self._error = str(e)
                    self._status = "error"
            finally:
                with self._lock:
                    self._finished_at = datetime.now()

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        return "started"


runner = SummarizeRunner()
