# SDF Addon Build Script
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot

# 1. Detect Python 3.11 libs path
$pythonPath = (py -3.11 -c "import sys; print(sys.prefix)")
$pythonLibs = Join-Path $pythonPath "libs"
$pythonExe = Join-Path $pythonPath "python.exe"
$env:PYO3_CROSS_LIB_DIR = $pythonLibs
$env:PYO3_PYTHON = $pythonExe

Write-Host "--- Rust SDF Module Build Start ---" -ForegroundColor Cyan

# 2. Build Rust
cargo build --release

# 3. Deploy
$sourceDll = "target\release\rust_gpu_sdf.dll"
$addonDir = "rust_gpu_sdf_addon"
if (!(Test-Path $addonDir)) { New-Item -ItemType Directory -Path $addonDir }

$destPyd = Join-Path $addonDir "rust_gpu_sdf.pyd"
Copy-Item $sourceDll $destPyd -Force
$binWinDir = Join-Path $addonDir "bin\win"
if (!(Test-Path $binWinDir)) { New-Item -ItemType Directory -Path $binWinDir -Force | Out-Null }
Copy-Item $sourceDll (Join-Path $binWinDir "rust_gpu_sdf.pyd") -Force

Write-Host "Build Complete: $destPyd" -ForegroundColor Green

# 4. Packaging (ZIP)
Write-Host "--- Packaging Addon ZIP ---" -ForegroundColor Cyan
$zipFile = "SDF_R_15_9_8_1.zip"

$zipPath = Join-Path (Get-Location) $zipFile
$compatZipPath = Join-Path (Get-Location) "rust_gpu_sdf_addon.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
if (Test-Path $compatZipPath) { Remove-Item $compatZipPath -Force }

$pycacheDir = Join-Path $addonDir "__pycache__"
if (Test-Path $pycacheDir) { Remove-Item $pycacheDir -Recurse -Force }

# Include the addon folder at the archive root.
$zipScript = @'
import os
import zipfile

src = os.path.abspath(r"__ADDON_DIR__")
dst = os.path.abspath(r"__ZIP_FILE__")
base = os.path.basename(src.rstrip("\\/"))

with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for name in files:
            if name.endswith(".pyc"):
                continue
            full = os.path.join(root, name)
            rel = os.path.join(base, os.path.relpath(full, src))
            zf.write(full, rel)
'@
$zipScript = $zipScript.Replace("__ADDON_DIR__", $addonDir).Replace("__ZIP_FILE__", $zipFile)
$zipScriptPath = Join-Path $env:TEMP "sdf_zip_pack.py"
Set-Content -LiteralPath $zipScriptPath -Value $zipScript -Encoding UTF8
& py -3.11 $zipScriptPath
$zipExit = $LASTEXITCODE
Remove-Item -LiteralPath $zipScriptPath -Force -ErrorAction SilentlyContinue
if ($zipExit -ne 0) { throw "Python packaging failed with exit code $zipExit" }
if (!(Test-Path $zipPath)) { throw "Package was not created: $zipPath" }
Copy-Item -LiteralPath $zipPath -Destination $compatZipPath -Force

Write-Host "Package Complete: $zipFile" -ForegroundColor Green
