from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def extract_panel_files(script: str) -> list[str]:
    match = re.search(r"\$panelFiles\s*=\s*@\((.*?)\)", script, re.DOTALL)
    assert match, "upload script must declare panel source files"
    return re.findall(r'"([^"]+\.py)"', match.group(1))


def assert_panel_source_set_imports(panel_files: list[str]) -> None:
    assert "loader_support.py" in panel_files
    admin_panel_files = sorted(
        path.relative_to(PROJECT_ROOT).as_posix() for path in (PROJECT_ROOT / "admin_panel").glob("*.py")
    )
    expected_panel_files = ["loader_support.py", *admin_panel_files]
    assert sorted(panel_files) == sorted(expected_panel_files)

    with tempfile.TemporaryDirectory(prefix="mslaunch-panel-kit-") as temp_dir:
        staged_root = Path(temp_dir)
        for relative_path in panel_files:
            source_path = PROJECT_ROOT / relative_path
            target_path = staged_root / relative_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, target_path)

        env = os.environ.copy()
        env.pop("PYTHONPATH", None)
        subprocess.run(
            [sys.executable, "-c", "import admin_panel.app"],
            cwd=staged_root,
            env=env,
            check=True,
        )


def main() -> int:
    script_path = PROJECT_ROOT / "release" / "upload_host_artifacts.ps1"
    assert script_path.is_file()

    script = script_path.read_text(encoding="utf-8")
    assert "MSLaunchPayload.dat" in script
    assert "MSLaunchSetup.exe" in script
    assert "bootstrap.json" in script
    assert "C859A9338100F74D1A1F420C2F22209A4F0C4271F7B86170398DC08ADB341C37" in script
    assert "166E36D6075787FE310FA45AF1431E16DC7CB452133A54CD0D06C4D2922B04A3" in script
    assert "38E21AE303A524F616FA39A2D8BDCAE1EA9CA350739B5F313775780BB46F2971" in script
    assert "/opt/mslaunch/data/downloads" in script
    assert "/opt/mslaunch/app" in script
    assert "/opt/mslaunch/backups" in script
    assert "host-upload-$timestamp" in script
    assert "$RemoteDir/backup-$timestamp" not in script
    assert "downloadBackupDir" in script
    assert "appBackupDir" in script
    assert "sha256sum -c -" in script
    assert "Invoke-RestMethod" in script
    assert "AppRemoteDir" in script
    assert "systemctl restart mslaunch-panel.service" in script
    assert "systemctl is-active mslaunch-panel.service" in script
    assert "password" not in script.lower()
    assert "sshpass" not in script.lower()
    assert "plink" not in script.lower()

    panel_files = extract_panel_files(script)
    assert_panel_source_set_imports(panel_files)

    print("host upload script smoke test: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
