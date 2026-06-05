from __future__ import annotations

import argparse
import hashlib
import json
import zipfile
from pathlib import Path


FIXED_ZIP_TIME = (2024, 1, 1, 0, 0, 0)
DEFAULT_BASE_URL = "https://mslaunch.186.246.12.238.sslip.io/downloads"
DEFAULT_GITHUB_URL = "https://github.com/mio-openliven/MSNukem/releases/download/v1.9.0-beta.1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_deterministic_zip(source_dir: Path, output_path: Path) -> None:
    files = sorted(path for path in source_dir.rglob("*") if path.is_file())
    if not files:
        raise RuntimeError(f"Payload source has no files: {source_dir}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file_path in files:
            relative_path = file_path.relative_to(source_dir).as_posix()
            info = zipfile.ZipInfo(relative_path, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, file_path.read_bytes())


def write_bootstrap_manifest(
    output_path: Path,
    *,
    version: str,
    payload_name: str,
    payload_sha256: str,
    setup_name: str,
    setup_sha256: str,
    base_url: str,
    github_url: str,
) -> None:
    manifest = {
        "version": version,
        "app_version": version,
        "package_name": payload_name,
        "package_sha256": payload_sha256,
        "setup_name": setup_name,
        "setup_sha256": setup_sha256,
        "sources": [
            {
                "name": "Host",
                "url": f"{base_url.rstrip('/')}/{payload_name}",
                "sha256": payload_sha256,
            },
            {
                "name": "GitHub",
                "url": f"{github_url.rstrip('/')}/{payload_name}",
                "sha256": payload_sha256,
            },
        ],
    }
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build deterministic MSLaunch payload and bootstrap manifest.")
    parser.add_argument("--version", required=True, help="Release/app version to write into bootstrap.json.")
    parser.add_argument("--dist-dir", default="dist/MSLauncher", help="Built launcher folder to package.")
    parser.add_argument("--setup", default="dist/MSLaunchSetup.exe", help="Built setup bootstrapper path.")
    parser.add_argument("--output-dir", default="dist", help="Directory for MSLaunchPayload.dat and bootstrap.json.")
    parser.add_argument("--payload-name", default="MSLaunchPayload.dat")
    parser.add_argument("--setup-name", default="MSLaunchSetup.exe")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--github-url", default=DEFAULT_GITHUB_URL)
    args = parser.parse_args()

    dist_dir = Path(args.dist_dir)
    setup_path = Path(args.setup)
    output_dir = Path(args.output_dir)
    payload_path = output_dir / args.payload_name
    bootstrap_path = output_dir / "bootstrap.json"

    if not dist_dir.is_dir():
        raise RuntimeError(f"Built launcher folder not found: {dist_dir}")
    if not setup_path.is_file():
        raise RuntimeError(f"Setup bootstrapper not found: {setup_path}")

    build_deterministic_zip(dist_dir, payload_path)
    payload_sha = sha256_file(payload_path)
    setup_sha = sha256_file(setup_path)
    write_bootstrap_manifest(
        bootstrap_path,
        version=args.version,
        payload_name=args.payload_name,
        payload_sha256=payload_sha,
        setup_name=args.setup_name,
        setup_sha256=setup_sha,
        base_url=args.base_url,
        github_url=args.github_url,
    )

    print(f"payload: {payload_path}")
    print(f"payload_sha256: {payload_sha}")
    print(f"setup: {setup_path}")
    print(f"setup_sha256: {setup_sha}")
    print(f"bootstrap: {bootstrap_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
