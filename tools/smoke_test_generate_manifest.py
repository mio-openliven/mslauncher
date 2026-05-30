from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        pack_path = Path(temp_dir) / "server_pack"
        mod_data = b"mod-bytes"
        config_data = b"config-bytes"
        pack_data = b"resource-pack-bytes"

        write_bytes(pack_path / "mods" / "cool mod \u0442\u0435\u0441\u0442.jar", mod_data)
        write_bytes(pack_path / "config" / "client settings.toml", config_data)
        write_bytes(pack_path / "resourcepacks" / "\u043c\u043e\u0434\u0435\u043b\u0438 pack.zip", pack_data)
        write_bytes(pack_path / "mods" / ".gitkeep", b"")
        write_bytes(pack_path / "mods" / "broken.jar.part", b"partial")
        write_bytes(pack_path / "mods" / ".mslauncher-staging" / "staged.jar", b"staged")

        subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "generate_manifest.py"),
                "--base-dir",
                str(pack_path),
                "--base-url",
                "https://example.com/mslauncher",
                "--minecraft-version",
                "1.20.1",
                "--loader",
                "fabric",
                "--server",
                "play.example.com",
                "--port",
                "25565",
                "--build-name",
                "Main Server",
            ],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

        manifest = json.loads((pack_path / "manifest.json").read_text(encoding="utf-8"))
        build = json.loads((pack_path / "build.json").read_text(encoding="utf-8"))

        files = {item["path"]: item for item in manifest["files"]}
        assert sorted(files) == [
            "config/client settings.toml",
            "mods/cool mod \u0442\u0435\u0441\u0442.jar",
            "resourcepacks/\u043c\u043e\u0434\u0435\u043b\u0438 pack.zip",
        ]

        mod_item = files["mods/cool mod \u0442\u0435\u0441\u0442.jar"]
        assert mod_item["sha256"] == sha256_bytes(mod_data)
        assert mod_item["size"] == len(mod_data)
        assert mod_item["url"] == (
            "https://example.com/mslauncher/mods/cool%20mod%20%D1%82%D0%B5%D1%81%D1%82.jar"
        )

        config_item = files["config/client settings.toml"]
        assert config_item["sha256"] == sha256_bytes(config_data)
        assert config_item["size"] == len(config_data)
        assert config_item["url"] == "https://example.com/mslauncher/config/client%20settings.toml"

        resource_item = files["resourcepacks/\u043c\u043e\u0434\u0435\u043b\u0438 pack.zip"]
        assert resource_item["sha256"] == sha256_bytes(pack_data)
        assert resource_item["size"] == len(pack_data)
        assert resource_item["url"] == (
            "https://example.com/mslauncher/resourcepacks/%D0%BC%D0%BE%D0%B4%D0%B5%D0%BB%D0%B8%20pack.zip"
        )

        assert build["name"] == "Main Server"
        assert build["minecraft_version"] == "1.20.1"
        assert build["loader"] == "fabric"
        assert build["loader_version"] == "latest"
        assert build["manifest_url"] == "https://example.com/mslauncher/manifest.json"
        assert build["server"] == "play.example.com"
        assert build["port"] == "25565"

        missing_url_result = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "generate_manifest.py"),
                "--base-dir",
                str(pack_path),
                "--output-manifest",
                "manifest-empty-url.json",
                "--output-build",
                "build-empty-url.json",
            ],
            cwd=str(PROJECT_ROOT),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert "WARNING: --base-url is empty" in missing_url_result.stdout
        empty_url_manifest = json.loads((pack_path / "manifest-empty-url.json").read_text(encoding="utf-8"))
        assert all(item["url"] == "" for item in empty_url_manifest["files"])

        bad_loader = subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "generate_manifest.py"),
                "--base-dir",
                str(pack_path),
                "--loader",
                "forge",
            ],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        assert bad_loader.returncode != 0
        assert "loader must be vanilla or fabric" in bad_loader.stderr

    print("generate manifest smoke test: OK")


if __name__ == "__main__":
    main()
