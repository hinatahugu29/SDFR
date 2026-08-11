# SDF-R (Rust-GPU-SDF) Documentation & User Guide
(For V15.9.x)

Welcome to the official documentation for **SDF-R (Rust-GPU-SDF)**, a next-generation Signed Distance Field (SDF) modeling engine built using Rust and GPU (wgpu/WGSL) acceleration for Blender.

---

## 1. Quick Start & Installation

### System Requirements
Before installing, please ensure your system matches the requirements:
* **Supported OS**: Windows 10/11 (64-bit) ONLY. (macOS and Linux are not supported yet).
* **GPU**: A dedicated graphics card (NVIDIA / AMD) supporting DirectX 12 or Vulkan is highly recommended. Integrated GPUs (like Intel Iris Xe) are supported with automated memory optimization, but may have lower performance at very high resolutions.
* **Blender Version**: Blender 3.6 LTS, 4.x, or 5.x.

### Installation Steps
1. Download the addon zip file (`SDF_R_V15_9_x.zip`).
2. In Blender, go to **Edit** > **Preferences** > **Add-ons**.
3. Click **Install...** and select the zip file.
4. Check the box to enable **SDF-R (Rust-GPU-SDF)**.
5. Save your preferences.

### Important: The First Startup (Warm-up Delay)
When you first toggle the **Live Update** in the SDF-R panel, you will experience a compilation delay of about **15 to 45 seconds** depending on your GPU.
* **What is happening?** The engine is compiling the high-performance GPU shaders (WGSL) and running a mandatory "driver warm-up" to optimize the rendering pipeline.
* **Do not panic**: Blender might seem temporarily unresponsive during this period. Do not close Blender.
* **Disk Caching**: This optimization is cached to your local disk. Subsequent starts will take only **2 to 3 seconds**.

---

## 2. Interface Overview

Once enabled, you will find the **SDF-R** tab in the Sidebar of the 3D Viewport (press `N` to open the sidebar).

The panel is structured into four main areas:
1. **Core Controls**: Toggles Live Update, Resolution, and Mesh Quality.
2. **Primitive List & Settings**: Manage shape types (Sphere, Box, Torus, Bezier Curve, etc.) and edit their individual dimensions, positions, and blending options.
3. **Deform Stack**: Non-destructively apply deformations like Bend, Twist, and Taper.
4. **Layout Stacking**: Repeat and mirror primitives in various spatial arrangements.

---

## 3. Core Concept: Dual Contouring vs. Marching Cubes

SDF-R features two mesh generation backends which you can choose depending on your model:

### Marching Cubes (MC)
* **Best for**: Smooth, organic, fluid, and clay-like shapes.
* **Characteristics**: Extremely stable topology, ideal for characters, liquids, or soft round surfaces.

### Dual Contouring (DC)
* **Best for**: Hard surface modeling, mechanical parts, sharp boxy corners.
* **Characteristics**: Uses a GPU-accelerated Quadratic Error Function (QEF) solver to identify and reconstruct sharp edges and creases that usually get rounded off in traditional SDF engines.
* *Note: First-time activation of DC triggers a brief lazy-compilation warm-up.*

---

## 4. Working with Deformers and Layout Stacking

SDF-R allows you to chain deformations and layout repetitions in real time.

### Non-Destructive Deform Stack
Apply **Twist**, **Bend**, or **Taper** deformations by adding items to the Deform List.
* **Dynamic Ordering**: You can reorder the deformers in the list. Changing the stack order (e.g., Tapering before Twisting vs. Twisting before Tapering) will change the final shape.
* **Stretch Correction**: The engine features an automatic mathematical distance correction so that extreme twists and bends do not cause mesh tearing or clipping.

### Layout Stacking
Instantly duplicate your shapes across space using:
* **Mirror**: Symmetry replication across selected axes.
* **Grid**: Compact repeat patterns.
* **Radial / Spiral**: Distribute duplicates in a circle or a climbing spiral.
* **Jitter**: Add randomized offsets to your layouts to make them look hand-crafted.

---

## 5. Attribute & Material Painting

SDF-R passes material attributes (color, metallic, roughness) directly from the primitives to the generated mesh.

* **Subtractive Painting**: When you perform a subtractive boolean operation (carving out shape A using shape B), the newly exposed inner surface created by the cut **automatically inherits the color and material properties of the cutting object B**. This allows you to "carving paint" multi-colored, multi-material details onto your models effortlessly.

---

## 6. Performance Optimization & Troubleshooting

### Low VRAM / Integrated GPU (iGPU) Safeguard
If you are running on an integrated GPU like Intel Iris Xe or a low-end laptop GPU:
* The addon dynamically queries the hardware limits (`max_storage_buffer_binding_size`) on startup.
* If memory is low, it will scale down the maximum active blocks automatically to prevent Blender from crashing.
* **Tip**: Keep the mesh generation resolution slider at a moderate level (e.g., 128 to 256) for optimal editing speed on integrated GPUs.

### Common Troubleshooting

#### Q: Blender freezes when I first click Live Update.
* **A**: This is normal. It is compiling shaders and caching them. Please wait up to 1 minute. All future activations will be instantaneous.

#### Q: The generated mesh has holes or missing faces under high deformation.
* **A**: Make sure the domain size is large enough to contain the deformed shape, and the mesh quality resolution is adequate. Additionally, verify that the deform parameters are within reasonable limits.

#### Q: I get a shader validation error on startup.
* **A**: Ensure your graphics card drivers are updated to the latest version. Make sure your system defaults to using your dedicated graphics card (NVIDIA/AMD) rather than the motherboard's integrated chip when running Blender.

---
*Documented on 2026-05-19 by Antigravity*
