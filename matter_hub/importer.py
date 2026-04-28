"""URL importer for fetching and storing articles from various sources."""

import hashlib
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

import httpx
import trafilatura
from matter_hub.config import load_config

_REDDIT_UA = "neta-trend-collector/1.0 (trend analysis tool)"
_REDDIT_PERMALINK_RE = re.compile(r"^/r/[^/]+/comments/[^/]+")
_X_STATUS_RE = re.compile(r"^/[A-Za-z0-9_]+/status/(\d+)")

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


def _fetch_reddit_article(url: str, note: str | None) -> dict | None:
    """Reddit permalink を JSON API で取得して article dict を返す。失敗時は None。"""
    parsed = urlparse(url)
    if not _REDDIT_PERMALINK_RE.match(parsed.path):
        return None

    json_url = f"https://www.reddit.com{parsed.path.rstrip('/')}/.json"
    try:
        resp = httpx.get(
            json_url,
            follow_redirects=True,
            timeout=15,
            headers={"User-Agent": _REDDIT_UA, "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()
        post = data[0]["data"]["children"][0]["data"]
    except (httpx.HTTPError, ValueError, KeyError, IndexError):
        return None

    title = post.get("title") or url
    author = post.get("author")
    subreddit = post.get("subreddit")
    publisher = f"reddit.com/r/{subreddit}" if subreddit else "reddit.com"
    created = post.get("created_utc")
    pub_date = None
    if isinstance(created, (int, float)):
        pub_date = datetime.fromtimestamp(created, tz=timezone.utc).strftime("%Y-%m-%d")

    return {
        "id": generate_id(url),
        "title": title,
        "url": url,
        "author": author,
        "publisher": publisher,
        "published_date": pub_date,
        "note": note,
        "library_state": None,
        "source": "reddit",
    }


def _extract_x_status_id(url: str) -> str | None:
    parsed = urlparse(url)
    m = _X_STATUS_RE.match(parsed.path)
    if not m:
        return None
    return m.group(1)


def _get_x_bearer_token() -> str | None:
    token = os.environ.get("X_BEARER_TOKEN") or os.environ.get("TWITTER_BEARER_TOKEN")
    if token and str(token).strip():
        return str(token).strip()

    config = load_config()
    cfg_token = config.get("x_bearer_token") or config.get("twitter_bearer_token")
    if cfg_token and str(cfg_token).strip():
        return str(cfg_token).strip()
    return None


def x_api_bearer_token_configured() -> bool:
    """X API の Bearer token が設定されているか（環境変数または config.json）。"""
    return _get_x_bearer_token() is not None


def x_summarize_button_disabled_without_bearer(article: dict) -> bool:
    """要約生成ボタンを無効化すべきか（X/Twitter 由来で Bearer が未設定のとき）。

    Matter 同期などで ``source`` が ``matter`` のままでも、URL が x.com / twitter.com なら
    ``source=x`` と同様に扱う。
    """
    if x_api_bearer_token_configured():
        return False
    if article.get("source") == "x":
        return True
    url = article.get("url") or ""
    return bool(re.search(r"(x\.com|twitter\.com)", url))


def _fetch_x_article_via_api(url: str, note: str | None) -> dict | None:
    tweet_id = _extract_x_status_id(url)
    if not tweet_id:
        return None

    token = _get_x_bearer_token()
    if not token:
        return None

    endpoint = (
        f"https://api.x.com/2/tweets/{tweet_id}"
        "?expansions=author_id&tweet.fields=created_at&user.fields=name,username"
    )
    try:
        resp = httpx.get(
            endpoint,
            timeout=15,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
        resp.raise_for_status()
        payload = resp.json()
        data = payload["data"]
    except (httpx.HTTPError, ValueError, KeyError):
        return None

    author = None
    users = payload.get("includes", {}).get("users", [])
    if users:
        user = users[0]
        author = user.get("name") or user.get("username")

    created_at = data.get("created_at")
    pub_date = created_at[:10] if isinstance(created_at, str) and len(created_at) >= 10 else None

    return {
        "id": generate_id(url),
        "title": data.get("text") or url,
        "url": url,
        "author": author,
        "publisher": "x.com",
        "published_date": pub_date,
        "note": note,
        "library_state": None,
        "source": "x",
    }


def fetch_article(url: str, source: str | None = None, note: str | None = None) -> dict:
    """URLから記事情報を取得してarticle dictを返す。"""
    resolved_source = source or detect_source(url)

    if resolved_source == "reddit":
        article = _fetch_reddit_article(url, note)
        if article is not None:
            return article

    if resolved_source == "x":
        article = _fetch_x_article_via_api(url, note)
        if article is not None:
            return article

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


def fetch_article_content_text(url: str, timeout: int = 20) -> str:
    """URLから本文テキストを抽出する。抽出できない場合は空文字を返す。"""
    try:
        resp = httpx.get(
            url,
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "matter-hub/1.0"},
        )
        resp.raise_for_status()
    except httpx.HTTPError:
        return ""

    extracted = trafilatura.extract(
        resp.text,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        favor_precision=True,
        url=url,
    )
    if not extracted:
        return ""
    return extracted.strip()


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
