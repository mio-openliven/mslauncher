from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.inspect_client_pack import ClientPackInspectionError, inspect_archive


def write_zip(path: Path, files: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)


def make_fabric_jar() -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        jar_path = Path(temp_dir) / "fabric-api.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr(
                "fabric.mod.json",
                json.dumps(
                    {
                        "schemaVersion": 1,
                        "id": "fabric-api",
                        "depends": {"minecraft": ">=1.20.1 <1.21"},
                    }
                ),
            )
        return jar_path.read_bytes()


def make_forge_jar() -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        jar_path = Path(temp_dir) / "forge-mod.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr(
                "META-INF/mods.toml",
                'modLoader="javafml"\n[[dependencies.example]]\nmodId="minecraft"\nversionRange="[1.19.2,1.20)"\n',
            )
        return jar_path.read_bytes()


def make_quilt_jar() -> bytes:
    with tempfile.TemporaryDirectory() as temp_dir:
        jar_path = Path(temp_dir) / "quilt-mod.jar"
        with zipfile.ZipFile(jar_path, "w") as jar:
            jar.writestr(
                "quilt.mod.json",
                json.dumps(
                    {
                        "schema_version": 1,
                        "quilt_loader": {
                            "id": "quilt_example",
                            "depends": [{"id": "minecraft", "versions": "1.20.1"}],
                        },
                    }
                ),
            )
        return jar_path.read_bytes()


def expect_inspection_error(callback) -> None:
    try:
        callback()
    except ClientPackInspectionError:
        return
    raise AssertionError("Expected ClientPackInspectionError")


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)

        fabric_archive = root / "fabric.zip"
        fabric_report_path = root / "fabric-report.md"
        write_zip(
            fabric_archive,
            {
                "mods/fabric-api.jar": make_fabric_jar(),
                "config/settings.toml": b"key=true",
                "resourcepacks/pack/pack.mcmeta": b'{"pack":{"pack_format":15}}',
            },
        )
        fabric_report = inspect_archive(fabric_archive, output_path=fabric_report_path)
        assert fabric_report.loader_guess == "fabric"
        assert fabric_report.confidence == "high"
        assert fabric_report.mod_count == 1
        assert "1.20.1" in fabric_report.possible_versions
        assert fabric_report_path.is_file()
        assert "Loader guess: `fabric`" in fabric_report_path.read_text(encoding="utf-8")

        extract_target = root / "server_pack"
        extracted_report = inspect_archive(fabric_archive, output_path=root / "extract-report.md", extract_to=extract_target)
        assert (extract_target / "mods" / "fabric-api.jar").is_file()
        assert (extract_target / "config" / "settings.toml").is_file()
        assert extracted_report.extracted_files

        forge_archive = root / "forge.zip"
        write_zip(forge_archive, {"minecraft/mods/forge-mod.jar": make_forge_jar()})
        forge_report = inspect_archive(forge_archive, output_path=root / "forge-report.md")
        assert forge_report.loader_guess == "forge"
        assert "1.19.2" in forge_report.possible_versions

        quilt_archive = root / "quilt.zip"
        write_zip(quilt_archive, {"mods/quilt-mod.jar": make_quilt_jar()})
        quilt_report = inspect_archive(quilt_archive, output_path=root / "quilt-report.md")
        assert quilt_report.loader_guess == "quilt"
        assert "1.20.1" in quilt_report.possible_versions

        traversal_archive = root / "traversal.zip"
        write_zip(traversal_archive, {"../evil.txt": b"nope"})
        expect_inspection_error(lambda: inspect_archive(traversal_archive, output_path=root / "bad-report.md"))
        assert "unsafe path" in (root / "bad-report.md").read_text(encoding="utf-8")

        empty_archive = root / "empty.zip"
        write_zip(empty_archive, {})
        empty_report_path = root / "empty-report.md"
        empty_report = inspect_archive(empty_archive, output_path=empty_report_path)
        assert empty_report.loader_guess == "unknown"
        assert empty_report.mod_count == 0
        assert "No mod jars found" in empty_report_path.read_text(encoding="utf-8")

        rar_archive = root / "pack.rar"
        rar_archive.write_bytes(b"not a real rar")
        expect_inspection_error(
            lambda: inspect_archive(rar_archive, output_path=root / "rar-report.md", rar_candidates=[])
        )
        assert "Install 7-Zip" in (root / "rar-report.md").read_text(encoding="utf-8")

    print("client pack inspector smoke test: OK")


if __name__ == "__main__":
    main()
