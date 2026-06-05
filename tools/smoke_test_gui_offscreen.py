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
from PyQt6.QtCore import QEvent, QPoint
from PyQt6.QtWidgets import QApplication, QWidget


def widget_rect_in_parent(widget: QWidget, parent: QWidget) -> tuple[int, int]:
    position = widget.mapTo(parent, QPoint(0, 0))
    return position.x(), position.x() + widget.width()


def assert_horizontal_no_overlap(parent: QWidget, widgets: list[QWidget]) -> None:
    visible_widgets = [widget for widget in widgets if widget.isVisible()]
    rects = [widget_rect_in_parent(widget, parent) for widget in visible_widgets]
    for (_, previous_right), (current_left, _) in zip(rects, rects[1:]):
        assert previous_right <= current_left


def assert_layout_fixes(window: gui.MSLauncherWindow, app: QApplication) -> None:
    control_frame = window.findChild(gui.QFrame, "controlFrame")
    assert control_frame is not None

    for width, height in ((1280, 720), (1040, 560)):
        window.resize(width, height)
        window.info_panel_mode = "settings"
        window.refresh_info_panel()
        window.show()
        app.processEvents()
        assert window.info_panel.geometry().bottom() < control_frame.geometry().top()

        window.launcher_update_version = "1.9.888"
        window.launcher_update_url = "https://example.com/MSLaunchSetup.exe"
        window.info_panel_mode = "update"
        window.refresh_info_panel()
        app.processEvents()
        assert window.info_title_label.wordWrap()
        assert window.info_title_label.height() >= window.info_title_label.sizeHint().height()

        window.client_mode = gui.CLIENT_MODE_NUKEM
        window.apply_translations()
        app.processEvents()
        assert 116 <= control_frame.height() <= 120
        assert window.username_input.height() == window.build_combo.height() == window.version_combo.height() == 38
        assert window.loader_combo.height() == 38
        assert window.play_button.height() == window.mods_button.height() == 38
        control_groups = [
            group
            for group in control_frame.findChildren(gui.QFrame, "controlGroup")
            if group.isVisible()
        ]
        assert len(control_groups) >= 6
        cta_groups = {window.mods_button.parentWidget(), window.play_button.parentWidget()}
        regular_groups = [group for group in control_groups if group not in cta_groups]
        assert all(60 <= group.height() <= 64 for group in regular_groups)
        assert 104 <= window.mods_button.parentWidget().height() <= 108
        assert 104 <= window.play_button.parentWidget().height() <= 108
        separators = [
            separator
            for separator in control_frame.findChildren(gui.QFrame, "controlSeparator")
            if separator.isVisible()
        ]
        assert len(separators) == 4
        assert all(separator.height() == 46 for separator in separators)
        control_row_widgets: list[QWidget] = [
            control_groups[0],
            separators[0],
            control_groups[1],
            separators[1],
            control_groups[2],
            separators[2],
            control_groups[3],
            separators[3],
            window.mods_button.parentWidget(),
            window.play_button.parentWidget(),
        ]
        assert_horizontal_no_overlap(control_frame, control_row_widgets)
        assert window.build_combo.width() >= min(window.build_combo.sizeHint().width(), 176)
        assert window.mods_button.width() >= window.mods_button.sizeHint().width()
        assert window.play_button.width() >= window.play_button.sizeHint().width()
        assert [window.loader_combo.itemText(index) for index in range(window.loader_combo.count())] == list(
            gui.SUPPORTED_LOADERS
        )
        window.set_loader_mode("fabric")
        assert window.loader_combo.currentText() == "fabric"
        assert window.loader_setting_combo.currentText() == "fabric"
        window.set_loader_mode("vanilla")
        assert window.loader_combo.currentText() == "vanilla"
        assert window.loader_setting_combo.currentText() == "vanilla"


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
        assert window.add_username_button.toolTip() == window.translate("add_username")
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
        assert window.update_poll_timer.interval() == 10 * 60_000
        assert window.update_poll_timer.isActive()
        original_get_text = gui.QInputDialog.getText
        gui.QInputDialog.getText = lambda *args, **kwargs: ("SmokePlayer", True)
        try:
            window.add_local_username()
        finally:
            gui.QInputDialog.getText = original_get_text
        assert window.get_current_username() == "SmokePlayer"
        assert window.recent_usernames[0] == "SmokePlayer"
        assert window.config["default_username"] == "SmokePlayer"
        assert not window.add_build_button.isHidden()
        assert window.hero_frame._animation_timer.interval() == gui.ParallaxFrame.IDLE_ANIMATION_INTERVAL_MS
        if gui.MASCOT_FEATURE_ENABLED:
            assert len(window.mascot_paths) >= 1
            window.show_mascot_picker()
            assert window.mascot_picker_frame.isVisible()
            window.select_floating_mascot(0)
            assert window.mascot_picker_frame.isHidden()
            assert window.mascot_window is not None
            assert window.mascot_window.isVisible()
            window.toggle_floating_mascot()
            assert window.mascot_window.isHidden()
            window.toggle_floating_mascot()
            assert window.mascot_window is not None
            assert window.mascot_window.isVisible()
            first_mascot_index = window.mascot_window.mascot_index
            window.register_floating_mascot_click()
            window.register_floating_mascot_click()
            assert window.mascot_window.mascot_index == first_mascot_index
            window.register_floating_mascot_click()
            assert window.mascot_window.mascot_index != first_mascot_index or len(window.mascot_paths) == 1
            window.toggle_floating_mascot()
            assert window.mascot_window.isHidden()
            window.set_update_check_state("ok")
            assert not window.register_update_ok_click()
            assert not window.register_update_ok_click()
            assert window.register_update_ok_click()
            assert window.mascot_window is not None
            assert window.mascot_window.isVisible()
            assert window.mascot_window.message_label.text() == window.translate("update_mascot_ok")
        else:
            assert window.mascot_paths == []
            assert window.mascot_button.isHidden()
            assert not window.mascot_button.isEnabled()
            window.show_mascot_picker()
            assert window.mascot_picker_frame.isHidden()
            window.toggle_floating_mascot()
            assert window.mascot_window is None
            window.set_update_check_state("ok")
            assert not window.register_update_ok_click()
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
        assert window.status_label.text() == window.translate("update_status")
        assert window.progress_bar.value() == 100
        assert window.update_mascot_frame.isHidden()
        if gui.MASCOT_FEATURE_ENABLED:
            assert window.mascot_window is not None
            assert window.mascot_window.message_label.text() == window.translate("update_mascot_found")
            window.dismiss_floating_mascot_message()
            assert window.mascot_window.isHidden()
        else:
            assert window.mascot_window is None
        window.on_launcher_update_loaded({"launcher_version": gui.APP_VERSION})
        assert window.update_check_button.text() == "OK"
        assert window.progress_bar.value() == 0
        window.config["last_seen_launcher_version"] = "0.0.1"
        window.show_startup_mascot_notice_if_needed()
        if gui.MASCOT_FEATURE_ENABLED:
            assert window.config["last_seen_launcher_version"] == gui.APP_VERSION
            assert window.mascot_window is not None
            assert window.mascot_window.message_label.text() == window.translate(
                "mascot_updated", version=gui.APP_VERSION
            )
            window.dismiss_floating_mascot_message()
        else:
            assert window.config["last_seen_launcher_version"] == "0.0.1"
            assert window.mascot_window is None
        window.show_success_status_card()
        assert window.info_panel_mode == "status"
        assert window.status_summary_timer.isActive() == bool(window.news_items)
        assert all(not row.isHidden() for row in window.status_rows)
        assert window.fabric_status_title.text() == window.translate("status_card_fabric")
        assert window.loader_setting_combo.currentText() in window.fabric_status_body.text()
        if window.news_items:
            window.show_news_summary_after_status()
            assert window.info_panel_mode == "news"
            assert window.news_frame.isVisible()
            window.show_success_status_card()
            assert window.info_panel_mode == "status"
        assert {
            window.loader_combo.itemText(index) for index in range(window.loader_combo.count())
        } == set(gui.SUPPORTED_LOADERS)
        window.set_loader_mode("quilt")
        assert window.loader_setting_combo.currentText() == "quilt"
        assert window.loader_combo.currentText() == "quilt"
        window.set_loader_mode("neoforge")
        assert window.loader_setting_combo.currentText() == "neoforge"
        assert window.loader_combo.currentText() == "neoforge"
        window.social_links = {
            "youtube": "https://youtube.example",
            "discord": "https://discord.example",
            "vk_group": "https://vk.example/group",
            "website": "https://site.example",
        }
        assert window.get_visible_social_links()[2] == ("vk", "https://vk.example/group")
        window.social_links = {
            "youtube": "https://youtube.example",
            "discord": "https://discord.example",
            "rutube": "https://rutube.example/channel",
            "website": "https://site.example",
        }
        assert window.get_visible_social_links()[2] == ("rutube", "https://rutube.example/channel")
        window.social_links = {
            "youtube": "https://youtube.example",
            "vk_group": "https://vk.example/group",
        }
        assert window.get_visible_social_links()[1] == ("vk", "https://vk.example/group")
        window.show_feedback_panel()
        assert not window.status_summary_timer.isActive()
        assert all(row.isHidden() for row in window.status_rows)
        assert window.open_crash_reports_button.text() == window.translate("report_bug")
        assert not window.open_crash_reports_button.icon().isNull()
        assert "GitHub" not in window.info_body_label.text()
        assert (
            "owner panel" in window.info_body_label.text()
            or "\u043f\u0430\u043d\u0435\u043b\u044c" in window.info_body_label.text()
        )
        assert "bug" not in window.open_crash_reports_button.text().lower()
        disclosure = window.create_report_disclosure_label()
        assert window.translate("report_payload_disclosure") in disclosure.text()
        assert "technical" in disclosure.text().lower() or "\u0442\u0435\u0445\u043d\u0438\u0447" in disclosure.text().lower()
        report_dialog_calls: list[bool] = []
        original_open_report_dialog = window.open_report_dialog
        original_send_panel_report = window.send_panel_report
        original_open_crash_reports_folder = window.open_crash_reports_folder
        opened_folders: list[bool] = []
        window.open_report_dialog = lambda: report_dialog_calls.append(True)
        window.send_panel_report = lambda context, user_message="", technical_details="": sent_reports.append(
            (context, user_message, technical_details)
        ) or True
        window.open_crash_reports_folder = lambda: opened_folders.append(True)
        try:
            window.handle_panel_report_action()
            assert report_dialog_calls
            assert not opened_folders

            sent_reports: list[tuple[str, str, str]] = []
            window.send_panel_report = lambda context, user_message="", technical_details="": sent_reports.append(
                (context, user_message, technical_details)
            ) or True
            window.submit_manual_report("Player typed problem")
            assert sent_reports
            assert sent_reports[-1][0] == "manual_report"
            assert sent_reports[-1][1] == "Player typed problem"
            assert "Manual player report" in sent_reports[-1][2]
            assert window.status_label.text() == window.translate("report_sent")

            fallback_reports: list[tuple[str, str]] = []
            window.send_panel_report = lambda context, user_message="", technical_details="": False
            original_warning_report = window.write_launcher_warning_report
            window.write_launcher_warning_report = lambda details, context: fallback_reports.append(
                (details, context)
            ) or (PROJECT_ROOT / "manual_report.txt")
            window.submit_manual_report("Panel is down")
            window.write_launcher_warning_report = original_warning_report
            assert fallback_reports
            assert "Panel is down" in fallback_reports[-1][0]
            assert not opened_folders
            assert window.status_label.text() == window.translate("report_saved_local")

            sent_reports.clear()
            window.send_panel_report = lambda context, user_message="", technical_details="": sent_reports.append(
                (context, user_message, technical_details)
            ) or True
            window.last_crash_reason = "What happened: Minecraft ran out of memory.\nTechnical line: OutOfMemoryError"
            assert window.submit_crash_report("Crash details from player")
            assert sent_reports[-1][0] == "crash"
            assert sent_reports[-1][1] == "Crash details from player"
            assert "OutOfMemoryError" in sent_reports[-1][2]
        finally:
            window.open_report_dialog = original_open_report_dialog
            window.send_panel_report = original_send_panel_report
            window.open_crash_reports_folder = original_open_crash_reports_folder
        crash_dialog_calls: list[bool] = []
        original_show_crash_help_dialog = window.show_crash_help_dialog
        window.show_crash_help_dialog = lambda: crash_dialog_calls.append(True)
        try:
            window.hidden_to_tray_for_game = True
            window.on_game_crashed("What happened: Minecraft crashed\nTechnical line: OutOfMemoryError")
            app.processEvents()
            assert crash_dialog_calls
            assert not window.hidden_to_tray_for_game
            assert window.isVisible()
            assert window.info_panel_mode == "crash"
            assert window.last_crash_report_path is not None
        finally:
            window.show_crash_help_dialog = original_show_crash_help_dialog
        window.hidden_to_tray_for_game = True
        window.on_launch_failed("java.lang.UnsupportedClassVersionError")
        app.processEvents()
        assert not window.hidden_to_tray_for_game
        assert window.isVisible()
        assert window.info_panel_mode == "error"
        window.last_crash_reason = "What happened: A mod does not match the selected loader."
        window.version_combo.setCurrentText("1.20.1")
        window.set_loader_mode("neoforge")
        google_url = window.build_crash_google_url()
        assert google_url.startswith("https://www.google.com/search?q=")
        assert "neoforge" in google_url.lower()
        window.last_crash_reason = "java.lang.OutOfMemoryError: Java heap space"
        window.memory_max_input.setValue(2)
        assert window.get_crash_memory_fix_value() == "4G"
        window.memory_max_input.setValue(1)
        window.refresh_memory_hint()
        assert window.memory_hint_label.text() == window.translate("memory_hint_low")
        assert window.memory_hint_label.property("risk") == "warm"
        window.memory_max_input.setValue(4)
        window.refresh_memory_hint()
        assert window.memory_hint_label.text() == window.translate("memory_hint_good")
        assert window.memory_hint_label.property("risk") == "good"
        window.memory_max_input.setValue(8)
        window.refresh_memory_hint()
        assert window.memory_hint_label.text() == window.translate("memory_hint_warm")
        window.memory_max_input.setValue(12)
        window.refresh_memory_hint()
        assert window.memory_hint_label.text() == window.translate("memory_hint_hot")
        window.client_mode = gui.CLIENT_MODE_INDEPENDENT
        window.social_links = gui.get_social_links(window.config, window.client_mode)
        window.refresh_project_backgrounds()
        window.refresh_social_buttons()
        window.refresh_nukem_control_policy()
        assert not window.add_build_button.isHidden()
        original_get_text = gui.QInputDialog.getText
        gui.QInputDialog.getText = lambda *args, **kwargs: ("Local Test Build", True)
        try:
            window.add_local_build()
        finally:
            gui.QInputDialog.getText = original_get_text
        assert window.config["default_build"] == "local-test-build"
        assert any(build.get("id") == "local-test-build" for build in window.builds)
        assert window.get_selected_build_id() == "local-test-build"
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
        assert window.news_frame.isHidden()
        window.show_news_summary_after_status()
        assert window.news_frame.isVisible()
        window.info_panel_mode = "status"
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
        assert window.news_frame.isHidden()
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
        assert window.memory_min_input.height() <= 32
        assert window.memory_max_input.height() <= 32
        assert window.memory_min_input.width() <= 160
        assert window.memory_max_input.width() <= 160
        assert window.settings_scroll_area.verticalScrollBar().width() >= 18

        window.info_panel_mode = "feedback"
        window.refresh_info_panel()
        assert all(widget.isHidden() for widget in window.settings_widgets)

        window.launcher_update_version = "1.9.1"
        window.launcher_update_url = "https://example.com/MSLauncher.zip"
        window.info_panel_mode = "update"
        window.refresh_info_panel()
        assert not window.download_update_button.isHidden()
        assert_layout_fixes(window, app)
    finally:
        window.save_user_preferences = original_save_preferences
        window.close()

    print("gui offscreen smoke test: OK")


if __name__ == "__main__":
    main()
