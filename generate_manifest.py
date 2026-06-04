from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from loader_support import SUPPORTED_LOADERS, format_supported_loaders, normalize_loader


SCAN_DIRECTORIES = ("mods", "config", "resourcepacks")
MANIFEST_FILE = "manifest.json"
BUILD_FILE = "build.json"
SKIPPED_SUFFIXES = (".part",)
SKIPPED_NAMES = {
    ".gitkeep",
    ".mslauncher-managed",
    MANIFEST_FILE,
    BUILD_FILE,
}


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
            if should_skip_file(file_path):
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

    encoded_path = "/".join(quote(part, safe="") for part in relative_path.split("/"))
    return f"{base_url}/{encoded_path}"


def should_skip_file(file_path: Path) -> bool:
    if file_path.name in SKIPPED_NAMES:
        return True
    if any(file_path.name.endswith(suffix) for suffix in SKIPPED_SUFFIXES):
        return True
    return ".mslauncher-staging" in file_path.parts


def generate_build_config(
    *,
    build_name: str,
    minecraft_version: str,
    loader: str,
    loader_version: str,
    base_url: str,
    output_manifest: str,
    server: str,
    port: str,
) -> dict[str, str]:
    normalized_loader = normalize_loader(loader) or "vanilla"
    validate_loader(normalized_loader)
    validate_port(port)

    manifest_url = ""
    normalized_base_url = base_url.rstrip("/")
    if normalized_base_url:
        manifest_url = build_file_url(normalized_base_url, Path(output_manifest).name)

    return {
        "name": build_name.strip() or "Main Server",
        "minecraft_version": minecraft_version.strip(),
        "loader": normalized_loader,
        "loader_version": loader_version.strip() or "latest",
        "manifest_url": manifest_url,
        "server": server.strip(),
        "port": str(port).strip(),
    }


def validate_loader(loader: str) -> None:
    if normalize_loader(loader) not in SUPPORTED_LOADERS:
        raise ValueError(f"loader must be {format_supported_loaders()}.")


def validate_port(port: str) -> None:
    normalized_port = str(port).strip()
    if not normalized_port:
        return
    if not normalized_port.isdigit() or not 1 <= int(normalized_port) <= 65535:
        raise ValueError("port must be a number from 1 to 65535.")


def resolve_output_path(base_directory: str | Path, output_path: str, *, legacy_output: bool = False) -> Path:
    path = Path(output_path)
    if path.is_absolute() or legacy_output:
        return path
    return Path(base_directory) / path


def write_json(path: Path, data: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate MSLauncher manifest.json and build.json.")
    parser.add_argument("--base-dir", default=".", help="Directory with mods/config/resourcepacks.")
    parser.add_argument("--base-url", default="", help="Raw base URL used to download files.")
    parser.add_argument("--minecraft-version", default="", help="Minecraft version for build.json.")
    parser.add_argument("--loader", default="vanilla", help=f"Loader for build.json: {format_supported_loaders()}.")
    parser.add_argument("--server", default="", help="Server address for build.json.")
    parser.add_argument("--port", default="", help="Server port for build.json.")
    parser.add_argument("--build-name", default="Main Server", help="Build name shown in launcher.")
    parser.add_argument("--loader-version", default="latest", help="Loader version for build.json.")
    parser.add_argument("--output-manifest", default=MANIFEST_FILE, help="Manifest output file.")
    parser.add_argument("--output-build", default=BUILD_FILE, help="Build config output file.")
    parser.add_argument("--output", default="", help="Legacy alias for --output-manifest.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        validate_loader(args.loader.strip().lower())
        validate_port(args.port)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    output_manifest = args.output or args.output_manifest
    manifest_path = resolve_output_path(args.base_dir, output_manifest, legacy_output=bool(args.output))
    build_path = resolve_output_path(args.base_dir, args.output_build)

    manifest = generate_manifest(args.base_dir, args.base_url)
    build_config = generate_build_config(
        build_name=args.build_name,
        minecraft_version=args.minecraft_version,
        loader=args.loader,
        loader_version=args.loader_version,
        base_url=args.base_url,
        output_manifest=manifest_path.name,
        server=args.server,
        port=args.port,
    )

    write_json(manifest_path, manifest)
    write_json(build_path, build_config)

    print(f"Generated {manifest_path}")
    print(f"Generated {build_path}")
    if not args.base_url.strip():
        print(
            "WARNING: --base-url is empty. Manifest file URLs are empty, "
            "so players cannot download files until base-url is set.",
            file=sys.stdout,
        )


if __name__ == "__main__":
    main()
