"""Background sync orchestration for the webapp."""

from __future__ import annotations

import threading
from collections import deque
from datetime import datetime
from typing import Literal

from matter_hub.sync import run_sync

Status = Literal["idle", "running", "ok", "error"]

_LOG_MAX = 100


class SyncRunner:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._status: Status = "idle"
        self._log: deque[str] = deque(maxlen=_LOG_MAX)
        self._started_at: datetime | None = None
        self._finished_at: datetime | None = None
        self._summary: dict | None = None
        self._error: str | None = None

    @property
    def status(self) -> Status:
        return self._status

    @property
    def running(self) -> bool:
        return self._status == "running"

    def snapshot(self) -> dict:
        return {
            "status": self._status,
            "log": list(self._log),
            "started_at": self._started_at.isoformat() if self._started_at else None,
            "finished_at": self._finished_at.isoformat() if self._finished_at else None,
            "summary": self._summary,
            "error": self._error,
        }

    def start(
        self,
        tag: bool = True,
        embed: bool = True,
        model: str = "gemma3:4b",
        translate_titles: bool = True,
        retranslate_all: bool = False,
    ) -> bool:
        with self._lock:
            if self._status == "running":
                return False
            self._status = "running"
            self._log.clear()
            self._started_at = datetime.now()
            self._finished_at = None
            self._summary = None
            self._error = None

        def _append(msg: str, level: str = "info") -> None:
            ts = datetime.now().strftime("%H:%M:%S")
            tag = f"[{level.upper()}] " if level in {"warn", "error"} else ""
            self._log.append(f"[{ts}] {tag}{msg}")

        def _worker() -> None:
            try:
                summary = run_sync(
                    tag=tag,
                    embed=embed,
                    translate_titles=translate_titles,
                    retranslate_all=retranslate_all,
                    model=model,
                    log=_append,
                    auto_start_ollama=False,
                )
                with self._lock:
                    self._summary = summary
                    self._status = "ok"
            except Exception as e:
                _append(f"エラー: {e}")
                with self._lock:
                    self._error = str(e)
                    self._status = "error"
            finally:
                with self._lock:
                    self._finished_at = datetime.now()

        self._thread = threading.Thread(target=_worker, daemon=True)
        self._thread.start()
        return True


runner = SyncRunner()
