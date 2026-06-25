# Linux collaborator build notes

This copy is for Linux packaging only.

## Build

1. Install Blender 4.x, Rust, and Python 3.11.
2. In this folder, run:
   `chmod +x build_sdf_addon.sh && ./build_sdf_addon.sh`
3. After the build, `rust_gpu_sdf_addon` itself is ready for distribution.
4. Zip the `rust_gpu_sdf_addon` folder directly if you want to package it by hand.
5. A convenience archive is also created as:
   `SDF_R_15_9_8_1_LINUX.zip`

## What changed in this copy

- The addon now loads its native module from `rust_gpu_sdf_addon/bin/linux/`.
- The folder is cleaned so `__pycache__` and `.pyc` files are not part of the distributable addon.
- The legacy Windows `.pyd` was removed from the package copy.

## Test goal

Please verify:

- The addon installs from ZIP in Blender.
- Enabling the addon does not raise an import error.
- GPU warm-up starts.
- A simple Sphere or Box can preview and bake successfully.
