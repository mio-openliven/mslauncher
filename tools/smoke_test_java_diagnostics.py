from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from java_diagnostics import (
    JavaDiagnosticError,
    diagnose_launch_environment,
    get_required_java_major,
    parse_java_major_version,
)


def expect_error(minecraft_version: str, loader: str, java_path: str) -> None:
    try:
        diagnose_launch_environment(minecraft_version, loader, java_path)
    except JavaDiagnosticError:
        return
    raise AssertionError("Expected JavaDiagnosticError")


def main() -> None:
    assert parse_java_major_version('java version "1.8.0_401"') == 8
    assert parse_java_major_version('openjdk version "17.0.10" 2024-01-16') == 17
    assert parse_java_major_version('openjdk version "21.0.2" 2024-01-16') == 21
    assert parse_java_major_version("bad output") is None

    assert get_required_java_major("1.16.5") == 8
    assert get_required_java_major("1.17.1") == 16
    assert get_required_java_major("1.18.2") == 17
    assert get_required_java_major("1.20.4") == 17
    assert get_required_java_major("1.20.5") == 21

    diagnose_launch_environment("1.20.1", "fabric", "")
    diagnose_launch_environment("1.12.2", "vanilla", "")
    expect_error("1.12.2", "fabric", "")

    print("java diagnostics smoke test: OK")


if __name__ == "__main__":
    main()
