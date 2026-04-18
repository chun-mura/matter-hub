"""Configuration management for Matter Hub.

Stores config (tokens) in ~/.matter-hub/config.json.
Stores database in <project>/data/matter-hub.db.
"""

import json
import os
from pathlib import Path

DEFAULT_DIR = Path.home() / ".matter-hub"
DEFAULT_CONFIG_PATH = DEFAULT_DIR / "config.json"
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save_config(data: dict, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2))


def get_db_path() -> Path:
    env = os.environ.get("MATTER_HUB_DB")
    if env:
        path = Path(env)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "matter-hub.db"
