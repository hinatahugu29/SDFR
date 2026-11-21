# SDF.R V17.0.3 Release Notes — No more black spots with Weld on

*Released 2026-11-21*

A fix release on top of V17.0.2. With **Weld (Merge)** turned on — the default — Marching Cubes
meshes could show small dark specks and wedge-shaped dark patches. Those are gone. This release
also turns **Live Normals** on for real; until now it had no effect.

---

## 🐛 Black spots on welded meshes

### What you saw

Generate a mesh with Weld on, and a few small black dots or dark wedges appear here and there on
the surface — most noticeable on smooth, curved areas. Turning Weld off made them disappear,
but left the mesh split into loose triangles.

### Why it happened

Where the surface runs exactly along the internal sampling grid, Marching Cubes produces
"needle" triangles: three points almost on one line, with practically no area. Their facing
direction is decided by rounding noise, so roughly half of them point inward. On their own they
are invisible, but once Weld joins them to their neighbours, Blender's smooth shading blends
their inward-facing normal into the surrounding vertices — and gives it a lot of weight, because
of how Blender weights normals by corner angle. The result was a dark wedge.

A second, smaller cause: two copies of the same point, a hair apart from rounding noise, could
fall just either side of a weld boundary and stay unjoined, leaving tiny seam holes.

### What it does now

- **Weld now repairs needle triangles** by flipping the edge they share with a neighbour. The
  face count, the outline and the overall shape stay exactly the same.
- **Weld also joins copies of the same point** that differ only by rounding noise, closing
  those small seam holes. Points that are genuinely separate are left alone.
- **Weld no longer leaves stray vertices.** It already removed collapsed faces, but the vertices
  only those faces used were left behind and turned up as loose vertices in Snapshot Mesh and
  Finalize results.
- **The Weld Threshold scale is now consistent everywhere.** On the default path (Auto backend
  below Chunk Start Res), Weld Threshold was being read as a distance in metres instead of as
  a fraction of the voxel size, so very small models were over-merged. It now works the same way
  as the chunked backends, with the same **Seam** value as its minimum.

On the test scene that showed the problem, at resolution 658: flipped faces 38 → 0, needle
triangles 524 → 0, open edges 76 → 0, same face count.

---

## ✨ Live Normals now actually works

**Live Normals** (and **Auto-enable Live Normals on High**) were meant to give the mesh smooth
shading taken straight from the SDF. The data was being written in a form Blender 4.1 and newer
silently ignore, so the switch did nothing. SDF.R now writes real custom normals: the
`custom_normal` attribute on Blender 5.0 and newer, and the standard custom split normals on 4.x.

**This is a visible change.** "Auto-enable Live Normals on High" is on by default, so pressing
**High** now gives the mesh custom normals, and Finalize keeps them on the baked mesh. If you
plan to keep editing a finalized mesh by hand, turn Live Normals off before you finalize, or
clear the custom normals afterwards (Object Data Properties → Geometry Data → Clear Custom
Split Normals Data).

---

## 🛡️ The add-on now notices a half-finished update

On Windows, installing a new zip while SDF.R is still enabled cannot replace the engine file
Blender has open, so you could end up with new add-on code running on the old engine — with
nothing to say so. SDF.R now checks that its engine matches its own version and shows
**Engine version mismatch** in the panel if it doesn't.

---

## Upgrading

**On Windows, follow these steps in order**, otherwise the old engine stays in place:

1. **Edit → Preferences → Add-ons**, and **disable** SDF.R.
2. **Restart Blender.**
3. Install the V17.0.3 zip and enable SDF.R.

macOS and Linux can install over the previous version as usual. No migration is needed, and
existing files open unchanged. If you see **Engine version mismatch** in the panel, repeat the
three steps above.

Windows, macOS (Apple Silicon) and Linux builds are all available.
