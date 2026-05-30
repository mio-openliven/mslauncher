from __future__ import annotations

from urllib.parse import urljoin

import requests

from url_policy import URLPolicyError, ensure_same_https_origin, normalize_https_url, normalize_source_key_url


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


def resolve_build_config(build: dict[str, object], *, allow_insecure_local: bool = False) -> dict[str, object]:
    source_key = str(build.get("source_key", "")).strip()
    if not source_key:
        return validate_build_config(dict(build), allow_insecure_local=allow_insecure_local)

    try:
        remote_url = normalize_source_key(source_key, allow_insecure_local=allow_insecure_local)
    except URLPolicyError as exc:
        raise RemoteBuildConfigError(str(exc)) from exc

    try:
        response = requests.get(remote_url, timeout=30, allow_redirects=False)
        if response.is_redirect:
            redirect_url = urljoin(remote_url, response.headers.get("Location", ""))
            try:
                remote_url = ensure_same_https_origin(remote_url, redirect_url, field_name="source_key")
            except URLPolicyError as exc:
                raise RemoteBuildConfigError(str(exc)) from exc
            response = requests.get(remote_url, timeout=30, allow_redirects=False)
            if response.is_redirect:
                raise RemoteBuildConfigError("Remote build config redirected more than once.")
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

    return validate_build_config(resolved_build, allow_insecure_local=allow_insecure_local)


def validate_build_config(build: dict[str, object], *, allow_insecure_local: bool = False) -> dict[str, object]:
    normalized_build = dict(build)
    loader = str(normalized_build.get("loader", "vanilla")).strip().lower() or "vanilla"
    if loader not in ("vanilla", "fabric"):
        raise RemoteBuildConfigError("Build loader must be vanilla or fabric.")
    normalized_build["loader"] = loader

    loader_version = str(normalized_build.get("loader_version", "latest")).strip()
    normalized_build["loader_version"] = loader_version or "latest"

    manifest_url = str(normalized_build.get("manifest_url", "")).strip()
    if manifest_url:
        try:
            manifest_url = normalize_https_url(
                manifest_url,
                "Build manifest_url",
                allow_insecure_local=allow_insecure_local,
            )
        except URLPolicyError as exc:
            raise RemoteBuildConfigError(str(exc)) from exc
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


def normalize_source_key(source_key: str, *, allow_insecure_local: bool = False) -> str:
    try:
        return normalize_source_key_url(source_key, allow_insecure_local=allow_insecure_local)
    except URLPolicyError as exc:
        raise RemoteBuildConfigError(str(exc)) from exc
