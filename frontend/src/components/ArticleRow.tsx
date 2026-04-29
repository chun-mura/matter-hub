import { useCallback, useEffect, useState } from "react";
import {
  getArticleSummary,
  getSummarizeStatus,
  postArchive,
  postDelete,
  postRestore,
  postSummarize,
  postSummaryClose,
  postUnarchive,
  type Article,
  type SummaryPanel,
} from "../api";
import { useSwipeRow } from "../hooks/useSwipeRow";

type Props = {
  article: Article;
  view: string;
  pollingSummarizeId: string | null;
  onSummarizePollingDone: () => void;
  onMutate: () => void;
  onRequestResummarize: (articleId: string) => void;
};

export function ArticleRow({
  article,
  view,
  pollingSummarizeId,
  onSummarizePollingDone,
  onMutate,
  onRequestResummarize,
}: Props) {
  const id = article.id;
  const disabled = Boolean(article.x_summarize_disabled);
  const displayTitle = (article.title_ja as string | null | undefined) || article.title || "";

  const [summaryPanel, setSummaryPanel] = useState<SummaryPanel | null>(null);
  const [summarizeError, setSummarizeError] = useState<string | null>(null);
  const [progressLog, setProgressLog] = useState<string[] | null>(null);
  const [localPolling, setLocalPolling] = useState(false);

  const pollingActive = localPolling || pollingSummarizeId === id;

  useEffect(() => {
    if (!pollingActive) return;
    const tick = async () => {
      try {
        const st = await getSummarizeStatus(id);
        if (st.job?.status === "running") {
          setProgressLog(st.job.log ?? []);
          setSummarizeError(null);
          return;
        }
        if (st.summary_panel) {
          setSummaryPanel(st.summary_panel);
          setSummarizeError(st.summary_panel.error);
          setProgressLog(null);
          setLocalPolling(false);
          onSummarizePollingDone();
          onMutate();
        } else if (!st.job) {
          setProgressLog(null);
          setLocalPolling(false);
          onSummarizePollingDone();
        }
      } catch {
        /* ignore */
      }
    };
    void tick();
    const interval = window.setInterval(() => void tick(), 1000);
    return () => window.clearInterval(interval);
  }, [pollingActive, id, onMutate, onSummarizePollingDone]);

  const onDelete = useCallback(async () => {
    if (!window.confirm("Delete this article?")) return;
    await postDelete(id);
    onMutate();
  }, [id, onMutate]);

  const onArchive = useCallback(async () => {
    await postArchive(id);
    onMutate();
  }, [id, onMutate]);

  const onUnarchive = useCallback(async () => {
    await postUnarchive(id);
    onMutate();
  }, [id, onMutate]);

  const onRestore = useCallback(async () => {
    await postRestore(id);
    onMutate();
  }, [id, onMutate]);

  const rowRef = useSwipeRow(id, view, onArchive, onUnarchive, onRestore, onDelete);

  const openSummary = async () => {
    setSummarizeError(null);
    try {
      const p = await getArticleSummary(id);
      setSummaryPanel(p);
    } catch (e) {
      setSummarizeError(e instanceof Error ? e.message : "error");
    }
  };

  const closeSummary = async () => {
    try {
      const p = await postSummaryClose(id);
      setSummaryPanel(p);
    } catch (e) {
      setSummarizeError(e instanceof Error ? e.message : "error");
    }
  };

  const startSummarize = async () => {
    setSummarizeError(null);
    try {
      const r = await postSummarize(id);
      if (r.outcome === "started") {
        setProgressLog(r.job.log ?? []);
        setLocalPolling(true);
      } else {
        setSummaryPanel(r.panel);
        setSummarizeError(r.panel.error);
      }
    } catch (e) {
      setSummarizeError(e instanceof Error ? e.message : "error");
    }
  };

  const summaryOpen = summaryPanel?.summary_open === true;
  const hasSummary = Boolean(article.summary);
  const showExpandedSummary = Boolean(summaryOpen && summaryPanel);

  return (
    <li
      ref={rowRef}
      className="article-row relative overflow-hidden border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900"
      id={`row-${id}`}
      data-article-id={id}
      data-view={view}
    >
      <div className="swipe-bg swipe-bg-left absolute inset-0 flex items-center justify-end pr-4 bg-red-600 text-white font-medium select-none pointer-events-none opacity-0">
        delete
      </div>
      <div className="swipe-bg swipe-bg-right absolute inset-0 flex items-center justify-start pl-4 bg-green-600 text-white font-medium select-none pointer-events-none opacity-0">
        {view === "archived" ? "unarchive" : view === "trash" ? "restore" : "archive"}
      </div>
      <div className="swipe-surface relative bg-white dark:bg-gray-900 p-3">
        <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-2">
          <div className="min-w-0 flex-1">
            <a
              className="font-medium text-blue-700 dark:text-blue-400 hover:underline break-words text-base leading-snug"
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
            >
              {displayTitle}
            </a>
            <div className="text-sm sm:text-xs text-gray-500 dark:text-gray-400 mt-1 break-words">
              {article.author ? String(article.author) : ""}
              {article.publisher ? ` · ${String(article.publisher)}` : ""}
              {article.published_date
                ? ` · ${String(article.published_date).slice(0, 10)}`
                : ""}
            </div>
          </div>
          <div className="text-sm sm:text-xs flex gap-2 sm:shrink-0 self-end sm:self-start flex-wrap justify-end">
            {view === "active" ? (
              <div className="flex flex-wrap gap-2 items-center justify-end">
                {hasSummary && summaryOpen ? (
                  <>
                    <button
                      type="button"
                      className="px-3 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded"
                      onClick={() => void closeSummary()}
                    >
                      要約を閉じる
                    </button>
                    {disabled ? (
                      <button
                        type="button"
                        disabled
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded opacity-60 cursor-not-allowed"
                        title="環境変数が未登録のため使用できません（再要約には X_BEARER_TOKEN または TWITTER_BEARER_TOKEN の設定が必要です）"
                      >
                        再要約
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded disabled:opacity-70"
                        disabled={progressLog !== null}
                        onClick={() => onRequestResummarize(id)}
                      >
                        再要約
                      </button>
                    )}
                  </>
                ) : hasSummary ? (
                  <>
                    <button
                      type="button"
                      className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded"
                      onClick={() => void openSummary()}
                    >
                      要約を見る
                    </button>
                    {disabled ? (
                      <button
                        type="button"
                        disabled
                        className="px-3 py-1.5 bg-indigo-600 text-white rounded opacity-60 cursor-not-allowed"
                        title="環境変数が未登録のため使用できません"
                      >
                        再要約
                      </button>
                    ) : (
                      <button
                        type="button"
                        className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded disabled:opacity-70"
                        disabled={progressLog !== null}
                        onClick={() => onRequestResummarize(id)}
                      >
                        再要約
                      </button>
                    )}
                  </>
                ) : disabled ? (
                  <button type="button" disabled className="px-3 py-1.5 bg-indigo-600 text-white rounded opacity-60">
                    要約生成
                  </button>
                ) : (
                  <button
                    type="button"
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded inline-flex items-center gap-1.5 disabled:opacity-70"
                    disabled={progressLog !== null}
                    onClick={() => void startSummarize()}
                  >
                    {progressLog !== null ? (
                      <>
                        <span className="summary-spinner" aria-hidden="true" />
                        生成中...
                      </>
                    ) : (
                      "要約生成"
                    )}
                  </button>
                )}
              </div>
            ) : null}
            {view === "trash" ? (
              <button
                type="button"
                className="px-3 py-1.5 bg-green-600 text-white rounded"
                onClick={() => void onRestore()}
              >
                restore
              </button>
            ) : (
              <>
                {view === "archived" ? (
                  <button
                    type="button"
                    className="px-3 py-1.5 bg-green-600 text-white rounded"
                    onClick={() => void onUnarchive()}
                  >
                    unarchive
                  </button>
                ) : view !== "trend" ? (
                  <button
                    type="button"
                    className="px-3 py-1.5 bg-gray-600 hover:bg-gray-700 text-white rounded"
                    onClick={() => void onArchive()}
                  >
                    archive
                  </button>
                ) : null}
                <button
                  type="button"
                  className="px-3 py-1.5 bg-red-600 text-white rounded"
                  onClick={() => void onDelete()}
                >
                  delete
                </button>
              </>
            )}
          </div>
        </div>

        {summarizeError ? (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">{summarizeError}</p>
        ) : null}

        {progressLog !== null ? (
          <div className="mt-2 rounded border border-amber-200 dark:border-amber-800 bg-amber-50/40 dark:bg-amber-950/20 p-2 text-sm">
            <div className="text-gray-800 dark:text-gray-100 font-medium">要約を実行しています…</div>
            {progressLog.length > 0 ? (
              <details className="mt-2 text-xs text-gray-600 dark:text-gray-300" open>
                <summary className="cursor-pointer select-none">ログ</summary>
                <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap bg-gray-900 dark:bg-gray-950 text-gray-100 rounded p-2 font-mono text-[11px] leading-snug">
                  {progressLog.join("\n")}
                </pre>
              </details>
            ) : (
              <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">ログを準備しています…</p>
            )}
          </div>
        ) : null}

        {showExpandedSummary && summaryPanel ? (
          <div className="mt-2 rounded border border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900/80 p-3 text-sm space-y-2">
            <p className="text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
              {String(summaryPanel.article.summary ?? "")}
            </p>
            {summaryPanel.article.summary_model ? (
              <p className="text-xs text-gray-500 dark:text-gray-400">
                model: {String(summaryPanel.article.summary_model)}
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </li>
  );
}
