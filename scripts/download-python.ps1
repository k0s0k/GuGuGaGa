[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
$cacheDirectory = Join-Path $projectRoot ".local"
$runtimeDirectory = Join-Path $cacheDirectory "desktop-python"
$archivePath = Join-Path $cacheDirectory "python-3.13.9-embed-amd64.zip"
$downloadUrl = "https://www.python.org/ftp/python/3.13.9/python-3.13.9-embed-amd64.zip"
# SHA-256 published in the official python.org .sigstore messageDigest.
$expectedHash = "91d828c2da3a029b41699e918674a0cb379c02cf20dab9c501306885f837402a"

New-Item -ItemType Directory -Path $cacheDirectory -Force | Out-Null
if (-not (Test-Path -LiteralPath $archivePath)) {
    Write-Host "Downloading the official Python 3.13.9 embeddable runtime..."
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath
}
$actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash
if ($actualHash -ne $expectedHash) {
    throw "The Python archive failed SHA-256 validation. Remove '$archivePath' and retry."
}

New-Item -ItemType Directory -Path $runtimeDirectory -Force | Out-Null
Expand-Archive -LiteralPath $archivePath -DestinationPath $runtimeDirectory -Force
& (Join-Path $runtimeDirectory "python.exe") -c "import json, sys; print('Bundled runtime:', sys.version.split()[0]); assert sys.version_info[:3] == (3, 13, 9)"
if ($LASTEXITCODE -ne 0) { throw "The embedded Python runtime could not start." }
Write-Host "Python runtime is ready at $runtimeDirectory"
