from __future__ import annotations

import re
import subprocess
from pathlib import Path


class JavaDiagnosticError(RuntimeError):
    pass


def diagnose_launch_environment(
    minecraft_version: str,
    loader: str,
    java_path: str,
) -> None:
    normalized_loader = loader.strip().lower()
    if normalized_loader == "fabric" and not is_modern_fabric_version(minecraft_version):
        raise JavaDiagnosticError(
            "Fabric is only supported for modern Minecraft versions in this launcher. "
            "Use vanilla for older versions or add a dedicated legacy loader later."
        )

    if not java_path.strip():
        return

    installed_java = get_java_major_version(java_path)
    required_java = get_required_java_major(minecraft_version)
    if installed_java < required_java:
        raise JavaDiagnosticError(
            f"Minecraft {minecraft_version} needs Java {required_java}+; selected Java is {installed_java}."
        )


def get_java_major_version(java_path: str) -> int:
    path = Path(java_path)
    if not path.is_file():
        raise JavaDiagnosticError("Selected Java executable was not found.")

    try:
        process = subprocess.run(
            [str(path), "-version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
    except OSError as exc:
        raise JavaDiagnosticError(f"Selected Java could not be started: {exc}") from exc
    except subprocess.TimeoutExpired as exc:
        raise JavaDiagnosticError("Selected Java did not answer in time.") from exc

    output = f"{process.stdout}\n{process.stderr}"
    major_version = parse_java_major_version(output)
    if major_version is None:
        raise JavaDiagnosticError("Could not detect selected Java version.")
    return major_version


def parse_java_major_version(output: str) -> int | None:
    match = re.search(r'version\s+"(?P<version>[^"]+)"', output)
    if not match:
        return None

    version = match.group("version")
    if version.startswith("1."):
        parts = version.split(".")
        return int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else None

    major = version.split(".", 1)[0]
    return int(major) if major.isdigit() else None


def get_required_java_major(minecraft_version: str) -> int:
    version_tuple = parse_minecraft_version(minecraft_version)
    if version_tuple >= (1, 20, 5):
        return 21
    if version_tuple >= (1, 18, 0):
        return 17
    if version_tuple >= (1, 17, 0):
        return 16
    return 8


def is_modern_fabric_version(minecraft_version: str) -> bool:
    version_tuple = parse_minecraft_version(minecraft_version)
    return version_tuple >= (1, 14, 0)


def parse_minecraft_version(minecraft_version: str) -> tuple[int, int, int]:
    parts = re.findall(r"\d+", minecraft_version)
    normalized_parts = [int(part) for part in parts[:3]]
    while len(normalized_parts) < 3:
        normalized_parts.append(0)
    return tuple(normalized_parts[:3])
