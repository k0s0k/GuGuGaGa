[CmdletBinding()]
param()

# Encode the approved artwork for the browser and Windows icon resources.
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$projectRoot = Split-Path -Parent $PSScriptRoot
$source = [Drawing.Image]::FromFile((Join-Path $projectRoot 'packaging/gugugaga-icon-source.png'))
function Get-PngBytes([int]$size) {
    $bitmap = [Drawing.Bitmap]::new($size, $size, [Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $graphics = [Drawing.Graphics]::FromImage($bitmap)
    $stream = [IO.MemoryStream]::new()
    try {
        $graphics.Clear([Drawing.Color]::Transparent)
        $graphics.InterpolationMode = [Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
        $graphics.PixelOffsetMode = [Drawing.Drawing2D.PixelOffsetMode]::HighQuality
        $graphics.DrawImage($source, [Drawing.Rectangle]::new(0, 0, $size, $size))
        $bitmap.Save($stream, [Drawing.Imaging.ImageFormat]::Png)
        return ,$stream.ToArray()
    } finally {
        $graphics.Dispose()
        $bitmap.Dispose()
        $stream.Dispose()
    }
}
try {
    [IO.File]::WriteAllBytes((Join-Path $projectRoot 'public/gugugaga-icon.png'), (Get-PngBytes 512))
    $sizes = @(16, 24, 32, 48, 64, 128, 256)
    $frames = @($sizes | ForEach-Object { ,(Get-PngBytes $_) })
    $file = [IO.File]::Create((Join-Path $projectRoot 'packaging/GuGuGaGa.ico'))
    $writer = [IO.BinaryWriter]::new($file)
    try {
        $writer.Write([uint16]0)
        $writer.Write([uint16]1)
        $writer.Write([uint16]$sizes.Count)
        $offset = 6 + 16 * $sizes.Count
        for ($index = 0; $index -lt $sizes.Count; $index++) {
            $edge = if ($sizes[$index] -eq 256) { 0 } else { $sizes[$index] }
            $writer.Write([byte]$edge)
            $writer.Write([byte]$edge)
            $writer.Write([byte]0)
            $writer.Write([byte]0)
            $writer.Write([uint16]1)
            $writer.Write([uint16]32)
            $writer.Write([uint32]$frames[$index].Length)
            $writer.Write([uint32]$offset)
            $offset += $frames[$index].Length
        }
        foreach ($frame in $frames) { $writer.Write([byte[]]$frame) }
    } finally {
        $writer.Dispose()
        $file.Dispose()
    }
} finally {
    $source.Dispose()
}
Write-Host 'Generated GuGuGaGa browser icon and seven Windows icon sizes.'
