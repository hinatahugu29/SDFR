# SDF.R V16.2.1 Release Notes — One Add-on, Separate Objects

*Released 2026-09-09*

Until now an SDF.R scene held exactly one SDF tree, and that tree produced exactly one mesh. If you
wanted a model's parts as separate objects — eyes apart from a head, a lid apart from a jar, a
print split into pieces that each need their own material — there was no way to get there from
inside the add-on. The V16.2.0 notes ended by saying "build them as a second SDF output". That
sentence now describes something you can actually do.

**A scene can hold as many SDF trees as you like.** Each has its own parts collection, its own
settings, and its own result mesh. They are separate objects from the moment they are built, so
there is nothing to split afterwards.

The release also adds **Mirror Blend**, which rounds off the hard crease that Layout Mirror has
always left down the middle of a mirrored shape.

**Existing files are unaffected.** A file with one tree keeps its names, its layout and its output.
Mirror Blend defaults to 0, which is the behaviour you have now.

---

## 🌳 Several SDF trees in one scene

The panel opens with a **Tree** row. The dropdown picks which tree you are editing, and **+** adds
a new one. Everything below that row — Parts, The Stack, Output & Quality — follows the tree you
have selected.

You can also just click a part in the viewport. The panel switches to whichever tree that part
belongs to.

```text
Tree: SDF_Result          ← the tree you are editing
Parts: SDF_Collection     ← its parts live here
```

Adding a tree does not disturb the one you have. The first tree keeps the names it has always
used (`SDF_Collection`, `SDF_Result`); new trees are numbered from there.

**Finalize applies to the active tree only.** Baking one tree leaves the others live and editable,
and Live Update stays on until the last one is finalized.

### What this is for

The obvious use is parts that must not fuse. Layer Boundary in V16.2.0 stops shapes from blending,
but a layer still merges into the scene as a Union, so overlapping shapes remain one connected
solid. Separate trees are separate meshes — nothing merges across them at all.

It also turns out to be **faster**, not slower. Splitting a model across trees means each request
carries fewer primitives, and sparse block detection has less to look at. A 216-sphere model at
resolution 128 took 5053 ms as one tree, 1904 ms split across four, and 1215 ms across eight. There
is no limit on the number of trees, because there is no cost that scales with having them.

### Tree Reference

A tree can read another tree's shape. Select a part, and **Add Tree Reference** puts an empty in
the stack; point it at another tree and choose a mode:

| Mode | Result |
|---|---|
| **Blend** | The referenced tree joins this one as a single merged group |
| **Subtract** | The referenced tree is carved out of this one |

Subtract is what you want for a fit — carve the lid's cavity from the jar so the two meet exactly.
Move the empty to offset the reference. Editing the referenced tree updates this one.

Two things to know. **Blend is exact.** **Subtract is exact as long as the referenced tree is built
from Union alone**; if it uses Subtract or Intersect internally, the carve is approximate there,
and the panel tells you so when that is the case. References also go one level deep — a reference
inside a referenced tree is not followed.

### The ghost preview still shows one tree

The live ghost preview draws the active tree only. Domain and symmetry are per-tree settings that
cannot be combined into a single pass, and the preview is the one thing that runs every frame.

This does not hide anything: every tree's **result mesh is a real object and is always visible**.
Only the live editing overlay is limited to the tree you are working on.

---

## 🪞 Mirror Blend

Layout Mirror on a primitive works by folding space, so the two halves always meet at a hard
minimum, and **Smoothness has never had any effect on that seam** — inside folded space there is
only one shape, and nothing to blend it against. On a mirrored sphere the join was a genuine crease
in the surface, not a shading artifact: 44 creased edges meeting at up to 84°.

**Mirror Blend** evaluates the two sides separately and joins them with the primitive's own blend
shape. On the same sphere it gives 0 creased edges at 8.5° — vertex for vertex, angle for angle,
identical to building two spheres and joining them with a smooth union. It works with two mirror
axes at once.

The control sits under Mirror Settings and **defaults to 0**, which takes the same path as before.
Raising it costs evaluation time, because both sides are evaluated: about 1.7× on one axis, doubling
again for each additional axis.

Two limits worth stating. The **ghost preview approximates this** — the seam looks rounded, but not
identically to the final mesh. And **Radial and Grid still crease**; they repeat space the same way,
but blending across cell boundaries needs neighbouring cells, which is a larger change than mirror's
two sides. Mirror, Radial and Grid on a **Collection Divider** have never had this problem, since
those copy shapes for real and join them with an ordinary smooth union.

---

## 🐛 Show Result Mesh now clears the mesh

Switching **Show Result Mesh** off hid the result but left the mesh data in place. An optimisation
added in V15.9.9.4 returned early, ahead of the branch that empties the mesh, so that branch had
become unreachable. It now clears, and switching back on rebuilds.

## 🐛 Fixes that came with multiple trees

- A finished tree no longer takes the others down with it when you Finalize.
- The Tree dropdown changes the tree, rather than only appearing to.
- The ghost preview switches as soon as the active tree does.
- An async mesh result goes back to the tree that asked for it. Previously one result was applied
  to every output, so a second tree came out the same shape as the first.
- `Auto Domain` and `Use Live Normals` re-mesh when toggled; they were missing from the state
  fingerprint.
- The Tree row stays visible with one tree. It used to disappear the moment you finalized down to
  one, which read as the controls being taken away.

## 🐛 The panel no longer unlocks before the engine is ready

The GPU-ready flag is a scene property, so it was saved into your .blend. Opening a file saved
after initialisation unlocked the panel while shaders were still compiling. The flag is now checked
against the engine's real state when a file loads.

Nothing broke if you did operate during warm-up — requests waited on the same lock and ran when
compilation finished — but the panel should not have looked ready.

---

## Upgrading

Install over the previous version as usual. Shader cache clearing is not required.

The GPU shader code changed in this release, so if you keep several versions side by side, use the
V16.2.1 build rather than mixing folders.

**First start after installing takes longer than usual**, because the shader cache from the previous
version no longer matches and the pipeline is rebuilt once. On a discrete GPU this is the usual
15–45 seconds. **On integrated graphics it can take several minutes** — an Intel Iris Xe measured
194 seconds. The console prints `Compiling MC Pipeline...` while this happens, and `GPU Engine
Ready!` when it finishes. Later starts take a second or two.

### Splitting an existing model into trees

There is no automatic split — a tree is built, not divided. To move a part out:

1. Add a tree with **+** on the Tree row.
2. Build the part in the new tree, or move its objects into the new tree's parts collection.
3. If the parts need to fit together, add a **Tree Reference** in Subtract mode so one carves the
   other.

Existing single-tree files need no migration and are not changed by opening them.
