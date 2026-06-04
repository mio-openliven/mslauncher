from __future__ import annotations

import hashlib
import shutil
import threading
import traceback
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

from launcher_core import MinecraftEngine
from manifest_validator import normalize_download_url, normalize_manifest_path
from panel_client import PanelClientError, get_panel_launcher_update, resolve_panel_active_build
from remote_config import resolve_build_config
from url_policy import URLPolicyError


CHUNK_SIZE = 1024 * 1024
DOWNLOAD_RETRIES = 3
REQUEST_TIMEOUT = 60
CLIENT_MODE_INDEPENDENT = "independent"
CLIENT_MODE_NUKEM = "nukem"


class VersionsWorker(QThread):
    versions_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine: MinecraftEngine) -> None:
        super().__init__()
        self.engine = engine

    def run(self) -> None:
        try:
            self.versions_loaded.emit(self.engine.get_all_versions())
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class BuildConfigWorker(QThread):
    build_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        build: dict[str, object],
        *,
        config: dict[str, object] | None = None,
        client_mode: str = CLIENT_MODE_INDEPENDENT,
        require_manifest: bool = False,
    ) -> None:
        super().__init__()
        self.build = build
        self.config = config or {}
        self.client_mode = client_mode
        self.require_manifest = require_manifest

    def run(self) -> None:
        try:
            if self.client_mode == CLIENT_MODE_NUKEM:
                try:
                    panel_build = resolve_panel_active_build(
                        self.config,
                        CLIENT_MODE_NUKEM,
                        require_manifest=self.require_manifest,
                    )
                except PanelClientError:
                    panel_build = {}
                if panel_build:
                    self.build_loaded.emit(panel_build)
                    return
            self.build_loaded.emit(resolve_build_config(self.build, require_manifest=self.require_manifest))
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class LauncherUpdateWorker(QThread):
    update_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        build: dict[str, object],
        *,
        config: dict[str, object],
        client_mode: str,
    ) -> None:
        super().__init__()
        self.build = dict(build)
        self.config = config
        self.client_mode = client_mode

    def run(self) -> None:
        try:
            resolved_build = dict(self.build)
            try:
                panel_update = get_panel_launcher_update(self.config)
            except PanelClientError:
                panel_update = {}
            if panel_update:
                self.update_loaded.emit({**resolved_build, **panel_update})
                return
            if resolved_build:
                resolved_build = resolve_build_config(resolved_build, require_manifest=False)
            self.update_loaded.emit(resolved_build)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class DownloadWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    status_detail_changed = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str, str)
    finished_successfully = pyqtSignal()

    def __init__(
        self,
        engine: MinecraftEngine,
        manifest_url: str,
        game_directory: str | Path,
        *,
        allow_insecure_local: bool = False,
        allow_insecure_http: bool = False,
        require_manifest_files: bool = True,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.manifest_url = manifest_url
        self.game_directory = Path(game_directory)
        self.allow_insecure_local = allow_insecure_local
        self.allow_insecure_http = allow_insecure_http
        self.require_manifest_files = require_manifest_files

    def run(self) -> None:
        staging_path = self.game_directory / ".mslauncher-staging"
        try:
            self.status_changed.emit("status_syncing")
            sync_plan = self.engine.sync_files(
                self.manifest_url,
                self.game_directory,
                allow_insecure_local=self.allow_insecure_local,
                allow_insecure_http=self.allow_insecure_http,
                require_files=self.require_manifest_files,
            )

            if sync_plan.warning:
                self.error_occurred.emit("sync_failed", sync_plan.warning)
                return

            try:
                if sync_plan.files_to_download:
                    self.status_changed.emit("status_downloading")
                    staged_files = self._download_files(sync_plan.files_to_download, staging_path)
                    self._replace_target_files(staged_files)

                self.engine.remove_unknown_mods(self.game_directory, sync_plan.unknown_mods)
            except Exception as exc:
                self.error_occurred.emit("download_failed", str(exc))
                return
            finally:
                self._cleanup_staging(staging_path)

            self.progress_changed.emit(100)
            if sync_plan.files_to_download:
                self.status_changed.emit("status_download_complete")
            else:
                self.status_changed.emit("status_no_downloads")
            self.finished_successfully.emit()
        except requests.RequestException as exc:
            self.error_occurred.emit("download_failed", str(exc))
        except Exception as exc:
            self.error_occurred.emit("sync_failed", str(exc))

    def _download_files(
        self,
        files: list[dict[str, str | int]],
        staging_path: Path,
    ) -> list[tuple[Path, Path]]:
        self._cleanup_staging(staging_path)
        total_bytes = sum(int(file.get("size", 0)) for file in files)
        completed_bytes = 0
        staged_files: list[tuple[Path, Path]] = []

        for file_info in files:
            relative_path = self._safe_relative_path(file_info)
            url = self._safe_download_url(file_info, relative_path)
            expected_hash = str(file_info.get("sha256", "")).lower().strip()
            expected_size = int(file_info.get("size", 0))

            self.status_detail_changed.emit("status_downloading_file", relative_path)
            target_path = self.game_directory / relative_path
            staged_path = staging_path / relative_path
            self._download_file_with_retry(
                url=url,
                staged_path=staged_path,
                expected_hash=expected_hash,
                expected_size=expected_size,
                relative_path=relative_path,
                completed_bytes=completed_bytes,
                total_bytes=total_bytes,
            )
            staged_files.append((staged_path, target_path))
            completed_bytes += expected_size
            self.progress_changed.emit(self._calculate_progress(completed_bytes, total_bytes))

        return staged_files

    def _download_file_with_retry(
        self,
        url: str,
        staged_path: Path,
        expected_hash: str,
        expected_size: int,
        relative_path: str,
        completed_bytes: int,
        total_bytes: int,
    ) -> None:
        last_error: Exception | None = None

        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            part_path = staged_path.with_name(f"{staged_path.name}.part")

            try:
                self._download_to_part_file(
                    url=url,
                    part_path=part_path,
                    completed_bytes=completed_bytes,
                    total_bytes=total_bytes,
                )
                self._verify_downloaded_file(part_path, expected_hash, expected_size, relative_path)
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                part_path.replace(staged_path)
                return
            except Exception as exc:
                last_error = exc
                part_path.unlink(missing_ok=True)
                staged_path.unlink(missing_ok=True)
                if attempt < DOWNLOAD_RETRIES:
                    self.msleep(500 * attempt)

        raise RuntimeError(f"Failed to download {relative_path}: {last_error}")

    def _download_to_part_file(
        self,
        url: str,
        part_path: Path,
        completed_bytes: int,
        total_bytes: int,
    ) -> None:
        part_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.unlink(missing_ok=True)
        current_file_bytes = 0

        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            with part_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue

                    file.write(chunk)
                    current_file_bytes += len(chunk)
                    self.progress_changed.emit(
                        self._calculate_progress(completed_bytes + current_file_bytes, total_bytes)
                    )

    def _verify_downloaded_file(
        self,
        part_path: Path,
        expected_hash: str,
        expected_size: int,
        relative_path: str,
    ) -> None:
        actual_size = part_path.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(f"Size mismatch for {relative_path}: expected {expected_size}, got {actual_size}")
        if expected_hash and self._calculate_sha256(part_path) != expected_hash:
            raise RuntimeError(f"Checksum mismatch for {relative_path}")

    def _replace_target_files(self, staged_files: list[tuple[Path, Path]]) -> None:
        for staged_path, target_path in staged_files:
            if not staged_path.is_file():
                raise RuntimeError(f"Staged file is missing: {staged_path.name}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.replace(target_path)

    def _cleanup_staging(self, staging_path: Path) -> None:
        if staging_path.exists():
            shutil.rmtree(staging_path, ignore_errors=True)

    def _safe_relative_path(self, file_info: dict[str, str | int]) -> str:
        return normalize_manifest_path(file_info.get("path", ""))

    def _safe_download_url(self, file_info: dict[str, str | int], relative_path: str) -> str:
        return normalize_download_url(
            file_info.get("url", ""),
            relative_path,
            allow_insecure_local=self.allow_insecure_local,
            allow_insecure_http=self.allow_insecure_http,
        )

    def _calculate_sha256(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _calculate_progress(self, downloaded_bytes: int, total_bytes: int) -> int:
        if total_bytes <= 0:
            return 0
        return min(100, int(downloaded_bytes * 100 / total_bytes))


class LaunchWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    crash_detected = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)
    finished_successfully = pyqtSignal()

    def __init__(
        self,
        engine: MinecraftEngine,
        version: str,
        username: str,
        launch_options: dict[str, object] | None = None,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.version = version
        self.username = username
        self.launch_options = launch_options or {}
        self.detach_event = threading.Event()
        self.launch_options["detach_event"] = self.detach_event

    def run(self) -> None:
        try:
            crash_reason = self.engine.launch_installed(
                self.version,
                self.username,
                self._on_minecraft_progress,
                self.launch_options,
            )

            if crash_reason:
                self.crash_detected.emit(crash_reason)
            else:
                self.finished_successfully.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc), traceback.format_exc())

    def _on_minecraft_progress(self, status: str, progress: int, maximum: int) -> None:
        self.status_changed.emit("status_game_installing")
        if maximum > 0:
            self.progress_changed.emit(min(100, int(progress * 100 / maximum)))

    def request_detach(self) -> None:
        self.detach_event.set()

    def request_terminate_game(self) -> None:
        self.engine.terminate_game_process()
