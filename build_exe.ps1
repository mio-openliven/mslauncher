$ErrorActionPreference = "Stop"

python -m PyInstaller --noconfirm MSLauncher.spec

Write-Host "Build complete: dist\MSLauncher\MSLauncher.exe"
