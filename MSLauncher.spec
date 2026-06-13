# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=collect_data_files('minecraft_launcher_lib') + [
        ('assets', 'assets'),
        ('launcher_config.json', '.'),
        ('release/CLIENT_SETUP_RU.md', 'docs'),
        ('release/NUKEM_SETUP_RU.md', 'docs'),
        ('release/PLAYER_README_RU.txt', 'docs'),
        ('release/RELEASE_CHECKLIST_RU.md', 'docs'),
        ('release/POST_RELEASE_BACKLOG_RU.md', 'docs'),
        ('release/launcher_config.template.json', 'docs'),
        ('release/launcher_config.nukem.template.json', 'docs'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MSLauncher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/app_icon.ico',
    contents_directory='.',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MSLauncher',
)
