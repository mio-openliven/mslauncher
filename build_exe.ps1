$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$exePath = Join-Path $projectRoot "dist\MSLauncher\MSLauncher.exe"

function Invoke-ProjectPython {
  param(
    [Parameter(Mandatory = $true)]
    [string[]]$Arguments
  )

  if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 @Arguments
    return
  }

  & python @Arguments
}

Push-Location $projectRoot
try {
  Invoke-ProjectPython -Arguments @("-m", "PyInstaller", "--noconfirm", "MSLauncher.spec")
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
