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
$zipFile = "SDF_R_16_0_4.zip"

$zipPath = Join-Path (Get-Location) $zipFile
$compatZipPath = Join-Path (Get-Location) "rust_gpu_sdf_addon.zip"
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
if (Test-Path $compatZipPath) {
    Remove-Item $compatZipPath -Force -ErrorAction SilentlyContinue
    if (Test-Path $compatZipPath) {
        Write-Warning "Compatibility ZIP is locked and will not be refreshed: $compatZipPath"
    }
}

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
if (!(Test-Path $compatZipPath)) {
    Copy-Item -LiteralPath $zipPath -Destination $compatZipPath -Force -ErrorAction SilentlyContinue
    if (!(Test-Path $compatZipPath)) {
        Write-Warning "Compatibility ZIP could not be created: $compatZipPath"
    }
}

Write-Host "--- Validating Package ---" -ForegroundColor Cyan
$validateScript = @'
import importlib
import os
import sys
import zipfile

addon = os.path.abspath(r"__ADDON_DIR__")
zip_path = os.path.abspath(r"__ZIP_FILE__")
required = {
    "rust_gpu_sdf_addon/__init__.py",
    "rust_gpu_sdf_addon/rust_gpu_sdf.pyd",
    "rust_gpu_sdf_addon/bin/win/rust_gpu_sdf.pyd",
    "rust_gpu_sdf_addon/assets/nodes.blend",
}

if not os.path.exists(os.path.join(addon, "rust_gpu_sdf.pyd")):
    raise SystemExit("Missing deployed pyd in addon root")
if not os.path.exists(os.path.join(addon, "bin", "win", "rust_gpu_sdf.pyd")):
    raise SystemExit("Missing deployed Windows pyd")

with zipfile.ZipFile(zip_path) as zf:
    names = set(zf.namelist())
    missing = sorted(required - names)
    if missing:
        raise SystemExit("Package missing entries: " + ", ".join(missing))
    bad = [name for name in names if "__pycache__" in name or name.endswith(".pyc")]
    if bad:
        raise SystemExit("Package contains Python cache files: " + ", ".join(sorted(bad)))

sys.path.insert(0, addon)
importlib.import_module("rust_gpu_sdf")
print("Validation Complete")
'@
$validateScript = $validateScript.Replace("__ADDON_DIR__", $addonDir).Replace("__ZIP_FILE__", $zipFile)
$validateScriptPath = Join-Path $env:TEMP "sdf_validate_package.py"
Set-Content -LiteralPath $validateScriptPath -Value $validateScript -Encoding UTF8
& py -3.11 $validateScriptPath
$validateExit = $LASTEXITCODE
Remove-Item -LiteralPath $validateScriptPath -Force -ErrorAction SilentlyContinue
if ($validateExit -ne 0) { throw "Package validation failed with exit code $validateExit" }

Write-Host "Package Complete: $zipFile" -ForegroundColor Green
