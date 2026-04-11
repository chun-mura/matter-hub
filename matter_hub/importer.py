"""URL importer for fetching and storing articles from various sources."""

import hashlib
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx

# ソース種別の自動判定マッピング
_SOURCE_PATTERNS = [
    (r"b\.hatena\.ne\.jp", "hatena"),
    (r"news\.ycombinator\.com", "hackernews"),
    (r"reddit\.com", "reddit"),
    (r"zenn\.dev", "zenn"),
    (r"qiita\.com", "qiita"),
    (r"(x\.com|twitter\.com)", "x"),
]


def detect_source(url: str) -> str:
    """URLからソース種別を自動判定する。"""
    for pattern, source in _SOURCE_PATTERNS:
        if re.search(pattern, url):
            return source
    return "web"


def generate_id(url: str) -> str:
    """URLからユニークなIDを生成する。"""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def _extract_title(html: str) -> str | None:
    """HTMLからtitleタグの中身を抽出する。"""
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    if m:
        title = m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", title)
        title = re.sub(r"\s+", " ", title)
        return title
    return None


def _extract_meta(html: str, name: str) -> str | None:
    """HTMLからmeta ogタグの値を抽出する。"""
    patterns = [
        rf'<meta\s+property="og:{name}"\s+content="([^"]*)"',
        rf'<meta\s+content="([^"]*)"\s+property="og:{name}"',
        rf"<meta\s+property='og:{name}'\s+content='([^']*)'",
    ]
    for pattern in patterns:
        m = re.search(pattern, html, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def fetch_article(url: str, source: str | None = None, note: str | None = None) -> dict:
    """URLから記事情報を取得してarticle dictを返す。"""
    resolved_source = source or detect_source(url)

    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": "matter-hub/1.0"},
        )
        resp.raise_for_status()
        html = resp.text
    except httpx.HTTPError:
        # フェッチ失敗時はURLだけで記事を作成
        return {
            "id": generate_id(url),
            "title": url,
            "url": url,
            "author": None,
            "publisher": urlparse(url).netloc,
            "published_date": None,
            "note": note,
            "library_state": None,
            "source": resolved_source,
        }

    title = _extract_meta(html, "title") or _extract_title(html) or url
    author = _extract_meta(html, "article:author")
    publisher = _extract_meta(html, "site_name") or urlparse(url).netloc
    pub_date = _extract_meta(html, "article:published_time")
    if pub_date and len(pub_date) >= 10:
        pub_date = pub_date[:10]

    return {
        "id": generate_id(url),
        "title": title,
        "url": url,
        "author": author,
        "publisher": publisher,
        "published_date": pub_date,
        "note": note,
        "library_state": None,
        "source": resolved_source,
    }


def parse_json_import(data: list[dict]) -> list[dict]:
    """JSON一括インポート用。各項目にid/sourceがなければ補完する。"""
    articles = []
    for item in data:
        url = item.get("url")
        if not url:
            continue
        article = {
            "id": item.get("id") or generate_id(url),
            "title": item.get("title") or url,
            "url": url,
            "author": item.get("author"),
            "publisher": item.get("publisher") or urlparse(url).netloc,
            "published_date": item.get("published_date"),
            "note": item.get("note"),
            "library_state": None,
            "source": item.get("source") or detect_source(url),
        }
        articles.append(article)
    return articles
