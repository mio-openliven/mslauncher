from __future__ import annotations

import os
import sys
from pathlib import Path
import hashlib

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import gui
from PyQt6.QtWidgets import QApplication


def main() -> None:
    gui.MSLauncherWindow.load_versions = lambda self: self.set_status("ready")

    app = QApplication.instance() or QApplication(sys.argv)
    window = gui.MSLauncherWindow()
    try:
        assert "MSLaunch" in window.windowTitle()
        assert window.play_button.text()
        assert window.mods_button.text()
        assert window.play_button.minimumHeight() == window.mods_button.minimumHeight()
        assert not window.progress_bar.isTextVisible()

        window.resize(960, 520)
        window.show()
        app.processEvents()
        assert window.width() >= 960
        assert window.height() >= 520
        assert window.info_panel_mode == "status"
        assert all(not row.isHidden() for row in window.status_rows)
        window.show_success_status_card()
        assert window.info_panel_mode == "status"
        assert all(not row.isHidden() for row in window.status_rows)
        window.info_panel_mode = "feedback"
        window.refresh_info_panel()
        assert all(row.isHidden() for row in window.status_rows)
        window.client_mode = gui.CLIENT_MODE_INDEPENDENT
        window.social_links = gui.get_social_links(window.config, window.client_mode)
        window.refresh_project_backgrounds()
        window.refresh_social_buttons()
        assert not window.social_buttons
        assert window.get_mods_action_key() == "game_folder"
        assert not window.hero_frame._slideshow_enabled

        window.config["social_links"] = {
            "nukem": {
                "youtube": "https://youtube.com/@nuckem?si=8B60TLzrzN8HVh98",
                "discord": "https://discord.com/invite/P35nvXQ",
            }
        }
        window.client_mode = gui.CLIENT_MODE_NUKEM
        window.social_links = gui.get_social_links(window.config, window.client_mode)
        window.refresh_project_backgrounds()
        window.refresh_social_buttons()
        assert len(window.social_buttons) == 2
        assert all(button.minimumSizeHint().width() > 0 for button in window.social_buttons)
        assert window.get_mods_action_key() == "download_mods"
        assert len(window.get_project_background_paths()) == 6
        assert window.hero_frame._slideshow_enabled
        window.config["project_access"] = {
            "nukem": {
                "password_enabled": True,
                "password_hash_sha256": "",
            }
        }
        window.show_error = lambda message: None
        window.project_access_unlocked = False
        assert not window.ensure_project_access()
        window.config["project_access"]["nukem"]["password_hash_sha256"] = hashlib.sha256(
            b"secret"
        ).hexdigest()
        original_password_prompt = window.request_build_password
        window.request_build_password = lambda build: "secret"
        try:
            assert window.ensure_project_access()
        finally:
            window.request_build_password = original_password_prompt

        window.info_panel_mode = "settings"
        window.refresh_info_panel()
        assert all(not widget.isHidden() for widget in window.settings_widgets)

        window.info_panel_mode = "feedback"
        window.refresh_info_panel()
        assert all(widget.isHidden() for widget in window.settings_widgets)

        window.launcher_update_version = "1.9.1"
        window.launcher_update_url = "https://example.com/MSLauncher.zip"
        window.info_panel_mode = "update"
        window.refresh_info_panel()
        assert not window.download_update_button.isHidden()
    finally:
        window.close()

    print("gui offscreen smoke test: OK")


if __name__ == "__main__":
    main()
