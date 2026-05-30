from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from manifest_validator import ManifestValidationError, validate_manifest


VALID_HASH = "a" * 64


def expect_error(manifest: object) -> None:
    try:
        validate_manifest(manifest)
    except ManifestValidationError:
        return
    raise AssertionError(f"Expected ManifestValidationError for {manifest}")


def file_item(**overrides: object) -> dict[str, object]:
    item: dict[str, object] = {
        "path": "mods/example.jar",
        "sha256": VALID_HASH,
        "url": "https://example.com/mods/example.jar",
        "size": 10,
    }
    item.update(overrides)
    return item


def main() -> None:
    validated_files = validate_manifest({"files": [file_item()]})
    assert validated_files[0]["path"] == "mods/example.jar"
    assert validated_files[0]["sha256"] == VALID_HASH
    assert validated_files[0]["size"] == 10

    expect_error([])
    expect_error({"files": "bad"})
    expect_error({"files": ["bad"]})
    expect_error({"files": [file_item(path="../mods/example.jar")]})
    expect_error({"files": [file_item(path="saves/world.dat")]})
    expect_error({"files": [file_item(path="mods/example.jar"), file_item(path="mods/example.jar")]})
    expect_error({"files": [file_item(sha256="bad")]})
    expect_error({"files": [file_item(url="http://example.com/mod.jar")]})
    expect_error({"files": [file_item(url="ftp://example.com/mod.jar")]})
    expect_error({"files": [file_item(url="https://user:pass@example.com/mod.jar")]})
    expect_error({"files": [file_item(url="https://example.com/mod.jar#bad")]})
    expect_error({"files": [file_item(url="")]})
    expect_error({"files": [file_item(size=-1)]})
    expect_error({"files": [file_item(size=True)]})

    local_http = validate_manifest(
        {"files": [file_item(url="http://127.0.0.1:8000/mods/example.jar")]},
        allow_insecure_local=True,
    )
    assert local_http[0]["url"].startswith("http://127.0.0.1")

    print("manifest validator smoke test: OK")


if __name__ == "__main__":
    main()
