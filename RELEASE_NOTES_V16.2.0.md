# SDF.R V16.2.0 Release Notes — Layer Boundary, Reworked

*Released 2026-09-04*

V16.2.0 makes Layer Boundary do what its name promises. Until now, switching it on gave you a
group that fused into one shape and then blended softly into the rest of the scene — which is the
opposite of a boundary. The divider now owns the seam, and defaults to a hard one.

**This changes how existing files look if they use Layer Boundary.** Nothing else in the release
alters output. If you have never switched it on, your meshes are identical to V16.1.3.

The release also fixes three faults in **Move to SDF**, and one in the ghost preview.

---

## 🧱 Layer Boundary now produces a hard boundary

### What was wrong

A layer boundary evaluates its group on its own and then merges the finished shape into the scene
once. That much always worked. The problem was the merge itself: it was a smooth union, and the
blend radius it used was read from **whichever primitive happened to come first in the group**.

That value was doing double duty, and badly. Inside the group, the first primitive's Smoothness has
no effect at all — the accumulator has nothing to blend against yet. So the number appeared to do
nothing while you were shaping the group, and then silently decided how the whole group met the
rest of the model. With the default Smoothness of 0.2 sitting on that first shape, turning Layer
Boundary on produced a group that melted into the scene as one soft lump.

If you tried to solve that by turning Smoothness down, you were working on the right idea with the
wrong control — and if the shape you turned down was not the first in the group, it did nothing.

### What changed

The divider now carries its own settings, shown when Layer Boundary is on:

| Setting | Meaning |
|---|---|
| **Layer Blend** | Blend radius where this layer meets the rest of the scene. Default **0.0** — a hard seam |
| **Profile** | Blend shape for that merge: Round, Sharp, Soft, Tight, Chamfer |

**Primitive Smoothness is untouched**, including the way a newly added primitive inherits the value
from the previous one. Shapes inside a group still blend with each other exactly as before. Only
the single merge into the scene changed hands.

---

## 📐 A layer now covers the group above its divider

Group layout — Mirror, Radial, Spiral, Grid, Jitter — and stack parenting have always acted on the
rows **above** a divider. The layer acted on the rows **below** it. One divider's settings applied
to two different groups, which is not something you can hold in your head while modelling.

They now agree: **a divider closes the group above it.** Everything from the previous divider down
to this one belongs to the group.

A layer also no longer leaks past the next divider. Previously a layer ran until the next divider
of any kind, so an unrelated plain divider would end it without saying so.

**If you have a file using Layer Boundary, its groups have shifted.** The rows you thought were in
the layer are now the rows above the divider instead of below it. In most stacks the fix is to move
the divider, or to place a second one.

---

## 🐛 Layout on a layer boundary no longer disappears

A divider carrying Radial, Grid or any other group layout threw the layout away entirely the moment
Layer Boundary was switched on. The layer branch finalised the group before the layout matrices
were applied.

The two now work together on a single divider, so a radially repeated group can also be its own
layer.

---

## 🐛 The ghost preview and the mesh agreed on layers

The layer rules exist in three places: the CPU mesher, the GPU mesher, and the GLSL raymarch that
draws the ghost preview. All three now implement the rules above. This was found while testing this
release, not reported from the field.

---

## 🐛 Move to SDF

Three separate faults, all in the same operator:

- **It chose the wrong destination.** The target collection came from the first output object found
  while walking the scene, so a file with more than one SDF output sent objects to an unpredictable
  one. The order is Blender's internal business, so it was not even consistent between sessions. It
  now uses the active output object.
- **It could leave the old link behind.** Unlinking while iterating an object's collections can skip
  entries, leaving an object in both its old collection and the SDF one.
- **It fell back to a sphere in silence.** Move to SDF identifies a shape from the object's *name* —
  box, cube, torus, cylinder — and anything else becomes a sphere. That is a real limitation, since
  there is no mesh-based SDF shape yet, but doing it without a word made it look as though the
  button had failed. It now reports which objects it had to guess at.

An arbitrary sculpted or imported mesh still cannot be brought in this way. Mesh SDF shapes are a
separate piece of work.

---

## Upgrading

Install over the previous version as usual. **Shader cache clearing is not required**; SDF.R
detects a failed start and retries by itself.

The GPU shader code changed in this release, so if you keep several versions side by side, use the
V16.2.0 build rather than mixing folders.

### If your file used Layer Boundary

1. Open the file and look at the shapes that were in a layer.
2. The group is now the rows **above** the divider. Move the divider, or add one, so the group is
   the set you meant.
3. The seam is now hard. If you want the old softness back, raise **Layer Blend** on that divider —
   0.2 reproduces the old default.

### If you want parts that do not melt together

This is what the feature is for, and it takes **one divider per part**. A single layer on its own
does very little: the first layer merges into an empty scene, so its Layer Blend has nothing to act
on, and any shape left outside every layer still blends into whatever the layers merged into.

```text
01 Body A
02 Body B
== Layer: Head ==     Layer Boundary on
03 Eye L
04 Eye R
05 Eyelid / Subtract  cuts the eyes only — the body is in another layer
== Layer: Eyes ==     Layer Boundary on, Layer Blend 0.0
06 Shell
== Layer: Shell ==    Layer Boundary on
```

Note that merging a layer is always a Union. Layer Boundary stops shapes from blending, but
overlapping shapes still form one connected solid. If you need the eyes as a separate mesh object,
build them as a second SDF output.

The user guide's chapter on Collection Divider and Layer Boundary has been rewritten around this,
and Workflow Examples gains a section on keeping eyes, eyelids and a shell apart.
