# SDF.R V16.2.2 Release Notes — The Mirror Blend preview moves with the mesh

*Released 2026-09-11*

V16.2.1 added **Mirror Blend**, which rounds off the hard crease that Layout Mirror leaves down the
middle of a mirrored shape. The final mesh has been correct since that release. **The ghost preview
was not**: raising Mirror Blend made the shape in the preview thinner rather than thicker, and past
a certain point the shape vanished from the preview altogether.

This release fixes the preview. It also adds a warning for a setting that surprises people.

**Nothing about your meshes or your files changes.** Meshing never used the preview's code, so
every mesh you generated on V16.2.1 was already correct, and so is every file you saved. If you have
never touched Mirror Blend, this release changes nothing you can see — at 0, the preview takes
exactly the path it always did.

---

## 🐛 The ghost preview drew Mirror Blend backwards

### What you saw

On V16.2.1, with Layout Mirror on a primitive and Mirror Blend above 0:

- Raising Mirror Blend made the preview **thinner**, while the generated mesh got **thicker**.
- Past roughly twice the sum of Offset and the shape's own size, **the shape disappeared from the
  preview entirely** — on a sphere of radius 0.15 at offset 0.25, that happened at Blend 0.8.
- The mesh was unaffected throughout, so the preview and the result disagreed, and the disagreement
  grew as you raised the value.

The most likely way to meet this was to raise Mirror Blend looking for a rounder seam, watch the
preview shrink or empty out, and conclude the feature was broken. It was the preview that was wrong.

### Why it happened

The final mesh evaluates the two mirrored halves separately and joins them with a smooth union,
which pushes the surface **outward** near the seam. The preview cannot do that: it evaluates each
shape once per frame, and there is only one shape inside folded space to evaluate.

V16.2.1's preview approximated the rounding by softening the fold itself — replacing the sharp
`abs()` at the mirror plane with a smoothed version. That does round the seam, but it rounds it
**inward**, eating into the shape instead of adding to it. The two went in opposite directions, and
at large values the inward cut consumed the shape completely.

### What it does now

The fold is sharp again, and the rounding is applied to the distance instead, reproducing the same
correction term the smooth union uses. The preview now swells as you raise Blend, in the same
direction and by a similar amount as the mesh.

It is still an approximation — one evaluation cannot reproduce two exactly — so the two do not round
identically. Measured on a mirrored sphere at radius 0.15 and offset 0.25:

| Mirror Blend | V16.2.1 preview | V16.2.2 preview |
|---|---|---|
| 0.4 | 0.110 off | 0.029 off |
| 0.8 | shape gone | 0.120 off |
| 2.0 | shape gone | 0.060 off |

Across one, two and three mirror axes the preview stays within about 0.02–0.12 of the mesh through
the range you would normally work in, widening to roughly 0.38 at Blend 2.0 on two and three axes.

**Mirror Blend at 0 is bit-for-bit the path it was before.** If you do not use the feature, nothing
in the preview has moved.

---

## 🪞 A warning when Blend goes past twice the Offset

**Raising Mirror Blend past twice the Offset thickens the whole shape, not just the seam.**

This is not a defect and it is not new — it is what joining two halves smoothly does. Once the blend
radius reaches across the gap between the two halves, no part of the shape is far enough from the
seam to be left alone, and the surface inflates everywhere. On a mirrored sphere it shows up as the
axis *across* the mirror growing, which is not a direction Mirror Blend looks like it should touch.

The panel now says so when your settings cross that line:

```text
Blend over 2x Offset swells the whole shape,
not just the seam. Raise Offset to keep the size.
```

If you want a rounder seam without a heavier shape, **raise Offset rather than Blend**.

---

## Upgrading

Install over V16.2.1 as usual. Existing files need no migration and are not changed by opening them.

The GPU shader code changed in this release, so **the first start after installing takes longer than
usual** while the cached pipeline is rebuilt once. On a discrete GPU that is the usual 15–45 seconds.
**On integrated graphics it can take several minutes** — an Intel Iris Xe measured 194 seconds. The
console prints `Compiling MC Pipeline...` while this happens and `GPU Engine Ready!` when it is done.
Later starts take a second or two.

Clearing the shader cache by hand is not required. If you keep several versions side by side, use the
V16.2.2 build rather than mixing folders.

Windows, macOS and Linux builds are all available.

Thank you to the owner who asked whether Mirror Blend and the mesh were really connected. The
original report turned out to be about something else, but measuring it is what turned this up.
