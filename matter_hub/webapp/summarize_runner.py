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
    """Processes summarization jobs serially; excess requests are queued."""

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

        # (article_id, content_text | None)
        self._queue: deque[tuple[str, str | None]] = deque()
        self._bulk_total: int = 0
        self._bulk_active: bool = False

    # ── public read ──────────────────────────────────────────────────────────

    def snapshot_for(self, article_id: str) -> dict | None:
        """Return job state for this article, or None if not active/recent/queued."""
        with self._lock:
            if self._article_id == article_id:
                return {
                    "status": self._status,
                    "log": list(self._log),
                    "started_at": self._started_at.isoformat() if self._started_at else None,
                    "finished_at": self._finished_at.isoformat() if self._finished_at else None,
                    "article": dict(self._article) if self._article else None,
                    "error": self._error,
                }
            for pos, (qid, _) in enumerate(self._queue):
                if qid == article_id:
                    return {
                        "status": "queued",
                        "log": [],
                        "started_at": None,
                        "finished_at": None,
                        "article": None,
                        "error": None,
                        "queue_position": pos,
                    }
            return None

    def queue_snapshot(self) -> dict:
        """Return queue progress for the web UI (bulk bar + global running)."""
        with self._lock:
            pending = len(self._queue)
            running_job = self._status == "running"
            if self._bulk_active:
                total = self._bulk_total
                done = max(total - pending - (1 if running_job else 0), 0)
            elif running_job:
                # Single summarize: no bulk fraction (avoids stale _bulk_total).
                total = 0
                done = 0
            elif self._bulk_total > 0 and pending == 0 and not running_job:
                # Bulk batch finished; keep totals until next start clears them.
                total = self._bulk_total
                done = self._bulk_total
            else:
                total = 0
                done = 0
            return {
                "running": running_job,
                "bulk_active": self._bulk_active,
                "current_id": self._article_id if running_job else None,
                "current_title": (
                    self._article.get("title_ja") or self._article.get("title") or self._article_id
                ) if running_job and self._article else None,
                "pending": pending,
                "total": total,
                "done": done,
            }

    # ── public write ─────────────────────────────────────────────────────────

    def start(self, article_id: str) -> Literal["started", "queued", "same"]:
        with self._lock:
            if self._status == "running":
                if self._article_id == article_id:
                    return "same"
                if not any(qid == article_id for qid, _ in self._queue):
                    self._queue.append((article_id, None))
                    if self._bulk_active:
                        self._bulk_total += 1
                return "queued"
            # New single run: clear bulk progress so queue API / header UI stays consistent.
            self._bulk_active = False
            self._bulk_total = 0
            self._reset_job(article_id)
        self._spawn(article_id, None)
        return "started"

    def start_with_text(self, article_id: str, content_text: str) -> Literal["started", "queued", "same"]:
        with self._lock:
            if self._status == "running":
                if self._article_id == article_id:
                    return "same"
                if not any(qid == article_id for qid, _ in self._queue):
                    self._queue.append((article_id, content_text))
                    if self._bulk_active:
                        self._bulk_total += 1
                return "queued"
            self._bulk_active = False
            self._bulk_total = 0
            self._reset_job(article_id)
        self._spawn(article_id, content_text)
        return "started"

    def start_bulk(self, article_ids: list[str]) -> int:
        """Queue article_ids for sequential summarization. Returns count enqueued."""
        next_item: tuple[str, str | None] | None = None

        with self._lock:
            ids = [a for a in article_ids if a != self._article_id]
            if not ids:
                # 候補が実行中の1件だけなど、積むものがないときはキューを壊さない
                return 0
            self._queue.clear()
            self._queue.extend((aid, None) for aid in ids)
            running_now = 1 if self._status == "running" else 0
            self._bulk_total = len(ids) + running_now
            self._bulk_active = True

            if self._status != "running" and self._queue:
                next_item = self._queue.popleft()
                self._reset_job(next_item[0])

        if next_item:
            self._spawn(next_item[0], next_item[1])
        return len(ids)

    def cancel_bulk(self) -> int:
        """Clear queue; current job runs to completion. Returns cancelled count."""
        with self._lock:
            count = len(self._queue)
            self._queue.clear()
            self._bulk_total = max(
                self._bulk_total - count,
                1 if self._status == "running" else 0,
            )
            return count

    # ── internal ─────────────────────────────────────────────────────────────

    def _reset_job(self, article_id: str) -> None:
        """Must be called with lock held."""
        self._status = "running"
        self._article_id = article_id
        self._article = None
        self._log.clear()
        self._started_at = datetime.now()
        self._finished_at = None
        self._error = None

    def _spawn(self, article_id: str, content_text: str | None) -> None:
        t = threading.Thread(target=self._worker, args=(article_id, content_text), daemon=True)
        with self._lock:
            self._thread = t
        t.start()

    def _log_append(self, msg: str, level: str = "info") -> None:
        line = _format_log_line(msg, level)
        with self._lock:
            self._log.append(line)

    def _advance(self) -> None:
        """Called from worker after it finishes. Start next queued job if any."""
        next_item: tuple[str, str | None] | None = None
        with self._lock:
            if self._queue:
                next_item = self._queue.popleft()
                self._reset_job(next_item[0])
            else:
                self._bulk_active = False
        if next_item:
            self._spawn(next_item[0], next_item[1])

    def _worker(self, article_id: str, content_text: str | None) -> None:
        db_path = get_db_path()
        try:
            db = Database(db_path)
            try:
                row = db.conn.execute("SELECT * FROM articles WHERE id = ?", (article_id,)).fetchone()
                if not row:
                    self._log_append("記事が見つかりません", level="error")
                    with self._lock:
                        self._article = {"id": article_id}
                        self._error = "記事が見つかりません"
                        self._status = "error"
                    return

                article = dict(row)
                with self._lock:
                    self._article = article

                if content_text is None:
                    if x_summarize_button_disabled_without_bearer(article):
                        msg = (
                            "環境変数が未登録のため要約生成は使用できません"
                            "（X_BEARER_TOKEN または TWITTER_BEARER_TOKEN を設定してください）"
                        )
                        self._log_append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return

                    self._log_append("Ollama の接続を確認しています…")
                    if not ensure_ollama_noninteractive(log=self._log_append, auto_start=True):
                        msg = "Ollamaに接続できません"
                        self._log_append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return

                    self._log_append("本文を取得しています…")
                    extracted = fetch_article_content_text(article["url"])
                    if not extracted:
                        fallback = [article.get("title") or "", article.get("note") or ""]
                        extracted = "\n".join([x for x in fallback if x]).strip()
                    if not extracted:
                        msg = "本文を抽出できませんでした"
                        self._log_append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return
                else:
                    self._log_append(f"貼り付けられた本文を使用します（{len(content_text)} 文字）")
                    self._log_append("Ollama の接続を確認しています…")
                    if not ensure_ollama_noninteractive(log=self._log_append, auto_start=True):
                        msg = "Ollamaに接続できません"
                        self._log_append(msg, level="error")
                        with self._lock:
                            self._error = msg
                            self._status = "error"
                        return
                    extracted = content_text

                self._log_append("要約を生成しています（モデル処理中）…")
                summary = summarize_article_ollama(
                    article, extracted, model="gemma3:4b", log=self._log_append
                )
                if not summary:
                    msg = "要約の生成に失敗しました"
                    self._log_append(msg, level="error")
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
                self._log_append("要約を保存しました")
            finally:
                db.close()
        except Exception as e:
            self._log_append(f"エラー: {e}", level="error")
            with self._lock:
                self._error = str(e)
                self._status = "error"
        finally:
            with self._lock:
                self._finished_at = datetime.now()
            self._advance()


runner = SummarizeRunner()
