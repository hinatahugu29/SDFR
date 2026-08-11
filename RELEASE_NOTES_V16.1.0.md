# SDF.R V16.1.0 Release Notes — Curve Workflow

*Released 2026-07-26*

V16.1.0 opens up a new way to build shapes in SDF.R: instead of composing everything from
numeric primitives, you can now **draw a path with Blender's own Curve tools and have SDF.R
turn it into a solid, blendable SDF pipe**. Curves behave like any other stack item, so they
blend smoothly with neighbouring shapes and support Union, Subtract, and Intersect.

---

## ✨ Highlights

### Curve Sync — native Blender Curves as SDF geometry

Any Blender Curve object can now drive an SDF pipe. Add as many curves as you like; each one
carries its own Pipe Radius, boolean Operation, Smoothness, Color, Metallic, and Roughness.

There are two ways to attach a curve, and both can be used in the same scene:

- **Move it in.** Select the curve and press **Move to SDF** (or drag it into the SDF
  Collection). The curve is registered directly as a Curve Sync stack item. Best when the
  curve exists purely to build the SDF shape.
- **Reference it.** Press **Curve Ref** in the Add New Primitives grid to create a small proxy
  item, then pick any curve in your scene as its **Target Curve**. The original object never
  moves and is never modified, so it stays available for animation, Geometry Nodes, or anything
  else. If a curve is already selected when you press the button, it is assigned automatically.

Because the settings live on the proxy rather than on the curve, you can also point **several
Curve Ref proxies at the same curve** and give each one a different radius, colour, or boolean
operation.

### Edit the referenced curve in one click

The Curve Sync panel includes an **Edit** button that selects the target curve and enters Edit
Mode immediately — no hunting through the Outliner. It safely exits any other object's edit
mode first, and unhides the curve if needed.

### Supported curve types

| Type | Support |
|---|---|
| Bezier | Full, including handles. **Subdiv Samples** controls sampling density. |
| Poly | Full; control points are used directly. |
| NURBS | Evaluated by Blender itself. **Subdiv Samples does not apply** — use the curve's own *Resolution Preview U*. |
| Cyclic (closed) | Supported; the pipe closes back on itself. |

*Curves with Bevel or Extrude applied generate surfaces rather than a path, so Curve Sync falls
back to a coarser approximation. Keep the curve as a plain path for best results.*

### Bezier Curve primitive

Separate from Curve Sync, a new **Bezier** primitive is available in the Add New Primitives
grid. It is a self-contained 3D quadratic Bezier defined numerically rather than by a curve
object:

- **Point B (Mid)** and **Point C (End)** control points — the start point is the primitive's
  own origin, so moving the object moves the whole curve.
- **Start R** and **End R** give independent radii at each end for a smooth taper.

Use Curve Sync when you want to draw a path by hand; use the Bezier primitive when you want a
compact, numerically-defined tapered arc that follows the object's transform and works with the
Layout and Deform stacks.

### Transmission & IOR in the Material section

The Material section gains a **Transmission** slider with a paired **IOR** control (enabled once
Transmission is above zero) for glass-like results.

> **Scope note:** Color, Metallic and Roughness are stored per vertex and can therefore differ
> per primitive. Transmission is a **single value applied to the whole SDF material** — you
> cannot currently make one primitive glass and another opaque within the same SDF object.
> Press **Setup Nodes** first, then **Apply Material All**, and view in Material Preview or
> Rendered shading.

---

## 🎯 Performance

### Lightweight Curve Sync preview

The real-time Ghost Preview draws Curve Sync as a **coloured guide line along the curve**
rather than a fully raymarched pipe. This is deliberate: the preview evaluates every primitive
for every ray step, so expanding each curve into a long chain of pipe segments would slow the
whole viewport down as curves are added.

- The **generated mesh is always exact** — thickness, blending, and boolean operations are fully
  applied there.
- Enable **Show Result Mesh** or press **Force Update** to see the true shape.
- The guide uses each item's colour, and its thickness is adjustable via **Curve Sync Guide
  Width** in the engine settings.

---

## 🔧 Fixes

### Instancing accuracy — missing geometry with Radial + Rotation

Fixed geometry that could go missing when **Radial or Spiral layouts were combined with
Individual/Step Rotation**. The bounding volume used to skip empty regions during meshing did
not account for the extra per-copy rotation, so parts of elongated or asymmetric shapes could be
culled away. Also fixed the same calculation ignoring the **Radial Axis** setting, which caused
losses when the axis was set to X or Y instead of Z.

This affects any elongated or asymmetric primitive, not just the new curve shapes.

### Other fixes

- Curve Sync items now respect stack order correctly, so **Subtract and Intersect operate on the
  shapes above them** as expected.
- Adding a Curve Ref no longer produces a duplicate group entry in The Stack.
- Solo mode now stops at the selected item reliably, even when a later item is incomplete.
- Duplicating a Collection Divider group now carries Curve Sync items across correctly.
- Removing a Curve Ref proxy deletes only the proxy; the referenced curve is left untouched.

---

## 📋 Interface Changes

- **Curve Ref** button added to the Add New Primitives grid.
- **Bezier** primitive added to the Add New Primitives grid.
- **Curve Sync Settings** panel appears when a synced Curve or Curve Ref proxy is selected.
- **Transmission** and **IOR** added to the Material section.
- **Curve Sync Guide Width** added to the engine settings.
- **Extrude** and **Lathe** have been removed from the Add New Primitives grid. Their two working
  cross-sections (rectangle and circle) overlapped almost entirely with the existing Rounded Box,
  Cylinder and Torus primitives, so the entry was removed rather than shipped half-complete.
  Arbitrary cross-section profiles remain on the roadmap. Existing objects are unaffected.

---

## ⚠️ Upgrade Note

This release changes the GPU shader code. When updating from V16.0.x, please **clear the shader
cache** before launching Blender:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
3. Restart Blender. The first startup after clearing will take the full warm-up time again.

---

## 📦 Downloads

All three platforms are available at V16.1.0.

| Platform | File | Architecture |
|---|---|---|
| Windows | `SDF_R_16_1_0.zip` (standard package) | x86-64 |
| macOS | `SDF_R_16_1_0_MAC.zip` (experimental test build) | Apple Silicon (arm64) |
| Linux | `SDF_R_16_1_0_LINUX.zip` (experimental test build) | x86-64 |

> **macOS note:** The test build is not code-signed. If Gatekeeper blocks it, open
> **System Settings → Privacy & Security**, find the message about `rust_gpu_sdf.so`, and click
> **Open Anyway**, then re-enable the add-on in Blender.
