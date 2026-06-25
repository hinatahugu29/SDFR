#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN="python3.11"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "Python 3 is required." >&2
  exit 1
fi

export PYO3_PYTHON="$PYTHON_BIN"
export PYO3_BUILD_EXTENSION_MODULE=1

echo "--- Rust SDF Module Build Start (macOS) ---"
cargo build --release

EXT_SUFFIX="$("$PYTHON_BIN" - <<'PY'
import sysconfig
print(sysconfig.get_config_var("EXT_SUFFIX") or ".so")
PY
)"

SOURCE_FILE=""
for candidate in \
  "target/release/librust_gpu_sdf.dylib" \
  "target/release/librust_gpu_sdf.so" \
  "target/release/rust_gpu_sdf.so"
do
  if [[ -f "$candidate" ]]; then
    SOURCE_FILE="$candidate"
    break
  fi
done

if [[ -z "$SOURCE_FILE" ]]; then
  echo "Build artifact not found in target/release." >&2
  exit 1
fi

ADDON_DIR="rust_gpu_sdf_addon"
BIN_DIR="$ADDON_DIR/bin/mac"
mkdir -p "$BIN_DIR"
find "$BIN_DIR" -maxdepth 1 -type f -name 'rust_gpu_sdf*' ! -name 'README.txt' -delete

DEST_FILE="$BIN_DIR/rust_gpu_sdf${EXT_SUFFIX}"
cp "$SOURCE_FILE" "$DEST_FILE"

# Keep the addon folder itself ready for direct zipping.
find "$ADDON_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "$ADDON_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

echo "Build Complete: $DEST_FILE"
echo "Addon folder ready: $ADDON_DIR"
echo "You can zip the rust_gpu_sdf_addon folder directly for distribution."
echo "--- Packaging Addon ZIP ---"

ZIP_FILE="SDF_R_15_9_8_1_MAC.zip"
rm -f "$ZIP_FILE"

"$PYTHON_BIN" - <<'PY'
import os
import zipfile

src = os.path.abspath("rust_gpu_sdf_addon")
dst = os.path.abspath("SDF_R_15_9_8_1_MAC.zip")
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
PY

echo "Package Complete: $ZIP_FILE"
