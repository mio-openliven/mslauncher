param(
  [ValidateSet("default", "nukem")]
  [string]$Preset = "default"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$presetTemplates = @{
  default = Join-Path $PSScriptRoot "launcher_config.template.json"
  nukem = Join-Path $PSScriptRoot "launcher_config.nukem.template.json"
}
$templateConfig = $presetTemplates[$Preset]
$projectConfig = Join-Path $projectRoot "launcher_config.json"
$buildScript = Join-Path $projectRoot "build_exe.ps1"
$distPath = Join-Path $projectRoot "dist\MSLauncher"
$docsPath = Join-Path $distPath "docs"

if (-not (Test-Path $templateConfig)) {
  throw "Preset config not found: $templateConfig"
}

Write-Host "MSLaunch release prepare"
Write-Host "Using preset: $Preset"
Write-Host "Copying preset config to launcher_config.json..."
Copy-Item -Path $templateConfig -Destination $projectConfig -Force

Write-Host "Building MSLaunch..."
Push-Location $projectRoot
try {
  powershell -ExecutionPolicy Bypass -File $buildScript
}
finally {
  Pop-Location
}

Write-Host "Copying release docs..."
New-Item -ItemType Directory -Path $docsPath -Force | Out-Null
Copy-Item -Path (Join-Path $PSScriptRoot "CLIENT_SETUP_RU.md") -Destination $docsPath -Force
Copy-Item -Path (Join-Path $PSScriptRoot "NUKEM_SETUP_RU.md") -Destination $docsPath -Force
Copy-Item -Path (Join-Path $PSScriptRoot "PLAYER_README_RU.txt") -Destination $docsPath -Force
Copy-Item -Path (Join-Path $PSScriptRoot "RELEASE_CHECKLIST_RU.md") -Destination $docsPath -Force
Copy-Item -Path (Join-Path $PSScriptRoot "POST_RELEASE_BACKLOG_RU.md") -Destination $docsPath -Force
Copy-Item -Path (Join-Path $PSScriptRoot "launcher_config.template.json") -Destination $docsPath -Force
Copy-Item -Path (Join-Path $PSScriptRoot "launcher_config.nukem.template.json") -Destination $docsPath -Force

Write-Host ""
Write-Host "Release folder:"
Write-Host $distPath
Write-Host ""
Write-Host "Give this whole folder to the client/player package:"
Write-Host $distPath
Write-Host ""
Write-Host "Before sending to players, check docs\RELEASE_CHECKLIST_RU.md inside the release folder."
