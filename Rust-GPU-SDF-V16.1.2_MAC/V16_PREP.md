# SDF.R V16 Preparation

V15.9.9.9 is the final stabilization point before V16 feature work.

## V15 Closure

- Diagnostics UI and runtime log toggles are available from the SDF-R panel.
- Build scripts validate package contents and native module import before reporting success.
- Rust `cargo check` is expected to finish without warnings.
- Python add-on files are expected to pass `py_compile`.

## V16 Direction

V16 should be positioned as a feature generation, not another stabilization pass.

Recommended first theme:

- Field Modeling
- New field primitives such as Gyroid, Voronoi, or procedural noise fields
- Field deformers such as Domain Warp, Repeat, and Tiling
- Preview modes for inspecting fields before meshing

## Branch/Copy Start Point

Use `Rust-GPU-SDF-V15.9.9.9` as the source folder for the first V16 copy.

Suggested first folder:

`Rust-GPU-SDF-V16.0.0`

Before implementing V16 features:

1. Copy from `Rust-GPU-SDF-V15.9.9.9`.
2. Update add-on version and package names to `16.0.0`.
3. Run `py_compile`.
4. Run `cargo check`.
5. Run `build_sdf_addon.ps1` once to verify the release package pipeline.
