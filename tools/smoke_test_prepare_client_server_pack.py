from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.prepare_client_server_pack import PrepareClientPackError, prepare_server_pack


RAW_BASE_URL = "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher"


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def make_fabric_jar(name: str = "fabric-api", minecraft: str | None = "1.20.1") -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        jar_path = Path(temp_dir) / "fabric.jar"
        data: dict[str, object] = {"schemaVersion": 1, "id": name}
        if minecraft is not None:
            data["depends"] = {"minecraft": minecraft}
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr("fabric.mod.json", json.dumps(data))
        return jar_path.read_bytes()


def make_forge_jar(version: str = "1.20.1") -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        jar_path = Path(temp_dir) / "forge.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr(
                "META-INF/mods.toml",
                f'modLoader="javafml"\nmodId="example"\nversionRange="[{version}]"\n',
            )
        return jar_path.read_bytes()


def expect_prepare_error(callback) -> str:
    try:
        callback()
    except PrepareClientPackError as exc:
        return str(exc)
    raise AssertionError("Expected PrepareClientPackError")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        archive = root / "fabric.zip"
        write_zip(
            archive,
            {
                "mods/fabric-api.jar": make_fabric_jar(),
                "mods/download.tmp": b"skip",
                "mods/partial.jar.part": b"skip",
                "config/settings.toml": b"enabled=true",
                "resourcepacks/pack.zip": b"pack",
            },
        )

        output_dir = root / "server_pack"
        (output_dir / "mods").mkdir(parents=True)
        (output_dir / "mods" / "old.jar").write_bytes(b"old")
        (output_dir / "keep.txt").write_text("keep", encoding="utf-8")
        outside = root / "outside.txt"
        outside.write_text("outside", encoding="utf-8")

        result = prepare_server_pack(
            archive_path=archive,
            output_dir=output_dir,
            base_url=RAW_BASE_URL,
            build_name="Nukem Project",
            server="play.example.com",
            port="25565",
            clean=True,
            report_path=root / "prepare-report.md",
        )

        assert result.loader == "fabric"
        assert result.minecraft_version == "1.20.1"
        assert (output_dir / "mods" / "fabric-api.jar").is_file()
        assert not (output_dir / "mods" / "old.jar").exists()
        assert not (output_dir / "mods" / "download.tmp").exists()
        assert not (output_dir / "mods" / "partial.jar.part").exists()
        assert (output_dir / "keep.txt").read_text(encoding="utf-8") == "keep"
        assert outside.read_text(encoding="utf-8") == "outside"

        manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
        build = json.loads((output_dir / "build.json").read_text(encoding="utf-8"))
        urls = {item["path"]: item["url"] for item in manifest["files"]}
        assert urls["mods/fabric-api.jar"] == f"{RAW_BASE_URL}/mods/fabric-api.jar"
        assert urls["config/settings.toml"] == f"{RAW_BASE_URL}/config/settings.toml"
        assert urls["resourcepacks/pack.zip"] == f"{RAW_BASE_URL}/resourcepacks/pack.zip"
        assert build["name"] == "Nukem Project"
        assert build["minecraft_version"] == "1.20.1"
        assert build["loader"] == "fabric"
        assert build["manifest_url"] == f"{RAW_BASE_URL}/manifest.json"
        assert build["server"] == "play.example.com"
        assert build["port"] == "25565"
        assert "git add server_pack" in (root / "prepare-report.md").read_text(encoding="utf-8")

        unknown_archive = root / "unknown.zip"
        write_zip(unknown_archive, {"mods/fabric-api.jar": make_fabric_jar(minecraft=None)})
        error = expect_prepare_error(
            lambda: prepare_server_pack(
                archive_path=unknown_archive,
                output_dir=root / "unknown_output",
                base_url=RAW_BASE_URL,
                loader="fabric",
                report_path=root / "unknown-report.md",
            )
        )
        assert "Minecraft version is unknown" in error

        forge_archive = root / "forge.zip"
        write_zip(
            forge_archive,
            {
                "mods/forge-one.jar": make_forge_jar(),
                "mods/forge-two.jar": make_forge_jar(),
            },
        )
        error = expect_prepare_error(
            lambda: prepare_server_pack(
                archive_path=forge_archive,
                output_dir=root / "forge_output",
                base_url=RAW_BASE_URL,
                report_path=root / "forge-report.md",
            )
        )
        assert "supports vanilla/fabric only" in error

    print("prepare client server pack smoke test: OK")


if __name__ == "__main__":
    main()
