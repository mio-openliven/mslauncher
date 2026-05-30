from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from launcher_core import MinecraftEngine


def run_failing_process() -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-c", "print('stdout fallback'); raise SystemExit(1)"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def main() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        game_path = Path(temp_dir)
        reports_path = game_path / "crash-reports"
        reports_path.mkdir(parents=True)
        old_report = reports_path / "crash-old.txt"
        new_report = reports_path / "crash-new.txt"
        old_report.write_text("Old NoClassDefFoundError oldmod.jar", encoding="utf-8")
        time.sleep(0.02)
        new_report.write_text("org.spongepowered.asm.mixin Mixin apply failed for mod cameramod", encoding="utf-8")

        engine = MinecraftEngine(game_path)
        message = engine.monitor_game_process(run_failing_process(), "EN")
        assert message is not None
        assert "crash-new.txt" in message
        assert "mixin" in message.lower()
        assert "cameramod" in message.lower()

    with tempfile.TemporaryDirectory() as temp_dir:
        game_path = Path(temp_dir)
        logs_path = game_path / "logs"
        logs_path.mkdir(parents=True)
        huge_prefix = "NoClassDefFoundError old-hidden.jar\n" + ("padding line\n" * 100000)
        tail_error = "java.lang.UnsupportedClassVersionError: modernmod needs newer Java\n"
        (logs_path / "latest.log").write_text(huge_prefix + tail_error, encoding="utf-8")

        engine = MinecraftEngine(game_path)
        message = engine.monitor_game_process(run_failing_process(), "EN")
        assert message is not None
        assert "latest.log" in message
        assert "java" in message.lower()
        assert "old-hidden.jar" not in message

    print("crash logs smoke test: OK")


if __name__ == "__main__":
    main()
