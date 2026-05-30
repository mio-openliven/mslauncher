from __future__ import annotations

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from settings_validator import LaunchSettingsError, validate_launch_settings


def expect_error(settings: dict[str, object]) -> None:
    try:
        validate_launch_settings(settings)
    except LaunchSettingsError:
        return
    raise AssertionError(f"Expected LaunchSettingsError for {settings}")


def main() -> None:
    valid = validate_launch_settings(
        {
            "loader": "fabric",
            "memory_min": "512m",
            "memory_max": "2g",
            "java_path": "",
            "jvm_args": ["-Dexample=true"],
        }
    )
    assert valid["loader"] == "fabric"
    assert valid["memory_min"] == "512M"
    assert valid["memory_max"] == "2G"

    expect_error({"loader": "forge", "memory_min": "512M", "memory_max": "2G"})
    expect_error({"loader": "vanilla", "memory_min": "abc", "memory_max": "2G"})
    expect_error({"loader": "vanilla", "memory_min": "4G", "memory_max": "2G"})
    expect_error({"loader": "vanilla", "memory_min": "128M", "memory_max": "2G"})
    expect_error({"loader": "vanilla", "memory_min": "512M", "memory_max": "2G", "java_path": "missing.exe"})

    with tempfile.TemporaryDirectory() as temp_dir:
        java_path = Path(temp_dir) / "java.exe"
        java_path.write_text("", encoding="utf-8")
        valid_java = validate_launch_settings(
            {
                "loader": "vanilla",
                "memory_min": "512M",
                "memory_max": "2G",
                "java_path": str(java_path),
            }
        )
        assert valid_java["java_path"] == str(java_path)

    print("settings smoke test: OK")


if __name__ == "__main__":
    main()
