from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app_paths


def main() -> None:
    source_root = Path(app_paths.__file__).resolve().parent
    assert app_paths.get_app_root() == source_root
    assert app_paths.get_bundle_root() == source_root
    assert app_paths.get_config_path() == source_root / "launcher_config.json"
    assert app_paths.get_asset_path("icons").is_dir()
    assert app_paths.get_default_profiles_directory() == source_root / "data" / "instances"

    original_frozen = getattr(sys, "frozen", None)
    original_meipass = getattr(sys, "_MEIPASS", None)
    original_executable = sys.executable
    try:
        sys.frozen = True
        sys._MEIPASS = str(source_root / "_internal")
        sys.executable = str(source_root / "MSLauncher.exe")

        assert app_paths.get_bundle_root() == source_root / "_internal"
        assert app_paths.get_app_root() == source_root
        assert app_paths.get_config_path() == source_root / "launcher_config.json"
        assert app_paths.get_default_profiles_directory() == source_root / "data" / "instances"
        assert app_paths.get_asset_path("backgrounds") == source_root / "_internal" / "assets" / "backgrounds"
    finally:
        sys.executable = original_executable
        if original_frozen is None:
            delattr(sys, "frozen")
        else:
            sys.frozen = original_frozen
        if original_meipass is None:
            delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = original_meipass

    print("app paths smoke test: OK")


if __name__ == "__main__":
    main()
