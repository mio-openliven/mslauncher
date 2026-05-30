$ErrorActionPreference = "Stop"

python -m PyInstaller `
  --noconfirm `
  --windowed `
  --onedir `
  --name MSLauncher `
  --add-data "assets;assets" `
  --add-data "launcher_config.json;." `
  gui.py

Copy-Item -Path "launcher_config.json" -Destination "dist\MSLauncher\launcher_config.json" -Force
Write-Host "Build complete: dist\MSLauncher\MSLauncher.exe"
