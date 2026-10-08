[CmdletBinding()]
param(
    [switch]$SkipFrontend,
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$env:PYTHONUTF8 = "1"
$env:PYINSTALLER_CONFIG_DIR = Join-Path $projectRoot ".local/pyinstaller-cache"
$env:PYTHONUSERBASE = Join-Path $projectRoot ".local/package-userbase"
$env:PYTHONNOUSERSITE = "1"
$packagingPython = Join-Path $projectRoot ".local/package-env/Scripts/python.exe"

if (-not (Test-Path -LiteralPath $packagingPython)) {
    & python -m venv (Join-Path $projectRoot ".local/package-env")
    if ($LASTEXITCODE -ne 0) { throw "Creating the packaging environment failed (Python 3.10+ is required)." }
}
if (-not $SkipInstall) {
    & $packagingPython -m pip install --disable-pip-version-check -r (Join-Path $projectRoot "requirements-desktop.txt")
    if ($LASTEXITCODE -ne 0) { throw "Installing desktop build dependencies failed." }
}

& (Join-Path $PSScriptRoot "download-python.ps1")

$compiler = Join-Path $projectRoot ".local/toolchains/w64devkit/bin/g++.exe"
if (-not (Test-Path -LiteralPath $compiler)) {
    throw "The portable C++ toolchain is missing. Run scripts/setup-cpp.ps1 before building."
}
if (-not $SkipFrontend) {
    & npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "Building the frontend failed." }
}

$releaseRoot = Join-Path $projectRoot "release"
$workRoot = Join-Path $projectRoot ".local/pyinstaller"
# --noconfirm overwrites only PyInstaller's generated CodeRecall release directory.
& $packagingPython -m PyInstaller --noconfirm --clean --distpath $releaseRoot --workpath $workRoot (Join-Path $projectRoot "packaging/CodeRecall.spec")
if ($LASTEXITCODE -ne 0) { throw "Packaging CodeRecall failed." }

$releaseDirectory = Join-Path $releaseRoot "CodeRecall"
Copy-Item -LiteralPath (Join-Path $projectRoot "README.md") -Destination (Join-Path $releaseDirectory "README.md") -Force
Copy-Item -LiteralPath (Join-Path $projectRoot "packaging/THIRD-PARTY-NOTICES.txt") -Destination (Join-Path $releaseDirectory "THIRD-PARTY-NOTICES.txt") -Force
foreach ($shortcutFile in @("create-shortcut.cmd", "create-shortcut.ps1")) {
    $shortcutSource = Join-Path $projectRoot "packaging/$shortcutFile"
    if (Test-Path -LiteralPath $shortcutSource) {
        Copy-Item -LiteralPath $shortcutSource -Destination (Join-Path $releaseDirectory $shortcutFile) -Force
    }
}
Write-Host ""
Write-Host "Build complete: $releaseDirectory/CodeRecall.exe"
Write-Host "Distribute the entire CodeRecall directory; the executable needs its _internal directory."
