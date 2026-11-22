# SDF.R V17.0.5 Release Notes — Round every edge at once, and a flat pyramid base

*Released 2026-11-22*

V17.0.5 builds on V17.0.4. It adds **Apply Edge All**, which sets the edges of every primitive in a
tree in one click. It also fixes the **Pyramid** base, which could come out stepped and render black.

---

## ✨ Apply Edge All

### Why

When an edge is perfectly sharp, smooth shading blends the normals across the corner. The rim of a
cylinder's end cap then looks dirty or streaky, in MC and DC alike. The shape itself is accurate.
Rounding the edge slightly, by about two voxels, gives the shading a real curve to follow, and the
rim comes out clean. Until now, that meant setting Edge and Size on each primitive one by one.

### How to use it

In the **SDF.R Modeling** panel, below the stack list, there is a new **Edges (All Primitives)** box:

1. Pick an edge profile: **Round**, Sharp, Soft, Tight or Chamfer.
2. Choose how to give the size:
   - **Voxels** (default 2): the size follows the current resolution. The grey line below it shows
     the resulting distance and the size of one voxel. Before the first mesh is generated, these
     numbers are an estimate, marked with **~**.
   - **Distance**: a fixed size in scene units.
3. Click **Apply Edge All**.

Every primitive in the active tree gets that profile and size, and the mesh is rebuilt once. Each
primitive can still be changed on its own afterwards, and **Ctrl+Z** undoes the whole step.

- Shapes without edges, such as spheres and tori, look the same as before.
- **Math Field** primitives have no edge setting and are skipped. The message at the bottom of the
  screen tells you how many were skipped.

### Rounding the seams that Subtract and Intersect cut

The rim of a hole cut with **Subtract**, or an edge left by **Intersect**, is not controlled by Edge
Size. It is controlled by that primitive's **Smoothness**. Turn on **Also round Subtract /
Intersect seams**, and Apply Edge All also sets Smoothness on those primitives, so their rims round to
about the same radius as the other edges. Smoothness is capped at 2.0. The option is off by default,
because it changes how deep those cuts blend.

---

## 🐛 Pyramid base: no more steps or black patches

### What you saw

The bottom face of a **Pyramid** was not flat. It came out in small stair steps, and not at the height
where it was placed. With **GeoRemesh_R** on, the base could render as black patches in Cycles.
Smooth blends between a pyramid and other shapes near the base were also distorted.

### Why it happened

The pyramid's distance function measured only the slanted sides. It never measured the base, so
near the bottom face it returned values that were badly wrong. Both MC and DC then placed the base at
the wrong height in a stepped pattern, and the normals there pointed in the wrong directions.

### What it does now

The distance to the base is now included, the same way in the GPU engine, the CPU engine and the
viewport preview. On our test scene at resolution 300:

| | Before | V17.0.5 |
|---|---|---|
| MC: base height | varies by 0.055 | exactly where it was placed |
| MC: worst face tilt on the base | 144.7° (flipped faces) | 0° |
| DC: base height | varies by 0.066 | exactly where it was placed |
| DC: worst face tilt on the base | 118.8° | 0° |
| Cycles with GeoRemesh_R | black patches | clean |

**Existing files:** pyramids change slightly near the base, which is now flat and sits exactly
where it was placed. Smooth blends that touch the base may also look a little different.

---

## Upgrading

**On Windows, follow these steps in order** (as with V17.0.4). Otherwise the old engine stays in
place:

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.5 zip and enable SDF.R.

macOS and Linux can install over the previous version as usual. No migration is needed. If you see
**Engine version mismatch** in the panel, repeat the three steps above.

Windows, macOS (Apple Silicon) and Linux builds are all available.
