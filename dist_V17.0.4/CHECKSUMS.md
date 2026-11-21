SDF.R V17.0.4 - distribution packages
built 2026-11-21 / commit 36a223f / Windows: local build (build_sdf_addon.ps1), macOS and Linux: CI run 44880305796

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_17_0_4.zip | 14,658,103 | 11125bc84a3f4dfb3aed630e89d8c1f7c568f613c774e15743da1074b259b656 |
| macOS (Apple Silicon) | SDF_R_17_0_4_Darwin.zip | 13,769,548 | 53d0ae5fb3ff2501b64db9f4f7d173fa274b9d79f777f6f4bc969380a70b6c07 |
| Linux (x86-64) | SDF_R_17_0_4_Linux.zip | 14,937,060 | 80119981208a3e4b28f3563496049b0db3c25e7516b590888b24007de9a1eb32 |

All three ZIPs contain byte-identical Python sources, and those match commit 36a223f. Only the native module differs between them. Every native module carries __version__ 17.0.4, and the CI build validation passed on all three OSes.
The macOS build is arm64 only (macos-15 runner) and does not run on Intel Macs.

V17.0.4 fixes the seam holes left by GPU Chunked MC at mid resolutions:
- Each chunk builds a cubic local grid of max(cells) + 2 cells, centred on its core. On an axis where the core is the partial last chunk (for example res 329 = 128 + 128 + 73), local - core is odd. That chunk's lattice then sat half a voxel off the global grid, so its seam vertices could not meet the neighbouring chunk's vertices, and Weld cannot close a half-voxel gap.
- The chunk centre now shifts by half a cell only when that difference is odd. When it is even, the centre stays exactly where it was. At least one ghost cell remains on each side.
- AUTO falls back to this path on low-VRAM GPUs, so it could hit these holes too.

Sample scene (sample-20261121-1.blend), measured with Blender 5.1 headless (verts/faces, boundary/non-manifold edges):
- res 329, GPU_CHUNKED_MC: 60760/121366, 324/22 -> 60696/121392, 0/0. This is identical to the non-chunked mesh.
- res 264, 658 and 1024: unchanged for GPU_CHUNKED_MC and AUTO.

Not changed in this release: GPU Chunked DC places its chunks the same way and is left for a follow-up.
Updating on Windows: as with V17.0.3, disable the add-on, restart Blender, then install the zip and enable it.
