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
    return TestClient(create_app())


def test_root_json():
    r = TestClient(create_app()).get("/")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/json")
    body = r.json()
    assert body["service"] == "matter-hub-api"


def test_cors_default_allows_tailscale_style_vite_origin():
    """既定の allow_origin_regex で LAN / Tailscale の IP:5173 を許可する。"""
    c = TestClient(create_app())
    origin = "http://100.79.172.93:5173"
    r = c.get("/api/sync", headers={"Origin": origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == origin


def test_cors_strict_without_regex_does_not_add_acao_for_unknown_origin(monkeypatch):
    monkeypatch.setenv("MATTER_HUB_CORS_STRICT", "1")
    monkeypatch.delenv("MATTER_HUB_CORS_ORIGIN_REGEX", raising=False)
    c = TestClient(create_app())
    origin = "http://100.79.172.93:5173"
    r = c.get("/api/sync", headers={"Origin": origin})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") in (None, "")


def test_bootstrap_title_ja_when_set(tmp_path, monkeypatch):
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
    r = TestClient(create_app()).get("/api/bootstrap")
    assert r.status_code == 200
    titles = [a.get("title_ja") or a.get("title") for a in r.json()["articles"]]
    assert "こんにちは世界" in titles
    assert "Hello World" not in titles


def test_bootstrap_summary_closed_by_default(tmp_path, monkeypatch):
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

    r = TestClient(create_app()).get("/api/bootstrap")
    assert r.status_code == 200
    a1 = r.json()["articles"][0]
    assert a1["summary"] == "初期表示では見えない要約"
    # 一覧 JSON には要約全文を載せない方針でもよいが、DB の列がそのまま返る
    assert "初期表示では見えない要約" in (a1.get("summary") or "")


def _seed_many(db_path):
    db = Database(db_path)
    for i, (title, tags, ls) in enumerate([
        ("Python basics", ["Python"], 0),
        ("Rust ownership", ["Rust"], 0),
        ("Python + AI", ["Python", "AI"], 0),
        ("Archived one", ["Python"], 2),
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


def test_api_articles_filters_by_view(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/api/articles?view=active")
    assert r.status_code == 200
    titles = [a["title"] for a in r.json()["articles"]]
    assert "Python basics" in titles
    assert "Archived one" not in titles


def test_api_articles_tags_and(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/api/articles?view=active&tags=Python,AI")
    titles = [a["title"] for a in r.json()["articles"]]
    assert "Python + AI" in titles
    assert "Python basics" not in titles


def test_api_articles_search(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/api/articles?view=active&q=Rust")
    titles = [a["title"] for a in r.json()["articles"]]
    assert "Rust ownership" in titles
    assert "Python basics" not in titles


def test_api_articles_orders_by_queue_order(tmp_path, monkeypatch):
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
    r = c.get("/api/articles?view=active")
    assert r.status_code == 200
    titles = [a["title"] for a in r.json()["articles"]]
    assert titles.index("Newer Article") < titles.index("Older Article")


def test_api_tags_active_view(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/api/tags?view=active")
    assert r.status_code == 200
    names = [t["name"] for t in r.json()["tags"]]
    assert "Python" in names
    assert "Rust" in names


def test_api_delete_soft_deletes(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/a0/delete")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    db = Database(db_path)
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='a0'").fetchone()
    assert row["deleted"] == 1
    db.close()


def test_api_delete_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/missing/delete")
    assert r.status_code == 404


def test_api_restore_clears_deleted_flag(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    db = Database(db_path)
    db.set_deleted("a0", True)
    db.close()
    c = TestClient(create_app())
    r = c.post("/api/articles/a0/restore")
    assert r.status_code == 200
    db = Database(db_path)
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='a0'").fetchone()
    assert row["deleted"] == 0
    db.close()


def test_api_restore_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/missing/restore")
    assert r.status_code == 404


def test_api_archive_sets_library_state_archived(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/a0/archive")
    assert r.status_code == 200
    assert r.json() == {"ok": True}
    db = Database(db_path)
    row = db.conn.execute("SELECT library_state FROM articles WHERE id='a0'").fetchone()
    assert row["library_state"] == 2
    db.close()


def test_api_archive_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/missing/archive")
    assert r.status_code == 404


def test_api_unarchive_restores_library_state(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    db = Database(db_path)
    db.set_library_state("a0", 2)
    db.close()
    c = TestClient(create_app())
    r = c.post("/api/articles/a0/unarchive")
    assert r.status_code == 200
    db = Database(db_path)
    row = db.conn.execute("SELECT library_state FROM articles WHERE id='a0'").fetchone()
    assert row["library_state"] == 1
    db.close()


def test_api_unarchive_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/missing/unarchive")
    assert r.status_code == 404


def test_api_bootstrap_respects_view_param(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/api/bootstrap?view=archived")
    assert r.status_code == 200
    titles = [a["title"] for a in r.json()["articles"]]
    assert "Archived one" in titles
    assert "Python basics" not in titles


def test_api_bootstrap_respects_tags_param(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/api/bootstrap?tags=Python,AI")
    titles = [a["title"] for a in r.json()["articles"]]
    assert "Python + AI" in titles
    assert "Rust ownership" not in titles


def test_api_get_article_summary(tmp_path, monkeypatch):
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
    r = c.get("/api/articles/a1/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["summary_open"] is True
    assert body["article"]["summary"] == "要約済みです"
    assert body["article"]["summary_model"] == "gemma3:4b"


def test_api_post_article_summary_close_success(tmp_path, monkeypatch):
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
    r = c.post("/api/articles/a1/summary/close")
    assert r.status_code == 200
    body = r.json()
    assert body["summary_open"] is False
    assert body["article"]["summary"] == "要約済みです"


def test_api_post_article_summary_close_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/missing/summary/close")
    assert r.status_code == 404


def test_api_post_article_summarize_success(tmp_path, monkeypatch):
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
    r = c.post("/api/articles/a1/summarize")
    assert r.status_code == 200
    start = r.json()
    assert start["outcome"] == "started"
    assert start["job"]["status"] == "running"

    final = None
    for _ in range(200):
        final = c.get("/api/articles/a1/summarize/status").json()
        if final.get("summary_panel") and final["summary_panel"]["article"].get("summary") == "生成された要約":
            break
        time.sleep(0.02)
    assert final is not None
    assert final["summary_panel"]["summary_open"] is True
    assert "生成された要約" in final["summary_panel"]["article"]["summary"]

    db = Database(db_path)
    row = db.conn.execute(
        "SELECT summary, summary_model, summary_source_url FROM articles WHERE id='a1'"
    ).fetchone()
    assert row["summary"] == "生成された要約"
    assert row["summary_model"] == "gemma3:4b"
    assert row["summary_source_url"] == "https://e.com/a1"
    db.close()


def test_api_post_article_resummarize_overwrites_existing(tmp_path, monkeypatch):
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
    r = c.post("/api/articles/a1/summarize")
    assert r.status_code == 200
    assert r.json()["outcome"] == "started"

    final = None
    for _ in range(200):
        final = c.get("/api/articles/a1/summarize/status").json()
        sp = final.get("summary_panel")
        if sp and sp["article"].get("summary") == "新しい要約":
            break
        time.sleep(0.02)
    assert final is not None
    assert final["summary_panel"]["article"]["summary"] == "新しい要約"

    db = Database(db_path)
    row = db.conn.execute("SELECT summary FROM articles WHERE id='a1'").fetchone()
    assert row["summary"] == "新しい要約"
    db.close()


def test_api_post_article_summarize_ollama_unavailable(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    monkeypatch.setattr("matter_hub.webapp.summarize_runner.ensure_ollama_noninteractive", lambda **_kwargs: False)

    c = TestClient(create_app())
    r = c.post("/api/articles/a0/summarize")
    assert r.status_code == 200
    assert r.json()["outcome"] == "started"

    final = None
    for _ in range(200):
        final = c.get("/api/articles/a0/summarize/status").json()
        sp = final.get("summary_panel")
        if sp and sp.get("error") and "Ollamaに接続できません" in sp["error"]:
            break
        time.sleep(0.02)
    assert final is not None
    assert "Ollamaに接続できません" in final["summary_panel"]["error"]


def test_api_post_article_summarize_unknown_returns_404(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.post("/api/articles/missing/summarize")
    assert r.status_code == 404


def test_api_bootstrap_x_article_summarize_disabled_without_bearer(tmp_path, monkeypatch):
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

    r = TestClient(create_app()).get("/api/bootstrap")
    assert r.status_code == 200
    x1 = next(a for a in r.json()["articles"] if a["id"] == "x1")
    assert x1["x_summarize_disabled"] is True


def test_api_bootstrap_x_article_summarize_enabled_with_bearer(tmp_path, monkeypatch):
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

    r = TestClient(create_app()).get("/api/bootstrap")
    x1 = next(a for a in r.json()["articles"] if a["id"] == "x1")
    assert x1["x_summarize_disabled"] is False


def test_api_bootstrap_x_url_matter_source_summarize_disabled_without_bearer(tmp_path, monkeypatch):
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

    r = TestClient(create_app()).get("/api/bootstrap")
    m1 = next(a for a in r.json()["articles"] if a["id"] == "m1")
    assert m1["x_summarize_disabled"] is True


def test_api_post_article_summarize_x_without_bearer_returns_error(tmp_path, monkeypatch):
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
    r = c.post("/api/articles/x1/summarize")
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "config_error"
    assert "環境変数が未登録のため要約生成は使用できません" in body["panel"]["error"]


def test_api_sync_get_returns_snapshot(client):
    r = client.get("/api/sync")
    assert r.status_code == 200
    data = r.json()
    assert "status" in data
    assert data["status"] in ("idle", "running", "ok", "error")
