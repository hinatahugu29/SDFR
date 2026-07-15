#!/bin/bash
# SDF Addon Build Script for macOS and Linux

set -e

# Change to the directory where the script is located
cd "$(dirname "$0")"

echo -e "\033[0;36m--- Rust SDF Module Build Start ---\033[0m"

# 1. Detect Python 3.11 libs path
# PyO3 will automatically detect Python from the active environment if `python3` or `python` is in PATH.
# Alternatively, you can ensure PYO3_PYTHON is set.
export PYO3_PYTHON=$(which python3.11 || which python3)

echo "Using Python for PyO3: $PYO3_PYTHON"

# 2. Build Rust
if [ "$(uname)" == "Darwin" ]; then
    export RUSTFLAGS="-C link-arg=-undefined -C link-arg=dynamic_lookup"
fi
cargo build --release

# 3. Deploy
# On Linux and macOS, the output is .so or .dylib, but PyO3 expects .so extension for the python module
ADDON_DIR="rust_gpu_sdf_addon"
mkdir -p "$ADDON_DIR"

if [ "$(uname)" == "Darwin" ]; then
    # macOS
    SOURCE_DLL="target/release/librust_gpu_sdf.dylib"
    BIN_DIR="$ADDON_DIR/bin/mac"
else
    # Linux
    SOURCE_DLL="target/release/librust_gpu_sdf.so"
    BIN_DIR="$ADDON_DIR/bin/linux"
fi

DEST_PYD="$ADDON_DIR/rust_gpu_sdf.so"

cp -f "$SOURCE_DLL" "$DEST_PYD"
mkdir -p "$BIN_DIR"
cp -f "$SOURCE_DLL" "$BIN_DIR/rust_gpu_sdf.so"

echo -e "\033[0;32mBuild Complete: $DEST_PYD\033[0m"

# 4. Packaging (ZIP)
echo -e "\033[0;36m--- Packaging Addon ZIP ---\033[0m"
ZIP_FILE="SDF_R_16_0_4_$(uname).zip"
COMPAT_ZIP="rust_gpu_sdf_addon_$(uname).zip"

rm -f "$ZIP_FILE" "$COMPAT_ZIP"
rm -rf "$ADDON_DIR/__pycache__"

# Include the addon folder at the archive root using Python's zipfile
ZIP_SCRIPT=$(mktemp)
cat << 'EOF' > "$ZIP_SCRIPT"
import os
import zipfile
import sys

src = os.path.abspath(sys.argv[1])
dst = os.path.abspath(sys.argv[2])
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
EOF

"$PYO3_PYTHON" "$ZIP_SCRIPT" "$ADDON_DIR" "$ZIP_FILE"
rm -f "$ZIP_SCRIPT"

if [ ! -f "$ZIP_FILE" ]; then
    echo "Package was not created: $ZIP_FILE"
    exit 1
fi

cp -f "$ZIP_FILE" "$COMPAT_ZIP"

echo -e "\033[0;36m--- Validating Package ---\033[0m"
"$PYO3_PYTHON" - "$ADDON_DIR" "$ZIP_FILE" << 'PY'
import importlib
import os
import sys
import zipfile

addon = os.path.abspath(sys.argv[1])
zip_path = os.path.abspath(sys.argv[2])
required = {
    "rust_gpu_sdf_addon/__init__.py",
    "rust_gpu_sdf_addon/rust_gpu_sdf.so",
    "rust_gpu_sdf_addon/assets/nodes.blend",
}

if not os.path.exists(os.path.join(addon, "rust_gpu_sdf.so")):
    raise SystemExit("Missing deployed extension in addon root")

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
PY

echo -e "\033[0;32mPackage Complete: $ZIP_FILE\033[0m"
