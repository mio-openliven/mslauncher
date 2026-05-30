from __future__ import annotations

from urllib.parse import urlparse

import requests


REMOTE_BUILD_KEYS = (
    "id",
    "name",
    "minecraft_version",
    "loader",
    "loader_version",
    "manifest_url",
    "server",
    "port",
)


class RemoteBuildConfigError(RuntimeError):
    pass


def resolve_build_config(build: dict[str, object]) -> dict[str, object]:
    source_key = str(build.get("source_key", "")).strip()
    if not source_key:
        return validate_build_config(dict(build))

    remote_url = normalize_source_key(source_key)
    try:
        response = requests.get(remote_url, timeout=30)
        response.raise_for_status()
        remote_config = response.json()
    except requests.Timeout as exc:
        raise RemoteBuildConfigError("Remote build config request timed out.") from exc
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        raise RemoteBuildConfigError(f"Remote build config returned HTTP {status_code}.") from exc
    except requests.RequestException as exc:
        raise RemoteBuildConfigError(f"Could not load remote build config: {exc}") from exc
    except ValueError as exc:
        raise RemoteBuildConfigError("Remote build config is not valid JSON.") from exc

    if not isinstance(remote_config, dict):
        raise RemoteBuildConfigError("Remote build config must be a JSON object.")

    resolved_build = dict(build)
    for key in REMOTE_BUILD_KEYS:
        value = remote_config.get(key)
        if value is None:
            continue
        if not isinstance(value, str):
            raise RemoteBuildConfigError(f"Remote field '{key}' must be a string.")
        resolved_build[key] = value.strip()

    return validate_build_config(resolved_build)


def validate_build_config(build: dict[str, object]) -> dict[str, object]:
    normalized_build = dict(build)
    loader = str(normalized_build.get("loader", "vanilla")).strip().lower() or "vanilla"
    if loader not in ("vanilla", "fabric"):
        raise RemoteBuildConfigError("Build loader must be vanilla or fabric.")
    normalized_build["loader"] = loader

    loader_version = str(normalized_build.get("loader_version", "latest")).strip()
    normalized_build["loader_version"] = loader_version or "latest"

    manifest_url = str(normalized_build.get("manifest_url", "")).strip()
    if manifest_url and not is_http_url(manifest_url):
        raise RemoteBuildConfigError("Build manifest_url must be an http or https URL.")
    normalized_build["manifest_url"] = manifest_url

    source_key = str(normalized_build.get("source_key", "")).strip()
    if source_key:
        normalized_build["source_key"] = source_key

    port = str(normalized_build.get("port", "")).strip()
    if port and (not port.isdigit() or not 1 <= int(port) <= 65535):
        raise RemoteBuildConfigError("Build port must be a number from 1 to 65535.")
    normalized_build["port"] = port

    for key in ("id", "name", "minecraft_version", "server"):
        value = normalized_build.get(key)
        if isinstance(value, str):
            normalized_build[key] = value.strip()

    return normalized_build


def normalize_source_key(source_key: str) -> str:
    stripped_source = source_key.strip()
    if is_http_url(stripped_source):
        return stripped_source
    return f"http://{stripped_source.strip('/')}/mslauncher/build.json"


def is_http_url(value: str) -> bool:
    parsed_url = urlparse(value)
    return parsed_url.scheme in ("http", "https") and bool(parsed_url.netloc)
