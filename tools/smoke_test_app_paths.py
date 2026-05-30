from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app_paths


def set_frozen(app_root: Path, bundle_root: Path) -> tuple[object, object, str]:
    original_frozen = getattr(sys, "frozen", None)
    original_meipass = getattr(sys, "_MEIPASS", None)
    original_executable = sys.executable
    sys.frozen = True
    sys._MEIPASS = str(bundle_root)
    sys.executable = str(app_root / "MSLauncher.exe")
    return original_frozen, original_meipass, original_executable


def restore_frozen(original_frozen: object, original_meipass: object, original_executable: str) -> None:
    sys.executable = original_executable
    if original_frozen is None:
        delattr(sys, "frozen")
    else:
        sys.frozen = original_frozen
    if original_meipass is None:
        delattr(sys, "_MEIPASS")
    else:
        sys._MEIPASS = original_meipass


def main() -> None:
    source_root = Path(app_paths.__file__).resolve().parent
    assert app_paths.get_app_root() == source_root
    assert app_paths.get_bundle_root() == source_root
    assert app_paths.get_asset_path("icons").is_dir()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        app_root = temp_root / "app"
        bundle_root = temp_root / "bundle"
        appdata_root = temp_root / "appdata"
        app_root.mkdir()
        bundle_root.mkdir()
        (bundle_root / "assets" / "backgrounds").mkdir(parents=True)
        (bundle_root / "launcher_config.json").write_text('{"default_language": "EN"}', encoding="utf-8")

        original_appdata = os.environ.get("APPDATA")
        original_override = os.environ.get("MSLAUNCHER_USER_DATA_ROOT")
        frozen_state = set_frozen(app_root, bundle_root)
        try:
            os.environ["APPDATA"] = str(appdata_root)
            os.environ.pop("MSLAUNCHER_USER_DATA_ROOT", None)
            app_paths.LAST_CONFIG_BACKUP_PATH = None

            assert app_paths.get_bundle_root() == bundle_root
            assert app_paths.get_app_root() == app_root
            assert app_paths.get_user_data_root() == appdata_root / "MSLauncher"
            assert app_paths.get_config_path() == appdata_root / "MSLauncher" / "launcher_config.json"
            assert app_paths.get_default_profiles_directory() == appdata_root / "MSLauncher" / "instances"
            assert app_paths.get_asset_path("backgrounds") == bundle_root / "assets" / "backgrounds"

            user_config = app_paths.ensure_user_config()
            assert user_config == appdata_root / "MSLauncher" / "launcher_config.json"
            assert json.loads(user_config.read_text(encoding="utf-8"))["default_language"] == "EN"

            user_config.write_text("{", encoding="utf-8")
            repaired_config = app_paths.ensure_user_config()
            backup_path = app_paths.get_last_config_backup_path()
            assert repaired_config == user_config
            assert backup_path is not None
            assert backup_path.is_file()
            assert backup_path.name.startswith("launcher_config.broken-")
            assert user_config.is_file()
            assert json.loads(user_config.read_text(encoding="utf-8"))["default_language"] == "EN"

            (app_root / ".portable").write_text("", encoding="utf-8")
            assert app_paths.is_portable_mode()
            assert app_paths.get_user_data_root() == app_root
            assert app_paths.get_config_path() == app_root / "launcher_config.json"
            assert app_paths.get_default_profiles_directory() == app_root / "instances"
        finally:
            restore_frozen(*frozen_state)
            if original_appdata is None:
                os.environ.pop("APPDATA", None)
            else:
                os.environ["APPDATA"] = original_appdata
            if original_override is None:
                os.environ.pop("MSLAUNCHER_USER_DATA_ROOT", None)
            else:
                os.environ["MSLAUNCHER_USER_DATA_ROOT"] = original_override

    print("app paths smoke test: OK")


if __name__ == "__main__":
    main()
