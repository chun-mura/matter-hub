import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  getArticles,
  getBootstrap,
  postSummarize,
  type Article,
  type Bootstrap,
  type TagCount,
} from "./api";
import { ArticleRow } from "./components/ArticleRow";
import { BulkSummarizePanel, type BulkSummarizePanelHandle } from "./components/BulkSummarizePanel";
import { ResummarizeModal } from "./components/ResummarizeModal";
import { SyncPanel } from "./components/SyncPanel";
import { Toast } from "./components/ui/Toast";

function readUrl(): { view: string; q: string; tags: string[] } {
  const p = new URLSearchParams(window.location.search);
  return {
    view: p.get("view") || "active",
    q: p.get("q") || "",
    tags: (p.get("tags") || "").split(",").filter(Boolean),
  };
}

function writeUrl(view: string, q: string, tags: string[]) {
  const p = new URLSearchParams();
  if (view && view !== "active") p.set("view", view);
  if (q) p.set("q", q);
  if (tags.length) p.set("tags", tags.join(","));
  const qs = p.toString();
  window.history.replaceState(null, "", `${window.location.pathname}${qs ? `?${qs}` : ""}`);
}

const IconArchive = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="2" y="3" width="20" height="5" rx="1"/><path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/><path d="M10 12h4"/>
  </svg>
);
const IconTrend = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/>
  </svg>
);
const IconTrash = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/>
  </svg>
);
const IconSearch = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
  </svg>
);
const IconSparkle = () => (
  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9z"/><path d="M5 3l.9 2.1L8 6l-2.1.9L5 9l-.9-2.1L2 6l2.1-.9z"/><path d="M19 15l.9 2.1 2.1.9-2.1.9-.9 2.1-.9-2.1-2.1-.9 2.1-.9z"/>
  </svg>
);
const IconX = () => (
  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
    <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
  </svg>
);
const IconMenu = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
    <line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/>
  </svg>
);
const IconList = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/>
    <line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/>
  </svg>
);

const TABS = [
  { id: "active",   label: "記事一覧",   icon: <IconList /> },
  { id: "archived", label: "アーカイブ", icon: <IconArchive /> },
  { id: "trend",    label: "トレンド",   icon: <IconTrend /> },
  { id: "trash",    label: "ゴミ箱",     icon: <IconTrash /> },
] as const;

export default function App() {
  const initial = useMemo(() => readUrl(), []);
  const [view, setView] = useState(initial.view);
  const [qInput, setQInput] = useState(initial.q);
  const [qApplied, setQApplied] = useState(initial.q);
  const [selectedTags, setSelectedTags] = useState<string[]>(initial.tags);
  const [articles, setArticles] = useState<Article[]>([]);
  const [tags, setTags] = useState<TagCount[]>([]);
  const [sync, setSync] = useState<Bootstrap["sync"] | null>(null);
  const [total, setTotal] = useState(0);
  const [unsummarizedCount, setUnsummarizedCount] = useState<number | null>(null);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimerRef = useRef<number | null>(null);

  const [resummarizeModalOpen, setResummarizeModalOpen] = useState(false);
  const [resummarizeId, setResummarizeId] = useState<string | null>(null);
  const [pollingSummarizeId, setPollingSummarizeId] = useState<string | null>(null);
  const [bulkCurrentId, setBulkCurrentId] = useState<string | null>(null);
  const [queueUnsummarizedCount, setQueueUnsummarizedCount] = useState<number | null>(null);
  const bulkRef = useRef<BulkSummarizePanelHandle>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadingMoreRef = useRef(false);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const tagsKey = selectedTags.join(",");

  const loadBootstrap = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = opts?.silent ?? false;
    setErr(null);
    if (!silent) setLoading(true);
    try {
      const b = await getBootstrap({ view, q: qApplied, tags: tagsKey || undefined });
      setArticles(b.articles);
      setTags(b.tags);
      setSync(b.sync);
      setTotal(b.total);
      setPage(b.page);
      setHasMore(b.has_more);
      setUnsummarizedCount(b.unsummarized_count);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "load failed");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [view, qApplied, tagsKey]);

  const onSyncFinished = useCallback(() => {
    void loadBootstrap({ silent: true });
  }, [loadBootstrap]);

  const onBulkSummarizeDone = useCallback(() => {
    void loadBootstrap({ silent: true });
  }, [loadBootstrap]);

  const onBulkSummarizeProgress = useCallback(() => {
    void loadBootstrap({ silent: true });
  }, [loadBootstrap]);

  useEffect(() => { void loadBootstrap(); }, [loadBootstrap]);

  useEffect(() => { writeUrl(view, qApplied, selectedTags); }, [view, qApplied, selectedTags]);

  const debounceRef = useRef<number | null>(null);
  useEffect(() => {
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => {
      setQApplied(qInput);
      setPage(1);
    }, 300);
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current);
    };
  }, [qInput]);

  const showToast = useCallback((message: string) => {
    setToastMessage(message);
    if (toastTimerRef.current) window.clearTimeout(toastTimerRef.current);
    toastTimerRef.current = window.setTimeout(() => setToastMessage(null), 3000);
  }, []);

  const handleMutate = useCallback((message?: string) => {
    void loadBootstrap({ silent: true });
    if (message) showToast(message);
  }, [loadBootstrap, showToast]);

  const onToggleTag = (name: string) => {
    setSelectedTags((prev) => {
      const s = new Set(prev);
      if (s.has(name)) s.delete(name);
      else s.add(name);
      return Array.from(s);
    });
    setPage(1);
  };

  const loadMore = useCallback(async () => {
    if (!hasMore || loadingMoreRef.current) return;
    const next = page + 1;
    setErr(null);
    loadingMoreRef.current = true;
    setLoadingMore(true);
    try {
      const a = await getArticles({ view, q: qApplied, tags: tagsKey || undefined, page: next });
      setArticles((prev) => [...prev, ...a.articles]);
      setPage(next);
      setHasMore(a.has_more);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "load failed");
    } finally {
      loadingMoreRef.current = false;
      setLoadingMore(false);
    }
  }, [hasMore, page, view, qApplied, tagsKey]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel || !hasMore) return;
    const observer = new IntersectionObserver(
      (entries) => { if (entries[0].isIntersecting) void loadMore(); },
      { threshold: 0 }
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, loadMore]);

  const onRequestResummarize = (id: string) => {
    setResummarizeId(id);
    setResummarizeModalOpen(true);
  };

  const handleResummarizeConfirm = async () => {
    if (!resummarizeId) return;
    try {
      const r = await postSummarize(resummarizeId);
      if (r.outcome === "started") {
        setPollingSummarizeId(resummarizeId);
      } else if (r.outcome === "queued") {
        showToast("キューに追加されました");
        setPollingSummarizeId(resummarizeId);
      } else {
        setErr(r.panel.error || "要約を開始できませんでした");
      }
    } catch (e) {
      setErr(e instanceof Error ? e.message : "error");
    } finally {
      setResummarizeModalOpen(false);
      setResummarizeId(null);
    }
  };

  const clearPolling = useCallback(() => { setPollingSummarizeId(null); }, []);

  const tabCounts: Record<string, number | null> = {
    active:   total,
    archived: null,
    trend:    null,
    trash:    null,
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", background: "var(--bg)", overflow: "hidden", color: "var(--text-primary)" }}>

      {/* ── Header ────────────────────────────────────── */}
      <header className="mh-header" style={{ background: "var(--bg-surface)", borderBottom: "1px solid var(--border)", padding: "0 20px", userSelect: "none", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12, height: 52 }}>

          {/* Hamburger (mobile only) */}
          <button
            type="button"
            className="mh-menu-btn"
            aria-label="サイドバーを開く"
            onClick={() => setSidebarOpen((v) => !v)}
          >
            {sidebarOpen ? <IconX /> : <IconMenu />}
          </button>

          {/* Logo */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginRight: 4, flexShrink: 0 }}>
            <div style={{ width: 28, height: 28, borderRadius: 7, background: "linear-gradient(135deg, var(--accent) 0%, #8b5cf6 100%)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
                <rect x="3" y="3" width="7" height="7" rx="1.5" fill="white" opacity="0.9"/>
                <rect x="14" y="3" width="7" height="7" rx="1.5" fill="white" opacity="0.6"/>
                <rect x="3" y="14" width="7" height="7" rx="1.5" fill="white" opacity="0.6"/>
                <rect x="14" y="14" width="7" height="7" rx="1.5" fill="white" opacity="0.3"/>
              </svg>
            </div>
            <span className="mh-logo-text" style={{ fontWeight: 600, fontSize: 15, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>MatterHub</span>
          </div>

          {/* Tab nav (desktop only) */}
          <nav className="mh-tab-nav" style={{ display: "flex", gap: 2, flex: 1, minWidth: 0 }}>
            {TABS.map((t) => {
              const active = view === t.id;
              const count = tabCounts[t.id];
              return (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => { setView(t.id); setPage(1); setSidebarOpen(false); }}
                  style={{
                    display: "flex", alignItems: "center", gap: 6,
                    padding: "5px 12px", borderRadius: 7, border: "none",
                    background: active ? "rgba(91,127,255,0.15)" : "transparent",
                    color: active ? "var(--accent)" : "var(--text-secondary)",
                    fontWeight: active ? 600 : 400,
                    fontSize: 13, cursor: "pointer",
                    transition: "background 0.12s, color 0.12s",
                    flexShrink: 0, whiteSpace: "nowrap",
                  }}
                >
                  {t.icon && <span style={{ color: "inherit", opacity: 0.8, display: "flex" }}>{t.icon}</span>}
                  {t.label}
                  {count != null && (
                    <span style={{
                      fontSize: 11, fontWeight: 600,
                      color: active ? "var(--accent)" : "var(--text-muted)",
                      background: active ? "rgba(91,127,255,0.15)" : "rgba(255,255,255,0.07)",
                      padding: "0 6px", borderRadius: 10, lineHeight: "18px",
                    }}>{count}</span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Spacer (mobile only — replaces hidden tab nav) */}
          <div className="mh-header-spacer" />

          {/* Right actions */}
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            {(queueUnsummarizedCount ?? unsummarizedCount ?? 0) > 0 && (
              <button
                type="button"
                disabled={bulkRef.current?.running}
                onClick={() => void bulkRef.current?.start()}
                style={{
                  display: "flex", alignItems: "center", gap: 6,
                  fontSize: 12, fontWeight: 500, padding: "5px 12px",
                  borderRadius: 6, border: "1px solid rgba(245,166,35,0.3)",
                  background: "var(--amber-dim)", color: "var(--amber)",
                  cursor: bulkRef.current?.running ? "default" : "pointer",
                  opacity: bulkRef.current?.running ? 0.6 : 1,
                  transition: "opacity 0.15s",
                }}
              >
                <IconSparkle />
                <span className="mh-bulk-label">未要約を一括生成</span>
                <span style={{ fontSize: 11, fontWeight: 700, background: "var(--amber)", color: "#1a1000", borderRadius: 10, padding: "0 5px", lineHeight: "16px" }}>
                  {queueUnsummarizedCount ?? unsummarizedCount}
                </span>
              </button>
            )}
            {sync ? <SyncPanel initial={sync} onSyncFinished={onSyncFinished} /> : null}
          </div>
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────── */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>

        {/* Sidebar backdrop (mobile) */}
        {sidebarOpen && (
          <div
            className="mh-sidebar-backdrop"
            onClick={() => setSidebarOpen(false)}
            aria-hidden="true"
          />
        )}

        {/* Sidebar */}
        <aside className={`mh-sidebar${sidebarOpen ? " is-open" : ""}`} style={{ width: 220, flexShrink: 0, borderRight: "1px solid var(--border)", padding: "16px 14px", overflowY: "auto", overflowX: "hidden", display: "flex", flexDirection: "column" }}>

          {/* Search */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, background: "var(--bg-surface)", border: "1px solid var(--border)", borderRadius: 8, padding: "7px 10px", marginBottom: 12 }}>
            <span style={{ color: "var(--text-muted)", flexShrink: 0, display: "flex" }}><IconSearch /></span>
            <label htmlFor="search-input" className="sr-only">記事を検索</label>
            <input
              id="search-input"
              type="search"
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
              placeholder="記事を検索"
              style={{ background: "none", border: "none", outline: "none", color: "var(--text-primary)", fontSize: 13, width: "100%" }}
            />
            {qInput && (
              <button onClick={() => setQInput("")} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)", padding: 2, display: "flex" }}>
                <IconX />
              </button>
            )}
          </div>

          {/* Tags label */}
          <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.1em", color: "var(--text-muted)", textTransform: "uppercase", marginBottom: 8, paddingLeft: 2 }}>
            タグ
          </div>

          {/* Tag list */}
          <div style={{ overflowY: "auto", flex: 1 }}>
            {tags.map((t) => {
              const active = selectedTags.includes(t.name);
              return (
                <button
                  key={t.name}
                  type="button"
                  onClick={() => onToggleTag(t.name)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    width: "100%", padding: "5px 8px", borderRadius: 6,
                    background: active ? "var(--tag-bg-active)" : "transparent",
                    border: "none", cursor: "pointer", marginBottom: 1, color: "inherit",
                  }}
                >
                  <span style={{ fontSize: 13, color: active ? "var(--accent)" : "var(--text-secondary)", fontWeight: active ? 500 : 400, textAlign: "left" }}>
                    {t.name}
                  </span>
                  <span style={{ fontSize: 11, color: active ? "var(--accent)" : "var(--text-muted)", fontWeight: 500, flexShrink: 0, marginLeft: 4 }}>
                    {t.count}
                  </span>
                </button>
              );
            })}
          </div>
        </aside>

        {/* Main content */}
        <main className="mh-main" style={{ flex: 1, overflowY: "auto", padding: "16px 20px" }}>

          {err ? (
            <p style={{ marginBottom: 8, fontSize: 13, color: "var(--red)" }} role="alert">{err}</p>
          ) : null}

          {/* Bulk summarize panel — progress/status display */}
          <BulkSummarizePanel
            ref={bulkRef}
            onDone={onBulkSummarizeDone}
            onProgress={onBulkSummarizeProgress}
            onCurrentIdChange={setBulkCurrentId}
            onUnsummarizedCountChange={setQueueUnsummarizedCount}
          />

          {/* Active filter chips */}
          {selectedTags.length > 0 && (
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginBottom: 12 }}>
              {selectedTags.map((tag) => (
                <span key={tag} style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 12, color: "var(--accent)", background: "var(--accent-dim)", border: "1px solid var(--tag-border-active)", borderRadius: 20, padding: "2px 10px" }}>
                  {tag}
                  <button onClick={() => onToggleTag(tag)} style={{ background: "none", border: "none", cursor: "pointer", padding: 1, color: "var(--accent)", display: "flex" }}>
                    <IconX />
                  </button>
                </span>
              ))}
              <button
                onClick={() => setSelectedTags([])}
                style={{ fontSize: 12, color: "var(--text-muted)", background: "none", border: "none", cursor: "pointer", padding: "2px 6px" }}
              >
                すべて解除
              </button>
            </div>
          )}

          {/* Results count */}
          <div style={{ fontSize: 12, color: "var(--text-muted)", marginBottom: 10, display: "flex", alignItems: "center", gap: 8 }}>
            {total}件
            {view === "trash" && (
              <span style={{ color: "var(--red)", fontSize: 11 }}>
                · ゴミ箱のアイテムは30日後に自動削除されます
              </span>
            )}
          </div>

          {loading ? (
            <p style={{ color: "var(--text-muted)" }}>読み込み中…</p>
          ) : articles.length === 0 ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", padding: "60px 0", gap: 10, color: "var(--text-muted)" }}>
              <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" opacity="0.4">
                <circle cx="12" cy="12" r="10"/><path d="M8 15s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/>
              </svg>
              <span style={{ fontSize: 13 }}>
                {qApplied || selectedTags.length > 0 ? "条件に一致する記事がありません" : "記事がありません"}
              </span>
            </div>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0, display: "flex", flexDirection: "column", gap: 10 }}>
              {articles.map((a) => (
                <ArticleRow
                  key={a.id}
                  article={a}
                  view={view}
                  pollingSummarizeId={pollingSummarizeId}
                  bulkCurrentId={bulkCurrentId}
                  onSummarizePollingDone={clearPolling}
                  onMutate={handleMutate}
                  onRequestResummarize={onRequestResummarize}
                />
              ))}
            </ul>
          )}

          <div ref={sentinelRef} aria-hidden="true" />
          {loadingMore ? (
            <p style={{ marginTop: 16, textAlign: "center", fontSize: 13, color: "var(--text-muted)" }}>読み込み中…</p>
          ) : null}
        </main>
      </div>

      {/* ── Bottom nav (mobile only) ──────────────────── */}
      <nav className="mh-bottom-nav" aria-label="メインナビゲーション">
        {TABS.map((t) => {
          const active = view === t.id;
          const count = tabCounts[t.id];
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => { setView(t.id); setPage(1); setSidebarOpen(false); }}
              style={{
                flex: 1,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 4,
                background: "none",
                border: "none",
                cursor: "pointer",
                color: active ? "var(--accent)" : "var(--text-muted)",
                padding: "4px 0 6px",
                position: "relative",
              }}
            >
              <span style={{ display: "flex", position: "relative" }}>
                {t.icon}
                {count != null && count > 0 && (
                  <span style={{
                    position: "absolute",
                    top: -3, right: -7,
                    fontSize: 9, fontWeight: 700,
                    background: active ? "var(--accent)" : "var(--text-muted)",
                    color: "#fff",
                    borderRadius: 8, padding: "0 3px",
                    lineHeight: "13px", minWidth: 13, textAlign: "center",
                  }}>
                    {count > 99 ? "99+" : count}
                  </span>
                )}
              </span>
              <span style={{ fontSize: 10, fontWeight: active ? 600 : 400, whiteSpace: "nowrap" }}>
                {t.label}
              </span>
            </button>
          );
        })}
      </nav>

      <ResummarizeModal
        open={resummarizeModalOpen}
        onClose={() => { setResummarizeModalOpen(false); setResummarizeId(null); }}
        onConfirm={handleResummarizeConfirm}
      />
      <Toast message={toastMessage} />
    </div>
  );
}
