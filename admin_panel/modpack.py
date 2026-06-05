from __future__ import annotations

import hashlib
import json
import shutil
import stat
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote


ALLOWED_ROOTS = {"mods", "config", "resourcepacks"}
SKIPPED_NAMES = {".gitkeep", ".mslauncher-managed", "manifest.json", "build.json"}
SKIPPED_SUFFIXES = (".part", ".tmp")


class UploadValidationError(RuntimeError):
    pass


def build_storage_path(storage_root: Path, project: str, build_id: str) -> Path:
    return storage_root / "projects" / safe_segment(project) / "builds" / safe_segment(build_id) / "files"


def safe_segment(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip().lower() if ch.isalnum() or ch in ("-", "_"))
    if not cleaned:
        raise UploadValidationError("Segment cannot be empty.")
    return cleaned


def safe_manifest_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/").strip()
    if (
        not normalized
        or normalized.startswith("/")
        or normalized.startswith("\\")
        or (len(normalized) >= 2 and normalized[1] == ":")
    ):
        raise UploadValidationError(f"Unsafe path: {raw_path}")
    normalized = normalized.strip("/")
    parts = [part for part in normalized.split("/") if part]
    if not parts or parts[0] not in ALLOWED_ROOTS:
        raise UploadValidationError(f"File must be under mods, config, or resourcepacks: {raw_path}")
    if len(parts) < 2:
        raise UploadValidationError(f"File must be inside mods, config, or resourcepacks: {raw_path}")
    if any(part in ("", ".", "..") for part in normalized.split("/")):
        raise UploadValidationError(f"Unsafe path: {raw_path}")
    if any(part == ".mslauncher-staging" for part in parts):
        raise UploadValidationError(f"Internal staging paths are not allowed: {raw_path}")
    if Path(normalized).is_absolute():
        raise UploadValidationError(f"Absolute path is not allowed: {raw_path}")
    file_name = parts[-1].lower()
    if file_name in SKIPPED_NAMES:
        raise UploadValidationError(f"Generated or internal file is not allowed in upload: {raw_path}")
    if any(file_name.endswith(suffix) for suffix in SKIPPED_SUFFIXES):
        raise UploadValidationError(f"Temporary or partial file is not allowed in upload: {raw_path}")
    if parts[0] == "mods" and len(parts) > 1 and not parts[-1].lower().endswith(".jar"):
        raise UploadValidationError(f"Only .jar files are allowed in mods: {raw_path}")
    return "/".join(parts)


def replace_build_files_from_zip(archive_path: Path, destination_root: Path) -> None:
    staging_root = destination_root.with_name(destination_root.name + ".staging")
    if staging_root.exists():
        shutil.rmtree(staging_root)
    staging_root.mkdir(parents=True, exist_ok=True)

    try:
        with zipfile.ZipFile(archive_path) as archive:
            copied_files = 0
            for member in archive.infolist():
                if member.is_dir():
                    continue
                if is_zip_symlink(member):
                    raise UploadValidationError(f"Symbolic links are not allowed in upload: {member.filename}")
                relative_path = safe_manifest_path(member.filename)
                target_path = staging_root / Path(relative_path)
                target_path.parent.mkdir(parents=True, exist_ok=True)
                with archive.open(member) as source, target_path.open("wb") as target:
                    shutil.copyfileobj(source, target)
                copied_files += 1

            if copied_files == 0:
                raise UploadValidationError("Upload ZIP does not contain files under mods, config, or resourcepacks.")

        if destination_root.exists():
            shutil.rmtree(destination_root)
        staging_root.replace(destination_root)
    except Exception:
        if staging_root.exists():
            shutil.rmtree(staging_root)
        raise


def generate_manifest(files_root: Path, files_base_url: str) -> dict[str, object]:
    files: list[dict[str, object]] = []
    normalized_base = files_base_url.rstrip("/")

    if files_root.is_dir():
        for file_path in sorted(path for path in files_root.rglob("*") if path.is_file()):
            if should_skip_file(file_path):
                continue
            relative_path = file_path.relative_to(files_root).as_posix()
            safe_manifest_path(relative_path)
            files.append(
                {
                    "path": relative_path,
                    "sha256": calculate_sha256(file_path),
                    "size": file_path.stat().st_size,
                    "url": f"{normalized_base}/{quote_path(relative_path)}",
                }
            )

    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": files,
    }


def calculate_file_stats(files_root: Path) -> tuple[int, int]:
    manifest = generate_manifest(files_root, "https://example.invalid/files")
    files = manifest["files"]
    assert isinstance(files, list)
    return len(files), sum(int(item.get("size", 0)) for item in files if isinstance(item, dict))


def write_manifest(files_root: Path, output_path: Path, files_base_url: str) -> dict[str, object]:
    manifest = generate_manifest(files_root, files_base_url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def calculate_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def quote_path(relative_path: str) -> str:
    return "/".join(quote(part, safe="") for part in relative_path.split("/"))


def should_skip_file(file_path: Path) -> bool:
    if file_path.name in SKIPPED_NAMES:
        return True
    if any(file_path.name.endswith(suffix) for suffix in SKIPPED_SUFFIXES):
        return True
    return ".mslauncher-staging" in file_path.parts


def is_zip_symlink(member: zipfile.ZipInfo) -> bool:
    file_type = (member.external_attr >> 16) & 0o170000
    return file_type == stat.S_IFLNK

