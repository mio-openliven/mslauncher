from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    release_path = PROJECT_ROOT / "release"
    preset_path = release_path / "launcher_config.nukem.template.json"
    docs_path = release_path / "NUKEM_SETUP_RU.md"
    prepare_script_path = release_path / "prepare_release.ps1"

    assert preset_path.is_file()
    assert docs_path.is_file()
    assert prepare_script_path.is_file()

    preset = json.loads(preset_path.read_text(encoding="utf-8"))
    assert preset["client_mode"] == "nukem"
    assert preset["default_language"] == "RU"
    assert preset["default_build"] == "nukem"
    assert preset["launch"]["loader"] == "fabric"
    assert preset["social_links"]["nukem"]["youtube"] == "https://www.youtube.com/@Nuckem"
    assert preset["social_links"]["nukem"]["discord"] == "https://discord.gg/P35nvXQ"
    assert preset["social_links"]["nukem"]["vk_group"] == "https://vk.com/nuckem_garage"
    assert preset["panel"]["enabled"] is True
    assert preset["panel"]["base_url"] == "https://mslaunch.186.246.12.238.sslip.io"
    assert preset["project_access"]["nukem"]["password_enabled"] is True
    assert (
        preset["project_access"]["nukem"]["password_hash_sha256"]
        == "b49c430845403cc609360a61bf424ce7bd01bad57b1aadb6794c76dcd07be0ef"
    )
    assert (
        preset["project_access"]["nukem"]["build_passwords"]["nukem"]
        == "b49c430845403cc609360a61bf424ce7bd01bad57b1aadb6794c76dcd07be0ef"
    )
    assert "admin_password_hash_sha256" in preset["project_access"]["nukem"]
    assert len(preset["news"]["nukem"]) <= 5

    builds = preset["builds"]
    assert len(builds) == 1
    build = builds[0]
    assert build["id"] == "nukem"
    assert build["name"] == "Nukem Project"
    assert build["loader"] == "fabric"
    assert build["minecraft_version"] == "1.20.1"
    assert build["source_key"] == "https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json"
    assert build["source_key"].startswith("https://raw.githubusercontent.com/")
    assert "OWNER/REPO/BRANCH" not in build["source_key"]

    prepare_script = prepare_script_path.read_text(encoding="utf-8")
    assert "[ValidateSet(\"default\", \"nukem\")]" in prepare_script
    assert "$Preset = \"default\"" in prepare_script
    assert "launcher_config.nukem.template.json" in prepare_script
    assert "Using preset: $Preset" in prepare_script

    docs_text = docs_path.read_text(encoding="utf-8")
    assert "mio-openliven/MSNukem" in docs_text
    assert "password_hash_sha256" in docs_text
    assert "публичный GitHub не скрывает файлы" in docs_text

    print("nukem release preset smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
