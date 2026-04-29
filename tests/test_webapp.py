import time

import pytest
from fastapi.testclient import TestClient

from matter_hub.db import Database
from matter_hub.webapp.main import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Hello World", "url": "https://e.com/a1",
        "author": "Alice", "publisher": "Blog", "published_date": "2025-01-01",
        "note": None, "library_state": 0,
    })
    db.add_tag("a1", "AI", "matter")
    db.close()
    app = create_app()
    return TestClient(app)


def test_index_returns_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Matter Hub" in r.text
    assert "要約生成" in r.text
    assert "生成中..." in r.text
    assert "summary-spinner" in r.text
    assert "resummarize-confirm-modal" in r.text
    assert "画面上の既存の要約" in r.text
    assert "再要約を開始" in r.text


def test_index_shows_title_ja_when_set(tmp_path, monkeypatch):
    db_path = tmp_path / "web2.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1",
        "title": "Hello World",
        "url": "https://e.com/a1",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 0,
    })
    db.update_title_translation("a1", "こんにちは世界", "Hello World")
    db.close()
    r = TestClient(create_app()).get("/")
    assert r.status_code == 200
    assert "こんにちは世界" in r.text
    assert "Hello World" not in r.text


def test_index_keeps_summary_closed_by_default(tmp_path, monkeypatch):
    db_path = tmp_path / "web_summary_closed.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1",
        "title": "Has Summary",
        "url": "https://e.com/a1",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 0,
    })
    db.update_article_summary("a1", "初期表示では見えない要約", "gemma3:4b", "https://e.com/a1")
    db.close()

    r = TestClient(create_app()).get("/")
    assert r.status_code == 200
    assert "要約を見る" in r.text
    assert "再要約" in r.text
    assert "要約を閉じる" not in r.text
    assert "初期表示では見えない要約" not in r.text


def _seed_many(db_path):
    db = Database(db_path)
    for i, (title, tags, ls) in enumerate([
        ("Python basics",  ["Python"],         0),
        ("Rust ownership", ["Rust"],           0),
        ("Python + AI",    ["Python", "AI"],   0),
        ("Archived one",   ["Python"],         2),
    ]):
        aid = f"a{i}"
        db.upsert_article({
            "id": aid, "title": title, "url": f"https://e.com/{aid}",
            "author": None, "publisher": None, "published_date": None,
            "note": None, "library_state": ls,
        })
        for t in tags:
            db.add_tag(aid, t, "matter")
    db.close()


def test_articles_partial_filters_by_view(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    app = create_app()
    c = TestClient(app)
    r = c.get("/articles?view=active")
    assert r.status_code == 200
    assert "Python basics" in r.text
    assert "Archived one" not in r.text


def test_articles_partial_tags_and(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/articles?view=active&tags=Python,AI")
    assert "Python + AI" in r.text
    assert "Python basics" not in r.text


def test_articles_partial_search(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/articles?view=active&q=Rust")
    assert "Rust ownership" in r.text
    assert "Python basics" not in r.text


def test_articles_partial_orders_by_queue_order(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "older",
        "title": "Older Article",
        "url": "https://e.com/older",
        "author": None,
        "publisher": None,
        "published_date": "2026-04-20",
        "note": None,
        "library_state": 0,
        "queue_order": 10,
    })
    db.upsert_article({
        "id": "newer",
        "title": "Newer Article",
        "url": "https://e.com/newer",
        "author": None,
        "publisher": None,
        "published_date": "2020-01-01",
        "note": None,
        "library_state": 0,
        "queue_order": 20,
    })
    db.close()

    c = TestClient(create_app())
    r = c.get("/articles?view=active")
    assert r.status_code == 200
    assert r.text.index("Newer Article") < r.text.index("Older Article")


def test_tags_partial_active_view(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/tags?view=active")
    assert r.status_code == 200
    assert "Python" in r.text
    assert "Rust" in r.text


def test_delete_soft_deletes_and_returns_empty(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/a0/delete")
    assert r.status_code == 200
    assert r.text.strip() == ""
    db = Database(db_path)
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='a0'").fetchone()
    assert row["deleted"] == 1
    db.close()


def test_delete_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/missing/delete")
    assert r.status_code == 404


def test_restore_clears_deleted_flag(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    db = Database(db_path)
    db.set_deleted("a0", True)
    db.close()
    c = TestClient(create_app())
    r = c.post("/articles/a0/restore")
    assert r.status_code == 200
    db = Database(db_path)
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='a0'").fetchone()
    assert row["deleted"] == 0
    db.close()


def test_restore_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/missing/restore")
    assert r.status_code == 404


def test_archive_sets_library_state_archived(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/a0/archive")
    assert r.status_code == 200
    assert r.text.strip() == ""
    db = Database(db_path)
    row = db.conn.execute("SELECT library_state FROM articles WHERE id='a0'").fetchone()
    assert row["library_state"] == 2
    db.close()


def test_archive_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/missing/archive")
    assert r.status_code == 404


def test_unarchive_restores_library_state(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    db = Database(db_path)
    db.set_library_state("a0", 2)
    db.close()
    c = TestClient(create_app())
    r = c.post("/articles/a0/unarchive")
    assert r.status_code == 200
    db = Database(db_path)
    row = db.conn.execute("SELECT library_state FROM articles WHERE id='a0'").fetchone()
    assert row["library_state"] == 1
    db.close()


def test_unarchive_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/missing/unarchive")
    assert r.status_code == 404


def test_index_respects_view_param(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/?view=archived")
    assert r.status_code == 200
    assert "Archived one" in r.text
    assert "Python basics" not in r.text


def test_index_respects_tags_param(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/?tags=Python,AI")
    assert "Python + AI" in r.text
    assert "Rust ownership" not in r.text


def test_get_article_summary_partial(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Has Summary", "url": "https://e.com/a1",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 0,
    })
    db.update_article_summary("a1", "要約済みです", "gemma3:4b", "https://e.com/a1")
    db.close()

    c = TestClient(create_app())
    r = c.get("/articles/a1/summary")
    assert r.status_code == 200
    assert "要約済みです" in r.text
    assert "gemma3:4b" in r.text
    assert "要約を閉じる" in r.text
    assert "再要約" in r.text
    assert 'class="summary-resummarize-trigger' in r.text
    assert 'data-article-id="a1"' in r.text


def test_post_article_summary_close_success(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Has Summary", "url": "https://e.com/a1",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 0,
    })
    db.update_article_summary("a1", "要約済みです", "gemma3:4b", "https://e.com/a1")
    db.close()

    c = TestClient(create_app())
    r = c.post("/articles/a1/summary/close")
    assert r.status_code == 200
    assert "要約済みです" not in r.text
    assert "要約を見る" in r.text
    assert "再要約" in r.text


def test_post_article_summary_close_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/missing/summary/close")
    assert r.status_code == 404


def test_post_article_summarize_success(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Need Summary", "url": "https://e.com/a1",
        "author": None, "publisher": None, "published_date": None,
        "note": "fallback", "library_state": 0,
    })
    db.close()

    monkeypatch.setattr("matter_hub.webapp.summarize_runner.ensure_ollama_noninteractive", lambda **_kwargs: True)
    monkeypatch.setattr(
        "matter_hub.webapp.summarize_runner.fetch_article_content_text", lambda *_args, **_kwargs: "本文"
    )
    monkeypatch.setattr(
        "matter_hub.webapp.summarize_runner.summarize_article_ollama", lambda *_args, **_kwargs: "生成された要約"
    )

    c = TestClient(create_app())
    r = c.post("/articles/a1/summarize")
    assert r.status_code == 200
    assert "summarize-progress-a1" in r.text
    assert "/articles/a1/summarize/status" in r.text

    final = None
    for _ in range(200):
        final = c.get("/articles/a1/summarize/status")
        if "生成された要約" in final.text and "要約を閉じる" in final.text:
            break
        time.sleep(0.02)
    assert final is not None
    assert "生成された要約" in final.text
    assert "要約を閉じる" in final.text

    db = Database(db_path)
    row = db.conn.execute(
        "SELECT summary, summary_model, summary_source_url FROM articles WHERE id='a1'"
    ).fetchone()
    assert row["summary"] == "生成された要約"
    assert row["summary_model"] == "gemma3:4b"
    assert row["summary_source_url"] == "https://e.com/a1"
    db.close()


def test_post_article_resummarize_overwrites_existing(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Has Old Summary", "url": "https://e.com/a1",
        "author": None, "publisher": None, "published_date": None,
        "note": "fallback", "library_state": 0,
    })
    db.update_article_summary("a1", "古い要約", "gemma3:4b", "https://e.com/a1")
    db.close()

    monkeypatch.setattr("matter_hub.webapp.summarize_runner.ensure_ollama_noninteractive", lambda **_kwargs: True)
    monkeypatch.setattr(
        "matter_hub.webapp.summarize_runner.fetch_article_content_text", lambda *_args, **_kwargs: "本文"
    )
    monkeypatch.setattr(
        "matter_hub.webapp.summarize_runner.summarize_article_ollama", lambda *_args, **_kwargs: "新しい要約"
    )

    c = TestClient(create_app())
    r = c.post("/articles/a1/summarize")
    assert r.status_code == 200
    assert "summarize-progress-a1" in r.text

    final = None
    for _ in range(200):
        final = c.get("/articles/a1/summarize/status")
        if "新しい要約" in final.text:
            break
        time.sleep(0.02)
    assert final is not None
    assert "新しい要約" in final.text
    assert "古い要約" not in final.text

    db = Database(db_path)
    row = db.conn.execute("SELECT summary FROM articles WHERE id='a1'").fetchone()
    assert row["summary"] == "新しい要約"
    db.close()


def test_post_article_summarize_ollama_unavailable(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    monkeypatch.setattr("matter_hub.webapp.summarize_runner.ensure_ollama_noninteractive", lambda **_kwargs: False)

    c = TestClient(create_app())
    r = c.post("/articles/a0/summarize")
    assert r.status_code == 200
    assert "summarize-progress-a0" in r.text

    final = None
    for _ in range(200):
        final = c.get("/articles/a0/summarize/status")
        if "Ollamaに接続できません" in final.text:
            break
        time.sleep(0.02)
    assert final is not None
    assert "Ollamaに接続できません" in final.text


def test_post_article_summarize_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/articles/missing/summarize")
    assert r.status_code == 404


def test_index_x_article_summarize_disabled_without_bearer(tmp_path, monkeypatch):
    db_path = tmp_path / "web_x_no_bearer.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    db = Database(db_path)
    db.upsert_article({
        "id": "x1",
        "title": "X post body",
        "url": "https://x.com/user/status/1",
        "author": None,
        "publisher": "x.com",
        "published_date": None,
        "note": None,
        "library_state": 0,
        "source": "x",
    })
    db.close()

    r = TestClient(create_app()).get("/")
    assert r.status_code == 200
    assert "環境変数が未登録のため使用できません" in r.text
    assert 'aria-disabled="true"' in r.text


def test_index_x_article_summarize_enabled_with_bearer(tmp_path, monkeypatch):
    db_path = tmp_path / "web_x_bearer.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    monkeypatch.setenv("X_BEARER_TOKEN", "test-token")
    db = Database(db_path)
    db.upsert_article({
        "id": "x1",
        "title": "X post body",
        "url": "https://x.com/user/status/1",
        "author": None,
        "publisher": "x.com",
        "published_date": None,
        "note": None,
        "library_state": 0,
        "source": "x",
    })
    db.close()

    r = TestClient(create_app()).get("/")
    assert r.status_code == 200
    assert 'hx-post="/articles/x1/summarize"' in r.text
    assert "環境変数が未登録のため使用できません" not in r.text


def test_index_x_url_matter_source_summarize_disabled_without_bearer(tmp_path, monkeypatch):
    """Matter 同期などで source が matter のままの X URL でも要約生成はロックする。"""
    db_path = tmp_path / "web_xurl_matter.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    db = Database(db_path)
    db.upsert_article({
        "id": "m1",
        "title": "Synced tweet title",
        "url": "https://x.com/user/status/999",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 0,
        "source": "matter",
    })
    db.close()

    r = TestClient(create_app()).get("/")
    assert r.status_code == 200
    assert "環境変数が未登録のため使用できません" in r.text
    assert 'aria-disabled="true"' in r.text


def test_post_article_summarize_x_without_bearer_returns_error(tmp_path, monkeypatch):
    db_path = tmp_path / "web_x_summarize_block.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    db = Database(db_path)
    db.upsert_article({
        "id": "x1",
        "title": "X post",
        "url": "https://x.com/user/status/1",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": "n",
        "library_state": 0,
        "source": "matter",
    })
    db.close()

    c = TestClient(create_app())
    r = c.post("/articles/x1/summarize")
    assert r.status_code == 200
    assert "環境変数が未登録のため要約生成は使用できません" in r.text
