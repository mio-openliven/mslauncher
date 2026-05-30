from __future__ import annotations

import shutil
import sys
from pathlib import Path


CONFIG_FILE_NAME = "launcher_config.json"


def get_bundle_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).resolve().parent)).resolve()
    return Path(__file__).resolve().parent


def get_app_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_asset_path(*parts: str) -> Path:
    return get_bundle_root().joinpath("assets", *parts)


def get_config_path() -> Path:
    return get_app_root() / CONFIG_FILE_NAME


def get_default_profiles_directory() -> Path:
    return get_app_root() / "data" / "instances"


def ensure_user_config() -> Path:
    user_config_path = get_config_path()
    if user_config_path.exists():
        return user_config_path

    bundled_config_path = get_bundle_root() / CONFIG_FILE_NAME
    if bundled_config_path.is_file() and bundled_config_path != user_config_path:
        user_config_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(bundled_config_path, user_config_path)

    return user_config_path
