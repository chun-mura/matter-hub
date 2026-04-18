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


def _seed_many(db_path):
    db = Database(db_path)
    for i, (title, tags, ls) in enumerate([
        ("Python basics",  ["Python"],         0),
        ("Rust ownership", ["Rust"],           0),
        ("Python + AI",    ["Python", "AI"],   0),
        ("Archived one",   ["Python"],         1),
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


def test_tags_partial_active_view(tmp_path, monkeypatch):
    db_path = tmp_path / "web.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(db_path))
    _seed_many(db_path)
    c = TestClient(create_app())
    r = c.get("/tags?view=active")
    assert r.status_code == 200
    assert "Python" in r.text
    assert "Rust" in r.text
