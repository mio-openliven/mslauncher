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
    assert "D17D011D64CFF1F523C4B2BFC45571D79002809BEB6D6D73E0ED81892D6A717E" in script
    assert "47AECEADCFD2A2E01456DB2B5507263BE2280505C785FD88DE379807434D27DA" in script
    assert "99ED2C3340E6795B45C9B04F9401A4227B26CE570BBFD7525F6BE79C091F7C56" in script
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
