$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$templateConfig = Join-Path $PSScriptRoot "launcher_config.template.json"
$projectConfig = Join-Path $projectRoot "launcher_config.json"
$buildScript = Join-Path $projectRoot "build_exe.ps1"
$distPath = Join-Path $projectRoot "dist\MSLauncher"

Write-Host "MSLauncher release prepare"
Write-Host "Copying template config to launcher_config.json..."
Copy-Item -Path $templateConfig -Destination $projectConfig -Force

Write-Host "Building MSLauncher..."
Push-Location $projectRoot
try {
  powershell -ExecutionPolicy Bypass -File $buildScript
}
finally {
  Pop-Location
}

Write-Host ""
Write-Host "Release folder:"
Write-Host $distPath
Write-Host ""
Write-Host "Before sending to players, check release\RELEASE_CHECKLIST_RU.md"
