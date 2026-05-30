from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


PROFILE_SERVER = "server"
PROFILE_PERSONAL = "personal"
PROFILE_OTHER = "other"
PROFILE_IDS = (PROFILE_SERVER, PROFILE_PERSONAL, PROFILE_OTHER)


@dataclass(frozen=True)
class LauncherProfile:
    profile_id: str
    directory: Path
    server_sync_enabled: bool


class LauncherProfileManager:
    """Keeps Minecraft installations isolated by launcher mode."""

    def __init__(self, base_directory: str | Path | None = None) -> None:
        self.base_directory = Path(base_directory or self._default_base_directory()).resolve()

    def get_profile(self, profile_id: str | None) -> LauncherProfile:
        normalized_id = self.normalize_profile_id(profile_id)
        profile = LauncherProfile(
            profile_id=normalized_id,
            directory=self.base_directory / normalized_id,
            server_sync_enabled=normalized_id == PROFILE_SERVER,
        )
        self.ensure_profile(profile)
        return profile

    def ensure_profile(self, profile: LauncherProfile) -> None:
        profile.directory.mkdir(parents=True, exist_ok=True)
        for folder_name in ("mods", "config", "resourcepacks", "saves"):
            (profile.directory / folder_name).mkdir(parents=True, exist_ok=True)

    def normalize_profile_id(self, profile_id: str | None) -> str:
        normalized_id = str(profile_id or "").strip().lower()
        return normalized_id if normalized_id in PROFILE_IDS else PROFILE_SERVER

    def _default_base_directory(self) -> Path:
        return Path(__file__).resolve().parent / "data" / "instances"
