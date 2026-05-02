import { useCallback, useEffect, useState } from "react";
import type React from "react";
import { Check, Copy, ExternalLink, RotateCcw, Sparkles, Trash2 } from "lucide-react";
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
  type Article,
  type SummaryPanel,
} from "../api";
import { useSwipeRow } from "../hooks/useSwipeRow";
import { SummarizeWithTextModal } from "./SummarizeWithTextModal";
import { ConfirmModal } from "./ui/ConfirmModal";

type Props = {
  article: Article;
  view: string;
  pollingSummarizeId: string | null;
  bulkCurrentId?: string | null;
  onSummarizePollingDone: () => void;
  onMutate: (message?: string) => void;
  onRequestResummarize: (articleId: string) => void;
};

const SOURCE_COLORS: Record<string, string> = {
  "x.com":           "#1a8cd8",
  "note.com":        "#4cc38a",
  "Qiita":           "#55c500",
  "zenn.dev":        "#3ea8ff",
  "speakerdeck.com": "#45a562",
  "oreilly.co.jp":   "#d44000",
  "scrapbox.io":     "#00A676",
};

function getSourceColor(source: string | null | undefined): string {
  if (!source) return "var(--text-muted)";
  return SOURCE_COLORS[source] ?? "var(--text-muted)";
}

const iconBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  cursor: "pointer",
  padding: "4px 5px",
  borderRadius: 5,
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  color: "var(--text-muted)",
  transition: "color 0.12s",
};

const primaryBtnStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  fontSize: 12,
  fontWeight: 500,
  padding: "5px 12px",
  borderRadius: 6,
  border: "none",
  cursor: "pointer",
  background: "var(--accent)",
  color: "#fff",
  transition: "opacity 0.15s, background 0.15s",
};

const closeBtnStyle: React.CSSProperties = {
  ...primaryBtnStyle,
  background: "var(--accent-dim)",
  color: "var(--accent)",
};

const ghostBtnStyle: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  gap: 5,
  fontSize: 12,
  fontWeight: 500,
  padding: "5px 11px",
  borderRadius: 6,
  border: "1px solid var(--border)",
  cursor: "pointer",
  background: "transparent",
  color: "var(--text-secondary)",
  transition: "background 0.12s, border-color 0.12s",
};

const TITLE_TRUNCATE = 80;

function SummaryBadge({ hasSummary }: { hasSummary: boolean }) {
  if (hasSummary) {
    return (
      <span style={{
        fontSize: 10, fontWeight: 600, letterSpacing: "0.06em",
        color: "var(--green)", background: "var(--green-dim)",
        border: "1px solid rgba(46,204,138,0.25)",
        padding: "1px 7px", borderRadius: 20, whiteSpace: "nowrap",
      }}>
        要約済
      </span>
    );
  }
  return (
    <span style={{
      fontSize: 10, fontWeight: 600, letterSpacing: "0.06em",
      color: "var(--text-muted)", background: "rgba(255,255,255,0.04)",
      border: "1px solid var(--border-subtle)",
      padding: "1px 7px", borderRadius: 20, whiteSpace: "nowrap",
    }}>
      未要約
    </span>
  );
}

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
        style={{ ...ghostBtnStyle, opacity: 0.5, cursor: "not-allowed" }}
        title="環境変数が未登録のため使用できません（再要約には X_BEARER_TOKEN または TWITTER_BEARER_TOKEN の設定が必要です）"
      >
        再要約
      </button>
    );
  }
  return (
    <button
      type="button"
      style={{ ...ghostBtnStyle, opacity: loading ? 0.7 : 1 }}
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
  bulkCurrentId,
  onSummarizePollingDone,
  onMutate,
  onRequestResummarize,
}: Props) {
  const id = article.id;
  const disabled = Boolean(article.x_summarize_disabled);
  const isBulkProcessing = bulkCurrentId === id;
  const displayTitle = (article.title_ja as string | null | undefined) || article.title || "";
  const publisher = article.publisher as string | null | undefined;
  const author = article.author as string | null | undefined;
  const publishedDate = article.published_date as string | null | undefined;
  const articleTags = article.tags as string[] | undefined;
  const hasSummaryData = Boolean(article.summary);

  const [summaryPanel, setSummaryPanel] = useState<SummaryPanel | null>(null);
  const [summarizeError, setSummarizeError] = useState<string | null>(null);
  const [progressLog, setProgressLog] = useState<string[] | null>(null);
  const [localPolling, setLocalPolling] = useState(false);
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [summaryDeleteConfirmOpen, setSummaryDeleteConfirmOpen] = useState(false);
  const [pasteModalOpen, setPasteModalOpen] = useState(false);
  const [summaryCopied, setSummaryCopied] = useState(false);
  const [titleExpanded, setTitleExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);

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
        if (st.job?.status === "queued") {
          const pos = st.job.queue_position ?? 0;
          const waitLabel = pos === 0 ? "次にこの記事を処理します" : `キューで待機中（先に ${pos} 件）`;
          setProgressLog([`[${new Date().toLocaleTimeString("ja-JP", { hour: "2-digit", minute: "2-digit", second: "2-digit" })}] ${waitLabel}`]);
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
      } else if (r.outcome === "queued") {
        onMutate("キューに追加されました");
        setProgressLog([]);
        setLocalPolling(true);
      } else {
        setSummaryPanel(r.panel);
        setSummarizeError(r.panel.error);
      }
    } catch (e) {
      setSummarizeError(e instanceof Error ? e.message : "error");
    }
  };

  const handleSubmitWithText = async (text: string) => {
    setSummarizeError(null);
    try {
      const r = await postSummarizeWithText(id, text);
      if (r.outcome === "started") {
        setProgressLog(r.job.log ?? []);
        setLocalPolling(true);
      } else if (r.outcome === "queued") {
        onMutate("キューに追加されました");
        setProgressLog([]);
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
  const hasSummary = hasSummaryData || Boolean(summaryPanel?.article?.summary);
  const showExpandedSummary = Boolean(summaryOpen && summaryPanel);

  const truncatedTitle = displayTitle.length > TITLE_TRUNCATE && !titleExpanded
    ? displayTitle.slice(0, TITLE_TRUNCATE) + "…"
    : displayTitle;

  const isTrash = view === "trash";

  return (
    <li
      ref={rowRef}
      className="article-row"
      id={`row-${id}`}
      data-article-id={id}
      data-view={view}
      style={{ position: "relative", overflow: "hidden", borderRadius: "var(--radius-card)", listStyle: "none" }}
    >
      {/* Swipe action backgrounds */}
      <div
        aria-hidden="true"
        className="swipe-bg swipe-bg-left"
        style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "flex-end", paddingRight: 16, background: "var(--red)", color: "#fff", fontWeight: 500, userSelect: "none", pointerEvents: "none", opacity: 0 }}
      >
        削除
      </div>
      <div
        aria-hidden="true"
        className="swipe-bg swipe-bg-right"
        style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "flex-start", paddingLeft: 16, background: "var(--green)", color: "#fff", fontWeight: 500, userSelect: "none", pointerEvents: "none", opacity: 0 }}
      >
        {view === "archived" ? "アーカイブ解除" : view === "trash" ? "復元" : "アーカイブ"}
      </div>

      {/* Card surface */}
      <div
        className="swipe-surface"
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        style={{
          position: "relative",
          background: hovered ? "var(--bg-card-hover)" : "var(--bg-card)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-card)",
          padding: "16px 18px",
          transition: "background 0.15s, border-color 0.15s",
          cursor: "default",
        }}
      >
        {/* Top row: source meta + badge + actions */}
        <div className="mh-article-top-row" style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "nowrap", minWidth: 0 }}>
          {/* Source dot */}
          <span style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: getSourceColor(publisher), flexShrink: 0, marginTop: 1 }} />

          {/* Author */}
          {author && (
            <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500, whiteSpace: "nowrap", flexShrink: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", maxWidth: 160 }}>
              {author}
            </span>
          )}
          {author && <span style={{ fontSize: 11, color: "var(--text-muted)", flexShrink: 0 }}>·</span>}

          {/* Publisher */}
          <span style={{ fontSize: 11, color: "var(--text-muted)", fontWeight: 500, whiteSpace: "nowrap", flexShrink: 0 }}>
            {publisher || ""}
          </span>

          {/* Date */}
          {publishedDate && (
            <span style={{ fontSize: 11, color: "var(--text-muted)", whiteSpace: "nowrap", flexShrink: 0 }}>
              · {String(publishedDate).slice(0, 10)}
            </span>
          )}

          <span style={{ flex: "1 1 0", minWidth: 0 }} />

          {/* Summary badge */}
          <SummaryBadge hasSummary={hasSummary} />

          {/* Action icon buttons */}
          <div style={{ display: "flex", gap: 4, marginLeft: 4 }}>
            {isTrash ? (
              <button onClick={() => void onRestore()} title="元に戻す" style={{ ...iconBtnStyle, color: "var(--green)" }}>
                <RotateCcw size={13} />
              </button>
            ) : (
              <>
                {view === "archived" ? (
                  <button onClick={() => void onUnarchive()} title="アーカイブ解除" style={{ ...iconBtnStyle, color: "var(--text-muted)" }}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="3" width="20" height="5" rx="1"/>
                      <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>
                      <path d="M10 12h4"/>
                      <line x1="12" y1="12" x2="12" y2="18"/>
                    </svg>
                  </button>
                ) : view !== "trend" ? (
                  <button onClick={() => void onArchive()} title="アーカイブ" style={iconBtnStyle}>
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
                      <rect x="2" y="3" width="20" height="5" rx="1"/>
                      <path d="M4 8v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8"/>
                      <path d="M10 12h4"/>
                    </svg>
                  </button>
                ) : null}
                <button onClick={() => setDeleteConfirmOpen(true)} title="ゴミ箱" style={iconBtnStyle}>
                  <Trash2 size={13} />
                </button>
              </>
            )}
          </div>
        </div>

        {/* Title */}
        <div style={{ marginBottom: 6 }}>
          <span style={{ fontSize: 14, fontWeight: 500, color: "var(--text-primary)", lineHeight: 1.65, display: "inline" }}>
            {truncatedTitle}
          </span>
          {displayTitle.length > TITLE_TRUNCATE && (
            <button
              onClick={() => setTitleExpanded((v) => !v)}
              style={{ background: "none", border: "none", cursor: "pointer", color: "var(--accent)", fontSize: 12, marginLeft: 4, padding: 0, display: "inline" }}
            >
              {titleExpanded ? "折りたたむ" : "続きを見る"}
            </button>
          )}
          {article.url && (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              title="元ページを開く"
              style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", marginLeft: 4, textDecoration: "none", opacity: 0.75, padding: "4px 6px", borderRadius: 5, minWidth: 28, minHeight: 28, transition: "opacity 0.12s, background 0.12s", verticalAlign: "middle" }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.opacity = "1"; (e.currentTarget as HTMLElement).style.background = "var(--accent-dim)"; }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.opacity = "0.75"; (e.currentTarget as HTMLElement).style.background = "transparent"; }}
            >
              <ExternalLink size={14} />
            </a>
          )}
        </div>

        {/* Tags */}
        {articleTags && articleTags.length > 0 && (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 5, marginBottom: 10 }}>
            {articleTags.map((tag) => (
              <span key={tag} style={{ fontSize: 11, color: "var(--text-secondary)", background: "var(--tag-bg)", border: "1px solid var(--tag-border)", borderRadius: 20, padding: "1px 8px", cursor: "default" }}>
                {tag}
              </span>
            ))}
          </div>
        )}

        {/* Summarize error */}
        {summarizeError ? (
          <p role="alert" style={{ marginTop: 8, fontSize: 13, color: "var(--red)" }}>
            {summarizeError}
          </p>
        ) : null}

        {/* Progress log */}
        {progressLog !== null ? (
          <div style={{ marginTop: 8, borderRadius: 7, border: "1px solid rgba(245,166,35,0.2)", background: "rgba(245,166,35,0.08)", padding: "10px 12px", fontSize: 13 }}>
            <div style={{ color: "var(--amber)", fontWeight: 500, marginBottom: 4 }}>要約を実行しています…</div>
            {progressLog.length > 0 ? (
              <details style={{ fontSize: 11, color: "var(--text-secondary)" }} open>
                <summary style={{ cursor: "pointer", userSelect: "none" }}>ログ</summary>
                <pre style={{ marginTop: 4, maxHeight: 192, overflowY: "auto", whiteSpace: "pre-wrap", background: "rgba(0,0,0,0.3)", borderRadius: 4, padding: "6px 8px", fontFamily: "monospace", fontSize: 11, lineHeight: 1.5 }}>
                  {progressLog.join("\n")}
                </pre>
              </details>
            ) : (
              <p style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 2 }}>ログを準備しています…</p>
            )}
          </div>
        ) : null}

        {/* Expanded summary */}
        {showExpandedSummary && summaryPanel ? (
          <div style={{ marginTop: 8, padding: "10px 12px", background: "rgba(91,127,255,0.07)", border: "1px solid rgba(91,127,255,0.18)", borderRadius: 7, fontSize: 13, color: "var(--text-secondary)", lineHeight: 1.7 }}>
            <div style={{ fontSize: 10, fontWeight: 600, letterSpacing: "0.08em", color: "var(--accent)", marginBottom: 5, textTransform: "uppercase" }}>
              AI要約
            </div>
            <p style={{ whiteSpace: "pre-wrap" }}>{String(summaryPanel.article.summary ?? "")}</p>
            {summaryPanel.article.summary_model ? (
              <p style={{ marginTop: 4, fontSize: 11, color: "var(--text-muted)" }}>
                model: {String(summaryPanel.article.summary_model)}
              </p>
            ) : null}
            <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 8 }}>
              <button
                type="button"
                title={summaryCopied ? "コピー済み" : "コピー"}
                style={iconBtnStyle}
                onClick={() => {
                  navigator.clipboard.writeText(String(summaryPanel.article.summary ?? "")).then(() => {
                    setSummaryCopied(true);
                    setTimeout(() => setSummaryCopied(false), 2000);
                  });
                }}
              >
                {summaryCopied ? <Check size={13} /> : <Copy size={13} />}
              </button>
              <button
                type="button"
                title="要約を削除"
                style={{ ...iconBtnStyle, color: "var(--red)" }}
                onClick={() => setSummaryDeleteConfirmOpen(true)}
              >
                <Trash2 size={13} />
              </button>
            </div>
          </div>
        ) : null}

        {/* Bottom action row */}
        {!isTrash && (view === "active" || view === "archived" || view === "trend") ? (
          <div style={{ display: "flex", gap: 6, alignItems: "center", marginTop: 10 }}>
            {hasSummary && summaryOpen ? (
              <>
                <button onClick={() => void closeSummary()} style={closeBtnStyle}>
                  要約を閉じる
                </button>
                <ResummarizeButton
                  disabled={disabled}
                  loading={progressLog !== null}
                  onClick={() => onRequestResummarize(id)}
                />
              </>
            ) : hasSummary ? (
              <>
                <button onClick={() => void openSummary()} style={primaryBtnStyle}>
                  <Sparkles size={12} />
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
                    style={{ ...primaryBtnStyle, opacity: 0.5, cursor: "not-allowed" }}
                    title="環境変数が未登録のため使用できません"
                  >
                    要約生成
                  </button>
                ) : (
                  <button
                    type="button"
                    style={{ ...primaryBtnStyle, opacity: progressLog !== null || isBulkProcessing ? 0.7 : 1 }}
                    disabled={progressLog !== null || isBulkProcessing}
                    onClick={() => void startSummarize()}
                  >
                    {progressLog !== null || isBulkProcessing ? (
                      <>
                        <span className="summary-spinner" aria-hidden="true" />
                        生成中…
                      </>
                    ) : (
                      <><Sparkles size={12} /> 要約生成</>
                    )}
                  </button>
                )}
                {disabled ? (
                  <button
                    type="button"
                    disabled={progressLog !== null}
                    style={{ ...ghostBtnStyle, opacity: progressLog !== null ? 0.7 : 1 }}
                    onClick={() => setPasteModalOpen(true)}
                  >
                    本文から要約
                  </button>
                ) : null}
              </>
            )}
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
      <SummarizeWithTextModal
        open={pasteModalOpen}
        onClose={() => setPasteModalOpen(false)}
        onSubmit={handleSubmitWithText}
      />
    </li>
  );
}
