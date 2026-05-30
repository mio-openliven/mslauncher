from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MSLAUNCHER_USER_DATA_ROOT", str(Path(tempfile.gettempdir()) / "mslauncher-smoke"))

from generate_manifest import generate_manifest
from gui import DownloadWorker
from launcher_core import MinecraftEngine
from profile_manager import MANAGED_MARKER


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


def run_successful_commit(engine: MinecraftEngine, worker: DownloadWorker, client_path: Path, manifest_url: str) -> None:
    sync_plan = engine.sync_files(manifest_url, client_path, allow_insecure_local=True)
    staging_path = client_path / ".mslauncher-staging"
    staged_files = worker._download_files(sync_plan.files_to_download, staging_path)
    worker._replace_target_files(staged_files)
    worker._cleanup_staging(staging_path)
    engine.remove_unknown_mods(client_path, sync_plan.unknown_mods)


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_root:
        temp_path = Path(temp_root)
        server_path = temp_path / "server"
        client_path = temp_path / "client"

        write_text(server_path / "mods" / "good.jar", "good mod")
        write_text(client_path / "mods" / "good.jar", "old mod")
        write_text(client_path / "mods" / "cheat.jar", "bad mod")

        server, base_url = run_server(server_path)

        try:
            manifest = generate_manifest(server_path, base_url)
            write_text(server_path / "manifest.json", json.dumps(manifest, ensure_ascii=False))

            engine = MinecraftEngine(client_path)
            worker = DownloadWorker(
                engine,
                f"{base_url}/manifest.json",
                client_path,
                allow_insecure_local=True,
            )

            unmanaged_plan = engine.sync_files(
                f"{base_url}/manifest.json",
                client_path,
                allow_insecure_local=True,
            )
            if not unmanaged_plan.warning:
                raise AssertionError("Unmanaged profile did not return a warning for extra mods.")
            try:
                engine.remove_unknown_mods(client_path, unmanaged_plan.unknown_mods)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Unmanaged profile allowed extra mod deletion.")
            if not (client_path / "mods" / "cheat.jar").is_file():
                raise AssertionError("Extra mod was deleted in unmanaged profile.")

            (client_path / MANAGED_MARKER).touch()
            managed_plan = engine.sync_files(
                f"{base_url}/manifest.json",
                client_path,
                allow_insecure_local=True,
            )
            if not (client_path / "mods" / "cheat.jar").is_file():
                raise AssertionError("Extra mod was removed before successful download.")

            bad_manifest = dict(manifest)
            bad_files = [dict(item) for item in manifest["files"]]
            bad_files[0]["sha256"] = "0" * 64
            bad_manifest["files"] = bad_files
            write_text(server_path / "bad-manifest.json", json.dumps(bad_manifest, ensure_ascii=False))

            bad_plan = engine.sync_files(
                f"{base_url}/bad-manifest.json",
                client_path,
                allow_insecure_local=True,
            )
            staging_path = client_path / ".mslauncher-staging"
            try:
                worker._download_files(bad_plan.files_to_download, staging_path)
            except RuntimeError:
                worker._cleanup_staging(staging_path)
            else:
                raise AssertionError("Hash mismatch download unexpectedly succeeded.")

            if (client_path / "mods" / "good.jar").read_text(encoding="utf-8") != "old mod":
                raise AssertionError("Old mod was replaced after failed download.")
            if not (client_path / "mods" / "cheat.jar").is_file():
                raise AssertionError("Extra mod was deleted after failed download.")
            if staging_path.exists():
                raise AssertionError("Staging folder was not cleaned after failed download.")

            run_successful_commit(engine, worker, client_path, f"{base_url}/manifest.json")

            if (client_path / "mods" / "good.jar").read_text(encoding="utf-8") != "good mod":
                raise AssertionError("Valid sync did not replace outdated mod.")
            if (client_path / "mods" / "cheat.jar").exists():
                raise AssertionError("Valid managed sync did not remove extra mod.")
            if staging_path.exists():
                raise AssertionError("Staging folder was not cleaned after successful sync.")

            print("safe sync smoke test: OK")
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    main()
