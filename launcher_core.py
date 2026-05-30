from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import threading
from collections import deque
from pathlib import Path
from typing import Callable, Iterable
from uuid import uuid4

import minecraft_launcher_lib
import minecraft_launcher_lib.mod_loader
import requests

from java_diagnostics import JavaDiagnosticError, diagnose_launch_environment
from manifest_validator import ManifestValidationError, validate_manifest


ProgressCallback = Callable[[str, int, int], None]


class MinecraftEngine:
    """Core Minecraft installer/launcher logic for MSLauncher."""

    def __init__(self, minecraft_directory: str | os.PathLike[str] | None = None) -> None:
        self.minecraft_directory = Path(
            minecraft_directory or minecraft_launcher_lib.utils.get_minecraft_directory()
        )
        self._last_log_lines: deque[str] = deque(maxlen=50)

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

    def monitor_game_process(self, process: subprocess.Popen[str]) -> str | None:
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

        exit_code = process.wait()
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)

        if exit_code == 0:
            return None

        return self._detect_crash_reason(self._last_log_lines, exit_code)

    def sync_files(
        self,
        manifest_url: str,
        game_directory: str | os.PathLike[str],
    ) -> list[dict[str, str | int]]:
        """Compare local files with a remote manifest and return files to download."""
        game_path = Path(game_directory)

        try:
            response = requests.get(manifest_url, timeout=30)
            response.raise_for_status()
            manifest = response.json()
        except requests.RequestException as exc:
            raise RuntimeError(f"Не удалось скачать манифест сборки: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Манифест сборки содержит некорректный JSON: {exc}") from exc

        try:
            manifest_files = validate_manifest(manifest)
        except ManifestValidationError as exc:
            raise RuntimeError(f"Манифест сборки поврежден: {exc}") from exc

        expected_files: dict[str, dict[str, str | int]] = {}
        files_to_download: list[dict[str, str | int]] = []

        for item in manifest_files:
            relative_path = str(item["path"])
            expected_hash = str(item.get("sha256", "")).lower()

            expected_files[relative_path] = item
            local_file = game_path / relative_path

            if not local_file.is_file() or self._calculate_sha256(local_file) != expected_hash:
                files_to_download.append(item)

        self._remove_unknown_mods(game_path, expected_files)
        return files_to_download

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

        try:
            launch_version = self._install_requested_version(version, callback_options, launch_options)

            options = {
                "username": username.strip() or "Player",
                "uuid": str(uuid4()),
                "token": "",
                "gameDirectory": str(self.minecraft_directory),
                "launcherName": "MSLauncher",
                "launcherVersion": "0.1.0",
            }
            options.update(self._build_launch_options(launch_options))

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

            return self.monitor_game_process(process)
        except Exception as exc:
            raise RuntimeError(f"Не удалось скачать или запустить Minecraft {version}: {exc}") from exc

    def _install_requested_version(
        self,
        version: str,
        callback_options: dict[str, Callable[..., None]],
        launch_options: dict[str, object] | None,
    ) -> str:
        loader = self._clean_config_text((launch_options or {}).get("loader")).lower()
        loader_version = self._clean_config_text((launch_options or {}).get("loader_version"))
        java_path = self._clean_config_text((launch_options or {}).get("java_path"))

        try:
            diagnose_launch_environment(version, loader or "vanilla", java_path)
        except JavaDiagnosticError as exc:
            raise RuntimeError(str(exc)) from exc

        if not loader or loader == "vanilla":
            minecraft_launcher_lib.install.install_minecraft_version(
                version,
                str(self.minecraft_directory),
                callback=callback_options,
            )
            return version

        if loader != "fabric":
            raise RuntimeError(f"Неподдерживаемый загрузчик модов: {loader}")

        fabric_loader = minecraft_launcher_lib.mod_loader.get_mod_loader("fabric")
        install_loader_version = None if loader_version in ("", "latest") else loader_version
        return fabric_loader.install(
            version,
            str(self.minecraft_directory),
            loader_version=install_loader_version,
            callback=callback_options,
            java=java_path or None,
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

        for line in stream:
            clean_line = line.rstrip()
            if clean_line:
                self._last_log_lines.append(clean_line)

    def _detect_crash_reason(self, log_lines: Iterable[str], exit_code: int) -> str:
        lines = list(log_lines)
        log_text = "\n".join(lines)
        lower_log = log_text.lower()

        checks = [
            (
                ("missing mandatory dependencies", "mod is missing mandatory dependencies"),
                "Forge обнаружил отсутствующую обязательную зависимость мода.",
            ),
            (
                ("requires version", "depends on", "requires any version of"),
                "Fabric сообщил об отсутствующей или несовместимой зависимости мода.",
            ),
            (
                ("modloadingexception", "failed to load mod", "loading errors encountered"),
                "Игра вылетела на этапе загрузки модов. Обычно причина в несовместимом моде или неверной версии загрузчика.",
            ),
            (
                ("noclassdeffounderror", "classnotfoundexception", "nosuchmethoderror", "nosuchfielderror"),
                "Игра вылетела из-за отсутствующего Java-класса. Чаще всего это значит, что мод несовместим с этой версией Minecraft или не хватает зависимости.",
            ),
            (
                ("mixin", "spongepowered", "mixintransformererror", "mixin apply failed", "mixin prepare failed"),
                "Игра вылетела из-за ошибки Mixin/SpongePowered. Обычно это конфликт модов или мод не подходит под выбранную версию загрузчика.",
            ),
            (
                ("incompatible mods found", "mod resolution encountered"),
                "Загрузчик нашел несовместимые моды в сборке.",
            ),
            (
                ("duplicate mods", "duplicate mod"),
                "В папке mods найдены дубликаты модов. Оставьте только одну версию каждого мода.",
            ),
            (
                ("forge", "fml", "mod file"),
                "Forge сообщил о проблеме с модами или обязательными зависимостями. Проверьте список модов и версию Forge.",
            ),
            (
                ("unsupportedclassversionerror",),
                "Игра или один из модов требует другую версию Java. Установите Java, подходящую для выбранной версии Minecraft.",
            ),
            (
                ("outofmemoryerror", "java heap space"),
                "Minecraft не хватило оперативной памяти. Увеличьте выделенную память в настройках лаунчера.",
            ),
        ]

        for needles, message in checks:
            if any(needle in lower_log for needle in needles):
                detail = self._extract_relevant_line(lines, needles)
                context = self._extract_crash_context(lines)
                return self._format_crash_message(message, detail, context)

        return (
            f"Игра завершилась с кодом {exit_code}. Точная причина не распознана, "
            "но последние строки лога сохранены для диагностики."
        )

    def _extract_relevant_line(self, log_lines: Iterable[str], needles: tuple[str, ...]) -> str:
        for line in reversed(list(log_lines)):
            lower_line = line.lower()
            if any(needle in lower_line for needle in needles):
                return line[-500:]
        return "нет отдельной строки ошибки"

    def _extract_crash_context(self, log_lines: Iterable[str]) -> dict[str, list[str]]:
        context = {
            "mods": [],
            "mod_ids": [],
            "dependencies": [],
        }

        for line in reversed(list(log_lines)):
            self._append_unique(context["mods"], self._find_mod_files(line), limit=4)
            self._append_unique(context["mod_ids"], self._find_mod_ids(line), limit=4)
            self._append_unique(context["dependencies"], self._find_dependencies(line), limit=4)

        return context

    def _find_mod_files(self, line: str) -> list[str]:
        matches = re.findall(r"[\w.+\-\[\]\(\)/\\]+\.jar", line, flags=re.IGNORECASE)
        return [Path(match.strip()).name for match in matches]

    def _find_mod_ids(self, line: str) -> list[str]:
        patterns = [
            r"mod ['\"]([a-z0-9_.-]+)['\"]",
            r"modid[:= ]+['\"]?([a-z0-9_.-]+)",
            r"for mod ([a-z0-9_.-]+)",
            r"failed to load mod ([a-z0-9_.-]+)",
        ]
        found: list[str] = []
        lower_line = line.lower()

        for pattern in patterns:
            found.extend(re.findall(pattern, lower_line, flags=re.IGNORECASE))

        return found

    def _find_dependencies(self, line: str) -> list[str]:
        patterns = [
            r"requires (?:any version of|version [^ ]+ of) ['\"]?([a-z0-9_.-]+)",
            r"depends on ['\"]?([a-z0-9_.-]+)",
            r"missing (?:mandatory )?dependencies?:?\s*([a-z0-9_.-]+)",
        ]
        found: list[str] = []
        lower_line = line.lower()

        for pattern in patterns:
            found.extend(re.findall(pattern, lower_line, flags=re.IGNORECASE))

        return found

    def _append_unique(self, target: list[str], values: Iterable[str], limit: int) -> None:
        for value in values:
            clean_value = value.strip(" '\".,;:()[]")
            if clean_value and clean_value not in target:
                target.append(clean_value)
            if len(target) >= limit:
                return

    def _format_crash_message(
        self,
        message: str,
        detail: str,
        context: dict[str, list[str]],
    ) -> str:
        parts = [message]

        if context["mods"]:
            parts.append(f"Возможный проблемный файл: {', '.join(context['mods'])}")
        if context["mod_ids"]:
            parts.append(f"Возможный mod id: {', '.join(context['mod_ids'])}")
        if context["dependencies"]:
            parts.append(f"Возможная отсутствующая зависимость: {', '.join(context['dependencies'])}")

        parts.append(f"Техническая строка: {detail}")
        return "\n\n".join(parts)

    def _remove_unknown_mods(
        self,
        game_path: Path,
        expected_files: dict[str, dict[str, str | int]],
    ) -> None:
        mods_path = game_path / "mods"
        if not mods_path.exists():
            return

        expected_mods = {
            path for path in expected_files if path == "mods" or path.startswith("mods/")
        }

        for local_file in mods_path.rglob("*"):
            if not local_file.is_file():
                continue

            relative_path = local_file.relative_to(game_path).as_posix()
            if relative_path not in expected_mods:
                try:
                    local_file.unlink()
                except OSError as exc:
                    raise RuntimeError(f"Не удалось удалить лишний мод {relative_path}: {exc}") from exc

    def _calculate_sha256(self, file_path: Path) -> str:
        digest = hashlib.sha256()

        try:
            with file_path.open("rb") as file:
                for chunk in iter(lambda: file.read(1024 * 1024), b""):
                    digest.update(chunk)
        except OSError as exc:
            raise RuntimeError(f"Не удалось прочитать файл {file_path}: {exc}") from exc

        return digest.hexdigest()
