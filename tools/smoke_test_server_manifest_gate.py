from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MSLAUNCHER_USER_DATA_ROOT", str(Path(tempfile.gettempdir()) / "mslauncher-smoke"))

from gui import requires_server_manifest
from profile_manager import LauncherProfile


def main() -> None:
    server_profile = LauncherProfile("server", Path("server"), True)
    personal_profile = LauncherProfile("personal", Path("personal"), False)
    other_profile = LauncherProfile("other", Path("other"), False)

    assert requires_server_manifest(server_profile, "")
    assert requires_server_manifest(server_profile, "   ")
    resolved_empty_manifest_url = ""
    assert requires_server_manifest(server_profile, resolved_empty_manifest_url)
    assert not requires_server_manifest(server_profile, "https://example.com/manifest.json")
    assert not requires_server_manifest(personal_profile, "")
    assert not requires_server_manifest(other_profile, "")

    print("server manifest gate smoke test: OK")


if __name__ == "__main__":
    main()
