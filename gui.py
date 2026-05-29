from __future__ import annotations

import hashlib
import json
import random
import sys
from pathlib import Path

import requests
from PyQt6.QtCore import QTimer, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QPainter, QPixmap
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
        "brand_title": "Nukem Team Launcher",
        "brand_subtitle": "Built for professional play",
        "language": "Language",
        "build": "Build",
        "username": "Nickname",
        "version": "Minecraft version",
        "play": "Check mods and PLAY",
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
        "brand_title": "\u041b\u0430\u0443\u043d\u0447\u0435\u0440 \u043a\u043e\u043c\u0430\u043d\u0434\u044b \u041d\u044e\u043a\u0435\u043c\u0430",
        "brand_subtitle": "\u0414\u043b\u044f \u0442\u0435\u0445, \u043a\u0442\u043e \u0438\u0433\u0440\u0430\u0435\u0442 \u043d\u0430 \u0443\u0440\u043e\u0432\u043d\u0435",
        "language": "\u042f\u0437\u044b\u043a",
        "build": "\u0421\u0431\u043e\u0440\u043a\u0430",
        "username": "\u041d\u0438\u043a\u043d\u0435\u0439\u043c",
        "version": "\u0412\u0435\u0440\u0441\u0438\u044f Minecraft",
        "play": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043c\u043e\u0434\u044b \u0438 \u0418\u0413\u0420\u0410\u0422\u042c",
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
    for key in ("id", "name", "minecraft_version", "manifest_url", "server", "port"):
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
        self._mist_offset = 0
        self._pixmap = self._load_background()
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
        if self.width() <= 0 or self.height() <= 0:
            return

        position = event.position()
        relative_x = (position.x() / self.width()) - 0.5
        relative_y = (position.y() / self.height()) - 0.5
        self._target_offset_x = relative_x * 58
        self._target_offset_y = relative_y * 36
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        self._target_offset_x = 0.0
        self._target_offset_y = 0.0
        super().leaveEvent(event)

    def _tick(self) -> None:
        self._current_offset_x += (self._target_offset_x - self._current_offset_x) * 0.08
        self._current_offset_y += (self._target_offset_y - self._current_offset_y) * 0.08
        self._mist_offset = (self._mist_offset + 1) % 240
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        if self._pixmap and not self._pixmap.isNull():
            self._paint_cover_pixmap(painter)
        else:
            painter.fillRect(self.rect(), QColor("#253642"))

        painter.fillRect(self.rect(), QColor(12, 18, 24, 112))
        painter.fillRect(self.rect(), QColor(36, 54, 66, 76))
        self._paint_mist(painter)
        self._paint_vignette(painter)
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

    def _paint_mist(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        mist_color = QColor(235, 245, 255, 18)
        painter.setBrush(mist_color)
        width = max(1, self.width())
        height = max(1, self.height())

        for index in range(4):
            x = ((index * 260 + self._mist_offset) % (width + 260)) - 180
            y = int(height * (0.18 + index * 0.13))
            painter.drawEllipse(x, y, 360, 84)

        painter.restore()

    def _paint_vignette(self, painter: QPainter) -> None:
        painter.fillRect(0, 0, self.width(), 26, QColor(0, 0, 0, 45))
        painter.fillRect(0, self.height() - 60, self.width(), 60, QColor(0, 0, 0, 70))
        painter.fillRect(0, 0, 42, self.height(), QColor(0, 0, 0, 42))
        painter.fillRect(self.width() - 42, 0, 42, self.height(), QColor(0, 0, 0, 42))


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
        hero_layout.setContentsMargins(24, 22, 24, 22)
        hero_layout.addStretch()

        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        hero_layout.addWidget(self.title_label)
        hero_layout.addWidget(self.subtitle_label)
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
        self.subtitle_label.setText(self.translate("brand_subtitle"))
        self.language_label.setText(self.translate("language"))
        self.build_label.setText(self.translate("build"))
        self.username_label.setText(self.translate("username"))
        self.version_label.setText(self.translate("version"))
        self.play_button.setText(self.translate("play"))

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
                background: #1f2a32;
            }
            #heroFrame {
                background: #253642;
                border: 0;
            }
            #controlFrame {
                background: #6aa84f;
                border-top: 1px solid #8bc76a;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            #titleLabel {
                color: #ffffff;
                font-size: 34px;
                font-weight: 800;
            }
            #subtitleLabel {
                color: #cdd7df;
                font-size: 14px;
            }
            #statusLabel {
                color: #eff7eb;
            }
            QLineEdit,
            QComboBox {
                background: #f5f7f2;
                color: #1f2a32;
                border: 1px solid #497a36;
                border-radius: 2px;
                padding: 5px 8px;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: 0;
                width: 22px;
            }
            QPushButton#playButton {
                background: #f0c13d;
                color: #ffffff;
                border: 0;
                border-radius: 4px;
                font-size: 17px;
                font-weight: 700;
                padding: 8px 18px;
            }
            QPushButton#playButton:disabled {
                background: #9aa36f;
                color: #e7eadb;
            }
            QProgressBar {
                background: #497a36;
                border: 0;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #f0c13d;
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
            self.set_status("ready")
            return

        manifest_url = str(resolved_build.get("manifest_url", "")).strip()
        if not manifest_url:
            self.show_error(self.translate("empty_manifest"))
            self.play_button.setEnabled(True)
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
        self.show_error(self.translate(error_key, error=error))
        self.set_status("ready")

    def on_launch_failed(self, error: str) -> None:
        self.play_button.setEnabled(True)
        self.show_error(self.translate("launch_failed", error=error))
        self.set_status("ready")

    def on_game_crashed(self, crash_reason: str) -> None:
        self.play_button.setEnabled(True)
        QMessageBox.critical(self, self.translate("crash_title"), crash_reason)
        self.set_status("ready")

    def on_game_closed(self) -> None:
        self.play_button.setEnabled(True)
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
        server = str(build.get("server", "")).strip()
        port = str(build.get("port", "")).strip()

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
        if kwargs:
            return text.format(**kwargs)
        return text


def main() -> None:
    app = QApplication(sys.argv)
    window = MSLauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
