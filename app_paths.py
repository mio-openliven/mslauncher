from __future__ import annotations

import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path


APP_NAME = "MSLauncher"
CONFIG_FILE_NAME = "launcher_config.json"
PORTABLE_MARKER = ".portable"
LAST_CONFIG_BACKUP_PATH: Path | None = None


class ConfigBootstrapError(RuntimeError):
    pass


def get_bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)).resolve()
    return Path(__file__).resolve().parent


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def is_portable_mode() -> bool:
    return (get_app_root() / PORTABLE_MARKER).is_file()


def get_user_data_root() -> Path:
    if is_portable_mode():
        return get_app_root()

    override_path = os.environ.get("MSLAUNCHER_USER_DATA_ROOT", "").strip()
    if override_path:
        return Path(override_path).expanduser().resolve()

    app_data_path = os.environ.get("APPDATA", "").strip()
    if app_data_path:
        return (Path(app_data_path) / APP_NAME).resolve()

    return (Path.home() / f".{APP_NAME.lower()}").resolve()


def get_asset_path(*parts: str) -> Path:
    return get_bundle_root().joinpath("assets", *parts)


def get_config_path() -> Path:
    return get_user_data_root() / CONFIG_FILE_NAME


def get_default_profiles_directory() -> Path:
    return get_user_data_root() / "instances"


def get_last_config_backup_path() -> Path | None:
    return LAST_CONFIG_BACKUP_PATH


def ensure_user_config() -> Path:
    global LAST_CONFIG_BACKUP_PATH

    LAST_CONFIG_BACKUP_PATH = None
    user_config_path = get_config_path()
    user_config_path.parent.mkdir(parents=True, exist_ok=True)

    if user_config_path.exists():
        if is_valid_json_file(user_config_path):
            return user_config_path

        LAST_CONFIG_BACKUP_PATH = backup_broken_config(user_config_path)
        copy_default_config(user_config_path)
        return user_config_path

    copy_default_config(user_config_path)
    return user_config_path


def is_valid_json_file(config_path: Path) -> bool:
    try:
        with config_path.open("r", encoding="utf-8") as file:
            json.load(file)
    except (OSError, json.JSONDecodeError):
        return False
    return True


def backup_broken_config(config_path: Path) -> Path:
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_path = config_path.with_name(f"launcher_config.broken-{timestamp}.json")
    counter = 1
    while backup_path.exists():
        backup_path = config_path.with_name(f"launcher_config.broken-{timestamp}-{counter}.json")
        counter += 1
    config_path.replace(backup_path)
    return backup_path


def copy_default_config(user_config_path: Path) -> None:
    bundled_config_path = get_bundle_root() / CONFIG_FILE_NAME
    if bundled_config_path.is_file() and bundled_config_path.resolve() != user_config_path.resolve():
        shutil.copyfile(bundled_config_path, user_config_path)
        return

    user_config_path.write_text("{}\n", encoding="utf-8")
