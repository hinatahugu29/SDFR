# Blender Rust-Accelerated Addon Build Script
# Builds the Rust code and deploys it to the addon folder.

$ErrorActionPreference = "Stop"

# 1. Detect Python 3.11 libs path
$pythonPath = $null
try {
    $pythonPath = (py -3.11 -c "import sys; print(sys.prefix)") 2>$null
} catch {}

if (-not $pythonPath) {
    $fallback = Join-Path $env:LOCALAPPDATA "Programs\Python\Python311"
    if (Test-Path (Join-Path $fallback "libs")) {
        $pythonPath = $fallback
        Write-Host "[INFO] Python 3.11 auto-detect failed. Using fallback: $fallback" -ForegroundColor Yellow
    } else {
        Write-Error "Python 3.11 not found. Please check py -3.11 or fallback path."
        exit 1
    }
}

$pythonLibs = Join-Path $pythonPath "libs"
$pythonExe = Join-Path $pythonPath "python.exe"
$env:PYO3_CROSS_LIB_DIR = $pythonLibs
$env:PYO3_PYTHON = $pythonExe
Write-Host "[INFO] Python libs: $pythonLibs" -ForegroundColor Gray

Write-Host "--- Rust Module Build Start ---" -ForegroundColor Cyan

# 2. Build Rust
Push-Location rust_mesh_core
try {
    cargo build --release
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Rust build failed with exit code $LASTEXITCODE"
        exit 1
    }
} finally {
    Pop-Location
}

# 3. Copy and Rename Binary
$sourceDll = Join-Path "rust_mesh_core" "target\release\rust_mesh_core.dll"
$destPyd = Join-Path "rust_mesh_accelerator" "rust_mesh_core.pyd"

if (Test-Path $sourceDll) {
    Write-Host "Copying binary: $sourceDll -> $destPyd" -ForegroundColor Green
    Copy-Item $sourceDll $destPyd -Force

    # 4. Auto Deploy to Blender AppData Addons directory
    $appData = [Environment]::GetFolderPath("ApplicationData")
    $blenderBase = Join-Path $appData "Blender Foundation\Blender"

    if (Test-Path $blenderBase) {
        $latestVersion = Get-ChildItem $blenderBase -Directory |
            Where-Object { $_.Name -match '^\d+\.\d+$' } |
            Sort-Object { [version]$_.Name } -Descending |
            Select-Object -First 1

        if ($latestVersion) {
            $blenderAddonsDir = Join-Path $latestVersion.FullName "scripts\addons\rust_mesh_accelerator"

            if (!(Test-Path $blenderAddonsDir)) {
                New-Item -ItemType Directory -Path $blenderAddonsDir -Force | Out-Null
            }

            Write-Host "Deploying addon to: $blenderAddonsDir" -ForegroundColor Yellow
            Copy-Item -Path (Join-Path "rust_mesh_accelerator" "*") -Destination $blenderAddonsDir -Recurse -Force

            Write-Host "Build and Deployment Complete! (Blender $($latestVersion.Name))" -ForegroundColor Cyan
            Write-Host "Please restart Blender to reload the addon." -ForegroundColor Cyan
        } else {
            Write-Warning "Blender version folder not found in: $blenderBase"
            Write-Host "Build completed. Manual deployment required." -ForegroundColor Yellow
        }
    } else {
        Write-Warning "Blender AppData directory not found: $blenderBase"
        Write-Host "Build completed. Manual deployment required." -ForegroundColor Yellow
    }
} else {
    Write-Error "Build artifact not found: $sourceDll"
}
