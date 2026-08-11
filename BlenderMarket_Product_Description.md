🔥 PHASE 2 LAUNCH SALE!

To celebrate our successful launch and initial milestones, we are offering a Phase 2 Special Price: Only $14.9 !
(This is a limited-time offer for the next 100 copies only — Secure your copy now before the price increases!)


Future Roadmap

To further elevate your modeling workflow, we are excited to share our vision for the next major milestones in Rust-GPU-SDF:

Arbitrary Cross-sections

Description: Real-time cross-section clipping at any angle/plane, and the ability to define custom 2D profiles to subtract or intersect with 3D SDF shapes.
Key Benefit: Enables precise, CAD-like section cuts and intuitive modeling of complex internal structures with zero lag.
Sweep along Curves

Description: Smoothly extrude any 2D profile along a guide path (such as Blender Bezier curves).
Key Benefit: Perfect for generating pipes, cables, or organic swept frames directly on the GPU in real-time.

🚨 CRITICAL SYSTEM REQUIREMENTS

    Supported OS: Windows (64-bit) ONLY. The addon bundles a pre-compiled high-performance Rust binary (.pyd). Currently, macOS and Linux are NOT supported.
    GPU Requirements: Dedicated Graphics Cards (NVIDIA / AMD) supporting DirectX 12 or Vulkan are highly recommended.
    Integrated GPUs: Intel Iris Xe and other integrated GPUs are supported with auto-VRAM memory scaling, but editing speeds may be reduced at extremely high resolutions.
    Blender Version: 3.6 LTS, 4.x, or 5.x.

SDF.R

Pioneering the Next Generation of Blender Modeling

SDF.R is a groundbreaking engine designed to bring the power of Signed Distance Fields (SDF) to Blender with unprecedented speed. As the first-ever add-on in its class to integrate a custom Rust-GPU backend, SDF.R sets a new standard for performance and topological quality.
Stability, High Performance, and Limitations
💎 Main Engine: Marching Cubes (MC) | Experimental Feature: Dual Contouring (DC)


SDF.R primarily features a Marching Cubes (MC) engine that combines stability with high performance.

Looking toward future development, it also includes an experimental GPU-accelerated Dual Contouring (DC) engine for users seeking cutting-edge sharpness. By utilizing a custom QEF (Quadratic Error Function) solver, this experimental DC mode preserves sharp corners and creases (such as box edges) that tend to be smoothed out in conventional SDF environments.
However, since the MC engine takes priority, please understand that DC is strictly an experimental implementation and may be unstable.
✨ What's New in V15.9.x

    ⚡ Local Pipeline Disk Cache & Driver Warm-up: No more mid-sculpt freezes! Compiled shader pipelines are cached locally, cutting subsequent startup times down to just 2-3 seconds.
    📐 Mathematical scale synchronization: Supports multiplicative scaling. Primitives scaled or stretched in Blender match the real-time viewport preview and final baked mesh 1:1.
    🎛️ Non-Destructive Deform Stack: Chain Twist, Bend, and Taper in any order. The mesh generation features stretch-distortion correction to prevent geometry tearing under high deformation.
    🎨 Boolean Subtraction Material Painting: Carved surfaces automatically inherit the Color, Roughness, and Metallic properties of the cutting tool object, enabling interactive multi-material sculpting.
    🛡️ iGPU Low-VRAM Safeguard: The engine dynamically checks your hardware boundaries (such as max_storage_buffer_binding_size) on startup and adjusts block sizes to prevent GPU-related crashes.

🚀 Key Features

    ⚡️ World's First Rust-GPU Engine: Breaking new ground in Blender development. SDF.R utilizes a dedicated Rust backend for unparalleled calculation speeds.
    🎮 Real-time GPU Previews: Instant, interactive feedback via Blender's GPU module. What you see is what you get.
    🧩 Advanced Topology Options: Choose between stable Marching Cubes (MC) for organic sculpting, or Dual Contouring (DC) for sharp mechanical features.
    🌊 Seamless Dynamic Fusion: Effortlessly blend organic curves or sharp mechanical joins with adjustable smoothing.
    📊 Advanced Layout Stacking: Create complex patterns with Mirror, Radial, Spiral, Grid, and Jitter modifiers in one unified stack.

🛠️ Optimized Workflow
1. Build
Arrange primitives in the stack.
2. Refine
Fusion & Boolean operations.
3. Preview
Interactive high-res feedback.
4. Bake
One-click high-quality mesh.





SDF.R V15.9.9 Release Notes


🚀 New Feature: Ultra-Fast "Ghost Preview Only Mode"

Massive Performance Boost via Complete Mesh Generation Bypass: The "Mesh Icon" in the UI has been vastly upgraded. It is no longer just a simple visibility toggle—it now acts as the Master Switch for the entire mesh generation process.
Zero FPS Drop Sculpting Experience: When the Mesh Icon is turned OFF (grayed out), heavy polygonization processes (like Marching Cubes) are completely bypassed. The viewport relies solely on the Raymarching Ghost Shader. You can now tweak shapes, increase resolution, and expand domain sizes with zero calculation overhead!
One-Click Mesh Restoration: After blazing through your modeling tasks in Preview Mode, simply toggle the Mesh Icon back ON. The mesh calculation triggers instantly in the background, rebuilding your actual wireframes and solid meshes on the fly.
💡 Recommended Workflow Keep the "Mesh OFF" for high-speed sculpting, positioning, and layout adjustments. Turn the "Mesh ON" only when you need final visual checks, exporting, or applying boolean modifiers. Experience the ultimate lightweight SDF workflow today!
Rust-GPU-SDF V15.9.8.1 Release Notes(Pilot implementation)

Full Collection Support in Ghost Preview: Advanced layout expansions using Collections (Empty dividers)—such as Mirror, Radial, and Grid—are now fully supported in the real-time Ghost Preview. This allows users to see fast and perfectly accurate raymarched previews in the viewport before generating the final mesh.
1-Click Collection Duplication (Duplicate Collection): Added a dedicated "Duplicate" button for Collection rows in 'The Stack' UI. With a single click, users can duplicate an entire Collection (Empty) along with all its contained SDF primitives. The duplicated group retains all existing layout parameters and is automatically appended to the bottom of the stack.
UI/UX Refinements:
Transformed the Collection name display (e.g., == SDF_Group_Empty ==) in the UI list into a clickable operator button, significantly improving the click hit-box and making it effortless to activate Collections.
Replaced the bulky "Break Parent" text label with a clean, toggleable "Chain" icon.
Optimized the visibility condition for the advanced rotation menu ("Rotation: Indiv & Accum"). The menu now dynamically appears for both primitives and Collections only when "Radial" or "Spiral" layouts are enabled, making the UI much cleaner and more intuitive.
🐛 Bug Fixes
Fixed Mesh Disappearance Caused by Negative Scaling (e.g., Mirroring): Resolved a critical bug in the Rust (WGSL) bounding box (AABB) calculation where negative scale values caused the calculation to break, resulting in missing or cropped meshes. By strictly enforcing absolute value calculations (abs()), the computational engine is now highly robust and safe against extreme layout deformations and scale inversions.


Release Notes (v15.9.8 / Color-related)

Overview
v15.9.8 improves the primitive color workflow with better visibility and user control.
The original fixed palette flow is preserved, while adding selectable color assignment modes for different workflows.

What’s New
Added scene-wide Color Mode
Fixed Palette
Keeps the existing sequential built-in palette behavior.
Auto Hue
Automatically rotates hue for each newly added primitive (with fixed saturation/value).
Single Color
Uses one shared base color for all newly added primitives.
Added Auto Hue controls
Saturation
Value
Hue Step (deg) (0–360, default: 120°)
Hue Offset
Switched Hue Step to degree-based UI
Replaced normalized step-style tuning with angle-based control for better intuitiveness.
UI now consistently uses Hue Step (deg).
Improved visibility in The Stack
Added a color chip per stack row.
Makes object-to-color mapping immediately readable from the list.
UI Placement
Color Mode and related controls are placed in primitive settings
below Color and above Metallic/Roughness.
Compatibility & Behavior
Default mode remains Fixed Palette, preserving current behavior by default.
Color mode is configured scene-wide.
New rules apply on primitive creation; existing object colors are not auto-recolored.

Release Notes  - Rust-GPU-SDF v15.9.7.4

Fixed a mismatch between viewport preview (shader) and generated mesh placement when using Grid layout.
Unified Grid index/clamp behavior in the preview shader to match the mesh-side centered logic.
Added post-Grid accum_idx updates in the preview path so Step Rotation behaves consistently.
Improved visual parity and more natural instancing results, especially with Grid + Step Rotation.


Release Notes for SDF.R V15.9.7.3 (Global UI Update)
We are pleased to announce the release of SDF.R V15.9.7.3. This update focuses on globalizing the add-on interface by standardizing all user-facing labels, property names, operator descriptions, dialog boxes, and warning notifications into English.

Internal logic, identifiers, and calculation properties remain completely unchanged, ensuring 100% stability and compatibility with your existing projects.

What's New in V15.9.7.3
1. Unified English User Interface (Global UI)
All hardcoded Japanese strings in the Blender Sidebar Panel have been translated into clean, industry-standard English terminology:

Deform Stack Types: Translated in both the UI selection dictionary and property metadata:
ストレッチ $\rightarrow$ Elongate
ベンド $\rightarrow$ Bend
ツイスト $\rightarrow$ Twist
テーパー $\rightarrow$ Taper
UI Properties & Dynamic Labels:
係数 / 滑らかさ $\rightarrow$ Factor / Smoothness
大きさ $\rightarrow$ Size
Shell (中空化) $\rightarrow$ Shell (Hollow)
変形 (スタック) $\rightarrow$ Deform (Stack)
種類 $\rightarrow$ Type
有効 $\rightarrow$ Enabled
角度 $\rightarrow$ Angle
Preview Quality Presets:
低 (128) $\rightarrow$ Low (128) (Low load, suitable for simple shapes)
中 (256) $\rightarrow$ Mid (256) (Balanced, suitable for standard deformation)
高 (512) $\rightarrow$ High (512) (High quality, minimizes rendering artifacts)
2. Globalized Dialogs and Warnings
Dual Contouring Switching Confirmation Popup:
Standardized the experimental notice, compilation time warning (approx. 65 seconds), and Blender unresponsive warning message into English.
Operators & Tooltips:
All operator labels (e.g., Add Deform, Remove Deform, Move Deform, Add SDF Primitive) and their corresponding tooltips/descriptions displayed in the status bar are now fully localized in English.
Reports and Notifications:
Operations warnings, such as "Output object not found" or "Up to 2 deforms are allowed (lightweight version)," have been translated for improved global usability.
3. Under the Hood & Documentation
Log System: Updated the console initialization and GPU warming-up print messages to output version V15.9.7.3.
Packaging: The package output is now version-upgraded and successfully compiled into SDF_R_15_9_7_3.zip.
Manual: Updated version metadata and setup package references inside README.md to V15.9.7.3.


Release Notes - Rust-GPU-SDF V15.9.7.2
Bug Fixes
Fixed Radial Pattern Alignment and Rotation Direction on Y-Axis (`axis == 1`):
   Resolved a misalignment issue where the real-time viewport preview (GLSL) and the generated mesh (Rust/WGSL) did not match when using the Radial/Spiral pattern on the Y-axis.
   Corrected the internal coordinate mapping in the mesh generator. Previously, the generator treated the X-axis as the primary coordinate and the Z-axis as the secondary coordinate (leading to a clockwise rotation and offset along the X-axis). It has now been corrected to use the Z-axis as the primary coordinate and the X-axis as the secondary coordinate, matching the viewport's behavior (counter-clockwise rotation and offset along the Z-axis).
   This fix also ensures that any step rotation or accumulated rotation calculations are correctly applied to the proper coordinate axes under the Y-axis radial layout.
## Affected Components
 `src/common.wgsl` - Updated layout evaluation logic for Y-axis radial patterns.
 `src/lib.rs` - Updated CPU-side coordinate transform mapping.
 `src/sdf.rs` - Updated CPU-side coordinate transform evaluation logic.

Release Notes: Rust-GPU-SDF-V15.9.7.1
This update introduces Primitive Edge Profiles, SDF Shelling, customizable Blend Profiles, and improved GPU initialization stability.

1. Key Features & Enhancements
Primitive Edge Profiles (Bevel / Rounding)
Added edge rounding and chamfering directly to primitives.
Supported Shapes: Box, Cylinder, Rounded Box, Hex Prism, Ngon Prism.
Profiles: Round (default), Sharp, Soft, Tight, and Chamfer (with adjustable smooth coefficient).
SDF Shelling (Hollow Modifier)
Hollows out shapes using the formula: abs(d) - shell_thickness.
Fully synchronized across CPU (Rust) and GPU (WGSL/Python shader).
Auto-calculated AABB bounds padding prevents clipping.
Custom Blend Profiles
Added transition profiles for blending operations (Union, Subtract, Intersect).
Profiles: Round (default), Sharp, Soft, Tight, and Chamfer.
GPU Initialization Auto-Recovery
Automatically removes corrupted shader cache files and retries compilation on startup failure.

2. Technical Changes
Blender Add-on (Python)
__init__.py: Updated version to (15, 9, 7, 2) and added cache deletion/retry logic on GPU init error.
properties.py & ui.py: Exposed properties and UI controls for edge profiles, shelling, and blend profiles.
engine.py: Added new properties to arguments passed to the Rust backend.
handlers.py & shader.py: Expanded GPU preview texture size from 15 to 16 pixels per primitive to transmit new parameters. Synchronized preview shader with GLSL.
Backend (Rust / WGSL)
Cargo.toml: Added Naga crate integration for shader validation.
src/gpu.rs & src/lib.rs & src/python_api.rs: Updated Primitive struct layouts and added shell/edge padding to AABB calculation.
src/common.wgsl & src/sdf.rs: Implemented new blend profiles and primitive edge math synchronously on both CPU and GPU.

SDF.R V15.9.7 Release Notes
We are excited to announce the release of SDF.R V15.9.7, which significantly expands the modeling capabilities of the add-on by introducing 5 new primitives and addresses critical rendering/meshing issues, especially in high-resolution settings and complex smooth-blending scenarios.

New Features
Added 5 New Primitive Types (Tier 1) Five highly requested shape primitives have been implemented across all pipeline layers (UI, Viewport Preview GLSL, GPU Compute WGSL, and CPU Fallback Rust):
Ellipsoid (with independent X/Y/Z radii parameters)
Rounded Cylinder (with base radius, height, and rounding radius)
Capped Torus (with major/minor radii and sweep angle limits)
Octahedron (with scale/size parameter)
Cut Sphere (with radius and cutting height plane)

Bug Fixes and Stability Improvements
Fixed GPU Shape Fallback Issue Resolved a bug where the newly added shapes fell back to the default "Sphere" primitive when generating meshes via the GPU path. The serialization maps in the Rust GPU bridge now correctly bind the new shape IDs (10 to 14).
Fixed Mesh Clipping on Parameter Changes Fixed a critical mesh clipping (loss of geometry) issue when scaling or adjusting parameters of the new shapes (such as the Ellipsoid's radii). The local AABB (Axis-Aligned Bounding Box) logic in the Rust engine and the domain expansion algorithm in Python are now synchronized dynamically with the shape-specific parameters.
Fixed Blocky/Circular Mesh Holes at High Resolutions Resolved an issue where shapes would appear with blocky or circular holes when meshing at high resolutions (e.g., Res 256). The GPU block detection shader (detect.wgsl) has been updated to correctly evaluate and keep the computation blocks for the new shape IDs (10 to 14), preventing sparse block skipping bugs.
Resolved Mesh Cracking in Smooth Blending Fixed a topological cracking bug that occurred when blending primitives (such as Cylinders) with high smoothness settings (e.g., Smoothness = 2.0) or when primitives were rotated.
The outer bounding radius calculation has been rewritten to use 3D diagonal vector lengths (length(local_ext * size)) instead of 1D maximums.
The safety margin for active block detection was expanded from max(step * 8.0, 0.45) to max(step * 12.0, 0.65), ensuring seamless blending across computation blocks without distance field discontinuities.

Release Notes — V15.9.6.2

V15.9.6.2 focuses on robustness improvements for mesh generation stability in complex CSG workflows, especially in scenes composed of spheres/cylinders with subtraction operations.

Improvements

Strengthened mitigation for band-like mesh dropout observed near shape boundaries during subtraction-heavy modeling.
Improved Detect Pass block evaluation and added a safety fallback to full-primitive evaluation when local primitive candidate lists become unreliable.
Added a conservative CSG safety mode to reduce topology corruption (unexpected holes/floating artifacts) caused by local-list culling in blocks affected by subtraction/intersection/smooth CSG operations.
Enhanced Marching Cubes boundary handling by adding local re-evaluation for near-surface empty/full cells, reducing thin-boundary sampling misses.
Improved GPU initialization and shader compilation stability in the updated pipeline path.
Updated add-on version metadata to 15.9.6.2.
Known Considerations

In CSG-heavy scenes, this version may trade some performance for improved mesh stability and correctness.
While significantly reduced, edge-case artifacts may still require additional tuning under extreme geometry/resolution combinations.

SDF.R V15.9.5 Release Notes
Highlights
Improved stability for integrated GPUs (iGPU) during startup
Fixed clipped/cutoff geometry in torus-heavy layout workflows
Improved GPU preview reliability for large procedural layouts
What’s Fixed
1) Torus clipping in layout workflows
Addressed an issue where torus shapes could appear cut off after using layout features such as radial/grid/spiral arrangements.
Detection bounds are now shape-aware and account for torus-specific parameters more accurately.
2) GPU initialization crash on iGPU systems
Added dynamic memory safety guards for integrated/UMA GPUs to prevent startup failures caused by oversized GPU buffers.
This reduces the chance of initialization errors such as “Not enough memory left” during buffer creation.
3) Preview cutoff while mesh output remains correct
Improved preview-domain handling so the raymarch preview better matches actual scene extent when auto-domain and layout features are used.
Preview step budgeting now scales more safely for larger scenes to reduce visual cutoff in the viewport overlay.
Internal Improvements
Updated add-on version metadata to 15.9.5
Rebuilt native module and refreshed packaged add-on archive for this release
Notes
These fixes prioritize reliability and visual consistency, especially on lower-memory GPU environments.
In very large scenes, performance may trade slightly for stability due to safer bound estimation.

---

Creator's Oath
 In the spirit of free software and the GNU GPL:
 May Blender forever remain free under the GPL!
 This addon guarantees all users the freedom to learn from,
 modify, and share this source code — forever.

Copyright © 2026 hinata_hugu. Built with passion and AI collaboration.
