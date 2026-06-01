from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import requests

from remote_config import RemoteBuildConfigError, validate_build_config


class PanelClientError(RuntimeError):
    pass


def get_panel_config(config: dict[str, object]) -> dict[str, object]:
    panel_config = config.get("panel")
    return panel_config if isinstance(panel_config, dict) else {}


def is_panel_enabled(config: dict[str, object]) -> bool:
    panel_config = get_panel_config(config)
    return bool(panel_config.get("enabled", False)) and bool(str(panel_config.get("base_url", "")).strip())


def get_panel_base_url(config: dict[str, object]) -> str:
    return str(get_panel_config(config).get("base_url", "")).strip().rstrip("/")


def get_panel_timeout(config: dict[str, object]) -> float:
    raw_timeout = get_panel_config(config).get("timeout_seconds", 8)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        return 8.0
    return min(max(timeout, 1.0), 30.0)


def get_panel_project(config: dict[str, object], fallback_project: str) -> str:
    project = str(get_panel_config(config).get("project", "")).strip().lower()
    return project or fallback_project


def allow_insecure_panel_url(url: str) -> bool:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "http" and host in {"127.0.0.1", "localhost", "::1"}


def resolve_panel_active_build(
    config: dict[str, object],
    project: str,
    *,
    require_manifest: bool = False,
) -> dict[str, object]:
    if not is_panel_enabled(config):
        return {}

    base_url = get_panel_base_url(config)
    panel_project = get_panel_project(config, project)
    url = f"{base_url}/api/projects/{panel_project}/active-build"
    try:
        response = requests.get(url, timeout=get_panel_timeout(config))
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise PanelClientError(f"Could not load panel active build: {exc}") from exc
    except ValueError as exc:
        raise PanelClientError("Panel active build response is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise PanelClientError("Panel active build must be a JSON object.")

    normalized = dict(data)
    if "id" not in normalized and normalized.get("build_id"):
        normalized["id"] = normalized["build_id"]
    normalized.setdefault("source", "panel")
    try:
        return validate_build_config(
            normalized,
            allow_insecure_local=allow_insecure_panel_url(base_url),
            require_manifest=require_manifest,
        )
    except RemoteBuildConfigError as exc:
        raise PanelClientError(str(exc)) from exc


def get_panel_launcher_update(config: dict[str, object]) -> dict[str, str]:
    if not is_panel_enabled(config):
        return {}

    base_url = get_panel_base_url(config)
    url = f"{base_url}/api/launcher/update"
    try:
        response = requests.get(url, timeout=get_panel_timeout(config))
        if response.status_code == 404:
            return {}
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise PanelClientError(f"Could not load panel launcher update: {exc}") from exc
    except ValueError as exc:
        raise PanelClientError("Panel update response is not valid JSON.") from exc

    if not isinstance(data, dict) or not bool(data.get("enabled", False)):
        return {}

    return {
        "launcher_version": str(data.get("version", "")).strip(),
        "launcher_download_url": str(data.get("download_url", "")).strip(),
        "launcher_sha256": str(data.get("sha256", "")).strip().lower(),
        "launcher_notes": str(data.get("notes", "")).strip(),
    }


def request_panel_build_access(
    config: dict[str, object],
    project: str,
    build: dict[str, object],
    password: str,
) -> dict[str, object]:
    if not is_panel_enabled(config):
        return {}

    build_id = str(build.get("build_id") or build.get("id") or "").strip()
    if not build_id:
        raise PanelClientError("Panel build id is missing.")

    base_url = get_panel_base_url(config)
    panel_project = get_panel_project(config, project)
    url = f"{base_url}/api/projects/{panel_project}/builds/{build_id}/access"
    try:
        response = requests.post(
            url,
            json={"password": password},
            timeout=get_panel_timeout(config),
        )
        if response.status_code == 403:
            raise PanelClientError("Wrong build password.")
        response.raise_for_status()
        data = response.json()
    except PanelClientError:
        raise
    except requests.RequestException as exc:
        raise PanelClientError(f"Could not unlock panel build: {exc}") from exc
    except ValueError as exc:
        raise PanelClientError("Panel build access response is not valid JSON.") from exc

    if not isinstance(data, dict):
        raise PanelClientError("Panel build access response must be a JSON object.")

    unlocked = dict(build)
    manifest_url = str(data.get("manifest_url", "")).strip()
    if manifest_url:
        unlocked["manifest_url"] = manifest_url

    try:
        return validate_build_config(
            unlocked,
            allow_insecure_local=allow_insecure_panel_url(base_url),
            require_manifest=True,
        )
    except RemoteBuildConfigError as exc:
        raise PanelClientError(str(exc)) from exc


def post_panel_report(config: dict[str, object], payload: dict[str, Any]) -> bool:
    if not is_panel_enabled(config):
        return False

    base_url = get_panel_base_url(config)
    try:
        response = requests.post(
            f"{base_url}/api/reports",
            json=payload,
            timeout=get_panel_timeout(config),
        )
        response.raise_for_status()
        return True
    except requests.RequestException:
        return False
