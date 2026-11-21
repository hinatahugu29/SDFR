# SDF.R V17.0.4 Release Notes — No more seam holes in chunked meshes

*Released 2026-11-21*

A fix release on top of V17.0.3. At some resolutions, the **GPU Chunked MC** backend left small
holes along the lines where it splits the model into chunks. Those holes are gone.

---

## 🐛 Seam holes in GPU Chunked MC meshes

### What you saw

With **GPU Chunked MC** at some mid-range resolutions — resolution 329 on our test scene — the
generated mesh had a row of small holes and broken edges along a straight line across the model.
In Edit Mode, **Select → Select All by Trait → Non Manifold** picks them out. Other resolutions, such as 264, 658 and 1024, came out clean. **AUTO** can hit this too: when the
GPU does not have enough memory for one pass, AUTO switches to GPU Chunked MC.

### Why it happened

GPU Chunked MC splits the model into chunks, meshes each chunk on its own sampling grid, and
then joins the results. When the resolution does not divide evenly into chunks, the last chunk on
an axis is smaller than the rest (329 = 128 + 128 + 73). For some of those sizes, that chunk's
grid ended up half a voxel off the grid of the chunks beside it, so their edge points could not
meet. Weld only joins points that are close together, and half a voxel was too far for it to close.

### What it does now

Every chunk's grid now lines up exactly with the model's overall grid, so the points on both sides
of a seam match and Weld joins them. Chunks that already lined up are placed exactly as before.

On the test scene at resolution 329: open edges 324 → 0 and non-manifold edges 22 → 0. The
result is now identical to the mesh made without chunks. Resolutions 264, 658 and 1024 give the
same mesh as before.

**Not covered yet:** the experimental **GPU Chunked DC** backend places its chunks the same way
and is left for a later release.

---

## Upgrading

**On Windows, follow these steps in order** (as with V17.0.3), otherwise the old engine stays in
place:

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.4 zip and enable SDF.R.

macOS and Linux can install over the previous version as usual. No migration is needed, and
existing files open unchanged. If you see **Engine version mismatch** in the panel, repeat the
three steps above.

Windows, macOS (Apple Silicon) and Linux builds are all available.
