from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


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
    assert "backup-$timestamp" in script
    assert "sha256sum -c -" in script
    assert "Invoke-RestMethod" in script
    assert "password" not in script.lower()
    assert "sshpass" not in script.lower()
    assert "plink" not in script.lower()

    print("host upload script smoke test: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
