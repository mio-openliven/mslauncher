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
from PyQt6.QtCore import QEvent
from PyQt6.QtWidgets import QApplication


def main() -> None:
    gui.MSLauncherWindow.load_versions = lambda self: self.set_status("ready")

    app = QApplication.instance() or QApplication(sys.argv)
    window = gui.MSLauncherWindow()
    original_save_preferences = window.save_user_preferences
    window.save_user_preferences = lambda: None
    try:
        assert "MSLaunch" in window.windowTitle()
        assert window.play_button.text()
        assert window.mods_button.text()
        assert not window.play_button.icon().isNull()
        assert not window.mods_button.icon().isNull()
        assert window.play_button.minimumHeight() == window.mods_button.minimumHeight()
        assert not window.progress_bar.isTextVisible()

        window.resize(960, 520)
        window.show()
        app.processEvents()
        assert window.width() >= 960
        assert window.height() >= 520
        assert window.info_panel_mode == "status"
        assert all(not row.isHidden() for row in window.status_rows)
        assert window.update_check_button.text() == "OK"
        assert window.update_poll_timer.interval() == 15_000
        assert window.update_poll_timer.isActive()
        assert window.project_switcher_expanded is False
        active_project_tab = window.project_tabs[window.client_mode]
        inactive_project_tabs = [
            tab for key, tab in window.project_tabs.items() if key != window.client_mode
        ]
        assert active_project_tab.isVisible()
        assert all(tab.isHidden() for tab in inactive_project_tabs)
        window.handle_project_tab(window.client_mode)
        assert window.project_switcher_expanded is True
        assert window.nukem_tab.isVisible()
        assert window.mslaunch_tab.isVisible()
        window.project_switcher_expanded = True
        window.eventFilter(window.project_switcher, QEvent(QEvent.Type.Leave))
        window.collapse_project_switcher()
        assert window.project_switcher_expanded is False
        assert all(tab.isHidden() for tab in inactive_project_tabs)
        window.resize(1280, 720)
        normal_size = window.size()
        window.toggle_window_size()
        assert window.width() >= normal_size.width()
        assert window.size_toggle_button.text()
        window.toggle_window_size()
        assert window.size() == normal_size
        next_version = f"{gui.APP_VERSION.rsplit('.', 1)[0]}.{int(gui.APP_VERSION.rsplit('.', 1)[1]) + 1}"
        window.on_launcher_update_loaded(
            {
                "launcher_version": next_version,
                "launcher_download_url": "https://example.com/MSLaunchSetup.exe",
                "launcher_sha256": "a" * 64,
                "launcher_notes": "Smoke update",
            }
        )
        assert window.update_check_button.text() == "!"
        assert window.info_panel_mode == "update"
        assert window.update_mascot_frame.isVisible()
        window.eventFilter(window.update_mascot_frame, QEvent(QEvent.Type.Enter))
        assert window.update_mascot_frame.isHidden()
        window.on_launcher_update_loaded({"launcher_version": gui.APP_VERSION})
        assert window.update_check_button.text() == "OK"
        window.show_success_status_card()
        assert window.info_panel_mode == "status"
        assert all(not row.isHidden() for row in window.status_rows)
        assert window.fabric_status_title.text() == window.translate("status_card_fabric")
        assert window.loader_setting_combo.currentText() in window.fabric_status_body.text()
        window.info_panel_mode = "feedback"
        window.refresh_info_panel()
        assert all(row.isHidden() for row in window.status_rows)
        assert window.open_crash_reports_button.text() == window.translate("report_bug")
        assert not window.open_crash_reports_button.icon().isNull()
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
        assert window.admin_button.isHidden()
        window.config["news"] = {
            gui.CLIENT_MODE_NUKEM: [
                {"title": "Notice one", "body": "First message"},
                {"title": "Notice two", "body": "Second message"},
            ]
        }
        window.info_panel_mode = "status"
        window.refresh_news_items()
        assert window.news_frame.isVisible()
        window.config["project_access"] = {
            "nukem": {
                "password_enabled": True,
                "password_hash_sha256": hashlib.sha256(b"secret").hexdigest(),
                "admin_password_hash_sha256": "",
            }
        }
        window.info_panel_mode = "settings"
        window.refresh_info_panel()
        assert window.news_frame.isHidden()
        assert window.admin_unlock_button.isHidden()
        errors: list[str] = []
        original_show_error = window.show_error
        window.show_error = lambda message: errors.append(str(message))
        window.show_admin_panel()
        assert window.info_panel_mode == "settings"
        assert errors and window.translate("admin_password_disabled") in errors[-1]
        window.toggle_info_panel()
        assert window.info_panel_mode == "status"
        assert window.news_frame.isVisible()
        window.show_player_panel()
        assert not window.skin_browse_button.isHidden()
        window.skin_url_input.setText("https://example.com/skin.png")
        window.save_skin_url()
        assert window.skin_path == "https://example.com/skin.png"
        assert window.loader_setting_combo.isHidden()
        window.set_update_check_state("available")
        assert window.update_check_button.text() == "!"
        window.set_update_check_state("ok")
        window.config["project_access"] = {
            "nukem": {
                "password_enabled": True,
                "password_hash_sha256": "",
                "admin_password_hash_sha256": hashlib.sha256(b"admin").hexdigest(),
            }
        }
        window.info_panel_mode = "settings"
        window.refresh_info_panel()
        assert not window.admin_unlock_button.isHidden()
        original_admin_prompt = window.request_admin_password
        window.request_admin_password = lambda: "admin"
        try:
            assert window.request_admin_access(show_panel=False)
        finally:
            window.request_admin_password = original_admin_prompt
        window.show_error = lambda message: errors.append(str(message))
        window.project_access_unlocked = False
        assert not window.ensure_project_access()
        window.config["project_access"]["nukem"]["password_hash_sha256"] = hashlib.sha256(
            b"secret"
        ).hexdigest()
        original_password_prompt = window.request_build_password
        window.request_build_password = lambda build: "admin"
        try:
            assert not window.ensure_project_access()
            assert window.info_panel_mode != "admin"
        finally:
            window.request_build_password = original_password_prompt
        window.request_build_password = lambda build: "secret"
        try:
            assert window.ensure_project_access()
        finally:
            window.request_build_password = original_password_prompt
            window.show_error = original_show_error

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
        window.save_user_preferences = original_save_preferences
        window.close()

    print("gui offscreen smoke test: OK")


if __name__ == "__main__":
    main()
