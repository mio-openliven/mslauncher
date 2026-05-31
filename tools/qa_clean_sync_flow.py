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

os.environ.setdefault("MSLAUNCHER_USER_DATA_ROOT", str(Path(tempfile.gettempdir()) / "mslauncher-qa"))

from generate_manifest import calculate_sha256, generate_build_config, generate_manifest, write_json
from gui import DownloadWorker
from launcher_core import MinecraftEngine, SyncPlan
from profile_manager import MANAGED_MARKER
from remote_config import resolve_build_config


class QuietHTTPRequestHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def run_server(directory: Path) -> tuple[ThreadingHTTPServer, str]:
    handler = partial(QuietHTTPRequestHandler, directory=str(directory))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    return server, f"http://{host}:{port}"


def prepare_server_pack(server_pack: Path) -> None:
    write_text(server_pack / "mods" / "good.jar", "good mod\n")
    write_text(server_pack / "config" / "settings.toml", "enabled=true\n")
    write_bytes(server_pack / "resourcepacks" / "pack.zip", b"pack data\n")


def publish_build(server_pack: Path, base_url: str) -> dict[str, object]:
    manifest = generate_manifest(server_pack, base_url)
    build = generate_build_config(
        build_name="QA Server",
        minecraft_version="1.20.1",
        loader="fabric",
        loader_version="latest",
        base_url=base_url,
        output_manifest="manifest.json",
        server="127.0.0.1",
        port="25565",
    )
    write_json(server_pack / "manifest.json", manifest)
    write_json(server_pack / "build.json", build)
    return manifest


def commit_sync(engine: MinecraftEngine, worker: DownloadWorker, client_path: Path, sync_plan: SyncPlan) -> None:
    staging_path = client_path / ".mslauncher-staging"
    try:
        staged_files = worker._download_files(sync_plan.files_to_download, staging_path)
        worker._replace_target_files(staged_files)
        engine.remove_unknown_mods(client_path, sync_plan.unknown_mods)
    finally:
        worker._cleanup_staging(staging_path)


def assert_manifest_files_match(manifest: dict[str, object], client_path: Path) -> None:
    for item in manifest["files"]:
        file_info = dict(item)
        relative_path = str(file_info["path"])
        target_path = client_path / relative_path
        if not target_path.is_file():
            raise AssertionError(f"Missing synced file: {relative_path}")
        if target_path.stat().st_size != int(file_info["size"]):
            raise AssertionError(f"Size mismatch after sync: {relative_path}")
        if calculate_sha256(target_path) != str(file_info["sha256"]):
            raise AssertionError(f"Hash mismatch after sync: {relative_path}")


def assert_raises_contains(action, expected_text: str) -> str:
    try:
        action()
    except Exception as exc:
        message = str(exc)
        if expected_text.lower() not in message.lower():
            raise AssertionError(f"Expected error containing {expected_text!r}, got {message!r}") from exc
        return message
    raise AssertionError(f"Expected error containing {expected_text!r}.")


def run_success_flow(temp_path: Path) -> tuple[int, int]:
    server_pack = temp_path / "server_pack"
    client_path = temp_path / "client-managed"
    prepare_server_pack(server_pack)
    write_text(client_path / "mods" / "good.jar", "old mod\n")
    write_text(client_path / "mods" / "extra.jar", "extra mod\n")
    (client_path / MANAGED_MARKER).touch()

    server, base_url = run_server(server_pack)
    try:
        manifest = publish_build(server_pack, base_url)
        build = resolve_build_config(
            {"id": "main", "source_key": f"{base_url}/build.json"},
            allow_insecure_local=True,
            require_manifest=True,
        )
        engine = MinecraftEngine(client_path)
        worker = DownloadWorker(engine, str(build["manifest_url"]), client_path, allow_insecure_local=True)
        sync_plan = engine.sync_files(
            str(build["manifest_url"]),
            client_path,
            allow_insecure_local=True,
            require_files=True,
        )

        if not (client_path / "mods" / "extra.jar").is_file():
            raise AssertionError("Extra mod was removed before successful sync.")

        downloaded = len(sync_plan.files_to_download)
        commit_sync(engine, worker, client_path, sync_plan)
        assert_manifest_files_match(manifest, client_path)

        if (client_path / "mods" / "extra.jar").exists():
            raise AssertionError("Extra mod was not deleted after successful managed sync.")
        return downloaded, 1
    finally:
        server.shutdown()
        server.server_close()


def run_unmanaged_delete_guard(temp_path: Path) -> None:
    server_pack = temp_path / "server_unmanaged"
    client_path = temp_path / "client-unmanaged"
    prepare_server_pack(server_pack)
    write_text(client_path / "mods" / "extra.jar", "extra mod\n")

    server, base_url = run_server(server_pack)
    try:
        publish_build(server_pack, base_url)
        engine = MinecraftEngine(client_path)
        sync_plan = engine.sync_files(f"{base_url}/manifest.json", client_path, allow_insecure_local=True)
        if not sync_plan.warning:
            raise AssertionError("Unmanaged profile did not return a deletion warning.")
        assert_raises_contains(lambda: engine.remove_unknown_mods(client_path, sync_plan.unknown_mods), "managed")
        if not (client_path / "mods" / "extra.jar").is_file():
            raise AssertionError("Unmanaged profile deleted an extra mod.")
    finally:
        server.shutdown()
        server.server_close()


def run_bad_hash_guard(temp_path: Path) -> None:
    server_pack = temp_path / "server_bad_hash"
    client_path = temp_path / "client-bad-hash"
    prepare_server_pack(server_pack)
    write_text(client_path / "mods" / "good.jar", "old mod\n")
    write_text(client_path / "mods" / "extra.jar", "extra mod\n")
    (client_path / MANAGED_MARKER).touch()

    server, base_url = run_server(server_pack)
    try:
        manifest = publish_build(server_pack, base_url)
        bad_manifest = dict(manifest)
        bad_files = [dict(item) for item in manifest["files"]]
        bad_files[0]["sha256"] = "0" * 64
        bad_manifest["files"] = bad_files
        write_json(server_pack / "bad-hash.json", bad_manifest)

        engine = MinecraftEngine(client_path)
        worker = DownloadWorker(engine, f"{base_url}/bad-hash.json", client_path, allow_insecure_local=True)
        sync_plan = engine.sync_files(
            f"{base_url}/bad-hash.json",
            client_path,
            allow_insecure_local=True,
            require_files=True,
        )
        assert_raises_contains(lambda: commit_sync(engine, worker, client_path, sync_plan), "checksum")

        if (client_path / "mods" / "good.jar").read_text(encoding="utf-8") != "old mod\n":
            raise AssertionError("Bad hash replaced an existing file.")
        if not (client_path / "mods" / "extra.jar").is_file():
            raise AssertionError("Bad hash deleted an extra mod.")
        if (client_path / ".mslauncher-staging").exists():
            raise AssertionError("Bad hash left staging files behind.")
    finally:
        server.shutdown()
        server.server_close()


def run_missing_file_guard(temp_path: Path) -> None:
    server_pack = temp_path / "server_missing_file"
    client_path = temp_path / "client-missing-file"
    prepare_server_pack(server_pack)
    write_text(client_path / "mods" / "good.jar", "old mod\n")
    write_text(client_path / "mods" / "extra.jar", "extra mod\n")
    (client_path / MANAGED_MARKER).touch()

    server, base_url = run_server(server_pack)
    try:
        manifest = publish_build(server_pack, base_url)
        broken_manifest = dict(manifest)
        broken_files = [dict(item) for item in manifest["files"]]
        broken_files[0]["url"] = f"{base_url}/mods/missing.jar"
        broken_manifest["files"] = broken_files
        write_json(server_pack / "missing-file.json", broken_manifest)

        engine = MinecraftEngine(client_path)
        worker = DownloadWorker(engine, f"{base_url}/missing-file.json", client_path, allow_insecure_local=True)
        sync_plan = engine.sync_files(
            f"{base_url}/missing-file.json",
            client_path,
            allow_insecure_local=True,
            require_files=True,
        )
        assert_raises_contains(lambda: commit_sync(engine, worker, client_path, sync_plan), "failed to download")

        if (client_path / "mods" / "good.jar").read_text(encoding="utf-8") != "old mod\n":
            raise AssertionError("Missing download replaced an existing file.")
        if not (client_path / "mods" / "extra.jar").is_file():
            raise AssertionError("Missing download deleted an extra mod.")
    finally:
        server.shutdown()
        server.server_close()


def run_manifest_guards(temp_path: Path) -> None:
    server_pack = temp_path / "server_manifest_guards"
    client_path = temp_path / "client-manifest-guards"
    prepare_server_pack(server_pack)
    client_path.mkdir(parents=True, exist_ok=True)
    (client_path / MANAGED_MARKER).touch()

    server, base_url = run_server(server_pack)
    try:
        publish_build(server_pack, base_url)
        engine = MinecraftEngine(client_path)
        assert_raises_contains(
            lambda: engine.sync_files(
                f"{base_url}/missing-manifest.json",
                client_path,
                allow_insecure_local=True,
                require_files=True,
            ),
            "manifest",
        )

        write_json(server_pack / "empty-manifest.json", {"version": 1, "files": []})
        assert_raises_contains(
            lambda: engine.sync_files(
                f"{base_url}/empty-manifest.json",
                client_path,
                allow_insecure_local=True,
                require_files=True,
            ),
            "contains no files",
        )
    finally:
        server.shutdown()
        server.server_close()


def run_qa() -> dict[str, int | str]:
    with tempfile.TemporaryDirectory() as temp_root:
        temp_path = Path(temp_root)
        downloaded, deleted_extra_mods = run_success_flow(temp_path)
        run_unmanaged_delete_guard(temp_path)
        run_bad_hash_guard(temp_path)
        run_missing_file_guard(temp_path)
        run_manifest_guards(temp_path)
        return {
            "downloaded": downloaded,
            "deleted_extra_mods": deleted_extra_mods,
            "failed_download_preserved_files": "OK",
        }


def main() -> int:
    summary = run_qa()
    print("QA clean sync flow: OK")
    print(f"downloaded: {summary['downloaded']}")
    print(f"deleted_extra_mods: {summary['deleted_extra_mods']}")
    print(f"failed_download_preserved_files: {summary['failed_download_preserved_files']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
