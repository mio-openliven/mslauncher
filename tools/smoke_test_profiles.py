from __future__ import annotations

import tempfile
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from profile_manager import MANAGED_MARKER, LauncherProfileManager


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        original_user_data = os.environ.get("MSLAUNCHER_USER_DATA_ROOT")
        os.environ["MSLAUNCHER_USER_DATA_ROOT"] = str(Path(temp_dir) / "userdata")
        try:
            manager = LauncherProfileManager()
            assert manager.base_directory == Path(temp_dir) / "userdata" / "instances"

            server = manager.get_profile("server")
            personal = manager.get_profile("personal")
            other = manager.get_profile("other")
            fallback = manager.get_profile("unknown")

            assert server.server_sync_enabled is True
            assert personal.server_sync_enabled is False
            assert other.server_sync_enabled is False
            assert fallback.profile_id == "server"

            for profile in (server, personal, other):
                assert profile.directory.is_dir()
                assert (profile.directory / "mods").is_dir()
                assert (profile.directory / "config").is_dir()
                assert (profile.directory / "resourcepacks").is_dir()
                assert (profile.directory / "saves").is_dir()
                assert (profile.directory / MANAGED_MARKER).is_file()
                assert manager.is_managed_profile(profile.directory)
        finally:
            if original_user_data is None:
                os.environ.pop("MSLAUNCHER_USER_DATA_ROOT", None)
            else:
                os.environ["MSLAUNCHER_USER_DATA_ROOT"] = original_user_data

    print("profile smoke test: OK")


if __name__ == "__main__":
    main()
