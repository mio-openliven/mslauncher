param(
  [string]$HostTarget = "root@186.246.12.238",
  [string]$RemoteDir = "/opt/mslaunch/data/downloads",
  [string]$RemoteAppDir = "/opt/mslaunch/app",
  [string]$PanelService = "mslaunch-panel.service",
  [string]$ArtifactDir = "",
  [switch]$DryRun,
  [switch]$SkipPanelRestart,
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

$expectedAppFiles = @(
  @{
    Name = "loader_support.py"
    Path = Join-Path $projectRoot "loader_support.py"
    Sha256 = "3024C90BCBB86668369804649C5F191D7915839C98BAB9DD4B94DF33A7C3B2A4"
  }
)

function Assert-ToolAvailable([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required tool not found in PATH: $Name"
  }
}

function Assert-LocalFile([hashtable]$FileSpec) {
  if ($FileSpec.ContainsKey("Path")) {
    $path = $FileSpec.Path
  } else {
    $path = Join-Path $ArtifactDir $FileSpec.Name
  }
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
    throw "Missing local file: $path"
  }
  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash.ToUpperInvariant()
  if ($hash -ne $FileSpec.Sha256) {
    throw "Unexpected SHA-256 for $($FileSpec.Name): $hash"
  }
  return $path
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

if ($PanelService -notmatch '^[A-Za-z0-9_.@-]+$') {
  throw "Unsafe panel service name: $PanelService"
}

$localPaths = @()
foreach ($fileSpec in ($expectedFiles + $expectedAppFiles)) {
  $localPaths += Assert-LocalFile $fileSpec
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$remoteTemp = "/tmp/mslaunch-upload-$timestamp"
$backupDir = "$RemoteDir/backup-$timestamp"
$appBackupDir = "$backupDir/app"

$names = $expectedFiles | ForEach-Object { $_.Name }
$appNames = $expectedAppFiles | ForEach-Object { $_.Name }
$mkdirScript = "set -eu; mkdir -p '$RemoteDir' '$RemoteAppDir' '$remoteTemp' '$backupDir' '$appBackupDir'"
Invoke-CheckedProcess "ssh" @($HostTarget, $mkdirScript)

foreach ($path in $localPaths) {
  Invoke-CheckedProcess "scp" @($path, "${HostTarget}:$remoteTemp/")
}

$verifyLines = @("set -eu", "cd '$remoteTemp'")
foreach ($fileSpec in ($expectedFiles + $expectedAppFiles)) {
  $verifyLines += "printf '%s  %s\n' '$($fileSpec.Sha256.ToLowerInvariant())' '$($fileSpec.Name)' | sha256sum -c -"
}
foreach ($name in $names) {
  $verifyLines += "if [ -f '$RemoteDir/$name' ]; then cp '$RemoteDir/$name' '$backupDir/$name'; fi"
}
foreach ($name in $names) {
  $verifyLines += "mv -f '$remoteTemp/$name' '$RemoteDir/$name'"
  $verifyLines += "chmod 0644 '$RemoteDir/$name'"
}
foreach ($name in $appNames) {
  $verifyLines += "if [ -f '$RemoteAppDir/$name' ]; then cp '$RemoteAppDir/$name' '$appBackupDir/$name'; fi"
}
foreach ($name in $appNames) {
  $verifyLines += "mv -f '$remoteTemp/$name' '$RemoteAppDir/$name'"
  $verifyLines += "chmod 0644 '$RemoteAppDir/$name'"
}
if (-not $SkipPanelRestart) {
  $verifyLines += "systemctl restart '$PanelService'"
}
$verifyLines += "rmdir '$remoteTemp'"
$verifyScript = $verifyLines -join "; "
Invoke-CheckedProcess "ssh" @($HostTarget, $verifyScript)

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
