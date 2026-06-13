from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import random
import shutil
import sys
import threading
import traceback
import time
from pathlib import Path

import requests
from PyQt6.QtCore import QEvent, QPointF, QSignalBlocker, QSize, QTimer, QThread, Qt, QUrl, pyqtSignal
from PyQt6.QtGui import QAction, QColor, QCursor, QDesktopServices, QIcon, QImage, QMovie, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QProgressBar,
    QFileDialog,
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from app_paths import (
    backup_broken_config,
    copy_default_config,
    ensure_user_config,
    get_asset_path,
    get_default_profiles_directory,
    get_last_config_backup_path,
)
from launcher_core import MinecraftEngine
from launcher_config_helpers import (
    CLIENT_MODE_INDEPENDENT,
    CLIENT_MODE_NUKEM,
    CLIENT_MODES,
    DEFAULT_NUKEM_SOCIAL_LINKS,
    SOCIAL_ICON_NAMES,
    get_admin_link,
    get_client_mode,
    get_config_builds,
    get_config_launch_options,
    get_config_string_list,
    get_config_text,
    get_profile_base_directory,
    get_social_links,
    get_support_url,
    load_launcher_config as load_launcher_config_file,
    requires_server_manifest,
    save_launcher_config,
    should_sync_profile,
)
from launcher_update import APP_DISPLAY_NAME, APP_VERSION, get_launcher_update_notice, parse_version_numbers
from manifest_validator import normalize_download_url, normalize_manifest_path
from panel_client import (
    PanelClientError,
    allow_insecure_panel_http,
    get_panel_launcher_update,
    post_panel_report,
    request_panel_build_access,
    resolve_panel_active_build,
)
from profile_manager import LauncherProfile, LauncherProfileManager, PROFILE_IDS, PROFILE_SERVER
from remote_config import resolve_build_config
from settings_validator import LaunchSettingsError, validate_launch_settings
from url_policy import URLPolicyError, normalize_https_url
from user_error_messages import explain_user_error, write_error_report
from gui_report_dialogs import prompt_report_message
from gui_reporting import (
    build_crash_google_url,
    build_manual_report_details,
    truncate_dialog_text,
    with_report_path,
    write_launcher_crash_report,
    write_launcher_error_report,
    write_launcher_warning_report,
)


CONFIG_FILE = ensure_user_config()
CONFIG_LOAD_WARNING = ""
CHUNK_SIZE = 1024 * 1024
DOWNLOAD_RETRIES = 3
REQUEST_TIMEOUT = 60
BACKGROUND_DIR = get_asset_path("backgrounds")
ICON_DIR = get_asset_path("icons")
PROJECT_ICON_DIR = get_asset_path("project_icons")
MASCOT_DIR = get_asset_path("mascots")
APP_ICON_PATH = get_asset_path("app_icon.ico")
UPDATE_MASCOT_PATH = get_asset_path("shigure-ui-dance.gif")
MASCOT_FEATURE_ENABLED = False
BACKGROUND_FILES = (
    "bg_01.jpg",
    "bg_02.jpg",
    "bg_03.jpg",
    "bg_04.jpg",
    "bg_05.jpg",
    "bg_06.jpg",
)
NUKEM_BACKGROUND_DIR = BACKGROUND_DIR / "nukem"
NUKEM_BACKGROUND_FILES = (
    "nukem_01_winter.jpg",
    "nukem_02_island.jpg",
    "nukem_03_city.jpg",
    "nukem_04_road.jpg",
    "nukem_05_river.jpg",
    "nukem_06_village.jpg",
)
PROJECT_ICON_FILES = {
    CLIENT_MODE_INDEPENDENT: "mslaunch.png",
    CLIENT_MODE_NUKEM: "nukem.png",
    "vibecraft": "vibecraft.png",
}
MASCOT_FILES = (
    "shigure_original_wide.gif",
    "shigure_dance_tall.gif",
    "shigure_vtuber.gif",
    "shigure_ui_jp.gif",
    "shigure_anime.gif",
)
SOCIAL_FALLBACK_LABELS = {
    "discord": "DS",
    "telegram": "TG",
    "youtube": "YT",
    "instagram": "IN",
    "tiktok": "TT",
    "vk": "VK",
    "vk_group": "VK",
    "rutube": "RT",
    "website": "WB",
    "link": "WB",
}
ACTION_ICON_FILES = {
    "play": "play.svg",
    "download_mods": "download.svg",
    "game_folder": "folder.svg",
    "report_bug": "report.svg",
    "open_error_report": "report.svg",
}
SYSTEM_DIALOG_STYLESHEET = """
QMessageBox,
QInputDialog,
QDialog#accessDialog {
    background: #f5f5f5;
}
QMessageBox QLabel,
QInputDialog QLabel,
QDialog#accessDialog QLabel {
    color: #151515;
    font-family: "Segoe UI", "Arial";
    font-size: 12px;
}
QMessageBox QPushButton,
QInputDialog QPushButton,
QDialog#accessDialog QPushButton {
    color: #151515;
    min-width: 72px;
    min-height: 24px;
}
QInputDialog QLineEdit,
QDialog#accessDialog QLineEdit,
QDialog#accessDialog QPlainTextEdit {
    color: #151515;
    background: #ffffff;
    border: 1px solid #7a7a7a;
    padding: 4px 6px;
}
QDialog#accessDialog {
    background: #071016;
}
QDialog#accessDialog QLabel {
    color: #eef8ff;
}
QDialog#accessDialog QPlainTextEdit {
    color: #ffffff;
    background: #03090d;
    border: 1px solid rgba(93, 202, 235, 130);
    border-radius: 8px;
    padding: 8px;
}
QDialog#accessDialog QPushButton {
    color: #ffffff;
    background: rgba(255, 255, 255, 18);
    border: 1px solid rgba(255, 255, 255, 44);
    border-radius: 8px;
    padding: 6px 12px;
}
QDialog#accessDialog QPushButton#primaryDialogButton {
    background: rgba(93, 202, 235, 34);
    border: 1px solid rgba(93, 202, 235, 150);
}
"""

TRANSLATIONS = {
    "EN": {
        "app_title": APP_DISPLAY_NAME,
        "brand_title": APP_DISPLAY_NAME,
        "brand_credit": f"Beta {APP_VERSION}",
        "brand_credit_nukem": f"Beta {APP_VERSION}",
        "brand_subtitle_project": "Project entry point",
        "brand_subtitle_crew": "Built for the crew",
        "brand_subtitle_places": "Everything in its place",
        "brand_subtitle_session": "A clean start for the session",
        "brand_subtitle_independent": "Profiles, mods and launch in one place",
        "brand_subtitle_nukem": "Nukem mods under control",
        "settings_title": "Launcher Panel",
        "settings_body": "Sync status, Java checks and crash reports will appear here.",
        "admin_panel_title": "Nukem admin",
        "admin_panel_body": "Customer panel: news, builds, passwords and reports. GitHub remains the fallback until the server database is connected.",
        "admin_password_title": "Admin password",
        "admin_password_body": "Enter admin password for this launcher.",
        "admin_password_open": "Open admin",
        "admin_password_disabled": "Admin access is not configured in this launcher.",
        "admin_create_news": "Create news",
        "admin_view_builds": "Builds",
        "admin_change_password": "Passwords",
        "open_modpack_repo": "Open modpack repo",
        "open_modpack_manifest": "Open manifest",
        "open_support_queue": "Open support queue",
        "open_profile": "Open profile folder",
        "open_game": "Open profiles root",
        "open_crash_reports": "Open crash reports",
        "open_error_report": "Open logs",
        "crash_panel_title": "Minecraft crashed",
        "crash_help_title": "Minecraft crashed",
        "crash_help_body": "MSLaunch found a likely cause. You can send it to the owner or inspect the exact error.",
        "crash_action_ok": "OK",
        "crash_action_report": "Report",
        "crash_action_self_help": "Fix myself",
        "crash_action_google": "Ask Google",
        "crash_self_help_title": "Crash details",
        "crash_google_failed": "Could not open browser search.",
        "error_panel_title": "Last launcher error",
        "loader": "Loader",
        "memory_min": "Min RAM",
        "memory_max": "Max RAM",
        "memory_hint_good": "Perfect for your PC!",
        "memory_hint_warm": "High allocation. Close heavy apps before launch.",
        "memory_hint_hot": "Risky allocation. This can starve the system.",
        "java_path": "Java path",
        "java_browse": "Browse",
        "skin": "Skin",
        "skin_browse": "Choose PNG",
        "skin_invalid": "Choose a PNG skin file.",
        "skin_saved": "Skin file saved. Server support depends on server plugins.",
        "skin_empty": "No skin file selected.",
        "skin_url": "Skin URL",
        "skin_url_apply": "Save URL",
        "skin_url_invalid": "Paste HTTPS skin URL.",
        "open_player_panel": "Player",
        "player_panel_title": "Player profile",
        "player_panel_body": "Skin and player settings. The nickname field keeps the last five names in its list.",
        "skin_button_tooltip": "Player skin",
        "language": "Language",
        "project_switcher_tooltip": "Switch launcher",
        "mode_independent": "Independent mode",
        "mode_nukem": "Nukem mode",
        "profile": "Mods",
        "profile_server": "Server",
        "profile_personal": "Personal",
        "profile_other": "Other",
        "build": "Build",
        "build_source_nukem": "NK Team",
        "build_source_local": "My builds",
        "add_build": "Add local build",
        "add_build_prompt": "Enter a local build name.",
        "build_saved": "Local build saved.",
        "username": "Nick",
        "add_username": "Add nickname",
        "add_username_prompt": "Enter a nickname to save locally.",
        "username_saved": "Nickname saved.",
        "version": "Version",
        "play": "Play",
        "mods": "Mods",
        "play_idle": "Play",
        "mods_idle": "Mods",
        "game_folder": "Game Folder",
        "download_mods": "Download Mods",
        "feedback_ok": "Everything OK?",
        "feedback_problem": "Click if there is a problem",
        "feedback_card_title": "Problems?",
        "feedback_card_body": "Report a problem or open logs if something does not launch cleanly.",
        "report_bug": "Report a problem",
        "support_offline": "Could not open the report page. Opening local reports instead.",
        "report_sent": "Report sent.",
        "report_send_failed": "Could not send the report. Opening local reports instead.",
        "feedback_panel_title": "Need help?",
        "feedback_panel_body": "Send a problem, critique, or wish for this project. If the panel is unavailable, the launcher opens local reports instead.",
        "report_dialog_title": "Report a problem",
        "report_dialog_body": "Write what happened, what you dislike, or what you want changed.",
        "report_dialog_placeholder": "Example: the launcher is confusing here, the button does not work, or I want...",
        "report_dialog_send": "Send",
        "report_dialog_cancel": "Cancel",
        "report_empty": "Write a comment before sending.",
        "report_saved_local": "Report saved locally.",
        "news_title": "News",
        "news_empty": "No news yet.",
        "status_card_mods": "Mods ready",
        "status_card_mods_body": "Files checked successfully.",
        "status_card_fabric": "Loader OK",
        "status_card_loader_body": "Loader {loader}",
        "status_card_java": "Java OK",
        "runtime_auto": "Runtime auto",
        "update_available": "Launcher update available: {version}",
        "update_mascot_found": "Found an update!",
        "update_mascot_ok": "All good!",
        "mascot_welcome": "Hi! Launcher is ready.",
        "mascot_updated": "Updated to {version}!",
        "manual_update_tooltip": "Check updates",
        "manual_update_checking": "Checking launcher updates...",
        "manual_update_ok": "Launcher is up to date.",
        "manual_update_failed": "Could not check launcher updates: {error}",
        "download_update": "Download update",
        "update_panel_body": "Manual update only. Download the new package and replace launcher files after closing the game.",
        "status_mods_ready": "Mod files are ready.",
        "status_mods_no_sync": "This profile does not use server mod sync.",
        "update_disabled": "No launcher update notice.",
        "access_password_title": "Build access",
        "access_password_body": "Enter the code for {build}. It unlocks mods for this build only. The admin will also give you the right server and exact game version so you can join without guesswork.",
        "access_password_prompt": "Build password",
        "access_password_download": "Download mods",
        "access_password_failed": "Wrong build password. Ask the Nukem admin for the current code.",
        "access_password_missing": "Build password is not configured. Ask the admin to add a password for this build.",
        "access_granted": "Project access granted.",
        "admin_access_granted": "Admin panel unlocked.",
        "action_motor": "Rolling!",
        "action_go": "Action!",
        "action_scene": "Scene up!",
        "action_cut": "Cut!",
        "action_awake": "Stay sharp!",
        "loading_versions": "Loading versions...",
        "ready": "Ready",
        "status_syncing": "Checking modpack files...",
        "status_loading_build": "Loading build config...",
        "status_skipping_sync": "Launching without server sync...",
        "status_no_downloads": "All files are up to date.",
        "status_downloading": "Downloading files...",
        "status_downloading_file": "Downloading: {file}",
        "status_download_complete": "Files downloaded.",
        "status_launching": "Launching Minecraft...",
        "status_game_installing": "Preparing Minecraft files...",
        "status_game_running": "Minecraft is running.",
        "status_game_closed": "Minecraft closed.",
        "error": "Error",
        "empty_username": "Enter a nickname.",
        "empty_version": "Select a Minecraft version.",
        "empty_build": "Select a build.",
        "empty_manifest": "Set manifest_url or source_key for the selected build in launcher_config.json.",
        "server_manifest_required": "Server profile needs a manifest_url or source_key before launch.",
        "versions_failed": "Could not load Minecraft versions: {error}",
        "sync_failed": "Could not sync files: {error}",
        "build_config_failed": "Could not load build config: {error}",
        "download_failed": "Could not download files: {error}",
        "launch_failed": "Could not launch Minecraft: {error}",
        "settings_failed": "Check launcher settings: {error}",
        "config_repaired": "Config was damaged. Backup saved here: {path}. Default settings were loaded.",
        "config_save_failed": "Could not save launcher settings: {error}",
        "close_game_prompt": "Minecraft is still running. What should MSLaunch do?",
        "leave_game_running": "Leave game running",
        "close_game": "Close game",
        "cancel_close": "Cancel",
        "launch_report_saved": "Technical report saved here: {path}",
        "error_report_saved": "Technical report saved here: {path}",
        "hash_failed": "Downloaded file checksum mismatch: {file}",
        "crash_title": "Minecraft crashed",
    },
    "RU": {
        "app_title": APP_DISPLAY_NAME,
        "brand_title": APP_DISPLAY_NAME,
        "brand_credit": f"Beta {APP_VERSION}",
        "brand_credit_nukem": f"Beta {APP_VERSION}",
        "brand_subtitle_project": "\u0422\u043e\u0447\u043a\u0430 \u0432\u0445\u043e\u0434\u0430 \u0432 \u043f\u0440\u043e\u0435\u043a\u0442",
        "brand_subtitle_crew": "\u0421\u043e\u0431\u0440\u0430\u043d\u043e \u0434\u043b\u044f \u0441\u0432\u043e\u0435\u0439 \u043a\u043e\u043c\u0430\u043d\u0434\u044b",
        "brand_subtitle_places": "\u0412\u0441\u0435 \u043d\u0430 \u0441\u0432\u043e\u0438\u0445 \u043c\u0435\u0441\u0442\u0430\u0445",
        "brand_subtitle_session": "\u0427\u0438\u0441\u0442\u044b\u0439 \u0441\u0442\u0430\u0440\u0442 \u0434\u043b\u044f \u0441\u0435\u0441\u0441\u0438\u0438",
        "brand_subtitle_independent": "\u041f\u0440\u043e\u0444\u0438\u043b\u0438, \u043c\u043e\u0434\u044b \u0438 \u0437\u0430\u043f\u0443\u0441\u043a \u0432 \u043e\u0434\u043d\u043e\u043c \u043c\u0435\u0441\u0442\u0435",
        "brand_subtitle_nukem": "\u041c\u043e\u0434\u044b Nukem \u043f\u043e\u0434 \u043a\u043e\u043d\u0442\u0440\u043e\u043b\u0435\u043c",
        "settings_title": "\u041f\u0430\u043d\u0435\u043b\u044c \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430",
        "settings_body": "\u0417\u0434\u0435\u0441\u044c \u0431\u0443\u0434\u0443\u0442 \u0441\u0442\u0430\u0442\u0443\u0441 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438, \u043f\u0440\u043e\u0432\u0435\u0440\u043a\u0438 Java \u0438 \u043e\u0442\u0447\u0435\u0442\u044b \u043e\u0448\u0438\u0431\u043e\u043a.",
        "admin_panel_title": "\u0410\u0434\u043c\u0438\u043d Nukem",
        "admin_panel_body": "\u041f\u0430\u043d\u0435\u043b\u044c \u0437\u0430\u043a\u0430\u0437\u0447\u0438\u043a\u0430: \u043d\u043e\u0432\u043e\u0441\u0442\u0438, \u0441\u0431\u043e\u0440\u043a\u0438, \u043f\u0430\u0440\u043e\u043b\u0438 \u0438 \u043e\u0442\u0447\u0435\u0442\u044b. GitHub \u043e\u0441\u0442\u0430\u0435\u0442\u0441\u044f \u0437\u0430\u043f\u0430\u0441\u043d\u044b\u043c \u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u043c \u0434\u043e \u043f\u043e\u0434\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f \u0431\u0430\u0437\u044b.",
        "admin_password_title": "\u041f\u0430\u0440\u043e\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0430",
        "admin_password_body": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043f\u0430\u0440\u043e\u043b\u044c \u0430\u0434\u043c\u0438\u043d\u0430 \u044d\u0442\u043e\u0433\u043e \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430.",
        "admin_password_open": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u0430\u0434\u043c\u0438\u043d\u043a\u0443",
        "admin_password_disabled": "\u0410\u0434\u043c\u0438\u043d-\u0432\u0445\u043e\u0434 \u0432 \u044d\u0442\u043e\u043c \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0435 \u043d\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0435\u043d.",
        "admin_create_news": "\u0421\u043e\u0437\u0434\u0430\u0442\u044c \u043d\u043e\u0432\u043e\u0441\u0442\u044c",
        "admin_view_builds": "\u0421\u0431\u043e\u0440\u043a\u0438",
        "admin_change_password": "\u041f\u0430\u0440\u043e\u043b\u0438",
        "open_modpack_repo": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c repo \u0441\u0431\u043e\u0440\u043a\u0438",
        "open_modpack_manifest": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c manifest",
        "open_support_queue": "\u041e\u0447\u0435\u0440\u0435\u0434\u044c report",
        "open_profile": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u0430\u043f\u043a\u0443 \u043f\u0440\u043e\u0444\u0438\u043b\u044f",
        "open_game": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043a\u043e\u0440\u0435\u043d\u044c \u043f\u0440\u043e\u0444\u0438\u043b\u0435\u0439",
        "open_crash_reports": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c crash-reports",
        "open_error_report": "\u041e\u0442\u043a\u0440\u044b\u0442\u044c \u043e\u0442\u0447\u0435\u0442\u044b",
        "crash_panel_title": "Minecraft \u0432\u044b\u043b\u0435\u0442\u0435\u043b",
        "crash_help_title": "Minecraft \u0432\u044b\u043b\u0435\u0442\u0435\u043b",
        "crash_help_body": "MSLaunch \u043d\u0430\u0448\u0451\u043b \u0432\u0435\u0440\u043e\u044f\u0442\u043d\u0443\u044e \u043f\u0440\u0438\u0447\u0438\u043d\u0443. \u041c\u043e\u0436\u043d\u043e \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u0435\u0451 \u0432\u043b\u0430\u0434\u0435\u043b\u044c\u0446\u0443 \u0438\u043b\u0438 \u043f\u043e\u0441\u043c\u043e\u0442\u0440\u0435\u0442\u044c \u0442\u043e\u0447\u043d\u0443\u044e \u043e\u0448\u0438\u0431\u043a\u0443.",
        "crash_action_ok": "OK",
        "crash_action_report": "\u0421\u043e\u043e\u0431\u0449\u0438\u0442\u044c",
        "crash_action_self_help": "\u0425\u043e\u0447\u0443 \u0441\u0430\u043c",
        "crash_action_google": "\u0421\u043f\u0440\u043e\u0441\u0438\u0442\u044c Google",
        "crash_self_help_title": "\u041f\u043e\u0434\u0440\u043e\u0431\u043d\u043e\u0441\u0442\u0438 \u0432\u044b\u043b\u0435\u0442\u0430",
        "crash_google_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u043f\u043e\u0438\u0441\u043a \u0432 \u0431\u0440\u0430\u0443\u0437\u0435\u0440\u0435.",
        "error_panel_title": "\u041f\u043e\u0441\u043b\u0435\u0434\u043d\u044f\u044f \u043e\u0448\u0438\u0431\u043a\u0430 \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430",
        "loader": "\u0417\u0430\u0433\u0440\u0443\u0437\u0447\u0438\u043a",
        "memory_min": "\u041c\u0438\u043d. RAM",
        "memory_max": "\u041c\u0430\u043a\u0441. RAM",
        "memory_hint_good": "\u0418\u0434\u0435\u0430\u043b\u044c\u043d\u043e \u0434\u043b\u044f \u0442\u0432\u043e\u0435\u0433\u043e \u041f\u041a!",
        "memory_hint_warm": "\u0412\u044b\u0441\u043e\u043a\u043e\u0435 \u0432\u044b\u0434\u0435\u043b\u0435\u043d\u0438\u0435. \u0417\u0430\u043a\u0440\u043e\u0439\u0442\u0435 \u0442\u044f\u0436\u0451\u043b\u044b\u0435 \u043f\u0440\u0438\u043b\u043e\u0436\u0435\u043d\u0438\u044f \u043f\u0435\u0440\u0435\u0434 \u0437\u0430\u043f\u0443\u0441\u043a\u043e\u043c.",
        "memory_hint_hot": "\u0420\u0438\u0441\u043a\u043e\u0432\u0430\u043d\u043d\u043e\u0435 \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435. \u0421\u0438\u0441\u0442\u0435\u043c\u0435 \u043c\u043e\u0436\u0435\u0442 \u043d\u0435 \u0445\u0432\u0430\u0442\u0438\u0442\u044c RAM.",
        "java_path": "\u041f\u0443\u0442\u044c Java",
        "java_browse": "\u041e\u0431\u0437\u043e\u0440",
        "skin": "Skin",
        "skin_browse": "\u0412\u044b\u0431\u0440\u0430\u0442\u044c PNG",
        "skin_invalid": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 PNG-\u0444\u0430\u0439\u043b \u0441\u043a\u0438\u043d\u0430.",
        "skin_saved": "\u0424\u0430\u0439\u043b \u0441\u043a\u0438\u043d\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d. \u041f\u043e\u0434\u0434\u0435\u0440\u0436\u043a\u0430 \u043d\u0430 \u0441\u0435\u0440\u0432\u0435\u0440\u0435 \u0437\u0430\u0432\u0438\u0441\u0438\u0442 \u043e\u0442 server plugins.",
        "skin_empty": "\u0424\u0430\u0439\u043b \u0441\u043a\u0438\u043d\u0430 \u043d\u0435 \u0432\u044b\u0431\u0440\u0430\u043d.",
        "skin_url": "\u0421\u0441\u044b\u043b\u043a\u0430 \u043d\u0430 \u0441\u043a\u0438\u043d",
        "skin_url_apply": "\u0421\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c URL",
        "skin_url_invalid": "\u0412\u0441\u0442\u0430\u0432\u044c\u0442\u0435 HTTPS-\u0441\u0441\u044b\u043b\u043a\u0443 \u043d\u0430 \u0441\u043a\u0438\u043d.",
        "open_player_panel": "\u041f\u0440\u043e\u0444\u0438\u043b\u044c",
        "player_panel_title": "\u041f\u0440\u043e\u0444\u0438\u043b\u044c \u0438\u0433\u0440\u043e\u043a\u0430",
        "player_panel_body": "\u0421\u043a\u0438\u043d \u0438 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u0438\u0433\u0440\u043e\u043a\u0430. \u041d\u0438\u043a \u0432\u044b\u0431\u0438\u0440\u0430\u0435\u0442\u0441\u044f \u0441\u043d\u0438\u0437\u0443, \u043f\u043e\u0441\u043b\u0435\u0434\u043d\u0438\u0435 \u043d\u0438\u043a\u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b \u0432 \u0441\u043f\u0438\u0441\u043a\u0435.",
        "skin_button_tooltip": "\u0421\u043a\u0438\u043d \u0438\u0433\u0440\u043e\u043a\u0430",
        "language": "\u042f\u0437\u044b\u043a",
        "project_switcher_tooltip": "\u0421\u043c\u0435\u043d\u0438\u0442\u044c \u043b\u0430\u0443\u043d\u0447\u0435\u0440",
        "mode_independent": "\u041d\u0435\u0437\u0430\u0432\u0438\u0441\u0438\u043c\u044b\u0439 \u0440\u0435\u0436\u0438\u043c",
        "mode_nukem": "Nukem mode",
        "profile": "\u041c\u043e\u0434\u044b",
        "profile_server": "\u0421\u0435\u0440\u0432\u0435\u0440",
        "profile_personal": "\u041b\u0438\u0447\u043d\u044b\u0435",
        "profile_other": "\u0414\u0440\u0443\u0433\u043e\u0435",
        "build": "\u0421\u0431\u043e\u0440\u043a\u0430",
        "build_source_nukem": "NK Team",
        "build_source_local": "\u041c\u043e\u0438 \u0441\u0431\u043e\u0440\u043a\u0438",
        "add_build": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0443\u044e \u0441\u0431\u043e\u0440\u043a\u0443",
        "add_build_prompt": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u0438\u043c\u044f \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e\u0439 \u0441\u0431\u043e\u0440\u043a\u0438.",
        "build_saved": "\u041b\u043e\u043a\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u0431\u043e\u0440\u043a\u0430 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d\u0430.",
        "username": "\u041d\u0438\u043a",
        "add_username": "\u0414\u043e\u0431\u0430\u0432\u0438\u0442\u044c \u043d\u0438\u043a",
        "add_username_prompt": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u0438\u043a, \u0447\u0442\u043e\u0431\u044b \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u0435\u0433\u043e \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e.",
        "username_saved": "\u041d\u0438\u043a \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d.",
        "version": "\u0412\u0435\u0440\u0441\u0438\u044f",
        "play": "\u0418\u0433\u0440\u0430\u0442\u044c",
        "mods": "\u041c\u043e\u0434\u044b",
        "play_idle": "\u0418\u0433\u0440\u0430\u0442\u044c",
        "mods_idle": "\u041c\u043e\u0434\u044b",
        "game_folder": "\u041f\u0430\u043f\u043a\u0430 \u0438\u0433\u0440\u044b",
        "download_mods": "\u0421\u043a\u0430\u0447\u0430\u0442\u044c \u043c\u043e\u0434\u044b",
        "feedback_ok": "\u0412\u0441\u0435 \u043e\u043a?",
        "feedback_problem": "\u041d\u0430\u0436\u043c\u0438, \u0435\u0441\u043b\u0438 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0430",
        "feedback_card_title": "\u041f\u0440\u043e\u0431\u043b\u0435\u043c\u044b?",
        "feedback_card_body": "\u0421\u043e\u043e\u0431\u0449\u0438\u0442\u0435 \u043e \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0435 \u0438\u043b\u0438 \u043e\u0442\u043a\u0440\u043e\u0439\u0442\u0435 \u043e\u0442\u0447\u0435\u0442\u044b, \u0435\u0441\u043b\u0438 \u0447\u0442\u043e-\u0442\u043e \u043d\u0435 \u0437\u0430\u043f\u0443\u0441\u043a\u0430\u0435\u0442\u0441\u044f.",
        "report_bug": "\u0421\u043e\u043e\u0431\u0449\u0438\u0442\u044c \u043e \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0435",
        "support_offline": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043a\u0440\u044b\u0442\u044c \u0431\u0430\u0433-\u0440\u0435\u043f\u043e\u0440\u0442. \u041e\u0442\u043a\u0440\u044b\u0432\u0430\u044e \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u043e\u0442\u0447\u0435\u0442\u044b.",
        "report_sent": "\u041e\u0442\u0447\u0451\u0442 \u043e\u0442\u043f\u0440\u0430\u0432\u043b\u0435\u043d.",
        "report_send_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c \u043e\u0442\u0447\u0451\u0442. \u041e\u0442\u043a\u0440\u044b\u0432\u0430\u044e \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u043e\u0442\u0447\u0451\u0442\u044b.",
        "feedback_panel_title": "\u041d\u0443\u0436\u043d\u0430 \u043f\u043e\u043c\u043e\u0449\u044c?",
        "feedback_panel_body": "\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u0435 \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0443, \u043a\u0440\u0438\u0442\u0438\u043a\u0443 \u0438\u043b\u0438 \u043f\u043e\u0436\u0435\u043b\u0430\u043d\u0438\u0435 \u043f\u043e \u044d\u0442\u043e\u043c\u0443 \u043f\u0440\u043e\u0435\u043a\u0442\u0443. \u0415\u0441\u043b\u0438 \u043f\u0430\u043d\u0435\u043b\u044c \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u043d\u0430, \u043b\u0430\u0443\u043d\u0447\u0435\u0440 \u043e\u0442\u043a\u0440\u043e\u0435\u0442 \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u044b\u0435 \u043e\u0442\u0447\u0435\u0442\u044b.",
        "report_dialog_title": "\u0421\u043e\u043e\u0431\u0449\u0438\u0442\u044c \u043e \u043f\u0440\u043e\u0431\u043b\u0435\u043c\u0435",
        "report_dialog_body": "\u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435, \u0447\u0442\u043e \u0441\u043b\u0443\u0447\u0438\u043b\u043e\u0441\u044c, \u0447\u0442\u043e \u043d\u0435 \u043d\u0440\u0430\u0432\u0438\u0442\u0441\u044f \u0438\u043b\u0438 \u0447\u0442\u043e \u0445\u043e\u0442\u0438\u0442\u0435 \u0438\u0437\u043c\u0435\u043d\u0438\u0442\u044c.",
        "report_dialog_placeholder": "\u041d\u0430\u043f\u0440\u0438\u043c\u0435\u0440: \u0442\u0443\u0442 \u043d\u0435\u043f\u043e\u043d\u044f\u0442\u043d\u043e, \u043a\u043d\u043e\u043f\u043a\u0430 \u043d\u0435 \u0440\u0430\u0431\u043e\u0442\u0430\u0435\u0442 \u0438\u043b\u0438 \u0445\u043e\u0447\u0443...",
        "report_dialog_send": "\u041e\u0442\u043f\u0440\u0430\u0432\u0438\u0442\u044c",
        "report_dialog_cancel": "\u041e\u0442\u043c\u0435\u043d\u0430",
        "report_empty": "\u041d\u0430\u043f\u0438\u0448\u0438\u0442\u0435 \u043a\u043e\u043c\u043c\u0435\u043d\u0442\u0430\u0440\u0438\u0439 \u043f\u0435\u0440\u0435\u0434 \u043e\u0442\u043f\u0440\u0430\u0432\u043a\u043e\u0439.",
        "report_saved_local": "\u041e\u0442\u0447\u0451\u0442 \u0441\u043e\u0445\u0440\u0430\u043d\u0451\u043d \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u043e.",
        "news_title": "\u041d\u043e\u0432\u043e\u0441\u0442\u0438",
        "news_empty": "\u041d\u043e\u0432\u043e\u0441\u0442\u0435\u0439 \u043f\u043e\u043a\u0430 \u043d\u0435\u0442.",
        "status_card_mods": "\u041c\u043e\u0434\u044b \u0433\u043e\u0442\u043e\u0432\u044b",
        "status_card_mods_body": "\u0424\u0430\u0439\u043b\u044b \u0443\u0441\u043f\u0435\u0448\u043d\u043e \u043f\u0440\u043e\u0432\u0435\u0440\u0435\u043d\u044b.",
        "status_card_fabric": "\u0417\u0430\u0433\u0440\u0443\u0437\u0447\u0438\u043a OK",
        "status_card_loader_body": "\u0417\u0430\u0433\u0440\u0443\u0437\u0447\u0438\u043a {loader}",
        "status_card_java": "Java OK",
        "runtime_auto": "\u0410\u0432\u0442\u043e Java",
        "update_available": "\u0412\u044b\u0448\u043b\u043e \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435 \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430: {version}",
        "update_mascot_found": "\u041d\u0430\u0448\u043b\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435!",
        "update_mascot_ok": "\u0412\u0441\u0451 \u043e\u043a!",
        "mascot_welcome": "\u041f\u0440\u0438\u0432\u0435\u0442! \u041b\u0430\u0443\u043d\u0447\u0435\u0440 \u0433\u043e\u0442\u043e\u0432.",
        "mascot_updated": "\u041e\u0431\u043d\u043e\u0432\u0438\u043b\u0430\u0441\u044c \u0434\u043e {version}!",
        "manual_update_tooltip": "\u041f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f",
        "manual_update_checking": "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0439...",
        "manual_update_ok": "\u041e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0439 \u043d\u0435\u0442",
        "manual_update_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u043f\u0440\u043e\u0432\u0435\u0440\u0438\u0442\u044c \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f: {error}",
        "download_update": "\u0421\u043a\u0430\u0447\u0430\u0442\u044c \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0435",
        "update_panel_body": "\u0410\u0432\u0442\u043e\u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u044f \u043f\u043e\u043a\u0430 \u043d\u0435\u0442. \u0421\u043a\u0430\u0447\u0430\u0439\u0442\u0435 \u043d\u043e\u0432\u044b\u0439 \u0430\u0440\u0445\u0438\u0432 \u0438 \u0437\u0430\u043c\u0435\u043d\u0438\u0442\u0435 \u0444\u0430\u0439\u043b\u044b \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430 \u043f\u043e\u0441\u043b\u0435 \u0437\u0430\u043a\u0440\u044b\u0442\u0438\u044f \u0438\u0433\u0440\u044b.",
        "status_mods_ready": "\u0424\u0430\u0439\u043b\u044b \u043c\u043e\u0434\u043e\u0432 \u0433\u043e\u0442\u043e\u0432\u044b.",
        "status_mods_no_sync": "\u042d\u0442\u043e\u0442 \u043f\u0440\u043e\u0444\u0438\u043b\u044c \u043d\u0435 \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0435\u0442 \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u0443\u044e \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u044e \u043c\u043e\u0434\u043e\u0432.",
        "update_disabled": "\u041d\u0435\u0442 \u0443\u0432\u0435\u0434\u043e\u043c\u043b\u0435\u043d\u0438\u044f \u043e\u0431 \u043e\u0431\u043d\u043e\u0432\u043b\u0435\u043d\u0438\u0438.",
        "access_password_title": "\u0414\u043e\u0441\u0442\u0443\u043f \u043a \u0441\u0431\u043e\u0440\u043a\u0435",
        "access_password_body": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043a\u043e\u0434 \u0434\u043b\u044f \u00ab{build}\u00bb. \u041e\u043d \u043e\u0442\u043a\u0440\u044b\u0432\u0430\u0435\u0442 \u043c\u043e\u0434\u044b \u0442\u043e\u043b\u044c\u043a\u043e \u044d\u0442\u043e\u0439 \u0441\u0431\u043e\u0440\u043a\u0438. \u0410\u0434\u043c\u0438\u043d \u043f\u043e\u0434\u0441\u043a\u0430\u0436\u0435\u0442 \u043d\u0443\u0436\u043d\u044b\u0439 \u0441\u0435\u0440\u0432\u0435\u0440 \u0438 \u0442\u043e\u0447\u043d\u0443\u044e \u0432\u0435\u0440\u0441\u0438\u044e \u0438\u0433\u0440\u044b, \u0447\u0442\u043e\u0431\u044b \u0432\u044b \u0441\u043f\u043e\u043a\u043e\u0439\u043d\u043e \u0437\u0430\u0448\u043b\u0438 \u0431\u0435\u0437 \u043b\u0438\u0448\u043d\u0435\u0439 \u0432\u043e\u0437\u043d\u0438.",
        "access_password_prompt": "\u041f\u0430\u0440\u043e\u043b\u044c \u0441\u0431\u043e\u0440\u043a\u0438",
        "access_password_download": "\u0421\u043a\u0430\u0447\u0430\u0442\u044c \u043c\u043e\u0434\u044b",
        "access_password_failed": "\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 \u043f\u0430\u0440\u043e\u043b\u044c \u0441\u0431\u043e\u0440\u043a\u0438. \u0423\u0442\u043e\u0447\u043d\u0438\u0442\u0435 \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b\u0439 \u043a\u043e\u0434 \u0443 \u0430\u0434\u043c\u0438\u043d\u0430 Nukem.",
        "access_password_missing": "\u041f\u0430\u0440\u043e\u043b\u044c \u044d\u0442\u043e\u0439 \u0441\u0431\u043e\u0440\u043a\u0438 \u043d\u0435 \u0437\u0430\u0434\u0430\u043d. \u0410\u0434\u043c\u0438\u043d \u0434\u043e\u043b\u0436\u0435\u043d \u0437\u0430\u0434\u0430\u0442\u044c \u043a\u043e\u0434 \u0434\u043b\u044f \u0441\u0431\u043e\u0440\u043a\u0438.",
        "access_granted": "\u0414\u043e\u0441\u0442\u0443\u043f \u043a \u043f\u0440\u043e\u0435\u043a\u0442\u0443 \u043e\u0442\u043a\u0440\u044b\u0442.",
        "admin_access_granted": "\u0410\u0434\u043c\u0438\u043d\u043a\u0430 \u043e\u0442\u043a\u0440\u044b\u0442\u0430.",
        "action_motor": "\u041c\u043e\u0442\u043e\u0440!",
        "action_go": "\u041f\u043e\u0435\u0445\u0430\u043b\u0438!",
        "action_scene": "\u042d\u043a\u0448\u0435\u043d\u0430!",
        "action_cut": "\u0421\u043d\u044f\u0442\u043e!",
        "action_awake": "\u041d\u0435 \u0441\u043f\u0438\u043c!",
        "loading_versions": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u0432\u0435\u0440\u0441\u0438\u0439...",
        "ready": "\u0413\u043e\u0442\u043e\u0432\u043e",
        "status_syncing": "\u041f\u0440\u043e\u0432\u0435\u0440\u043a\u0430 \u0444\u0430\u0439\u043b\u043e\u0432 \u0441\u0431\u043e\u0440\u043a\u0438...",
        "status_loading_build": "\u0417\u0430\u0433\u0440\u0443\u0437\u043a\u0430 \u043a\u043e\u043d\u0444\u0438\u0433\u0430 \u0441\u0431\u043e\u0440\u043a\u0438...",
        "status_skipping_sync": "\u0417\u0430\u043f\u0443\u0441\u043a \u0431\u0435\u0437 \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u043e\u0439 \u0441\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0430\u0446\u0438\u0438...",
        "status_no_downloads": "\u0412\u0441\u0435 \u0444\u0430\u0439\u043b\u044b \u0443\u0436\u0435 \u0430\u043a\u0442\u0443\u0430\u043b\u044c\u043d\u044b.",
        "status_downloading": "\u0421\u043a\u0430\u0447\u0438\u0432\u0430\u043d\u0438\u0435 \u0444\u0430\u0439\u043b\u043e\u0432...",
        "status_downloading_file": "\u0421\u043a\u0430\u0447\u0438\u0432\u0430\u043d\u0438\u0435: {file}",
        "status_download_complete": "\u0424\u0430\u0439\u043b\u044b \u0441\u043a\u0430\u0447\u0430\u043d\u044b.",
        "status_launching": "\u0417\u0430\u043f\u0443\u0441\u043a Minecraft...",
        "status_game_installing": "\u041f\u043e\u0434\u0433\u043e\u0442\u043e\u0432\u043a\u0430 \u0444\u0430\u0439\u043b\u043e\u0432 Minecraft...",
        "status_game_running": "Minecraft \u0437\u0430\u043f\u0443\u0449\u0435\u043d.",
        "status_game_closed": "Minecraft \u0437\u0430\u043a\u0440\u044b\u0442.",
        "error": "\u041e\u0448\u0438\u0431\u043a\u0430",
        "empty_username": "\u0412\u0432\u0435\u0434\u0438\u0442\u0435 \u043d\u0438\u043a\u043d\u0435\u0439\u043c.",
        "empty_version": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0432\u0435\u0440\u0441\u0438\u044e Minecraft.",
        "empty_build": "\u0412\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u0441\u0431\u043e\u0440\u043a\u0443.",
        "empty_manifest": "\u0423\u043a\u0430\u0436\u0438\u0442\u0435 manifest_url \u0438\u043b\u0438 source_key \u0434\u043b\u044f \u0432\u044b\u0431\u0440\u0430\u043d\u043d\u043e\u0439 \u0441\u0431\u043e\u0440\u043a\u0438 \u0432 launcher_config.json.",
        "server_manifest_required": "\u0414\u043b\u044f \u0441\u0435\u0440\u0432\u0435\u0440\u043d\u043e\u0433\u043e \u043f\u0440\u043e\u0444\u0438\u043b\u044f \u043d\u0443\u0436\u0435\u043d manifest_url \u0438\u043b\u0438 source_key \u043f\u0435\u0440\u0435\u0434 \u0437\u0430\u043f\u0443\u0441\u043a\u043e\u043c.",
        "versions_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u0432\u0435\u0440\u0441\u0438\u0438 Minecraft: {error}",
        "sync_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u0432\u0435\u0440\u0438\u0442\u044c \u0444\u0430\u0439\u043b\u044b: {error}",
        "build_config_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u0433\u0440\u0443\u0437\u0438\u0442\u044c \u043a\u043e\u043d\u0444\u0438\u0433 \u0441\u0431\u043e\u0440\u043a\u0438: {error}",
        "download_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043a\u0430\u0447\u0430\u0442\u044c \u0444\u0430\u0439\u043b\u044b: {error}",
        "launch_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0437\u0430\u043f\u0443\u0441\u0442\u0438\u0442\u044c Minecraft: {error}",
        "settings_failed": "\u041f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435 \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430: {error}",
        "config_repaired": "\u041a\u043e\u043d\u0444\u0438\u0433 \u0431\u044b\u043b \u043f\u043e\u0432\u0440\u0435\u0436\u0434\u0435\u043d. Backup \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d \u0437\u0434\u0435\u0441\u044c: {path}. \u0417\u0430\u0433\u0440\u0443\u0436\u0435\u043d\u044b \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043f\u043e \u0443\u043c\u043e\u043b\u0447\u0430\u043d\u0438\u044e.",
        "config_save_failed": "\u041d\u0435 \u0443\u0434\u0430\u043b\u043e\u0441\u044c \u0441\u043e\u0445\u0440\u0430\u043d\u0438\u0442\u044c \u043d\u0430\u0441\u0442\u0440\u043e\u0439\u043a\u0438 \u043b\u0430\u0443\u043d\u0447\u0435\u0440\u0430: {error}",
        "close_game_prompt": "Minecraft \u0432\u0441\u0435 \u0435\u0449\u0435 \u0437\u0430\u043f\u0443\u0449\u0435\u043d. \u0427\u0442\u043e \u0441\u0434\u0435\u043b\u0430\u0442\u044c MSLaunch?",
        "leave_game_running": "\u041e\u0441\u0442\u0430\u0432\u0438\u0442\u044c \u0438\u0433\u0440\u0443",
        "close_game": "\u0417\u0430\u043a\u0440\u044b\u0442\u044c \u0438\u0433\u0440\u0443",
        "cancel_close": "\u041e\u0442\u043c\u0435\u043d\u0430",
        "launch_report_saved": "\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0439 report \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d \u0437\u0434\u0435\u0441\u044c: {path}",
        "error_report_saved": "\u0422\u0435\u0445\u043d\u0438\u0447\u0435\u0441\u043a\u0438\u0439 report \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d \u0437\u0434\u0435\u0441\u044c: {path}",
        "hash_failed": "\u0425\u044d\u0448 \u0441\u043a\u0430\u0447\u0430\u043d\u043d\u043e\u0433\u043e \u0444\u0430\u0439\u043b\u0430 \u043d\u0435 \u0441\u043e\u0432\u043f\u0430\u043b: {file}",
        "crash_title": "Minecraft \u0432\u044b\u043b\u0435\u0442\u0435\u043b",
    },
}


class VersionsWorker(QThread):
    versions_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, engine: MinecraftEngine) -> None:
        super().__init__()
        self.engine = engine

    def run(self) -> None:
        try:
            self.versions_loaded.emit(self.engine.get_all_versions())
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class BuildConfigWorker(QThread):
    build_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        build: dict[str, object],
        *,
        config: dict[str, object] | None = None,
        client_mode: str = CLIENT_MODE_INDEPENDENT,
        require_manifest: bool = False,
    ) -> None:
        super().__init__()
        self.build = build
        self.config = config or {}
        self.client_mode = client_mode
        self.require_manifest = require_manifest

    def run(self) -> None:
        try:
            if self.client_mode == CLIENT_MODE_NUKEM:
                try:
                    panel_build = resolve_panel_active_build(
                        self.config,
                        CLIENT_MODE_NUKEM,
                        require_manifest=self.require_manifest,
                    )
                except PanelClientError:
                    panel_build = {}
                if panel_build:
                    self.build_loaded.emit(panel_build)
                    return
            self.build_loaded.emit(resolve_build_config(self.build, require_manifest=self.require_manifest))
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class LauncherUpdateWorker(QThread):
    update_loaded = pyqtSignal(dict)
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        build: dict[str, object],
        *,
        config: dict[str, object],
        client_mode: str,
    ) -> None:
        super().__init__()
        self.build = dict(build)
        self.config = config
        self.client_mode = client_mode

    def run(self) -> None:
        try:
            resolved_build = dict(self.build)
            try:
                panel_update = get_panel_launcher_update(self.config)
            except PanelClientError:
                panel_update = {}
            if panel_update:
                self.update_loaded.emit({**resolved_build, **panel_update})
                return
            if resolved_build:
                resolved_build = resolve_build_config(resolved_build, require_manifest=False)
            self.update_loaded.emit(resolved_build)
        except Exception as exc:
            self.error_occurred.emit(str(exc))


class DownloadWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    status_detail_changed = pyqtSignal(str, str)
    error_occurred = pyqtSignal(str, str)
    finished_successfully = pyqtSignal()

    def __init__(
        self,
        engine: MinecraftEngine,
        manifest_url: str,
        game_directory: str | Path,
        *,
        allow_insecure_local: bool = False,
        allow_insecure_http: bool = False,
        require_manifest_files: bool = True,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.manifest_url = manifest_url
        self.game_directory = Path(game_directory)
        self.allow_insecure_local = allow_insecure_local
        self.allow_insecure_http = allow_insecure_http
        self.require_manifest_files = require_manifest_files

    def run(self) -> None:
        staging_path = self.game_directory / ".mslauncher-staging"
        try:
            self.status_changed.emit("status_syncing")
            sync_plan = self.engine.sync_files(
                self.manifest_url,
                self.game_directory,
                allow_insecure_local=self.allow_insecure_local,
                allow_insecure_http=self.allow_insecure_http,
                require_files=self.require_manifest_files,
            )

            if sync_plan.warning:
                self.error_occurred.emit("sync_failed", sync_plan.warning)
                return

            try:
                if sync_plan.files_to_download:
                    self.status_changed.emit("status_downloading")
                    staged_files = self._download_files(sync_plan.files_to_download, staging_path)
                    self._replace_target_files(staged_files)

                self.engine.remove_unknown_mods(self.game_directory, sync_plan.unknown_mods)
            except Exception as exc:
                self.error_occurred.emit("download_failed", str(exc))
                return
            finally:
                self._cleanup_staging(staging_path)

            self.progress_changed.emit(100)
            if sync_plan.files_to_download:
                self.status_changed.emit("status_download_complete")
            else:
                self.status_changed.emit("status_no_downloads")
            self.finished_successfully.emit()
        except requests.RequestException as exc:
            self.error_occurred.emit("download_failed", str(exc))
        except Exception as exc:
            self.error_occurred.emit("sync_failed", str(exc))

    def _download_files(
        self,
        files: list[dict[str, str | int]],
        staging_path: Path,
    ) -> list[tuple[Path, Path]]:
        self._cleanup_staging(staging_path)
        total_bytes = sum(int(file.get("size", 0)) for file in files)
        completed_bytes = 0
        staged_files: list[tuple[Path, Path]] = []

        for file_info in files:
            relative_path = self._safe_relative_path(file_info)
            url = self._safe_download_url(file_info, relative_path)
            expected_hash = str(file_info.get("sha256", "")).lower().strip()
            expected_size = int(file_info.get("size", 0))

            self.status_detail_changed.emit("status_downloading_file", relative_path)
            target_path = self.game_directory / relative_path
            staged_path = staging_path / relative_path
            self._download_file_with_retry(
                url=url,
                staged_path=staged_path,
                expected_hash=expected_hash,
                expected_size=expected_size,
                relative_path=relative_path,
                completed_bytes=completed_bytes,
                total_bytes=total_bytes,
            )
            staged_files.append((staged_path, target_path))
            completed_bytes += expected_size
            self.progress_changed.emit(self._calculate_progress(completed_bytes, total_bytes))

        return staged_files

    def _download_file_with_retry(
        self,
        url: str,
        staged_path: Path,
        expected_hash: str,
        expected_size: int,
        relative_path: str,
        completed_bytes: int,
        total_bytes: int,
    ) -> None:
        last_error: Exception | None = None

        for attempt in range(1, DOWNLOAD_RETRIES + 1):
            part_path = staged_path.with_name(f"{staged_path.name}.part")

            try:
                self._download_to_part_file(
                    url=url,
                    part_path=part_path,
                    completed_bytes=completed_bytes,
                    total_bytes=total_bytes,
                )
                self._verify_downloaded_file(part_path, expected_hash, expected_size, relative_path)
                staged_path.parent.mkdir(parents=True, exist_ok=True)
                part_path.replace(staged_path)
                return
            except Exception as exc:
                last_error = exc
                part_path.unlink(missing_ok=True)
                staged_path.unlink(missing_ok=True)
                if attempt < DOWNLOAD_RETRIES:
                    self.msleep(500 * attempt)

        raise RuntimeError(f"Failed to download {relative_path}: {last_error}")

    def _download_to_part_file(
        self,
        url: str,
        part_path: Path,
        completed_bytes: int,
        total_bytes: int,
    ) -> None:
        part_path.parent.mkdir(parents=True, exist_ok=True)
        part_path.unlink(missing_ok=True)
        current_file_bytes = 0

        with requests.get(url, stream=True, timeout=REQUEST_TIMEOUT) as response:
            response.raise_for_status()
            with part_path.open("wb") as file:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                    if not chunk:
                        continue

                    file.write(chunk)
                    current_file_bytes += len(chunk)
                    self.progress_changed.emit(
                        self._calculate_progress(completed_bytes + current_file_bytes, total_bytes)
                    )

    def _verify_downloaded_file(
        self,
        part_path: Path,
        expected_hash: str,
        expected_size: int,
        relative_path: str,
    ) -> None:
        actual_size = part_path.stat().st_size
        if actual_size != expected_size:
            raise RuntimeError(f"Size mismatch for {relative_path}: expected {expected_size}, got {actual_size}")
        if expected_hash and self._calculate_sha256(part_path) != expected_hash:
            raise RuntimeError(f"Checksum mismatch for {relative_path}")

    def _replace_target_files(self, staged_files: list[tuple[Path, Path]]) -> None:
        for staged_path, target_path in staged_files:
            if not staged_path.is_file():
                raise RuntimeError(f"Staged file is missing: {staged_path.name}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            staged_path.replace(target_path)

    def _cleanup_staging(self, staging_path: Path) -> None:
        if staging_path.exists():
            shutil.rmtree(staging_path, ignore_errors=True)

    def _safe_relative_path(self, file_info: dict[str, str | int]) -> str:
        return normalize_manifest_path(file_info.get("path", ""))

    def _safe_download_url(self, file_info: dict[str, str | int], relative_path: str) -> str:
        return normalize_download_url(
            file_info.get("url", ""),
            relative_path,
            allow_insecure_local=self.allow_insecure_local,
            allow_insecure_http=self.allow_insecure_http,
        )

    def _calculate_sha256(self, file_path: Path) -> str:
        digest = hashlib.sha256()
        with file_path.open("rb") as file:
            for chunk in iter(lambda: file.read(CHUNK_SIZE), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _calculate_progress(self, downloaded_bytes: int, total_bytes: int) -> int:
        if total_bytes <= 0:
            return 0
        return min(100, int(downloaded_bytes * 100 / total_bytes))


class LaunchWorker(QThread):
    progress_changed = pyqtSignal(int)
    status_changed = pyqtSignal(str)
    crash_detected = pyqtSignal(str)
    error_occurred = pyqtSignal(str, str)
    game_started = pyqtSignal()
    finished_successfully = pyqtSignal()

    def __init__(
        self,
        engine: MinecraftEngine,
        version: str,
        username: str,
        launch_options: dict[str, object] | None = None,
    ) -> None:
        super().__init__()
        self.engine = engine
        self.version = version
        self.username = username
        self.launch_options = launch_options or {}
        self.detach_event = threading.Event()
        self.launch_options["detach_event"] = self.detach_event
        self.launch_options["game_started_callback"] = self.game_started.emit

    def run(self) -> None:
        try:
            crash_reason = self.engine.launch_installed(
                self.version,
                self.username,
                self._on_minecraft_progress,
                self.launch_options,
            )

            if crash_reason:
                self.crash_detected.emit(crash_reason)
            else:
                self.finished_successfully.emit()
        except Exception as exc:
            self.error_occurred.emit(str(exc), traceback.format_exc())

    def _on_minecraft_progress(self, status: str, progress: int, maximum: int) -> None:
        self.status_changed.emit("status_game_installing")
        if maximum > 0:
            self.progress_changed.emit(min(100, int(progress * 100 / maximum)))

    def request_detach(self) -> None:
        self.detach_event.set()

    def request_terminate_game(self) -> None:
        self.engine.terminate_game_process()


class StatusGlyph(QFrame):
    def __init__(self, glyph: str, size: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.glyph = glyph
        self.setFixedSize(size, size)
        self.setObjectName("statusCheck" if glyph == "check" else "statusIcon")

    def paintEvent(self, event) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = self.rect().adjusted(3, 3, -3, -3)
        border = QColor(93, 202, 235, 110)
        ink = QColor("#5dcaeb")

        painter.setPen(QPen(QColor(93, 202, 235, 38), 3.2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 7, 7)
        painter.setPen(QPen(border, 1.0))
        painter.setBrush(QColor(93, 202, 235, 16 if self.glyph != "check" else 10))
        painter.drawRoundedRect(rect, 7, 7)
        painter.setPen(QPen(ink, 1.85, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))

        width = self.width()
        height = self.height()
        if self.glyph == "shield":
            path = QPainterPath()
            path.moveTo(width * 0.50, height * 0.18)
            path.lineTo(width * 0.74, height * 0.27)
            path.lineTo(width * 0.70, height * 0.56)
            path.lineTo(width * 0.50, height * 0.78)
            path.lineTo(width * 0.30, height * 0.56)
            path.lineTo(width * 0.26, height * 0.27)
            path.closeSubpath()
            painter.drawPath(path)
            self._paint_check(painter, width, height, 0.02)
        elif self.glyph == "fabric":
            for offset in (-10, 0, 10):
                painter.drawLine(QPointF(width * 0.34 + offset, height * 0.68), QPointF(width * 0.62 + offset, height * 0.30))
                painter.drawLine(QPointF(width * 0.36 + offset, height * 0.32), QPointF(width * 0.66 + offset, height * 0.66))
            painter.setPen(QPen(ink, 1.25, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            for x_position in (0.35, 0.50, 0.65):
                painter.drawPoint(QPointF(width * x_position, height * 0.50))
        elif self.glyph == "java":
            for offset in (-8, 8):
                path = QPainterPath(QPointF(width * 0.50 + offset, height * 0.22))
                path.cubicTo(width * 0.38 + offset, height * 0.35, width * 0.62 + offset, height * 0.42, width * 0.48 + offset, height * 0.55)
                painter.drawPath(path)
            painter.drawLine(QPointF(width * 0.30, height * 0.68), QPointF(width * 0.70, height * 0.68))
            painter.drawLine(QPointF(width * 0.36, height * 0.78), QPointF(width * 0.64, height * 0.78))
        else:
            self._paint_check(painter, width, height, 0.0)

    def _paint_check(self, painter: QPainter, width: int, height: int, shift: float) -> None:
        painter.drawLine(QPointF(width * (0.34 + shift), height * 0.52), QPointF(width * (0.45 + shift), height * 0.64))
        painter.drawLine(QPointF(width * (0.45 + shift), height * 0.64), QPointF(width * (0.68 + shift), height * 0.38))


class MascotWindow(QWidget):
    clicked = pyqtSignal()
    hovered = pyqtSignal()

    def __init__(self, mascot_paths: list[Path]) -> None:
        super().__init__(None)
        self.mascot_paths = mascot_paths
        self.mascot_index = 0
        self._drag_position = None
        self._press_global = None
        self._was_dragged = False
        self.movie: QMovie | None = None
        self._transparent_movie_frame = False
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.message_label = QLabel()
        self.message_label.setObjectName("floatingMascotMessage")
        self.message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.message_label.hide()
        layout.addWidget(self.message_label)
        self.image_label = QLabel()
        self.image_label.setObjectName("floatingMascot")
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)
        self.set_mascot_index(0)

    def set_mascot_index(self, index: int) -> None:
        if not self.mascot_paths:
            self.image_label.setText("MS")
            self.image_label.setFixedSize(120, 120)
            self.resize(120, 120)
            return

        self.mascot_index = index % len(self.mascot_paths)
        path = self.mascot_paths[self.mascot_index]
        if self.movie is not None:
            self.movie.stop()
        self.movie = QMovie(str(path))
        self.movie.setCacheMode(QMovie.CacheMode.CacheAll)
        self.movie.frameChanged.connect(self.refresh_movie_frame)
        self.movie.jumpToFrame(0)
        source_size = self.movie.currentPixmap().size()
        if source_size.isEmpty():
            source_size = QSize(180, 220)
        target_size = self._fit_size(source_size)
        self.movie.setScaledSize(target_size)
        self.image_label.setFixedSize(target_size)
        self._transparent_movie_frame = True
        self.image_label.setMovie(None)
        self.resize(target_size)
        self.movie.start()
        self.refresh_movie_frame()

    def set_message(self, message: str) -> None:
        self.message_label.setText(message)
        self.message_label.setVisible(bool(message.strip()))
        if self.message_label.isVisible():
            self.message_label.setFixedWidth(max(self.image_label.width(), 230))
        self.adjustSize()

    def next_mascot(self) -> None:
        self.set_mascot_index(self.mascot_index + 1)

    def refresh_movie_frame(self, *_args) -> None:
        if self.movie is None:
            return
        pixmap = self.movie.currentPixmap()
        if pixmap.isNull():
            return
        if self._transparent_movie_frame:
            pixmap = QPixmap.fromImage(self.make_near_black_transparent(pixmap.toImage()))
        self.image_label.setPixmap(pixmap)

    def make_near_black_transparent(self, image: QImage) -> QImage:
        converted = image.convertToFormat(QImage.Format.Format_ARGB32)
        for y in range(converted.height()):
            for x in range(converted.width()):
                color = QColor(converted.pixel(x, y))
                if color.red() < 24 and color.green() < 24 and color.blue() < 24:
                    color.setAlpha(0)
                    converted.setPixelColor(x, y, color)
        return converted

    def _fit_size(self, source_size: QSize) -> QSize:
        max_width = 240
        max_height = 280
        width = max(1, source_size.width())
        height = max(1, source_size.height())
        scale = min(max_width / width, max_height / height, 1.0)
        return QSize(max(96, int(width * scale)), max(96, int(height * scale)))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            global_position = event.globalPosition().toPoint()
            self._press_global = global_position
            self._was_dragged = False
            self._drag_position = global_position - self.frameGeometry().topLeft()
            self.setCursor(QCursor(Qt.CursorShape.ClosedHandCursor))
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            global_position = event.globalPosition().toPoint()
            if self._press_global is not None and (global_position - self._press_global).manhattanLength() > 8:
                self._was_dragged = True
            self.move(global_position - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None
        self._press_global = None
        self.setCursor(QCursor(Qt.CursorShape.OpenHandCursor))
        if not self._was_dragged and event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def enterEvent(self, event) -> None:
        self.hovered.emit()
        super().enterEvent(event)


class ParallaxFrame(QFrame):
    def __init__(self) -> None:
        super().__init__()
        self.setMouseTracking(False)
        self._current_offset_x = 0.0
        self._current_offset_y = 0.0
        self._target_offset_x = 0.0
        self._target_offset_y = 0.0
        self._background_paths = self._default_background_paths()
        self._background_index = random.randrange(len(self._background_paths)) if self._background_paths else 0
        self._pixmap = self._load_current_background()
        self._next_pixmap: QPixmap | None = None
        self._fade_progress = 1.0
        self._slideshow_enabled = False
        self._slide_ticks = 0
        self._slide_interval_ticks = 122
        self._cinema_phase = random.random() * math.tau
        self._particle_phase = 0
        self._particles = self._create_particles()
        self._glow_particles = self._create_glow_particles()
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(33)
        self._animation_timer.timeout.connect(self._tick)
        self._animation_timer.start()

    def _default_background_paths(self) -> list[Path]:
        return [BACKGROUND_DIR / name for name in BACKGROUND_FILES if (BACKGROUND_DIR / name).is_file()]

    def set_background_files(self, paths: list[Path], slideshow_enabled: bool = False) -> None:
        available_paths = [path for path in paths if path.is_file()] or self._default_background_paths()
        if available_paths == self._background_paths and slideshow_enabled == self._slideshow_enabled:
            return

        self._background_paths = available_paths
        self._background_index = random.randrange(len(self._background_paths)) if self._background_paths else 0
        self._pixmap = self._load_current_background()
        self._next_pixmap = None
        self._fade_progress = 1.0
        self._slideshow_enabled = slideshow_enabled and len(self._background_paths) > 1
        self._slide_ticks = 0
        self._cinema_phase = random.random() * math.tau
        self.update()

    def _load_current_background(self) -> QPixmap | None:
        if not self._background_paths:
            return None
        return QPixmap(str(self._background_paths[self._background_index]))

    def _load_next_background(self) -> QPixmap | None:
        if len(self._background_paths) < 2:
            return None
        self._background_index = (self._background_index + 1) % len(self._background_paths)
        return QPixmap(str(self._background_paths[self._background_index]))

    def mouseMoveEvent(self, event) -> None:
        super().mouseMoveEvent(event)

    def leaveEvent(self, event) -> None:
        super().leaveEvent(event)

    def _tick(self) -> None:
        self._current_offset_x *= 0.94
        self._current_offset_y *= 0.94
        self._cinema_phase = (self._cinema_phase + 0.0014) % math.tau

        if self._next_pixmap is not None:
            self._fade_progress += 0.022
            if self._fade_progress >= 1:
                self._pixmap = self._next_pixmap
                self._next_pixmap = None
                self._fade_progress = 1.0
                self._slide_ticks = 0
        elif self._slideshow_enabled:
            self._slide_ticks += 1
            if self._slide_ticks >= self._slide_interval_ticks:
                next_pixmap = self._load_next_background()
                if next_pixmap is not None and not next_pixmap.isNull():
                    self._next_pixmap = next_pixmap
                    self._fade_progress = 0.0
                else:
                    self._slide_ticks = 0

        self._particle_phase = (self._particle_phase + 1) % 1620
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)

        if self._pixmap and not self._pixmap.isNull():
            self._paint_cover_pixmap(painter, self._pixmap, 1.0)
            if self._next_pixmap and not self._next_pixmap.isNull():
                self._paint_cover_pixmap(painter, self._next_pixmap, min(1.0, self._fade_progress))
        else:
            painter.fillRect(self.rect(), QColor("#253642"))

        painter.fillRect(self.rect(), QColor(5, 9, 12, 122))
        self._paint_particles(painter)
        self._paint_glow_particles(painter)
        self._paint_depth_overlay(painter)
        super().paintEvent(event)

    def _paint_cover_pixmap(self, painter: QPainter, pixmap: QPixmap, opacity: float) -> None:
        target_width = max(1, int(self.width() * 1.10) + 64)
        target_height = max(1, int(self.height() * 1.10) + 48)
        scaled = pixmap.scaled(
            target_width,
            target_height,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        cinematic_x = math.sin(self._cinema_phase * 0.74) * 10
        cinematic_y = math.cos(self._cinema_phase * 0.52) * 6
        x = int((self.width() - scaled.width()) / 2 - self._current_offset_x - cinematic_x)
        y = int((self.height() - scaled.height()) / 2 - self._current_offset_y - cinematic_y)
        painter.save()
        painter.setOpacity(opacity)
        painter.drawPixmap(x, y, scaled)
        painter.restore()

    def _paint_depth_overlay(self, painter: QPainter) -> None:
        width = self.width()
        height = self.height()
        painter.fillRect(0, 0, width, int(height * 0.12), QColor(0, 12, 8, 64))
        painter.fillRect(0, int(height * 0.7), width, int(height * 0.3), QColor(0, 0, 0, 82))
        for index in range(10):
            alpha = max(0, 44 - index * 4)
            painter.fillRect(index * 7, 0, 7, height, QColor(0, 0, 0, alpha))
            painter.fillRect(width - (index + 1) * 9, 0, 9, height, QColor(0, 0, 0, max(0, 42 - index * 4)))

    def _create_particles(self) -> list[tuple[float, float, float, int, int]]:
        randomizer = random.Random(42)
        return [
            (
                randomizer.random(),
                randomizer.random(),
                randomizer.uniform(0.18, 0.75),
                randomizer.choice((1, 1, 1, 1, 2, 3)),
                randomizer.randint(18, 62),
            )
            for _ in range(204)
        ]

    def _create_glow_particles(self) -> list[tuple[float, float, float, int, int, int, int]]:
        randomizer = random.Random(73)
        return [
            (
                randomizer.random(),
                randomizer.uniform(0.18, 0.82),
                randomizer.uniform(0.06, 0.16),
                randomizer.randint(1, 2),
                randomizer.randint(45, 95),
                randomizer.randint(150, 270),
                randomizer.randint(150, 270),
            )
            for _ in range(10)
        ]

    def _paint_particles(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        width = max(1, self.width())
        height = max(1, self.height())

        for index, (base_x, base_y, speed, size, alpha) in enumerate(self._particles):
            drift_cycle = 315
            drift = (self._particle_phase * speed + index * 19) % drift_cycle
            fade = abs((drift_cycle / 2) - drift) / (drift_cycle / 2)
            particle_alpha = int(min(92, alpha * 1.15 * (1 - fade * 0.56)))
            if particle_alpha <= 4:
                continue

            x = int((base_x * width + drift * 0.12) % width)
            y = int((base_y * height - drift * 0.08) % height)

            painter.setBrush(QColor(225, 238, 230, particle_alpha))
            painter.drawEllipse(x, y, size, size)

        painter.restore()

    def _paint_glow_particles(self, painter: QPainter) -> None:
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        width = max(1, self.width())
        height = max(1, self.height())
        phase = self._particle_phase

        for index, (base_x, base_y, speed, size, peak_alpha, active_span, cycle) in enumerate(self._glow_particles):
            age = (phase + index * 113) % cycle
            active_span = min(cycle - 20, active_span)
            if age > active_span:
                continue

            fade_in = min(1.0, age / 45)
            fade_out = min(1.0, (active_span - age) / 60)
            pulse = 0.65 + 0.35 * math.sin((age / max(1, active_span)) * math.tau)
            alpha = int(peak_alpha * max(0.0, min(fade_in, fade_out)) * pulse)
            if alpha <= 8:
                continue

            x = int((base_x * width + age * speed * 8) % width)
            y = int(base_y * height + math.sin((age + index * 17) * 0.025) * 10)
            painter.setBrush(QColor(134, 255, 200, min(16, alpha // 4)))
            painter.drawEllipse(x - size * 2, y - size * 2, size * 5, size * 5)
            painter.setBrush(QColor(190, 255, 220, alpha))
            painter.drawEllipse(x, y, size, size)

        painter.restore()


class MSLauncherWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.config, config_warning = load_launcher_config_file(CONFIG_FILE)
        global CONFIG_LOAD_WARNING
        CONFIG_LOAD_WARNING = config_warning
        self.builds = get_config_builds(self.config)
        config_language = get_config_text(self.config, "default_language", "EN")
        self.language = config_language if config_language in TRANSLATIONS else "EN"
        self.client_mode = get_client_mode(self.config)
        self.social_links = get_social_links(self.config, self.client_mode)
        self.recent_usernames = get_config_string_list(self.config, "recent_usernames")
        self.profile_manager = LauncherProfileManager(get_profile_base_directory(self.config) or None)
        self.active_profile = self.profile_manager.get_profile(get_config_text(self.config, "default_profile"))
        self.engine = MinecraftEngine(str(self.active_profile.directory))
        self.game_directory = self.active_profile.directory
        self.download_worker: DownloadWorker | None = None
        self.launch_worker: LaunchWorker | None = None
        self.versions_worker: VersionsWorker | None = None
        self.build_config_worker: BuildConfigWorker | None = None
        self.update_check_worker: LauncherUpdateWorker | None = None
        self.update_check_manual = False
        self.selected_profile: LauncherProfile = self.active_profile
        self.selected_username = ""
        self.selected_version = ""
        self.selected_manifest_url = ""
        self.selected_launch_options: dict[str, object] = {}
        self.action_requires_mod_access = False
        self.last_crash_reason = ""
        self.last_crash_report_path: Path | None = None
        self.last_error_message = ""
        self.last_error_report_path: Path | None = None
        self.launcher_update_version = ""
        self.launcher_update_url = ""
        self.launcher_update_notes = ""
        self.launcher_update_error = ""
        self.skin_path = get_config_text(self.config, "skin_path")
        self.info_panel_mode = "status"
        self.status_card_confirmed = True
        self._drag_position = None
        self.project_access_unlocked = False
        self.admin_access_unlocked = False
        self.unlocked_build_ids: set[str] = set()
        self.project_switcher_expanded = False
        self.large_window_enabled = False
        self.mascot_paths = (
            [MASCOT_DIR / name for name in MASCOT_FILES if (MASCOT_DIR / name).is_file()]
            if MASCOT_FEATURE_ENABLED
            else []
        )
        self.mascot_window: MascotWindow | None = None
        self.mascot_user_enabled = False
        self.mascot_click_times: list[float] = []
        self.floating_mascot_message_active = False
        self.tray_icon: QSystemTrayIcon | None = None
        self.hidden_to_tray_for_game = False
        self.update_check_state = "ok"
        self.update_pulse_on = False
        self.update_mascot_dismissed = False
        self.update_mascot_message_key = ""
        self.update_ok_click_times: list[float] = []
        self.update_pulse_timer = QTimer(self)
        self.update_pulse_timer.setInterval(650)
        self.update_pulse_timer.timeout.connect(self.toggle_update_pulse)
        self.update_poll_timer = QTimer(self)
        self.update_poll_timer.setInterval(15_000)
        self.update_poll_timer.timeout.connect(self.auto_check_launcher_update)
        self.news_items: list[dict[str, str]] = []
        self.news_index = 0
        self.news_timer = QTimer(self)
        self.news_timer.setInterval(30_000)
        self.news_timer.timeout.connect(self.show_next_news_item)
        self.brand_subtitle_key = random.choice(self.get_brand_subtitle_keys())
        self.action_phrase_key = "play_idle"
        self.launch_after_sync = True

        self._build_ui()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Window)
        if APP_ICON_PATH.is_file():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.setup_tray_icon()
        self.refresh_project_backgrounds()
        self._connect_signals()
        self.apply_translations()
        self.update_poll_timer.start()
        QTimer.singleShot(1_000, self.auto_check_launcher_update)
        if MASCOT_FEATURE_ENABLED:
            QTimer.singleShot(1_600, self.show_startup_mascot_notice_if_needed)
        self.show_config_repair_warning_if_needed()
        self.load_versions()

    def _build_ui(self) -> None:
        central_widget = QWidget(self)
        root_layout = QVBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.hero_frame = ParallaxFrame()
        hero_frame = self.hero_frame
        hero_frame.setObjectName("heroFrame")
        hero_frame.setMinimumHeight(540)
        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setContentsMargins(42, 20, 30, 22)
        hero_layout.setSpacing(14)

        top_layout = QGridLayout()
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setHorizontalSpacing(12)
        top_layout.setColumnStretch(0, 1)
        top_layout.setColumnStretch(1, 0)
        top_layout.setColumnStretch(2, 1)

        brand_lockup = QFrame()
        brand_lockup.setObjectName("brandLockup")
        brand_lockup.setMaximumWidth(430)
        brand_lockup_layout = QHBoxLayout(brand_lockup)
        brand_lockup_layout.setContentsMargins(0, 0, 0, 0)
        brand_lockup_layout.setSpacing(12)

        logo_badge = QLabel("MS")
        logo_badge.setObjectName("logoBadge")
        logo_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_badge.setFixedSize(60, 60)
        logo_badge.hide()

        brand_text_layout = QVBoxLayout()
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(0)
        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setMaximumWidth(320)
        self.logo_label = QLabel()
        self.logo_label.setObjectName("brandIcon")
        self.logo_label.setFixedSize(58, 58)
        self.logo_label.setScaledContents(True)
        self.subtitle_label = QLabel()
        self.subtitle_label.setObjectName("subtitleLabel")
        self.subtitle_label.setWordWrap(True)
        self.subtitle_label.setMaximumWidth(340)
        self.subtitle_label.hide()
        self.credit_label = QLabel()
        self.credit_label.setObjectName("creditLabel")
        self.credit_label.setMaximumWidth(340)
        brand_text_layout.addWidget(self.title_label)
        brand_text_layout.addWidget(self.subtitle_label)
        brand_text_layout.addWidget(self.credit_label)
        brand_lockup_layout.addWidget(logo_badge)
        brand_lockup_layout.addWidget(self.logo_label)
        brand_lockup_layout.addLayout(brand_text_layout)

        self.project_switcher = QFrame()
        self.project_switcher.setObjectName("projectSwitcher")
        self.project_switcher.setToolTip(self.translate("project_switcher_tooltip"))
        self.project_switcher.installEventFilter(self)
        self.project_layout = QHBoxLayout(self.project_switcher)
        self.project_layout.setContentsMargins(0, 0, 0, 0)
        self.project_layout.setSpacing(6)
        self.mslaunch_tab = self.create_project_tab("MS", "MSLaunch")
        self.nukem_tab = self.create_project_tab("KH", "MS Nuckem")
        self.vibecraft_tab = self.create_project_tab("VC", "VibeCraft")
        self.vibecraft_tab.setEnabled(False)
        self.project_tabs = {
            CLIENT_MODE_INDEPENDENT: self.mslaunch_tab,
            CLIENT_MODE_NUKEM: self.nukem_tab,
            "vibecraft": self.vibecraft_tab,
        }
        for tab in self.project_tabs.values():
            tab.installEventFilter(self)
            self.project_layout.addWidget(tab)

        self.language_toggle_button = QPushButton()
        self.language_toggle_button.setObjectName("languageToggle")
        self.language_toggle_button.setFixedSize(42, 34)
        self.language_toggle_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_check_button = QPushButton("OK")
        self.update_check_button.setObjectName("updateCheckButton")
        self.update_check_button.setFixedSize(40, 34)
        self.update_check_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        right_controls = QFrame()
        right_controls.setObjectName("topRightControls")
        right_controls_layout = QHBoxLayout(right_controls)
        right_controls_layout.setContentsMargins(0, 0, 0, 0)
        right_controls_layout.setSpacing(6)

        title_controls = QFrame()
        title_controls.setObjectName("windowControls")
        title_controls_layout = QHBoxLayout(title_controls)
        title_controls_layout.setContentsMargins(0, 0, 0, 0)
        title_controls_layout.setSpacing(6)
        self.minimize_button = QPushButton("-")
        self.minimize_button.setObjectName("windowButton")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.size_toggle_button = QPushButton("\u25a1")
        self.size_toggle_button.setObjectName("windowButton")
        self.size_toggle_button.setFixedSize(30, 30)
        self.size_toggle_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.close_button = QPushButton("x")
        self.close_button.setObjectName("windowButton")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        title_controls_layout.addWidget(self.minimize_button)
        title_controls_layout.addWidget(self.size_toggle_button)
        title_controls_layout.addWidget(self.close_button)
        right_controls_layout.addWidget(self.update_check_button)
        right_controls_layout.addWidget(self.language_toggle_button)
        right_controls_layout.addWidget(title_controls)

        top_layout.addWidget(brand_lockup, 0, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        top_layout.addWidget(self.project_switcher, 0, 1, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        top_layout.addWidget(right_controls, 0, 2, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
        hero_layout.addLayout(top_layout, 0)

        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("sidebarFrame")
        self.sidebar_layout = QVBoxLayout(self.sidebar_frame)
        self.sidebar_layout.setContentsMargins(9, 12, 9, 12)
        self.sidebar_layout.setSpacing(8)

        self.settings_button = self.create_side_button("settings")
        self.settings_button.clicked.connect(self.toggle_info_panel)
        self.sidebar_layout.addWidget(self.settings_button)

        self.mascot_button = self.create_side_button("mascot", "MS")
        self.mascot_button.installEventFilter(self)
        self.mascot_button.clicked.connect(self.toggle_floating_mascot)
        self.sidebar_layout.addWidget(self.mascot_button)
        self.mascot_button.setVisible(MASCOT_FEATURE_ENABLED)
        self.mascot_button.setEnabled(MASCOT_FEATURE_ENABLED)

        self.report_button = self.create_side_button("report", "DOC")
        self.report_button.setProperty("role", "report")
        self.report_button.clicked.connect(self.show_feedback_panel)
        self.sidebar_layout.addWidget(self.report_button)

        self.admin_button = self.create_side_button("admin", "ADM")
        self.admin_button.clicked.connect(self.show_admin_panel)
        self.sidebar_layout.addWidget(self.admin_button)

        self.mode_button = self.create_side_button("mode", "NK")
        self.mode_button.hide()

        self.social_buttons: list[QPushButton] = []
        self.refresh_social_buttons()

        self.sidebar_layout.addStretch()

        self.info_panel = QFrame()
        self.info_panel.setObjectName("infoPanel")
        info_layout = QVBoxLayout(self.info_panel)
        info_layout.setContentsMargins(24, 24, 24, 24)
        info_layout.setSpacing(14)
        self.info_title_label = QLabel()
        self.info_title_label.setObjectName("infoTitle")
        self.info_title_label.setWordWrap(True)
        self.info_title_label.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.MinimumExpanding,
        )
        self.info_body_label = QLabel()
        self.info_body_label.setObjectName("infoBody")
        self.info_body_label.setWordWrap(True)
        self.info_body_label.setMinimumWidth(240)
        info_layout.addWidget(self.info_title_label)
        info_layout.addWidget(self.info_body_label)

        self.mods_status_title, self.mods_status_body, self.mods_status_check, mods_row = self.create_status_row(
            "shield", "Mods ready", "All mods loaded and compatible."
        )
        self.fabric_status_title, self.fabric_status_body, self.fabric_status_check, fabric_row = self.create_status_row(
            "fabric", "Loader OK", "Loader ready"
        )
        self.java_status_title, self.java_status_body, self.java_status_check, java_row = self.create_status_row(
            "java", "Java OK", "Runtime ready"
        )
        info_layout.addWidget(mods_row)
        info_layout.addWidget(fabric_row)
        info_layout.addWidget(java_row)
        self.status_rows = [mods_row, fabric_row, java_row]

        self.open_profile_button = QPushButton()
        self.open_profile_button.setObjectName("panelButton")
        self.open_game_button = QPushButton()
        self.open_game_button.setObjectName("panelButton")
        self.open_crash_reports_button = QPushButton()
        self.open_crash_reports_button.setObjectName("panelButton")
        self.download_update_button = QPushButton()
        self.download_update_button.setObjectName("panelButton")
        info_layout.addWidget(self.open_profile_button)
        info_layout.addWidget(self.open_game_button)
        info_layout.addWidget(self.open_crash_reports_button)
        info_layout.addWidget(self.download_update_button)

        self.open_modpack_repo_button = QPushButton()
        self.open_modpack_repo_button.setObjectName("panelButton")
        self.open_modpack_manifest_button = QPushButton()
        self.open_modpack_manifest_button.setObjectName("panelButton")
        self.open_support_queue_button = QPushButton()
        self.open_support_queue_button.setObjectName("panelButton")
        self.admin_news_button = QPushButton()
        self.admin_news_button.setObjectName("panelButton")
        self.admin_builds_button = QPushButton()
        self.admin_builds_button.setObjectName("panelButton")
        self.admin_password_button = QPushButton()
        self.admin_password_button.setObjectName("panelButton")
        info_layout.addWidget(self.open_modpack_repo_button)
        info_layout.addWidget(self.open_modpack_manifest_button)
        info_layout.addWidget(self.open_support_queue_button)
        info_layout.addWidget(self.admin_news_button)
        info_layout.addWidget(self.admin_builds_button)
        info_layout.addWidget(self.admin_password_button)
        self.admin_widgets = [
            self.open_modpack_repo_button,
            self.open_modpack_manifest_button,
            self.open_support_queue_button,
            self.admin_news_button,
            self.admin_builds_button,
            self.admin_password_button,
        ]

        self.loader_setting_label = QLabel()
        self.loader_setting_combo = QComboBox()
        self.loader_setting_combo.addItems(["vanilla", "fabric"])
        self.memory_min_label = QLabel()
        self.memory_min_input = QSpinBox()
        self.memory_min_input.setObjectName("memorySpin")
        self.memory_min_input.setRange(1, 16)
        self.memory_min_input.setSuffix("G")
        self.memory_max_label = QLabel()
        self.memory_max_input = QSpinBox()
        self.memory_max_input.setObjectName("memorySpin")
        self.memory_max_input.setRange(1, 32)
        self.memory_max_input.setSuffix("G")
        self.memory_hint_label = QLabel()
        self.memory_hint_label.setObjectName("memoryHint")
        self.memory_hint_label.setWordWrap(True)
        self.java_path_label = QLabel()
        self.java_path_input = QLineEdit()
        self.java_browse_button = QPushButton()
        self.java_browse_button.setObjectName("panelButton")
        self.skin_label = QLabel()
        self.skin_status_label = QLabel()
        self.skin_status_label.setObjectName("infoBody")
        self.skin_status_label.setWordWrap(True)
        self.skin_browse_button = QPushButton()
        self.skin_browse_button.setObjectName("panelButton")
        self.skin_url_label = QLabel()
        self.skin_url_input = QLineEdit()
        self.skin_url_button = QPushButton()
        self.skin_url_button.setObjectName("panelButton")
        self.admin_unlock_button = QPushButton()
        self.admin_unlock_button.setObjectName("panelButton")

        launch_options = get_config_launch_options(self.config)
        self.loader_setting_combo.setCurrentText(str(launch_options.get("loader", "vanilla")))
        self.memory_min_input.setValue(self.memory_setting_to_gb(str(launch_options.get("memory_min", "512M"))))
        self.memory_max_input.setValue(self.memory_setting_to_gb(str(launch_options.get("memory_max", "2G"))))
        self.java_path_input.setText(str(launch_options.get("java_path", "")))
        self.refresh_memory_hint()
        for hidden_launch_widget in (
            self.loader_setting_label,
            self.loader_setting_combo,
            self.java_path_label,
            self.java_path_input,
            self.java_browse_button,
        ):
            hidden_launch_widget.hide()

        self.settings_scroll_area = QScrollArea()
        self.settings_scroll_area.setObjectName("settingsScrollArea")
        self.settings_scroll_area.setWidgetResizable(True)
        self.settings_scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.settings_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.settings_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.settings_container = QFrame()
        self.settings_container.setObjectName("settingsContainer")
        settings_layout = QVBoxLayout(self.settings_container)
        settings_layout.setContentsMargins(0, 0, 0, 0)
        settings_layout.setSpacing(8)
        for widget in (
            self.loader_setting_label,
            self.loader_setting_combo,
            self.memory_min_label,
            self.memory_min_input,
            self.memory_max_label,
            self.memory_max_input,
            self.memory_hint_label,
            self.skin_label,
            self.skin_status_label,
            self.skin_browse_button,
            self.skin_url_label,
            self.skin_url_input,
            self.skin_url_button,
        ):
            settings_layout.addWidget(widget)
        settings_layout.addStretch()
        self.settings_scroll_area.setWidget(self.settings_container)
        info_layout.addWidget(self.admin_unlock_button)
        info_layout.addWidget(self.settings_scroll_area, 1)
        self.settings_widgets = [self.settings_scroll_area]
        self.launch_settings_widgets = [
            self.memory_min_label,
            self.memory_min_input,
            self.memory_max_label,
            self.memory_max_input,
            self.memory_hint_label,
        ]
        self.player_widgets = [
            self.skin_label,
            self.skin_status_label,
            self.skin_browse_button,
            self.skin_url_label,
            self.skin_url_input,
            self.skin_url_button,
        ]
        info_layout.addStretch()
        self.info_panel.setMinimumWidth(390)
        self.info_panel.setMaximumWidth(430)
        self.info_panel.setMinimumHeight(220)

        self.news_frame = QFrame()
        self.news_frame.setObjectName("newsFrame")
        news_layout = QVBoxLayout(self.news_frame)
        news_layout.setContentsMargins(20, 16, 20, 16)
        news_layout.setSpacing(8)
        self.news_title_label = QLabel()
        self.news_title_label.setObjectName("newsTitle")
        self.news_body_label = QLabel()
        self.news_body_label.setObjectName("newsBody")
        self.news_body_label.setWordWrap(True)
        self.news_counter_label = QLabel()
        self.news_counter_label.setObjectName("newsCounter")
        news_layout.addWidget(self.news_title_label)
        news_layout.addWidget(self.news_body_label)
        news_layout.addWidget(self.news_counter_label)
        self.news_frame.setMinimumWidth(260)
        self.news_frame.setMaximumWidth(330)

        self.update_mascot_frame = QFrame()
        self.update_mascot_frame.setObjectName("updateMascot")
        self.update_mascot_frame.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.update_mascot_frame.installEventFilter(self)
        mascot_layout = QVBoxLayout(self.update_mascot_frame)
        mascot_layout.setContentsMargins(14, 10, 14, 12)
        mascot_layout.setSpacing(4)
        self.update_mascot_title = QLabel(self.translate("update_mascot_found"))
        self.update_mascot_title.setObjectName("updateMascotTitle")
        self.update_mascot_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_mascot_gif = QLabel()
        self.update_mascot_gif.setObjectName("updateMascotGif")
        self.update_mascot_gif.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.update_mascot_movie: QMovie | None = None
        if UPDATE_MASCOT_PATH.is_file():
            self.update_mascot_movie = QMovie(str(UPDATE_MASCOT_PATH))
            self.update_mascot_movie.setScaledSize(QSize(150, 116))
            self.update_mascot_gif.setMovie(self.update_mascot_movie)
            self.update_mascot_movie.start()
        else:
            self.update_mascot_gif.setText("!")
        mascot_layout.addWidget(self.update_mascot_title)
        mascot_layout.addWidget(self.update_mascot_gif)
        self.update_mascot_frame.setFixedSize(196, 166)
        self.update_mascot_frame.hide()

        self.mascot_picker_frame = QFrame()
        self.mascot_picker_frame.setObjectName("mascotPicker")
        self.mascot_picker_frame.installEventFilter(self)
        mascot_picker_layout = QHBoxLayout(self.mascot_picker_frame)
        mascot_picker_layout.setContentsMargins(8, 8, 8, 8)
        mascot_picker_layout.setSpacing(6)
        self.mascot_choice_buttons: list[QPushButton] = []
        for index, mascot_path in enumerate(self.mascot_paths):
            button = self.create_mascot_choice_button(mascot_path, index)
            button.clicked.connect(lambda checked=False, choice=index: self.select_floating_mascot(choice))
            self.mascot_choice_buttons.append(button)
            mascot_picker_layout.addWidget(button)
        self.mascot_picker_frame.hide()

        stage_layout = QHBoxLayout()
        stage_layout.setSpacing(18)
        stage_layout.addWidget(self.sidebar_frame, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        stage_layout.addWidget(self.mascot_picker_frame, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        stage_layout.addWidget(self.news_frame, 0, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        stage_layout.addStretch(1)
        stage_layout.addWidget(self.update_mascot_frame, 0, Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)
        stage_layout.addStretch(1)
        stage_layout.addWidget(self.info_panel, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        hero_layout.addLayout(stage_layout, 1)

        control_frame = QFrame()
        control_frame.setObjectName("controlFrame")
        control_frame.setMinimumHeight(116)
        control_frame.setMaximumHeight(120)
        outer_control_layout = QVBoxLayout(control_frame)
        outer_control_layout.setContentsMargins(8, 10, 8, 10)
        outer_control_layout.setSpacing(0)
        control_layout = QHBoxLayout()
        control_layout.setContentsMargins(0, 0, 0, 0)
        control_layout.setSpacing(3)

        self.language_label = QLabel()
        self.language_combo = QComboBox()
        self.language_combo.addItems(["EN", "RU"])
        self.language_combo.setCurrentText(self.language)

        self.profile_label = QLabel()
        self.profile_combo = QComboBox()
        self.populate_profiles()

        self.username_label, self.username_label_text = self.create_control_label("user")
        self.username_input = QComboBox()
        self.username_input.setEditable(True)
        self.username_input.setMaxVisibleItems(5)
        self.populate_usernames()
        username_field = QFrame()
        username_field.setObjectName("inlineFieldFrame")
        username_field.setFixedHeight(38)
        username_field_layout = QHBoxLayout(username_field)
        username_field_layout.setContentsMargins(0, 0, 0, 0)
        username_field_layout.setSpacing(0)
        self.add_username_button = QPushButton("+")
        self.add_username_button.setObjectName("labelActionButton")
        self.add_username_button.setFixedSize(22, 20)
        self.add_username_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.skin_quick_button = QPushButton()
        self.skin_quick_button.setObjectName("labelActionButton")
        self.skin_quick_button.setFixedSize(22, 20)
        self.skin_quick_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        skin_icon_path = ICON_DIR / "skin.svg"
        if skin_icon_path.is_file():
            self.skin_quick_button.setIcon(QIcon(str(skin_icon_path)))
            self.skin_quick_button.setIconSize(QSize(14, 14))
        username_field_layout.addWidget(self.username_input, 1)
        self.add_label_actions(self.username_label, self.add_username_button, self.skin_quick_button)

        self.build_label, self.build_label_text = self.create_control_label("build")
        self.build_combo = QComboBox()
        self.build_combo.setEditable(True)
        self.build_combo.setMinimumWidth(176)
        self.populate_builds()
        build_field = QFrame()
        build_field.setObjectName("inlineFieldFrame")
        build_field.setFixedHeight(38)
        build_field_layout = QHBoxLayout(build_field)
        build_field_layout.setContentsMargins(0, 0, 0, 0)
        build_field_layout.setSpacing(0)
        self.add_build_button = QPushButton("+")
        self.add_build_button.setObjectName("labelActionButton")
        self.add_build_button.setFixedSize(22, 20)
        self.add_build_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        build_field_layout.addWidget(self.build_combo, 1)
        self.add_label_actions(self.build_label, self.add_build_button)

        self.version_label, self.version_label_text = self.create_control_label("version")
        self.version_combo = QComboBox()

        self.loader_label, self.loader_label_text = self.create_control_label("loader")
        self.loader_combo = QComboBox()
        self.loader_combo.addItems(["vanilla", "fabric"])
        self.loader_combo.setCurrentText(self.loader_setting_combo.currentText())

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(8)
        self.progress_bar.setMinimumWidth(118)
        self.progress_bar.setMaximumWidth(132)

        self.status_label = QLabel()
        self.status_label.setObjectName("statusLabel")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setMinimumHeight(18)
        self.status_label.setMinimumWidth(120)
        self.status_label.setMaximumWidth(204)

        self.play_button = QPushButton()
        self.play_button.setObjectName("playButton")
        self.play_button.setFixedHeight(38)
        self.play_button.setMinimumWidth(132)
        self.play_button.setMaximumWidth(140)
        self.play_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.mods_button = QPushButton()
        self.mods_button.setObjectName("modsButton")
        self.mods_button.setFixedHeight(38)
        self.mods_button.setMinimumWidth(204)
        self.mods_button.setMaximumWidth(212)
        self.mods_button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.set_button_icon(self.play_button, "play", 22)
        self.set_button_icon(self.mods_button, self.get_mods_action_key(), 21)

        self.feedback_button = QPushButton()
        self.feedback_button.setObjectName("panelButton")
        self.feedback_button.setMinimumHeight(34)

        username_group = self.create_control_group(self.username_label, username_field)
        self.build_group = self.create_control_group(self.build_label, build_field)
        self.version_group = self.create_control_group(self.version_label, self.version_combo)
        username_group.setMinimumWidth(204)
        username_group.setMaximumWidth(268)
        self.build_group.setMinimumWidth(168)
        self.build_group.setMaximumWidth(190)
        self.version_group.setMinimumWidth(90)
        self.version_group.setMaximumWidth(100)
        loader_group = self.create_control_group(self.loader_label, self.loader_combo)
        loader_group.setMinimumWidth(118)
        loader_group.setMaximumWidth(132)
        mods_group = QFrame()
        mods_group.setObjectName("controlGroup")
        mods_group.setFixedHeight(106)
        mods_layout = QVBoxLayout(mods_group)
        mods_layout.setContentsMargins(0, 0, 0, 0)
        mods_layout.setSpacing(3)
        mods_label_spacer = QLabel(" ")
        mods_layout.addWidget(mods_label_spacer)
        mods_layout.addWidget(self.mods_button)
        mods_layout.addWidget(self.status_label, 0, Qt.AlignmentFlag.AlignHCenter)
        mods_group.setMinimumWidth(204)
        mods_group.setMaximumWidth(212)
        play_group = QFrame()
        play_group.setObjectName("controlGroup")
        play_group.setFixedHeight(106)
        play_layout = QVBoxLayout(play_group)
        play_layout.setContentsMargins(0, 0, 0, 0)
        play_layout.setSpacing(3)
        play_layout.addWidget(QLabel(" "))
        play_layout.addWidget(self.play_button)
        progress_slot = QFrame()
        progress_slot.setObjectName("progressSlot")
        progress_slot_layout = QVBoxLayout(progress_slot)
        progress_slot_layout.setContentsMargins(0, 6, 0, 6)
        progress_slot_layout.setSpacing(0)
        progress_slot_layout.addWidget(self.progress_bar, 0, Qt.AlignmentFlag.AlignHCenter)
        play_layout.addWidget(progress_slot)
        play_group.setMinimumWidth(132)
        play_group.setMaximumWidth(140)
        control_layout.addWidget(username_group, 2)
        control_layout.addWidget(self.create_control_separator(), 0)
        control_layout.addWidget(self.build_group, 2)
        control_layout.addWidget(self.create_control_separator(), 0)
        control_layout.addWidget(self.version_group, 2)
        control_layout.addWidget(self.create_control_separator(), 0)
        control_layout.addWidget(loader_group, 2)
        control_layout.addWidget(self.create_control_separator(), 0)
        control_layout.addWidget(mods_group, 0)
        control_layout.addWidget(play_group, 0)
        outer_control_layout.addLayout(control_layout, 1)

        hidden_controls = QFrame()
        hidden_controls.hide()
        hidden_layout = QVBoxLayout(hidden_controls)
        hidden_layout.addWidget(self.profile_label)
        hidden_layout.addWidget(self.profile_combo)
        hidden_layout.addWidget(self.language_label)
        hidden_layout.addWidget(self.language_combo)
        hidden_layout.addWidget(self.feedback_button)
        hero_layout.addWidget(hidden_controls)

        for widget, minimum_width in (
            (self.username_input, 82),
            (self.profile_combo, 106),
            (self.build_combo, 176),
            (self.version_combo, 86),
            (self.loader_combo, 122),
            (self.language_combo, 106),
        ):
            widget.setMinimumWidth(minimum_width)
            widget.setFixedHeight(38)

        hero_layout.addWidget(control_frame, 0)
        root_layout.addWidget(hero_frame, 1)

        self.setCentralWidget(central_widget)
        self.setMinimumSize(960, 540)
        self.resize(1280, 720)
        self.apply_styles()

    def create_project_tab(self, badge: str, label: str) -> QPushButton:
        button = QPushButton(f"{badge}  {label}")
        button.setObjectName("projectTab")
        button.setProperty("badge", badge)
        button.setProperty("label", label)
        button.setFixedSize(52, 46)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return button

    def set_button_icon(self, button: QPushButton, icon_key: str, size: int = 22) -> None:
        icon_file = ACTION_ICON_FILES.get(icon_key)
        icon_path = ICON_DIR / icon_file if icon_file else Path()
        if icon_path.is_file():
            button.setIcon(QIcon(str(icon_path)))
            button.setIconSize(QSize(size, size))
        else:
            button.setIcon(QIcon())

    def get_project_icon_path(self, project_key: str) -> Path:
        icon_name = PROJECT_ICON_FILES.get(project_key, PROJECT_ICON_FILES[CLIENT_MODE_INDEPENDENT])
        return PROJECT_ICON_DIR / icon_name

    def create_control_label(self, icon_name: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("controlLabelFrame")
        frame.setFixedHeight(22)
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        icon_label = QLabel()
        icon_label.setObjectName("controlLabelIcon")
        icon_label.setFixedSize(14, 14)
        icon_path = ICON_DIR / f"{icon_name}.svg"
        if icon_path.is_file():
            icon_label.setPixmap(QIcon(str(icon_path)).pixmap(QSize(14, 14)))
        text_label = QLabel()
        text_label.setObjectName("controlLabelText")
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(text_label, 0, Qt.AlignmentFlag.AlignVCenter)
        return frame, text_label

    def add_label_actions(self, label_frame: QFrame, *buttons: QPushButton) -> None:
        layout = label_frame.layout()
        if layout is None:
            return
        layout.addSpacing(6)
        for button in buttons:
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignVCenter)

    def create_control_group(self, label: QWidget, field: QWidget) -> QFrame:
        frame = QFrame()
        frame.setObjectName("controlGroup")
        frame.setFixedHeight(62)
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(label)
        layout.addWidget(field)
        return frame

    def create_control_separator(self) -> QFrame:
        separator = QFrame()
        separator.setObjectName("controlSeparator")
        separator.setFixedSize(1, 46)
        return separator

    def create_status_row(self, glyph: str, title: str, body: str) -> tuple[QLabel, QLabel, QFrame, QFrame]:
        row = QFrame()
        row.setObjectName("statusRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(1)
        title_label = QLabel(title)
        title_label.setObjectName("statusTitle")
        body_label = QLabel(body)
        body_label.setObjectName("statusBody")
        body_label.setWordWrap(True)
        text_layout.addWidget(title_label)
        text_layout.addWidget(body_label)
        check = StatusGlyph("check", 32)
        layout.addLayout(text_layout, 1)
        layout.addWidget(check)
        return title_label, body_label, check, row

    def create_side_button(self, icon_name: str, fallback_text: str = "") -> QPushButton:
        button = QPushButton()
        button.setObjectName("sideButton")
        icon_path = ICON_DIR / f"{icon_name}.svg"
        if icon_path.is_file():
            button.setIcon(QIcon(str(icon_path)))
            button.setIconSize(QSize(22, 22))
        else:
            button.setText(fallback_text or icon_name[:2].upper())
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        return button

    def create_mascot_choice_button(self, mascot_path: Path, index: int) -> QPushButton:
        button = QPushButton()
        button.setObjectName("mascotChoice")
        button.setFixedSize(54, 54)
        button.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        button.setToolTip(f"Mascot {index + 1}")
        movie = QMovie(str(mascot_path))
        movie.jumpToFrame(0)
        pixmap = movie.currentPixmap()
        if not pixmap.isNull():
            button.setIcon(QIcon(pixmap))
            button.setIconSize(QSize(38, 38))
        else:
            button.setText(str(index + 1))
        return button

    def _connect_signals(self) -> None:
        self.language_combo.currentTextChanged.connect(self.change_language)
        self.profile_combo.currentIndexChanged.connect(self.on_profile_changed)
        self.build_combo.currentIndexChanged.connect(self.on_build_changed)
        self.mslaunch_tab.clicked.connect(lambda: self.handle_project_tab(CLIENT_MODE_INDEPENDENT))
        self.nukem_tab.clicked.connect(lambda: self.handle_project_tab(CLIENT_MODE_NUKEM))
        self.vibecraft_tab.clicked.connect(lambda: self.handle_project_tab("vibecraft"))
        self.language_toggle_button.clicked.connect(self.toggle_language)
        self.update_check_button.clicked.connect(self.manual_check_launcher_update)
        self.minimize_button.clicked.connect(self.showMinimized)
        self.size_toggle_button.clicked.connect(self.toggle_window_size)
        self.close_button.clicked.connect(self.close)
        self.mode_button.clicked.connect(self.toggle_client_mode)
        self.play_button.clicked.connect(self.check_mods_and_play)
        self.mods_button.clicked.connect(self.check_mods_only)
        self.feedback_button.clicked.connect(self.show_feedback_panel)
        self.open_profile_button.clicked.connect(self.open_current_profile_folder)
        self.open_game_button.clicked.connect(self.open_profiles_root_folder)
        self.open_crash_reports_button.clicked.connect(self.handle_panel_report_action)
        self.download_update_button.clicked.connect(self.open_launcher_update_url)
        self.open_modpack_repo_button.clicked.connect(self.open_modpack_repo)
        self.open_modpack_manifest_button.clicked.connect(self.open_modpack_manifest)
        self.open_support_queue_button.clicked.connect(self.open_support_queue)
        self.admin_news_button.clicked.connect(self.open_modpack_repo)
        self.admin_builds_button.clicked.connect(self.open_modpack_manifest)
        self.admin_password_button.clicked.connect(self.open_support_queue)
        self.admin_unlock_button.clicked.connect(self.request_admin_access)
        self.java_browse_button.clicked.connect(self.browse_java_path)
        self.skin_browse_button.clicked.connect(self.browse_skin_file)
        self.skin_url_button.clicked.connect(self.save_skin_url)
        self.skin_quick_button.clicked.connect(self.show_player_panel)
        self.add_username_button.clicked.connect(self.add_local_username)
        self.add_build_button.clicked.connect(self.add_local_build)
        self.loader_setting_combo.currentTextChanged.connect(lambda *_: self.save_user_preferences())
        self.loader_setting_combo.currentTextChanged.connect(self.sync_loader_segments)
        self.loader_combo.currentTextChanged.connect(self.set_loader_mode)
        self.memory_min_input.valueChanged.connect(self.on_memory_setting_changed)
        self.memory_max_input.valueChanged.connect(self.on_memory_setting_changed)
        self.java_path_input.editingFinished.connect(self.save_user_preferences)
        self.username_input.editTextChanged.connect(lambda *_: self.save_user_preferences())

    def change_language(self, language: str) -> None:
        if language in TRANSLATIONS:
            self.language = language
            self.apply_translations()
            self.save_user_preferences()

    def eventFilter(self, watched: object, event: QEvent) -> bool:
        if watched is getattr(self, "update_mascot_frame", None) and event.type() == QEvent.Type.Enter:
            self.update_mascot_dismissed = True
            self.refresh_update_mascot()
            return True
        if watched in (getattr(self, "mascot_button", None), getattr(self, "mascot_picker_frame", None)):
            if event.type() == QEvent.Type.Enter:
                self.show_mascot_picker()
            elif event.type() == QEvent.Type.Leave:
                QTimer.singleShot(120, self.hide_mascot_picker_if_cursor_left)
        return super().eventFilter(watched, event)

    def collapse_project_switcher_if_cursor_left(self) -> None:
        if not self.project_switcher_expanded:
            return
        local_cursor = self.project_switcher.mapFromGlobal(QCursor.pos())
        if self.project_switcher.rect().contains(local_cursor):
            return
        self.collapse_project_switcher()

    def collapse_project_switcher(self) -> None:
        if not self.project_switcher_expanded:
            return
        self.project_switcher_expanded = False
        self.update_project_tabs()

    def toggle_window_size(self) -> None:
        self.large_window_enabled = not self.large_window_enabled
        if self.large_window_enabled:
            screen_geometry = self.screen().availableGeometry() if self.screen() else self.geometry()
            width = min(1600, max(1280, screen_geometry.width() - 80))
            height = min(900, max(720, screen_geometry.height() - 80))
            self.resize(width, height)
            self.size_toggle_button.setText("\u25a3")
        else:
            self.resize(1280, 720)
            self.size_toggle_button.setText("\u25a1")
        self.center_on_screen()

    def center_on_screen(self) -> None:
        screen_geometry = self.screen().availableGeometry() if self.screen() else None
        if screen_geometry is None:
            return
        frame = self.frameGeometry()
        frame.moveCenter(screen_geometry.center())
        self.move(frame.topLeft())

    def show_mascot_picker(self) -> None:
        if not self.mascot_choice_buttons:
            return
        self.mascot_picker_frame.show()

    def hide_mascot_picker_if_cursor_left(self) -> None:
        if not hasattr(self, "mascot_picker_frame"):
            return
        cursor_position = QCursor.pos()
        for widget in (self.mascot_button, self.mascot_picker_frame):
            local_position = widget.mapFromGlobal(cursor_position)
            if widget.rect().contains(local_position):
                return
        self.mascot_picker_frame.hide()

    def setup_tray_icon(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(self)
        if APP_ICON_PATH.is_file():
            self.tray_icon.setIcon(QIcon(str(APP_ICON_PATH)))
        else:
            self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip(APP_DISPLAY_NAME)
        menu = QMenu()
        restore_action = QAction("Open MSLaunch", self)
        restore_action.triggered.connect(self.restore_launcher_from_tray)
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(self.close)
        menu.addAction(restore_action)
        menu.addAction(quit_action)
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.restore_launcher_from_tray()

    def restore_launcher_from_tray(self) -> None:
        self.hidden_to_tray_for_game = False
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def hide_launcher_to_tray_for_game(self) -> None:
        if self.tray_icon is None:
            self.showMinimized()
            return
        self.hidden_to_tray_for_game = True
        self.hide()

    def get_or_create_mascot_window(self) -> MascotWindow:
        if not MASCOT_FEATURE_ENABLED:
            raise RuntimeError("Mascot feature is temporarily disabled")
        if self.mascot_window is None:
            self.mascot_window = MascotWindow(self.mascot_paths)
            self.mascot_window.clicked.connect(self.register_floating_mascot_click)
            self.mascot_window.hovered.connect(self.dismiss_floating_mascot_message)
        return self.mascot_window

    def toggle_floating_mascot(self) -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        mascot = self.get_or_create_mascot_window()
        if mascot.isVisible():
            self.mascot_user_enabled = False
            self.floating_mascot_message_active = False
            mascot.set_message("")
            mascot.hide()
            return
        self.mascot_user_enabled = True
        self.show_floating_mascot()

    def register_floating_mascot_click(self) -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        now = time.monotonic()
        self.mascot_click_times = [click for click in self.mascot_click_times if now - click <= 5.0]
        self.mascot_click_times.append(now)
        if len(self.mascot_click_times) < 3:
            return
        self.mascot_click_times.clear()
        self.cycle_floating_mascot()

    def select_floating_mascot(self, index: int) -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        mascot = self.get_or_create_mascot_window()
        mascot.set_mascot_index(index)
        self.mascot_user_enabled = True
        self.show_floating_mascot(mascot.message_label.text())
        if hasattr(self, "mascot_picker_frame"):
            self.mascot_picker_frame.hide()

    def cycle_floating_mascot(self) -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        mascot = self.get_or_create_mascot_window()
        mascot.next_mascot()
        if not mascot.isVisible():
            mascot.show()

    def show_floating_mascot(self, message: str = "") -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        mascot = self.get_or_create_mascot_window()
        self.floating_mascot_message_active = bool(message.strip())
        mascot.set_message(message)
        if not mascot.isVisible():
            screen_geometry = self.screen().availableGeometry() if self.screen() else self.geometry()
            mascot.move(
                screen_geometry.right() - mascot.width() - 72,
                screen_geometry.bottom() - mascot.height() - 86,
            )
        mascot.show()
        mascot.raise_()

    def dismiss_floating_mascot_message(self) -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        if (
            not self.floating_mascot_message_active
            and not self.update_mascot_message_key
            and self.update_check_state != "available"
        ):
            return
        self.update_mascot_dismissed = True
        self.update_mascot_message_key = ""
        self.floating_mascot_message_active = False
        if self.mascot_window is not None:
            self.mascot_window.set_message("")
            if not self.mascot_user_enabled:
                self.mascot_window.hide()

    def show_startup_mascot_notice_if_needed(self) -> None:
        if not MASCOT_FEATURE_ENABLED:
            return
        previous_version = str(self.config.get("last_seen_launcher_version", "")).strip()
        if previous_version == APP_VERSION:
            return
        self.config["last_seen_launcher_version"] = APP_VERSION
        self.save_user_preferences()
        message_key = "mascot_updated" if previous_version else "mascot_welcome"
        self.show_floating_mascot(self.translate(message_key, version=APP_VERSION))

    def toggle_language(self) -> None:
        self.change_language("EN" if self.language == "RU" else "RU")

    def set_loader_mode(self, loader: str) -> None:
        if loader not in ("vanilla", "fabric"):
            return
        if self.loader_setting_combo.currentText() != loader:
            self.loader_setting_combo.setCurrentText(loader)
        self.sync_loader_segments(loader)
        self.save_user_preferences()

    def sync_loader_segments(self, loader: str = "") -> None:
        active_loader = loader or self.loader_setting_combo.currentText().strip() or "vanilla"
        if hasattr(self, "loader_combo") and self.loader_combo.currentText() != active_loader:
            self.loader_combo.setCurrentText(active_loader)

    def memory_setting_to_gb(self, memory_value: str) -> int:
        value = memory_value.strip().upper()
        if value.endswith("G") and value[:-1].isdigit():
            return max(1, int(value[:-1]))
        if value.endswith("M") and value[:-1].isdigit():
            return max(1, round(int(value[:-1]) / 1024))
        return 2

    def on_memory_setting_changed(self) -> None:
        if self.memory_min_input.value() > self.memory_max_input.value():
            sender = self.sender()
            if sender is self.memory_min_input:
                self.memory_max_input.setValue(self.memory_min_input.value())
            else:
                self.memory_min_input.setValue(self.memory_max_input.value())
        self.refresh_memory_hint()
        self.save_user_preferences()

    def refresh_memory_hint(self) -> None:
        if not hasattr(self, "memory_hint_label"):
            return
        max_gb = self.memory_max_input.value()
        if max_gb >= 12:
            risk = "hot"
            hint_key = "memory_hint_hot"
        elif max_gb >= 8:
            risk = "warm"
            hint_key = "memory_hint_warm"
        else:
            risk = "good"
            hint_key = "memory_hint_good"
        for widget in (self.memory_min_input, self.memory_max_input, self.memory_hint_label):
            widget.setProperty("risk", risk)
            widget.style().unpolish(widget)
            widget.style().polish(widget)
        self.memory_hint_label.setText(self.translate(hint_key))

    def handle_project_tab(self, client_mode: str) -> None:
        if client_mode not in CLIENT_MODES:
            self.project_switcher_expanded = False
            self.update_project_tabs()
            return
        if client_mode == self.client_mode:
            self.project_switcher_expanded = not self.project_switcher_expanded
            self.update_project_tabs()
            return
        self.project_switcher_expanded = False
        self.set_client_mode(client_mode)

    def toggle_client_mode(self) -> None:
        next_mode = (
            CLIENT_MODE_NUKEM
            if self.client_mode == CLIENT_MODE_INDEPENDENT
            else CLIENT_MODE_INDEPENDENT
        )
        self.set_client_mode(next_mode)

    def set_client_mode(self, client_mode: str) -> None:
        if client_mode not in CLIENT_MODES or client_mode == self.client_mode:
            self.update_project_tabs()
            return
        self.client_mode = client_mode
        self.project_access_unlocked = False
        self.unlocked_build_ids.clear()
        self.project_switcher_expanded = False
        self.social_links = get_social_links(self.config, self.client_mode)
        self.refresh_project_backgrounds()
        self.refresh_social_buttons()
        self.apply_translations()
        self.save_user_preferences()

    def get_project_background_paths(self) -> list[Path]:
        if self.client_mode == CLIENT_MODE_NUKEM:
            return [
                NUKEM_BACKGROUND_DIR / name
                for name in NUKEM_BACKGROUND_FILES
                if (NUKEM_BACKGROUND_DIR / name).is_file()
            ]
        return [BACKGROUND_DIR / name for name in BACKGROUND_FILES if (BACKGROUND_DIR / name).is_file()]

    def refresh_project_backgrounds(self) -> None:
        self.hero_frame.set_background_files(
            self.get_project_background_paths(),
            slideshow_enabled=self.client_mode == CLIENT_MODE_NUKEM,
        )

    def refresh_social_buttons(self) -> None:
        for button in self.social_buttons:
            button.setParent(None)
            button.deleteLater()
        self.social_buttons = []
        self.admin_button.hide()

        visible_links = self.get_visible_social_links()
        for offset, (link_name, url) in enumerate(visible_links):
            icon_name = SOCIAL_ICON_NAMES.get(link_name, "link")
            fallback_text = SOCIAL_FALLBACK_LABELS.get(link_name, "WB")
            button = self.create_side_button(icon_name, fallback_text)
            button.clicked.connect(lambda checked=False, link=url: self.open_external_link(link))
            button.setVisible(True)
            self.social_buttons.append(button)
            self.sidebar_layout.insertWidget(3 + offset, button)

    def get_visible_social_links(self) -> list[tuple[str, str]]:
        if len(self.social_links) <= 3:
            return list(self.social_links.items())

        direct_links: list[tuple[str, str]] = []
        for key in ("youtube", "discord"):
            url = self.social_links.get(key)
            if url:
                direct_links.append((key, url))

        for key in ("vk_group", "vk", "rutube", "website", "link"):
            url = self.social_links.get(key)
            if url:
                direct_links.append(("link" if key != "vk" else "vk", url))
                break

        return direct_links[:3]

    def get_project_news_items(self) -> list[dict[str, str]]:
        raw_news = self.config.get("news")
        if isinstance(raw_news, dict):
            raw_items = raw_news.get(self.client_mode, raw_news.get("default", []))
        elif isinstance(raw_news, list):
            raw_items = raw_news
        else:
            raw_items = []

        if not isinstance(raw_items, list):
            return []

        items: list[dict[str, str]] = []
        for item in raw_items:
            title = ""
            body = ""
            if isinstance(item, dict):
                title = str(item.get("title", "")).strip()
                body = str(item.get("body", item.get("text", ""))).strip()
            elif isinstance(item, str):
                body = item.strip()
            if body:
                items.append({"title": title or self.translate("news_title"), "body": body})
            if len(items) == 5:
                break
        return items

    def refresh_news_items(self) -> None:
        self.news_items = self.get_project_news_items()
        self.news_index = min(self.news_index, max(len(self.news_items) - 1, 0))
        self.update_news_panel()

    def show_next_news_item(self) -> None:
        if len(self.news_items) <= 1:
            return
        self.news_index = (self.news_index + 1) % len(self.news_items)
        self.update_news_panel()

    def update_news_panel(self) -> None:
        if not self.news_items:
            self.news_title_label.setText(self.translate("news_title"))
            self.news_body_label.setText(self.translate("news_empty"))
            self.news_counter_label.setText("")
        else:
            item = self.news_items[self.news_index]
            self.news_title_label.setText(item["title"])
            self.news_body_label.setText(item["body"])
            self.news_counter_label.setText(f"{self.news_index + 1}/{len(self.news_items)}")
        self.refresh_news_visibility()

    def refresh_news_visibility(self) -> None:
        visible = bool(self.news_items) and self.info_panel_mode in ("status", "help")
        self.news_frame.setVisible(visible)
        if visible and len(self.news_items) > 1:
            if not self.news_timer.isActive():
                self.news_timer.start()
        else:
            self.news_timer.stop()

    def update_project_tabs(self) -> None:
        active_key = self.client_mode if self.client_mode in CLIENT_MODES else CLIENT_MODE_INDEPENDENT
        if self.project_switcher_expanded:
            ordered_keys = (
                (CLIENT_MODE_NUKEM, CLIENT_MODE_INDEPENDENT, "vibecraft")
                if active_key == CLIENT_MODE_INDEPENDENT
                else (CLIENT_MODE_INDEPENDENT, CLIENT_MODE_NUKEM, "vibecraft")
            )
        else:
            ordered_keys = (active_key,)

        for tab in self.project_tabs.values():
            self.project_layout.removeWidget(tab)
        for project_key in ordered_keys:
            self.project_layout.addWidget(self.project_tabs[project_key])

        tab_states = (
            (self.mslaunch_tab, CLIENT_MODE_INDEPENDENT, active_key == CLIENT_MODE_INDEPENDENT),
            (self.nukem_tab, CLIENT_MODE_NUKEM, active_key == CLIENT_MODE_NUKEM),
            (self.vibecraft_tab, "vibecraft", False),
        )
        self.project_switcher.setProperty("expanded", self.project_switcher_expanded)
        self.project_switcher.style().unpolish(self.project_switcher)
        self.project_switcher.style().polish(self.project_switcher)
        active_icon = self.get_project_icon_path(self.client_mode)
        if active_icon.is_file():
            self.logo_label.setPixmap(QPixmap(str(active_icon)))

        for tab, project_key, active in tab_states:
            tab.setProperty("active", active)
            badge = str(tab.property("badge") or "")
            label = str(tab.property("label") or "")
            icon_path = self.get_project_icon_path(project_key)
            if icon_path.is_file():
                tab.setIcon(QIcon(str(icon_path)))
                tab.setIconSize(QSize(30, 30))
            tab.setText(label if self.project_switcher_expanded and active else "")
            tab.setToolTip(label)
            tab.setVisible(project_key in ordered_keys)
            tab.setFixedSize(154 if self.project_switcher_expanded and active else 52, 46)
            tab.style().unpolish(tab)
            tab.style().polish(tab)
            tab.update()

    def get_mode_credit_key(self) -> str:
        return "brand_credit_nukem" if self.client_mode == CLIENT_MODE_NUKEM else "brand_credit"

    def get_mode_subtitle_key(self) -> str:
        return (
            "brand_subtitle_nukem"
            if self.client_mode == CLIENT_MODE_NUKEM
            else "brand_subtitle_independent"
        )

    def get_mods_action_key(self) -> str:
        return "download_mods" if self.client_mode == CLIENT_MODE_NUKEM else "game_folder"

    def apply_translations(self) -> None:
        self.setWindowTitle(self.translate("app_title"))
        self.title_label.setText(self.translate("brand_title"))
        self.subtitle_label.setText(self.translate(self.get_mode_subtitle_key()))
        self.credit_label.setText(self.translate(self.get_mode_credit_key()))
        self.refresh_info_panel()
        self.open_profile_button.setText(self.translate("open_profile"))
        self.open_game_button.setText(self.translate("open_game"))
        self.open_crash_reports_button.setText(self.translate("open_crash_reports"))
        self.download_update_button.setText(self.translate("download_update"))
        self.open_modpack_repo_button.setText(self.translate("open_modpack_repo"))
        self.open_modpack_manifest_button.setText(self.translate("open_modpack_manifest"))
        self.open_support_queue_button.setText(self.translate("open_support_queue"))
        self.admin_news_button.setText(self.translate("admin_create_news"))
        self.admin_builds_button.setText(self.translate("admin_view_builds"))
        self.admin_password_button.setText(self.translate("admin_change_password"))
        self.admin_unlock_button.setText(self.translate("admin_password_open"))
        self.update_mascot_title.setText(self.translate("update_mascot_found"))
        self.update_check_button.setToolTip(self.translate("manual_update_tooltip"))
        self.project_switcher.setToolTip(self.translate("project_switcher_tooltip"))
        self.skin_quick_button.setToolTip(self.translate("skin_button_tooltip"))
        self.add_username_button.setToolTip(self.translate("add_username"))
        self.add_build_button.setToolTip(self.translate("add_build"))
        self.refresh_info_panel()
        self.memory_min_label.setText(self.translate("memory_min"))
        self.memory_max_label.setText(self.translate("memory_max"))
        self.refresh_memory_hint()
        self.java_path_label.setText(self.translate("java_path"))
        self.java_browse_button.setText(self.translate("java_browse"))
        self.skin_label.setText(self.translate("skin"))
        self.skin_browse_button.setText(self.translate("skin_browse"))
        self.skin_url_label.setText(self.translate("skin_url"))
        self.skin_url_button.setText(self.translate("skin_url_apply"))
        self.skin_url_input.setPlaceholderText(self.translate("skin_url_invalid"))
        self.refresh_skin_status()
        self.language_label.setText(self.translate("language"))
        self.profile_label.setText(self.translate("profile"))
        self.refresh_profile_labels()
        self.build_label_text.setText(
            self.translate("build_source_nukem")
            if self.client_mode == CLIENT_MODE_NUKEM
            else self.translate("build_source_local")
        )
        self.build_label_text.setProperty("role", "nukem" if self.client_mode == CLIENT_MODE_NUKEM else "")
        self.build_label_text.style().unpolish(self.build_label_text)
        self.build_label_text.style().polish(self.build_label_text)
        self.username_label_text.setText(self.translate("username"))
        self.version_label_text.setText(self.translate("version"))
        self.loader_label_text.setText(self.translate("loader"))
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.mods_button.setText(self.translate(self.get_mods_action_key()))
        self.refresh_action_button_icons()
        self.feedback_button.setText(self.translate("feedback_ok"))
        self.language_toggle_button.setText(self.language)
        self.refresh_update_check_button()
        self.refresh_nukem_control_policy()
        self.mode_button.setText("NK" if self.client_mode == CLIENT_MODE_INDEPENDENT else "MS")
        self.mode_button.setToolTip(
            self.translate(
                "mode_nukem"
                if self.client_mode == CLIENT_MODE_INDEPENDENT
                else "mode_independent"
            )
        )
        self.update_project_tabs()
        self.refresh_news_items()

        status_key = self.status_label.property("status_key")
        status_detail = self.status_label.property("status_detail")
        if isinstance(status_key, str) and isinstance(status_detail, str):
            self.set_status_detail(status_key, status_detail)
        elif isinstance(status_key, str):
            self.set_status(status_key)
        else:
            self.set_status("ready")

    def refresh_action_button_icons(self) -> None:
        self.set_button_icon(self.play_button, "play", 19)
        self.set_button_icon(self.mods_button, self.get_mods_action_key(), 18)

    def apply_styles(self) -> None:
        stylesheet = (
            """
            QMainWindow {
                background: #030607;
                font-family: "Segoe UI", "Arial";
            }
            #heroFrame {
                background: #030607;
                border: 0;
            }
            #brandLockup {
                background: transparent;
                border: 0;
            }
            #logoBadge {
                color: #dffcf0;
                border: 2px solid rgba(116, 231, 186, 190);
                border-radius: 8px;
                font-size: 20px;
                font-weight: 900;
            }
            #brandIcon {
                background: transparent;
                border: 0;
            }
            #projectSwitcher {
                background: transparent;
                border: 0;
            }
            #projectSwitcher[expanded="true"] {
                background: transparent;
                border: 0;
            }
            #windowControls {
                background: transparent;
                border: 0;
            }
            #topRightControls {
                background: transparent;
                border: 0;
            }
            QPushButton#windowButton {
                background: rgba(8, 11, 15, 70);
                color: rgba(255, 255, 255, 168);
                border: 1px solid rgba(93, 202, 235, 24);
                border-radius: 8px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton#windowButton:hover {
                background: rgba(93, 202, 235, 18);
                color: #ffffff;
            }
            #sidebarFrame {
                background: rgba(8, 10, 12, 148);
                border: 1px solid rgba(255, 255, 255, 30);
                border-radius: 8px;
                min-width: 64px;
                max-width: 64px;
            }
            #mascotPicker {
                background: rgba(8, 11, 15, 168);
                border: 1px solid rgba(116, 231, 186, 46);
                border-radius: 8px;
            }
            QPushButton#mascotChoice {
                background: rgba(255, 255, 255, 12);
                border: 1px solid rgba(255, 255, 255, 24);
                border-radius: 8px;
                padding: 3px;
                color: #ffffff;
                font-weight: 800;
            }
            QPushButton#mascotChoice:hover {
                background: rgba(116, 231, 186, 28);
                border: 1px solid rgba(116, 231, 186, 120);
            }
            #newsFrame {
                background: rgba(7, 10, 11, 128);
                border: 1px solid rgba(116, 231, 186, 42);
                border-radius: 8px;
            }
            #newsTitle {
                color: #9ff4cf;
                font-size: 15px;
                font-weight: 800;
            }
            #newsBody {
                color: #f3f6f2;
                font-size: 13px;
                line-height: 120%;
            }
            #newsCounter {
                color: rgba(255, 255, 255, 130);
                font-size: 11px;
            }
            #updateMascot {
                background: rgba(8, 11, 15, 120);
                border: 1px solid rgba(116, 231, 186, 68);
                border-radius: 10px;
            }
            #updateMascotTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 900;
            }
            #updateMascotGif {
                background: transparent;
                border: 0;
                color: #9ff4cf;
                font-size: 34px;
                font-weight: 900;
            }
            #floatingMascot,
            #floatingMascotMessage {
                background: transparent;
                border: 0;
            }
            #floatingMascotMessage {
                color: #ffffff;
                font-size: 22px;
                font-weight: 900;
                padding: 0 6px 6px 6px;
            }
            #infoPanel {
                background: rgba(10, 10, 10, 182);
                border: 1px solid rgba(255, 255, 255, 36);
                border-radius: 8px;
            }
            #settingsScrollArea,
            #settingsScrollArea QWidget,
            #settingsContainer {
                background: transparent;
                border: 0;
            }
            #settingsScrollArea QScrollBar:vertical {
                background: rgba(255, 255, 255, 16);
                width: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            #settingsScrollArea QScrollBar::handle:vertical {
                background: rgba(116, 231, 186, 90);
                border-radius: 4px;
            }
            #settingsScrollArea QScrollBar::add-line:vertical,
            #settingsScrollArea QScrollBar::sub-line:vertical {
                height: 0;
            }
            #controlFrame {
                background: rgba(7, 10, 11, 164);
                border: 1px solid rgba(255, 255, 255, 28);
                border-radius: 8px;
            }
            #controlFrame QLineEdit,
            #controlFrame QComboBox {
                font-size: 13px;
                padding-left: 9px;
                padding-right: 24px;
            }
            #controlFrame QLabel {
                color: rgba(255, 255, 255, 190);
                font-size: 11px;
                font-weight: 700;
            }
            #controlLabelFrame {
                background: transparent;
                border: 0;
            }
            #controlLabelIcon {
                background: transparent;
                border: 0;
            }
            #controlLabelText {
                color: rgba(255, 255, 255, 205);
                font-size: 11px;
                font-weight: 800;
            }
            QLabel#controlLabelText[role="nukem"] {
                color: #bdf7ff;
                font-weight: 900;
            }
            #fieldActions {
                background: transparent;
                border: 0;
            }
            QPushButton#labelActionButton {
                background: rgba(93, 202, 235, 12);
                color: #eafcff;
                border: 1px solid rgba(93, 202, 235, 58);
                border-radius: 6px;
                font-size: 10px;
                font-weight: 800;
                padding: 0;
            }
            QPushButton#labelActionButton:hover {
                background: rgba(93, 202, 235, 30);
                border: 1px solid rgba(93, 202, 235, 120);
            }
            #controlSeparator {
                background: rgba(255, 255, 255, 34);
                border: 0;
            }
            QLabel {
                color: #f3f6f2;
                font-size: 14px;
            }
            #titleLabel {
                color: #ffffff;
                font-size: 28px;
                font-weight: 800;
            }
            #subtitleLabel {
                color: #9ff4cf;
                font-size: 13px;
                font-weight: 700;
            }
            #creditLabel {
                color: #bcc4c1;
                font-size: 12px;
            }
            #infoTitle {
                color: #ffffff;
                font-size: 22px;
                font-weight: 800;
            }
            #infoBody {
                color: #d5d8d5;
                font-size: 14px;
            }
            #statusLabel {
                color: #8ddcf2;
            }
            #statusRow {
                border-bottom: 1px solid rgba(93, 202, 235, 32);
                min-height: 48px;
            }
            #statusIcon {
                color: #5dcaeb;
                background: transparent;
                border: 0;
                border-radius: 8px;
            }
            #statusTitle {
                color: #ffffff;
                font-size: 17px;
                font-weight: 800;
            }
            #statusBody {
                color: #c8ccca;
                font-size: 12px;
            }
            #statusCheck {
                color: #5dcaeb;
                background: transparent;
                border: 0;
                border-radius: 8px;
            }
            QPushButton#projectTab {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(20, 38, 45, 150),
                    stop:0.48 rgba(4, 11, 15, 182),
                    stop:1 rgba(2, 6, 8, 212));
                color: #f3f6f2;
                border: 1px solid rgba(93, 202, 235, 58);
                border-radius: 9px;
                padding: 0 8px;
                text-align: left;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton#projectTab:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(35, 76, 88, 170),
                    stop:0.50 rgba(5, 20, 28, 214),
                    stop:1 rgba(2, 8, 12, 230));
                border: 1px solid rgba(93, 202, 235, 130);
            }
            QPushButton#projectTab[active="true"] {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgba(27, 62, 73, 175),
                    stop:0.46 rgba(4, 16, 22, 220),
                    stop:1 rgba(2, 8, 12, 238));
                border: 1px solid rgba(93, 202, 235, 112);
                color: #ffffff;
            }
            QPushButton#projectTab:disabled {
                color: rgba(255, 255, 255, 118);
                background: rgba(6, 10, 12, 118);
                border: 1px solid rgba(255, 255, 255, 24);
            }
            QPushButton#languageToggle {
                background: rgba(8, 11, 15, 120);
                color: #d8f7ff;
                border: 1px solid rgba(93, 202, 235, 46);
                border-radius: 8px;
                font-size: 12px;
                font-weight: 800;
            }
            QPushButton#languageToggle:hover {
                background: rgba(93, 202, 235, 22);
                border: 1px solid rgba(93, 202, 235, 100);
            }
            QPushButton#updateCheckButton {
                background: rgba(8, 11, 15, 122);
                color: #8ddcf2;
                border: 1px solid rgba(93, 202, 235, 58);
                border-radius: 8px;
                font-size: 11px;
                font-weight: 900;
            }
            QPushButton#updateCheckButton[state="checking"] {
                color: #ffffff;
                border: 1px solid rgba(116, 231, 186, 140);
            }
            QPushButton#updateCheckButton[state="available"] {
                color: #ff3b30;
                background: rgba(30, 18, 4, 210);
                border: 2px solid #ffd45c;
            }
            QPushButton#updateCheckButton[state="available"][pulse="true"] {
                background: rgba(82, 43, 8, 235);
                border: 2px solid #ffe88a;
            }
            QPushButton#updateCheckButton[state="error"] {
                color: #ff8d7f;
                border: 1px solid rgba(255, 120, 96, 150);
            }
            QPushButton#sideButton {
                background: rgba(255, 255, 255, 14);
                color: #f3f6f2;
                border: 1px solid rgba(255, 255, 255, 26);
                border-radius: 8px;
                min-width: 44px;
                min-height: 44px;
                max-width: 44px;
                max-height: 44px;
                font-size: 13px;
                font-weight: 800;
            }
            QPushButton#sideButton:hover {
                background: rgba(116, 231, 186, 44);
                color: #ffffff;
                border: 1px solid rgba(116, 231, 186, 130);
            }
            QPushButton#sideButton[role="report"] {
                background: rgba(7, 18, 26, 188);
                border: 1px solid rgba(93, 202, 235, 82);
            }
            QPushButton#sideButton[role="report"]:hover {
                background: rgba(12, 34, 48, 224);
                border: 1px solid rgba(255, 211, 138, 150);
            }
            QPushButton#panelButton {
                background: rgba(255, 255, 255, 20);
                color: #f3f6f2;
                border: 1px solid rgba(255, 255, 255, 36);
                border-radius: 8px;
                min-height: 32px;
                padding: 7px 12px;
                font-size: 13px;
                font-weight: 700;
                text-align: left;
            }
            QPushButton#panelButton:hover {
                background: rgba(116, 231, 186, 36);
                border: 1px solid rgba(116, 231, 186, 110);
            }
            #inlineFieldFrame {
                background: transparent;
                border: 0;
            }
            QPushButton#miniIconButton {
                background: rgba(93, 202, 235, 10);
                color: #f3f6f2;
                border: 1px solid rgba(93, 202, 235, 44);
                border-radius: 8px;
            }
            QPushButton#miniIconButton:hover {
                background: rgba(93, 202, 235, 24);
                border: 1px solid rgba(93, 202, 235, 100);
            }
            QLineEdit,
            QComboBox,
            QSpinBox {
                background: rgba(3, 7, 9, 156);
                color: #ffffff;
                border: 1px solid rgba(93, 202, 235, 36);
                border-radius: 8px;
                padding: 4px 8px;
                min-height: 28px;
                max-height: 38px;
                font-size: 13px;
            }
            QLineEdit:focus,
            QComboBox:focus,
            QSpinBox:focus {
                border: 1px solid #74e7ba;
            }
            QSpinBox#memorySpin[risk="good"] {
                border: 1px solid rgba(93, 202, 235, 132);
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 rgba(5, 18, 24, 190),
                    stop:0.55 rgba(3, 9, 13, 172),
                    stop:1 rgba(6, 34, 42, 210));
            }
            QSpinBox#memorySpin[risk="warm"] {
                border: 1px solid rgba(255, 179, 71, 150);
                background: rgba(44, 25, 7, 170);
            }
            QSpinBox#memorySpin[risk="hot"] {
                border: 1px solid rgba(255, 78, 70, 180);
                background: rgba(48, 8, 8, 190);
            }
            QLabel#memoryHint {
                color: #8ddcf2;
                font-size: 12px;
                font-weight: 800;
            }
            QLabel#memoryHint[risk="good"] {
                color: #a9f4ff;
            }
            QLabel#memoryHint[risk="warm"] {
                color: #ffbf73;
            }
            QLabel#memoryHint[risk="hot"] {
                color: #ff756e;
            }
            QSpinBox#memorySpin {
                padding-right: 34px;
            }
            QSpinBox#memorySpin::up-button,
            QSpinBox#memorySpin::down-button {
                subcontrol-origin: border;
                width: 28px;
                background: rgba(93, 202, 235, 16);
                border-left: 1px solid rgba(93, 202, 235, 42);
            }
            QSpinBox#memorySpin::up-button {
                subcontrol-position: top right;
                border-top-right-radius: 8px;
            }
            QSpinBox#memorySpin::down-button {
                subcontrol-position: bottom right;
                border-bottom-right-radius: 8px;
            }
            QSpinBox#memorySpin::up-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #5dcaeb;
            }
            QSpinBox#memorySpin::down-arrow {
                image: none;
                width: 0;
                height: 0;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #5dcaeb;
            }
            QComboBox::drop-down {
                border: 0;
                width: 24px;
                subcontrol-origin: padding;
                subcontrol-position: top right;
            }
            QComboBox::down-arrow {
                image: url("__CHEVRON_ICON__");
                width: 14px;
                height: 14px;
                margin-right: 7px;
            }
            QComboBox QAbstractItemView {
                background: rgba(3, 7, 9, 245);
                color: #f3f6f2;
                border: 1px solid rgba(93, 202, 235, 90);
                border-radius: 8px;
                padding: 4px;
                outline: 0;
                selection-background-color: rgba(93, 202, 235, 46);
                selection-color: #ffffff;
            }
            QComboBox QAbstractItemView::item {
                min-height: 26px;
                padding: 4px 8px;
                border-radius: 6px;
            }
            QPushButton#playButton,
            QPushButton#modsButton {
                color: #ffffff;
                border-radius: 10px;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0px;
                padding: 4px 10px;
            }
            QPushButton#playButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #ffa22b, stop:1 #ff7d12);
                border: 1px solid #ffc36b;
            }
            QPushButton#playButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f89b22, stop:1 #e87712);
                border: 1px solid rgba(255, 203, 111, 190);
            }
            QPushButton#modsButton {
                background: rgba(6, 17, 24, 188);
                border: 1px solid #3aa3d8;
            }
            QPushButton#modsButton:hover {
                background: rgba(18, 44, 60, 218);
                color: #ffffff;
                border: 1px solid #66c6f2;
            }
            QPushButton#playButton:disabled,
            QPushButton#modsButton:disabled {
                background: rgba(255, 255, 255, 18);
                color: rgba(255, 255, 255, 110);
                border: 1px solid rgba(255, 255, 255, 44);
            }
            QProgressBar {
                background: rgba(255, 255, 255, 24);
                border: 0;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background: #74e7ba;
                border-radius: 4px;
            }
            """
        )
        self.setStyleSheet(stylesheet.replace("__CHEVRON_ICON__", (ICON_DIR / "chevron.svg").as_posix()))

    def populate_profiles(self) -> None:
        self.profile_combo.clear()
        default_profile = self.profile_manager.normalize_profile_id(
            get_config_text(self.config, "default_profile")
        )
        selected_index = 0

        for index, profile_id in enumerate(PROFILE_IDS):
            self.profile_combo.addItem(self.translate(f"profile_{profile_id}"), profile_id)
            if profile_id == default_profile:
                selected_index = index

        self.profile_combo.setCurrentIndex(selected_index)

    def refresh_profile_labels(self) -> None:
        current_profile = self.get_selected_profile_id()
        for index, profile_id in enumerate(PROFILE_IDS):
            self.profile_combo.setItemText(index, self.translate(f"profile_{profile_id}"))
        index = self.profile_combo.findData(current_profile)
        if index >= 0:
            self.profile_combo.setCurrentIndex(index)

    def populate_usernames(self) -> None:
        current_username = get_config_text(self.config, "default_username").strip()
        usernames = self.get_recent_usernames(current_username)
        self.username_input.clear()
        self.username_input.addItems(usernames)
        self.username_input.setCurrentText(current_username)

    def get_current_username(self) -> str:
        return self.username_input.currentText().strip()

    def get_recent_usernames(self, preferred_username: str = "") -> list[str]:
        usernames: list[str] = []
        for username in [preferred_username, *self.recent_usernames]:
            cleaned_username = username.strip()
            if cleaned_username and cleaned_username not in usernames:
                usernames.append(cleaned_username)
        return usernames[:5]

    def add_local_username(self) -> None:
        username, accepted = QInputDialog.getText(
            self,
            self.translate("add_username"),
            self.translate("add_username_prompt"),
            text=self.get_current_username(),
        )
        username = username.strip()
        if not accepted:
            return
        if not username:
            self.show_error(self.translate("empty_username"))
            return
        self.username_input.setCurrentText(username)
        self.recent_usernames = self.get_recent_usernames(username)
        self.config["default_username"] = username
        self.config["recent_usernames"] = self.recent_usernames
        self.populate_usernames()
        self.set_status_text(self.translate("username_saved"))
        self.save_user_preferences()

    def on_profile_changed(self) -> None:
        self.active_profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        self.game_directory = self.active_profile.directory
        self.engine.minecraft_directory = self.game_directory
        self.save_user_preferences()

    def get_selected_profile_id(self) -> str:
        profile_id = self.profile_combo.currentData()
        if isinstance(profile_id, str):
            return self.profile_manager.normalize_profile_id(profile_id)
        return PROFILE_SERVER

    def populate_builds(self) -> None:
        self.build_combo.clear()
        default_build = get_config_text(self.config, "default_build")
        selected_index = 0

        for index, build in enumerate(self.builds):
            build_id = str(build.get("id", "")).strip()
            build_name = str(build.get("name", build_id or "Build")).strip()
            self.build_combo.addItem(build_name, build)
            if build_id and build_id == default_build:
                selected_index = index

        if self.build_combo.count() > 0:
            self.build_combo.setCurrentIndex(selected_index)

    def load_versions(self) -> None:
        self.set_status("loading_versions")
        self.version_combo.clear()
        self.version_combo.setEnabled(False)

        self.versions_worker = VersionsWorker(self.engine)
        self.versions_worker.versions_loaded.connect(self.on_versions_loaded)
        self.versions_worker.error_occurred.connect(self.on_versions_failed)
        self.versions_worker.start()

    def on_versions_loaded(self, versions: list) -> None:
        for version in versions:
            if not isinstance(version, dict):
                continue

            version_id = str(version.get("id", ""))
            if version_id:
                self.version_combo.addItem(version_id)

        self.version_combo.setEnabled(True)
        self.on_build_changed()
        self.refresh_nukem_control_policy()
        self.set_status("ready")

    def on_versions_failed(self, error: str) -> None:
        self.version_combo.setEnabled(True)
        self.refresh_nukem_control_policy()
        user_error = explain_user_error(error, language=self.language, context="versions")
        report_path = self.write_launcher_error_report(user_error, error, "versions")
        self.show_error(self.with_report_path(self.translate("versions_failed", error=user_error), report_path))
        self.set_status("ready")

    def on_build_changed(self) -> None:
        build = self.get_selected_build()
        if build is None:
            return

        configured_version = str(build.get("minecraft_version", "")).strip()
        if not configured_version:
            return

        index = self.version_combo.findText(configured_version)
        if index >= 0:
            self.version_combo.setCurrentIndex(index)
        elif self.client_mode == CLIENT_MODE_NUKEM:
            self.version_combo.addItem(configured_version)
            self.version_combo.setCurrentText(configured_version)

        self.save_user_preferences()
        self.refresh_nukem_control_policy()

    def refresh_nukem_control_policy(self) -> None:
        nukem_locked = self.client_mode == CLIENT_MODE_NUKEM
        if hasattr(self, "build_label_text"):
            self.build_label_text.setText(
                self.translate("build_source_nukem")
                if nukem_locked
                else self.translate("build_source_local")
            )
            self.build_label_text.setProperty("role", "nukem" if nukem_locked else "")
            self.build_label_text.style().unpolish(self.build_label_text)
            self.build_label_text.style().polish(self.build_label_text)
        if nukem_locked:
            self.select_nukem_managed_build()
        self.build_combo.setEnabled(not nukem_locked)
        self.build_combo.setEditable(not nukem_locked)
        if hasattr(self, "add_build_button"):
            self.add_build_button.setVisible(True)
            self.add_build_button.setEnabled(True)
        self.version_combo.setEnabled(not nukem_locked and self.version_combo.count() > 0)
        if hasattr(self, "admin_unlock_button"):
            self.admin_unlock_button.setVisible(
                self.info_panel_mode == "settings"
                and self.client_mode == CLIENT_MODE_NUKEM
                and self.is_admin_access_configured()
            )
        if hasattr(self, "build_group"):
            self.build_group.setToolTip(
                "Build is selected by the Nukem admin panel." if nukem_locked else ""
            )
        if hasattr(self, "version_group"):
            self.version_group.setToolTip(
                "Minecraft version comes from the active Nukem build." if nukem_locked else ""
            )

    def select_nukem_managed_build(self) -> None:
        if self.build_combo.count() <= 0:
            return
        current_data = self.build_combo.currentData()
        if isinstance(current_data, dict) and self.is_nukem_managed_build(current_data):
            return
        for index in range(self.build_combo.count()):
            build = self.build_combo.itemData(index)
            if isinstance(build, dict) and self.is_nukem_managed_build(build):
                with QSignalBlocker(self.build_combo):
                    self.build_combo.setCurrentIndex(index)
                return

    def is_nukem_managed_build(self, build: dict[str, object]) -> bool:
        project = str(build.get("project", "")).strip().lower()
        build_id = str(build.get("id", "")).strip().lower()
        source_key = str(build.get("source_key", "")).strip().lower()
        manifest_url = str(build.get("manifest_url", "")).strip().lower()
        return (
            project == CLIENT_MODE_NUKEM
            or build_id in {CLIENT_MODE_NUKEM, "main-server", "nk-team"}
            or "msnukem" in source_key
            or "msnukem" in manifest_url
        )

    def get_selected_build(self) -> dict[str, object] | None:
        build = self.build_combo.currentData()
        if isinstance(build, dict):
            return build
        build_name = self.build_combo.currentText().strip()
        if build_name and self.client_mode != CLIENT_MODE_NUKEM:
            return {
                "id": build_name,
                "name": build_name,
                "minecraft_version": self.version_combo.currentText().strip(),
                "loader": self.loader_setting_combo.currentText().strip() or "vanilla",
            }
        return None

    def get_selected_build_id(self) -> str:
        build = self.get_selected_build()
        if build is None:
            return ""
        return str(build.get("id", "")).strip()

    def make_local_build_id(self, build_name: str) -> str:
        build_id = []
        previous_dash = False
        for char in build_name.strip().lower():
            if char.isalnum():
                build_id.append(char)
                previous_dash = False
            elif not previous_dash:
                build_id.append("-")
                previous_dash = True
        normalized = "".join(build_id).strip("-")
        return normalized or "local-build"

    def add_local_build(self) -> None:
        if self.client_mode == CLIENT_MODE_NUKEM:
            self.set_client_mode(CLIENT_MODE_INDEPENDENT)
        build_name, accepted = QInputDialog.getText(
            self,
            self.translate("add_build"),
            self.translate("add_build_prompt"),
            text=self.build_combo.currentText().strip(),
        )
        build_name = build_name.strip()
        if not accepted:
            return
        if not build_name:
            self.show_error(self.translate("empty_build"))
            return

        build_id = self.make_local_build_id(build_name)
        build = {
            "id": build_id,
            "name": build_name,
            "minecraft_version": self.version_combo.currentText().strip(),
            "loader": self.loader_setting_combo.currentText().strip() or "vanilla",
            "loader_version": "latest",
            "manifest_url": "",
            "source_key": "",
            "server": "",
            "port": "",
        }
        self.builds = [existing for existing in self.builds if str(existing.get("id", "")).strip() != build_id]
        self.builds.append(build)
        self.config["builds"] = self.builds
        self.config["default_build"] = build_id
        self.populate_builds()
        index = self.build_combo.findData(build)
        if index >= 0:
            self.build_combo.setCurrentIndex(index)
        self.set_status_text(self.translate("build_saved"))
        self.save_user_preferences()

    def get_project_access_config(self) -> dict[str, object]:
        access_config = self.config.get("project_access")
        if not isinstance(access_config, dict):
            return {}
        project_config = access_config.get(self.client_mode)
        return project_config if isinstance(project_config, dict) else {}

    def get_build_access_key(self, build: dict[str, object]) -> str:
        project = str(build.get("project") or self.client_mode).strip() or self.client_mode
        build_id = str(build.get("build_id") or build.get("id") or self.get_selected_build_id()).strip()
        return f"{project}:{build_id}"

    def get_build_access_hash(self, build: dict[str, object]) -> str:
        for key in ("access_hash_sha256", "access_password_hash_sha256", "password_hash_sha256"):
            value = str(build.get(key, "")).strip().lower()
            if value:
                return value

        access_config = self.get_project_access_config()
        build_id = str(build.get("build_id") or build.get("id") or self.get_selected_build_id()).strip()
        build_passwords = access_config.get("build_passwords")
        if isinstance(build_passwords, dict) and build_id:
            value = str(build_passwords.get(build_id, "")).strip().lower()
            if value:
                return value

        if bool(access_config.get("password_enabled", False)):
            return str(access_config.get("password_hash_sha256", "")).strip().lower()
        return ""

    def build_access_required(self, build: dict[str, object]) -> bool:
        raw_required = build.get("access_required")
        if isinstance(raw_required, bool):
            return raw_required
        if str(raw_required).strip().lower() in {"1", "true", "yes", "required"}:
            return True
        if bool(self.get_project_access_config().get("password_enabled", False)):
            return True
        return bool(self.get_build_access_hash(build))

    def get_admin_access_hash(self) -> str:
        value = self.get_project_access_config().get("admin_password_hash_sha256", "")
        return str(value).strip().lower()

    def is_admin_access_configured(self) -> bool:
        return len(self.get_admin_access_hash()) == 64

    def is_admin_password(self, password: str) -> bool:
        expected_hash = self.get_admin_access_hash()
        if not self.is_admin_access_configured():
            return False
        actual_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hmac.compare_digest(actual_hash, expected_hash)

    def get_access_dialog_stylesheet(self) -> str:
        return """
            QDialog#accessDialog {
                background: #081012;
                border: 1px solid rgba(116, 231, 186, 80);
                font-family: "Segoe UI", "Arial";
            }
            QLabel#accessTitle {
                color: #ffffff;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#accessBody {
                color: #d8e0dc;
                font-size: 14px;
            }
            QLineEdit#accessInput {
                background: rgba(0, 0, 0, 150);
                color: #ffffff;
                border: 1px solid rgba(116, 231, 186, 95);
                border-radius: 8px;
                padding: 10px 12px;
                min-height: 38px;
                font-size: 15px;
            }
            QPushButton#accessCancelButton,
            QPushButton#accessDownloadButton {
                border-radius: 8px;
                min-height: 38px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton#accessCancelButton {
                color: rgba(255, 255, 255, 190);
                background: rgba(255, 255, 255, 18);
                border: 1px solid rgba(255, 255, 255, 42);
            }
            QPushButton#accessDownloadButton {
                color: #ffffff;
                background: rgba(12, 38, 52, 230);
                border: 1px solid #46b8ee;
            }
            """

    def request_admin_password(self) -> str | None:
        dialog = QDialog(self)
        dialog.setObjectName("accessDialog")
        dialog.setWindowTitle(self.translate("admin_password_title"))
        dialog.setModal(True)
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel(self.translate("admin_password_title"))
        title.setObjectName("accessTitle")
        body = QLabel(self.translate("admin_password_body"))
        body.setObjectName("accessBody")
        body.setWordWrap(True)
        input_field = QLineEdit()
        input_field.setObjectName("accessInput")
        input_field.setEchoMode(QLineEdit.EchoMode.Password)
        input_field.setPlaceholderText(self.translate("admin_password_title"))

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton(self.translate("cancel_close"))
        cancel_button.setObjectName("accessCancelButton")
        admin_button = QPushButton(self.translate("admin_password_open"))
        admin_button.setObjectName("accessDownloadButton")
        button_row.addWidget(cancel_button)
        button_row.addWidget(admin_button)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(input_field)
        layout.addLayout(button_row)
        dialog.setStyleSheet(self.get_access_dialog_stylesheet())

        cancel_button.clicked.connect(dialog.reject)
        admin_button.clicked.connect(dialog.accept)
        input_field.returnPressed.connect(dialog.accept)
        input_field.setFocus()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return input_field.text()

    def request_admin_access(self, checked: bool = False, *, show_panel: bool = True) -> bool:
        del checked
        if self.admin_access_unlocked:
            if show_panel:
                self.show_admin_panel(require_auth=False)
            return True

        if not self.is_admin_access_configured():
            self.show_error(self.translate("admin_password_disabled"))
            self.set_status("ready")
            return False

        expected_hash = self.get_admin_access_hash()
        if expected_hash:
            password = self.request_admin_password()
            if password is None:
                return False
            if not self.is_admin_password(password):
                self.show_error(self.translate("access_password_failed"))
                return False

        self.admin_access_unlocked = True
        self.set_status("admin_access_granted")
        if show_panel:
            self.show_admin_panel(require_auth=False)
        return True

    def request_build_password(self, build: dict[str, object]) -> str | None:
        build_name = str(build.get("name") or build.get("build_id") or build.get("id") or "Nukem build").strip()
        dialog = QDialog(self)
        dialog.setObjectName("accessDialog")
        dialog.setWindowTitle(self.translate("access_password_title"))
        dialog.setModal(True)
        dialog.setMinimumWidth(420)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(14)

        title = QLabel(self.translate("access_password_title"))
        title.setObjectName("accessTitle")
        body = QLabel(self.translate("access_password_body", build=build_name))
        body.setObjectName("accessBody")
        body.setWordWrap(True)
        input_field = QLineEdit()
        input_field.setObjectName("accessInput")
        input_field.setEchoMode(QLineEdit.EchoMode.Password)
        input_field.setPlaceholderText(self.translate("access_password_prompt"))

        button_row = QHBoxLayout()
        button_row.addStretch()
        cancel_button = QPushButton(self.translate("cancel_close"))
        cancel_button.setObjectName("accessCancelButton")
        download_button = QPushButton(self.translate("access_password_download"))
        download_button.setObjectName("accessDownloadButton")
        self.set_button_icon(download_button, "download_mods", 19)
        button_row.addWidget(cancel_button)
        button_row.addWidget(download_button)

        layout.addWidget(title)
        layout.addWidget(body)
        layout.addWidget(input_field)
        layout.addLayout(button_row)

        dialog.setStyleSheet(
            """
            QDialog#accessDialog {
                background: #081012;
                border: 1px solid rgba(116, 231, 186, 80);
                font-family: "Segoe UI", "Arial";
            }
            QLabel#accessTitle {
                color: #ffffff;
                font-size: 22px;
                font-weight: 800;
            }
            QLabel#accessBody {
                color: #d8e0dc;
                font-size: 14px;
            }
            QLineEdit#accessInput {
                background: rgba(0, 0, 0, 150);
                color: #ffffff;
                border: 1px solid rgba(116, 231, 186, 95);
                border-radius: 8px;
                padding: 10px 12px;
                min-height: 38px;
                font-size: 15px;
            }
            QPushButton#accessCancelButton,
            QPushButton#accessDownloadButton {
                border-radius: 8px;
                min-height: 38px;
                padding: 8px 14px;
                font-size: 14px;
                font-weight: 800;
            }
            QPushButton#accessCancelButton {
                color: rgba(255, 255, 255, 190);
                background: rgba(255, 255, 255, 18);
                border: 1px solid rgba(255, 255, 255, 42);
            }
            QPushButton#accessDownloadButton {
                color: #ffffff;
                background: rgba(12, 38, 52, 230);
                border: 1px solid #46b8ee;
            }
            """
        )

        cancel_button.clicked.connect(dialog.reject)
        download_button.clicked.connect(dialog.accept)
        input_field.returnPressed.connect(dialog.accept)
        input_field.setFocus()
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return input_field.text()

    def ensure_build_access(self, build: dict[str, object]) -> bool:
        if self.client_mode != CLIENT_MODE_NUKEM:
            return True

        access_key = self.get_build_access_key(build)
        if access_key in self.unlocked_build_ids:
            return True
        if not self.build_access_required(build):
            return True

        panel_required = (
            str(build.get("source", "")).strip().lower() == "panel"
            and str(build.get("access_required", "")).strip()
        )
        expected_hash = "" if panel_required else self.get_build_access_hash(build)
        if not panel_required and not expected_hash:
            self.show_error(self.translate("access_password_missing"))
            self.set_status("ready")
            return False

        password = self.request_build_password(build)
        if password is None:
            self.set_status("ready")
            return False

        if panel_required:
            try:
                unlocked_build = request_panel_build_access(self.config, self.client_mode, build, password)
            except PanelClientError:
                self.show_error(self.translate("access_password_failed"))
                self.set_status("ready")
                return False
            build.update(unlocked_build)
            self.unlocked_build_ids.add(access_key)
            self.project_access_unlocked = True
            self.set_status("access_granted")
            return True

        actual_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(actual_hash, expected_hash):
            self.show_error(self.translate("access_password_failed"))
            self.set_status("ready")
            return False

        self.project_access_unlocked = True
        self.unlocked_build_ids.add(access_key)
        self.set_status("access_granted")
        return True

    def ensure_project_access(self) -> bool:
        build = self.get_selected_build() or {}
        return self.ensure_build_access(dict(build))

    def check_mods_and_play(self) -> None:
        self.start_mod_check(launch_after_sync=True)

    def check_mods_only(self) -> None:
        if self.client_mode != CLIENT_MODE_NUKEM:
            self.open_current_profile_folder()
            return
        self.start_mod_check(launch_after_sync=False)

    def start_mod_check(self, launch_after_sync: bool) -> None:
        username = self.get_current_username()
        build = self.get_selected_build()

        if launch_after_sync and not username:
            self.show_error(self.translate("empty_username"))
            return
        if build is None:
            self.show_error(self.translate("empty_build"))
            return

        self.selected_profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        self.active_profile = self.selected_profile
        self.game_directory = self.selected_profile.directory
        self.engine.minecraft_directory = self.selected_profile.directory
        self.selected_username = username
        self.launch_after_sync = launch_after_sync
        self.action_requires_mod_access = self.client_mode == CLIENT_MODE_NUKEM and not launch_after_sync
        self.action_phrase_key = random.choice(self.get_action_phrase_keys()) if launch_after_sync else "mods_idle"
        if launch_after_sync:
            self.play_button.setText(self.translate(self.action_phrase_key))
            self.refresh_action_button_icons()
        self.set_action_buttons_enabled(False)
        self.progress_bar.setValue(0)
        sync_enabled = should_sync_profile(self.client_mode, self.selected_profile)
        if self.client_mode == CLIENT_MODE_NUKEM and launch_after_sync:
            sync_enabled = False

        if sync_enabled or self.client_mode == CLIENT_MODE_NUKEM:
            self.set_status("status_loading_build")
            self.build_config_worker = BuildConfigWorker(
                build,
                config=self.config,
                client_mode=self.client_mode,
                require_manifest=sync_enabled,
            )
            self.build_config_worker.build_loaded.connect(self.on_build_config_loaded)
            self.build_config_worker.error_occurred.connect(self.on_build_config_failed)
            self.build_config_worker.start()
            return

        self.set_status("status_skipping_sync")
        self.on_build_config_loaded(dict(build))

    def on_build_config_loaded(self, resolved_build: dict) -> None:
        self.evaluate_launcher_update(resolved_build)

        version = self.version_combo.currentText().strip()
        configured_version = str(resolved_build.get("minecraft_version", "")).strip()
        if configured_version:
            version = configured_version
            index = self.version_combo.findText(configured_version)
            if index >= 0:
                self.version_combo.setCurrentIndex(index)
            elif self.client_mode == CLIENT_MODE_NUKEM:
                self.version_combo.addItem(configured_version)
                self.version_combo.setCurrentText(configured_version)

        if not version:
            self.show_error(self.translate("empty_version"))
            self.reset_action_buttons()
            self.set_status("ready")
            return

        if self.action_requires_mod_access and not self.ensure_build_access(resolved_build):
            self.reset_action_buttons()
            self.set_status("ready")
            return

        manifest_url = str(resolved_build.get("manifest_url", "")).strip()
        self.selected_version = version
        self.selected_manifest_url = manifest_url
        sync_enabled = should_sync_profile(self.client_mode, self.selected_profile)
        if self.client_mode == CLIENT_MODE_NUKEM and self.launch_after_sync:
            sync_enabled = False
        if requires_server_manifest(self.selected_profile, manifest_url, self.client_mode):
            self.reset_action_buttons()
            user_error = explain_user_error(
                "Server profile needs manifest_url or source_key before launch.",
                language=self.language,
                context="server_manifest",
            )
            report_path = self.write_launcher_error_report(user_error, "Missing manifest_url/source_key.", "server_manifest")
            self.show_error(self.with_report_path(self.translate("server_manifest_required"), report_path))
            self.set_status("ready")
            return

        try:
            self.selected_launch_options = self.build_launch_options(resolved_build)
        except LaunchSettingsError as exc:
            self.reset_action_buttons()
            user_error = explain_user_error(exc, language=self.language, context="settings")
            report_path = self.write_launcher_error_report(user_error, str(exc), "settings")
            self.show_error(self.with_report_path(self.translate("settings_failed", error=user_error), report_path))
            self.set_status("ready")
            return

        self.selected_launch_options["language"] = self.language
        self.save_user_preferences()

        if not sync_enabled:
            self.progress_bar.setValue(0)
            if self.launch_after_sync:
                self.set_status("status_mods_no_sync")
                self.show_success_status_card()
                self.launch_game()
            else:
                self.set_status("status_mods_no_sync")
                self.show_success_status_card()
                self.reset_action_buttons()
            return

        self.download_worker = DownloadWorker(
            self.engine,
            self.selected_manifest_url,
            self.game_directory,
            allow_insecure_http=allow_insecure_panel_http(self.config),
        )
        self.download_worker.progress_changed.connect(self.progress_bar.setValue)
        self.download_worker.status_changed.connect(self.set_status)
        self.download_worker.status_detail_changed.connect(self.set_status_detail)
        self.download_worker.error_occurred.connect(self.on_download_failed)
        self.download_worker.finished_successfully.connect(self.on_sync_finished)
        self.download_worker.start()

    def on_build_config_failed(self, error: str) -> None:
        self.reset_action_buttons()
        user_error = explain_user_error(error, language=self.language, context="build_config")
        report_path = self.write_launcher_error_report(user_error, error, "build_config")
        self.show_error(self.with_report_path(self.translate("build_config_failed", error=user_error), report_path))
        self.set_status("ready")

    def on_sync_finished(self) -> None:
        if self.launch_after_sync:
            self.set_status("status_mods_ready")
            self.show_success_status_card()
            self.launch_game()
            return

        self.set_status("status_mods_ready")
        self.show_success_status_card()
        self.reset_action_buttons()

    def launch_game(self) -> None:
        self.set_status("status_launching")
        self.launch_worker = LaunchWorker(
            self.engine,
            self.selected_version,
            self.selected_username,
            self.selected_launch_options,
        )
        self.launch_worker.progress_changed.connect(self.progress_bar.setValue)
        self.launch_worker.status_changed.connect(self.set_status)
        self.launch_worker.crash_detected.connect(self.on_game_crashed)
        self.launch_worker.error_occurred.connect(self.on_launch_failed)
        self.launch_worker.game_started.connect(self.on_game_started)
        self.launch_worker.finished_successfully.connect(self.on_game_closed)
        self.launch_worker.start()

    def on_game_started(self) -> None:
        self.set_status("status_game_running")
        self.hide_launcher_to_tray_for_game()

    def on_download_failed(self, error_key: str, error: str) -> None:
        self.reset_action_buttons()
        user_error = explain_user_error(error, language=self.language, context=error_key)
        report_path = self.write_launcher_error_report(user_error, error, error_key)
        self.show_error(self.with_report_path(self.translate(error_key, error=user_error), report_path))
        self.set_status("ready")

    def evaluate_launcher_update(self, resolved_build: dict, *, show_panel: bool = True) -> bool:
        remote_version = str(resolved_build.get("launcher_version", "")).strip()
        if remote_version and not parse_version_numbers(remote_version):
            self.launcher_update_error = f"Malformed launcher_version in build config: {remote_version}"
            self.write_launcher_warning_report(
                self.launcher_update_error,
                "launcher_update",
            )
            self.set_update_check_state("error")
            return False

        update_notice = get_launcher_update_notice(resolved_build, APP_VERSION)
        if not update_notice:
            self.launcher_update_version = ""
            self.launcher_update_url = ""
            self.launcher_update_notes = ""
            if self.info_panel_mode == "update":
                self.info_panel_mode = "status"
                self.refresh_info_panel()
            return False

        download_url = update_notice["download_url"]
        if download_url:
            try:
                download_url = normalize_https_url(download_url, "Build launcher_download_url")
            except URLPolicyError as exc:
                self.write_launcher_warning_report(str(exc), "launcher_update")
                download_url = ""

        self.launcher_update_version = update_notice["version"]
        self.launcher_update_url = download_url
        self.launcher_update_notes = update_notice["notes"]
        self.update_mascot_dismissed = False
        self.set_status_text(self.translate("update_available", version=self.launcher_update_version))
        self.set_update_check_state("available")
        if show_panel:
            self.show_launcher_update_panel()
        return True

    def manual_check_launcher_update(self) -> None:
        if self.update_check_state == "available" and self.launcher_update_version:
            self.show_launcher_update_panel()
            return
        if self.register_update_ok_click():
            return
        self.start_launcher_update_check(manual=True)

    def register_update_ok_click(self) -> bool:
        if not MASCOT_FEATURE_ENABLED:
            return False
        if self.update_check_state not in {"ok", "checking"}:
            return False
        now = time.monotonic()
        self.update_ok_click_times = [click for click in self.update_ok_click_times if now - click <= 5.0]
        self.update_ok_click_times.append(now)
        if len(self.update_ok_click_times) < 3:
            return False
        self.update_ok_click_times.clear()
        self.update_mascot_message_key = "update_mascot_ok"
        self.update_mascot_dismissed = False
        self.refresh_update_mascot()
        return True

    def auto_check_launcher_update(self) -> None:
        self.start_launcher_update_check(manual=False)

    def start_launcher_update_check(self, *, manual: bool) -> None:
        if self.update_check_worker is not None and self.update_check_worker.isRunning():
            return
        build = self.get_selected_build() or {}
        self.update_check_manual = manual
        if manual:
            self.set_update_check_state("checking")
            self.set_status("manual_update_checking")
        self.update_check_worker = LauncherUpdateWorker(
            dict(build),
            config=self.config,
            client_mode=self.client_mode,
        )
        self.update_check_worker.update_loaded.connect(self.on_launcher_update_loaded)
        self.update_check_worker.error_occurred.connect(self.on_launcher_update_failed)
        self.update_check_worker.start()

    def on_launcher_update_loaded(self, resolved_build: dict) -> None:
        self.launcher_update_error = ""
        found_update = self.evaluate_launcher_update(resolved_build, show_panel=True)
        if found_update:
            self.set_update_check_state("available")
            return
        if self.launcher_update_error:
            self.set_update_check_state("error")
            if self.update_check_manual:
                self.set_status_text(self.translate("manual_update_failed", error=self.launcher_update_error))
            return
        self.set_update_check_state("ok")
        if self.update_check_manual:
            self.set_status("manual_update_ok")

    def on_launcher_update_failed(self, error: str) -> None:
        self.launcher_update_error = str(error).strip() or "Unknown launcher update check error"
        if self.launcher_update_version:
            self.set_update_check_state("available")
        else:
            self.set_update_check_state("error")
        if self.update_check_manual:
            self.set_status_text(self.translate("manual_update_failed", error=self.launcher_update_error))

    def set_update_check_state(self, state: str) -> None:
        self.update_check_state = state if state in {"available", "checking", "error", "ok"} else "ok"
        if self.update_check_state != "error":
            self.launcher_update_error = ""
        if self.update_check_state in {"available", "checking", "error"}:
            self.update_mascot_message_key = ""
        if self.update_check_state != "available" and not self.update_mascot_message_key:
            self.update_mascot_dismissed = False
        self.refresh_update_check_button()
        self.refresh_update_mascot()

    def toggle_update_pulse(self) -> None:
        self.update_pulse_on = not self.update_pulse_on
        self.refresh_update_check_button()

    def refresh_update_check_button(self) -> None:
        if not hasattr(self, "update_check_button"):
            return
        labels = {
            "available": "!",
            "checking": "...",
            "error": "!",
            "ok": "OK",
        }
        self.update_check_button.setText(labels.get(self.update_check_state, "OK"))
        tooltip = self.translate("manual_update_tooltip")
        if self.update_check_state == "checking":
            tooltip = self.translate("manual_update_checking")
        elif self.update_check_state == "available" and self.launcher_update_version:
            tooltip = self.translate("update_available", version=self.launcher_update_version)
        elif self.update_check_state == "error" and self.launcher_update_error:
            tooltip = self.translate("manual_update_failed", error=self.launcher_update_error)
        self.update_check_button.setToolTip(tooltip)
        self.update_check_button.setProperty("state", self.update_check_state)
        self.update_check_button.setProperty("pulse", self.update_pulse_on and self.update_check_state == "available")
        self.update_check_button.style().unpolish(self.update_check_button)
        self.update_check_button.style().polish(self.update_check_button)
        if self.update_check_state == "available":
            if not self.update_pulse_timer.isActive():
                self.update_pulse_timer.start()
        else:
            self.update_pulse_timer.stop()
            self.update_pulse_on = False

    def refresh_update_mascot(self) -> None:
        if not hasattr(self, "update_mascot_frame"):
            return
        if not MASCOT_FEATURE_ENABLED:
            self.update_mascot_frame.hide()
            if self.update_mascot_movie is not None:
                self.update_mascot_movie.stop()
            return
        custom_visible = bool(self.update_mascot_message_key) and not self.update_mascot_dismissed
        update_visible = (
            self.update_check_state == "available"
            and bool(self.launcher_update_version)
            and not self.update_mascot_dismissed
        )
        visible = custom_visible or update_visible
        title_key = self.update_mascot_message_key if custom_visible else "update_mascot_found"
        self.update_mascot_title.setText(self.translate(title_key))
        self.update_mascot_frame.hide()
        if visible:
            self.show_floating_mascot(self.translate(title_key))
        elif self.mascot_window is not None:
            self.floating_mascot_message_active = False
            self.mascot_window.set_message("")
            if not self.mascot_user_enabled:
                self.mascot_window.hide()
        if self.update_mascot_movie is not None:
            self.update_mascot_movie.stop()

    def show_launcher_update_panel(self) -> None:
        if not self.launcher_update_version:
            return
        if self.info_panel_mode in ("crash", "error"):
            return
        self.info_panel_mode = "update"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()

    def toggle_info_panel(self) -> None:
        if self.info_panel_mode == "settings":
            self.info_panel_mode = "status" if self.status_card_confirmed else "help"
        elif self.info_panel_mode not in ("crash", "error", "update"):
            self.info_panel_mode = "settings"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()

    def refresh_info_panel(self) -> None:
        self.set_admin_widgets_visible(False)
        self.set_launch_settings_visible(False)
        self.set_player_widgets_visible(False)
        if hasattr(self, "admin_unlock_button"):
            self.admin_unlock_button.hide()
        self.info_panel.setMinimumHeight(220)
        self.info_title_label.setMinimumHeight(0)
        self.info_title_label.setWordWrap(False)
        if hasattr(self, "news_frame"):
            self.refresh_news_visibility()

        if self.info_panel_mode == "crash" and self.last_crash_reason:
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(False)
            self.info_title_label.show()
            self.info_body_label.show()
            self.info_title_label.setText(self.translate("crash_panel_title"))
            self.info_body_label.setText(self.last_crash_reason)
            self.open_crash_reports_button.setText(self.translate("open_crash_reports"))
            self.set_button_icon(self.open_crash_reports_button, "open_error_report", 18)
            self.open_crash_reports_button.show()
            self.download_update_button.hide()
            return

        if self.info_panel_mode == "error" and self.last_error_message:
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(False)
            self.info_title_label.show()
            self.info_body_label.show()
            self.info_title_label.setText(self.translate("error_panel_title"))
            self.info_body_label.setText(self.last_error_message)
            self.open_crash_reports_button.setText(self.translate("open_error_report"))
            self.set_button_icon(self.open_crash_reports_button, "open_error_report", 18)
            self.open_crash_reports_button.show()
            self.download_update_button.hide()
            return

        if self.info_panel_mode == "update" and self.launcher_update_version:
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(False)
            self.info_title_label.show()
            self.info_body_label.show()
            self.info_title_label.setWordWrap(True)
            self.info_title_label.setMinimumHeight(76)
            self.info_title_label.setText(self.translate("update_available", version=self.launcher_update_version))
            body_parts = [self.translate("update_panel_body")]
            if self.launcher_update_notes:
                body_parts.insert(0, self.launcher_update_notes)
            self.info_body_label.setText("\n".join(body_parts))
            self.open_crash_reports_button.hide()
            self.download_update_button.setText(self.translate("download_update"))
            self.download_update_button.setVisible(bool(self.launcher_update_url))
            return

        if self.info_panel_mode == "feedback":
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(False)
            self.info_title_label.show()
            self.info_body_label.show()
            self.info_title_label.setText(self.translate("feedback_panel_title"))
            self.info_body_label.setText(self.translate("feedback_panel_body"))
            self.open_crash_reports_button.setText(self.translate("report_bug"))
            self.set_button_icon(self.open_crash_reports_button, "report_bug", 18)
            self.open_crash_reports_button.show()
            self.download_update_button.hide()
            return

        if self.info_panel_mode == "help":
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(False)
            self.info_title_label.show()
            self.info_body_label.show()
            self.info_title_label.setText(self.translate("feedback_card_title"))
            self.info_body_label.setText(self.translate("feedback_card_body"))
            self.open_profile_button.hide()
            self.open_game_button.hide()
            self.open_crash_reports_button.setText(self.translate("report_bug"))
            self.set_button_icon(self.open_crash_reports_button, "report_bug", 18)
            self.open_crash_reports_button.show()
            self.download_update_button.hide()
            return

        if self.info_panel_mode == "settings":
            self.info_panel.setMinimumHeight(300)
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(True)
            self.set_launch_settings_visible(True)
            self.admin_unlock_button.setVisible(
                self.client_mode == CLIENT_MODE_NUKEM and self.is_admin_access_configured()
            )
            self.info_title_label.show()
            self.info_body_label.hide()
            self.info_title_label.setText(self.translate("settings_title"))
            self.open_crash_reports_button.setText(self.translate("open_crash_reports"))
            self.open_crash_reports_button.hide()
            self.download_update_button.hide()
            return

        if self.info_panel_mode == "player":
            self.info_panel.setMinimumHeight(300)
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(True)
            self.set_player_widgets_visible(True)
            self.info_title_label.show()
            self.info_body_label.hide()
            self.info_title_label.setText(self.translate("player_panel_title"))
            self.open_profile_button.hide()
            self.open_game_button.hide()
            self.open_crash_reports_button.hide()
            self.download_update_button.hide()
            return

        if self.info_panel_mode == "admin":
            self.info_panel.setMinimumHeight(330)
            self.set_status_rows_visible(False)
            self.set_settings_widgets_visible(False)
            self.set_admin_widgets_visible(True)
            self.info_title_label.show()
            self.info_body_label.show()
            self.info_title_label.setText(self.translate("admin_panel_title"))
            self.info_body_label.setText(self.translate("admin_panel_body"))
            self.open_profile_button.hide()
            self.open_game_button.hide()
            self.open_crash_reports_button.hide()
            self.download_update_button.hide()
            return

        if not self.status_card_confirmed:
            self.info_panel_mode = "help"
            self.refresh_info_panel()
            return

        self.info_panel_mode = "status"
        self.set_settings_widgets_visible(False)
        self.set_status_rows_visible(True)
        self.info_title_label.hide()
        self.info_body_label.hide()
        self.open_profile_button.hide()
        self.open_game_button.hide()
        self.open_crash_reports_button.hide()
        self.download_update_button.hide()
        self.mods_status_title.setText(self.translate("status_card_mods"))
        status_text = self.status_label.text() if self.status_label.text() else self.translate("status_card_mods_body")
        self.mods_status_body.setText(status_text)
        self.fabric_status_title.setText(self.translate("status_card_fabric"))
        self.fabric_status_body.setText(
            self.translate("status_card_loader_body", loader=self.loader_setting_combo.currentText())
        )
        self.java_status_title.setText(self.translate("status_card_java"))
        java_path = self.java_path_input.text().strip()
        self.java_status_body.setText(java_path if java_path else self.translate("runtime_auto"))
        return

    def set_status_rows_visible(self, visible: bool) -> None:
        for row in getattr(self, "status_rows", []):
            row.setVisible(visible)
        for widget in (
            getattr(self, "mods_status_title", None),
            getattr(self, "mods_status_body", None),
            getattr(self, "mods_status_check", None),
            getattr(self, "fabric_status_title", None),
            getattr(self, "fabric_status_body", None),
            getattr(self, "fabric_status_check", None),
            getattr(self, "java_status_title", None),
            getattr(self, "java_status_body", None),
            getattr(self, "java_status_check", None),
        ):
            if widget is not None:
                widget.setVisible(visible)

    def show_settings_panel(self) -> None:
        self.info_panel_mode = "settings"
        self.refresh_info_panel()

    def show_success_status_card(self) -> None:
        if self.info_panel_mode in ("admin", "crash", "error", "update", "settings", "feedback", "player"):
            return
        self.status_card_confirmed = True
        self.info_panel_mode = "status"
        self.refresh_info_panel()

    def set_settings_widgets_visible(self, visible: bool) -> None:
        for widget in getattr(self, "settings_widgets", []):
            widget.setVisible(visible)

    def set_launch_settings_visible(self, visible: bool) -> None:
        for widget in getattr(self, "launch_settings_widgets", []):
            widget.setVisible(visible)

    def set_player_widgets_visible(self, visible: bool) -> None:
        for widget in getattr(self, "player_widgets", []):
            widget.setVisible(visible)

    def set_admin_widgets_visible(self, visible: bool) -> None:
        for widget in getattr(self, "admin_widgets", []):
            widget.setVisible(visible)

    def show_feedback_panel(self) -> None:
        self.feedback_button.setText(self.translate("feedback_problem"))
        self.info_panel_mode = "feedback"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()

    def show_player_panel(self) -> None:
        self.info_panel_mode = "player"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()

    def show_admin_panel(self, checked: bool = False, *, require_auth: bool = True) -> None:
        del checked
        if require_auth and not self.request_admin_access(show_panel=False):
            return
        self.info_panel_mode = "admin"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()

    def handle_panel_report_action(self) -> None:
        if self.info_panel_mode in ("help", "feedback"):
            self.open_report_dialog()
            return
        self.open_crash_reports_folder()

    def open_report_dialog(self) -> None:
        user_message = prompt_report_message(
            self,
            title=self.translate("report_dialog_title"),
            body=self.translate("report_dialog_body"),
            placeholder=self.translate("report_dialog_placeholder"),
            accept_label=self.translate("report_dialog_send"),
            cancel_label=self.translate("report_dialog_cancel"),
            stylesheet=SYSTEM_DIALOG_STYLESHEET,
            empty_message=self.translate("report_empty"),
            on_empty=self.show_error,
        )
        if user_message is None:
            return
        self.submit_manual_report(user_message)

    def submit_manual_report(self, user_message: str) -> None:
        technical_details = f"Manual player report from {APP_DISPLAY_NAME} {APP_VERSION}."
        if self.send_panel_report("manual_report", user_message, technical_details):
            self.set_status_text(self.translate("report_sent"))
            return
        report_path = self.write_launcher_warning_report(
            f"{technical_details}\n\nUser message:\n{user_message}",
            "manual_report",
        )
        self.last_error_message = user_message
        if report_path is not None:
            self.last_error_report_path = report_path
            self.set_status_text(self.translate("report_saved_local"))
            return
        self.set_status_text(self.translate("report_send_failed"))
        self.open_crash_reports_folder()

    def send_panel_report(self, context: str, user_message: str = "", technical_details: str = "") -> bool:
        if self.client_mode != "nukem":
            return False
        return post_panel_report(
            self.config,
            {
                "project": self.client_mode,
                "build_id": self.get_selected_build_id(),
                "username": self.get_current_username(),
                "launcher_version": APP_VERSION,
                "error_type": context,
                "user_message": user_message or self.last_error_message or "Player pressed report button.",
                "technical_details": technical_details or f"Manual report from {APP_DISPLAY_NAME} {APP_VERSION}.",
            },
        )

    def open_modpack_repo(self) -> None:
        repo_url = get_admin_link(self.config, self.client_mode, "repo_url")
        if repo_url:
            self.open_external_link(repo_url)

    def open_modpack_manifest(self) -> None:
        manifest_url = get_admin_link(self.config, self.client_mode, "manifest_url")
        if manifest_url:
            self.open_external_link(manifest_url)

    def open_support_queue(self) -> None:
        support_url = get_support_url(self.config, self.client_mode)
        if support_url:
            self.open_external_link(support_url)

    def open_current_profile_folder(self) -> None:
        profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        self.open_folder(profile.directory)

    def open_profiles_root_folder(self) -> None:
        self.profile_manager.base_directory.mkdir(parents=True, exist_ok=True)
        self.open_folder(self.profile_manager.base_directory)

    def open_crash_reports_folder(self) -> None:
        if self.info_panel_mode == "error" and self.last_error_report_path is not None:
            self.open_folder(self.last_error_report_path.parent)
            return

        profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        crash_reports_path = profile.directory / "crash-reports"
        if not crash_reports_path.exists():
            crash_reports_path = profile.directory
        self.open_folder(crash_reports_path)

    def open_external_link(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def open_launcher_update_url(self) -> None:
        if self.launcher_update_url:
            self.open_external_link(self.launcher_update_url)

    def open_folder(self, folder_path: Path) -> None:
        try:
            folder_path.mkdir(parents=True, exist_ok=True)
            os.startfile(str(folder_path))
        except OSError as exc:
            self.show_error(str(exc))

    def browse_java_path(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("java_path"),
            self.java_path_input.text().strip() or str(Path.home()),
            "Java (*.exe);;All files (*)",
        )
        if selected_path:
            self.java_path_input.setText(selected_path)
            self.save_user_preferences()

    def browse_skin_file(self) -> None:
        selected_path, _ = QFileDialog.getOpenFileName(
            self,
            self.translate("skin"),
            str(Path.home()),
            "PNG (*.png);;All files (*)",
        )
        if not selected_path:
            return

        source_path = Path(selected_path)
        if source_path.suffix.lower() != ".png":
            self.show_error(self.translate("skin_invalid"))
            return

        profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        skin_directory = profile.directory / "skin"
        skin_directory.mkdir(parents=True, exist_ok=True)
        target_path = skin_directory / "skin.png"
        shutil.copyfile(source_path, target_path)
        self.skin_path = str(target_path)
        self.refresh_skin_status()
        self.set_status_text(self.translate("skin_saved"))
        self.save_user_preferences()

    def save_skin_url(self) -> None:
        raw_url = self.skin_url_input.text().strip()
        if not raw_url:
            self.show_error(self.translate("skin_url_invalid"))
            return
        try:
            skin_url = normalize_https_url(raw_url, "Skin URL")
        except URLPolicyError:
            self.show_error(self.translate("skin_url_invalid"))
            return
        self.skin_path = skin_url
        self.refresh_skin_status()
        self.set_status_text(self.translate("skin_saved"))
        self.save_user_preferences()

    def refresh_skin_status(self) -> None:
        if self.skin_path:
            self.skin_status_label.setText(f"{self.translate('skin_saved')}\n{self.skin_path}")
            if self.skin_path.startswith("https://"):
                self.skin_url_input.setText(self.skin_path)
            return
        self.skin_status_label.setText(self.translate("skin_empty"))

    def on_launch_failed(self, error: str, technical_report: str = "") -> None:
        if self.hidden_to_tray_for_game:
            self.restore_launcher_from_tray()
        self.reset_action_buttons()
        user_error = explain_user_error(error, language=self.language, context="launch")
        report_path = self.write_launcher_error_report(user_error, technical_report or error, "launch")
        self.show_error(self.with_report_path(self.translate("launch_failed", error=user_error), report_path))
        self.set_status("ready")

    def on_game_crashed(self, crash_reason: str) -> None:
        if self.hidden_to_tray_for_game:
            self.restore_launcher_from_tray()
        self.reset_action_buttons()
        self.last_crash_reason = crash_reason
        self.last_crash_report_path = self.write_launcher_crash_report(crash_reason, "mslauncher-last-crash.txt")
        self.info_panel_mode = "crash"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()
        self.set_status("ready")
        QTimer.singleShot(0, self.show_crash_help_dialog)

    def show_crash_help_dialog(self) -> None:
        if not self.last_crash_reason:
            return

        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Warning)
        dialog.setWindowTitle(self.translate("crash_help_title"))
        dialog.setText(self.translate("crash_help_body"))
        dialog.setInformativeText(truncate_dialog_text(self.last_crash_reason))
        dialog.setStyleSheet(SYSTEM_DIALOG_STYLESHEET)

        ok_button = dialog.addButton(self.translate("crash_action_ok"), QMessageBox.ButtonRole.AcceptRole)
        report_button = dialog.addButton(self.translate("crash_action_report"), QMessageBox.ButtonRole.ActionRole)
        self_help_button = dialog.addButton(
            self.translate("crash_action_self_help"),
            QMessageBox.ButtonRole.ActionRole,
        )
        google_button = dialog.addButton(self.translate("crash_action_google"), QMessageBox.ButtonRole.ActionRole)

        dialog.setDefaultButton(ok_button)
        dialog.exec()
        clicked_button = dialog.clickedButton()
        if clicked_button == report_button:
            self.handle_crash_report_action()
        elif clicked_button == self_help_button:
            self.show_crash_self_help_dialog()
        elif clicked_button == google_button:
            self.open_crash_google_search()

    def handle_crash_report_action(self) -> None:
        user_message = self.request_player_report_message()
        if user_message is None:
            return
        self.submit_crash_report(user_message)

    def submit_crash_report(self, user_message: str) -> bool:
        technical_details = self.last_crash_reason or self.build_manual_report_details()
        if self.send_panel_report("crash", user_message, technical_details):
            self.set_status_text(self.translate("report_sent"))
            return True
        self.save_crash_report_fallback(user_message, technical_details)
        self.set_status_text(self.translate("report_send_failed"))
        return False

    def save_crash_report_fallback(self, user_message: str, technical_details: str) -> Path | None:
        try:
            profile = self.profile_manager.get_profile(self.get_selected_profile_id())
            report_path = write_error_report(
                technical_details,
                user_message=user_message,
                context="crash",
                base_directory=profile.directory,
            )
        except OSError:
            return None

        self.last_error_message = user_message
        self.last_error_report_path = report_path
        return report_path

    def show_crash_self_help_dialog(self) -> None:
        if not self.last_crash_reason:
            return
        QMessageBox.information(
            self,
            self.translate("crash_self_help_title"),
            truncate_dialog_text(self.last_crash_reason, limit=3600),
        )

    def request_player_report_message(self) -> str | None:
        return prompt_report_message(
            self,
            title=self.translate("report_dialog_title"),
            body=self.translate("report_dialog_body"),
            placeholder=self.translate("report_dialog_placeholder"),
            accept_label=self.translate("report_dialog_send"),
            cancel_label=self.translate("report_dialog_cancel"),
            stylesheet=SYSTEM_DIALOG_STYLESHEET,
            empty_message=self.translate("report_empty"),
            on_empty=self.set_status_text,
        )

    def build_manual_report_details(self) -> str:
        return build_manual_report_details(
            app_display_name=APP_DISPLAY_NAME,
            app_version=APP_VERSION,
            client_mode=self.client_mode,
            build_id=self.get_selected_build_id(),
            profile_id=self.get_selected_profile_id(),
            last_error=self.last_error_message,
        )

    def build_crash_google_url(self) -> str:
        return build_crash_google_url(
            self.version_combo.currentText(),
            self.loader_setting_combo.currentText(),
            self.last_crash_reason,
        )

    def open_crash_google_search(self) -> None:
        if not QDesktopServices.openUrl(QUrl(self.build_crash_google_url())):
            self.set_status_text(self.translate("crash_google_failed"))

    def write_launcher_crash_report(self, crash_reason: str, file_name: str) -> Path | None:
        profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        return write_launcher_crash_report(profile.directory, crash_reason, file_name)

    def write_launcher_error_report(self, user_message: str, technical_details: str, context: str) -> Path | None:
        profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        report_path = write_launcher_error_report(
            profile.directory,
            user_message=user_message,
            technical_details=technical_details,
            context=context,
        )
        if report_path is None:
            return None

        self.last_error_message = user_message
        self.last_error_report_path = report_path
        self.send_panel_report(context, user_message, technical_details)
        self.info_panel_mode = "error"
        self.refresh_info_panel()
        self.info_panel.show()
        for button in self.social_buttons:
            button.show()
        return report_path

    def write_launcher_warning_report(self, technical_details: str, context: str) -> Path | None:
        profile = self.profile_manager.get_profile(self.get_selected_profile_id())
        return write_launcher_warning_report(profile.directory, technical_details, context)

    def with_report_path(self, message: str, report_path: Path | None) -> str:
        return with_report_path(
            message,
            report_path,
            self.translate("error_report_saved", path=report_path),
        )

    def on_game_closed(self) -> None:
        self.reset_action_buttons()
        self.set_status("status_game_closed")
        if self.hidden_to_tray_for_game:
            self.restore_launcher_from_tray()

    def set_action_buttons_enabled(self, enabled: bool) -> None:
        self.play_button.setEnabled(enabled)
        self.mods_button.setEnabled(enabled)

    def reset_action_buttons(self) -> None:
        self.set_action_buttons_enabled(True)
        self.action_phrase_key = "play_idle"
        self.play_button.setText(self.translate(self.action_phrase_key))
        self.mods_button.setText(self.translate(self.get_mods_action_key()))
        self.refresh_action_button_icons()

    def set_status(self, key: str) -> None:
        self.status_label.setProperty("status_key", key)
        self.status_label.setProperty("status_detail", None)
        self.status_label.setText(self.translate(key))
        self.refresh_status_panel_text(self.translate(key))

    def set_status_detail(self, key: str, detail: str) -> None:
        self.status_label.setProperty("status_key", key)
        self.status_label.setProperty("status_detail", detail)
        self.status_label.setText(self.translate(key, file=detail))
        self.refresh_status_panel_text(self.translate(key, file=detail))

    def set_status_text(self, text: str) -> None:
        self.status_label.setProperty("status_key", None)
        self.status_label.setProperty("status_detail", None)
        self.status_label.setText(text)
        self.refresh_status_panel_text(text)

    def refresh_status_panel_text(self, text: str) -> None:
        if self.info_panel_mode == "settings" and self.info_panel.isVisible():
            self.info_body_label.setText(text)
        if self.info_panel_mode == "status":
            self.mods_status_body.setText(text)

    def show_error(self, message: str) -> None:
        self.last_error_message = message
        self.info_panel_mode = "error"
        self.refresh_info_panel()
        self.info_panel.show()
        self.set_status_text(message.splitlines()[0] if message else self.translate("error"))

    def build_launch_options(self, build: dict[str, object]) -> dict[str, object]:
        launch_options = self.get_current_launch_settings()
        loader = str(build.get("loader", "")).strip()
        loader_version = str(build.get("loader_version", "")).strip()
        server = str(build.get("server", "")).strip()
        port = str(build.get("port", "")).strip()

        if loader and bool(build.get("force_loader", False)):
            launch_options["loader"] = loader
        if loader_version:
            launch_options["loader_version"] = loader_version
        if server:
            launch_options["server"] = server
        if port:
            launch_options["port"] = port

        return launch_options

    def get_current_launch_settings(self) -> dict[str, object]:
        launch_options = dict(get_config_launch_options(self.config))
        launch_options["loader"] = self.loader_setting_combo.currentText().strip() or "vanilla"
        launch_options["memory_min"] = f"{self.memory_min_input.value()}G"
        launch_options["memory_max"] = f"{self.memory_max_input.value()}G"
        launch_options["java_path"] = self.java_path_input.text().strip()
        return validate_launch_settings(launch_options)

    def save_user_preferences(self) -> None:
        try:
            self.config["launch"] = self.get_current_launch_settings()
        except LaunchSettingsError as exc:
            user_error = explain_user_error(exc, language=self.language, context="settings")
            self.write_launcher_error_report(user_error, str(exc), "settings")
            self.set_status_text(self.translate("settings_failed", error=user_error))

        self.config["default_language"] = self.language
        username = self.get_current_username()
        self.recent_usernames = self.get_recent_usernames(username)
        self.config["default_username"] = username
        self.config["recent_usernames"] = self.recent_usernames
        self.config["client_mode"] = self.client_mode
        self.config["skin_path"] = self.skin_path
        self.config["default_profile"] = self.get_selected_profile_id()
        selected_build_id = self.get_selected_build_id()
        if selected_build_id:
            self.config["default_build"] = selected_build_id

        try:
            save_launcher_config(self.config)
        except OSError as exc:
            user_error = explain_user_error(exc, language=self.language, context="config_save")
            report_path = self.write_launcher_error_report(user_error, str(exc), "config_save")
            message = self.with_report_path(self.translate("config_save_failed", error=user_error), report_path)
            self.set_status_text(message)
            if self.isVisible():
                self.show_error(message)

    def show_config_repair_warning_if_needed(self) -> None:
        backup_path = CONFIG_LOAD_WARNING or get_last_config_backup_path()
        if backup_path:
            user_error = explain_user_error("Damaged launcher_config.json", language=self.language, context="config_load")
            report_path = self.write_launcher_error_report(
                user_error,
                f"Config backup created: {backup_path}",
                "config_load",
            )
            self.show_error(self.with_report_path(self.translate("config_repaired", path=backup_path), report_path))

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton and event.position().y() <= 92:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_position is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None
        super().mouseReleaseEvent(event)

    def closeEvent(self, event) -> None:
        if self.launch_worker is not None and self.launch_worker.isRunning() and self.engine.is_game_process_running():
            choice = self.ask_game_close_choice()
            if choice == "cancel":
                event.ignore()
                return
            if choice == "terminate":
                self.launch_worker.request_terminate_game()
                self.launch_worker.wait(7000)
            else:
                self.launch_worker.request_detach()
                self.launch_worker.wait(3000)

        self.save_user_preferences()
        if not self.wait_for_worker_shutdown(self.download_worker):
            event.ignore()
            return
        if not self.wait_for_worker_shutdown(self.build_config_worker):
            event.ignore()
            return
        if not self.wait_for_worker_shutdown(self.versions_worker):
            event.ignore()
            return
        if not self.wait_for_worker_shutdown(self.launch_worker):
            event.ignore()
            return
        if self.mascot_window is not None:
            self.mascot_window.close()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        super().closeEvent(event)

    def ask_game_close_choice(self) -> str:
        dialog = QMessageBox(self)
        dialog.setIcon(QMessageBox.Icon.Question)
        dialog.setWindowTitle(self.translate("app_title"))
        dialog.setText(self.translate("close_game_prompt"))
        dialog.setStyleSheet(SYSTEM_DIALOG_STYLESHEET)
        leave_button = dialog.addButton(self.translate("leave_game_running"), QMessageBox.ButtonRole.AcceptRole)
        close_button = dialog.addButton(self.translate("close_game"), QMessageBox.ButtonRole.DestructiveRole)
        cancel_button = dialog.addButton(self.translate("cancel_close"), QMessageBox.ButtonRole.RejectRole)
        dialog.exec()

        clicked_button = dialog.clickedButton()
        if clicked_button is close_button:
            return "terminate"
        if clicked_button is cancel_button:
            return "cancel"
        if clicked_button is leave_button:
            return "detach"
        return "cancel"

    def wait_for_worker_shutdown(self, worker: QThread | None) -> bool:
        if worker is not None and worker.isRunning():
            return worker.wait(3000)
        return True

    def translate(self, key: str, **kwargs: object) -> str:
        text = TRANSLATIONS.get(self.language, TRANSLATIONS["EN"]).get(key, key)
        if isinstance(text, list):
            return str(text[0]) if text else key
        if kwargs:
            return text.format(**kwargs)
        return text

    def get_brand_subtitle_keys(self) -> list[str]:
        return [
            "brand_subtitle_project",
            "brand_subtitle_crew",
            "brand_subtitle_places",
            "brand_subtitle_session",
        ]

    def get_action_phrase_keys(self) -> list[str]:
        return [
            "action_motor",
            "action_go",
            "action_scene",
            "action_cut",
            "action_awake",
        ]


def main() -> None:
    app = QApplication(sys.argv)
    window = MSLauncherWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
