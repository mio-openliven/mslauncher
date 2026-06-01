from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    release_path = PROJECT_ROOT / "release"
    template_path = release_path / "launcher_config.template.json"
    nukem_template_path = release_path / "launcher_config.nukem.template.json"
    setup_path = release_path / "CLIENT_SETUP_RU.md"
    nukem_setup_path = release_path / "NUKEM_SETUP_RU.md"
    player_readme_path = release_path / "PLAYER_README_RU.txt"
    checklist_path = release_path / "RELEASE_CHECKLIST_RU.md"
    backlog_path = release_path / "POST_RELEASE_BACKLOG_RU.md"
    helper_path = release_path / "prepare_release.ps1"

    assert template_path.is_file()
    assert nukem_template_path.is_file()
    assert setup_path.is_file()
    assert nukem_setup_path.is_file()
    assert player_readme_path.is_file()
    assert checklist_path.is_file()
    assert backlog_path.is_file()
    assert helper_path.is_file()

    template = json.loads(template_path.read_text(encoding="utf-8"))
    builds = template.get("builds")
    assert isinstance(builds, list)
    assert len(builds) == 1

    build = builds[0]
    assert build["id"] == "main"
    assert build["source_key"] == "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json"
    assert not str(build["source_key"]).lower().startswith("http://")
    assert build["loader"] == "fabric"
    assert build["minecraft_version"] == "1.20.1"
    assert template["launch"]["memory_max"] == "4G"
    assert template["launch"]["loader"] == "fabric"

    nukem_template = json.loads(nukem_template_path.read_text(encoding="utf-8"))
    nukem_builds = nukem_template.get("builds")
    assert isinstance(nukem_builds, list)
    assert len(nukem_builds) == 1
    assert nukem_template["client_mode"] == "nukem"
    assert nukem_template["default_build"] == "nukem"
    assert nukem_template["social_links"]["nukem"]["youtube"] == "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98"
    assert nukem_template["social_links"]["nukem"]["discord"] == "https://discord.com/invite/P35nvXQ"
    assert nukem_template["project_access"]["nukem"]["password_enabled"] is True
    assert nukem_template["project_access"]["nukem"]["password_hash_sha256"] == ""
    assert "admin_password_hash_sha256" in nukem_template["project_access"]["nukem"]
    assert len(nukem_template["news"]["nukem"]) <= 5
    assert nukem_builds[0]["id"] == "nukem"
    assert nukem_builds[0]["name"] == "Nukem Project"
    assert nukem_builds[0]["source_key"] == "https://raw.githubusercontent.com/OWNER/REPO/BRANCH/mslauncher/build.json"

    checklist_text = checklist_path.read_text(encoding="utf-8")
    backlog_text = backlog_path.read_text(encoding="utf-8")
    assert "Windows без Python" in checklist_text
    assert "source_key" in checklist_text
    assert "GitHub" in checklist_text
    assert "UI-барьер" in checklist_text
    assert "POST_RELEASE_BACKLOG_RU.md" in checklist_text
    assert "Bundled Java" in backlog_text
    assert "manifest.json" in backlog_text
    assert "Content-Length" in backlog_text
    assert "System Check" in backlog_text
    assert "не должен автоматически удалять" in backlog_text

    setup_text = setup_path.read_text(encoding="utf-8")
    nukem_setup_text = nukem_setup_path.read_text(encoding="utf-8")
    player_readme_text = player_readme_path.read_text(encoding="utf-8")
    assert "build.json" in setup_text
    assert "manifest.json" in setup_text
    assert "source_key" in setup_text
    assert "raw.githubusercontent.com" in setup_text
    assert "публичный GitHub не скрывает файлы" in setup_text
    assert "client-side барьер" in setup_text
    assert "server_pack" in setup_text
    assert "server_pack/mods" in setup_text
    assert "dist\\MSLauncher" in setup_text
    assert "MSLauncher.exe" in player_readme_text
    assert "mslauncher-last-error.txt" in player_readme_text
    assert "prepare_release.ps1 -Preset nukem" in nukem_setup_text
    assert "password_hash_sha256" in nukem_setup_text
    assert "публичный GitHub не скрывает файлы" in nukem_setup_text

    print("release package smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
