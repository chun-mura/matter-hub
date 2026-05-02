import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";
import {
  getSummarizeQueue,
  postSummarizeAll,
  postSummarizeQueueCancel,
  type QueueSnapshot,
} from "../api";

export type BulkSummarizePanelHandle = {
  start: () => Promise<void>;
  running: boolean;
};

export const BulkSummarizePanel = forwardRef<
  BulkSummarizePanelHandle,
  {
    onDone?: () => void;
    onProgress?: () => void;
    onCurrentIdChange?: (id: string | null) => void;
    onUnsummarizedCountChange?: (count: number) => void;
  }
>(function BulkSummarizePanel({ onDone, onProgress, onCurrentIdChange, onUnsummarizedCountChange }, ref) {
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

  useEffect(() => {
    if (snap?.unsummarized_count == null) return;
    onUnsummarizedCountChange?.(snap.unsummarized_count);
  }, [snap?.unsummarized_count, onUnsummarizedCountChange]);

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

  useImperativeHandle(ref, () => ({
    start: handleStart,
    running,
  }), [running]); // eslint-disable-line react-hooks/exhaustive-deps

  const bulkActive = snap?.bulk_active ?? false;
  const total = snap?.total ?? 0;
  const done = snap?.done ?? 0;
  const showBulkFraction = running && bulkActive && total > 0;
  const isDone = !running && total > 0 && done >= total;

  if (!running && !isDone && !statusMessage) return null;

  return (
    <div style={{ fontSize: 12, color: "var(--text-secondary)", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "6px 12px", marginBottom: 8 }}>
      {running ? (
        <>
          {showBulkFraction ? (
            <span role="status">
              一括要約中… {done}/{total}件
              {snap?.current_title ? ` — ${snap.current_title}` : ""}
            </span>
          ) : (
            <span role="status">
              要約を実行中です{snap?.current_title ? `（${snap.current_title}）` : ""}
            </span>
          )}
          <button
            type="button"
            aria-label="キューに残っている未実行の要約を破棄する"
            onClick={() => void handleCancel()}
            style={{ fontSize: 11, padding: "2px 8px", borderRadius: 5, border: "1px solid var(--border)", background: "transparent", color: "var(--text-muted)", cursor: "pointer" }}
          >
            キャンセル
          </button>
        </>
      ) : isDone ? (
        <span role="status" style={{ color: "var(--green)" }}>{done}件の要約が完了しました</span>
      ) : null}
      {statusMessage ? (
        <p
          role={statusMessage.tone === "error" ? "alert" : "status"}
          style={{ fontSize: 12, color: statusMessage.tone === "error" ? "var(--red)" : "var(--text-muted)", margin: 0 }}
        >
          {statusMessage.text}
        </p>
      ) : null}
    </div>
  );
});
