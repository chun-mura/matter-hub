/**
 * 開発時: ``VITE_API_BASE_URL`` を空にすると ``/api`` への相対 URL になり、Vite の
 * ``server.proxy`` 経由でバックエンドへ届く（ブラウザからは同一オリジン＝CORS 不要）。
 * 本番ビルド: 未設定時は ``http://127.0.0.1:8000`` に向ける（ビルド時に ``VITE_API_BASE_URL`` を渡すこと）。
 */
function resolveApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE_URL;
  if (raw != null && String(raw).trim() !== "") {
    return String(raw).replace(/\/$/, "");
  }
  if (import.meta.env.DEV) {
    return "";
  }
  return "http://127.0.0.1:8000";
}

export const API_BASE = resolveApiBase();

export type Article = Record<string, unknown> & {
  id: string;
  title?: string | null;
  title_ja?: string | null;
  url: string;
  x_summarize_disabled?: boolean;
};

export type TagCount = { name: string; count: number };

export type SummaryPanel = {
  article: Article;
  error: string | null;
  summary_open: boolean;
};

export type SummarizeJob = {
  status: string;
  log: string[];
  article: Article | null;
  error: string | null;
};

export type Bootstrap = {
  articles: Article[];
  total: number;
  page: number;
  has_more: boolean;
  tags: TagCount[];
  selected_tags: string[];
  view: string;
  q: string;
  sync: SyncSnapshot;
};

export type ArticlesPage = {
  articles: Article[];
  total: number;
  view: string;
  q: string;
  selected_tags: string[];
  page: number;
  has_more: boolean;
};

export type TagsResponse = {
  tags: TagCount[];
  selected_tags: string[];
  view: string;
};

export type SyncSnapshot = {
  status: string;
  log: string[];
  summary: Record<string, unknown> | null;
  error: string | null;
};

function buildQuery(params: Record<string, string | number | undefined>): string {
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === "") continue;
    sp.set(k, String(v));
  }
  const q = sp.toString();
  return q ? `?${q}` : "";
}

async function parseJson<T>(r: Response): Promise<T> {
  const text = await r.text();
  if (!r.ok) {
    throw new Error(`${r.status}: ${text.slice(0, 200)}`);
  }
  return text ? (JSON.parse(text) as T) : ({} as T);
}

export async function getBootstrap(params: {
  q?: string;
  tags?: string;
  view?: string;
}): Promise<Bootstrap> {
  const r = await fetch(`${API_BASE}/api/bootstrap${buildQuery(params)}`);
  return parseJson<Bootstrap>(r);
}

export async function getArticles(params: {
  q?: string;
  tags?: string;
  view?: string;
  page?: number;
}): Promise<ArticlesPage> {
  const r = await fetch(`${API_BASE}/api/articles${buildQuery(params)}`);
  return parseJson<ArticlesPage>(r);
}

export async function getTags(params: { view?: string; tags?: string }): Promise<TagsResponse> {
  const r = await fetch(`${API_BASE}/api/tags${buildQuery(params)}`);
  return parseJson<TagsResponse>(r);
}

export async function getSync(): Promise<SyncSnapshot> {
  const r = await fetch(`${API_BASE}/api/sync`);
  return parseJson<SyncSnapshot>(r);
}

export async function postSync(): Promise<SyncSnapshot> {
  const r = await fetch(`${API_BASE}/api/sync`, { method: "POST" });
  return parseJson<SyncSnapshot>(r);
}

export async function postDelete(articleId: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(articleId)}/delete`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(String(r.status));
}

export async function postRestore(articleId: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(articleId)}/restore`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(String(r.status));
}

export async function postArchive(articleId: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(articleId)}/archive`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(String(r.status));
}

export async function postUnarchive(articleId: string): Promise<void> {
  const r = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(articleId)}/unarchive`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(String(r.status));
}

export async function getArticleSummary(articleId: string): Promise<SummaryPanel> {
  const r = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(articleId)}/summary`);
  return parseJson<SummaryPanel>(r);
}

export async function postSummaryClose(articleId: string): Promise<SummaryPanel> {
  const r = await fetch(
    `${API_BASE}/api/articles/${encodeURIComponent(articleId)}/summary/close`,
    { method: "POST" },
  );
  return parseJson<SummaryPanel>(r);
}

export type SummarizePostResult =
  | { outcome: "started"; article: Article; job: SummarizeJob }
  | { outcome: "busy" | "config_error" | "start_failed"; panel: SummaryPanel };

export async function postSummarize(articleId: string): Promise<SummarizePostResult> {
  const r = await fetch(`${API_BASE}/api/articles/${encodeURIComponent(articleId)}/summarize`, {
    method: "POST",
  });
  if (!r.ok) throw new Error(String(r.status));
  return parseJson<SummarizePostResult>(r);
}

export type SummarizeStatusResult = {
  job: SummarizeJob | null;
  summary_panel: SummaryPanel | null;
};

export async function getSummarizeStatus(articleId: string): Promise<SummarizeStatusResult> {
  const r = await fetch(
    `${API_BASE}/api/articles/${encodeURIComponent(articleId)}/summarize/status`,
  );
  return parseJson<SummarizeStatusResult>(r);
}
