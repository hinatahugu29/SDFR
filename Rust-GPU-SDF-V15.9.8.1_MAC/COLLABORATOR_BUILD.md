# macOS collaborator build notes

This copy is for macOS packaging only.

## Build

1. Install Blender 4.x, Rust, and Python 3.11.
2. In this folder, run:
   `chmod +x build_sdf_addon.sh && ./build_sdf_addon.sh`
3. The output zip will be:
   `SDF_R_15_9_8_1_MAC.zip`

## What changed in this copy

- The addon now loads its native module from `rust_gpu_sdf_addon/bin/mac/`.
- The legacy Windows `.pyd` was removed from the package copy.
- A placeholder `bin/mac` folder is kept inside the zip so the package layout stays stable.

## Test goal

Please verify:

- The addon installs from ZIP in Blender.
- Enabling the addon does not raise an import error.
- GPU warm-up starts.
- A simple Sphere or Box can preview and bake successfully.
