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
    Sha256 = "D25FB662A47EA4EF346F680B2F4FD00C626A629EDD2DFC48C8674E4AE07744ED"
  },
  @{
    Name = "MSLaunchSetup.exe"
    Sha256 = "921AA8902A0FEF513930C935AE0D7825B9ADADE0510B52377095700F45810B94"
  },
  @{
    Name = "bootstrap.json"
    Sha256 = "F4D6101A8404C17744F07C6B7408DDD6DBF5C3E3B7FC70E09997296868C5C534"
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
  if ($bootstrap.package_sha256 -ne "d25fb662a47ea4ef346f680b2f4fd00c626a629edd2dfc48c8674e4ae07744ed") {
    throw "Public bootstrap package_sha256 mismatch: $($bootstrap.package_sha256)"
  }
  if ($bootstrap.setup_sha256 -ne "921aa8902a0fef513930c935ae0d7825b9adade0510b52377095700f45810b94") {
    throw "Public bootstrap setup_sha256 mismatch: $($bootstrap.setup_sha256)"
  }
}

Write-Host ""
Write-Host "Host upload complete and verified."
