$ErrorActionPreference = "Stop"

# WIDER FACE is useful for local detector testing because it contains varied
# pose, scale, occlusion and crowd scenes. Keep the downloaded dataset outside
# the release assets; the project only stores a small local validation sample.
$root = Split-Path -Parent $PSScriptRoot
$target = Join-Path $root "test_images\wider_face_sample"
$archive = Join-Path ([IO.Path]::GetTempPath()) "OnlyMyFace-WIDER_val.zip"
$url = "https://huggingface.co/datasets/wider_face/resolve/main/data/WIDER_val.zip?download=true"

New-Item -ItemType Directory -Force -Path $target | Out-Null
if (-not (Test-Path $archive)) {
    Write-Host "Downloading WIDER FACE validation archive..."
    Invoke-WebRequest -Uri $url -OutFile $archive
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [IO.Compression.ZipFile]::OpenRead($archive)
try {
    $entries = @($zip.Entries | Where-Object { $_.FullName -match '\.(jpg|jpeg|png)$' } | Select-Object -First 24)
    if (-not $entries.Count) { throw "No image entries found in the archive." }
    foreach ($entry in $entries) {
        $name = Split-Path $entry.FullName -Leaf
        $destination = Join-Path $target $name
        if (Test-Path $destination) { continue }
        [IO.Compression.ZipFileExtensions]::ExtractToFile($entry, $destination)
    }
}
finally {
    $zip.Dispose()
}

@"
WIDER FACE validation sample

Source: https://huggingface.co/datasets/wider_face
Original dataset page: http://shuoyang1213.me/WIDERFACE/
License: Creative Commons BY-NC-ND (see the original dataset terms)

These images are for local detector testing only. Do not include this folder
in the public Only My Face release or redistribute the images.
"@ | Set-Content -Encoding UTF8 (Join-Path $target "README.txt")

Write-Host "Saved $($entries.Count) local test images to $target"
