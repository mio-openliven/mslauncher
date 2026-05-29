from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


SCAN_DIRECTORIES = ("mods", "config", "resourcepacks")
MANIFEST_FILE = "manifest.json"


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()

    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def generate_manifest(base_directory: str | Path = ".", base_url: str = "") -> dict[str, object]:
    base_path = Path(base_directory).resolve()
    files: list[dict[str, object]] = []
    normalized_base_url = base_url.rstrip("/")

    for directory_name in SCAN_DIRECTORIES:
        directory_path = base_path / directory_name
        if not directory_path.exists():
            continue

        for file_path in sorted(directory_path.rglob("*")):
            if not file_path.is_file():
                continue

            relative_path = file_path.relative_to(base_path).as_posix()
            files.append(
                {
                    "path": relative_path,
                    "sha256": calculate_sha256(file_path),
                    "size": file_path.stat().st_size,
                    "url": build_file_url(normalized_base_url, relative_path),
                }
            )

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def build_file_url(base_url: str, relative_path: str) -> str:
    if not base_url:
        return ""

    encoded_path = "/".join(quote(part) for part in relative_path.split("/"))
    return f"{base_url}/{encoded_path}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MSLauncher file manifest.")
    parser.add_argument("--base-dir", default=".", help="Directory with mods/config/resourcepacks.")
    parser.add_argument("--base-url", default="", help="Raw base URL used to download files.")
    parser.add_argument("--output", default=MANIFEST_FILE, help="Manifest output file.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    manifest = generate_manifest(args.base_dir, args.base_url)

    with Path(args.output).open("w", encoding="utf-8") as file:
        json.dump(manifest, file, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
