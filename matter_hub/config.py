"""Configuration management for Matter Hub.

Stores config (tokens) in ~/.matter-hub/config.json.
Stores database in ~/.matter-hub/matter-hub.db.
"""

import json
from pathlib import Path

DEFAULT_DIR = Path.home() / ".matter-hub"
DEFAULT_CONFIG_PATH = DEFAULT_DIR / "config.json"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_config(data: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def get_db_path() -> Path:
    return DEFAULT_DIR / "matter-hub.db"
