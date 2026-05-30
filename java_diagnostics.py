from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


class JavaDiagnosticError(RuntimeError):
    pass


def diagnose_launch_environment(
    minecraft_version: str,
    loader: str,
    java_path: str,
    *,
    java_search_roots: list[Path] | None = None,
    path_env: str | None = None,
) -> str:
    normalized_loader = loader.strip().lower()
    if normalized_loader == "fabric" and not is_modern_fabric_version(minecraft_version):
        raise JavaDiagnosticError(
            "Fabric is only supported for modern Minecraft versions in this launcher. "
            "Use vanilla for older versions or add a dedicated legacy loader later."
        )

    required_java = get_required_java_major(minecraft_version)
    cleaned_java_path = java_path.strip()

    if not cleaned_java_path:
        return find_compatible_java(
            minecraft_version,
            required_java,
            java_search_roots=java_search_roots,
            path_env=path_env,
        )

    installed_java = get_java_major_version(cleaned_java_path)
    if installed_java < required_java:
        raise JavaDiagnosticError(
            f"Minecraft {minecraft_version} needs Java {required_java}+; selected Java is {installed_java}. "
            "Choose a newer java.exe in launcher settings."
        )
    return str(Path(cleaned_java_path))


def find_compatible_java(
    minecraft_version: str,
    required_java: int,
    *,
    java_search_roots: list[Path] | None = None,
    path_env: str | None = None,
) -> str:
    best_found_version: int | None = None

    for candidate in iter_java_candidates(java_search_roots=java_search_roots, path_env=path_env):
        try:
            installed_java = get_java_major_version(str(candidate))
        except JavaDiagnosticError:
            continue

        best_found_version = max(best_found_version or 0, installed_java)
        if installed_java >= required_java:
            return str(candidate)

    if best_found_version is not None:
        raise JavaDiagnosticError(
            f"Minecraft {minecraft_version} needs Java {required_java}+; newest detected Java is {best_found_version}. "
            "Install a newer Java or set the path to java.exe in launcher settings."
        )

    raise JavaDiagnosticError(
        f"Minecraft {minecraft_version} needs Java {required_java}+. "
        "Install Java or set the path to java.exe in launcher settings."
    )


def iter_java_candidates(
    *,
    java_search_roots: list[Path] | None = None,
    path_env: str | None = None,
) -> list[Path]:
    candidates: list[Path] = []
    seen: set[str] = set()

    path_java = shutil.which("java", path=path_env)
    if path_java:
        add_candidate(candidates, seen, Path(path_java))

    for root in java_search_roots if java_search_roots is not None else get_default_java_search_roots():
        add_standard_java_candidates(candidates, seen, root)

    return candidates


def add_standard_java_candidates(candidates: list[Path], seen: set[str], root: Path) -> None:
    if not root.exists():
        return

    add_candidate(candidates, seen, root / "bin" / "java.exe")
    add_candidate(candidates, seen, root / "bin" / "java")

    for pattern in ("*/bin/java.exe", "*/bin/java", "jdk-*/bin/java.exe", "jdk-*/bin/java"):
        for candidate in sorted(root.glob(pattern), reverse=True):
            add_candidate(candidates, seen, candidate)


def add_candidate(candidates: list[Path], seen: set[str], candidate: Path) -> None:
    if not candidate.is_file():
        return

    key = str(candidate.resolve()).lower()
    if key in seen:
        return

    seen.add(key)
    candidates.append(candidate)


def get_default_java_search_roots() -> list[Path]:
    return [
        Path(r"C:\Program Files\Eclipse Adoptium"),
        Path(r"C:\Program Files\Java"),
        Path(r"C:\Program Files\Microsoft"),
        Path(r"C:\Program Files (x86)\Java"),
    ]


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
