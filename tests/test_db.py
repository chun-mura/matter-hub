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


def test_set_deleted_flips_flag(tmp_path):
    db = Database(tmp_path / "test.db")
    db.upsert_article({
        "id": "art1", "title": "T", "url": "https://e.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 0,
    })
    assert db.set_deleted("art1", True) is True
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='art1'").fetchone()
    assert row["deleted"] == 1
    assert db.set_deleted("art1", False) is True
    row = db.conn.execute("SELECT deleted FROM articles WHERE id='art1'").fetchone()
    assert row["deleted"] == 0
    db.close()


def test_set_deleted_unknown_id_returns_false(tmp_path):
    db = Database(tmp_path / "test.db")
    assert db.set_deleted("missing", True) is False
    db.close()


def _seed(db):
    samples = [
        # (id, title, library_state, deleted, tags)
        ("a1", "Python basics",  0, 0, ["Python"]),
        ("a2", "Rust ownership",  0, 0, ["Rust"]),
        ("a3", "Python + AI",     0, 0, ["Python", "AI"]),
        ("a4", "Old archived",    1, 0, ["Python"]),
        ("a5", "Trashed item",    0, 1, ["Python"]),
    ]
    for aid, title, ls, deleted, tags in samples:
        db.upsert_article({
            "id": aid, "title": title, "url": f"https://e.com/{aid}",
            "author": None, "publisher": None, "published_date": None,
            "note": None, "library_state": ls,
        })
        if deleted:
            db.set_deleted(aid, True)
        for t in tags:
            db.add_tag(aid, t, "matter")


def test_list_filtered_active_default(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, total = db.list_articles_filtered(q=None, tags=[], view="active", limit=50, offset=0)
    ids = {r["id"] for r in rows}
    assert ids == {"a1", "a2", "a3"}
    assert total == 3
    db.close()


def test_list_filtered_archived_view(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, total = db.list_articles_filtered(q=None, tags=[], view="archived", limit=50, offset=0)
    assert {r["id"] for r in rows} == {"a4"}
    assert total == 1
    db.close()


def test_list_filtered_trash_view(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, total = db.list_articles_filtered(q=None, tags=[], view="trash", limit=50, offset=0)
    assert {r["id"] for r in rows} == {"a5"}
    assert total == 1
    db.close()


def test_list_filtered_tags_and_semantics(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, _ = db.list_articles_filtered(q=None, tags=["Python", "AI"], view="active", limit=50, offset=0)
    assert {r["id"] for r in rows} == {"a3"}
    db.close()


def test_list_filtered_query_fts(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, _ = db.list_articles_filtered(q="Rust", tags=[], view="active", limit=50, offset=0)
    assert {r["id"] for r in rows} == {"a2"}
    db.close()


def test_list_filtered_pagination(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, total = db.list_articles_filtered(q=None, tags=[], view="active", limit=2, offset=0)
    assert len(rows) == 2
    assert total == 3
    rows2, _ = db.list_articles_filtered(q=None, tags=[], view="active", limit=2, offset=2)
    assert len(rows2) == 1
    db.close()


def test_list_filtered_query_and_tags_combined(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    rows, total = db.list_articles_filtered(
        q="Python", tags=["AI"], view="active", limit=50, offset=0
    )
    assert {r["id"] for r in rows} == {"a3"}
    assert total == 1
    db.close()


def test_active_view_includes_null_and_queue_state(tmp_path):
    db = Database(tmp_path / "t.db")
    # Matter emits library_state in {None, 1, 2} for synced items. Only state=1 is archived.
    samples = [
        ("null_item",  None),
        ("zero_item",  0),
        ("queue_item", 2),
        ("archive",    1),
    ]
    for aid, ls in samples:
        db.upsert_article({
            "id": aid, "title": aid, "url": f"https://e.com/{aid}",
            "author": None, "publisher": None, "published_date": None,
            "note": None, "library_state": ls,
        })
    active, _ = db.list_articles_filtered(q=None, tags=[], view="active", limit=50, offset=0)
    archived, _ = db.list_articles_filtered(q=None, tags=[], view="archived", limit=50, offset=0)
    assert {r["id"] for r in active} == {"null_item", "zero_item", "queue_item"}
    assert {r["id"] for r in archived} == {"archive"}
    db.close()


def test_list_tags_filtered_active(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    tags = db.list_tags_filtered(view="active")
    as_dict = dict(tags)
    assert as_dict["Python"] == 2    # a1, a3
    assert as_dict["AI"] == 1        # a3
    assert as_dict["Rust"] == 1      # a2
    assert "Python" in as_dict       # a4 archived excluded, a5 trash excluded
    db.close()


def test_list_tags_filtered_archived(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    tags = db.list_tags_filtered(view="archived")
    assert dict(tags) == {"Python": 1}  # only a4
    db.close()


def test_list_tags_filtered_trash(tmp_path):
    db = Database(tmp_path / "t.db")
    _seed(db)
    tags = db.list_tags_filtered(view="trash")
    assert dict(tags) == {"Python": 1}  # only a5
    db.close()


def test_is_deleted(tmp_path):
    db = Database(tmp_path / "t.db")
    db.upsert_article({
        "id": "art1", "title": "T", "url": "https://e.com",
        "author": None, "publisher": None, "published_date": None,
        "note": None, "library_state": 0,
    })
    assert db.is_deleted("art1") is False
    db.set_deleted("art1", True)
    assert db.is_deleted("art1") is True
    assert db.is_deleted("missing") is False
    db.close()
