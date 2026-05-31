from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    release_path = PROJECT_ROOT / "release"
    template_path = release_path / "launcher_config.template.json"
    setup_path = release_path / "CLIENT_SETUP_RU.md"
    checklist_path = release_path / "RELEASE_CHECKLIST_RU.md"
    helper_path = release_path / "prepare_release.ps1"

    assert template_path.is_file()
    assert setup_path.is_file()
    assert checklist_path.is_file()
    assert helper_path.is_file()

    template = json.loads(template_path.read_text(encoding="utf-8"))
    builds = template.get("builds")
    assert isinstance(builds, list)
    assert len(builds) == 1

    build = builds[0]
    assert build["id"] == "main"
    assert build["source_key"] == "example.com"
    assert not str(build["source_key"]).lower().startswith("http://")
    assert build["loader"] == "fabric"
    assert build["minecraft_version"] == "1.20.1"
    assert template["launch"]["memory_max"] == "4G"
    assert template["launch"]["loader"] == "fabric"

    checklist_text = checklist_path.read_text(encoding="utf-8")
    assert "Windows без Python" in checklist_text
    assert "source_key" in checklist_text

    setup_text = setup_path.read_text(encoding="utf-8")
    assert "build.json" in setup_text
    assert "server_pack/mods" in setup_text
    assert "dist\\MSLauncher" in setup_text

    print("release package smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
