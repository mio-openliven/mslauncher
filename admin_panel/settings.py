from __future__ import annotations

import os
from pathlib import Path


APP_NAME = "MSLaunch Panel"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


def get_panel_data_root() -> Path:
    configured = os.environ.get("MSLAUNCH_PANEL_DATA", "").strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path.cwd() / "panel_data").resolve()


def get_database_path() -> Path:
    return get_panel_data_root() / "panel.sqlite3"


def get_storage_root() -> Path:
    return get_panel_data_root() / "storage"


def get_downloads_root() -> Path:
    return get_panel_data_root() / "downloads"


def get_session_secret() -> str:
    return os.environ.get("MSLAUNCH_PANEL_SECRET", "dev-panel-secret-change-me")


def get_public_base_url(default: str = "") -> str:
    return os.environ.get("MSLAUNCH_PANEL_PUBLIC_URL", default).rstrip("/")
