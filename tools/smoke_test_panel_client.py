from __future__ import annotations

import json
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from panel_client import get_panel_launcher_update, post_panel_report, resolve_panel_active_build


class Handler(SimpleHTTPRequestHandler):
    reports: list[dict[str, object]] = []

    def do_GET(self) -> None:
        if self.path == "/api/projects/nukem/active-build":
            self.send_json(
                {
                    "project": "nukem",
                    "build_id": "panel-build",
                    "name": "Panel Build",
                    "minecraft_version": "1.20.1",
                    "loader": "fabric",
                    "loader_version": "latest",
                    "manifest_url": f"http://127.0.0.1:{self.server.server_port}/manifest.json",
                    "server": "",
                    "port": "",
                }
            )
            return
        if self.path == "/api/launcher/update":
            self.send_json(
                {
                    "enabled": True,
                    "version": "1.9.1",
                    "download_url": f"http://127.0.0.1:{self.server.server_port}/MSLaunch.zip",
                    "sha256": "b" * 64,
                    "notes": "Panel update",
                }
            )
            return
        if self.path == "/manifest.json":
            self.send_json({"version": 1, "files": []})
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/reports":
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            Handler.reports.append(payload)
            self.send_json({"ok": True})
            return
        self.send_response(404)
        self.end_headers()

    def log_message(self, format: str, *args: object) -> None:
        return

    def send_json(self, payload: dict[str, object]) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> None:
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base_url = f"http://127.0.0.1:{server.server_port}"
        config = {
            "panel": {
                "enabled": True,
                "base_url": base_url,
                "project": "nukem",
                "timeout_seconds": 2,
            }
        }
        build = resolve_panel_active_build(config, "nukem", require_manifest=True)
        assert build["id"] == "panel-build"
        assert build["manifest_url"].startswith(base_url)

        update = get_panel_launcher_update(config)
        assert update["launcher_version"] == "1.9.1"
        assert update["launcher_download_url"].startswith(base_url)

        assert post_panel_report(config, {"project": "nukem", "error_type": "sync_failed"})
        assert Handler.reports[-1]["error_type"] == "sync_failed"

        assert resolve_panel_active_build({"panel": {"enabled": False}}, "nukem") == {}
    finally:
        server.shutdown()
        thread.join(timeout=3)

    print("panel client smoke test: OK")


if __name__ == "__main__":
    main()

