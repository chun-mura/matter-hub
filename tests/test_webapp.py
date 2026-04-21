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
