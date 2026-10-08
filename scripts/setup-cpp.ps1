param([switch]$DownloadOnly)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$projectRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..'))
$toolchainRoot = Join-Path $projectRoot '.local\toolchains'
$compilerPath = Join-Path $toolchainRoot 'w64devkit\bin\g++.exe'
$version = '2.10.0'
$filename = "w64devkit-x64-$version.7z.exe"
$archivePath = Join-Path $toolchainRoot $filename
$downloadUrl = "https://github.com/skeeto/w64devkit/releases/download/v$version/$filename"
# SHA-256 published by the official GitHub release asset API.
$expectedHash = '18d0a4c71a166f8401ab6305781bec5882b40b5e06ba9807c61cb5f3b3c6325e'

if (Test-Path -LiteralPath $compilerPath) {
    Write-Output "C++ compiler already available: $compilerPath"
    & $compilerPath --version | Select-Object -First 1
    exit 0
}

New-Item -ItemType Directory -Path $toolchainRoot -Force | Out-Null
if (-not (Test-Path -LiteralPath $archivePath)) {
    Write-Output "Downloading project-local w64devkit $version from the official release..."
    Invoke-WebRequest -Uri $downloadUrl -OutFile $archivePath -TimeoutSec 180
}
$actualHash = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actualHash -ne $expectedHash) {
    throw "SHA-256 mismatch; archive was NOT executed. Expected $expectedHash, got $actualHash."
}
Write-Output 'SHA-256 verified.'
if ($DownloadOnly) { exit 0 }

# This is a self-extracting archive, not a system installer. It writes only
# beneath .local/toolchains and does not change PATH, registry, or user settings.
$extractArguments = @('-y', ('-o"' + $toolchainRoot + '"'))
$extractProcess = Start-Process -FilePath $archivePath -ArgumentList $extractArguments -WindowStyle Hidden -Wait -PassThru
if ($extractProcess.ExitCode -ne 0 -or -not (Test-Path -LiteralPath $compilerPath)) {
    throw "Toolchain extraction failed with exit code $($extractProcess.ExitCode)."
}
Write-Output "C++ compiler ready: $compilerPath"
& $compilerPath --version | Select-Object -First 1
