import numpy as np

from matter_hub.db import Database


def test_init_creates_tables(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1",
        "title": "Test Article",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 1,
    })
    articles = db.search("")
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article"
    db.close()


def test_upsert_article_updates_existing(tmp_path):
    db = Database(tmp_path / "test.db")
    article = {
        "id": "art1",
        "title": "Original",
        "url": "https://example.com",
        "author": None,
        "publisher": None,
        "published_date": None,
        "note": None,
        "library_state": 1,
    }
    db.upsert_article(article)
    article["title"] = "Updated"
    db.upsert_article(article)
    articles = db.list_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Updated"
    db.close()


def test_add_and_query_tags(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "matter")
    db.add_tag("art1", "Python", "ai")
    tags = db.get_tags("art1")
    assert len(tags) == 2
    assert {"name": "AI", "source": "matter"} in tags
    db.close()


def test_add_and_query_highlights(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_highlight("art1", "important text", "my note", "2025-01-01")
    highlights = db.get_highlights("art1")
    assert len(highlights) == 1
    assert highlights[0]["text"] == "important text"
    db.close()


def test_fts_search(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Machine Learning Guide",
        "url": "https://example.com", "author": "Alice",
        "publisher": "TechBlog", "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "Cooking Recipes",
        "url": "https://example.com/cook", "author": "Bob",
        "publisher": "FoodBlog", "published_date": None,
        "note": None, "library_state": 1,
    })
    results = db.search("Machine")
    assert len(results) == 1
    assert results[0]["id"] == "art1"
    db.close()


def test_search_by_tag(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Article 1", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "Article 2", "url": "https://example.com/2",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    results = db.search_by_tag("AI")
    assert len(results) == 1
    assert results[0]["id"] == "art1"
    db.close()


def test_list_all_tags_with_counts(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "A1", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "A2", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    db.add_tag("art2", "AI", "ai")
    db.add_tag("art1", "Python", "ai")
    tag_counts = db.list_tags()
    assert tag_counts == [("AI", 2), ("Python", 1)]
    db.close()


def test_remove_tag(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    db.remove_tag("art1", "AI")
    tags = db.get_tags("art1")
    assert len(tags) == 0
    db.close()


def test_articles_without_ai_tags(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Tagged", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "Untagged", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    untagged = db.articles_without_ai_tags()
    assert len(untagged) == 1
    assert untagged[0]["id"] == "art2"
    db.close()


def test_stats(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "A1", "url": "https://a.com",
        "author": "Alice", "publisher": "TechBlog",
        "published_date": "2025-01-15", "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "A2", "url": "https://b.com",
        "author": "Alice", "publisher": "FoodBlog",
        "published_date": "2025-02-10", "note": None, "library_state": 1,
    })
    db.add_tag("art1", "AI", "ai")
    db.add_tag("art2", "AI", "ai")
    stats = db.get_stats()
    assert stats["total_articles"] == 2
    assert stats["total_tags"] == 1
    assert ("Alice", 2) in stats["top_authors"]
    db.close()


def test_save_and_get_embedding(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Test", "url": "https://example.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    embedding = np.random.rand(768).astype(np.float32)
    db.save_embedding("art1", embedding.tobytes())
    result = db.get_embedding("art1")
    assert result is not None
    recovered = np.frombuffer(result, dtype=np.float32)
    np.testing.assert_array_almost_equal(embedding, recovered)
    db.close()


def test_articles_without_embedding(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "Has embedding", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "No embedding", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    embedding = np.random.rand(768).astype(np.float32)
    db.save_embedding("art1", embedding.tobytes())
    without = db.articles_without_embedding()
    assert len(without) == 1
    assert without[0]["id"] == "art2"
    db.close()


def test_get_all_embeddings(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "A1", "url": "https://a.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    db.upsert_article({
        "id": "art2", "title": "A2", "url": "https://b.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 1,
    })
    emb1 = np.random.rand(768).astype(np.float32)
    emb2 = np.random.rand(768).astype(np.float32)
    db.save_embedding("art1", emb1.tobytes())
    db.save_embedding("art2", emb2.tobytes())
    results = db.get_all_embeddings()
    assert len(results) == 2
    assert results[0]["id"] in ("art1", "art2")
    assert len(np.frombuffer(results[0]["embedding"], dtype=np.float32)) == 768
    db.close()


def test_deleted_column_added(tmp_path):
    db = Database(tmp_path / "test.db")
    cols = [r[1] for r in db.conn.execute("PRAGMA table_info(articles)").fetchall()]
    assert "deleted" in cols
    db.close()


def test_deleted_column_default_zero(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "T", "url": "https://e.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 0,
    })
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='art1'").fetchone()
    assert row["deleted"] == 0
    db.close()


def test_wal_mode_enabled(tmp_path):
    db = Database(tmp_path / "test.db")
    mode = db.conn.execute("PRAGMA journal_mode").fetchone()[0]
    assert mode.lower() == "wal"
    db.close()


def test_migration_idempotent_when_deleted_exists(tmp_path):
    db_path = tmp_path / "test.db"
    db1 = Database(db_path)
    db1.close()
    db2 = Database(db_path)
    cols = [r[1] for r in db2.conn.execute("PRAGMA table_info(articles)").fetchall()]
    assert cols.count("deleted") == 1
    db2.close()
