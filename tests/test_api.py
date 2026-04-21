import json
import httpx
import pytest

from matter_hub.api import MatterClient, parse_feed_entry

SAMPLE_FEED_ENTRY = {
    "id": "entry1",
    "content": {
        "title": "Test Article",
        "url": "https://example.com/article",
        "author": {"any_name": "Alice"},
        "publisher": {"any_name": "TechBlog"},
        "publication_date": "2025-01-15",
        "tags": [
            {"name": "tech", "created_date": "2025-01-15"}
        ],
        "my_annotations": [
            {"text": "highlighted text", "note": "my note", "created_date": "2025-01-16", "word_start": 0, "word_end": 10}
        ],
        "my_note": {"note": "article note"},
        "library": {"library_state": 1, "queue_order": 12345},
    },
    "annotations": [],
}

SAMPLE_DELETED_ENTRY = {
    "id": "entry2",
    "content": {
        "title": "Deleted",
        "url": "https://example.com/deleted",
        "author": {"any_name": None},
        "publisher": {"any_name": None},
        "publication_date": None,
        "tags": [],
        "my_annotations": [],
        "my_note": {"note": ""},
        "library": {"library_state": 3},
    },
    "annotations": [],
}


def test_parse_feed_entry():
    result = parse_feed_entry(SAMPLE_FEED_ENTRY)
    assert result["article"]["id"] == "entry1"
    assert result["article"]["title"] == "Test Article"
    assert result["article"]["author"] == "Alice"
    assert result["article"]["publisher"] == "TechBlog"
    assert result["article"]["url"] == "https://example.com/article"
    assert result["article"]["library_state"] == 1
    assert result["article"]["queue_order"] == 12345
    assert result["article"]["note"] == "article note"
    assert len(result["tags"]) == 1
    assert result["tags"][0]["name"] == "tech"
    assert len(result["highlights"]) == 1
    assert result["highlights"][0]["text"] == "highlighted text"


def test_parse_feed_entry_deleted():
    result = parse_feed_entry(SAMPLE_DELETED_ENTRY)
    assert result["article"]["library_state"] == 3


def test_parse_feed_entry_null_fields():
    entry = {
        "id": "entry3",
        "content": {
            "title": "Minimal",
            "url": "https://example.com",
            "author": None,
            "publisher": None,
            "publication_date": None,
            "tags": [],
            "my_annotations": [],
            "my_note": None,
            "library": None,
        },
        "annotations": [],
    }
    result = parse_feed_entry(entry)
    assert result["article"]["author"] is None
    assert result["article"]["publisher"] is None
    assert result["article"]["library_state"] is None
    assert result["article"]["queue_order"] is None
    assert result["article"]["note"] is None


def test_trigger_qr_login(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/qr_login/trigger/",
        json={"session_token": "test_session_123"},
    )
    client = MatterClient()
    token = client.trigger_qr_login()
    assert token == "test_session_123"


def test_exchange_token_success(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/qr_login/exchange/",
        json={"access_token": "acc_123", "refresh_token": "ref_456"},
    )
    client = MatterClient()
    result = client.exchange_token("session_123")
    assert result == {"access_token": "acc_123", "refresh_token": "ref_456"}


def test_exchange_token_pending(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/qr_login/exchange/",
        status_code=408,
    )
    client = MatterClient()
    result = client.exchange_token("session_123")
    assert result is None


def test_fetch_updates_feed(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/library_items/updates_feed/",
        json={"feed": [SAMPLE_FEED_ENTRY], "next": None},
    )
    client = MatterClient(access_token="test_token")
    entries = client.fetch_all_articles()
    assert len(entries) == 1
    assert entries[0]["id"] == "entry1"


def test_fetch_updates_feed_pagination(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/library_items/updates_feed/",
        json={
            "feed": [SAMPLE_FEED_ENTRY],
            "next": "https://api.getmatter.app/api/v11/library_items/updates_feed/?page=2",
        },
    )
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/library_items/updates_feed/?page=2",
        json={"feed": [SAMPLE_DELETED_ENTRY], "next": None},
    )
    client = MatterClient(access_token="test_token")
    entries = client.fetch_all_articles()
    assert len(entries) == 2


def test_refresh_token(httpx_mock):
    httpx_mock.add_response(
        url="https://api.getmatter.app/api/v11/token/refresh/",
        json={"access_token": "new_acc", "refresh_token": "new_ref"},
    )
    client = MatterClient(access_token="old", refresh_token="old_ref")
    result = client.refresh_access_token()
    assert result["access_token"] == "new_acc"
    assert client.access_token == "new_acc"
    assert client.refresh_token == "new_ref"
