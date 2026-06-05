from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import bootstrapper


EXPECTED_PAYLOAD_NAME = "MSLaunchPayload.dat"
EXPECTED_PAYLOAD_SHA = "c859a9338100f74d1a1f420c2f22209a4f0c4271f7b86170398dc08adb341c37"


def main() -> None:
    assert bootstrapper.PACKAGE_NAME == EXPECTED_PAYLOAD_NAME
    assert bootstrapper.PACKAGE_SHA256 == EXPECTED_PAYLOAD_SHA
    assert bootstrapper.SOURCES
    assert all(source[2] == EXPECTED_PAYLOAD_SHA for source in bootstrapper.SOURCES)
    assert any(EXPECTED_PAYLOAD_NAME in source[1] for source in bootstrapper.SOURCES)
    assert any("/v1.9.7/bootstrap.json" in url for url in bootstrapper.BOOTSTRAP_MANIFESTS)
    assert any("/v1.9.7/MSLaunchPayload.dat" in source[1] for source in bootstrapper.SOURCES)
    assert bootstrapper.parse_bootstrap_manifest(
        {
            "package_name": EXPECTED_PAYLOAD_NAME,
            "package_sha256": "0" * 64,
            "sources": [
                {
                    "name": "Stale",
                    "url": "https://example.com/MSLaunchPayload.dat",
                    "sha256": "0" * 64,
                }
            ],
        }
    ) == []
    assert bootstrapper.parse_bootstrap_manifest(
        {
            "package_name": EXPECTED_PAYLOAD_NAME,
            "package_sha256": EXPECTED_PAYLOAD_SHA,
            "sources": [
                {
                    "name": "GitHub",
                    "url": "https://example.com/MSLaunchPayload.dat",
                    "sha256": EXPECTED_PAYLOAD_SHA,
                }
            ],
        }
    ) == [("GitHub", "https://example.com/MSLaunchPayload.dat", EXPECTED_PAYLOAD_SHA)]

    setup_source = (PROJECT_ROOT / "setup_bootstrapper" / "MSLaunchSetup.cs").read_text(encoding="utf-8")
    assert f'private const string PackageName = "{EXPECTED_PAYLOAD_NAME}";' in setup_source
    assert f'private const string PackageSha256 = "{EXPECTED_PAYLOAD_SHA}";' in setup_source
    assert "MSLaunch-1.9.0-beta.zip" not in setup_source
    assert "/v1.9.7/bootstrap.json" in setup_source
    assert "/v1.9.7/MSLaunchPayload.dat" in setup_source

    print("bootstrap fallback smoke test: OK")


if __name__ == "__main__":
    main()
