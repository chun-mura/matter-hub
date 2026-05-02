import { useEffect, useRef, useState } from "react";
import {
  getSummarizeQueue,
  postSummarizeAll,
  postSummarizeQueueCancel,
  type QueueSnapshot,
} from "../api";

export function BulkSummarizePanel({
  onDone,
  onProgress,
  onCurrentIdChange,
}: {
  onDone?: () => void;
  onProgress?: () => void;
  onCurrentIdChange?: (id: string | null) => void;
}) {
  const [snap, setSnap] = useState<QueueSnapshot | null>(null);
  const [statusMessage, setStatusMessage] = useState<{
    tone: "error" | "info";
    text: string;
  } | null>(null);
  const wasRunningRef = useRef(false);
  const prevDoneRef = useRef(0);

  const refresh = async () => {
    try {
      const next = await getSummarizeQueue();
      setSnap(next);
      setStatusMessage((m) => (m?.tone === "error" ? null : m));
    } catch (e) {
      setStatusMessage({
        tone: "error",
        text: e instanceof Error ? e.message : "キュー状態の取得に失敗しました",
      });
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  useEffect(() => {
    if (!snap?.running) return;
    const id = window.setInterval(() => void refresh(), 3000);
    return () => window.clearInterval(id);
  }, [snap?.running]);

  useEffect(() => {
    const wasRunning = wasRunningRef.current;
    wasRunningRef.current = snap?.running ?? false;
    if (wasRunning && !snap?.running && (snap?.total ?? 0) > 0) {
      onDone?.();
    }
  }, [snap?.running, snap?.total, onDone]);

  useEffect(() => {
    const prev = prevDoneRef.current;
    const current = snap?.done ?? 0;
    prevDoneRef.current = current;
    if (current > prev) {
      onProgress?.();
    }
  }, [snap?.done, onProgress]);

  useEffect(() => {
    const id = (snap?.running && snap?.bulk_active) ? (snap.current_id ?? null) : null;
    onCurrentIdChange?.(id);
  }, [snap?.current_id, snap?.running, snap?.bulk_active, onCurrentIdChange]);

  const handleStart = async () => {
    setStatusMessage(null);
    try {
      const r = await postSummarizeAll();
      setSnap(r.queue);
      if (r.outcome === "nothing_to_do") {
        setStatusMessage({ tone: "info", text: "未要約の記事はありません" });
      } else if (r.outcome === "skipped") {
        setStatusMessage({
          tone: "info",
          text: "キューに追加できる未要約がありません（いま実行中の記事だけの可能性があります）",
        });
      }
    } catch (e) {
      setStatusMessage({
        tone: "error",
        text: e instanceof Error ? e.message : "一括要約を開始できませんでした",
      });
    }
  };

  const handleCancel = async () => {
    setStatusMessage(null);
    try {
      const r = await postSummarizeQueueCancel();
      setSnap(r.queue);
    } catch (e) {
      setStatusMessage({
        tone: "error",
        text: e instanceof Error ? e.message : "キャンセルに失敗しました",
      });
    }
  };

  const running = snap?.running ?? false;
  const bulkActive = snap?.bulk_active ?? false;
  const total = snap?.total ?? 0;
  const done = snap?.done ?? 0;
  const unsummarized = snap?.unsummarized_count ?? null;
  const showBulkFraction = running && bulkActive && total > 0;
  const isDone = !running && total > 0 && done >= total;
  const buttonDisabled = running || unsummarized === 0;

  return (
    <div className="flex flex-col gap-1 text-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <button
          type="button"
          disabled={buttonDisabled}
          title="未要約をキューに入れて順に実行します。既にキューに並んでいる手動の要約は、この操作で置き換えられます。"
          onClick={() => void handleStart()}
          className={
            buttonDisabled
              ? "px-3 py-1.5 rounded text-sm bg-gray-400 text-white cursor-not-allowed"
              : "px-3 py-1.5 rounded text-sm bg-action-confirm text-white hover:bg-action-confirm-hover"
          }
        >
          未要約を一括要約
        </button>
        {!running && snap !== null ? (
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {(snap.unsummarized_count ?? 0) > 0
              ? `未要約 ${snap.unsummarized_count}件`
              : "すべて要約済み"}
          </span>
        ) : null}
        {running ? (
          <>
            {showBulkFraction ? (
              <span role="status" className="text-gray-600 dark:text-gray-300">
                {done}/{total} 件
                {snap?.current_title ? ` — ${snap.current_title}` : ""}
              </span>
            ) : (
              <span role="status" className="text-gray-600 dark:text-gray-300">
                要約を実行中です
                {snap?.current_title ? `（${snap.current_title}）` : ""}
              </span>
            )}
            <button
              type="button"
              aria-label="キューに残っている未実行の要約を破棄する"
              onClick={() => void handleCancel()}
              className="px-2 py-1 rounded text-xs bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
            >
              キャンセル
            </button>
          </>
        ) : isDone ? (
          <span role="status" className="text-xs text-emerald-700 dark:text-emerald-400">
            {done}件の要約が完了しました
          </span>
        ) : null}
      </div>
      {statusMessage ? (
        <p
          role={statusMessage.tone === "error" ? "alert" : "status"}
          className={
            statusMessage.tone === "error"
              ? "text-xs text-red-600 dark:text-red-400"
              : "text-xs text-gray-600 dark:text-gray-400"
          }
        >
          {statusMessage.text}
        </p>
      ) : null}
    </div>
  );
}
