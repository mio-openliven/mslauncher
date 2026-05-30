from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse


ALLOWED_ROOTS = ("mods", "config", "resourcepacks")
SHA256_PATTERN = re.compile(r"^[a-fA-F0-9]{64}$")


class ManifestValidationError(RuntimeError):
    pass


def validate_manifest(manifest: object) -> list[dict[str, str | int]]:
    if not isinstance(manifest, dict):
        raise ManifestValidationError("Manifest must be a JSON object.")

    manifest_files = manifest.get("files")
    if not isinstance(manifest_files, list):
        raise ManifestValidationError("Manifest field 'files' must be a list.")

    validated_files: list[dict[str, str | int]] = []
    seen_paths: set[str] = set()

    for index, item in enumerate(manifest_files):
        if not isinstance(item, dict):
            raise ManifestValidationError(f"Manifest file #{index + 1} must be an object.")

        relative_path = normalize_manifest_path(item.get("path", ""))
        if relative_path in seen_paths:
            raise ManifestValidationError(f"Manifest contains duplicate path: {relative_path}")
        seen_paths.add(relative_path)

        expected_hash = normalize_sha256(item.get("sha256", ""), relative_path)
        download_url = normalize_download_url(item.get("url", ""), relative_path)
        size = normalize_size(item.get("size", 0), relative_path)

        validated_files.append(
            {
                "path": relative_path,
                "sha256": expected_hash,
                "url": download_url,
                "size": size,
            }
        )

    return validated_files


def normalize_manifest_path(raw_path: object) -> str:
    if not isinstance(raw_path, str):
        raise ManifestValidationError("Manifest path must be a string.")

    relative_path = raw_path.replace("\\", "/").strip("/")
    path_parts = Path(relative_path).parts

    if (
        not relative_path
        or Path(relative_path).is_absolute()
        or ".." in path_parts
        or relative_path.startswith(("/", "\\"))
    ):
        raise ManifestValidationError(f"Manifest contains unsafe path: {raw_path}")

    if path_parts[0] not in ALLOWED_ROOTS:
        raise ManifestValidationError(
            f"Manifest path must start with mods, config, or resourcepacks: {relative_path}"
        )

    return relative_path


def normalize_sha256(raw_hash: object, relative_path: str) -> str:
    expected_hash = str(raw_hash).strip().lower()
    if not SHA256_PATTERN.match(expected_hash):
        raise ManifestValidationError(f"Manifest sha256 is invalid for {relative_path}.")
    return expected_hash


def normalize_download_url(raw_url: object, relative_path: str) -> str:
    if not isinstance(raw_url, str):
        raise ManifestValidationError(f"Manifest url must be a string for {relative_path}.")

    download_url = raw_url.strip()
    parsed_url = urlparse(download_url)
    if parsed_url.scheme not in ("http", "https") or not parsed_url.netloc:
        raise ManifestValidationError(f"Manifest url must be http or https for {relative_path}.")
    return download_url


def normalize_size(raw_size: object, relative_path: str) -> int:
    if isinstance(raw_size, bool):
        raise ManifestValidationError(f"Manifest size must be a non-negative integer for {relative_path}.")

    try:
        size = int(raw_size)
    except (TypeError, ValueError) as exc:
        raise ManifestValidationError(f"Manifest size must be a non-negative integer for {relative_path}.") from exc

    if size < 0:
        raise ManifestValidationError(f"Manifest size must be a non-negative integer for {relative_path}.")
    return size
