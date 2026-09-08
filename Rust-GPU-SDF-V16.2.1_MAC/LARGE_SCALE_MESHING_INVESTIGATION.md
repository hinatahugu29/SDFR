# SDF.R V15.9.9.3 Large-Scale Meshing Investigation

Date: 2026-07-09
Base: V15.9.9.2

## Initial Question

High-density Marching Cubes output can show missing mesh regions, and generated edges are not clean enough for larger modeling work. The goal of V15.9.9.3 is to investigate a more scalable meshing design without assuming that these limits are purely unavoidable.

## Current Pipeline Observations

- The GPU path already uses a sparse block workflow: `detect_pass` marks active 8x8x8 blocks, then Sparse MC or GPU Dual Contouring runs only on those blocks.
- The current architecture still has hard global capacities: max vertices, max indices, max triangles, max active blocks, block data capacity, and per-block primitive list capacity.
- Missing output at high density is likely to come from one or more of these classes:
  - active block overflow or clamping;
  - triangle/vertex/index buffer saturation;
  - block detection false negatives from bounds estimation;
  - per-block primitive list fallback or overflow;
  - chunk neighbor lookup failure in DC face generation;
  - MC sampling limitations for thin or tangential features.
- Edge quality is partly a Marching Cubes limitation. MC reconstructs from corner sign changes and linear edge interpolation, so it is not feature-preserving by design.
- GPU Dual Contouring is present and is the right family for sharper features, but it depends on robust Hermite data, stable QEF solving, crack-free neighbor references, and non-manifold handling.

## Investigation Priorities

### 1. Make Failures Observable

Before changing algorithms, the branch should make high-density failure modes explicit.

Recommended diagnostics:

- Report when `active_count > max_blocks`, not only to console but to the add-on UI or mesh status.
- Report when `tri_count == max_tris` or when counters imply triangle/index/vertex saturation.
- Track `MissingPtrs` and `EmptyVoxels` separately for MC and DC.
- Add a "meshing health" status: OK, capacity-limited, block-detection-risk, neighbor-missing, or empty-result.
- Avoid silently returning a partial mesh that looks like valid geometry.

Expected impact:

- This does not improve quality directly, but it separates algorithmic limits from implementation capacity loss.

### 2. Replace Global High Resolution With Chunked Narrow-Band Meshing

The long-term scalable path is not a single monolithic `res^3` domain. It should be a chunked sparse field:

- Divide the domain into independent chunks/bricks.
- Evaluate only chunks that intersect the surface narrow band.
- Add ghost cells around each chunk so MC/DC can generate boundary faces without cracks.
- Stream chunks through fixed-size GPU buffers instead of requiring one enormous global mesh buffer.
- Merge chunk outputs on CPU or write them into Blender incrementally.

Suggested chunk shape:

- Internal cells: 32^3 or 64^3.
- Ghost border: 1 cell minimum for MC, likely 1-2 cells for DC and feature recovery.
- Work unit: one chunk can produce its own local mesh and diagnostics.

Expected impact:

- Reduces memory pressure.
- Prevents a single dense model from hitting global active block and triangle ceilings.
- Enables large worlds or large assemblies where only a small fraction is near the surface.

### 3. Keep MC as Preview, Add a Final-Quality Mesher

Marching Cubes should remain the fast preview mode. Final-quality export should use a separate path.

Candidate final meshers:

- Dual Contouring with stronger crack handling and feature constraints.
- Dual Marching Cubes / adaptive dual extraction.
- MC followed by robust remesh plus SDF projection.
- Hybrid: MC preview, DC/DMC final, optional Blender Geometry Nodes remesh after bake.

Expected impact:

- Better edge preservation than MC.
- More predictable final output for product-grade modeling.

### 4. Feature-Aware SDF Extraction

Clean edges require more than dense sampling. The mesher should know where analytic sharp features exist.

Possible data to preserve:

- primitive type;
- boolean operation boundaries;
- bevel/chamfer parameters;
- analytic normals;
- feature tags for hard edges, flat faces, and intended creases.

Expected impact:

- Avoids relying on numerical gradients alone to recover intentional hard edges.
- Gives DC/QEF a better constraint set.

## Concrete V15.9.9.3 Milestones

1. Diagnostic milestone:
   - Add structured counters for capacity saturation and block/neighbor misses.
   - Surface these diagnostics in Python/UI.

2. Stability milestone:
   - Refuse or warn on partial results when capacities are exceeded.
   - Add conservative fallback modes for high density.

3. Chunk prototype:
   - Implement CPU-driven chunk iteration using existing GPU MC kernels per chunk.
   - Start with MC only, fixed chunk size, and ghost border.

4. Quality prototype:
   - Compare MC, current DC, and remeshed/projected MC on the same test scenes.
   - Identify whether DC failures are from QEF, block boundaries, or topology.

5. Final architecture decision:
   - Decide whether V15.9.9.x should keep improving current sparse block extraction or whether V16 should introduce a new chunked meshing backend.

## Recommended Test Scenes

- Large smooth sphere at high resolution: capacity and memory baseline.
- Thin rods / wires: MC miss detection and subcell recovery.
- Box unions and subtracts: sharp edge quality.
- Dense grid layout instances: active block and primitive-list stress.
- Deformed/twisted primitives: bounds false-negative stress.
- Multi-chunk shape crossing chunk boundaries: crack detection.

## Working Hypothesis

The missing mesh issue is probably not a single Marching Cubes limitation. It is likely a combination of capacity saturation, sparse block detection risk, and MC sampling limits. Edge quality, however, is fundamentally limited by MC and should be addressed with a final-quality mesher rather than only by increasing resolution.

## Implemented In This Branch

- Added GPU mesh statistics in `src/gpu.rs`.
- Added `get_mesh_diagnostics()` to the Rust Python module.
- Stored the latest mesh health string after GPU and CPU mesh generation.
- Displayed a compact mesh health line in the Output & Quality panel.
- Added `Protect Partial Mesh`, enabled by default, to keep the previous valid mesh when diagnostics report `CAPACITY_LIMITED` or `EMPTY_RESULT`.
- Added `Chunked GPU Fallback`, enabled by default, to stream MC extraction through fixed-size GPU chunks when a dense monolithic GPU mesh reports capacity pressure. It reports `algo=GPU_CHUNKED_MC`, uses an automatically adjusted divisor chunk size when possible, and falls back to CPU chunking when needed.
- Added a selectable meshing backend: `Auto`, `GPU Chunked MC`, and `CPU Chunked MC`. This allows large scenes to start with chunked extraction instead of waiting for a monolithic mesh attempt to fail.
- Added `Auto Chunk High Res`, enabled by default, so the Auto backend starts with GPU chunked MC at high preview/export resolutions. The default start threshold is 512.
- Added an experimental `GPU Chunked DC` backend. It reuses the existing GPU DC vertex/face passes per fixed-size chunk and reports `algo=GPU_CHUNKED_DC; experimental=true`. This is intended for edge-quality investigation and still needs dedicated chunk-boundary validation.
- Split GPU chunked MC and GPU chunked DC attempt tracking. A failed explicit `GPU_CHUNKED_DC` run can still fall back to `GPU_CHUNKED_MC` at the original resolution, but normal DC capacity failures now skip chunked DC and prefer the stable chunked MC fallback.
- Extended chunk diagnostics with total chunks, non-empty chunks, empty chunks, and problem chunks. The Output & Quality panel now surfaces those values, plus explicit `reason` fields when a backend refuses or falls back.
- Added one-cell ghost evaluation for GPU chunked MC/DC. Each chunk evaluates a one-cell expanded domain, then filters output triangles by centroid back to the original core chunk bounds. Diagnostics report `ghost_cells=1`.
- Added `filtered_tris` diagnostics for ghost/core filtering so boundary trimming can be inspected from the Output & Quality panel.
- Added chunk-only seam weld scaling. Chunked GPU/CPU paths now use at least `Seam Weld` scale, default `0.05`, while the normal monolithic path keeps the user's regular weld threshold. This targets visible chunk/DC boundary seams without globally increasing weld aggressiveness.
- Changed chunk sizing policy to avoid tiny divisor chunks. The default chunk size is now 128, GPU MC keeps at least 32 cells, and GPU DC keeps at least 64 cells. Non-divisible resolutions are handled directly by the chunk iterator instead of forcing a smaller divisor or falling back.
- Added chunk-count guards to prevent long-running accidental micro-chunk jobs: GPU MC allows up to 2048 chunks, GPU DC up to 512 chunks before reporting `reason=too_many_chunks`.
- User testing showed that `GPU_CHUNKED_DC` leaves visible seams even when seam weld is adjusted. Auto high-resolution DC no longer selects chunked DC; it remains an explicit seam-test backend only. Stable high-resolution fallback now prefers `GPU_CHUNKED_MC`.
- Added `Auto Safe Retry`, enabled by default, to retry once at half resolution after chunked GPU fallback is unavailable or still cannot produce a safe result. This does not change the user's configured resolution.
- Added `Chunked CPU Fallback`, enabled by default, as a final fallback after protected GPU capacity failures. It runs a memory-light CPU Marching Cubes pass in x-axis chunks and reports `algo=CPU_CHUNKED_MC`.
- Split GPU and CPU fallback attempt tracking so a failed `GPU_CHUNKED_MC` result can still proceed to `CPU_CHUNKED_MC` instead of being blocked by a shared "chunked already tried" flag.
- Expanded the Output & Quality diagnostics line with face count, vertex count, and chunk size when those values are available.
- Added GPU domain-origin groundwork: `GpuConfig` and WGSL `Config` now carry `domain_origin`, and MC/DC/detect coordinate generation routes through `grid_to_world()`. The shader path is now ready for per-chunk GPU dispatch.
- Updated `build_sdf_addon.ps1` package name to `SDF_R_15_9_9_3.zip`.
- Rebuilt `rust_gpu_sdf_addon/rust_gpu_sdf.pyd` and `rust_gpu_sdf_addon/bin/win/rust_gpu_sdf.pyd`.

Current health labels:

- `OK`: generation completed without detected capacity pressure.
- `CAPACITY_LIMITED`: active blocks, triangles, vertices, or indices hit a configured cap.
- `BLOCK_OR_PRIM_FALLBACK`: block/primitive list fallback or missing pointer counters were observed.
- `SURFACE_UNDER_SAMPLED`: MC saw empty/refined cells that may indicate missed thin or tangential features.
- `EMPTY_RESULT`: generation produced no mesh data.

This is intentionally a diagnostic first step. The next implementation step should use these labels to drive an automatic fallback policy, such as lowering preview density, switching final output to chunked extraction, or refusing to silently apply a partial mesh.
