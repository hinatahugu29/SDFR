# SDF.R V16.1.2 Release Notes — macOS Crash Fix

*Released 2026-08-12*

V16.1.2 fixes a crash on macOS, and changes how I talk about the macOS and Linux builds.
Nothing about mesh generation or the preview changes — the geometry SDF.R produces is identical
to V16.1.1.

---

## 🐛 The macOS crash — found and fixed

One user reported Blender crashing the moment they added a primitive, every time, on macOS with
Blender 5.2. It took several rounds to track down, and the answer is worth stating plainly:
**the fault was mine, not their setup.**

### What was happening

While SDF.R waits for the mesh calculation to finish, it runs a repeating timer. That timer was
asking Blender for the scene's dependency graph — and in Blender, that request does not merely
hand one over. If Blender decides an update is due, **it re-evaluates the entire scene right
there**.

Inside an operator, that is the flow Blender expects and it is safe. From a timer callback it
begins evaluating at a moment Blender never scheduled, and if the scene's composition shifted
just beforehand, the evaluator reads past the end of its own object list. The result is an
immediate segmentation fault, in a place with no visible connection to the add-on.

The timer no longer forces an evaluation. It takes the dependency graph only if one already
exists, and skips the cycle otherwise.

### Why it looked like an add-on conflict

With **Factory Settings and only SDF.R enabled, the crash never happened.** That result was
misleading, and it nearly sent the investigation in the wrong direction. With a quiet scene the
forced evaluation happens to survive; with other add-ons touching the scene it becomes fatal.
The dangerous call was ours the whole time — other add-ons only widened the window.

If you hit this and concluded something in your setup was to blame, it was not.

### Was I affected?

Only if this specific timing lined up on your machine. It never once occurred on my own Windows
system across both Blender 5.1 and 5.2, which is exactly why this took an outside report to
find. If SDF.R has been stable for you, nothing changes — but the fragile call was present in
every earlier version, so this fix is worth taking regardless of platform.

---

## 🔧 Also in this release

- **A safety limit on the mesh timer.** If the dependency graph stays unavailable, the timer now
  gives up on the queued update after about two seconds instead of polling indefinitely. It
  counts only that specific situation — waiting while you drag an object, or while the engine is
  still calculating, is normal and is not affected.

---

## 🖥️ Where the macOS and Linux builds stand

I am retiring the "experimental test build" label, and I want to explain why rather than just
quietly change the wording.

SDF.R ships for **Windows**, **macOS (Apple Silicon)** and **Linux (x86-64)**. All three are
built from the same source, by the same automated pipeline, in every release. They are not side
projects and they are not afterthoughts.

I want to be straightforward about one thing: **I develop on Windows, and I do not own a Mac or
a Linux machine.** I cannot sit down and reproduce a problem on those platforms myself. What I
can do is read a crash report and fix what it points to — and that works. The crash fixed in
this release was found entirely from one user's crash log, and the cause turned out to be my own
code, not their environment.

So these platforms improve exactly as fast as people tell me things.

**That includes telling me when things work.** A crash report tells me something is broken. A
message saying "runs fine on macOS 26.6, M3 Max, Blender 5.2" tells me where the line is, and
that is just as valuable — I currently have very few of those. If SDF.R is working for you on
macOS or Linux, one sentence would genuinely help.

### If something breaks

The fastest route to a fix:

1. Launch Blender from Terminal — on macOS, `/Applications/Blender.app/Contents/MacOS/Blender` —
   reproduce the problem, and copy whatever the Terminal printed.
2. Send `blender.crash.txt` from your temporary folder. On macOS, `open $TMPDIR` in Terminal
   opens it. That file contains the add-on's own line numbers, which is usually all I need.

That is exactly what solved this release's crash.

### Code signing

The macOS build is not notarized, so Gatekeeper blocks it on first use. Open
**System Settings → Privacy & Security**, find the message about `rust_gpu_sdf.so`, and click
**Open Anyway**, then re-enable the add-on in Blender.

---

## ⚠️ Upgrade Note

**Coming from V16.1.0 or V16.1.1:** no special steps. The GPU shader code is unchanged across
these releases, so **clearing the shader cache is not required.**

**Coming from V16.0.x or earlier:** please clear the shader cache before launching Blender, since
V16.1.0 did change the GPU shader code:

1. Close Blender completely.
2. Delete `%APPDATA%\Blender Foundation\Blender\<your version>\datafiles\rust_gpu_sdf\shader_cache.bin`
3. Restart Blender. The first startup after clearing takes the full warm-up time again.

---

## 📦 Downloads

| Platform | File | Architecture |
|---|---|---|
| Windows | `SDF_R_16_1_2.zip` (standard package) | x86-64 |
| macOS | `SDF_R_16_1_2_MAC.zip` | Apple Silicon (arm64) |
| Linux | `SDF_R_16_1_2_LINUX.zip` | x86-64 |

---

## Previously in V16.1.1

V16.1.1 was a viewport performance release, plus a set of fixes:

- **Adaptive preview resolution** — the Ghost Preview renders at reduced resolution while the
  camera moves or an object is transformed, then returns to full resolution the instant you stop.
- **Faster normals during interaction** — a 3-tap estimate while moving, full 6-tap quality when
  still.
- **Blender 5.2 support for the Post-Process panel** — 5.2 changed where Geometry Nodes modifier
  inputs are stored, leaving the panel empty. This affected every earlier version of SDF.R on 5.2.
- **Ghost Preview with split viewports** — the preview could fail to appear once the camera came
  to rest when more than one 3D Viewport was open.
- **Mesh data safety check** — vertex indices from the engine are range-checked before being
  handed to Blender.

See the V16.1.1 release notes for full details.
