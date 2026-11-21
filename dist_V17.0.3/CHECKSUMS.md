SDF.R V17.0.3 - distribution packages
built 2026-11-21 / local Windows build (build_sdf_addon.ps1) from the Rust-GPU-SDF-V17.0.3_CI tree / macOS and Linux pending CI

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_17_0_3.zip | 14,657,412 | c908a21009e3d6adfffb3d786881e57184c329a399651d6e3eaa4a336757921a |
| macOS (Apple Silicon) | SDF_R_17_0_3_Darwin.zip | - | pending (build-sdf-r-v17-0-3-cross-platform.yml) |
| Linux (x86-64) | SDF_R_17_0_3_Linux.zip | - | pending (build-sdf-r-v17-0-3-cross-platform.yml) |

V17.0.3 fixes the black spots that appeared with Weld (Merge) ON:
- Weld now flips "cap" triangles (apex > 175 deg, three nearly collinear vertices) that Marching Cubes emits where the surface runs along a grid line. Welded into the mesh, their flipped normals were dragging Blender's angle-weighted vertex normals into wedge-shaped dark spots.
- Weld also merges float-noise duplicates (<= 1e-6 x extent) that straddle a rounding-cell boundary, closing small seam holes.
- Weld removes vertices left unreferenced after degenerate faces are dropped (they stayed as loose vertices in Finalize/Snapshot results).
- The non-chunked GPU mesher (AUTO below Chunk Start Res) used Weld Threshold as a world-space distance instead of a voxel fraction, over-merging small models. It now uses the same voxel-relative threshold as the chunked paths, max(Weld Threshold, Seam Weld) x voxel.
- The add-on now checks that the native engine matches its own version and shows "Engine version mismatch" in the panel if not. On Windows, installing a zip over an enabled add-on cannot replace the loaded bin/win/rust_gpu_sdf.pyd, which left a V17.0.2 engine under V17.0.3 Python and caused black spots in DC (welding at 0.05 world units). Fix: disable the add-on, restart Blender, install the zip, enable it.
- Live Normals now applies real custom normals (custom_normal attribute on Blender 5.0+, normals_split_custom_set_from_vertices on 4.x). The old "normals" attribute was ignored by Blender 4.1+ and is removed from existing meshes.

Sample scene (sample-20261121-1.blend, res 658, GPU_CHUNKED_MC), measured on the Windows zip in Blender 5.1:
flipped faces 38 -> 0, cap triangles 524 -> 0, mis-shaded vertices 49 -> 12 (all of them loose vertices, which Weld now removes: loose 12 -> 0), boundary edges 76 -> 0, face count unchanged.
res 329 (AUTO, non-chunked GPU MC): boundary edges 8 -> 0, loose vertices 36 -> 0.

Note: Live Normals now has a visible effect. "Auto-enable Live Normals on High" is on by default, so the High preset now writes custom normals, and Finalize keeps them on the baked mesh.
