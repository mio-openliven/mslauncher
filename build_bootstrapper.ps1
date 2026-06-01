$ErrorActionPreference = "Stop"

$projectRoot = $PSScriptRoot
$exePath = Join-Path $projectRoot "dist\MSLaunchSetup.exe"
$sourcePath = Join-Path $projectRoot "setup_bootstrapper\MSLaunchSetup.cs"
$cscPath = Join-Path $env:WINDIR "Microsoft.NET\Framework64\v4.0.30319\csc.exe"
if (-not (Test-Path -LiteralPath $cscPath -PathType Leaf)) {
  $cscPath = Join-Path $env:WINDIR "Microsoft.NET\Framework\v4.0.30319\csc.exe"
}
if (-not (Test-Path -LiteralPath $cscPath -PathType Leaf)) {
  throw "Build failed: csc.exe was not found."
}

Push-Location $projectRoot
try {
  New-Item -ItemType Directory -Force -Path "dist" | Out-Null
  if (Test-Path -LiteralPath $exePath -PathType Leaf) {
    Remove-Item -LiteralPath $exePath -Force
  }
  & $cscPath `
    /nologo `
    /target:winexe `
    /optimize+ `
    /out:$exePath `
    /win32icon:assets\app_icon.ico `
    /reference:System.Windows.Forms.dll `
    /reference:System.Drawing.dll `
    /reference:System.Web.Extensions.dll `
    /reference:System.IO.Compression.dll `
    /reference:System.IO.Compression.FileSystem.dll `
    $sourcePath
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
