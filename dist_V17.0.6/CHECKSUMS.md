SDF.R V17.0.6 - distribution packages
built 2026-11-23 / commit a9886f2 / Windows, macOS and Linux: CI run 45119991491

| Platform | File | Size | SHA-256 |
|---|---|---:|---|
| Windows | SDF_R_17_0_6.zip | 14,656,582 | 17a014d250b1866a58762f068567c2fea5fb3a4969c31a5f6393e8d135dbd11d |
| macOS (Apple Silicon) | SDF_R_17_0_6_Darwin.zip | 13,772,465 | a34cef1d1e5d83000488a6981685bacc8520d07f40948fddb97f9ad81a1e6b67 |
| Linux (x86-64) | SDF_R_17_0_6_Linux.zip | 14,940,835 | 02f36321962cea6151471ed8e843ffe110ee1686463a60f8ff3eb7a725781d8a |

The Python sources in all three ZIPs are identical to commit a9886f2. Only the native module differs between them. The Windows native module reports __version__ 17.0.6, and the CI build validation, which checks this on each OS, passed on all three.
The macOS build is arm64 only (macos-15 runner) and does not run on Intel Macs.

V17.0.6 cleans up the edge where a Math Field is clipped:
- Boundary = Box Clip used a hard max between the wall and the clip face, so every cut edge came out as one-voxel stair steps. The corner is now rounded with a radius of half the wall thickness, in the GPU, CPU and preview implementations.
- Use Previous as Mask left Smoothness at 0.2, which is wider than the wall, so the walls near the mask surface were eaten into knife-edge fins. The operator now sets Smoothness to half the wall thickness (0.04 for the MEDIUM preset).

MEDIUM preset, res 204, MC, Blender 5.1 headless, measured on the Windows ZIP above:
- Use Previous as Mask: Smoothness set to 0.04, 87294 vertices, the same mesh as Box Clip alone (87294)
- Fade (68586) and Open (89112): unchanged from V17.0.5

Behavior change: Box Clip scenes change slightly at the cut edge, which is now rounded. Scenes made with Use Previous as Mask keep their Smoothness until the operator is run again, or until Smoothness is lowered by hand.
Not checked on screen: the preview (ghost) shader.
Updating on Windows: disable the add-on, restart Blender, then install the zip and enable it.
