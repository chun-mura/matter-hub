# tests/test_cli.py
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from matter_hub.cli import cli
from matter_hub.db import Database


def test_auth_displays_qr_and_saves_token():
    runner = CliRunner()
    mock_client = MagicMock()
    mock_client.trigger_qr_login.return_value = "session_123"
    mock_client.exchange_token.side_effect = [None, {"access_token": "acc", "refresh_token": "ref"}]

    with patch("matter_hub.cli.MatterClient", return_value=mock_client), \
         patch("matter_hub.cli.save_config") as mock_save, \
         patch("matter_hub.cli.qrcode") as mock_qr, \
         patch("matter_hub.cli.time") as mock_time:
        result = runner.invoke(cli, ["auth"])

    assert result.exit_code == 0
    assert "認証成功" in result.output
    mock_save.assert_called_once()


def test_sync_fetches_and_stores_articles(tmp_path):
    runner = CliRunner()

    sample_entry = {
        "id": "art1",
        "content": {
            "title": "Test Article",
            "url": "https://example.com",
            "author": {"any_name": "Alice"},
            "publisher": {"any_name": "Tech"},
            "publication_date": "2025-01-01",
            "tags": [{"name": "tech", "created_date": "2025-01-01"}],
            "my_annotations": [{"text": "highlight", "note": None, "created_date": "2025-01-02", "word_start": 0, "word_end": 5}],
            "my_note": {"note": "a note"},
            "library": {"library_state": 1},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [sample_entry]

    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["sync"])

    assert result.exit_code == 0
    assert "1 件の記事を同期しました" in result.output

    db = Database(db_path)
    articles = db.list_articles()
    assert len(articles) == 1
    assert articles[0]["title"] == "Test Article"
    tags = db.get_tags("art1")
    assert len(tags) == 1
    highlights = db.get_highlights("art1")
    assert len(highlights) == 1
    db.close()


def test_sync_skips_deleted_articles(tmp_path):
    runner = CliRunner()

    deleted_entry = {
        "id": "art_del",
        "content": {
            "title": "Deleted",
            "url": "https://example.com/del",
            "author": None,
            "publisher": None,
            "publication_date": None,
            "tags": [],
            "my_annotations": [],
            "my_note": None,
            "library": {"library_state": 3},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [deleted_entry]

    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["sync"])

    assert result.exit_code == 0
    db = Database(db_path)
    articles = db.list_articles()
    assert len(articles) == 0
    db.close()


def _seed_db(db_path):
    """Helper to create a seeded DB for CLI tests."""
    db = Database(db_path)
    db.upsert_article({
        "id": "a1", "title": "Machine Learning入門", "url": "https://ml.example.com",
        "author": "Alice", "publisher": "TechBlog",
        "published_date": "2025-01-15", "note": "good article", "library_state": 1,
    })
    db.upsert_article({
        "id": "a2", "title": "料理レシピ集", "url": "https://cook.example.com",
        "author": "Bob", "publisher": "FoodBlog",
        "published_date": "2025-02-10", "note": None, "library_state": 1,
    })
    db.add_tag("a1", "AI", "ai")
    db.add_tag("a1", "機械学習", "ai")
    db.add_tag("a2", "料理", "ai")
    db.add_highlight("a1", "transformers are powerful", "note1", "2025-01-16")
    db.close()
    return db_path


def test_search_keyword(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["search", "Machine"])
    assert result.exit_code == 0
    assert "Machine Learning入門" in result.output
    assert "料理レシピ集" not in result.output


def test_search_by_tag_flag(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["search", "--tag", "AI"])
    assert result.exit_code == 0
    assert "Machine Learning入門" in result.output


def test_list_default(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["list"])
    assert result.exit_code == 0
    assert "Machine Learning入門" in result.output
    assert "料理レシピ集" in result.output


def test_list_json_output(tmp_path):
    import json as json_mod
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["list", "--json"])
    assert result.exit_code == 0
    data = json_mod.loads(result.output)
    assert len(data) == 2


def test_tags_list(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["tags"])
    assert result.exit_code == 0
    assert "AI" in result.output


def test_tag_add(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["tag", "add", "a2", "健康"])
    assert result.exit_code == 0
    db = Database(db_path)
    tags = db.get_tags("a2")
    assert any(t["name"] == "健康" for t in tags)
    db.close()


def test_tag_remove(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["tag", "remove", "a1", "AI"])
    assert result.exit_code == 0
    db = Database(db_path)
    tags = db.get_tags("a1")
    assert not any(t["name"] == "AI" for t in tags)
    db.close()


def test_stats(tmp_path):
    runner = CliRunner()
    db_path = _seed_db(tmp_path / "test.db")
    with patch("matter_hub.cli.get_db_path", return_value=db_path):
        result = runner.invoke(cli, ["stats"])
    assert result.exit_code == 0
    assert "2" in result.output
    assert "Alice" in result.output


def test_full_workflow(tmp_path):
    """Integration test: sync → search → tag → stats"""
    runner = CliRunner()

    sample_entry = {
        "id": "int1",
        "content": {
            "title": "LLM入門ガイド",
            "url": "https://example.com/llm",
            "author": {"any_name": "太郎"},
            "publisher": {"any_name": "AI Weekly"},
            "publication_date": "2025-03-01",
            "tags": [{"name": "AI", "created_date": "2025-03-01"}],
            "my_annotations": [],
            "my_note": {"note": "great intro"},
            "library": {"library_state": 1},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [sample_entry]
    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path):
        # Sync
        result = runner.invoke(cli, ["sync"])
        assert result.exit_code == 0

        # Search
        result = runner.invoke(cli, ["search", "LLM*"])
        assert "LLM入門ガイド" in result.output

        # Tag add
        result = runner.invoke(cli, ["tag", "add", "int1", "機械学習"])
        assert result.exit_code == 0

        # Tags list
        result = runner.invoke(cli, ["tags"])
        assert "AI" in result.output
        assert "機械学習" in result.output

        # Stats
        result = runner.invoke(cli, ["stats"])
        assert "太郎" in result.output


def test_sync_with_embed(tmp_path):
    runner = CliRunner()

    sample_entry = {
        "id": "art1",
        "content": {
            "title": "Test Article",
            "url": "https://example.com",
            "author": {"any_name": "Alice"},
            "publisher": {"any_name": "Tech"},
            "publication_date": "2025-01-01",
            "tags": [{"name": "tech", "created_date": "2025-01-01"}],
            "my_annotations": [],
            "my_note": None,
            "library": {"library_state": 1},
        },
        "annotations": [],
    }

    mock_client = MagicMock()
    mock_client.fetch_all_articles.return_value = [sample_entry]

    db_path = tmp_path / "test.db"

    with patch("matter_hub.cli.get_client_from_config", return_value=mock_client), \
         patch("matter_hub.cli.get_db_path", return_value=db_path), \
         patch("matter_hub.cli._ensure_ollama", return_value=True), \
         patch("matter_hub.ollama.generate_embedding", return_value=[0.1] * 768):
        result = runner.invoke(cli, ["sync", "--embed"])

    assert result.exit_code == 0
    assert "Embedding" in result.output

    db = Database(db_path)
    emb = db.get_embedding("art1")
    assert emb is not None
    db.close()
