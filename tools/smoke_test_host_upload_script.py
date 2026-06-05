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
    assert "8432DD1AF8A0134EAF79F85886AA4C52FFF3189EBFA32BCE7336F41248164174" in script
    assert "C5F2AD47B720AA4460C477F7E5CEFE95F36655FE1C33116BAF4907BA1E4838E3" in script
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
