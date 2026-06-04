from __future__ import annotations

import re
from pathlib import Path

from loader_support import SUPPORTED_LOADERS, format_supported_loaders, normalize_loader

MEMORY_PATTERN = re.compile(r"^(?P<amount>[1-9][0-9]*)(?P<unit>[mMgG])$")


class LaunchSettingsError(ValueError):
    pass


def validate_launch_settings(settings: dict[str, object]) -> dict[str, object]:
    normalized_settings = dict(settings)
    normalized_settings["loader"] = validate_loader(str(settings.get("loader", "vanilla")))
    normalized_settings["memory_min"] = validate_memory(str(settings.get("memory_min", "512M")), "Min RAM")
    normalized_settings["memory_max"] = validate_memory(str(settings.get("memory_max", "2G")), "Max RAM")
    validate_memory_order(
        str(normalized_settings["memory_min"]),
        str(normalized_settings["memory_max"]),
    )

    java_path = str(settings.get("java_path", "")).strip()
    if java_path:
        normalized_settings["java_path"] = validate_java_path(java_path)
    else:
        normalized_settings["java_path"] = ""

    return normalized_settings


def validate_loader(loader: str) -> str:
    normalized_loader = normalize_loader(loader) or "vanilla"
    if normalized_loader not in SUPPORTED_LOADERS:
        raise LaunchSettingsError(f"Unsupported loader: {loader}. Use {format_supported_loaders()}.")
    return normalized_loader


def validate_memory(memory_value: str, field_name: str) -> str:
    normalized_memory = memory_value.strip()
    match = MEMORY_PATTERN.match(normalized_memory)
    if not match:
        raise LaunchSettingsError(f"{field_name} must look like 512M, 2G, or 4096M.")

    amount = int(match.group("amount"))
    unit = match.group("unit").upper()
    if unit == "M" and amount < 256:
        raise LaunchSettingsError(f"{field_name} is too low. Use at least 256M.")
    if unit == "G" and amount > 64:
        raise LaunchSettingsError(f"{field_name} is too high. Use 64G or less.")
    if unit == "M" and amount > 65536:
        raise LaunchSettingsError(f"{field_name} is too high. Use 65536M or less.")

    return f"{amount}{unit}"


def validate_memory_order(memory_min: str, memory_max: str) -> None:
    if memory_to_mb(memory_min) > memory_to_mb(memory_max):
        raise LaunchSettingsError("Min RAM cannot be greater than Max RAM.")


def validate_java_path(java_path: str) -> str:
    path = Path(java_path)
    if not path.is_file():
        raise LaunchSettingsError("Java path does not point to an existing file.")
    if path.name.lower() != "java.exe":
        raise LaunchSettingsError("Java path must point to java.exe.")
    return str(path)


def memory_to_mb(memory_value: str) -> int:
    match = MEMORY_PATTERN.match(memory_value.strip())
    if not match:
        raise LaunchSettingsError(f"Invalid memory value: {memory_value}")

    amount = int(match.group("amount"))
    unit = match.group("unit").upper()
    return amount * 1024 if unit == "G" else amount
