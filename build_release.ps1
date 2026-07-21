# Creates a complete Windows release folder, then compiles OnlyMyFace-Setup.exe
# when Inno Setup 6 is installed.  End users never need Python.
param(
  [string]$Python = "py",
  [string[]]$PythonArgs = @("-3.12")
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = $PSScriptRoot
$StageRoot = Join-Path $ProjectRoot 'release\OnlyMyFace-build'
$RuntimeRoot = Join-Path $StageRoot 'runtime'
$ModelSource = Join-Path $env:USERPROFILE '.insightface\models\buffalo_l'
$ModelDestination = Join-Path $StageRoot 'models\insightface\models\buffalo_l'

& $Python @PythonArgs -c "import insightface, onnxruntime; print('Runtime check:', onnxruntime.__version__)"
if ($LASTEXITCODE -ne 0) { throw 'The selected Python does not have the required app packages.' }

if (-not (Test-Path -LiteralPath $ModelSource)) {
  throw "buffalo_l model is missing. Start the development app once and process a photo first: $ModelSource"
}

if (Test-Path -LiteralPath $StageRoot) {
  Remove-Item -LiteralPath $StageRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $RuntimeRoot, $ModelDestination | Out-Null

# Copy the known-good Python installation used to run the app.  A venv is not
# used because it still points to a Python installation on the build PC.
$PythonHome = & $Python @PythonArgs -c "import sys; print(sys.prefix)"
Copy-Item -Path (Join-Path $PythonHome '*') -Destination $RuntimeRoot -Recurse -Force

# A normal Python installation carries documentation, package test suites, pip
# and bytecode caches.  They are never used by the installed app and otherwise
# add hundreds of MB (especially ONNX's model-test corpus) to the installer.
@(
  (Join-Path $RuntimeRoot 'Doc'),
  (Join-Path $RuntimeRoot 'Lib\test'),
  (Join-Path $RuntimeRoot 'Lib\ensurepip'),
  (Join-Path $RuntimeRoot 'Lib\site-packages\pip'),
  (Join-Path $RuntimeRoot 'Lib\site-packages\setuptools'),
  (Join-Path $RuntimeRoot 'Lib\site-packages\wheel')
) | ForEach-Object {
  if (Test-Path -LiteralPath $_) { Remove-Item -LiteralPath $_ -Recurse -Force }
}
# Do NOT strip folders named "testing": numpy/testing and similar are real
# importable submodules other packages depend on at runtime (e.g. scipy's
# array_api_compat imports numpy.testing), not just test suites.
Get-ChildItem -LiteralPath (Join-Path $RuntimeRoot 'Lib\site-packages') -Directory -Recurse |
  Where-Object { $_.Name -in @('__pycache__', 'tests', 'test') } |
  Sort-Object { $_.FullName.Length } -Descending |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue }

Copy-Item -LiteralPath (Join-Path $ProjectRoot 'app.py') -Destination $StageRoot -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'assets') -Destination $StageRoot -Recurse -Force
Copy-Item -LiteralPath (Join-Path $ProjectRoot 'installer\OnlyMyFace.vbs') -Destination $StageRoot -Force
Copy-Item -Path (Join-Path $ModelSource '*') -Destination $ModelDestination -Recurse -Force

& (Join-Path $RuntimeRoot 'python.exe') -c "import customtkinter, insightface, onnxruntime; print('Bundled runtime is ready')"
if ($LASTEXITCODE -ne 0) { throw 'The staged runtime could not import the required packages.' }

$InnoSetup = Get-Command iscc.exe -ErrorAction SilentlyContinue
if (-not $InnoSetup) {
  $KnownInnoPaths = @(
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles}\Inno Setup 7\ISCC.exe"
  )
  $InnoSetupPath = $KnownInnoPaths | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
  if ($InnoSetupPath) {
    $InnoSetup = [pscustomobject]@{ Source = $InnoSetupPath }
  }
}
if (-not $InnoSetup) {
  throw 'Release folder is ready, but Inno Setup 6 is required to make OnlyMyFace-Setup.exe. Install it, then run this script again.'
}

& $InnoSetup.Source (Join-Path $ProjectRoot 'installer\OnlyMyFace.iss')
if ($LASTEXITCODE -ne 0) { throw 'Inno Setup compilation failed.' }
Write-Host "Installer created: $(Join-Path $ProjectRoot 'dist\OnlyMyFace-Setup.exe')"
