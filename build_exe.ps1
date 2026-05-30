$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --windowed `
  --onedir `
  --name MSLauncher `
  --add-data "assets;assets" `
  --add-data "launcher_config.json;." `
  gui.py

Write-Host "Build complete: dist\MSLauncher\MSLauncher.exe"
