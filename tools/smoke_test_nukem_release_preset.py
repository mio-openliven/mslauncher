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
    assert preset["social_links"]["nukem"]["youtube"] == "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98"
    assert preset["social_links"]["nukem"]["discord"] == "https://discord.com/invite/P35nvXQ"
    assert preset["project_access"]["nukem"]["password_enabled"] is True
    assert preset["project_access"]["nukem"]["password_hash_sha256"] == ""
    assert "admin_password_hash_sha256" in preset["project_access"]["nukem"]
    assert len(preset["news"]["nukem"]) <= 5

    builds = preset["builds"]
    assert len(builds) == 1
    build = builds[0]
    assert build["id"] == "nukem"
    assert build["name"] == "Nukem Project"
    assert build["loader"] == "fabric"
    assert build["source_key"] == "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json"
    assert build["source_key"].startswith("https://raw.githubusercontent.com/")
    assert "OWNER/REPO/BRANCH" in build["source_key"]

    prepare_script = prepare_script_path.read_text(encoding="utf-8")
    assert "[ValidateSet(\"default\", \"nukem\")]" in prepare_script
    assert "$Preset = \"default\"" in prepare_script
    assert "launcher_config.nukem.template.json" in prepare_script
    assert "Using preset: $Preset" in prepare_script

    docs_text = docs_path.read_text(encoding="utf-8")
    assert "OWNER" in docs_text
    assert "REPO" in docs_text
    assert "BRANCH" in docs_text
    assert "password_hash_sha256" in docs_text
    assert "публичный GitHub не скрывает файлы" in docs_text

    print("nukem release preset smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
