"""Configuration management for Matter Hub.

Stores config (tokens) and database under <project>/data/ by default.
Override paths with MATTER_HUB_CONFIG / MATTER_HUB_DB env vars.
"""

import json
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_CONFIG_PATH = DATA_DIR / "config.json"


def get_config_path() -> Path:
    env = os.environ.get("MATTER_HUB_CONFIG")
    if env:
        return Path(env)
    return DEFAULT_CONFIG_PATH


def load_config(path: Path | None = None) -> dict:
    target = path if path is not None else get_config_path()
    if not target.exists():
        return {}
    return json.loads(target.read_text())


def save_config(data: dict, path: Path | None = None) -> None:
    target = path if path is not None else get_config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, indent=2))


def get_db_path() -> Path:
    env = os.environ.get("MATTER_HUB_DB")
    if env:
        path = Path(env)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_DIR / "matter-hub.db"
