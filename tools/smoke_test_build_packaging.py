from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    build_script = (PROJECT_ROOT / "build_exe.ps1").read_text(encoding="utf-8")
    spec_file = (PROJECT_ROOT / "MSLauncher.spec").read_text(encoding="utf-8")
    prepare_script = (PROJECT_ROOT / "release" / "prepare_release.ps1").read_text(encoding="utf-8")

    assert "function Invoke-ProjectPython" in build_script
    assert '& py -3 @Arguments' in build_script
    assert '& python @Arguments' in build_script
    assert 'Invoke-ProjectPython -Arguments @("-m", "PyInstaller", "--noconfirm", "MSLauncher.spec")' in build_script
    assert "--add-data" not in build_script
    assert "dist\\MSLauncher\\MSLauncher.exe" in build_script
    assert "Test-Path" in build_script
    assert "throw" in build_script

    assert "('assets', 'assets')" in spec_file
    assert "('launcher_config.json', '.')" in spec_file
    assert "release/CLIENT_SETUP_RU.md" in spec_file
    assert "release/NUKEM_SETUP_RU.md" in spec_file
    assert "release/PLAYER_README_RU.txt" in spec_file
    assert "release/RELEASE_CHECKLIST_RU.md" in spec_file
    assert "release/POST_RELEASE_BACKLOG_RU.md" in spec_file
    assert "release/launcher_config.nukem.template.json" in spec_file
    assert "console=False" in spec_file
    assert "name='MSLauncher'" in spec_file
    assert "contents_directory='.'" in spec_file

    assert (PROJECT_ROOT / "release" / "CLIENT_SETUP_RU.md").is_file()
    assert (PROJECT_ROOT / "release" / "NUKEM_SETUP_RU.md").is_file()
    assert (PROJECT_ROOT / "release" / "PLAYER_README_RU.txt").is_file()
    assert (PROJECT_ROOT / "release" / "RELEASE_CHECKLIST_RU.md").is_file()
    assert (PROJECT_ROOT / "release" / "POST_RELEASE_BACKLOG_RU.md").is_file()
    assert (PROJECT_ROOT / "release" / "launcher_config.template.json").is_file()
    assert "build_exe.ps1" in prepare_script
    assert "$Preset" in prepare_script
    assert "launcher_config.nukem.template.json" in prepare_script
    assert "NUKEM_SETUP_RU.md" in prepare_script
    assert "dist\\MSLauncher" in prepare_script
    assert "PLAYER_README_RU.txt" in prepare_script
    assert "POST_RELEASE_BACKLOG_RU.md" in prepare_script
    assert "docs" in prepare_script

    print("build packaging smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
