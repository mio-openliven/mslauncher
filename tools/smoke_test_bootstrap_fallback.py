from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bootstrapper


EXPECTED_PAYLOAD_NAME = "MSLaunchPayload.dat"
EXPECTED_PAYLOAD_SHA = "d17d011d64cff1f523c4b2bfc45571d79002809beb6d6d73e0ed81892d6a717e"


def main() -> None:
    assert bootstrapper.PACKAGE_NAME == EXPECTED_PAYLOAD_NAME
    assert bootstrapper.PACKAGE_SHA256 == EXPECTED_PAYLOAD_SHA
    assert bootstrapper.SOURCES
    assert all(source[2] == EXPECTED_PAYLOAD_SHA for source in bootstrapper.SOURCES)
    assert any(EXPECTED_PAYLOAD_NAME in source[1] for source in bootstrapper.SOURCES)

    setup_source = (PROJECT_ROOT / "setup_bootstrapper" / "MSLaunchSetup.cs").read_text(encoding="utf-8")
    assert f'private const string PackageName = "{EXPECTED_PAYLOAD_NAME}";' in setup_source
    assert f'private const string PackageSha256 = "{EXPECTED_PAYLOAD_SHA}";' in setup_source
    assert "MSLaunch-1.9.0-beta.zip" not in setup_source

    print("bootstrap fallback smoke test: OK")


if __name__ == "__main__":
    main()
