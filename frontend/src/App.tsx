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

function NavButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={
        active
          ? "px-3 py-1.5 rounded text-sm bg-nav-active text-white"
          : "px-3 py-1.5 rounded text-sm bg-gray-200 dark:bg-gray-800 dark:text-gray-100"
      }
    >
      {children}
    </button>
  );
}

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
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [tagPanelOpen, setTagPanelOpen] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const toastTimerRef = useRef<number | null>(null);

  const [resummarizeModalOpen, setResummarizeModalOpen] = useState(false);
  const [resummarizeId, setResummarizeId] = useState<string | null>(null);
  const [pollingSummarizeId, setPollingSummarizeId] = useState<string | null>(null);
  const [loadingMore, setLoadingMore] = useState(false);
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadingMoreRef = useRef(false);

  const tagsKey = selectedTags.join(",");

  const loadBootstrap = useCallback(async (opts?: { silent?: boolean }) => {
    const silent = opts?.silent ?? false;
    setErr(null);
    if (!silent) setLoading(true);
    try {
      const b = await getBootstrap({
        view,
        q: qApplied,
        tags: tagsKey || undefined,
      });
      setArticles(b.articles);
      setTags(b.tags);
      setSync(b.sync);
      setTotal(b.total);
      setPage(b.page);
      setHasMore(b.has_more);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "load failed");
    } finally {
      if (!silent) setLoading(false);
    }
  }, [view, qApplied, tagsKey]);

  const onSyncFinished = useCallback(() => {
    void loadBootstrap({ silent: true });
  }, [loadBootstrap]);

  useEffect(() => {
    void loadBootstrap();
  }, [loadBootstrap]);

  useEffect(() => {
    writeUrl(view, qApplied, selectedTags);
  }, [view, qApplied, selectedTags]);

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

  useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const apply = (dark: boolean) => {
      root.classList.toggle("dark", dark);
      root.style.colorScheme = dark ? "dark" : "light";
    };
    apply(media.matches);
    const fn = (e: MediaQueryListEvent) => apply(e.matches);
    media.addEventListener("change", fn);
    return () => media.removeEventListener("change", fn);
  }, []);

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
      const a = await getArticles({
        view,
        q: qApplied,
        tags: tagsKey || undefined,
        page: next,
      });
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
      (entries) => {
        if (entries[0].isIntersecting) void loadMore();
      },
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

  const clearPolling = useCallback(() => {
    setPollingSummarizeId(null);
  }, []);

  return (
    <div className="max-w-6xl mx-auto p-3 sm:p-4 min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100 text-base">
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-gray-200 dark:border-gray-800 pb-2 mb-4">
        <h1 className="text-lg sm:text-xl font-semibold">Matter Hub</h1>
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <NavButton active={view === "active"} onClick={() => { setView("active"); setPage(1); }}>記事一覧</NavButton>
          <NavButton active={view === "archived"} onClick={() => { setView("archived"); setPage(1); }}>アーカイブ</NavButton>
          <NavButton active={view === "trend"} onClick={() => { setView("trend"); setPage(1); }}>トレンド</NavButton>
          <NavButton active={view === "trash"} onClick={() => { setView("trash"); setPage(1); }}>ゴミ箱</NavButton>
          <span className="text-gray-500 dark:text-gray-400 text-sm">{total} 件</span>
        </div>
        <div className="w-full">
          {sync ? <SyncPanel initial={sync} onSyncFinished={onSyncFinished} /> : null}
        </div>
      </header>

      {err ? (
        <p className="mb-2 text-sm text-red-600 dark:text-red-400" role="alert">
          {err}
        </p>
      ) : null}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <aside className="md:col-span-1">
          <label htmlFor="search-input" className="sr-only">記事を検索</label>
          <input
            id="search-input"
            type="search"
            placeholder="記事を検索"
            className="w-full border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-900 rounded px-3 py-2 text-base"
            value={qInput}
            onChange={(e) => setQInput(e.target.value)}
          />
          <div className="mt-4 text-sm">
            <button
              type="button"
              className="md:hidden w-full py-2 px-2 bg-gray-100 dark:bg-gray-800 rounded font-medium text-base text-left flex justify-between items-center"
              aria-expanded={tagPanelOpen}
              aria-controls="tag-filter"
              onClick={() => setTagPanelOpen((prev) => !prev)}
            >
              <span>タグ</span>
              <span aria-hidden="true">{tagPanelOpen ? "▾" : "▸"}</span>
            </button>
            <div id="tag-filter" className={`${tagPanelOpen ? "" : "hidden md:block"} mt-2 md:mt-0 space-y-1`}>
              {tags.map((t) => (
                <label key={t.name} className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={selectedTags.includes(t.name)}
                    onChange={() => onToggleTag(t.name)}
                    value={t.name}
                  />
                  <span>
                    {t.name}{" "}
                    <span className="text-gray-500 dark:text-gray-400">({t.count})</span>
                  </span>
                </label>
              ))}
            </div>
          </div>
        </aside>
        <section className="md:col-span-3">
          {loading ? (
            <p className="text-gray-500">読み込み中…</p>
          ) : articles.length === 0 ? (
            <p className="py-8 text-center text-sm text-gray-500 dark:text-gray-400">
              {qApplied || selectedTags.length > 0
                ? "条件に一致する記事がありません"
                : "記事がありません"}
            </p>
          ) : (
            <ul className="space-y-2">
              {articles.map((a) => (
                <ArticleRow
                  key={a.id}
                  article={a}
                  view={view}
                  pollingSummarizeId={pollingSummarizeId}
                  onSummarizePollingDone={clearPolling}
                  onMutate={handleMutate}
                  onRequestResummarize={onRequestResummarize}
                />
              ))}
            </ul>
          )}
          <div ref={sentinelRef} aria-hidden="true" />
          {loadingMore ? (
            <p className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">読み込み中…</p>
          ) : null}
        </section>
      </div>

      <ResummarizeModal
        open={resummarizeModalOpen}
        onClose={() => {
          setResummarizeModalOpen(false);
          setResummarizeId(null);
        }}
        onConfirm={handleResummarizeConfirm}
      />
      <Toast message={toastMessage} />
    </div>
  );
}
