param(
  [string]$HostTarget = "root@186.246.12.238",
  [string]$RemoteDir = "/opt/mslaunch/data/downloads",
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
    Sha256 = "D17D011D64CFF1F523C4B2BFC45571D79002809BEB6D6D73E0ED81892D6A717E"
  },
  @{
    Name = "MSLaunchSetup.exe"
    Sha256 = "47AECEADCFD2A2E01456DB2B5507263BE2280505C785FD88DE379807434D27DA"
  },
  @{
    Name = "bootstrap.json"
    Sha256 = "99ED2C3340E6795B45C9B04F9401A4227B26CE570BBFD7525F6BE79C091F7C56"
  }
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

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$remoteTemp = "/tmp/mslaunch-upload-$timestamp"
$backupDir = "$RemoteDir/backup-$timestamp"

$names = $expectedFiles | ForEach-Object { $_.Name }
$mkdirScript = "set -eu; mkdir -p '$RemoteDir' '$remoteTemp' '$backupDir'"
Invoke-CheckedProcess "ssh" @($HostTarget, $mkdirScript)

foreach ($path in $localPaths) {
  Invoke-CheckedProcess "scp" @($path, "${HostTarget}:$remoteTemp/")
}

$verifyLines = @("set -eu", "cd '$remoteTemp'")
foreach ($fileSpec in $expectedFiles) {
  $verifyLines += "printf '%s  %s\n' '$($fileSpec.Sha256.ToLowerInvariant())' '$($fileSpec.Name)' | sha256sum -c -"
}
foreach ($name in $names) {
  $verifyLines += "if [ -f '$RemoteDir/$name' ]; then cp '$RemoteDir/$name' '$backupDir/$name'; fi"
}
foreach ($name in $names) {
  $verifyLines += "mv -f '$remoteTemp/$name' '$RemoteDir/$name'"
  $verifyLines += "chmod 0644 '$RemoteDir/$name'"
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
  if ($bootstrap.package_sha256 -ne "d17d011d64cff1f523c4b2bfc45571d79002809beb6d6d73e0ed81892d6a717e") {
    throw "Public bootstrap package_sha256 mismatch: $($bootstrap.package_sha256)"
  }
  if ($bootstrap.setup_sha256 -ne "47aeceadcfd2a2e01456db2b5507263be2280505c785fd88de379807434d27da") {
    throw "Public bootstrap setup_sha256 mismatch: $($bootstrap.setup_sha256)"
  }
}

Write-Host ""
Write-Host "Host upload complete and verified."
