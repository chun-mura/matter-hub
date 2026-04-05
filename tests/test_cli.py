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
