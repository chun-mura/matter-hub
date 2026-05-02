import { useCallback, useEffect, useState } from "react";
import {
  deleteSummary,
  getArticleSummary,
  getSummarizeStatus,
  postArchive,
  postDelete,
  postRestore,
  postSummarize,
  postSummarizeWithText,
  postSummaryClose,
  postUnarchive,
  putSummaryManual,
  type Article,
  type SummaryPanel,
} from "../api";
import { useSwipeRow } from "../hooks/useSwipeRow";
import { SummarizeWithTextModal } from "./SummarizeWithTextModal";
import { SummaryEditModal } from "./SummaryEditModal";
import { ConfirmModal } from "./ui/ConfirmModal";

type Props = {
  article: Article;
  view: string;
  pollingSummarizeId: string | null;
  onSummarizePollingDone: () => void;
  onMutate: (message?: string) => void;
  onRequestResummarize: (articleId: string) => void;
};

function ResummarizeButton({
  disabled,
  loading,
  onClick,
}: {
  disabled: boolean;
  loading: boolean;
  onClick: () => void;
}) {
  if (disabled) {
    return (
      <button
        type="button"
        disabled
        className="px-3 py-1.5 bg-action-primary text-white rounded opacity-60 cursor-not-allowed"
        title="環境変数が未登録のため使用できません（再要約には X_BEARER_TOKEN または TWITTER_BEARER_TOKEN の設定が必要です）"
      >
        再要約
      </button>
    );
  }
  return (
    <button
      type="button"
      className="px-3 py-1.5 bg-action-primary hover:bg-action-primary-hover text-white rounded disabled:opacity-70"
      disabled={loading}
      onClick={onClick}
    >
      再要約
    </button>
  );
}

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
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [summaryDeleteConfirmOpen, setSummaryDeleteConfirmOpen] = useState(false);
  const [pasteModalOpen, setPasteModalOpen] = useState(false);

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
    await postDelete(id);
    onMutate("削除しました");
  }, [id, onMutate]);

  const handleDeleteConfirm = useCallback(async () => {
    await postDelete(id);
    setDeleteConfirmOpen(false);
    onMutate("削除しました");
  }, [id, onMutate]);

  const onArchive = useCallback(async () => {
    await postArchive(id);
    onMutate("アーカイブしました");
  }, [id, onMutate]);

  const onUnarchive = useCallback(async () => {
    await postUnarchive(id);
    onMutate("アーカイブ解除しました");
  }, [id, onMutate]);

  const onRestore = useCallback(async () => {
    await postRestore(id);
    onMutate("復元しました");
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

  const handleSaveSummary = async (text: string) => {
    const p = await putSummaryManual(id, text);
    setSummaryPanel(p);
    onMutate();
  };

  const handleSubmitWithText = async (text: string) => {
    setSummarizeError(null);
    try {
      const r = await postSummarizeWithText(id, text);
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

  const handleDeleteSummary = async () => {
    await deleteSummary(id);
    setSummaryPanel(null);
    setSummaryDeleteConfirmOpen(false);
    onMutate();
  };

  const summaryOpen = summaryPanel?.summary_open === true;
  const hasSummary = Boolean(article.summary) || Boolean(summaryPanel?.article?.summary);
  const showExpandedSummary = Boolean(summaryOpen && summaryPanel);

  return (
    <li
      ref={rowRef}
      className="article-row relative overflow-hidden border border-gray-200 dark:border-gray-700 rounded bg-white dark:bg-gray-900"
      id={`row-${id}`}
      data-article-id={id}
      data-view={view}
    >
      <div
        aria-hidden="true"
        className="swipe-bg swipe-bg-left absolute inset-0 flex items-center justify-end pr-4 bg-action-danger text-white font-medium select-none pointer-events-none opacity-0"
      >
        削除
      </div>
      <div
        aria-hidden="true"
        className="swipe-bg swipe-bg-right absolute inset-0 flex items-center justify-start pl-4 bg-action-restore text-white font-medium select-none pointer-events-none opacity-0"
      >
        {view === "archived" ? "アーカイブ解除" : view === "trash" ? "復元" : "アーカイブ"}
      </div>
      <div className="swipe-surface relative bg-white dark:bg-gray-900 p-3">
        {/* 上段: タイトル・メタ情報 + 記事操作ボタン */}
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
            {view === "trash" ? (
              <button
                type="button"
                className="px-3 py-1.5 bg-action-restore hover:bg-action-restore-hover text-white rounded"
                onClick={() => void onRestore()}
              >
                復元
              </button>
            ) : (
              <>
                {view === "archived" ? (
                  <button
                    type="button"
                    className="px-3 py-1.5 bg-action-restore hover:bg-action-restore-hover text-white rounded"
                    onClick={() => void onUnarchive()}
                  >
                    アーカイブ解除
                  </button>
                ) : view !== "trend" ? (
                  <button
                    type="button"
                    className="px-3 py-1.5 bg-action-neutral hover:bg-action-neutral-hover text-white rounded"
                    onClick={() => void onArchive()}
                  >
                    アーカイブ
                  </button>
                ) : null}
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-danger hover:bg-action-danger-hover text-white rounded"
                  onClick={() => setDeleteConfirmOpen(true)}
                >
                  削除
                </button>
              </>
            )}
          </div>
        </div>

        {/* 下段: 要約操作ボタン (active ビューのみ) */}
        {view === "active" ? (
          <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-800 flex flex-wrap gap-2 items-center justify-end text-sm sm:text-xs">
            {hasSummary && summaryOpen ? (
              <>
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-warning hover:bg-action-warning-hover text-white rounded"
                  onClick={() => void closeSummary()}
                >
                  要約を閉じる
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-neutral hover:bg-action-neutral-hover text-white rounded"
                  onClick={() => setEditModalOpen(true)}
                >
                  編集
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-danger hover:bg-action-danger-hover text-white rounded"
                  onClick={() => setSummaryDeleteConfirmOpen(true)}
                >
                  要約を削除
                </button>
                <ResummarizeButton
                  disabled={disabled}
                  loading={progressLog !== null}
                  onClick={() => onRequestResummarize(id)}
                />
              </>
            ) : hasSummary ? (
              <>
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-confirm hover:bg-action-confirm-hover text-white rounded"
                  onClick={() => void openSummary()}
                >
                  要約を見る
                </button>
                <ResummarizeButton
                  disabled={disabled}
                  loading={progressLog !== null}
                  onClick={() => onRequestResummarize(id)}
                />
              </>
            ) : (
              <>
                {disabled ? (
                  <button
                    type="button"
                    disabled
                    className="px-3 py-1.5 bg-action-primary text-white rounded opacity-60"
                    title="環境変数が未登録のため使用できません"
                  >
                    要約生成
                  </button>
                ) : (
                  <button
                    type="button"
                    className="px-3 py-1.5 bg-action-primary hover:bg-action-primary-hover text-white rounded inline-flex items-center gap-1.5 disabled:opacity-70"
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
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-primary hover:bg-action-primary-hover text-white rounded disabled:opacity-70"
                  disabled={progressLog !== null}
                  onClick={() => setPasteModalOpen(true)}
                >
                  本文から要約
                </button>
                <button
                  type="button"
                  className="px-3 py-1.5 bg-action-neutral hover:bg-action-neutral-hover text-white rounded disabled:opacity-70"
                  disabled={progressLog !== null}
                  onClick={() => setEditModalOpen(true)}
                >
                  手動入力
                </button>
              </>
            )}
          </div>
        ) : null}

        {summarizeError ? (
          <p role="alert" className="mt-2 text-sm text-red-600 dark:text-red-400">
            {summarizeError}
          </p>
        ) : null}

        {progressLog !== null ? (
          <div className="mt-2 rounded border border-amber-200 dark:border-amber-800 bg-amber-50/40 dark:bg-amber-950/20 p-2 text-sm">
            <div className="text-gray-800 dark:text-gray-100 font-medium">要約を実行しています…</div>
            {progressLog.length > 0 ? (
              <details className="mt-2 text-xs text-gray-600 dark:text-gray-300" open>
                <summary className="cursor-pointer select-none">ログ</summary>
                <pre className="mt-1 max-h-48 overflow-auto whitespace-pre-wrap bg-gray-900 dark:bg-gray-950 text-gray-100 rounded p-2 font-mono text-xs leading-snug">
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
            <div className="flex gap-2 justify-end pt-1">
              <button
                type="button"
                className="px-3 py-1.5 bg-action-neutral hover:bg-action-neutral-hover text-white rounded text-xs"
                onClick={() => setEditModalOpen(true)}
              >
                編集
              </button>
              <button
                type="button"
                className="px-3 py-1.5 bg-action-danger hover:bg-action-danger-hover text-white rounded text-xs"
                onClick={() => setSummaryDeleteConfirmOpen(true)}
              >
                削除
              </button>
            </div>
          </div>
        ) : null}
      </div>

      <ConfirmModal
        open={deleteConfirmOpen}
        title="記事を削除"
        description="この記事を削除しますか？取り消しはできません。"
        confirmLabel="削除する"
        variant="danger"
        onClose={() => setDeleteConfirmOpen(false)}
        onConfirm={handleDeleteConfirm}
      />
      <ConfirmModal
        open={summaryDeleteConfirmOpen}
        title="要約を削除"
        description="この記事の要約を削除しますか？取り消しはできません。"
        confirmLabel="削除する"
        variant="danger"
        onClose={() => setSummaryDeleteConfirmOpen(false)}
        onConfirm={handleDeleteSummary}
      />
      <SummaryEditModal
        open={editModalOpen}
        initialValue={String(summaryPanel?.article?.summary ?? article.summary ?? "")}
        onClose={() => setEditModalOpen(false)}
        onSave={handleSaveSummary}
      />
      <SummarizeWithTextModal
        open={pasteModalOpen}
        onClose={() => setPasteModalOpen(false)}
        onSubmit={handleSubmitWithText}
      />
    </li>
  );
}
