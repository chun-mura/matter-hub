import httpx

from matter_hub.importer import (
    fetch_article,
    fetch_article_content_text,
    x_summarize_button_disabled_without_bearer,
)


def test_fetch_article_content_text_success(monkeypatch):
    html = "<html><body><article><p>Hello world</p></article></body></html>"

    def fake_get(*_args, **_kwargs):
        req = httpx.Request("GET", "https://example.com")
        return httpx.Response(200, text=html, request=req)

    monkeypatch.setattr("matter_hub.importer.httpx.get", fake_get)
    monkeypatch.setattr("matter_hub.importer.trafilatura.extract", lambda *_args, **_kwargs: "Hello world")

    result = fetch_article_content_text("https://example.com")
    assert result == "Hello world"


def test_fetch_article_content_text_http_error(monkeypatch):
    def fake_get(*_args, **_kwargs):
        raise httpx.ConnectError("failed", request=httpx.Request("GET", "https://example.com"))

    monkeypatch.setattr("matter_hub.importer.httpx.get", fake_get)
    result = fetch_article_content_text("https://example.com")
    assert result == ""


def test_fetch_article_x_via_api_success(monkeypatch):
    x_url = "https://x.com/example/status/1234567890"

    def fake_get(url, *_args, **_kwargs):
        req = httpx.Request("GET", url)
        if url.startswith("https://api.x.com/2/tweets/1234567890"):
            return httpx.Response(
                200,
                json={
                    "data": {
                        "id": "1234567890",
                        "text": "hello from x",
                        "created_at": "2026-01-02T03:04:05.000Z",
                    },
                    "includes": {"users": [{"name": "Alice", "username": "alice"}]},
                },
                request=req,
            )
        return httpx.Response(200, text="<html><title>fallback</title></html>", request=req)

    monkeypatch.setattr("matter_hub.importer.httpx.get", fake_get)
    monkeypatch.setattr("matter_hub.importer.load_config", lambda: {"x_bearer_token": "test-token"})

    article = fetch_article(x_url, source="x")
    assert article["source"] == "x"
    assert article["title"] == "hello from x"
    assert article["author"] == "Alice"
    assert article["published_date"] == "2026-01-02"
    assert article["publisher"] == "x.com"


def test_fetch_article_x_fallback_without_token(monkeypatch):
    x_url = "https://x.com/example/status/1234567890"

    def fake_get(url, *_args, **_kwargs):
        req = httpx.Request("GET", url)
        if url == x_url:
            return httpx.Response(
                200,
                text=(
                    '<html><head><meta property="og:title" content="Public Post"></head>'
                    "<body></body></html>"
                ),
                request=req,
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("matter_hub.importer.httpx.get", fake_get)
    monkeypatch.setattr("matter_hub.importer.load_config", lambda: {})
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)

    article = fetch_article(x_url, source="x")
    assert article["source"] == "x"
    assert article["title"] == "Public Post"
    assert article["url"] == x_url


def test_x_summarize_disabled_x_source_no_token(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    monkeypatch.setattr("matter_hub.importer.load_config", lambda: {})
    assert x_summarize_button_disabled_without_bearer({"source": "x", "url": "https://example.com"}) is True


def test_x_summarize_disabled_x_url_matter_source_no_token(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    monkeypatch.setattr("matter_hub.importer.load_config", lambda: {})
    assert x_summarize_button_disabled_without_bearer(
        {"source": "matter", "url": "https://x.com/u/status/1"}
    ) is True


def test_x_summarize_not_disabled_with_token(monkeypatch):
    monkeypatch.setenv("X_BEARER_TOKEN", "t")
    assert x_summarize_button_disabled_without_bearer({"source": "x", "url": "https://x.com/u/status/1"}) is False


def test_x_summarize_not_disabled_non_x(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    monkeypatch.setattr("matter_hub.importer.load_config", lambda: {})
    assert x_summarize_button_disabled_without_bearer(
        {"source": "matter", "url": "https://example.com/a"}
    ) is False
