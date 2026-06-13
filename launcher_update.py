from __future__ import annotations

import re
from typing import Any


APP_DISPLAY_NAME = "MSLaunch"
APP_VERSION = "1.9.9"


def parse_version_numbers(version: object) -> list[int]:
    if not isinstance(version, str):
        return []
    return [int(part) for part in re.findall(r"\d+", version)]


def is_remote_version_newer(current: str, remote: str) -> bool:
    current_parts = parse_version_numbers(current)
    remote_parts = parse_version_numbers(remote)
    if not current_parts or not remote_parts:
        return False

    length = max(len(current_parts), len(remote_parts))
    normalized_current = current_parts + [0] * (length - len(current_parts))
    normalized_remote = remote_parts + [0] * (length - len(remote_parts))
    return normalized_remote > normalized_current


def get_launcher_update_notice(build: dict[str, Any], current_version: str = APP_VERSION) -> dict[str, str]:
    remote_version = str(build.get("launcher_version", "")).strip()
    if not remote_version or not is_remote_version_newer(current_version, remote_version):
        return {}

    return {
        "version": remote_version,
        "download_url": str(build.get("launcher_download_url", "")).strip(),
        "notes": str(build.get("launcher_notes", "")).strip(),
        "sha256": str(build.get("launcher_sha256", "")).strip(),
    }
