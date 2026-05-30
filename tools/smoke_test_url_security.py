from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_validator import ManifestValidationError, normalize_download_url
from remote_config import RemoteBuildConfigError, normalize_source_key, validate_build_config


def expect_remote_error(callback) -> None:
    try:
        callback()
    except RemoteBuildConfigError:
        return
    raise AssertionError("Expected RemoteBuildConfigError")


def expect_manifest_error(callback) -> None:
    try:
        callback()
    except ManifestValidationError:
        return
    raise AssertionError("Expected ManifestValidationError")


def main() -> None:
    assert normalize_source_key("example.com") == "https://example.com/mslauncher/build.json"
    assert normalize_source_key("example.com:443") == "https://example.com:443/mslauncher/build.json"
    assert normalize_source_key("https://example.com/build.json") == "https://example.com/build.json"

    expect_remote_error(lambda: normalize_source_key("http://example.com/build.json"))
    expect_remote_error(lambda: normalize_source_key("https://user:pass@example.com/build.json"))
    expect_remote_error(lambda: normalize_source_key("https://example.com/build.json#frag"))
    expect_remote_error(lambda: normalize_source_key(""))
    expect_remote_error(lambda: validate_build_config({"manifest_url": "http://example.com/manifest.json"}))
    expect_remote_error(lambda: validate_build_config({"manifest_url": "https://user:pass@example.com/manifest.json"}))
    expect_remote_error(lambda: validate_build_config({"manifest_url": "https://example.com/manifest.json#frag"}))
    expect_remote_error(lambda: validate_build_config({"manifest_url": "https://127.0.0.1/manifest.json"}))

    validate_build_config({"manifest_url": "https://example.com/manifest.json"})

    expect_manifest_error(lambda: normalize_download_url("http://example.com/file.jar", "mods/file.jar"))
    expect_manifest_error(lambda: normalize_download_url("https://user:pass@example.com/file.jar", "mods/file.jar"))
    expect_manifest_error(lambda: normalize_download_url("https://example.com/file.jar#frag", "mods/file.jar"))
    expect_manifest_error(lambda: normalize_download_url("https://127.0.0.1/file.jar", "mods/file.jar"))
    assert normalize_download_url("https://example.com/file.jar", "mods/file.jar") == "https://example.com/file.jar"
    assert (
        normalize_download_url(
            "http://127.0.0.1:8000/file.jar",
            "mods/file.jar",
            allow_insecure_local=True,
        )
        == "http://127.0.0.1:8000/file.jar"
    )

    print("url security smoke test: OK")


if __name__ == "__main__":
    main()
