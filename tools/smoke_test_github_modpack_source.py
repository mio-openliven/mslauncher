from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generate_manifest import generate_build_config, generate_manifest
from manifest_validator import ManifestValidationError, normalize_download_url
from remote_config import RemoteBuildConfigError, normalize_source_key, validate_build_config


RAW_BASE_URL = "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher"
RAW_BUILD_URL = f"{RAW_BASE_URL}/build.json"
RAW_MANIFEST_URL = f"{RAW_BASE_URL}/manifest.json"


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


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
    assert normalize_source_key(RAW_BUILD_URL) == RAW_BUILD_URL
    validate_build_config({"manifest_url": RAW_MANIFEST_URL})

    expect_remote_error(
        lambda: normalize_source_key("http://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json")
    )
    expect_manifest_error(
        lambda: normalize_download_url(
            "http://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/mods/good.jar",
            "mods/good.jar",
        )
    )

    with tempfile.TemporaryDirectory() as temp_dir:
        pack_path = Path(temp_dir) / "server_pack"
        write_bytes(pack_path / "mods" / "cool mod.jar", b"mod")
        write_bytes(pack_path / "config" / "client settings.toml", b"config")
        write_bytes(pack_path / "resourcepacks" / "models pack.zip", b"pack")

        manifest = generate_manifest(pack_path, RAW_BASE_URL)
        build = generate_build_config(
            build_name="Main Server",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="latest",
            base_url=RAW_BASE_URL,
            output_manifest="manifest.json",
            server="play.example.com",
            port="25565",
        )

    assert build["manifest_url"] == RAW_MANIFEST_URL
    urls = {item["path"]: item["url"] for item in manifest["files"]}
    assert urls["mods/cool mod.jar"] == f"{RAW_BASE_URL}/mods/cool%20mod.jar"
    assert urls["config/client settings.toml"] == f"{RAW_BASE_URL}/config/client%20settings.toml"
    assert urls["resourcepacks/models pack.zip"] == f"{RAW_BASE_URL}/resourcepacks/models%20pack.zip"
    assert all(url.startswith(RAW_BASE_URL) for url in urls.values())

    readme_text = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8")
    setup_text = (PROJECT_ROOT / "release" / "CLIENT_SETUP_RU.md").read_text(encoding="utf-8")
    assert "GitHub Modpack Hosting" in readme_text
    assert "raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json" in readme_text
    assert "client-side UI barrier" in readme_text
    assert "public GitHub repository does not hide files" in readme_text
    assert "GitHub-хостинг сборки" in setup_text
    assert "публичный GitHub не скрывает файлы" in setup_text
    assert "client-side барьер" in setup_text

    print("github modpack source smoke test: OK")


if __name__ == "__main__":
    main()
