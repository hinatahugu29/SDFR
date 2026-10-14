# SDF.R V17.0.0 Release Notes — Viewport Gizmos

*Released 2026-10-14*

V17.0.0 is a major update built entirely on top of V16.2.2 — **the Rust engine is unchanged.**
It adds viewport gizmos: a way to edit a selected SDF primitive's parameters by dragging or
clicking directly in the 3D viewport, instead of always going through the side panel's number
fields. The panel still has every field it always had; the gizmos are a second way in, not a
replacement.

---

## 🧰 What you can now drag or click in the viewport

Select an SDF primitive and the following show up as colored arrows or small buttons around it,
depending on its shape:

**On every primitive:**

- **Fillet / Edge Size** (orange arrow) — on primitives that actually have corners to round
  (Box, Cylinder, Hex Prism, Pyramid, Tapered Cylinder, N-gon Prism, Rounded Cylinder, Capped
  Torus, Octahedron, Cut Sphere). Left off shapes with no edges (Sphere, Torus, Capsule,
  Ellipsoid), since dragging it there wouldn't visibly change anything.
- **Shell / Hollow thickness** (cyan arrow) — on every closed solid, including the smooth
  shapes the fillet gizmo skips.
- **Smoothness** (magenta arrow) — the blend radius this primitive uses when it joins its
  neighbors. Only visible where it joins something, same as in the panel: on a single primitive
  with nothing overlapping it, dragging it changes the number but there's nothing to see yet.
- **Operation** (three buttons: Union / Subtract / Intersect) — click to switch, same as the
  panel dropdown. The active one is shown solid; the other two are dimmed.
- **Edge Profile** (five buttons in two rows: Round / Sharp / Soft / Tight / Chamfer, on the
  same shapes as the fillet gizmo) — click to switch the rounding style.

**Shape-specific, where the panel already shows a dedicated field:**

Torus (Main Radius / Pipe Radius), Cylinder (Radius / Height), Capped Cone (Bottom Radius / Top
Radius / Height), Ellipsoid (Radius X/Y/Z, colored red/green/blue to match the axes they move
along), Rounded Cylinder (Radius / Edge Radius / Height), Pyramid (Base Size / Height), Hex
Prism (Radius / Height), Rounded Box (Roundness), Octahedron (Size), and Cut Sphere (Cut
Height) each get their own matching arrows.

**Not covered yet:** Capped Torus's arc Angle and N-gon Prism's side count don't fit the arrow
pattern (one is a rotation, the other an integer step) and still live in the panel only.
Deform Stack entries (Elongate / Bend / Twist / Taper) aren't gizmo-driven yet either — see
below.

---

## Why this doesn't touch your files or your meshes

Every gizmo writes to the exact same property the panel field already used, through the same
update path the panel always went through. There is no new data on your objects, no new file
format, and no change to how any shape is meshed. **If you never touch a gizmo, nothing about
how SDF.R behaves has changed.**

Because the Rust engine is untouched, there's no shader cache rebuild — the first start after
upgrading is as fast as always.

---

## A note on scope

This release focuses on primitive-level parameters only. Two further areas are planned but not
in V17.0.0:

- **Boolean-relationship values** (blend radius between two specific primitives, layer
  boundaries) — these describe a relationship between objects rather than a single primitive,
  and need a different kind of gizmo to place correctly.
- **The Deform Stack** (Elongate / Bend / Twist / Taper) — this is a list, not a single value
  per object, and its own position/axis fields need a different gizmo shape (a 3D move widget)
  than the arrows used here.

Both are still just panel-only for now; nothing about them changed in this release.

---

## Upgrading

Install over V16.2.2 as usual. Existing files need no migration and open exactly as they did
before — gizmos are a viewport-only addition with no new per-object data.

Windows, macOS and Linux builds are all available.
