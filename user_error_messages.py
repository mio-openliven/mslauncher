from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app_paths import get_user_data_root


REPORT_FILE_NAME = "mslauncher-last-error.txt"


def explain_user_error(error: object, *, language: str = "EN", context: str = "") -> str:
    technical = str(error or "").strip()
    normalized_language = language if language in ("EN", "RU") else "EN"
    lower_error = technical.lower()
    lower_context = context.lower()

    if "java" in lower_error:
        return _message(
            normalized_language,
            "Java is missing or too old for this Minecraft version. Install the required Java version or choose java.exe in launcher settings.",
            "Java не найдена или слишком старая для этой версии Minecraft. Установите нужную Java или укажите java.exe в настройках лаунчера.",
        )

    if "must use https" in lower_error or "http is not supported" in lower_error or "https://" in lower_error:
        return _message(
            normalized_language,
            "The server link is not safe. Use an HTTPS link for source_key, manifest_url, and all file URLs.",
            "Ссылка на сборку небезопасна. Используйте HTTPS для source_key, manifest_url и всех файлов сборки.",
        )

    if "manifest_url" in lower_error and (
        "must provide" in lower_error or "server profile" in lower_error or "source_key" in lower_error
    ):
        return _message(
            normalized_language,
            "Server profile cannot start yet. Add manifest_url or source_key to launcher_config.json.",
            "Серверный профиль пока нельзя запускать. Добавьте manifest_url или source_key в launcher_config.json.",
        )

    if "contains no files" in lower_error or "empty manifest" in lower_error:
        return _message(
            normalized_language,
            "Server manifest is empty. Ask the admin to regenerate manifest.json after adding mods/config/resourcepacks.",
            "Серверный manifest пустой. Попросите администратора заново сгенерировать manifest.json после добавления mods/config/resourcepacks.",
        )

    if "checksum" in lower_error or "hash mismatch" in lower_error or "sha256" in lower_error:
        file_name = _extract_file_name(technical)
        if file_name:
            return _message(
                normalized_language,
                f"Downloaded file failed integrity check: {file_name}. Existing files were kept. Try again or ask the admin to rebuild the manifest.",
                f"Файл не прошел проверку целостности: {file_name}. Старые файлы сохранены. Повторите попытку или попросите администратора пересобрать manifest.",
            )
        return _message(
            normalized_language,
            "A downloaded file failed integrity check. Existing files were kept. Try again or ask the admin to rebuild the manifest.",
            "Скачанный файл не прошел проверку целостности. Старые файлы сохранены. Повторите попытку или попросите администратора пересобрать manifest.",
        )

    if "timed out" in lower_error or "timeout" in lower_error:
        return _message(
            normalized_language,
            "Connection timed out. Check the internet connection and try again.",
            "Сервер не ответил вовремя. Проверьте интернет и повторите попытку.",
        )

    if (
        "could not load remote build config" in lower_error
        or "could not download" in lower_error
        or "failed to download" in lower_error
        or "connection" in lower_error
        or "network" in lower_error
        or "name resolution" in lower_error
    ):
        return _message(
            normalized_language,
            "Could not download launcher files. Check the internet connection and make sure the server links open in a browser.",
            "Не удалось скачать файлы лаунчера. Проверьте интернет и убедитесь, что ссылки сервера открываются в браузере.",
        )

    if "manifest" in lower_error or "build config" in lower_error or "source_key" in lower_error:
        return _message(
            normalized_language,
            "Could not read the server build config or manifest. Check source_key, manifest_url, and the generated JSON files.",
            "Не удалось прочитать конфиг сборки или manifest. Проверьте source_key, manifest_url и сгенерированные JSON-файлы.",
        )

    if "config" in lower_context or "json" in lower_error:
        return _message(
            normalized_language,
            "Launcher config is damaged or cannot be saved. A backup/report was created; check launcher_config.json.",
            "Конфиг лаунчера поврежден или не сохраняется. Backup/report создан; проверьте launcher_config.json.",
        )

    if "crash" in lower_context or "exit code" in lower_error:
        return _message(
            normalized_language,
            "Minecraft closed with an error. Open crash reports and send latest.log or the crash report to the admin.",
            "Minecraft закрылся с ошибкой. Откройте отчеты и отправьте администратору latest.log или crash report.",
        )

    return _message(
        normalized_language,
        "Something went wrong. Try again; if it repeats, send the technical report to the admin.",
        "Что-то пошло не так. Повторите попытку; если ошибка повторится, отправьте технический отчет администратору.",
    )


def write_error_report(
    technical_details: object,
    *,
    user_message: str = "",
    context: str = "",
    base_directory: str | Path | None = None,
) -> Path:
    report_root = Path(base_directory) if base_directory is not None else get_user_data_root()
    report_path = report_root / "logs" / REPORT_FILE_NAME
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        "\n".join(
            [
                f"time: {datetime.now().isoformat(timespec='seconds')}",
                f"context: {context or 'unknown'}",
                f"user_message: {user_message}",
                "",
                "technical_details:",
                str(technical_details or ""),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return report_path


def _message(language: str, english: str, russian: str) -> str:
    return russian if language == "RU" else english


def _extract_file_name(message: str) -> str:
    for marker in ("for ", "download "):
        if marker in message.lower():
            index = message.lower().find(marker)
            tail = message[index + len(marker) :].strip()
            return tail.split(":", 1)[0].strip()
    return ""
