import { useEffect, useRef, useState } from "react";
import { getSync, postSync, type SyncSnapshot } from "../api";

export function SyncPanel({
  initial,
  onSyncFinished,
}: {
  initial: SyncSnapshot;
  onSyncFinished?: () => void;
}) {
  const [sync, setSync] = useState(initial);

  useEffect(() => {
    setSync(initial);
  }, [initial]);

  const prevStatusRef = useRef<string | null>(null);
  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = sync.status;
    if (prev === "running" && sync.status !== "running") {
      onSyncFinished?.();
    }
  }, [sync.status, onSyncFinished]);

  useEffect(() => {
    if (sync.status !== "running") return;
    const id = window.setInterval(async () => {
      try {
        setSync(await getSync());
      } catch {
        /* ignore */
      }
    }, 2000);
    return () => window.clearInterval(id);
  }, [sync.status]);

  const running = sync.status === "running";

  const onClick = async () => {
    if (running) return;
    try {
      setSync(await postSync());
    } catch {
      /* ignore */
    }
  };

  const summary = sync.summary as Record<string, number | null | undefined> | null;

  return (
    <div className="flex flex-col gap-1 text-sm">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <button
          type="button"
          disabled={running}
          onClick={() => void onClick()}
          className={
            running
              ? "px-3 py-1.5 rounded text-sm bg-gray-400 text-white cursor-not-allowed"
              : "px-3 py-1.5 rounded text-sm bg-action-confirm text-white hover:bg-action-confirm-hover"
          }
        >
          {running ? "同期中…" : "同期"}
        </button>
        {sync.status === "ok" && summary ? (
          <span role="status" className="text-xs text-emerald-700 dark:text-emerald-400">
            完了: {summary.synced}件同期
            {summary.deleted ? `、${summary.deleted}件削除` : ""}
            {summary.tagged != null ? `、${summary.tagged}件タグ付け` : ""}
            {summary.embedded != null ? `、${summary.embedded}件埋め込み` : ""}
            {summary.titles_translated != null
              ? `、${summary.titles_translated}件翻訳`
              : ""}
          </span>
        ) : null}
        {sync.status === "error" && sync.error ? (
          <span role="alert" className="text-xs text-red-600 dark:text-red-400">
            エラー: {sync.error}
          </span>
        ) : null}
      </div>
      {sync.log && sync.log.length > 0 ? (
        <details className="text-xs text-gray-600 dark:text-gray-300" open={running}>
          <summary className="cursor-pointer select-none">ログ</summary>
          <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap bg-gray-900 dark:bg-gray-950 text-gray-100 rounded p-2">
            {sync.log.join("\n")}
          </pre>
        </details>
      ) : null}
    </div>
  );
}
