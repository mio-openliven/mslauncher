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
    assert "6AF86A819D500550A8C4462D17568FDAB577DC266D33D6B11558ED49EAF98B0C" in script
    assert "45E55F4B389925838E294770F8C3C2C95E57F118B64F246CF611DBB2EF5C2ABF" in script
    assert "95400D0F8CBF94676E0ED5E1281F7F9D42C55467D76A242778BCA8556207DD1E" in script
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
