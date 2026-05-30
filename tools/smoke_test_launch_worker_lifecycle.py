from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("MSLAUNCHER_USER_DATA_ROOT", str(Path(tempfile.gettempdir()) / "mslauncher-smoke"))

from PyQt6.QtCore import QCoreApplication

from gui import LaunchWorker


class MockEngine:
    def __init__(self) -> None:
        self.terminated = False

    def launch_installed(self, version, username, progress_callback, launch_options):
        detach_event = launch_options["detach_event"]
        while not detach_event.is_set() and not self.terminated:
            time.sleep(0.02)
        return None

    def terminate_game_process(self) -> None:
        self.terminated = True


def main() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])
    del app

    engine = MockEngine()
    worker = LaunchWorker(engine, "1.20.1", "Player", {})
    worker.start()
    time.sleep(0.1)
    worker.request_detach()
    assert worker.wait(2000)

    engine = MockEngine()
    worker = LaunchWorker(engine, "1.20.1", "Player", {})
    worker.start()
    time.sleep(0.1)
    worker.request_terminate_game()
    assert worker.wait(2000)
    assert engine.terminated

    print("launch worker lifecycle smoke test: OK")


if __name__ == "__main__":
    main()
