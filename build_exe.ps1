$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$exePath = Join-Path $projectRoot "dist\MSLauncher\MSLauncher.exe"

Push-Location $projectRoot
try {
  python -m PyInstaller --noconfirm MSLauncher.spec
}
finally {
  Pop-Location
}

if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
  throw "Build failed: dist\MSLauncher\MSLauncher.exe was not created."
}

Write-Host ""
Write-Host "Build complete:"
Write-Host $exePath
Write-Host ""
Write-Host "Release folder:"
Write-Host (Join-Path $projectRoot "dist\MSLauncher")
