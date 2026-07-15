import re

file_path = "e:/blender_addon/外部テスト/Rust-GPU-SDF-V15.9.7.1/src/gpu.rs"
with open(file_path, "r", encoding="utf-8") as f:
    text = f.read()

prefix = """use wgpu::util::DeviceExt;
use std::sync::{atomic::{AtomicUsize, Ordering}, RwLock};

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuPrimitive {
    pub center_and_shape: [f32; 4], // [x, y, z, shape_type]
    pub rotation: [f32; 4],         // [x, y, z, w]
    pub size_and_op: [f32; 4],      // [sx, sy, sz, operation]
    pub params: [f32; 4],           // [radius, smoothness, metallic, roughness]
    pub noise_params: [f32; 4],     // [strength, scale, color_r, color_g]
    pub color_b_and_extra: [f32; 4], // [color_b, unused, unused, unused]
    pub layout_data1: [f32; 4],     // [mode_flags, p1, p2, p3]
    pub layout_data2: [f32; 4],     // [p4, p5, p6, p7]
    pub layout_data3: [f32; 4],     // [p8, p9, p10, p11]
    pub layout_data4: [f32; 4],     // [p12, p13, p14, p15]
    pub extra_params: [f32; 4],     // [p1, p2, p3, p4] (V13)
    pub deform_data1: [f32; 4],     // [flags, stretch_x, stretch_y, stretch_z]
    pub deform_data2: [f32; 4],     // [bend_angle, bend_axis, bend_center, twist_angle]
    pub deform_data3: [f32; 4],     // [twist_axis, twist_center, taper_factor, taper_axis]
    pub deform_data4: [f32; 4],     // [taper_center, 0, 0, 0]
    pub modifier_params: [f32; 4],  // [edge_profile, shell_thickness, edge_chamfer_smooth, free]
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuBvhNode {
    pub min: [f32; 4], // [x, y, z, child_or_prim_idx]
    pub max: [f32; 4], // [x, y, z, count] (count > 0 means leaf)
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuConfig {
    pub res: u32,
    pub domain_size: f32,
    pub num_primitives: u32,
    pub symmetry: u32, // Bitmask: X=1, Y=2, Z=4
"""

start_idx = text.find("    pub hash_table_size: u32,")
if start_idx != -1:
    new_text = prefix + text[start_idx:]
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Fixed gpu.rs")
else:
    print("Could not find start idx")
