from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from launcher_update import APP_VERSION, get_launcher_update_notice, is_remote_version_newer
from remote_config import RemoteBuildConfigError, validate_build_config


def expect_remote_error(callback) -> None:
    try:
        callback()
    except RemoteBuildConfigError:
        return
    raise AssertionError("Expected RemoteBuildConfigError")


def smoke_gui_update_states(next_version: str) -> None:
    import gui
    from PyQt6.QtWidgets import QApplication

    gui.MSLauncherWindow.load_versions = lambda self: self.set_status("ready")
    gui.MSLauncherWindow.auto_check_launcher_update = lambda self: None

    app = QApplication.instance() or QApplication(sys.argv)
    window = gui.MSLauncherWindow()
    try:
        window.on_launcher_update_loaded(
            {
                "launcher_version": next_version,
                "launcher_download_url": "https://example.com/MSLaunchSetup.exe",
                "launcher_sha256": "a" * 64,
                "launcher_notes": "Smoke update",
            }
        )
        assert window.update_check_state == "available"
        assert window.update_check_button.text() == "!"
        assert next_version in window.update_check_button.toolTip()
        assert window.info_panel_mode == "update"
        assert window.launcher_update_version == next_version

        window.update_check_manual = False
        window.on_launcher_update_failed("network down")
        assert window.update_check_state == "available"
        assert window.update_check_button.text() == "!"
        assert window.launcher_update_version == next_version

        window.launcher_update_version = ""
        window.launcher_update_url = ""
        window.launcher_update_notes = ""
        window.info_panel_mode = "status"
        window.set_update_check_state("ok")
        window.update_check_manual = False
        window.on_launcher_update_failed("network down")
        assert window.update_check_state == "error"
        assert window.update_check_button.text() == "!"
        assert "network down" in window.update_check_button.toolTip()

        window.update_check_manual = True
        window.on_launcher_update_loaded({"launcher_version": APP_VERSION})
        assert window.update_check_state == "ok"
        assert window.update_check_button.text() == "OK"
        assert window.update_check_button.toolTip() == window.translate("manual_update_tooltip")

        window.update_check_manual = True
        window.on_launcher_update_loaded({"launcher_version": "version-next"})
        assert window.update_check_state == "error"
        assert window.update_check_button.text() == "!"
        assert "Malformed launcher_version" in window.update_check_button.toolTip()
    finally:
        window.close()


def main() -> None:
    current_major, current_minor, current_patch = (int(part) for part in APP_VERSION.split("."))
    next_version = f"{current_major}.{current_minor}.{current_patch + 1}"

    assert is_remote_version_newer("1.9.0", "1.9.1")
    assert is_remote_version_newer("1.9.9", "1.10.0")
    assert is_remote_version_newer("1.9.0", "1.9.1-beta")
    assert not is_remote_version_newer("1.9.0", "1.9.0")
    assert not is_remote_version_newer("1.9.0", "1.8.9")
    assert not is_remote_version_newer("1.9.0", "bad-version")

    assert get_launcher_update_notice({"launcher_version": APP_VERSION}) == {}
    assert get_launcher_update_notice({"launcher_version": "1.9.0"}) == {}
    assert get_launcher_update_notice({"launcher_version": "1.8.9"}) == {}
    assert get_launcher_update_notice({}) == {}

    update_notice = get_launcher_update_notice(
        {
            "launcher_version": next_version,
            "launcher_download_url": f"https://github.com/OWNER/REPO/releases/download/v{next_version}/MSLaunchSetup.exe",
            "launcher_sha256": "a" * 64,
            "launcher_notes": "Small update",
        }
    )
    assert update_notice["version"] == next_version
    assert update_notice["download_url"].startswith("https://github.com/")
    assert update_notice["sha256"] == "a" * 64
    assert update_notice["notes"] == "Small update"

    accepted = validate_build_config(
        {
            "loader": "fabric",
            "manifest_url": "https://example.com/manifest.json",
            "launcher_version": next_version,
            "launcher_download_url": f"https://github.com/OWNER/REPO/releases/download/v{next_version}/MSLaunchSetup.exe",
            "launcher_sha256": "A" * 64,
            "launcher_notes": "Update note",
        }
    )
    assert accepted["launcher_version"] == next_version
    assert accepted["launcher_download_url"].startswith("https://github.com/")
    assert accepted["launcher_sha256"] == "a" * 64
    assert accepted["launcher_notes"] == "Update note"

    missing_fields = validate_build_config({"loader": "fabric", "manifest_url": "https://example.com/manifest.json"})
    assert missing_fields["launcher_version"] == ""
    assert missing_fields["launcher_download_url"] == ""
    assert missing_fields["launcher_sha256"] == ""
    assert missing_fields["launcher_notes"] == ""

    expect_remote_error(
        lambda: validate_build_config(
            {
                "loader": "fabric",
                "manifest_url": "https://example.com/manifest.json",
                "launcher_download_url": "http://example.com/MSLauncher.zip",
            }
        )
    )
    expect_remote_error(
        lambda: validate_build_config(
            {
                "loader": "fabric",
                "manifest_url": "https://example.com/manifest.json",
                "launcher_sha256": "not-a-sha",
            }
        )
    )

    smoke_gui_update_states(next_version)

    print("launcher update smoke test: OK")


if __name__ == "__main__":
    main()
