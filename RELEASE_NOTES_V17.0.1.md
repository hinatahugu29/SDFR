# SDF.R V17.0.1 Release Notes — Snapshot and Finalize keep their own material

*Released 2026-10-16*

A small fix on top of V17.0.0: **Snapshot Mesh** and **Finalize (Bake All)** no longer share a
material with the live SDF tree.

---

## 🐛 A frozen snapshot wasn't actually frozen

### What you saw

Press **Snapshot Mesh** or **Finalize**, keep working on the live tree, and the snapshot or
finalized result's **colors changed along with it** — Reset, Apply Material All, or just
building a new tree later could all do it.

### Why it happened

Two separate things, both now fixed:

- **Snapshot Mesh and Finalize's backup copied the mesh, but not the material.** Duplicating a
  mesh in Blender copies which material slots point to which material — it does not duplicate
  the material itself. So the "frozen" copy and the live tree ended up pointing at the exact
  same material datablock, and any later edit to that material showed up on both.
- **A finalized tree's output name could be reused.** Finalize renames its output object away
  from `SDF_Result` to `SDF_Result_001`, which frees the name `SDF_Result` back up. The next new
  tree you built could then pick that name up again, and because **Setup Material** names its
  material after the output object (`SDF_Material_SDF_Result`), the new tree's material lookup
  would find — and silently reuse — the old material a past Finalize backup was still holding
  onto.

### What it does now

Snapshot Mesh and Finalize now duplicate the material itself at the moment they run, so the
frozen copy's appearance is independent from that point on. Separately, an output name is no
longer treated as free just because no live object holds it anymore — if a material of that
name still exists, the name stays retired.

---

## Upgrading

Install over V17.0.0 as usual. Existing files are unaffected: a Snapshot or Finalize result
already saved in a file keeps whatever material it already has: this only changes what happens
the *next* time you press Snapshot Mesh or Finalize.

Windows, macOS and Linux builds are all available.
