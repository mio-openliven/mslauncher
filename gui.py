from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import requests
from PyQt6.QtCore import QSize, QTimer, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QCursor, QIcon, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from launcher_core import MinecraftEngine


CONFIG_FILE = "launcher_config.json"
CHUNK_SIZE = 1024 * 1024
DOWNLOAD_RETRIES = 3
REQUEST_TIMEOUT = 60
BACKGROUND_DIR = Path(__file__).resolve().parent / "assets" / "backgrounds"
ICON_DIR = Path(__file__).resolve().parent / "assets" / "icons"
BACKGROUND_FILES = (
    "bg_01.jpg",
    "bg_02.jpg",
    "bg_03.jpg",
    "bg_04.jpg",
    "bg_05.jpg",
    "bg_06.jpg",
)


TRANSLATIONS = {
    "EN": {
        "app_title": "MSLauncher",
        "brand_title": "MSLauncher 1.9.0",
        "brand_credit": "Software by Nukem coders",
        "brand_subtitle_project": "Project entry point",
        "brand_subtitle_crew": "Built for the crew",
        "brand_subtitle_places": "Everything in its place",
        "brand_subtitle_session": "A clean start for the session",
        "settings_title": "Launcher Panel",
        "settings_body": "Build config, sync status and crash reports will appear here.",
        "language": "Language",
        "build": "Build",
        "username": "Nickname",
        "version": "Minecraft version",
        "play": "Check mods and PLAY",
        "play_idle": "Launch & Mods",
        "action_motor": "Rolling!",
        "action_go": "Action!",
        "action_scene": "Scene up!",
        "action_cut": "Cut!",
        "action_awake": "Stay sharp!",
        "loading_versions": "Loading versions...",
        "ready": "Ready",
        "status_syncing": "Checking modpack files...",
        "status_loading_build": "Loading build config...",
        "status_no_downloads": "All files are up to date.",
        "status_downloading": "Downloading files...",
        "status_downloading_file": "Downloading: {file}",
        "status_download_complete": "Files downloaded.",
        "status_launching": "Launching Minecraft...",
        "status_game_installing": "Preparing Minecraft files...",
        "status_game_running": "Minecraft is running.",
        "status_game_closed": "Minecraft closed.",
        "error": "Error",
        "empty_username": "Enter a nickname.",
        "empty_version": "Select a Minecraft version.",
        "empty_build": "Select a build.",
        "empty_manifest": "Set manifest_url or source_key for the selected build in launcher_config.json.",
        "versions_failed": "Could not load Minecraft versions: {error}",
        "sync_failed": "Could not sync files: {error}",
        "build_config_failed": "Could not load build config: {error}",
        "download_failed": "Could not download files: {error}",
        "launch_failed": "Could not launch Minecraft: {error}",
        "hash_failed": "Downloaded file checksum mismatch: {file}",
        "crash_title": "Minecraft crashed",
    },
    "RU": {
        "app_title": "MSLauncher",
        "brand_title": "MSLauncher 1.9.0",
        "brand_credit": "\u0421\u043e\u0444\u0442 \u043e\u0442 \u043a\u043e\u0434\u0435\u0440\u043e\u0432 \u041d\u044e\u043a\u0435\u043c\u0430",
        "brand_subtitle_project": "\u0422\u043e\u0447\u043a\u0430 \u0432\u0445\u043e\u0434\u0430 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442",
        "brand_subtitle_crew": "\u0421\u043e\u0431\u0440\u0430\u043d\u043e \u0434\u043b\u044f \u0441\u0432\u043e\u0435\u0439 \u043a\u043e\u043c\u0430\u043d\u0434\u044b",
        "brand_subtitle_places": "\u0412\u0441\u0435 \u043d\u0430 \u0441\u0432\u043e\u0438\u0445 \u043c\u0435\u0441\u0442\u0430\u0445",
        "brand_subtitle_session": "\u0427\u0438\u0441\u0442\u044b\u0439 \u0441\u0442\u0430\u0440\u0442 \u0434\u043b\u044f \u0441\u0435\u0441\u0441\u0438\u0438",
        "settings_title": "\u041f\u0430\u043d\u0435\u043b\u044c \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430",
        "settings_body": "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0443\u0442 \u043a\u043e\u043d\u0444\u0438\u0433 \u0441\u0431\u043e\u0440\u043a\u0438, \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438 \u0438 \u043e\u0442\u0447\u0435\u0442\u044b \u043e\u0448\u0438\u0431\u043e\u043a.",
        "language": "\u042f\u0437\u044b\u043a",
        "build": "\u0421\u0431\u043e\u0440\u043a\u0430",
        "username": "\u041d\u0438\u043a\u043d\u0435\u0439\u043c",
        "version": "\u0412\u0435\u0440\u0441\u0438\u044f Minecraft",
        "play": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043c\u043e\u0434\u044b \u0438 \u0418\u0413\u0420\u0410\u0422\u042c",
        "play_idle": "\u0417\u0430\u043f\u0443\u0441\u043a \u0438 \u043c\u043e\u0434\u044b",
        "action_motor": "\u041c\u043e\u0442\u043e\u0440!",
        "action_go": "\u041f\u043e\u0435\u0445\u0430\u043b\u0438!",
        "action_scene": "\u042d\u043a\u0448\u0435\u043d\u0430!",
        "action_cut": "\u0421\u043d\u044f\u0442\u043e!",
        "action_awake": "\u041d\u0435 \u0441\u043f\u0438\u043c!",
        "loading_versions": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0432\u0435\u0440\u0441\u0438\u0439...",
        "ready": "\u0413\u043e\u0442\u043e\u0432\u043e",
        "status_syncing": "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0444\u0430\u0439\u043b\u043e\u0432 \u0441\u0431\u043e\u0440\u043a\u0438...",
        "status_loading_build": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043a\u043e\u043d\u0444\u0438\u0433\u0430 \u0441\u0431\u043e\u0440\u043a\u0438...",
        "status_no_downloads": "\u0412\u0441\u0435 \u0444\u0430\u0439\u043b\u044b \u0443\u0436\u0435 \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b.",
        "status_downloading": "\u0421\u043a\u0430\u0447\u0438\u0432\u0430\u043d\u0438\u0435 \u0444\u0430\u0439\u043b\u043e\u0432...",
        "status_downloading_file": "\u0421\u043a\u0430\u0447\u0438\u0432\u0430\u043d\u0438\u0435: {file}",
        "status_download_complete": "\u0424\u0430\u0439\u043b\u044b \u0441\u043a\u0430\u0447\u0430\u043d\u044b.",
        "status_launching": "\u0417\u0430\u043f\u0443\u0441\u043a Minecraft...",
        "status_game_installing": "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 \u0444\u0430\u0439\u043b\u043e\u0432 Minecraft...",
        "status_game_running": "Minecraft \u0437\u0430\u043f\u0443\u0449\u0435\u043d.",
        "status_game_closed": "Minecraft \u0437\u0430\u043a\u0440\u044b\u0442.",
        "error": "\u041e\u0448\u0438\u0431\u043a\u0430",
        "empty_username": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u0438\u043a\u043d\u0435\u0439\u043c.",
        "empty_version": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432\u0435\u0440\u0441\u0438\u044e Minecraft.",
        "empty_build": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0431\u043e\u0440\u043a\u0443.",
        "empty_manifest": "\u0423\u043a\u0430\u0436\u0438\u0442\u0435 manifest_url \u0438\u043b\u0438 source_key \u0434\u043b\u044f \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0439 \u0441\u0431\u043e\u0440\u043a\u0438 \u0432 launcher_config.json.",
        "versions_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0432\u0435\u0440\u0441\u0438\u0438 Minecraft: {error}",
        "sync_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u0432\u0435\u0440\u0438\u0442\u044c \u0444\u0430\u0439\u043b\u044b: {error}",
        "build_config_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043a\u043e\u043d\u0444\u0438\u0433 \u0441\u0431\u043e\u0440\u043a\u0438: {error}",
        "download_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043a\u0430\u0447\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b: {error}",
        "launch_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c Minecraft: {error}",
        "hash_failed": "\u0425\u044d\u0448 \u0441\u043a\u0430\u0447\u0430\u043d\u043d\u043e\u0433\u043e \u0444\u0430\u0439\u043b\u0430 \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u043b: {file}",
        "crash_title": "Minecraft \u0432\u044b\u043b\u0435\u0442\u0435\u043b",
    },
}


def load_launcher_config(config_path: str | Path = CONFIG_FILE) -> dict[str, object]:
    default_config: dict[str, object] = {
        "manifest_url": "",
        "game_directory": "",
        "default_language": "EN",
        "default_username": "",
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
    except (OSError, json.JSONDecodeError):
        return default_config

    if not isinstance(loaded_config, dict):
        return default_config

    for key in ("manifest_url", "game_directory", "default_language", "default_username", "default_build"):
        value = loaded_config.get(key)
        if isinstance(value, str):
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
    with path.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def get_config_text(config: dict[str, object], key: str, default: str = "") -> str:
    value = config.get(key, default)
    return value if isinstance(value, str) else default


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


def resolve_build_config(build: dict[str, object]) -> dict[str, object]:
    source_key = str(build.get("source_key", "")).strip()
    if not source_key:
        return dict(build)

    response = requests.get(normalize_source_key(source_key), timeout=30)
    response.raise_for_status()
    remote_config = response.json()

    if not isinstance(remote_config, dict):
        raise RuntimeError("Remote build config must be a JSON object.")

    resolved_build = dict(build)
    for key in ("id", "name", "minecraft_version", "loader", "loader_version", "manifest_url", "server", "port"):
        value = remote_config.get(key)
        if isinstance(value, str):
            resolved_build[key] = value

    return resolved_build


def normalize_source_key(source_key: str) -> str:
    if source_key.startswith(("http://", "https://")):
        return source_key
    return f"http://{source_key.strip('/')}/mslauncher/build.json"


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

    def __init__(self, build: dict[str, object]) -> None:
        super().__init__()
        self.build = build

    def run(self) -> None:
        try:
            self.build_loaded.emit(resolve_build_config(self.build))
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
    ) -> None:
        super().__init__()
        self.engine = engine
        self.manifest_url = manifest_url
        self.game_directory = Path(game_directory)

    def run(self) -> None:
        try:
            self.status_changed.emit("status_syncing")
            files = self.engine.sync_files(self.manifest_url, self.game_directory)

            if not files:
                self.progress_changed.emit(100)
                self.status_changed.emit("status_no_downloads")
                self.finished_successfully.emit()
                return

            self.status_changed.emit("status_downloading")
            try:
                self._download_files(files)
            except Exception as exc:
                self.error_occurred.emit("download_failed", str(exc))
                return

            self.progress_changed.emit(100)
            self.status_changed.emit("status_download_complete")
            self.finished_successfully.emit()
        except requests.RequestException as exc:
            self.error_occurred.emit("download_failed", str(exc))
        except Exception as exc:
            self.error_occurred.emit("sync_failed", str(exc))

    def _download_files(self, files: list[dict[str, str | int]]) -> None:
        total_bytes = sum(int(file.get("size", 0)) for file in files)
        completed_bytes = 0

        for file_info in files:
            relative_path = self._safe_relative_path(file_info)
            url = str(file_info.get("url", "")).strip()
            expected_hash = str(file_info.get("sha256", "")).lower().strip()
            expected_size = int(file_info.get("size", 0))

            if not url:
                raise RuntimeError(f"Missing download URL for {relative_path}")

            self.status_detail_changed.emit("status_downloading_file", relative_path)
            target_path = self.game_directory / relative_path
            self._download_file_with_retry(
                url=url,
                target_path=target_path,
                expected_hash=expected_hash,
                relative_path=relative_path,
                completed_bytes=completed_bytes,
                total_bytes=total_bytes,
            )
            completed_bytes += expected_size
            self.progress_changed.emit(self._calculate_progress(completed_bytes, total_bytes))

    def _download_file_with_retry(
        self,
        url: str,
        target_path: Path,
        expected_hash: str,
        relative_path: str,
        completed_bytes: int,
        total_bytes: int,
    ) -> None:
        last_error: Exception | None = None

        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            part_path = target_path.with_name(f"{target_path.name}.part")

            try:
                self._download_to_part_file(
                    url=url,
                    part_path=part_path,
                    completed_bytes=completed_bytes,
                    total_bytes=total_bytes,
                )
                self._verify_downloaded_file(part_path, expected_hash, relative_path)
                self._replace_target_file(part_path, target_path)
                return
            except Exception as exc:
                last_error = exc
                part_path.unlink(missing_ok=True)
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

    def _verify_downloaded_file(self, part_path: Path, expected_hash: str, relative_path: str) -> None:
        if expected_hash and self._calculate_sha256(part_path) != expected_hash:
            raise RuntimeError(f"Checksum mismatch for {relative_path}")

    def _replace_target_file(self, part_path: Path, target_path: Path) -> None:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.replace(target_path)

    def _safe_relative_path(self, file_info: dict[str, str | int]) -> str:
        relative_path = str(file_info.get("path", "")).replace("\\", "/").strip("/")
        if not relative_path or ".." in Path(relative_path).parts:
            raise RuntimeError(f"Unsafe manifest path: {relative_path}")
        return relative_path

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
    error_occurred = pyqtSignal(str)
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
            self.error_occurred.emit(str(exc))

    def _on_minecraft_progress(self, status: str, progress: int, maximum: int) -> None:
        self.status_changed.emit("status_game_installing")
        if maximum > 0:
            self.progress_changed.emit(min(100, int(progress * 100 / maximum)))


class ParallaxFrame(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(True)
        self._current_offset_x = 0.0
        self._current_offset_y = 0.0
        self._target_offset_x = 0.0
        self._target_offset_y = 0.0
        self._pixmap = self._load_background()
        self._particle_phase = 0
        self._particles = self._create_particles()
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(16)
        self._animation_timer.timeout.connect(self._tick)
        self._animation_timer.start()

    def _load_background(self) -> QPixmap | None:
        available_files = [BACKGROUND_DIR / name for name in BACKGROUND_FILES if (BACKGROUND_DIR / name).is_file()]
        if not available_files:
            return None
        return QPixmap(str(random.choice(available_files)))

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._target_offset_x = 0.0
        self._target_offset_y = 0.0
        super().leaveEvent(event)

    def _tick(self) -> None:
        if self.window().isActiveWindow():
            local_position = self.mapFromGlobal(QCursor.pos())
            bounded_x = min(max(local_position.x(), 0), max(1, self.width()))
            bounded_y = min(max(local_position.y(), 0), max(1, self.height()))
            relative_x = (bounded_x / max(1, self.width())) - 0.5
            relative_y = (bounded_y / max(1, self.height())) - 0.5
            curve_x = relative_x + (relative_y * relative_y * 0.42 if relative_x >= 0 else -relative_y * relative_y * 0.42)
            curve_y = relative_y - relative_x * relative_y * 0.55
            self._target_offset_x = curve_x * 70
            self._target_offset_y = curve_y * 42

        self._current_offset_x += (self._target_offset_x - self._current_offset_x) * 0.08
        self._current_offset_y += (self._target_offset_y - self._current_offset_y) * 0.08
        self._particle_phase = (self._particle_phase + 1) % 720
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        if self._pixmap and not self._pixmap.isNull():
            self._paint_cover_pixmap(painter)
        else:
            painter.fillRect(self.rect(), QColor("#253642"))

        painter.fillRect(self.rect(), QColor(5, 9, 12, 122))
        self._paint_particles(painter)
        self._paint_depth_overlay(painter)
        super().paintEvent(event)

    def _paint_cover_pixmap(self, painter: QPainter) -> None:
        target_width = max(1, int(self.width() * 1.2) + 120)
        target_height = max(1, int(self.height() * 1.2) + 100)
        scaled = self._pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        x = int((self.width() - scaled.width()) / 2 - self._current_offset_x)
        y = int((self.height() - scaled.height()) / 2 - self._current_offset_y)
        painter.drawPixmap(x, y, scaled)

    def _paint_depth_overlay(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        painter.fillRect(0, 0, width, int(height * 0.12), QColor(0, 12, 8, 64))
        painter.fillRect(0, int(height * 0.7), width, int(height * 0.3), QColor(0, 0, 0, 82))
        for index in range(10):
            alpha = max(0, 44 - index * 4)
            painter.fillRect(index * 7, 0, 7, height, QColor(0, 0, 0, alpha))
            painter.fillRect(width - (index + 1) * 9, 0, 9, height, QColor(0, 0, 0, max(0, 42 - index * 4)))

    def _create_particles(self) -> list[tuple[float, float, float, int, int]]:
        randomizer = random.Random(42)
        return [
            (
                randomizer.random(),
                randomizer.random(),
                randomizer.uniform(0.18, 0.75),
                randomizer.choice((1, 1, 1, 1, 2, 3)),
                randomizer.randint(18, 62),
            )
            for _ in range(204)
        ]

    def _paint_particles(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        width = max(1, self.width())
        height = max(1, self.height())
        cursor_position = self.mapFromGlobal(QCursor.pos())
        cursor_x = min(max(cursor_position.x(), 0), width)
        cursor_y = min(max(cursor_position.y(), 0), height)

        for index, (base_x, base_y, speed, size, alpha) in enumerate(self._particles):
            drift_cycle = 315
            drift = (self._particle_phase * speed + index * 19) % drift_cycle
            fade = abs((drift_cycle / 2) - drift) / (drift_cycle / 2)
            particle_alpha = int(min(92, alpha * 1.15 * (1 - fade * 0.56)))
            if particle_alpha <= 4:
                continue

            x = int((base_x * width + drift * 0.22 + self._current_offset_x * 0.22) % width)
            y = int((base_y * height - drift * 0.16 + self._current_offset_y * 0.16) % height)
            distance_x = x - cursor_x
            distance_y = y - cursor_y
            distance_squared = distance_x * distance_x + distance_y * distance_y
            repel_radius = 150
            if 0 < distance_squared < repel_radius * repel_radius:
                distance = distance_squared ** 0.5
                force = (1 - distance / repel_radius) ** 2
                x += int((distance_x / distance) * force * 56)
                y += int((distance_y / distance) * force * 56)

            painter.setBrush(QColor(225, 238, 230, particle_alpha))
            painter.drawEllipse(x, y, size, size)

        painter.restore()


class MSLauncherWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config = load_launcher_config()
        self.builds = get_config_builds(self.config)
        config_language = get_config_text(self.config, "default_language", "EN")
        self.language = config_language if config_language in TRANSLATIONS else "EN"
        configured_game_directory = get_config_text(self.config, "game_directory").strip()
        self.engine = MinecraftEngine(configured_game_directory or None)
        self.game_directory = self.engine.minecraft_directory
        self.download_worker: DownloadWorker | None = None
        self.launch_worker: LaunchWorker | None = None
        self.versions_worker: VersionsWorker | None = None
        self.build_config_worker: BuildConfigWorker | None = None
        self.selected_username = ""
        self.selected_version = ""
        self.selected_manifest_url = ""
        self.selected_launch_options: dict[str, object] = {}
        self.brand_subtitle_key = random.choice(self.get_brand_subtitle_keys())
        self.action_phrase_key = "play_idle"

        self._build_ui()
        self._connect_signals()
        self.apply_translations()
        self.load_versions()

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        hero_frame = ParallaxFrame()
        hero_frame.setObjectName("heroFrame")
        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setContentsMargins(34, 28, 34, 30)
        hero_layout.addStretch()

        hero_content_layout = QHBoxLayout()
        hero_content_layout.setSpacing(22)

        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebarFrame")
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(10, 14, 10, 14)
        sidebar_layout.setSpacing(11)

        self.settings_button = self.create_side_button("settings")
        self.settings_button.clicked.connect(self.toggle_info_panel)
        sidebar_layout.addWidget(self.settings_button)

        self.social_buttons: list[QPushButton] = []
        for icon_name in ("discord", "tiktok", "telegram", "youtube", "instagram", "link"):
            button = self.create_side_button(icon_name)
            button.hide()
            self.social_buttons.append(button)
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        brand_panel = QFrame()
        brand_panel.setObjectName("brandPanel")
        brand_layout = QVBoxLayout(brand_panel)
        brand_layout.setContentsMargins(24, 16, 24, 16)
        brand_layout.setSpacing(5)

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.credit_label = QLabel()
        self.credit_label.setObjectName("creditLabel")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        brand_layout.addWidget(self.title_label)
        brand_layout.addWidget(self.subtitle_label)
        brand_layout.addWidget(self.credit_label)
        brand_panel.setMaximumWidth(500)
        brand_panel.setMaximumHeight(142)

        self.info_panel = QFrame()
        self.info_panel.setObjectName("infoPanel")
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(22, 18, 22, 18)
        info_layout.setSpacing(10)
        self.info_title_label = QLabel()
        self.info_title_label.setObjectName("infoTitle")
        self.info_body_label = QLabel()
        self.info_body_label.setObjectName("infoBody")
        self.info_body_label.setWordWrap(True)
        info_layout.addWidget(self.info_title_label)
        info_layout.addWidget(self.info_body_label)
        info_layout.addStretch()
        self.info_panel.setMaximumWidth(320)
        self.info_panel.hide()

        hero_content_layout.addWidget(self.sidebar_frame)
        hero_content_layout.addWidget(brand_panel)
        hero_content_layout.addWidget(self.info_panel)
        hero_content_layout.addStretch()

        hero_layout.addLayout(hero_content_layout)
        hero_layout.addStretch()

        control_frame = QFrame()
        control_frame.setObjectName("controlFrame")
        control_layout = QGridLayout(control_frame)
        control_layout.setContentsMargins(18, 12, 18, 14)
        control_layout.setHorizontalSpacing(10)
        control_layout.setVerticalSpacing(6)

        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["EN", "RU"])
        self.language_combo.setCurrentText(self.language)

        self.username_label = QLabel()
        self.username_input = QLineEdit()
        self.username_input.setText(get_config_text(self.config, "default_username"))

        self.build_label = QLabel()
        self.build_combo = QComboBox()
        self.populate_builds()

        self.version_label = QLabel()
        self.version_combo = QComboBox()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(8)

        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

        self.play_button = QPushButton()
        self.play_button.setObjectName("playButton")
        self.play_button.setMinimumHeight(48)

        control_layout.addWidget(self.username_label, 0, 0)
        control_layout.addWidget(self.build_label, 0, 1)
        control_layout.addWidget(self.version_label, 0, 2)
        control_layout.addWidget(self.language_label, 0, 3)
        control_layout.addWidget(self.username_input, 1, 0)
        control_layout.addWidget(self.build_combo, 1, 1)
        control_layout.addWidget(self.version_combo, 1, 2)
        control_layout.addWidget(self.language_combo, 1, 3)
        control_layout.addWidget(self.play_button, 0, 4, 2, 1)
        control_layout.addWidget(self.status_label, 2, 0, 1, 4)
        control_layout.addWidget(self.progress_bar, 2, 4)
        control_layout.setColumnStretch(0, 2)
        control_layout.setColumnStretch(1, 2)
        control_layout.setColumnStretch(2, 2)
        control_layout.setColumnStretch(3, 1)
        control_layout.setColumnStretch(4, 2)

        root_layout.addWidget(hero_frame, 1)
        root_layout.addWidget(control_frame, 0)

        self.setCentralWidget(central_widget)
        self.setMinimumSize(760, 360)
        self.resize(900, 460)
        self.apply_styles()

    def create_side_button(self, icon_name: str) -> QPushButton:
        button = QPushButton()
        button.setObjectName("sideButton")
        icon_path = ICON_DIR / f"{icon_name}.svg"
        if icon_path.is_file():
            button.setIcon(QIcon(str(icon_path)))
            button.setIconSize(QSize(21, 21))
        else:
            button.setText(icon_name[:2].upper())
        return button

    def _connect_signals(self) -> None:
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.build_combo.currentIndexChanged.connect(self.on_build_changed)
        self.play_button.clicked.connect(self.check_mods_and_play)

    def change_language(self, language: str) -> None:
        if language in TRANSLATIONS:
            self.language = language
            self.apply_translations()
            self.save_user_preferences()

    def apply_translations(self) -> None:
        self.setWindowTitle(self.translate("app_title"))
        self.title_label.setText(self.translate("brand_title"))
        self.subtitle_label.setText(self.translate(self.brand_subtitle_key))
        self.credit_label.setText(self.translate("brand_credit"))
        self.info_title_label.setText(self.translate("settings_title"))
        self.info_body_label.setText(self.translate("settings_body"))
        self.language_label.setText(self.translate("language"))
        self.build_label.setText(self.translate("build"))
        self.username_label.setText(self.translate("username"))
        self.version_label.setText(self.translate("version"))
        self.play_button.setText(self.translate(self.action_phrase_key))

        status_key = self.status_label.property("status_key")
        status_detail = self.status_label.property("status_detail")
        if isinstance(status_key, str) and isinstance(status_detail, str):
            self.set_status_detail(status_key, status_detail)
        elif isinstance(status_key, str):
            self.set_status(status_key)
        else:
            self.set_status("ready")

    def apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow {
                background: #07140f;
            }
            #heroFrame {
                background: #07140f;
                border: 0;
            }
            #brandPanel {
                background: rgba(14, 18, 18, 188);
                border: 1px solid rgba(255, 255, 255, 26);
                border-radius: 8px;
            }
            #sidebarFrame {
                background: rgba(8, 12, 12, 138);
                border: 1px solid rgba(255, 255, 255, 12);
                border-radius: 8px;
                min-width: 54px;
                max-width: 54px;
            }
            #infoPanel {
                background: rgba(14, 18, 18, 188);
                border: 1px solid rgba(255, 255, 255, 22);
                border-radius: 8px;
            }
            #controlFrame {
                background: #111917;
                border-top: 1px solid #263a31;
            }
            QLabel {
                color: #dceee4;
                font-size: 12px;
            }
            #titleLabel {
                color: #ffffff;
                font-size: 30px;
                font-weight: 800;
            }
            #subtitleLabel {
                color: #b8c9bf;
                font-size: 12px;
            }
            #creditLabel {
                color: #e5f2ea;
                font-size: 12px;
                font-weight: 700;
            }
            #infoTitle {
                color: #ffffff;
                font-size: 18px;
                font-weight: 800;
            }
            #infoBody {
                color: #b5c8bd;
                font-size: 13px;
            }
            #statusLabel {
                color: #b9d4c4;
            }
            QPushButton#sideButton {
                background: rgba(255, 255, 255, 18);
                color: #dceee4;
                border: 1px solid rgba(255, 255, 255, 16);
                border-radius: 8px;
                min-width: 34px;
                min-height: 34px;
                max-width: 34px;
                max-height: 34px;
                font-size: 10px;
                font-weight: 800;
            }
            QPushButton#sideButton:hover {
                background: rgba(36, 223, 119, 80);
                color: #ffffff;
                border: 1px solid rgba(36, 223, 119, 130);
                padding-left: 1px;
                padding-top: 1px;
            }
            QLineEdit,
            QComboBox {
                background: #eaf1ec;
                color: #111917;
                border: 1px solid #284b38;
                border-radius: 4px;
                padding: 5px 8px;
                min-height: 24px;
            }
            QLineEdit:focus,
            QComboBox:focus {
                border: 1px solid #1ee06f;
            }
            QComboBox::drop-down {
                border: 0;
                width: 22px;
            }
            QPushButton#playButton {
                background: rgba(214, 230, 220, 22);
                color: #dceee4;
                border: 1px solid rgba(220, 238, 228, 70);
                border-radius: 18px;
                font-size: 13px;
                font-weight: 700;
                letter-spacing: 0px;
                padding: 8px 20px;
            }
            QPushButton#playButton:hover {
                background: rgba(117, 152, 134, 58);
                color: #ffffff;
                border: 1px solid rgba(191, 223, 206, 130);
            }
            QPushButton#playButton:disabled {
                background: rgba(117, 152, 134, 28);
                color: #aab9b1;
                border: 1px solid rgba(191, 223, 206, 58);
            }
            QProgressBar {
                background: #25382e;
                border: 0;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #86b89d;
                border-radius: 3px;
            }
            """
        )

    def populate_builds(self) -> None:
        self.build_combo.clear()
        default_build = get_config_text(self.config, "default_build")
        selected_index = 0

        for index, build in enumerate(self.builds):
            build_id = str(build.get("id", "")).strip()
            build_name = str(build.get("name", build_id or "Build")).strip()
            self.build_combo.addItem(build_name, build)
            if build_id and build_id == default_build:
                selected_index = index

        if self.build_combo.count() > 0:
            self.build_combo.setCurrentIndex(selected_index)

    def load_versions(self) -> None:
        self.set_status("loading_versions")
        self.version_combo.clear()
        self.version_combo.setEnabled(False)

        self.versions_worker = VersionsWorker(self.engine)
        self.versions_worker.versions_loaded.connect(self.on_versions_loaded)
        self.versions_worker.error_occurred.connect(self.on_versions_failed)
        self.versions_worker.start()

    def on_versions_loaded(self, versions: list) -> None:
        for version in versions:
            if not isinstance(version, dict):
                continue

            version_id = str(version.get("id", ""))
            if version_id:
                self.version_combo.addItem(version_id)

        self.version_combo.setEnabled(True)
        self.on_build_changed()
        self.set_status("ready")

    def on_versions_failed(self, error: str) -> None:
        self.version_combo.setEnabled(True)
        self.show_error(self.translate("versions_failed", error=error))
        self.set_status("ready")

    def on_build_changed(self) -> None:
        build = self.get_selected_build()
        if build is None:
            return

        configured_version = str(build.get("minecraft_version", "")).strip()
        if not configured_version:
            return

        index = self.version_combo.findText(configured_version)
        if index >= 0:
            self.version_combo.setCurrentIndex(index)

        self.save_user_preferences()

    def get_selected_build(self) -> dict[str, object] | None:
        build = self.build_combo.currentData()
        return build if isinstance(build, dict) else None

    def get_selected_build_id(self) -> str:
        build = self.get_selected_build()
        if build is None:
            return ""
        return str(build.get("id", "")).strip()

    def check_mods_and_play(self) -> None:
        username = self.username_input.text().strip()
        build = self.get_selected_build()

        if not username:
            self.show_error(self.translate("empty_username"))
            return
        if build is None:
            self.show_error(self.translate("empty_build"))
            return

        self.selected_username = username
        self.action_phrase_key = random.choice(self.get_action_phrase_keys())
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.play_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.set_status("status_loading_build")

        self.build_config_worker = BuildConfigWorker(build)
        self.build_config_worker.build_loaded.connect(self.on_build_config_loaded)
        self.build_config_worker.error_occurred.connect(self.on_build_config_failed)
        self.build_config_worker.start()

    def on_build_config_loaded(self, resolved_build: dict) -> None:
        version = self.version_combo.currentText().strip()
        configured_version = str(resolved_build.get("minecraft_version", "")).strip()
        if configured_version:
            version = configured_version
            index = self.version_combo.findText(configured_version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)

        if not version:
            self.show_error(self.translate("empty_version"))
            self.play_button.setEnabled(True)
            self.action_phrase_key = "play_idle"
            self.play_button.setText(self.translate(self.action_phrase_key))
            self.set_status("ready")
            return

        manifest_url = str(resolved_build.get("manifest_url", "")).strip()
        if not manifest_url:
            self.show_error(self.translate("empty_manifest"))
            self.play_button.setEnabled(True)
            self.action_phrase_key = "play_idle"
            self.play_button.setText(self.translate(self.action_phrase_key))
            self.set_status("ready")
            return

        self.selected_version = version
        self.selected_manifest_url = manifest_url
        self.selected_launch_options = self.build_launch_options(resolved_build)
        self.save_user_preferences()

        self.download_worker = DownloadWorker(self.engine, self.selected_manifest_url, self.game_directory)
        self.download_worker.progress_changed.connect(self.progress_bar.setValue)
        self.download_worker.status_changed.connect(self.set_status)
        self.download_worker.status_detail_changed.connect(self.set_status_detail)
        self.download_worker.error_occurred.connect(self.on_download_failed)
        self.download_worker.finished_successfully.connect(self.launch_game)
        self.download_worker.start()

    def on_build_config_failed(self, error: str) -> None:
        self.play_button.setEnabled(True)
        self.action_phrase_key = "play_idle"
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.show_error(self.translate("build_config_failed", error=error))
        self.set_status("ready")

    def launch_game(self) -> None:
        self.set_status("status_launching")
        self.launch_worker = LaunchWorker(
            self.engine,
            self.selected_version,
            self.selected_username,
            self.selected_launch_options,
        )
        self.launch_worker.progress_changed.connect(self.progress_bar.setValue)
        self.launch_worker.status_changed.connect(self.set_status)
        self.launch_worker.crash_detected.connect(self.on_game_crashed)
        self.launch_worker.error_occurred.connect(self.on_launch_failed)
        self.launch_worker.finished_successfully.connect(self.on_game_closed)
        self.launch_worker.start()

    def on_download_failed(self, error_key: str, error: str) -> None:
        self.play_button.setEnabled(True)
        self.action_phrase_key = "play_idle"
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.show_error(self.translate(error_key, error=error))
        self.set_status("ready")

    def toggle_info_panel(self) -> None:
        should_show = not self.info_panel.isVisible()
        self.info_panel.setVisible(should_show)
        for button in self.social_buttons:
            button.setVisible(should_show)

    def on_launch_failed(self, error: str) -> None:
        self.play_button.setEnabled(True)
        self.action_phrase_key = "play_idle"
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.show_error(self.translate("launch_failed", error=error))
        self.set_status("ready")

    def on_game_crashed(self, crash_reason: str) -> None:
        self.play_button.setEnabled(True)
        self.action_phrase_key = "play_idle"
        self.play_button.setText(self.translate(self.action_phrase_key))
        QMessageBox.critical(self, self.translate("crash_title"), crash_reason)
        self.set_status("ready")

    def on_game_closed(self) -> None:
        self.play_button.setEnabled(True)
        self.action_phrase_key = "play_idle"
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.set_status("status_game_closed")

    def set_status(self, key: str) -> None:
        self.status_label.setProperty("status_key", key)
        self.status_label.setProperty("status_detail", None)
        self.status_label.setText(self.translate(key))

    def set_status_detail(self, key: str, detail: str) -> None:
        self.status_label.setProperty("status_key", key)
        self.status_label.setProperty("status_detail", detail)
        self.status_label.setText(self.translate(key, file=detail))

    def show_error(self, message: str) -> None:
        QMessageBox.critical(self, self.translate("error"), message)

    def build_launch_options(self, build: dict[str, object]) -> dict[str, object]:
        launch_options = dict(get_config_launch_options(self.config))
        loader = str(build.get("loader", "")).strip()
        loader_version = str(build.get("loader_version", "")).strip()
        server = str(build.get("server", "")).strip()
        port = str(build.get("port", "")).strip()

        if loader:
            launch_options["loader"] = loader
        if loader_version:
            launch_options["loader_version"] = loader_version
        if server:
            launch_options["server"] = server
        if port:
            launch_options["port"] = port

        return launch_options

    def save_user_preferences(self) -> None:
        self.config["default_language"] = self.language
        self.config["default_username"] = self.username_input.text().strip()
        selected_build_id = self.get_selected_build_id()
        if selected_build_id:
            self.config["default_build"] = selected_build_id

        try:
            save_launcher_config(self.config)
        except OSError:
            pass

    def closeEvent(self, event) -> None:
        self.save_user_preferences()
        super().closeEvent(event)

    def translate(self, key: str, **kwargs: object) -> str:
        text = TRANSLATIONS.get(self.language, TRANSLATIONS["EN"]).get(key, key)
        if isinstance(text, list):
            return str(text[0]) if text else key
        if kwargs:
            return text.format(**kwargs)
        return text

    def get_brand_subtitle_keys(self) -> list[str]:
        return [
            "brand_subtitle_project",
            "brand_subtitle_crew",
            "brand_subtitle_places",
            "brand_subtitle_session",
        ]

    def get_action_phrase_keys(self) -> list[str]:
        return [
            "action_motor",
            "action_go",
            "action_scene",
            "action_cut",
            "action_awake",
        ]


def main() -> None:
    app = QApplication(sys.argv)
    window = MSLauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
