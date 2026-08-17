# SDF.R V16.1.3 Release Notes — Global Symmetry Mesh Fix

*Released 2026-08-17*

V16.1.3 fixes Global Symmetry. With **X**, **Y** or **Z** enabled in the Mesh Settings panel, the
Ghost Preview showed the mirrored result correctly — and then generating a mesh dropped or
distorted any primitive sitting on the negative side of that plane. That is fixed.

If you never used Global Symmetry, nothing in this release changes your output. Meshes generated
with Symmetry off are identical to V16.1.2.

---

## 🐛 Global Symmetry dropped negative-side primitives — fixed

### If you hit this with Booleans, that was the same bug

This was reported to me as Symmetry not working with Booleans — the cut showing in the preview but
not in the final mesh. That is the same fault, and it is worth describing separately because it
looks nothing like the single-shape case.

With one shape on the negative side, you get an empty mesh, and something is obviously wrong. With
a Boolean, the base shape still meshes perfectly — **only the cut disappears.** A Subtract sphere
placed on the negative side of the symmetry plane was dropped entirely, so what came out was the
uncut solid. Nothing errored, nothing looked broken, and the preview kept showing the cut you
expected.

Measured before and after, with a Subtract sphere cutting a box under Symmetry X:

| Subtract sphere at | V16.1.2 | V16.1.3 |
|---|---|---|
| X = +2 | 109,503 verts (cut correctly) | 109,503 verts |
| X = −2 | **77,748 verts — exactly the uncut box** | 109,503 verts |

Intersect behaved the same way, collapsing to almost nothing on the negative side. Both placements
now produce identical meshes, which is what symmetry requires.

### Were you affected?

This is worth stating precisely, because Symmetry did **not** fail across the board. What mattered
was where a primitive's centre sat relative to the symmetry plane:

| Primitive centre | Before (V16.1.2) |
|---|---|
| On the positive side | Correct |
| Exactly on the plane | Correct |
| Negative side, crossing the plane | **Silently came out smaller than it should** |
| Entirely on the negative side | **Contributed nothing — empty mesh if it was your only shape** |

One more case worth knowing: if you had a matching primitive on the positive side, the result
could look completely correct, because the positive one covered the same space after mirroring.
**The problem could stay hidden in exactly the symmetric scenes Symmetry is used for.**

### What you saw

Enable **Symmetry: X / Y / Z** in Mesh Settings, and the viewport does exactly what you expect.
Then press generate, with either **Marching Cubes** or **Dual Contouring**, and a shape you had
placed on the negative side is missing entirely — or, if it straddled the plane, quietly shrunk.

The preview being right is what made this confusing. It looked like the meshing step was refusing
to run. It was running — it was simply looking in the wrong place.

### Why it happened

The Ghost Preview and the mesh generator are two separate implementations of the same scene.
The preview raymarches the SDF directly. The mesh generator first works out **where in space it
needs to look**, then samples only that volume on the GPU. Global Symmetry was handled correctly
in the preview and incorrectly in the second path — in two independent ways that reinforced each
other.

**1. The search volume was clamped to one side of the plane.**

Before sampling, the generator computes a bounding box around every primitive. For a symmetry
axis it was setting that box to span from **0 to +max** — the positive half only. The mirrored
half of your model, and any primitive you had placed on the negative side, sat outside the volume
the generator ever looked at. Geometry there was discarded before meshing began.

The box now spans **−max to +max**, covering both halves.

**2. Primitive centres were not folded onto the mirrored side.**

Global Symmetry works by folding the sampled point onto one side of the plane. The preview shader
also folds each primitive's centre to match. The meshing shaders — both the detection pass that
finds occupied cells and the layout evaluation that positions each primitive — did not. A
primitive sitting at X = −2 with Symmetry X on was therefore evaluated as if it were somewhere
else entirely.

Both meshing shaders now fold primitive centres the same way the preview does.

When the two faults lined up — which happened as soon as a primitive was on the negative side —
the search volume was empty and the output was an empty mesh.

### What is affected

- **Global Symmetry only** — the X / Y / Z toggles in the Mesh Settings panel.
- **Per-primitive Mirror** in the Layout section was never affected and is unchanged.
- **Both meshing algorithms** are fixed, Marching Cubes and Dual Contouring alike — both verified.
- **Output with Symmetry off is unchanged** from V16.1.2.

---

## 🔧 Also in this release

**One internal change, with no visible effect:** all three platform builds now load their native
engine through the same code path. Until now the Windows build loaded it one way and the macOS and
Linux builds another, which meant the three packages carried slightly different Python and had to
be reconciled by hand for every release. They are now byte-for-byte identical.

This matters for you indirectly: the macOS and Linux builds now run exactly the code I can test on
Windows, rather than a hand-adjusted variant of it.

### Verified

Checked on Blender 5.1.2 in headless mode, with the shipped binary:

| Case | V16.1.2 | V16.1.3 |
|---|---|---|
| Marching Cubes, primitive at X = −2.0, Symmetry X | **empty** | 14,160 verts, spans −3.0 → +3.0 |
| Dual Contouring, primitive at X = −2.0, Symmetry X | **empty** | 2,368 verts, spans −3.0 → +3.0 |
| Primitive at X = −0.5, crossing the plane | spans −0.5 → +0.5 | spans −1.5 → +1.5 |
| Symmetry X + Y + Z, corner at (−2, −2, −2) | **empty** | full eight-way symmetric mesh |
| Primitive at X = +2.0 / on the plane / Symmetry off | correct | unchanged |

---

## 🔄 Upgrade Note

No mandatory steps. If SDF.R ever fails to start after an update, it now clears its own shader
cache and retries automatically, so the manual cleanup that older release notes asked for is no
longer required.

If you would still rather clear it by hand — it is harmless, and costs one slower startup:

1. Close Blender completely.
2. Delete the shader cache:
   - Windows: `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
   - macOS: `~/Library/Application Support/Blender/<your version>/datafiles/rust_gpu_sdf/shader_cache.bin`
   - Linux: `~/.config/blender/<your version>/datafiles/rust_gpu_sdf/shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

---

## 🖥️ macOS and Linux

Unchanged from V16.1.2: all three platforms are built from the same source, by the same automated
pipeline, in every release. The symmetry fix is in the Windows, macOS and Linux builds alike.

The macOS build is not notarized, so Gatekeeper blocks it on first use. Open
**System Settings → Privacy & Security**, find the message about `rust_gpu_sdf.so`, and click
**Open Anyway**, then re-enable the add-on in Blender.

I develop on Windows and do not own a Mac or a Linux machine, so those platforms improve exactly
as fast as people tell me things — including telling me when things work. If SDF.R runs fine for
you on macOS or Linux, one sentence genuinely helps.

If something breaks: launch Blender from Terminal, reproduce it, and send me what the terminal
printed, plus `blender.crash.txt` from your temporary folder if Blender went down.

---

## 📦 Downloads

| Platform | File | Architecture |
|---|---|---|
| Windows | `SDF_R_16_1_3.zip` (standard package) | x86-64 |
| macOS | `SDF_R_16_1_3_MAC.zip` | Apple Silicon (arm64) |
| Linux | `SDF_R_16_1_3_LINUX.zip` | x86-64 |

---

## Previously in V16.1.2

V16.1.2 fixed a crash on macOS:

- **Blender crashed the moment a primitive was added**, on some macOS setups. While waiting for
  the mesh calculation, SDF.R ran a timer that asked Blender for the scene's dependency graph — a
  request that makes Blender re-evaluate the entire scene if it decides one is due. From a timer,
  that happens at a moment Blender never scheduled, and the evaluator can read past the end of its
  own object list. The timer no longer forces an evaluation.
- **A safety limit on the mesh timer** — if the dependency graph stays unavailable, the timer now
  gives up on the queued update after about two seconds instead of polling indefinitely.

See the V16.1.2 release notes for full details.
