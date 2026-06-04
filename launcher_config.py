from __future__ import annotations

import json
from pathlib import Path

from app_paths import (
    backup_broken_config,
    copy_default_config,
    ensure_user_config,
    get_default_profiles_directory,
)
from profile_manager import LauncherProfile, PROFILE_SERVER


CONFIG_FILE = ensure_user_config()
CONFIG_LOAD_WARNING = ""


CLIENT_MODE_INDEPENDENT = "independent"
CLIENT_MODE_NUKEM = "nukem"
CLIENT_MODES = (CLIENT_MODE_INDEPENDENT, CLIENT_MODE_NUKEM)
PROJECT_ICON_FILES = {
    CLIENT_MODE_INDEPENDENT: "mslaunch.png",
    CLIENT_MODE_NUKEM: "nukem.png",
    "vibecraft": "vibecraft.png",
}
SOCIAL_ICON_NAMES = {
    "discord": "discord",
    "telegram": "telegram",
    "youtube": "youtube",
    "instagram": "instagram",
    "tiktok": "tiktok",
    "vk": "vk",
    "vk_group": "vk",
    "rutube": "rutube",
    "website": "link",
    "link": "link",
}
SOCIAL_FALLBACK_LABELS = {
    "discord": "DS",
    "telegram": "TG",
    "youtube": "YT",
    "instagram": "IN",
    "tiktok": "TT",
    "vk": "VK",
    "vk_group": "VK",
    "rutube": "RT",
    "website": "WB",
    "link": "WB",
}


DEFAULT_NUKEM_SOCIAL_LINKS = {
    "youtube": "https://www.youtube.com/@Nuckem",
    "discord": "https://discord.gg/P35nvXQ",
    "vk": "https://vk.com/belchak",
    "vk_group": "https://vk.com/nuckem_garage",
    "rutube": "https://rutube.ru/channel/64641198",
}


def load_launcher_config(config_path: str | Path = CONFIG_FILE) -> dict[str, object]:
    global CONFIG_LOAD_WARNING

    default_config: dict[str, object] = {
        "manifest_url": "",
        "game_directory": "",
        "profiles_directory": "",
        "default_profile": PROFILE_SERVER,
        "default_language": "RU",
        "default_username": "",
        "recent_usernames": [],
        "client_mode": CLIENT_MODE_INDEPENDENT,
        "social_links": {
            CLIENT_MODE_NUKEM: dict(DEFAULT_NUKEM_SOCIAL_LINKS),
        },
        "support_url": "https://github.com/mio-openliven/mslauncher/issues/new",
        "support_urls": {
            "independent": "https://github.com/mio-openliven/mslauncher/issues/new"
        },
        "panel": {
            "enabled": False,
            "base_url": "",
            "project": CLIENT_MODE_NUKEM,
            "timeout_seconds": 8,
            "allow_insecure_http": False,
        },
        "admin_links": {
            CLIENT_MODE_NUKEM: {
                "repo_url": "https://github.com/mio-openliven/MSNukem",
                "manifest_url": "https://raw.githubusercontent.com/mio-openliven/MSNukem/main/manifest.json",
            }
        },
        "project_access": {
            CLIENT_MODE_NUKEM: {
                "password_enabled": False,
                "password_hash_sha256": "",
                "admin_password_hash_sha256": "",
                "build_passwords": {},
                "password_hint": "Ask the project admin for the access password.",
            }
        },
        "skin_path": "",
        "news": {
            CLIENT_MODE_NUKEM: [],
            CLIENT_MODE_INDEPENDENT: [],
        },
        "default_build": "",
        "launch": {},
        "builds": [],
    }

    path = Path(config_path)
    if not path.exists():
        return default_config

    try:
        with path.open("r", encoding="utf-8") as file:
            loaded_config = json.load(file)
    except json.JSONDecodeError:
        backup_path = backup_broken_config(path)
        copy_default_config(path)
        CONFIG_LOAD_WARNING = str(backup_path)
        return default_config
    except OSError as exc:
        CONFIG_LOAD_WARNING = str(exc)
        return default_config

    if not isinstance(loaded_config, dict):
        return default_config

    for key in (
        "manifest_url",
        "game_directory",
        "profiles_directory",
        "default_profile",
        "default_language",
        "default_username",
        "client_mode",
        "support_url",
        "skin_path",
        "default_build",
    ):
        value = loaded_config.get(key)
        if isinstance(value, str):
            default_config[key] = value

    recent_usernames = loaded_config.get("recent_usernames")
    if isinstance(recent_usernames, list):
        default_config["recent_usernames"] = [
            username.strip()
            for username in recent_usernames
            if isinstance(username, str) and username.strip()
        ][:5]

    social_links = loaded_config.get("social_links")
    if isinstance(social_links, dict):
        merged_links = {
            CLIENT_MODE_NUKEM: dict(DEFAULT_NUKEM_SOCIAL_LINKS),
        }
        for project_key, project_links in social_links.items():
            if not isinstance(project_key, str) or not isinstance(project_links, dict):
                continue
            project_merged = dict(merged_links.get(project_key, {}))
            for link_key, url in project_links.items():
                if isinstance(link_key, str) and isinstance(url, str) and url.strip():
                    project_merged[link_key] = url.strip()
            merged_links[project_key] = project_merged
        default_config["social_links"] = merged_links

    support_urls = loaded_config.get("support_urls")
    if isinstance(support_urls, dict):
        default_config["support_urls"] = support_urls

    panel_config = loaded_config.get("panel")
    if isinstance(panel_config, dict):
        merged_panel = dict(default_config["panel"])
        merged_panel.update(panel_config)
        default_config["panel"] = merged_panel

    for key in ("admin_links", "project_access", "news"):
        value = loaded_config.get(key)
        if isinstance(value, dict):
            default_config[key] = value

    builds = loaded_config.get("builds")
    if isinstance(builds, list):
        default_config["builds"] = [build for build in builds if isinstance(build, dict)]

    launch_options = loaded_config.get("launch")
    if isinstance(launch_options, dict):
        default_config["launch"] = launch_options

    return default_config


def save_launcher_config(config: dict[str, object], config_path: str | Path = CONFIG_FILE) -> None:
    path = Path(config_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def get_config_text(config: dict[str, object], key: str, default: str = "") -> str:
    value = config.get(key, default)
    return value if isinstance(value, str) else default


def get_config_string_list(config: dict[str, object], key: str) -> list[str]:
    values = config.get(key, [])
    if not isinstance(values, list):
        return []

    result: list[str] = []
    for value in values:
        if isinstance(value, str):
            cleaned_value = value.strip()
            if cleaned_value and cleaned_value not in result:
                result.append(cleaned_value)
    return result


def get_client_mode(config: dict[str, object]) -> str:
    mode = get_config_text(config, "client_mode", CLIENT_MODE_INDEPENDENT).strip().lower()
    return mode if mode in CLIENT_MODES else CLIENT_MODE_INDEPENDENT


def get_social_links(config: dict[str, object], client_mode: str = CLIENT_MODE_NUKEM) -> dict[str, str]:
    if client_mode != CLIENT_MODE_NUKEM:
        return {}

    raw_links = config.get("social_links", {})
    if not isinstance(raw_links, dict):
        return {}

    project_links = raw_links.get(CLIENT_MODE_NUKEM)
    if isinstance(project_links, dict):
        raw_links = project_links

    links: dict[str, str] = {}
    for raw_name, raw_value in raw_links.items():
        name = str(raw_name).strip().lower()
        if name not in SOCIAL_ICON_NAMES:
            continue

        url = ""
        enabled = True
        if isinstance(raw_value, str):
            url = raw_value.strip()
        elif isinstance(raw_value, dict):
            enabled = bool(raw_value.get("enabled", True))
            value = raw_value.get("url", "")
            url = value.strip() if isinstance(value, str) else ""

        if enabled and url:
            links[name] = url
    return links


def get_support_url(config: dict[str, object], client_mode: str) -> str:
    support_urls = config.get("support_urls")
    if isinstance(support_urls, dict):
        project_url = support_urls.get(client_mode)
        if isinstance(project_url, str) and project_url.strip():
            return project_url.strip()
    return get_config_text(config, "support_url").strip()


def get_admin_link(config: dict[str, object], client_mode: str, key: str) -> str:
    admin_links = config.get("admin_links")
    if not isinstance(admin_links, dict):
        return ""
    project_links = admin_links.get(client_mode)
    if not isinstance(project_links, dict):
        return ""
    value = project_links.get(key)
    return value.strip() if isinstance(value, str) else ""


def get_config_builds(config: dict[str, object]) -> list[dict[str, object]]:
    builds = config.get("builds", [])
    if isinstance(builds, list) and builds:
        return [build for build in builds if isinstance(build, dict)]

    fallback_manifest_url = get_config_text(config, "manifest_url")
    if fallback_manifest_url:
        return [
            {
                "id": "main",
                "name": "Main Server",
                "minecraft_version": "",
                "manifest_url": fallback_manifest_url,
            }
        ]

    return []


def get_config_launch_options(config: dict[str, object]) -> dict[str, object]:
    launch_options = config.get("launch", {})
    return launch_options if isinstance(launch_options, dict) else {}


def get_profile_base_directory(config: dict[str, object]) -> str:
    profiles_directory = get_config_text(config, "profiles_directory").strip()
    if profiles_directory:
        return profiles_directory
    legacy_game_directory = get_config_text(config, "game_directory").strip()
    if legacy_game_directory:
        return legacy_game_directory
    return str(get_default_profiles_directory())


def should_sync_profile(client_mode: str, profile: LauncherProfile) -> bool:
    return client_mode == CLIENT_MODE_NUKEM and profile.server_sync_enabled


def requires_server_manifest(profile: LauncherProfile, manifest_url: str, client_mode: str) -> bool:
    return should_sync_profile(client_mode, profile) and not manifest_url.strip()


def get_config_load_warning() -> str:
    return CONFIG_LOAD_WARNING
