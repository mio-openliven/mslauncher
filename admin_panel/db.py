from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Iterable

from .settings import get_database_path, get_downloads_root, get_panel_data_root, get_storage_root


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('owner', 'project_admin', 'viewer')),
    project_slug TEXT NOT NULL DEFAULT 'nukem',
    active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS projects (
    slug TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    fallback_source_key TEXT NOT NULL DEFAULT '',
    support_url TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS builds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_slug TEXT NOT NULL,
    build_id TEXT NOT NULL,
    name TEXT NOT NULL,
    minecraft_version TEXT NOT NULL,
    loader TEXT NOT NULL CHECK(loader IN ('vanilla', 'fabric')),
    loader_version TEXT NOT NULL DEFAULT 'latest',
    server TEXT NOT NULL DEFAULT '',
    port TEXT NOT NULL DEFAULT '',
    access_hash_sha256 TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL CHECK(status IN ('draft', 'active', 'archived')) DEFAULT 'draft',
    file_count INTEGER NOT NULL DEFAULT 0,
    total_size INTEGER NOT NULL DEFAULT 0,
    created_by TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    activated_at TEXT NOT NULL DEFAULT '',
    UNIQUE(project_slug, build_id)
);

CREATE TABLE IF NOT EXISTS launcher_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL,
    download_url TEXT NOT NULL DEFAULT '',
    sha256 TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project TEXT NOT NULL DEFAULT '',
    build_id TEXT NOT NULL DEFAULT '',
    username TEXT NOT NULL DEFAULT '',
    launcher_version TEXT NOT NULL DEFAULT '',
    error_type TEXT NOT NULL DEFAULT '',
    user_message TEXT NOT NULL DEFAULT '',
    technical_details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


DEFAULT_PROJECTS = (
    (
        "nukem",
        "MS Nuckem",
        "https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json",
        "https://github.com/mio-openliven/MSNukem/issues/new",
    ),
    ("vibecraft", "VibeCraft", "", ""),
)


class ClosingConnection(sqlite3.Connection):
    def __exit__(self, exc_type, exc_value, traceback) -> bool:
        result = super().__exit__(exc_type, exc_value, traceback)
        self.close()
        return result


def connect(database_path: Path | None = None) -> sqlite3.Connection:
    path = database_path or get_database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, factory=ClosingConnection)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys=ON")
    return connection


def init_db(database_path: Path | None = None) -> None:
    get_panel_data_root().mkdir(parents=True, exist_ok=True)
    get_storage_root().mkdir(parents=True, exist_ok=True)
    get_downloads_root().mkdir(parents=True, exist_ok=True)
    with connect(database_path) as connection:
        connection.executescript(SCHEMA)
        ensure_user_columns(connection)
        ensure_build_columns(connection)
        seed_projects(connection, DEFAULT_PROJECTS)


def ensure_user_columns(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(users)").fetchall()
    }
    if "project_slug" not in columns:
        connection.execute("ALTER TABLE users ADD COLUMN project_slug TEXT NOT NULL DEFAULT 'nukem'")


def ensure_build_columns(connection: sqlite3.Connection) -> None:
    columns = {
        str(row["name"])
        for row in connection.execute("PRAGMA table_info(builds)").fetchall()
    }
    if "access_hash_sha256" not in columns:
        connection.execute("ALTER TABLE builds ADD COLUMN access_hash_sha256 TEXT NOT NULL DEFAULT ''")


def seed_projects(connection: sqlite3.Connection, projects: Iterable[tuple[str, str, str, str]]) -> None:
    for slug, name, fallback_source_key, support_url in projects:
        connection.execute(
            """
            INSERT INTO projects (slug, name, fallback_source_key, support_url)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(slug) DO UPDATE SET
                name=excluded.name,
                fallback_source_key=excluded.fallback_source_key,
                support_url=excluded.support_url
            """,
            (slug, name, fallback_source_key, support_url),
        )
