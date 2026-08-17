# SDF.R V16.1.3 Release Notes — Global Symmetry Mesh Fix

*Released 2026-08-17*

V16.1.3 fixes Global Symmetry. If you turned on **X**, **Y** or **Z** in the Mesh Settings panel,
the Ghost Preview showed the mirrored result correctly — and then generating a mesh gave you
nothing, or only part of the shape. That is fixed.

If you never used Global Symmetry, nothing in this release changes your output. Meshes generated
with Symmetry off are identical to V16.1.2.

---

## 🐛 Global Symmetry produced no mesh — fixed

### What you saw

Enable **Symmetry: X / Y / Z** in Mesh Settings, and the viewport does exactly what you expect —
the shape appears mirrored across the plane. Then press generate, with either **Marching Cubes**
or **Dual Contouring**, and the result is an empty mesh, or a mesh missing everything on one side.

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
- **Both meshing algorithms** are fixed, Marching Cubes and Dual Contouring alike.
- **Output with Symmetry off is unchanged** from V16.1.2.

### Verified

Checked on Blender 5.1.2 in headless mode, with the shipped binary:

| Case | Result |
|---|---|
| Primitive at X = +2.0, Symmetry X | Mesh spans X −3.0 → +3.0 |
| Primitive at X = −2.0, Symmetry X | Mesh spans X −3.0 → +3.0 |
| Symmetry X + Y + Z together | Full eight-way symmetric mesh, 37,056 vertices |

The negative-side case is the one that used to return nothing at all.

---

## ⚠️ Upgrade Note

**The GPU shader code changed in this release.** Please clear the shader cache before launching
Blender:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
   On macOS: `~/Library/Application Support/Blender/<your version>/datafiles/rust_gpu_sdf/shader_cache.bin`
   On Linux: `~/.config/blender/<your version>/datafiles/rust_gpu_sdf/shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

This applies whichever version you are coming from.

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
