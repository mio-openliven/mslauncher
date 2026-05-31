from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generate_manifest import generate_build_config, generate_manifest
from remote_config import normalize_source_key


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def assert_manifest_contract(base_url: str) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        pack_path = Path(temp_dir) / "mslauncher"
        write_bytes(pack_path / "mods" / "some mod \u0442\u0435\u0441\u0442.jar", b"mod")
        write_bytes(pack_path / "config" / "file name.toml", b"config")
        write_bytes(pack_path / "resourcepacks" / "\u043f\u0430\u043a.zip", b"pack")

        manifest = generate_manifest(pack_path, base_url)
        build = generate_build_config(
            build_name="Main Server",
            minecraft_version="1.20.1",
            loader="fabric",
            loader_version="latest",
            base_url=base_url,
            output_manifest="manifest.json",
            server="play.example.com",
            port="25565",
        )

        assert build["manifest_url"] == "https://example.com/mslauncher/manifest.json"
        assert build["minecraft_version"] == "1.20.1"
        assert build["loader"] == "fabric"
        assert build["loader_version"] == "latest"
        assert build["server"] == "play.example.com"
        assert build["port"] == "25565"

        for item in manifest["files"]:
            assert "\\" not in item["path"]
            assert item["url"].startswith("https://example.com/mslauncher/")
            assert "//mods" not in item["url"]
            assert "//config" not in item["url"]
            assert "//resourcepacks" not in item["url"]

        urls = {item["path"]: item["url"] for item in manifest["files"]}
        assert urls["mods/some mod \u0442\u0435\u0441\u0442.jar"] == (
            "https://example.com/mslauncher/mods/some%20mod%20%D1%82%D0%B5%D1%81%D1%82.jar"
        )
        assert urls["config/file name.toml"] == "https://example.com/mslauncher/config/file%20name.toml"
        assert urls["resourcepacks/\u043f\u0430\u043a.zip"] == (
            "https://example.com/mslauncher/resourcepacks/%D0%BF%D0%B0%D0%BA.zip"
        )


def main() -> None:
    assert normalize_source_key("example.com") == "https://example.com/mslauncher/build.json"
    assert (
        normalize_source_key("https://example.com/mslauncher/build.json")
        == "https://example.com/mslauncher/build.json"
    )

    assert_manifest_contract("https://example.com/mslauncher")
    assert_manifest_contract("https://example.com/mslauncher/")

    readme_path = PROJECT_ROOT / "server_pack" / "README.txt"
    example_build_path = PROJECT_ROOT / "server_pack" / "build.example.json"
    assert readme_path.is_file()
    assert example_build_path.is_file()

    example_build = json.loads(example_build_path.read_text(encoding="utf-8"))
    assert example_build == {
        "name": "Main Server",
        "minecraft_version": "1.20.1",
        "loader": "fabric",
        "loader_version": "latest",
        "manifest_url": "https://example.com/mslauncher/manifest.json",
        "server": "play.example.com",
        "port": "25565",
    }

    print("remote server contract smoke test: OK")


if __name__ == "__main__":
    main()
