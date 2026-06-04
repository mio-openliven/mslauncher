from __future__ import annotations

import hashlib
import json
import os
import subprocess
import threading
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

import minecraft_launcher_lib
import minecraft_launcher_lib.mod_loader
import requests

from crash_advisor import advise_crash
from java_diagnostics import JavaDiagnosticError, diagnose_launch_environment
from launcher_update import APP_DISPLAY_NAME, APP_VERSION
from loader_support import INSTALLABLE_LOADERS, format_supported_loaders, normalize_loader
from manifest_validator import ManifestValidationError, validate_manifest
from profile_manager import MANAGED_MARKER
from url_policy import URLPolicyError, normalize_https_url


ProgressCallback = Callable[[str, int, int], None]
MAX_LOG_LINES = 300
MAX_CRASH_LOG_BYTES = 512 * 1024


@dataclass(frozen=True)
class SyncPlan:
    files_to_download: list[dict[str, str | int]]
    unknown_mods: list[str]
    managed_profile: bool
    warning: str = ""


@dataclass(frozen=True)
class CrashLogSource:
    path: Path | None
    lines: list[str]


class MinecraftEngine:
    """Core Minecraft installer/launcher logic for MSLauncher."""

    def __init__(self, minecraft_directory: str | os.PathLike[str] | None = None) -> None:
        self.minecraft_directory = Path(
            minecraft_directory or minecraft_launcher_lib.utils.get_minecraft_directory()
        )
        self._last_log_lines: deque[str] = deque(maxlen=MAX_LOG_LINES)
        self._current_process: subprocess.Popen[str] | None = None
        self._process_lock = threading.Lock()

    def get_all_versions(self) -> list[dict[str, str]]:
        """Return all release versions available from Mojang."""
        try:
            versions = minecraft_launcher_lib.utils.get_version_list()
        except Exception as exc:
            raise RuntimeError(f"Не удалось получить список версий Minecraft: {exc}") from exc

        return [version for version in versions if version.get("type") == "release"]

    def download_and_launch(
        self,
        version: str,
        username: str,
        progress_callback: ProgressCallback | None = None,
        launch_options: dict[str, object] | None = None,
    ) -> threading.Thread:
        """Download the requested version and launch it in a background thread."""
        worker = threading.Thread(
            target=self._download_and_launch_sync,
            args=(version, username, progress_callback, launch_options),
            daemon=True,
        )
        worker.start()
        return worker

    def launch_installed(
        self,
        version: str,
        username: str,
        progress_callback: ProgressCallback | None = None,
        launch_options: dict[str, object] | None = None,
    ) -> str | None:
        """Download missing vanilla assets if needed, launch Minecraft, and return crash text."""
        return self._download_and_launch_sync(version, username, progress_callback, launch_options)

    def monitor_game_process(
        self,
        process: subprocess.Popen[str],
        language: str = "EN",
        detach_event: threading.Event | None = None,
    ) -> str | None:
        """Read game logs in real time and return a human-readable crash reason."""
        self._last_log_lines.clear()

        stdout_thread = threading.Thread(
            target=self._read_stream,
            args=(process.stdout,),
            daemon=True,
        )
        stderr_thread = threading.Thread(
            target=self._read_stream,
            args=(process.stderr,),
            daemon=True,
        )

        stdout_thread.start()
        stderr_thread.start()

        while True:
            if detach_event is not None and detach_event.is_set():
                self._close_process_pipes(process)
                return None

            exit_code = process.poll()
            if exit_code is not None:
                break
            time.sleep(0.2)

        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)

        if exit_code == 0:
            return None

        crash_source = self._collect_crash_log_source()
        log_lines = crash_source.lines or list(self._last_log_lines)
        return self._detect_crash_reason(log_lines, exit_code, language, crash_source.path)

    def sync_files(
        self,
        manifest_url: str,
        game_directory: str | os.PathLike[str],
        *,
        allow_insecure_local: bool = False,
        allow_insecure_http: bool = False,
        require_files: bool = False,
    ) -> SyncPlan:
        """Compare local files with a remote manifest and return a safe sync plan."""
        game_path = Path(game_directory)

        try:
            safe_manifest_url = normalize_https_url(
                manifest_url,
                "manifest_url",
                allow_insecure_local=allow_insecure_local,
                allow_insecure_http=allow_insecure_http,
            )
            response = requests.get(safe_manifest_url, timeout=30)
            response.raise_for_status()
            manifest = response.json()
        except URLPolicyError as exc:
            raise RuntimeError(str(exc)) from exc
        except requests.RequestException as exc:
            raise RuntimeError(f"Не удалось скачать манифест сборки: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Манифест сборки содержит некорректный JSON: {exc}") from exc

        try:
            manifest_files = validate_manifest(
                manifest,
                allow_insecure_local=allow_insecure_local,
                allow_insecure_http=allow_insecure_http,
            )
        except ManifestValidationError as exc:
            raise RuntimeError(f"Манифест сборки поврежден: {exc}") from exc
        if require_files and not manifest_files:
            raise RuntimeError("Server manifest contains no files. Check generated manifest.json before launching.")

        expected_files: dict[str, dict[str, str | int]] = {}
        files_to_download: list[dict[str, str | int]] = []

        for item in manifest_files:
            relative_path = str(item["path"])
            expected_hash = str(item.get("sha256", "")).lower()

            expected_files[relative_path] = item
            local_file = game_path / relative_path

            if not local_file.is_file() or self._calculate_sha256(local_file) != expected_hash:
                files_to_download.append(item)

        unknown_mods = self._find_unknown_mods(game_path, expected_files)
        managed_profile = self._is_managed_profile(game_path)
        warning = ""
        if unknown_mods and not managed_profile:
            warning = (
                "Extra mods were found, but this folder is not marked as managed by MSLauncher. "
                "No files will be deleted."
            )

        return SyncPlan(files_to_download, unknown_mods, managed_profile, warning)

    def _normalize_manifest_path(self, raw_path: object) -> str:
        relative_path = str(raw_path).replace("\\", "/").strip("/")
        path_parts = Path(relative_path).parts

        if (
            not relative_path
            or Path(relative_path).is_absolute()
            or ".." in path_parts
            or relative_path.startswith(("/", "\\"))
        ):
            raise RuntimeError(f"Манифест содержит небезопасный путь: {raw_path}")

        return relative_path

    def _download_and_launch_sync(
        self,
        version: str,
        username: str,
        progress_callback: ProgressCallback | None,
        launch_options: dict[str, object] | None = None,
    ) -> str | None:
        self.minecraft_directory.mkdir(parents=True, exist_ok=True)

        callback_options = self._build_callback_options(progress_callback)
        effective_launch_options = dict(launch_options or {})

        try:
            launch_version = self._install_requested_version(version, callback_options, effective_launch_options)

            options = {
                "username": username.strip() or "Player",
                "uuid": str(uuid4()),
                "token": "",
                "gameDirectory": str(self.minecraft_directory),
                "launcherName": APP_DISPLAY_NAME,
                "launcherVersion": APP_VERSION,
            }
            options.update(self._build_launch_options(effective_launch_options))

            command = minecraft_launcher_lib.command.get_minecraft_command(
                launch_version,
                str(self.minecraft_directory),
                options,
            )

            process = subprocess.Popen(
                command,
                cwd=str(self.minecraft_directory),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            with self._process_lock:
                self._current_process = process

            language = self._clean_config_text(effective_launch_options.get("language")) or "EN"
            detach_event = effective_launch_options.get("detach_event")
            if not isinstance(detach_event, threading.Event):
                detach_event = None
            try:
                return self.monitor_game_process(process, language, detach_event)
            finally:
                with self._process_lock:
                    if self._current_process is process:
                        self._current_process = None
        except RuntimeError:
            raise
        except Exception as exc:
            raise RuntimeError(f"Не удалось скачать или запустить Minecraft {version}: {exc}") from exc

    def _install_requested_version(
        self,
        version: str,
        callback_options: dict[str, Callable[..., None]],
        launch_options: dict[str, object] | None,
    ) -> str:
        loader = normalize_loader(self._clean_config_text((launch_options or {}).get("loader")))
        loader_version = self._clean_config_text((launch_options or {}).get("loader_version"))
        java_path = self._clean_config_text((launch_options or {}).get("java_path"))

        try:
            selected_java_path = diagnose_launch_environment(version, loader or "vanilla", java_path)
        except JavaDiagnosticError as exc:
            raise RuntimeError(str(exc)) from exc
        if launch_options is not None:
            launch_options["java_path"] = selected_java_path

        if not loader or loader == "vanilla":
            minecraft_launcher_lib.install.install_minecraft_version(
                version,
                str(self.minecraft_directory),
                callback=callback_options,
            )
            return version

        if loader not in INSTALLABLE_LOADERS:
            raise RuntimeError(f"Unsupported mod loader: {loader}. Use {format_supported_loaders()}.")

        mod_loader = minecraft_launcher_lib.mod_loader.get_mod_loader(loader)
        install_loader_version = None if loader_version in ("", "latest") else loader_version
        return mod_loader.install(
            version,
            str(self.minecraft_directory),
            loader_version=install_loader_version,
            callback=callback_options,
            java=selected_java_path,
        )

    def _build_launch_options(self, launch_options: dict[str, object] | None) -> dict[str, object]:
        if not launch_options:
            return {}

        options: dict[str, object] = {}
        jvm_arguments: list[str] = []

        memory_min = self._clean_config_text(launch_options.get("memory_min"))
        memory_max = self._clean_config_text(launch_options.get("memory_max"))
        java_path = self._clean_config_text(launch_options.get("java_path"))
        extra_jvm_args = launch_options.get("jvm_args")
        server = self._clean_config_text(launch_options.get("server"))
        port = self._clean_config_text(launch_options.get("port"))

        if memory_min:
            jvm_arguments.append(f"-Xms{memory_min}")
        if memory_max:
            jvm_arguments.append(f"-Xmx{memory_max}")
        if isinstance(extra_jvm_args, list):
            jvm_arguments.extend(str(argument) for argument in extra_jvm_args if str(argument).strip())

        if java_path:
            options["executablePath"] = java_path
            options["defaultExecutablePath"] = java_path
        if jvm_arguments:
            options["jvmArguments"] = jvm_arguments
        if server:
            options["server"] = server
        if port:
            options["port"] = port

        return options

    def _clean_config_text(self, value: object) -> str:
        return value.strip() if isinstance(value, str) else ""

    def _build_callback_options(
        self,
        progress_callback: ProgressCallback | None,
    ) -> dict[str, Callable[..., None]]:
        if progress_callback is None:
            return {}

        state = {"status": "Подготовка", "progress": 0, "max": 0}

        def set_status(status: str) -> None:
            state["status"] = status
            progress_callback(state["status"], state["progress"], state["max"])

        def set_progress(progress: int) -> None:
            state["progress"] = progress
            progress_callback(state["status"], state["progress"], state["max"])

        def set_maximum(maximum: int) -> None:
            state["max"] = maximum
            progress_callback(state["status"], state["progress"], state["max"])

        return {
            "setStatus": set_status,
            "setProgress": set_progress,
            "setMax": set_maximum,
        }

    def _read_stream(self, stream: Iterable[str] | None) -> None:
        if stream is None:
            return

        try:
            for line in stream:
                clean_line = line.rstrip()
                if clean_line:
                    self._last_log_lines.append(clean_line)
        except (OSError, ValueError):
            return

    def _detect_crash_reason(
        self,
        log_lines: Iterable[str],
        exit_code: int,
        language: str = "EN",
        source_path: Path | None = None,
    ) -> str:
        return advise_crash(log_lines, exit_code, language, source_path)

    def _collect_crash_log_source(self) -> CrashLogSource:
        crash_report = self._find_latest_crash_report()
        if crash_report is not None:
            return CrashLogSource(crash_report, self._read_log_tail(crash_report))

        latest_log = self.minecraft_directory / "logs" / "latest.log"
        if latest_log.is_file():
            return CrashLogSource(latest_log, self._read_log_tail(latest_log))

        return CrashLogSource(None, [])

    def _find_latest_crash_report(self) -> Path | None:
        crash_reports_path = self.minecraft_directory / "crash-reports"
        if not crash_reports_path.is_dir():
            return None

        reports = [path for path in crash_reports_path.glob("*.txt") if path.is_file()]
        if not reports:
            return None
        return max(reports, key=lambda path: path.stat().st_mtime)

    def _read_log_tail(self, log_path: Path, max_bytes: int = MAX_CRASH_LOG_BYTES) -> list[str]:
        try:
            file_size = log_path.stat().st_size
            with log_path.open("rb") as file:
                if file_size > max_bytes:
                    file.seek(-max_bytes, os.SEEK_END)
                data = file.read(max_bytes)
        except OSError:
            return []

        text = data.decode("utf-8", errors="replace")
        return [line.rstrip() for line in text.splitlines() if line.rstrip()][-MAX_LOG_LINES:]

    def _close_process_pipes(self, process: subprocess.Popen[str]) -> None:
        for stream in (process.stdout, process.stderr):
            if stream is not None:
                try:
                    stream.close()
                except OSError:
                    pass

    def is_game_process_running(self) -> bool:
        with self._process_lock:
            return self._current_process is not None and self._current_process.poll() is None

    def terminate_game_process(self, timeout: float = 5.0) -> None:
        with self._process_lock:
            process = self._current_process
        if process is None or process.poll() is not None:
            return

        process.terminate()
        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=timeout)

    def remove_unknown_mods(
        self,
        game_path: str | os.PathLike[str],
        unknown_mods: list[str],
    ) -> None:
        resolved_game_path = Path(game_path)
        if not unknown_mods:
            return
        if not self._is_managed_profile(resolved_game_path):
            raise RuntimeError(
                "Extra mods were not deleted because this folder is not marked as managed by MSLauncher."
            )

        for relative_path in unknown_mods:
            normalized_path = relative_path.replace("\\", "/").strip("/")
            path_parts = Path(normalized_path).parts
            if not normalized_path.startswith("mods/") or ".." in path_parts:
                raise RuntimeError(f"Unsafe extra mod path: {relative_path}")

            local_file = resolved_game_path / normalized_path
            if local_file.is_file():
                try:
                    local_file.unlink()
                except OSError as exc:
                    raise RuntimeError(f"Could not delete extra mod {normalized_path}: {exc}") from exc

    def _find_unknown_mods(
        self,
        game_path: Path,
        expected_files: dict[str, dict[str, str | int]],
    ) -> list[str]:
        mods_path = game_path / "mods"
        if not mods_path.exists():
            return []

        expected_mods = {
            path for path in expected_files if path == "mods" or path.startswith("mods/")
        }

        unknown_mods: list[str] = []
        for local_file in mods_path.rglob("*"):
            if not local_file.is_file():
                continue

            relative_path = local_file.relative_to(game_path).as_posix()
            if relative_path not in expected_mods:
                unknown_mods.append(relative_path)

        return unknown_mods

    def _is_managed_profile(self, game_path: Path) -> bool:
        return (game_path / MANAGED_MARKER).is_file()

    def _calculate_sha256(self, file_path: Path) -> str:
        digest = hashlib.sha256()

        try:
            with file_path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise RuntimeError(f"Не удалось прочитать файл {file_path}: {exc}") from exc

        return digest.hexdigest()
