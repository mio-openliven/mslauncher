from __future__ import annotations

from pathlib import Path
from urllib.parse import quote_plus

from user_error_messages import write_error_report


def build_manual_report_details(
    *,
    app_display_name: str,
    app_version: str,
    client_mode: str,
    build_id: str,
    profile_id: str,
    last_error: str,
) -> str:
    return "\n".join(
        [
            f"Manual report from {app_display_name} {app_version}.",
            f"client_mode: {client_mode}",
            f"build_id: {build_id}",
            f"profile: {profile_id}",
            f"last_error: {last_error}",
        ]
    )


def build_crash_google_url(version_text: str, loader_text: str, crash_reason: str) -> str:
    first_detail_line = ""
    for line in crash_reason.splitlines():
        stripped_line = line.strip()
        if stripped_line:
            first_detail_line = stripped_line
            break

    query_parts = [
        "Minecraft",
        version_text.strip(),
        loader_text.strip(),
        first_detail_line[:180],
    ]
    query = " ".join(part for part in query_parts if part)
    return "https://www.google.com/search?q=" + quote_plus(query)


def truncate_dialog_text(text: str, *, limit: int = 2400) -> str:
    stripped_text = text.strip()
    if len(stripped_text) <= limit:
        return stripped_text
    return stripped_text[: limit - 3].rstrip() + "..."


def write_launcher_crash_report(base_directory: Path, crash_reason: str, file_name: str) -> Path | None:
    reports_path = base_directory / "crash-reports"
    try:
        reports_path.mkdir(parents=True, exist_ok=True)
        report_path = reports_path / file_name
        report_path.write_text(crash_reason, encoding="utf-8")
        return report_path
    except OSError:
        return None


def write_launcher_error_report(
    base_directory: Path,
    *,
    user_message: str,
    technical_details: str,
    context: str,
) -> Path | None:
    try:
        return write_error_report(
            technical_details,
            user_message=user_message,
            context=context,
            base_directory=base_directory,
        )
    except OSError:
        return None


def write_launcher_warning_report(base_directory: Path, technical_details: str, context: str) -> Path | None:
    try:
        return write_error_report(
            technical_details,
            user_message="Launcher warning; no action was blocked.",
            context=context,
            base_directory=base_directory,
        )
    except OSError:
        return None


def with_report_path(message: str, report_path: Path | None, report_saved_message: str) -> str:
    if report_path is None:
        return message
    return f"{message}\n\n{report_saved_message}"
