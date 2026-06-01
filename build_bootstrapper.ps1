$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$exePath = Join-Path $projectRoot "dist\MSLaunchSetup.exe"

Push-Location $projectRoot
try {
  python -m PyInstaller `
    --noconfirm `
    --clean `
    --onefile `
    --windowed `
    --name MSLaunchSetup `
    --icon assets\app_icon.ico `
    bootstrapper.py
}
finally {
  Pop-Location
}

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
  throw "Build failed: dist\MSLaunchSetup.exe was not created."
}

Write-Host ""
Write-Host "Bootstrapper build complete:"
Write-Host $exePath
