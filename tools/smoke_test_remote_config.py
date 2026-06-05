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

from remote_config import RemoteBuildConfigError, normalize_source_key, resolve_build_config, validate_build_config


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


def expect_error(build: dict[str, object]) -> None:
    try:
        resolve_build_config(build)
    except RemoteBuildConfigError:
        return
    raise AssertionError(f"Expected RemoteBuildConfigError for {build}")


def main() -> None:
    assert normalize_source_key("example.com") == "https://example.com/mslauncher/build.json"
    assert normalize_source_key("https://example.com/build.json") == "https://example.com/build.json"

    expect_error({"loader": "forge"})
    expect_error({"loader": "vanilla", "manifest_url": "ftp://example.com/manifest.json"})
    expect_error({"loader": "vanilla", "manifest_url": "http://example.com/manifest.json"})
    expect_error({"loader": "vanilla", "port": "99999"})
    validate_build_config({"loader": "vanilla", "manifest_url": ""})
    assert validate_build_config({"loader": "quilt", "manifest_url": ""})["loader"] == "quilt"
    assert validate_build_config({"loader": "neoforge", "manifest_url": ""})["loader"] == "neoforge"
    try:
        validate_build_config({"loader": "vanilla", "manifest_url": ""}, require_manifest=True)
    except RemoteBuildConfigError:
        pass
    else:
        raise AssertionError("Expected RemoteBuildConfigError for required manifest.")

    with tempfile.TemporaryDirectory() as temp_root:
        server_path = Path(temp_root)
        write_text(
            server_path / "valid.json",
            json.dumps(
                {
                    "id": "remote-id-must-not-win",
                    "name": "Remote",
                    "minecraft_version": "1.20.1",
                    "loader": "fabric",
                    "manifest_url": "https://example.com/manifest.json",
                    "server": "play.example.com",
                    "port": "25565",
                },
                ensure_ascii=False,
            ),
        )
        write_text(server_path / "empty-manifest.json", json.dumps({"manifest_url": ""}))
        write_text(server_path / "bad-json.json", "{")
        write_text(server_path / "array.json", "[]")
        write_text(server_path / "bad-loader.json", json.dumps({"loader": "forge"}))
        write_text(server_path / "bad-type.json", json.dumps({"port": 25565}))

        server, base_url = run_server(server_path)
        try:
            build = resolve_build_config(
                {"id": "main", "source_key": f"{base_url}/valid.json"},
                allow_insecure_local=True,
            )
            assert build["id"] == "main"
            assert build["name"] == "Remote"
            assert build["loader"] == "fabric"
            assert build["port"] == "25565"
            assert build["manifest_url"] == "https://example.com/manifest.json"

            required_build = resolve_build_config(
                {"id": "main", "source_key": f"{base_url}/valid.json"},
                allow_insecure_local=True,
                require_manifest=True,
            )
            assert required_build["manifest_url"] == "https://example.com/manifest.json"

            try:
                resolve_build_config(
                    {"id": "main", "source_key": f"{base_url}/empty-manifest.json"},
                    allow_insecure_local=True,
                    require_manifest=True,
                )
            except RemoteBuildConfigError:
                pass
            else:
                raise AssertionError("Expected RemoteBuildConfigError for remote empty manifest.")

            for path in ("missing.json", "bad-json.json", "array.json", "bad-loader.json", "bad-type.json"):
                try:
                    resolve_build_config({"id": "main", "source_key": f"{base_url}/{path}"}, allow_insecure_local=True)
                except RemoteBuildConfigError:
                    pass
                else:
                    raise AssertionError(f"Expected RemoteBuildConfigError for {path}")
        finally:
            server.shutdown()
            server.server_close()

    print("remote config smoke test: OK")


if __name__ == "__main__":
    main()
