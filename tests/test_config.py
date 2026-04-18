import json
from pathlib import Path

from matter_hub.config import load_config, save_config, get_db_path


def test_load_config_returns_empty_when_no_file(tmp_path):
    config = load_config(tmp_path / "config.json")
    assert config == {}


def test_save_and_load_config(tmp_path):
    config_path = tmp_path / "config.json"
    data = {"access_token": "abc123", "refresh_token": "def456"}
    save_config(data, config_path)
    loaded = load_config(config_path)
    assert loaded == data


def test_save_config_creates_parent_dirs(tmp_path):
    config_path = tmp_path / "subdir" / "config.json"
    save_config({"key": "value"}, config_path)
    assert config_path.exists()


def test_get_db_path():
    db_path = get_db_path()
    assert db_path.name == "matter-hub.db"
    assert "data" in str(db_path)


def test_get_db_path_respects_env(tmp_path, monkeypatch):
    custom = tmp_path / "custom.db"
    monkeypatch.setenv("MATTER_HUB_DB", str(custom))
    assert get_db_path() == custom


def test_get_db_path_default_when_env_absent(monkeypatch):
    monkeypatch.delenv("MATTER_HUB_DB", raising=False)
    from matter_hub.config import DATA_DIR
    assert get_db_path() == DATA_DIR / "matter-hub.db"
