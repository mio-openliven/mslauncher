from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from tkinter import BOTH, LEFT, RIGHT, Tk, StringVar, ttk


APP_NAME = "MSLaunch"
INSTALL_ROOT = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "MSLaunch" / "Launcher"
USER_CONFIG_PATH = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "MSLauncher" / "launcher_config.json"
DESKTOP = Path(os.environ.get("USERPROFILE", str(Path.home()))) / "Desktop"
SHORTCUT_PATH = DESKTOP / "MSLaunch.lnk"
EXE_NAME = "MSLauncher.exe"
PACKAGE_NAME = "MSLaunch-1.9.0-beta.zip"
PACKAGE_SHA256 = "6ee7eb6217fb531c0d1c6c47f97159b2ead1598d8d51e83eb0b4f472b8f533f7"
BOOTSTRAP_MANIFESTS = [
    "https://mslaunch.186.246.12.238.sslip.io/downloads/bootstrap.json",
    "https://github.com/mio-openliven/MSNukem/releases/download/v1.9.0-beta.1/bootstrap.json",
]
PROBE_BYTES = 64 * 1024
CHUNK_SIZE = 1024 * 256

SOURCES = [
    ("Host", f"https://mslaunch.186.246.12.238.sslip.io/downloads/{PACKAGE_NAME}", PACKAGE_SHA256),
    (
        "GitHub",
        "https://github.com/mio-openliven/MSNukem/releases/download/v1.9.0-beta.1/MSLaunchPayload.dat",
        PACKAGE_SHA256,
    ),
]


class SetupUi:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("MSLaunch Setup")
        self.root.geometry("430x155")
        self.root.resizable(False, False)
        self.status = StringVar(value="Подготовка...")
        self.detail = StringVar(value="")
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill=BOTH, expand=True)
        ttk.Label(frame, text="MSLaunch", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, textvariable=self.status).pack(anchor="w", pady=(10, 4))
        self.progress = ttk.Progressbar(frame, mode="determinate", maximum=100)
        self.progress.pack(fill="x", pady=(0, 8))
        ttk.Label(frame, textvariable=self.detail, foreground="#666").pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=(10, 0))
        ttk.Button(row, text="Закрыть", command=self.root.destroy).pack(side=RIGHT)

    def set_progress(self, value: int) -> None:
        self.progress["value"] = max(0, min(100, value))

    def set_text(self, status: str, detail: str = "") -> None:
        self.status.set(status)
        self.detail.set(detail)

    def run_worker(self) -> None:
        thread = threading.Thread(target=self._worker, daemon=True)
        thread.start()
        self.root.mainloop()

    def _worker(self) -> None:
        try:
            install(self)
            self.root.after(0, self._finish_success)
        except Exception as exc:
            detail = str(exc)
            self.root.after(0, lambda: self.set_text("Не удалось установить MSLaunch.", detail))

    def _finish_success(self) -> None:
        self.set_progress(100)
        self.set_text("Готово.", "Лаунчер запускается...")
        self.root.after(1200, self.root.destroy)


def probe_source(name: str, url: str, expected_sha256: str) -> tuple[float, str, str, str]:
    started = time.perf_counter()
    request = urllib.request.Request(url, headers={"Range": f"bytes=0-{PROBE_BYTES - 1}", "User-Agent": "MSLaunchSetup/1.0"})
    with urllib.request.urlopen(request, timeout=8) as response:
        response.read(PROBE_BYTES)
    return time.perf_counter() - started, name, url, expected_sha256


def load_bootstrap_sources() -> list[tuple[str, str, str]]:
    for manifest_url in BOOTSTRAP_MANIFESTS:
        try:
            request = urllib.request.Request(manifest_url, headers={"User-Agent": "MSLaunchSetup/1.1"})
            with urllib.request.urlopen(request, timeout=8) as response:
                payload = json.loads(response.read(256 * 1024).decode("utf-8-sig"))
            sources = parse_bootstrap_manifest(payload)
            if sources:
                return sources
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return SOURCES


def parse_bootstrap_manifest(payload: object) -> list[tuple[str, str, str]]:
    if not isinstance(payload, dict):
        return []
    parsed: list[tuple[str, str, str]] = []
    raw_sources = payload.get("sources")
    if not isinstance(raw_sources, list):
        return []
    for item in raw_sources:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip()[:40] or "Source"
        url = str(item.get("url", "")).strip()
        sha256_value = str(item.get("sha256", "")).strip().lower()
        if not url.startswith("https://") or len(sha256_value) != 64:
            continue
        parsed.append((name, url, sha256_value))
    return parsed


def order_sources(sources: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    results: list[tuple[float, str, str, str]] = []
    threads: list[threading.Thread] = []
    lock = threading.Lock()

    def run_probe(source: tuple[str, str, str]) -> None:
        try:
            result = probe_source(*source)
        except Exception:
            result = (9999.0, source[0], source[1], source[2])
        with lock:
            results.append(result)

    for source in sources:
        thread = threading.Thread(target=run_probe, args=(source,), daemon=True)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join(timeout=10)

    if not results:
        return sources
    return [(name, url, expected_sha256) for _, name, url, expected_sha256 in sorted(results, key=lambda item: item[0])]


def download_package(ui: SetupUi, url: str, target: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "MSLaunchSetup/1.0"})
    with urllib.request.urlopen(request, timeout=30) as response, target.open("wb") as file:
        total = int(response.headers.get("content-length") or "0")
        downloaded = 0
        while True:
            chunk = response.read(CHUNK_SIZE)
            if not chunk:
                break
            file.write(chunk)
            downloaded += len(chunk)
            if total:
                ui.set_progress(int(downloaded * 75 / total))
                ui.set_text("Скачивание лаунчера...", f"{downloaded // 1024 // 1024} / {max(1, total // 1024 // 1024)} MB")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_package(ui: SetupUi, archive_path: Path) -> None:
    ui.set_text("Распаковка...", str(INSTALL_ROOT))
    staging = INSTALL_ROOT.with_name(INSTALL_ROOT.name + ".staging")
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as archive:
        archive.extractall(staging)
    if INSTALL_ROOT.exists():
        shutil.rmtree(INSTALL_ROOT)
    staging.replace(INSTALL_ROOT)


def create_shortcut(exe_path: Path) -> None:
    command = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:USERPROFILE + '\\Desktop\\MSLaunch.lnk');"
        f"$s.TargetPath='{exe_path}';"
        f"$s.WorkingDirectory='{exe_path.parent}';"
        "$s.IconLocation=$s.TargetPath + ',0';"
        "$s.Save()"
    )
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], check=False)


def update_user_config() -> None:
    bundled_config_path = INSTALL_ROOT / "launcher_config.json"
    if not bundled_config_path.is_file():
        return

    bundled = read_json_object(bundled_config_path)
    current = read_json_object(USER_CONFIG_PATH)
    preserve_keys = (
        "game_directory",
        "profiles_directory",
        "default_profile",
        "default_username",
        "recent_usernames",
        "skin_path",
        "launch",
    )
    merged = dict(bundled)
    for key in preserve_keys:
        if key in current:
            merged[key] = current[key]

    # Distribution-owned fields must stay fresh, otherwise old beta configs keep stale passwords.
    for key in (
        "panel",
        "builds",
        "default_build",
        "client_mode",
        "default_language",
        "project_access",
        "support_url",
        "support_urls",
        "admin_links",
        "social_links",
        "news",
    ):
        if key in bundled:
            merged[key] = bundled[key]

    USER_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if USER_CONFIG_PATH.exists():
        backup_path = USER_CONFIG_PATH.with_name(f"launcher_config.before-setup-{int(time.time())}.json")
        shutil.copyfile(USER_CONFIG_PATH, backup_path)
    USER_CONFIG_PATH.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json_object(path: Path) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def launch(exe_path: Path) -> None:
    subprocess.Popen([str(exe_path)], cwd=str(exe_path.parent), close_fds=True)


def install(ui: SetupUi) -> None:
    ui.set_text("Выбор быстрого источника...", "Проверяем хост и GitHub")
    sources = order_sources(load_bootstrap_sources())
    errors: list[str] = []
    with tempfile.TemporaryDirectory(prefix="mslaunch-setup-") as temp_dir:
        archive_path = Path(temp_dir) / PACKAGE_NAME
        for name, url, expected_sha256 in sources:
            try:
                ui.set_progress(0)
                ui.set_text("Скачивание лаунчера...", f"Источник: {name}")
                download_package(ui, url, archive_path)
                if sha256(archive_path) != expected_sha256:
                    raise RuntimeError("Проверка SHA256 не совпала.")
                extract_package(ui, archive_path)
                exe_path = INSTALL_ROOT / EXE_NAME
                if not exe_path.is_file():
                    raise RuntimeError("MSLauncher.exe не найден после распаковки.")
                ui.set_progress(92)
                ui.set_text("Обновление настроек...", str(USER_CONFIG_PATH))
                update_user_config()
                ui.set_text("Создание ярлыка...", str(SHORTCUT_PATH))
                create_shortcut(exe_path)
                launch(exe_path)
                return
            except (urllib.error.URLError, OSError, RuntimeError, zipfile.BadZipFile) as exc:
                errors.append(f"{name}: {exc}")
                archive_path.unlink(missing_ok=True)
    raise RuntimeError("; ".join(errors) or "Нет доступных источников.")


def main() -> None:
    ui = SetupUi()
    ui.run_worker()


if __name__ == "__main__":
    main()
