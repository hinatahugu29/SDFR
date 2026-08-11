# SDF.R V16.1.1 Release Notes — Viewport Preview Performance

*Released 2026-08-11*

V16.1.1 is a focused performance update for the real-time Ghost Preview. **Nothing about mesh
generation changes** — the geometry SDF.R produces is bit-for-bit identical to V16.1.0. Only how
the preview is drawn while you are actively navigating or editing has changed.

---

## 🎯 What changed

### Adaptive preview resolution during interaction

The Ghost Preview is raymarched, which means its cost is roughly:

```
viewport pixels × ray steps × primitive count
```

Step count was already reduced while you navigate. V16.1.1 adds the missing piece: **the preview
is now rendered at a reduced resolution while the camera is moving or an object is being
transformed, then upscaled to fill the viewport.**

- Camera orbit / pan / zoom renders at 50% linear resolution — **a quarter of the pixels**.
- Object transforms render at 65% linear resolution.
- **The moment you stop, the preview is redrawn at full resolution.** Still frames are unchanged.

Because this scales down pixel count, it helps regardless of how complex the scene is — which is
exactly the case that used to degrade worst.

### Faster normals while interacting

When a ray hits a surface, the shading normal was estimated with a 6-tap central difference,
meaning six extra full-scene evaluations per hit pixel. During interaction this now uses a 3-tap
forward difference that reuses the distance already computed at the hit point, **halving that
cost**. Full 6-tap quality returns as soon as you stop moving.

---

## 📊 What this does and does not help

Being precise about this, because it sets expectations correctly:

| Situation | Effect |
|---|---|
| **Camera orbit / pan / zoom** | Helps fully. The primitive buffer is cached, so this is pure draw cost. |
| **Dragging an object** | Helps the drawing portion only. Moving an object also rebuilds the preview's primitive buffer on the Python side, and that cost is untouched by this release. |
| **Still frames** | No change — full resolution and full-quality normals, exactly as before. |
| **Generated mesh** | No change whatsoever. |

If you want to see where time is actually going in your scene, enable **Engine Diagnostics >
Perf** and watch the system console. Note that `avg duration` in that log measures CPU-side
command submission, not GPU execution — **FPS is the number to compare**. A high
`texture rebuilds` count indicates the Python-side rebuild, not drawing, is your bottleneck.

---

## 🔧 Also fixed

- **Blender 5.2 support for the Post-Process panel.** On Blender 5.2 the Post-Process
  (Smoothing) section came up empty, with `property not found` errors in the console. Blender 5.2
  changed how Geometry Nodes modifier inputs are stored — they are now regular properties
  (`modifier.properties.inputs.<id>.value`) instead of custom properties (`modifier["<id>"]`).
  SDF.R now finds the values either way, so the same build works on 5.1 and 5.2. Note that this
  affects **every earlier version of SDF.R too** when run on Blender 5.2; it is not something
  V16.1.1 introduced.
- **Ghost Preview in split viewports.** With more than one 3D Viewport open, the preview could
  fail to appear once the camera came to rest, and stayed locked in its reduced-quality
  interactive state. Motion was being detected with a single shared value, so simply alternating
  between two viewports looked like continuous camera movement. Detection is now tracked per
  viewport. This dates back to V15.9.9.4; the adaptive resolution added in V16.1.1 is what made it
  visible.
- **Reduced-resolution buffer reuse.** With split viewports of differing sizes, the buffer used
  for reduced-resolution drawing was discarded and recreated on every frame, cancelling out the
  speed-up this release is built around. Buffers are now kept per size.
- **Mesh data safety check.** Vertex indices coming back from the engine are now range-checked
  before being handed to Blender. Out-of-range data is rejected with a message in the system
  console rather than written into the mesh — writing it could corrupt memory and crash Blender
  later, in a place with no obvious connection to the real cause. Valid data is unaffected.
- **Collection cleanup when adding a primitive.** An object that belonged to three or more
  collections could be left linked to some of them after being moved into `SDF_Collection`.
- Fixed the preview being drawn as a small patch in the middle of the viewport instead of filling
  it, under the new reduced-resolution path. (Introduced and fixed within V16.1.1 development;
  V16.1.0 is unaffected.)

---

## 🔍 Known issue — macOS, and a request

One user has reported Blender crashing immediately when adding any primitive, on **macOS 26.6 /
Apple Silicon / Blender 5.2**. I want to be upfront that **I have not been able to reproduce it.**
The same steps work here on Windows under both Blender 5.1 and 5.2, and the crash lands inside
Blender's own scene evaluation rather than anywhere I can point to in the add-on. The cause is
still unknown.

**Workaround:** turning **Show Result Mesh** off lets you add and shape primitives normally. You
keep the live Ghost Preview and the full modelling workflow — you just don't get the final
generated mesh until this is solved.

The mesh data safety check added in this release (see above) may or may not address it. That is an
honest "may" — it closes a real hole, but I have no evidence yet that this particular hole is the
one being hit.

**I would genuinely appreciate hearing from macOS and Linux users either way:**

- **If it crashes for you**, the single most useful thing is the console output. Launch Blender
  from Terminal with `/Applications/Blender.app/Contents/MacOS/Blender`, reproduce the crash, and
  send me whatever the Terminal printed. The engine's own log at
  `~/Library/Application Support/Blender/<version>/datafiles/rust_gpu_sdf/sdf_debug.log` helps too.
- **If it works fine for you, please tell me that as well.** Knowing which macOS versions, chips
  and Blender versions are *unaffected* narrows this down just as much as a crash report does.
  Right now I have exactly one data point, and I can't tell how widespread this is.

---

## ⚠️ Upgrade Note

**Coming from V16.1.0:** no special steps. The GPU compute shaders are unchanged in this release,
so **clearing the shader cache is not required.**

**Coming from V16.0.x or earlier:** please clear the shader cache before launching Blender, since
V16.1.0 did change the GPU shader code:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

---

## 📦 Downloads

| Platform | File | Architecture |
|---|---|---|
| Windows | `SDF_R_16_1_1.zip` (standard package) | x86-64 |
| macOS | `SDF_R_16_1_1_MAC.zip` (experimental test build) | Apple Silicon (arm64) |
| Linux | `SDF_R_16_1_1_LINUX.zip` (experimental test build) | x86-64 |

> **macOS note:** The test build is not code-signed. If Gatekeeper blocks it, open
> **System Settings → Privacy & Security**, find the message about `rust_gpu_sdf.so`, and click
> **Open Anyway**, then re-enable the add-on in Blender.

---

## Previously in V16.1.0

If you are updating from V16.0.x, V16.1.0 introduced the curve workflow:

- **Curve Sync** — draw a path with Blender's own Curve tools and SDF.R turns it into a solid,
  blendable SDF pipe supporting Union, Subtract, and Intersect.
- **Curve Ref** — reference a curve living anywhere else in your scene without moving it.
- **Bezier Curve primitive** — a numerically-defined 3D quadratic Bezier with independent start
  and end radius.
- **Transmission & IOR** — glass-like transmission for the generated SDF material.
- **Instancing accuracy fix** — geometry no longer goes missing when Radial/Spiral layouts are
  combined with Individual/Step Rotation, or when Radial Axis is set to X or Y.

See the V16.1.0 release notes for full details.
