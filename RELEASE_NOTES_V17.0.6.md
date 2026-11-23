# SDF.R V17.0.6 Release Notes — Clean cut edges on Math Fields

*Released 2026-11-23*

V17.0.6 builds on V17.0.5. It cleans up the edge where a **Math Field** is cut off, both with
**Boundary = Box Clip** and with **Use Previous as Mask**.

---

## 🐛 Math Field cut edges: no more stair steps or ragged fins

### What you saw

Where a Math Field (gyroid and the other formulas) is cut off, its thin walls end in a cut face.
With **Boundary = Box Clip**, the rim of every cut face came out as small stair steps, about one voxel
high. After **Use Previous as Mask**, it was worse: near the surface of the mask shape, the walls were
worn down into thin, ragged, blade-like fins.

### Why it happened

- **Box Clip** cut the walls with a perfectly sharp corner. The walls are only a few voxels thick,
  and a sharp corner on such a thin wall cannot be placed cleanly on the voxel grid. It comes out
  stepped.
- **Use Previous as Mask** turns the Math Field into an **Intersect** with the shape before it, and
  it left **Smoothness** at the default of 0.2. That blend is wider than the walls themselves, which
  are 0.16 thick on the MEDIUM preset. So the blend ate into the walls near the mask surface and left
  only thin fins.

### What it does now

- **Box Clip** now rounds the corner where a wall meets the cut face. The radius is half the wall
  thickness (half of **Thickness**). The change is the same in the GPU engine, the CPU engine and the
  viewport preview.
- **Use Previous as Mask** now sets the Math Field's **Smoothness** to half of its **Thickness**
  (0.04 for the MEDIUM preset), so the blend stays narrower than the walls.

On our test scene (MEDIUM preset, resolution 204, MC), both routes now give clean, rounded rims, and
they produce exactly the same mesh. The FINE preset no longer leaves slivers along the cut edge.
**Fade** and **Open** are unchanged.

**Existing files:**

- Math Fields that use **Box Clip** change slightly along the cut edge, which is now rounded.
- Scenes already set up with **Use Previous as Mask** keep their Smoothness. Click **Use Previous as
  Mask** again, or lower **Smoothness** by hand to about half of **Thickness**.

**Tip:** the FINE preset has very thin walls, about two voxels at resolution 204. If you see dark,
flipped faces on its surface, raise the resolution. That comes from the resolution, not from this
fix, and it happened before V17.0.6 too.

---

## Upgrading

**On Windows, follow these steps in order** (as with V17.0.5). Otherwise the old engine stays in
place:

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.6 zip and enable SDF.R.

macOS and Linux can install over the previous version as usual. No migration is needed. If you see
**Engine version mismatch** in the panel, repeat the three steps above.

Windows, macOS (Apple Silicon) and Linux builds are all available.
