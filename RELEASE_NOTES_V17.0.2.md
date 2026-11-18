# SDF.R V17.0.2 Release Notes — Round edges finally follow Edge Size

*Released 2026-11-18*

A small fix on top of V17.0.1: the **Round** edge profile now actually rounds. It ignored
**Edge Size** entirely, both in the preview and in the generated mesh.

---

## 🐛 Round ignored Edge Size

### What you saw

Add a Box (or Cylinder, Hex Prism, Ngon Prism), leave **Edge** on **Round** — the default — and
raise **Size**. Nothing happened: the corners stayed sharp in the viewport preview and in the
mesh. Switching to Soft, Tight or Chamfer with the same Size did round the corners. The Fillet
gizmo had the same problem, since it drives the same value.

### Why it happened

Round is the first entry in the Edge list, and internally the first entry was treated as "no
edge treatment at all". The preview and both meshing engines (GPU and CPU) skipped the edge step
whenever Round was selected, whatever Size said. Before V17.0.0 the panel hid the Size field for
Round, so this went unnoticed; V17.0.0 started showing it, which made the dead field visible.

### What it does now

- **Round is a true circular round, and Size is its radius.** Size 0.5 on a default 2 m cube
  rounds every edge with a 0.5 m radius, and the corners come out as clean spherical patches. The
  rounding stays inside the shape's outline: it never makes the object smaller than its size, and
  the radius stops growing at half the shape's thinnest dimension.
- **Size 0 means sharp edges, for every profile.** Sharp, Soft and Tight could misbehave at Size 0;
  they now simply give the plain shape.
- **Sharp, Soft, Tight and Chamfer look exactly as before** at any Size above 0.
- **Edge Size now starts at 0** instead of 0.1 on new primitives. Pick a profile, then raise Size.

Thanks to the user who reported this with a precise diagnosis.

---

## Upgrading

Install over V17.0.1 as usual. No migration is needed.

**Existing files:** primitives whose Edge Size you never touched keep their sharp look. A
primitive on Round that already had an Edge Size set — for example one you dragged with the
Fillet gizmo while it seemed to do nothing — will now be rounded by that amount. If a shape looks
softer than you expect after updating, set its Edge Size back to 0.

Windows, macOS (Apple Silicon) and Linux builds are all available.
