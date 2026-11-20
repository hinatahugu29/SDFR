SDF.R V17.0.3 - distribution packages
built 2026-11-21 / local Windows build (build_sdf_addon.ps1) from the Rust-GPU-SDF-V17.0.3_CI tree / macOS and Linux pending CI

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_17_0_3.zip | 14,655,117 | 12ed7bef8f6b62fba9ae2af7c289b74226017a5a9627efbc0f8f7fd636f7716c |
| macOS (Apple Silicon) | SDF_R_17_0_3_Darwin.zip | - | pending (build-sdf-r-v17-0-3-cross-platform.yml) |
| Linux (x86-64) | SDF_R_17_0_3_Linux.zip | - | pending (build-sdf-r-v17-0-3-cross-platform.yml) |

V17.0.3 fixes the black spots that appeared with Weld (Merge) ON:
- Weld now flips "cap" triangles (apex > 175 deg, three nearly collinear vertices) that Marching Cubes emits where the surface runs along a grid line. Welded into the mesh, their flipped normals were dragging Blender's angle-weighted vertex normals into wedge-shaped dark spots.
- Weld also merges float-noise duplicates (<= 1e-6 x extent) that straddle a rounding-cell boundary, closing small seam holes.
- Live Normals now applies real custom normals (custom_normal attribute on Blender 5.0+, normals_split_custom_set_from_vertices on 4.x). The old "normals" attribute was ignored by Blender 4.1+ and is removed from existing meshes.

Sample scene (sample-20261121-1.blend, res 658, GPU_CHUNKED_MC), measured on the Windows zip in Blender 5.1:
flipped faces 38 -> 0, cap triangles 524 -> 0, mis-shaded vertices 49 -> 12 (the 12 are loose vertices), boundary edges 76 -> 0, face count unchanged.
