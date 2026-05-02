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
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <button
        type="button"
        disabled={running}
        onClick={() => void onClick()}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 12,
          fontWeight: 500,
          padding: "5px 12px",
          borderRadius: 6,
          border: "1px solid var(--border)",
          cursor: running ? "default" : "pointer",
          background: "transparent",
          color: running ? "var(--green)" : "var(--text-secondary)",
          transition: "color 0.15s",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            animation: running ? "mh-spin 1s linear infinite" : "none",
          }}
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2.2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 12a9 9 0 0 1 9-9 9.75 9.75 0 0 1 6.74 2.74L21 8" />
            <path d="M21 3v5h-5" />
            <path d="M21 12a9 9 0 0 1-9 9 9.75 9.75 0 0 1-6.74-2.74L3 16" />
            <path d="M8 16H3v5" />
          </svg>
        </span>
        {running ? "同期中…" : "同期"}
      </button>
      {sync.status === "ok" && summary ? (
        <span style={{ fontSize: 11, color: "var(--green)" }} role="status">
          {summary.synced}件同期完了
        </span>
      ) : null}
      {sync.status === "error" && sync.error ? (
        <span style={{ fontSize: 11, color: "var(--red)" }} role="alert">
          エラー: {sync.error}
        </span>
      ) : null}
    </div>
  );
}
