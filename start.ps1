[CmdletBinding()]
param(
    [ValidateRange(1, 65535)][int]$Port = 8766,
    [string]$Data = "",
    [switch]$Rebuild
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
$env:PYTHONUTF8 = "1"

try {
    $pythonCommand = $null
    $pythonPrefix = @()
    foreach ($candidateName in @("python", "python3", "py")) {
        $candidate = Get-Command $candidateName -ErrorAction SilentlyContinue
        if ($null -eq $candidate) { continue }
        $prefix = @()
        if ($candidateName -eq "py") { $prefix = @("-3") }
        try {
            & $candidate.Source @prefix -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>$null
        }
        catch { continue }
        if ($LASTEXITCODE -eq 0) {
            $pythonCommand = $candidate.Source
            $pythonPrefix = $prefix
            break
        }
    }
    if ($null -eq $pythonCommand) {
        throw "Python 3.10+ was not found. Install Python, enable Add to PATH, then reopen the terminal."
    }

    $indexPath = Join-Path $PSScriptRoot "dist/index.html"
    $needsBuild = $Rebuild.IsPresent -or -not (Test-Path -LiteralPath $indexPath)
    if (-not $needsBuild) {
        $builtAt = (Get-Item -LiteralPath $indexPath).LastWriteTimeUtc
        $inputs = @(Get-ChildItem -LiteralPath (Join-Path $PSScriptRoot "src") -Recurse -File)
        foreach ($relative in @("package.json", "package-lock.json", "index.html", "vite.config.ts", "tsconfig.json")) {
            $candidatePath = Join-Path $PSScriptRoot $relative
            if (Test-Path -LiteralPath $candidatePath) { $inputs += Get-Item -LiteralPath $candidatePath }
        }
        $needsBuild = @($inputs | Where-Object { $_.LastWriteTimeUtc -gt $builtAt }).Count -gt 0
    }

    if ($needsBuild) {
        $nodeCommand = Get-Command node -ErrorAction SilentlyContinue
        $npmCommand = Get-Command npm.cmd -ErrorAction SilentlyContinue
        if ($null -eq $npmCommand) { $npmCommand = Get-Command npm -ErrorAction SilentlyContinue }
        if ($null -eq $nodeCommand -or $null -eq $npmCommand) {
            throw "The frontend needs a build. Install Node.js with npm, reopen the terminal, and run start.cmd again."
        }
        if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot "node_modules/.bin/vite"))) {
            Write-Host "Installing frontend dependencies (network required on first run)..."
            & $npmCommand.Source install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed. Check the network/proxy and the error above, then retry." }
        }
        Write-Host "Building the frontend..."
        & $npmCommand.Source run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed. Fix the error above, or run npm install and npm run build manually." }
    }

    $serverArguments = @("-m", "server.app", "--port", "$Port")
    if (-not [string]::IsNullOrWhiteSpace($Data)) { $serverArguments += @("--data", $Data) }
    Write-Host ""
    Write-Host "Open http://127.0.0.1:$Port in your browser. Press Ctrl+C here to stop."
    Write-Host "The server stays in this terminal; no extra background window is created."
    & $pythonCommand @pythonPrefix @serverArguments
    exit $LASTEXITCODE
}
catch {
    Write-Host ""
    Write-Host "GuGuGaGa could not start: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
