$ErrorActionPreference = 'Stop'

# The packaged copy of this script lives beside GuGuGaGa.exe.
$executablePath = Join-Path $PSScriptRoot 'GuGuGaGa.exe'
if (-not (Test-Path -LiteralPath $executablePath -PathType Leaf)) {
    throw 'GuGuGaGa.exe was not found beside this script. Run the copy inside release\GuGuGaGa-v2.2.0.'
}
$executablePath = (Resolve-Path -LiteralPath $executablePath).ProviderPath
$workingDirectory = Split-Path -Parent $executablePath
$desktopDirectory = [Environment]::GetFolderPath('Desktop')
if ([string]::IsNullOrWhiteSpace($desktopDirectory) -or -not (Test-Path -LiteralPath $desktopDirectory -PathType Container)) {
    throw 'The current user Desktop folder is unavailable.'
}

$shellObject = New-Object -ComObject WScript.Shell
$temporaryLink = Join-Path $desktopDirectory ('.gugugaga-' + [Guid]::NewGuid().ToString('N') + '.lnk')
try {
    $shortcut = $shellObject.CreateShortcut($temporaryLink)
    try {
        $shortcut.TargetPath = $executablePath
        $shortcut.WorkingDirectory = $workingDirectory
        $shortcut.IconLocation = $executablePath + ',0'
        $shortcut.Description = 'GuGuGaGa - Knowledge study and spaced repetition'
        $shortcut.Save()
    }
    finally {
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shortcut)
    }

    $number = 1
    while ($true) {
        $name = if ($number -eq 1) { 'GuGuGaGa.lnk' } else { 'GuGuGaGa (' + $number + ').lnk' }
        $shortcutPath = Join-Path $desktopDirectory $name
        if (Test-Path -LiteralPath $shortcutPath) {
            $existing = $null
            $sameTarget = $false
            try {
                $existing = $shellObject.CreateShortcut($shortcutPath)
                if (-not [string]::IsNullOrWhiteSpace($existing.TargetPath)) {
                    $existingTarget = [IO.Path]::GetFullPath([Environment]::ExpandEnvironmentVariables($existing.TargetPath))
                    $sameTarget = [string]::Equals($existingTarget, $executablePath, [StringComparison]::OrdinalIgnoreCase)
                }
            }
            catch {
                # Unreadable or unrelated shortcuts are left untouched.
                $sameTarget = $false
            }
            finally {
                if ($null -ne $existing) {
                    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($existing)
                }
            }
            if ($sameTarget) {
                Write-Output "The desktop shortcut already exists: $shortcutPath"
                return
            }
            $number += 1
            continue
        }
        try {
            # Atomic no-replace publication also protects a shortcut created concurrently.
            [IO.File]::Move($temporaryLink, $shortcutPath)
            Write-Output "Desktop shortcut created: $shortcutPath"
            break
        }
        catch [IO.IOException] {
            if (-not (Test-Path -LiteralPath $shortcutPath)) { throw }
            # Recheck the colliding shortcut before trying a different name.
        }
    }
}
finally {
    if (Test-Path -LiteralPath $temporaryLink) {
        Remove-Item -LiteralPath $temporaryLink -Force
    }
    [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($shellObject)
}
