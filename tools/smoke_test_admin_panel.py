from __future__ import annotations

import os
import sys
import tempfile
import zipfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        os.environ["MSLAUNCH_PANEL_DATA"] = str(Path(temp_dir) / "panel_data")
        os.environ["MSLAUNCH_PANEL_SECRET"] = "smoke-secret"

        from fastapi.testclient import TestClient

        from admin_panel.app import app
        from admin_panel.cli import create_user

        create_user("li2fly", "owner", "secret")
        archive_path = Path(temp_dir) / "pack.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            archive.writestr("mods/example.jar", b"jar-data")
            archive.writestr("config/settings.toml", b"enabled=true")

        with TestClient(app) as client:
            login = client.post(
                "/login",
                data={"username": "li2fly", "password": "secret"},
                follow_redirects=False,
            )
            assert login.status_code == 303

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

            manifest = client.get("/api/projects/nukem/builds/nukem-test/manifest.json")
            assert manifest.status_code == 200
            files = manifest.json()["files"]
            assert len(files) == 2
            assert {item["path"] for item in files} == {"mods/example.jar", "config/settings.toml"}

            downloaded = client.get("/files/nukem/nukem-test/mods/example.jar")
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

    print("admin panel smoke test: OK")


if __name__ == "__main__":
    main()

