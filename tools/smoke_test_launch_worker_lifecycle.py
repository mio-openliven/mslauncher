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

import launcher_core
from gui import LaunchWorker
from launcher_core import MinecraftEngine


class MockEngine:
    def __init__(self) -> None:
        self.terminated = False

    def launch_installed(self, version, username, progress_callback, launch_options):
        detach_event = launch_options["detach_event"]
        game_started_callback = launch_options["game_started_callback"]
        game_started_callback()
        while not detach_event.is_set() and not self.terminated:
            time.sleep(0.02)
        return None

    def terminate_game_process(self) -> None:
        self.terminated = True


class FakeProcess:
    stdout = None
    stderr = None

    def poll(self):
        return None


def assert_engine_emits_game_started_after_process_set() -> None:
    fake_process = FakeProcess()
    engine = MinecraftEngine(Path(tempfile.gettempdir()) / "mslauncher-lifecycle-engine")
    engine._install_requested_version = lambda version, callback_options, launch_options: version
    engine.monitor_game_process = lambda process, language, detach_event: None

    original_get_command = launcher_core.minecraft_launcher_lib.command.get_minecraft_command
    original_popen = launcher_core.subprocess.Popen
    started_states: list[bool] = []
    try:
        launcher_core.minecraft_launcher_lib.command.get_minecraft_command = lambda *args, **kwargs: ["fake"]
        launcher_core.subprocess.Popen = lambda *args, **kwargs: fake_process
        engine.launch_installed(
            "1.20.1",
            "Player",
            None,
            {"game_started_callback": lambda: started_states.append(engine.is_game_process_running())},
        )
    finally:
        launcher_core.minecraft_launcher_lib.command.get_minecraft_command = original_get_command
        launcher_core.subprocess.Popen = original_popen

    assert started_states == [True]
    assert not engine.is_game_process_running()


def main() -> None:
    app = QCoreApplication.instance() or QCoreApplication([])

    assert_engine_emits_game_started_after_process_set()

    engine = MockEngine()
    worker = LaunchWorker(engine, "1.20.1", "Player", {})
    started = []
    worker.game_started.connect(lambda: started.append(True))
    worker.start()
    time.sleep(0.1)
    app.processEvents()
    assert started
    worker.request_detach()
    assert worker.wait(2000)

    engine = MockEngine()
    worker = LaunchWorker(engine, "1.20.1", "Player", {})
    worker.start()
    time.sleep(0.1)
    worker.request_terminate_game()
    assert worker.wait(2000)
    assert engine.terminated
    del app

    print("launch worker lifecycle smoke test: OK")


if __name__ == "__main__":
    main()
