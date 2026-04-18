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
