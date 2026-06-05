param(
  [string]$HostTarget = "root@186.246.12.238",
  [string]$RemoteDir = "/opt/mslaunch/data/downloads",
  [string]$AppRemoteDir = "/opt/mslaunch/app",
  [string]$BackupRoot = "/opt/mslaunch/backups",
  [string]$ArtifactDir = "",
  [switch]$DryRun,
  [switch]$SkipPublicVerify
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ArtifactDir) {
  $ArtifactDir = Join-Path $projectRoot "dist"
}

$expectedFiles = @(
  @{
    Name = "MSLaunchPayload.dat"
    Sha256 = "C859A9338100F74D1A1F420C2F22209A4F0C4271F7B86170398DC08ADB341C37"
  },
  @{
    Name = "MSLaunchSetup.exe"
    Sha256 = "166E36D6075787FE310FA45AF1431E16DC7CB452133A54CD0D06C4D2922B04A3"
  },
  @{
    Name = "bootstrap.json"
    Sha256 = "38E21AE303A524F616FA39A2D8BDCAE1EA9CA350739B5F313775780BB46F2971"
  }
)

$panelFiles = @(
  "loader_support.py",
  "admin_panel/__init__.py",
  "admin_panel/app.py",
  "admin_panel/cli.py",
  "admin_panel/db.py",
  "admin_panel/html.py",
  "admin_panel/modpack.py",
  "admin_panel/security.py",
  "admin_panel/settings.py"
)

function Assert-ToolAvailable([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required tool not found in PATH: $Name"
  }
}

function Assert-LocalArtifact([hashtable]$FileSpec) {
  $path = Join-Path $ArtifactDir $FileSpec.Name
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Missing local artifact: $path"
  }
  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpperInvariant()
  if ($hash -ne $FileSpec.Sha256) {
    throw "Unexpected SHA-256 for $($FileSpec.Name): $hash"
  }
  return $path
}

function Assert-LocalPanelFile([string]$RelativePath) {
  $localRelativePath = $RelativePath -replace "/", [System.IO.Path]::DirectorySeparatorChar
  $path = Join-Path $projectRoot $localRelativePath
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Missing panel source file: $path"
  }
  return [pscustomobject]@{
    Relative = $RelativePath
    Path = $path
  }
}

function Invoke-CheckedProcess([string]$FileName, [string[]]$Arguments) {
  Write-Host ""
  Write-Host "Running: $FileName $($Arguments -join ' ')"
  if ($DryRun) {
    return
  }
  & $FileName @Arguments
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed with exit code ${LASTEXITCODE}: $FileName"
  }
}

Assert-ToolAvailable "ssh"
Assert-ToolAvailable "scp"

$localPaths = @()
foreach ($fileSpec in $expectedFiles) {
  $localPaths += Assert-LocalArtifact $fileSpec
}

$localPanelFiles = @()
foreach ($relativePath in $panelFiles) {
  $localPanelFiles += Assert-LocalPanelFile $relativePath
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$remoteTemp = "/tmp/mslaunch-upload-$timestamp"
$backupDir = "$BackupRoot/host-upload-$timestamp"
$downloadBackupDir = "$backupDir/downloads"
$appBackupDir = "$backupDir/app"

$names = $expectedFiles | ForEach-Object { $_.Name }
$mkdirScript = "set -eu; mkdir -p '$RemoteDir' '$AppRemoteDir' '$AppRemoteDir/admin_panel' '$remoteTemp' '$remoteTemp/app/admin_panel' '$downloadBackupDir' '$appBackupDir/admin_panel'"
Invoke-CheckedProcess "ssh" @($HostTarget, $mkdirScript)

foreach ($path in $localPaths) {
  Invoke-CheckedProcess "scp" @($path, "${HostTarget}:$remoteTemp/")
}

foreach ($file in $localPanelFiles) {
  Invoke-CheckedProcess "scp" @($file.Path, "${HostTarget}:$remoteTemp/app/$($file.Relative)")
}

$verifyLines = @("set -eu", "cd '$remoteTemp'")
foreach ($fileSpec in $expectedFiles) {
  $verifyLines += "printf '%s  %s\n' '$($fileSpec.Sha256.ToLowerInvariant())' '$($fileSpec.Name)' | sha256sum -c -"
}
foreach ($name in $names) {
  $verifyLines += "if [ -f '$RemoteDir/$name' ]; then cp '$RemoteDir/$name' '$downloadBackupDir/$name'; fi"
}
foreach ($relativePath in $panelFiles) {
  $verifyLines += "if [ -f '$AppRemoteDir/$relativePath' ]; then cp '$AppRemoteDir/$relativePath' '$appBackupDir/$relativePath'; fi"
}
foreach ($name in $names) {
  $verifyLines += "mv -f '$remoteTemp/$name' '$RemoteDir/$name'"
  $verifyLines += "chmod 0644 '$RemoteDir/$name'"
}
foreach ($relativePath in $panelFiles) {
  $verifyLines += "mv -f '$remoteTemp/app/$relativePath' '$AppRemoteDir/$relativePath'"
  $verifyLines += "chmod 0644 '$AppRemoteDir/$relativePath'"
}
$verifyLines += "rmdir '$remoteTemp/app/admin_panel' '$remoteTemp/app' '$remoteTemp'"
$verifyScript = $verifyLines -join "; "
Invoke-CheckedProcess "ssh" @($HostTarget, $verifyScript)

$restartScript = "set -eu; systemctl restart mslaunch-panel.service; systemctl is-active mslaunch-panel.service"
Invoke-CheckedProcess "ssh" @($HostTarget, $restartScript)

if ($DryRun) {
  Write-Host ""
  Write-Host "Dry run complete. Local artifacts and command plan are valid."
  exit 0
}

if (-not $SkipPublicVerify) {
  $bootstrap = Invoke-RestMethod -Uri "https://mslaunch.186.246.12.238.sslip.io/downloads/bootstrap.json" -TimeoutSec 30
  if ($bootstrap.package_sha256 -ne "c859a9338100f74d1a1f420c2f22209a4f0c4271f7b86170398dc08adb341c37") {
    throw "Public bootstrap package_sha256 mismatch: $($bootstrap.package_sha256)"
  }
  if ($bootstrap.setup_sha256 -ne "166e36d6075787fe310fa45af1431e16dc7cb452133a54cd0d06c4d2922b04a3") {
    throw "Public bootstrap setup_sha256 mismatch: $($bootstrap.setup_sha256)"
  }
}

Write-Host ""
Write-Host "Host upload complete and verified."
