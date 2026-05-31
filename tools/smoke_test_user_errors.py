from __future__ import annotations

import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from user_error_messages import explain_user_error, write_error_report


def main() -> None:
    java_message = explain_user_error(
        "Minecraft 1.20.1 needs Java 17+; selected Java is 8.",
        language="EN",
        context="launch",
    )
    assert "Java" in java_message
    assert "java.exe" in java_message

    https_message = explain_user_error(
        "Build manifest_url must use https://. HTTP is not supported.",
        language="EN",
        context="build_config",
    )
    assert "HTTPS" in https_message

    hash_message = explain_user_error(
        "Failed to download mods/good.jar: Checksum mismatch for mods/good.jar",
        language="EN",
        context="download_failed",
    )
    assert "mods/good.jar" in hash_message
    assert "Existing files were kept" in hash_message

    manifest_message = explain_user_error(
        "Server build config must provide manifest_url.",
        language="EN",
        context="build_config",
    )
    assert "manifest_url" in manifest_message
    assert "source_key" in manifest_message

    ru_message = explain_user_error(
        "Server build config must provide manifest_url.",
        language="RU",
        context="build_config",
    )
    assert "manifest_url" in ru_message
    assert "source_key" in ru_message

    with tempfile.TemporaryDirectory() as temp_root:
        report_path = write_error_report(
            "Traceback line\nRuntimeError: launch failed",
            user_message="Could not launch Minecraft.",
            context="launch",
            base_directory=temp_root,
        )
        assert report_path == Path(temp_root) / "logs" / "mslauncher-last-error.txt"
        report_text = report_path.read_text(encoding="utf-8")
        assert "context: launch" in report_text
        assert "RuntimeError: launch failed" in report_text

    print("user errors smoke test: OK")


if __name__ == "__main__":
    sys.exit(main())
