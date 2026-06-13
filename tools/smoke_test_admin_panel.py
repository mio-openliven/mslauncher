from __future__ import annotations

import hashlib
import os
import sys
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    smoke_test_panel_client_fallbacks()

    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["MSLAUNCH_PANEL_DATA"] = str(Path(temp_dir) / "panel_data")
        os.environ["MSLAUNCH_PANEL_SECRET"] = "smoke-secret"
        installer_bytes = b"installer-data"
        installer_sha256 = hashlib.sha256(installer_bytes).hexdigest().upper()
        downloads_root = Path(os.environ["MSLAUNCH_PANEL_DATA"]) / "downloads"
        downloads_root.mkdir(parents=True, exist_ok=True)
        (downloads_root / "MSLaunchSetup.exe").write_bytes(installer_bytes)

        from fastapi.testclient import TestClient

        from admin_panel.app import app
        from admin_panel.cli import create_user

        create_user("li2fly", "owner", "secret")
        create_user("SKELET", "project_admin", "nukem-secret", project_slug="nukem")
        archive_path = Path(temp_dir) / "pack.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("mods/example.jar", b"jar-data")
            archive.writestr("config/settings.toml", b"enabled=true")

        with TestClient(app) as client:
            client_page = client.get("/client")
            assert client_page.status_code == 200
            assert "MSLaunchSetup.exe" in client_page.text
            assert 'href="/login?next=/"' in client_page.text
            assert "Панель проекта" in client_page.text
            assert installer_sha256 in client_page.text
            stale_checksum = "C493BCBBA070657F7E4861D8CEEDDD05076ED1A24888A1836" "C1CA069003FA5CD"
            assert stale_checksum not in client_page.text

            installer = client.get("/downloads/MSLaunchSetup.exe")
            assert installer.status_code == 200
            assert installer.content == installer_bytes

            builds_redirect = client.get("/builds", follow_redirects=False)
            assert builds_redirect.status_code == 303
            assert builds_redirect.headers["location"] == "/login?next=%2Fbuilds"

            login_page = client.get("/login?next=/builds")
            assert login_page.status_code == 200
            assert 'name="next" type="hidden" value="/builds"' in login_page.text

            panel_login = client.post(
                "/login",
                data={"username": "li2fly", "password": "secret", "next": "/builds"},
                follow_redirects=False,
            )
            assert panel_login.status_code == 303
            assert panel_login.headers["location"] == "/builds"

            logout = client.post("/logout", follow_redirects=False)
            assert logout.status_code == 303

            unsafe_login = client.post(
                "/login",
                data={"username": "li2fly", "password": "secret", "next": "https://example.invalid/client"},
                follow_redirects=False,
            )
            assert unsafe_login.status_code == 303
            assert unsafe_login.headers["location"] == "/"

            logout = client.post("/logout", follow_redirects=False)
            assert logout.status_code == 303

            login = client.post(
                "/login",
                data={"username": "li2fly", "password": "secret"},
                follow_redirects=False,
            )
            assert login.status_code == 303
            assert login.headers["location"] == "/"

            with archive_path.open("rb") as file:
                created = client.post(
                    "/builds/create",
                    data={
                        "project_slug": "nukem",
                        "build_id": "nukem-test",
                        "name": "Nukem Test",
                        "minecraft_version": "1.20.1",
                        "loader": "fabric",
                        "loader_version": "latest",
                        "server": "",
                        "port": "",
                        "access_password": "pack-secret",
                        "make_active": "1",
                    },
                    files={"archive": ("pack.zip", file, "application/zip")},
                    follow_redirects=False,
                )
            assert created.status_code == 303

            active = client.get("/api/projects/nukem/active-build")
            assert active.status_code == 200
            active_data = active.json()
            assert active_data["build_id"] == "nukem-test"
            assert active_data["minecraft_version"] == "1.20.1"
            assert active_data["access_required"] is True

            manifest = client.get("/api/projects/nukem/builds/nukem-test/manifest.json")
            assert manifest.status_code == 403

            wrong_access = client.post(
                "/api/projects/nukem/builds/nukem-test/access",
                json={"password": "wrong"},
            )
            assert wrong_access.status_code == 403

            access = client.post(
                "/api/projects/nukem/builds/nukem-test/access",
                json={"password": "pack-secret"},
            )
            assert access.status_code == 200
            access_data = access.json()
            token = access_data["access_token"]
            assert token

            manifest = client.get(f"/api/projects/nukem/builds/nukem-test/manifest.json?access={token}")
            assert manifest.status_code == 200
            files = manifest.json()["files"]
            assert len(files) == 2
            assert {item["path"] for item in files} == {"mods/example.jar", "config/settings.toml"}
            assert all("access=" in item["url"] for item in files)

            downloaded = client.get(f"/files/nukem/nukem-test/mods/example.jar?access={token}")
            assert downloaded.status_code == 200
            assert downloaded.content == b"jar-data"

            update = client.post(
                "/updates/create",
                data={
                    "version": "1.9.1",
                    "download_url": "https://example.com/MSLaunch.zip",
                    "sha256": "a" * 64,
                    "notes": "Smoke",
                    "enabled": "1",
                },
                follow_redirects=False,
            )
            assert update.status_code == 303
            update_api = client.get("/api/launcher/update")
            assert update_api.status_code == 200
            assert update_api.json()["version"] == "1.9.1"

            report = client.post(
                "/api/reports",
                json={
                    "project": "nukem",
                    "build_id": "nukem-test",
                    "username": "Player",
                    "launcher_version": "1.9.0",
                    "error_type": "sync_failed",
                    "user_message": "Could not sync",
                    "technical_details": "details",
                },
            )
            assert report.status_code == 200
            reports_page = client.get("/reports")
            assert "sync_failed" in reports_page.text

            logout = client.post("/logout", follow_redirects=False)
            assert logout.status_code == 303
            login = client.post(
                "/login",
                data={"username": "SKELET", "password": "nukem-secret"},
                follow_redirects=False,
            )
            assert login.status_code == 303
            dashboard = client.get("/")
            assert "MS Nuckem" in dashboard.text
            assert "VibeCraft" not in dashboard.text
            builds_page = client.get("/builds")
            assert "MS Nuckem" in builds_page.text
            assert "VibeCraft" not in builds_page.text
            forbidden = client.post(
                "/builds/create",
                data={
                    "project_slug": "vibecraft",
                    "build_id": "vc-test",
                    "name": "Vibe Test",
                    "minecraft_version": "1.20.1",
                    "loader": "vanilla",
                },
                follow_redirects=False,
            )
            assert forbidden.status_code == 403

    print("admin panel smoke test: OK")


def smoke_test_panel_client_fallbacks() -> None:
    from panel_client import (
        get_panel_launcher_update,
        resolve_panel_active_build,
    )

    github_build = {
        "id": "main",
        "name": "GitHub fallback",
        "minecraft_version": "1.20.1",
        "loader": "fabric",
        "loader_version": "latest",
        "source_key": "https://raw.githubusercontent.com/mio-openliven/MSNukem/main/build.json",
        "manifest_url": "",
    }
    disabled_config = {"panel": {"enabled": False, "base_url": ""}, "builds": [github_build]}
    missing_url_config = {"panel": {"enabled": True, "base_url": ""}, "builds": [github_build]}
    enabled_config = {
        "panel": {
            "enabled": True,
            "base_url": "https://panel.example",
            "project": "nukem",
            "timeout_seconds": 1,
        },
        "builds": [github_build],
    }

    assert resolve_panel_active_build(disabled_config, "nukem") == {}
    assert resolve_panel_active_build(missing_url_config, "nukem") == {}
    assert get_panel_launcher_update(disabled_config) == {}
    assert get_panel_launcher_update(missing_url_config) == {}

    class NotFoundResponse:
        status_code = 404

        def raise_for_status(self) -> None:
            raise AssertionError("404 must be handled as fallback before raise_for_status.")

        def json(self) -> dict[str, object]:
            raise AssertionError("404 fallback must not parse JSON.")

    with patch("panel_client.requests.get", return_value=NotFoundResponse()) as request_get:
        assert resolve_panel_active_build(enabled_config, "nukem") == {}
        assert get_panel_launcher_update(enabled_config) == {}
        requested_urls = [call.args[0] for call in request_get.call_args_list]
        assert requested_urls == [
            "https://panel.example/api/projects/nukem/active-build",
            "https://panel.example/api/launcher/update",
        ]


if __name__ == "__main__":
    main()
