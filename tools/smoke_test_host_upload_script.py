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
    assert "D25FB662A47EA4EF346F680B2F4FD00C626A629EDD2DFC48C8674E4AE07744ED" in script
    assert "921AA8902A0FEF513930C935AE0D7825B9ADADE0510B52377095700F45810B94" in script
    assert "F4D6101A8404C17744F07C6B7408DDD6DBF5C3E3B7FC70E09997296868C5C534" in script
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
