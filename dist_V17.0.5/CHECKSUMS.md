SDF.R V17.0.5 - distribution packages
built 2026-11-22 / commit 2926b3a / Windows: local build (build_sdf_addon.ps1), macOS and Linux: CI run 44963625124

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_17_0_5.zip | 14,660,652 | 45ff8d470b1b17c602ee64cf30082bb786aa5ba0f2b8333a642d2ae8ff14e511 |
| macOS (Apple Silicon) | SDF_R_17_0_5_Darwin.zip | 13,771,839 | a85baeec41ae19d8aa049998da78b6ab67e11964d25b6a6c148a6cc7c2383e46 |
| Linux (x86-64) | SDF_R_17_0_5_Linux.zip | 14,939,897 | be8f5a3c052f92e16cc3e9defffdbbb8d5abd0165fe76d4561fb9f036d8b3857 |

All three ZIPs contain byte-identical Python sources, and those match commit 2926b3a. Only the native module differs between them. Every native module carries __version__ 17.0.5, and the CI build validation passed on all three OSes.
The macOS build is arm64 only (macos-15 runner) and does not run on Intel Macs.

V17.0.5 adds Apply Edge All and fixes the pyramid base:
- Apply Edge All (Edges panel) sets one edge profile and size on every primitive of the active output. The size is given in voxels (default 2) or as a distance. Math Field primitives are skipped. An option also sets Smoothness on Subtract and Intersect items, so their cut seams round to about the same radius.
- The pyramid distance function measured only the slanted sides, so near the base it returned about +-1 instead of the distance to the base. The base came out as stair steps, smooth blends were distorted, and GeoRemesh_R custom normals rendered black in Cycles. The base distance is now included in the GPU, CPU and preview implementations.

Sample scene (sample-20261121-3.blend), res 300, Blender 5.1 headless (base interior face height, max face tilt from -Z), measured on the Windows ZIP above:
- MC: -3.763..-3.708, 144.7 deg -> -3.8331 exactly, 0 deg
- DC: -3.792..-3.726, 118.8 deg -> -3.8331 exactly, 0 deg

Behavior change: files that use pyramids change slightly near the base, which no longer bulges below it.
Not checked on screen: the preview (ghost) pyramid and the new panel.
Updating on Windows: disable the add-on, restart Blender, then install the zip and enable it.
