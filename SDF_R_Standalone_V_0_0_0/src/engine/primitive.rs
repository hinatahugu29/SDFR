use glam::{Vec3, Quat};
use serde::{Serialize, Deserialize};

pub const LAYOUT_FLAG_MIRROR: u32 = 1;
pub const LAYOUT_FLAG_RADIAL: u32 = 2;
pub const LAYOUT_FLAG_GRID: u32 = 8;

pub const DEFORM_TYPE_NONE: u32 = 0;
pub const DEFORM_TYPE_ELONGATE: u32 = 1;
pub const DEFORM_TYPE_BEND: u32 = 2;
pub const DEFORM_TYPE_TWIST: u32 = 3;
pub const DEFORM_TYPE_TAPER: u32 = 4;
pub const DEFORM_TYPE_SHELL: u32 = 5;

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
    pub extra_params: [f32; 4],     // [p1, p2, p3, p4]
    pub deform_data1: [f32; 4],     // [flags, p1, p2, p3]
    pub deform_data2: [f32; 4],     // [p4, p5, p6, p7]
    pub deform_data3: [f32; 4],     // [p8, p9, p10, p11]
    pub deform_data4: [f32; 4],     // [p12, 0, 0, 0]
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuConfig {
    pub res: u32,
    pub domain_size: f32,
    pub num_primitives: u32,
    pub symmetry: u32,
    
    pub bg_color: [f32; 3],
    pub ao_strength: f32,
    
    pub shadow_softness: f32,
    pub _pad1: [u32; 3], 
    
    pub floor_color: [f32; 3],
    pub env_intensity: f32,
    
    pub selected_idx: i32,
    pub _pad2: [u32; 3],
}

#[derive(Clone, Copy, Debug)]
pub struct SdfPrimitive {
    pub center: Vec3,
    pub shape_type: u32,
    pub rotation: Quat,
    pub size: Vec3,
    pub operation: u32,
    pub radius: f32,
    pub smoothness: f32,
    pub metallic: f32,
    pub roughness: f32,
    pub color: Vec3,
    pub visible: bool,
    pub noise_strength: f32,
    pub noise_scale: f32,
    pub layout_flags: u32,
    pub layout_params: [[f32; 4]; 4],
    pub deform_flags: u32,
    pub deform_params: [[f32; 4]; 4],
    pub extra_params: [f32; 4],
    pub emission: f32,
    pub color_influence: f32,
    pub shell_thickness: f32,
    pub id: u32,
    pub parent_id: Option<u32>,
    pub is_group: bool,
}

#[derive(Serialize, Deserialize)]
pub struct SdfPrimitiveSerial {
    pub center: [f32; 3],
    pub shape_type: u32,
    pub rotation: [f32; 4],
    pub size: [f32; 3],
    pub operation: u32,
    pub radius: f32,
    pub smoothness: f32,
    pub metallic: f32,
    pub roughness: f32,
    pub color: [f32; 3],
    pub visible: bool,
    pub noise_strength: f32,
    pub noise_scale: f32,
    pub layout_flags: u32,
    pub layout_params: [[f32; 4]; 4],
    pub deform_flags: u32,
    pub deform_params: [[f32; 4]; 4],
    pub extra_params: [f32; 4],
    pub emission: f32,
    pub color_influence: f32,
    pub shell_thickness: f32,
    pub id: u32,
    pub parent_id: Option<u32>,
    pub is_group: bool,
}

impl SdfPrimitiveSerial {
    pub fn from_primitive(p: &SdfPrimitive) -> Self {
        Self {
            center: [p.center.x, p.center.y, p.center.z],
            shape_type: p.shape_type,
            rotation: [p.rotation.x, p.rotation.y, p.rotation.z, p.rotation.w],
            size: [p.size.x, p.size.y, p.size.z],
            operation: p.operation,
            radius: p.radius,
            smoothness: p.smoothness,
            metallic: p.metallic,
            roughness: p.roughness,
            color: [p.color.x, p.color.y, p.color.z],
            visible: p.visible,
            noise_strength: p.noise_strength,
            noise_scale: p.noise_scale,
            layout_flags: p.layout_flags,
            layout_params: p.layout_params,
            deform_flags: p.deform_flags,
            deform_params: p.deform_params,
            extra_params: p.extra_params,
            emission: p.emission,
            color_influence: p.color_influence,
            shell_thickness: p.shell_thickness,
            id: p.id,
            parent_id: p.parent_id,
            is_group: p.is_group,
        }
    }

    pub fn to_primitive(&self) -> SdfPrimitive {
        SdfPrimitive {
            center: Vec3::new(self.center[0], self.center[1], self.center[2]),
            shape_type: self.shape_type,
            rotation: Quat::from_xyzw(self.rotation[0], self.rotation[1], self.rotation[2], self.rotation[3]),
            size: Vec3::new(self.size[0], self.size[1], self.size[2]),
            operation: self.operation,
            radius: self.radius,
            smoothness: self.smoothness,
            metallic: self.metallic,
            roughness: self.roughness,
            color: Vec3::new(self.color[0], self.color[1], self.color[2]),
            visible: self.visible,
            noise_strength: self.noise_strength,
            noise_scale: self.noise_scale,
            layout_flags: self.layout_flags,
            layout_params: self.layout_params,
            deform_flags: self.deform_flags,
            deform_params: self.deform_params,
            extra_params: self.extra_params,
            emission: self.emission,
            color_influence: self.color_influence,
            shell_thickness: self.shell_thickness,
            id: self.id,
            parent_id: self.parent_id,
            is_group: self.is_group,
        }
    }
}

impl SdfPrimitive {
    pub fn new_sphere(pos: Vec3, radius: f32) -> Self {
        Self {
            center: pos,
            shape_type: 0,
            rotation: Quat::IDENTITY,
            size: Vec3::ONE,
            operation: 0,
            radius,
            smoothness: 0.1,
            metallic: 0.0,
            roughness: 0.5,
            color: Vec3::new(0.8, 0.8, 0.8),
            visible: true,
            noise_strength: 0.0,
            noise_scale: 1.0,
            layout_flags: 0,
            layout_params: [[0.0; 4]; 4],
            deform_flags: 0,
            deform_params: [[0.0; 4]; 4],
            extra_params: [0.0; 4],
            emission: 0.0,
            color_influence: 1.0,
            shell_thickness: 0.0,
            id: 0,
            parent_id: None,
            is_group: false,
        }
    }

    pub fn new_group(pos: Vec3) -> Self {
        Self {
            center: pos,
            shape_type: 255, 
            rotation: Quat::IDENTITY,
            size: Vec3::ONE,
            operation: 0,
            radius: 0.0,
            smoothness: 0.0,
            metallic: 0.0,
            roughness: 0.0,
            color: Vec3::new(1.0, 1.0, 0.0), 
            visible: true,
            noise_strength: 0.0,
            noise_scale: 1.0,
            layout_flags: 0,
            layout_params: [[0.0; 4]; 4],
            deform_flags: 0,
            deform_params: [[0.0; 4]; 4],
            extra_params: [0.0; 4],
            emission: 0.0,
            color_influence: 0.0,
            shell_thickness: 0.0,
            id: 0,
            parent_id: None,
            is_group: true,
        }
    }

    pub fn new_cube(pos: Vec3, size: Vec3) -> Self {
        Self {
            center: pos,
            shape_type: 1,
            rotation: Quat::IDENTITY,
            size,
            operation: 0,
            radius: 0.0,
            smoothness: 0.1,
            metallic: 0.0,
            roughness: 0.5,
            color: Vec3::new(0.8, 0.8, 0.8),
            visible: true,
            noise_strength: 0.0,
            noise_scale: 1.0,
            layout_flags: 0,
            layout_params: [[0.0; 4]; 4],
            deform_flags: 0,
            deform_params: [[0.0; 4]; 4],
            extra_params: [0.0; 4],
            emission: 0.0,
            color_influence: 1.0,
            shell_thickness: 0.0,
            id: 0,
            parent_id: None,
            is_group: false,
        }
    }

    pub fn new_torus(pos: Vec3, r1: f32, r2: f32) -> Self {
        let mut p = Self::new_sphere(pos, r1);
        p.shape_type = 2;
        p.extra_params[0] = r1;
        p.extra_params[1] = r2;
        p
    }

    pub fn new_cylinder(pos: Vec3, r: f32, h: f32) -> Self {
        let mut p = Self::new_sphere(pos, r);
        p.shape_type = 3;
        p.extra_params[0] = r;
        p.extra_params[1] = h;
        p
    }

    pub fn new_rounded_box(pos: Vec3, size: Vec3, r: f32) -> Self {
        let mut p = Self::new_cube(pos, size);
        p.shape_type = 4;
        p.extra_params[0] = r;
        p
    }

    pub fn new_capsule(pos: Vec3, r: f32, h: f32) -> Self {
        let mut p = Self::new_sphere(pos, r);
        p.shape_type = 5;
        p.extra_params[0] = r;
        p.extra_params[1] = h;
        p
    }

    pub fn new_hex_prism(pos: Vec3, r: f32, h: f32) -> Self {
        let mut p = Self::new_sphere(pos, r);
        p.shape_type = 6;
        p.extra_params[0] = r;
        p.extra_params[1] = h;
        p
    }



    pub fn to_gpu(&self, is_selected: bool) -> GpuPrimitive {
        let mut op = if self.visible { self.operation as f32 } else { 15.0 };
        let mut radius = self.radius;
        let mut shape_type = self.shape_type;
        
        if self.is_group {
            if is_selected {
                op = 0.0; // Union to make it visible
                radius = 0.05; // Small point
                shape_type = 0; // Sphere
            } else {
                op = 15.0; // Invisible
            }
        }
        
        let layout_packed = (self.layout_flags & 0xFF) | (self.layout_params[0][0] as u32 & 0xFFFF_FF00);
        
        let mut deform_flags = [0u32; 2];
        for i in 0..2 {
            let slot_type = (self.deform_flags >> (i * 6)) & 0xF;
            let slot_axis = (self.deform_flags >> (i * 6 + 4)) & 0x3;
            deform_flags[i] = (slot_type & 0xF) | ((slot_axis & 0x3) << 4);
        }

        GpuPrimitive {
            center_and_shape: [self.center.x, self.center.y, self.center.z, shape_type as f32],
            rotation: [self.rotation.x, self.rotation.y, self.rotation.z, self.rotation.w],
            size_and_op: [self.size.x, self.size.y, self.size.z, op],
            params: [radius, self.smoothness, self.metallic, self.roughness],
            noise_params: [self.noise_strength, self.noise_scale, self.color.x, self.color.y],
            color_b_and_extra: [self.color.z, self.emission, self.color_influence, self.shell_thickness],
            layout_data1: [layout_packed as f32, self.layout_params[0][1], self.layout_params[0][2], self.layout_params[0][3]],
            layout_data2: self.layout_params[1],
            layout_data3: self.layout_params[2],
            layout_data4: self.layout_params[3],
            extra_params: self.extra_params,
            deform_data1: [deform_flags[0] as f32, self.deform_params[0][0], self.deform_params[0][1], self.deform_params[0][2]],
            deform_data2: [self.deform_params[0][3], 0.0, 0.0, 0.0],
            deform_data3: [deform_flags[1] as f32, self.deform_params[1][0], self.deform_params[1][1], self.deform_params[1][2]],
            deform_data4: [self.deform_params[1][3], 0.0, 0.0, 0.0],
        }
    }
}
