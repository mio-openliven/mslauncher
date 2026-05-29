from __future__ import annotations

import json
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from generate_manifest import generate_manifest
from gui import DownloadWorker, resolve_build_config
from launcher_core import MinecraftEngine


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_server(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_root:
        temp_path = Path(temp_root)
        server_path = temp_path / "server"
        client_path = temp_path / "client"

        write_text(server_path / "mods" / "good.jar", "good mod")
        write_text(server_path / "config" / "settings.toml", "enabled=true")
        write_text(server_path / "resourcepacks" / "pack.zip", "pack data")
        write_text(client_path / "mods" / "cheat.jar", "bad mod")
        write_text(client_path / "mods" / "good.jar", "old mod")

        server, base_url = run_server(server_path)

        try:
            manifest = generate_manifest(server_path, base_url)
            write_text(server_path / "manifest.json", json.dumps(manifest, ensure_ascii=False))
            write_text(
                server_path / "mslauncher" / "build.json",
                json.dumps(
                    {
                        "name": "Smoke Test",
                        "minecraft_version": "1.20.1",
                        "manifest_url": f"{base_url}/manifest.json",
                        "server": "127.0.0.1",
                        "port": "25565",
                    },
                    ensure_ascii=False,
                ),
            )

            build = resolve_build_config({"id": "main", "source_key": f"{base_url}/mslauncher/build.json"})
            engine = MinecraftEngine(client_path)
            files_to_download = engine.sync_files(str(build["manifest_url"]), client_path)

            if (client_path / "mods" / "cheat.jar").exists():
                raise AssertionError("Extra mod was not removed.")

            worker = DownloadWorker(engine, str(build["manifest_url"]), client_path)
            worker._download_files(files_to_download)

            expected_files = [
                client_path / "mods" / "good.jar",
                client_path / "config" / "settings.toml",
                client_path / "resourcepacks" / "pack.zip",
            ]

            missing_files = [path for path in expected_files if not path.is_file()]
            if missing_files:
                raise AssertionError(f"Missing downloaded files: {missing_files}")

            if (client_path / "mods" / "good.jar").read_text(encoding="utf-8") != "good mod":
                raise AssertionError("Outdated mod was not replaced.")

            print("sync smoke test: OK")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
