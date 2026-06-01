from __future__ import annotations

import sys
from pathlib import Path

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

    print("launcher update smoke test: OK")


if __name__ == "__main__":
    main()
