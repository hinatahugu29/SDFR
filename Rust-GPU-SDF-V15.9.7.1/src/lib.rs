use pyo3::prelude::*;
use nalgebra::{Vector2, Vector3, Quaternion, UnitQuaternion};
use std::time::Instant;
use std::collections::HashMap;

mod tables;
mod gpu;
mod gpu_table_gen;
mod dc;

use tables::get_triangles;
use gpu::{SdfGpuContext, GpuPrimitive, GpuConfig, GpuBvhNode};
use once_cell::sync::Lazy;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};

static GPU_CONTEXT: Mutex<Option<SdfGpuContext>> = Mutex::new(None);

// V10.3: 非同期ステート管理
static MESH_RESULT: Lazy<Mutex<Option<(Vec<f32>, Vec<u32>)>>> = Lazy::new(|| Mutex::new(None));
static IS_UPDATING: AtomicBool = AtomicBool::new(false);


#[pyclass]
#[derive(Clone)]
pub struct SdfPrimitive {
    pub shape_type: String,
    pub center: [f32; 3],
    pub rotation: [f32; 4],
    pub radius: f32,
    pub size: [f32; 3],
    pub operation: i32,
    pub smoothness: f32,
    pub color: [f32; 3],
    pub metallic: f32,
    pub roughness: f32,
    pub noise_strength: f32,
    pub noise_scale: f32,
    pub layout_data1: [f32; 4],
    pub layout_data2: [f32; 4],
    pub layout_data3: [f32; 4],
    pub layout_data4: [f32; 4],
    pub extra_params: [f32; 4],
    pub deform_data1: [f32; 4],
    pub deform_data2: [f32; 4],
    pub deform_data3: [f32; 4],
    pub deform_data4: [f32; 4],
    pub blend_profile: u32,
    pub chamfer_smooth: f32,
    pub edge_profile: u32,
    pub edge_profile_size: f32,
    pub edge_chamfer_smooth: f32,
    pub shell_thickness: f32,
    pub vertices: Option<Vec<f32>>,
    pub indices: Option<Vec<u32>>,
}

#[pymethods]
impl SdfPrimitive {
    #[new]
    #[pyo3(signature = (shape_type, center, rotation, radius, size, operation, smoothness, color, metallic, roughness, noise_strength, noise_scale, layout_data1=[0.0,0.0,0.0,0.0], layout_data2=[0.0,0.0,0.0,0.0], layout_data3=[0.0,0.0,0.0,0.0], layout_data4=[0.0,0.0,0.0,0.0], extra_params=[0.0,0.0,0.0,0.0], deform_data1=[0.0,0.0,0.0,0.0], deform_data2=[0.0,0.0,0.0,0.0], deform_data3=[0.0,0.0,0.0,0.0], deform_data4=[0.0,0.0,0.0,0.0], blend_profile=0, chamfer_smooth=0.0, edge_profile=0, edge_chamfer_smooth=0.0, shell_thickness=0.0, edge_profile_size=0.0, vertices=None, indices=None))]
    fn new(
        shape_type: String,
        center: [f32; 3],
        rotation: [f32; 4],
        radius: f32,
        size: [f32; 3],
        operation: i32,
        smoothness: f32,
        color: [f32; 3],
        metallic: f32,
        roughness: f32,
        noise_strength: f32,
        noise_scale: f32,
        layout_data1: [f32; 4],
        layout_data2: [f32; 4],
        layout_data3: [f32; 4],
        layout_data4: [f32; 4],
        extra_params: [f32; 4],
        deform_data1: [f32; 4],
        deform_data2: [f32; 4],
        deform_data3: [f32; 4],
        deform_data4: [f32; 4],
        blend_profile: u32,
        chamfer_smooth: f32,
        edge_profile: u32,
        edge_chamfer_smooth: f32,
        shell_thickness: f32,
        edge_profile_size: f32,
        vertices: Option<Vec<f32>>,
        indices: Option<Vec<u32>>,
    ) -> Self {
        Self {
            shape_type,
            center,
            rotation,
            radius,
            size,
            operation,
            smoothness,
            color,
            metallic,
            roughness,
            noise_strength,
            noise_scale,
            layout_data1,
            layout_data2,
            layout_data3,
            layout_data4,
            extra_params,
            deform_data1,
            deform_data2,
            deform_data3,
            deform_data4,
            blend_profile,
            chamfer_smooth,
            edge_profile,
            edge_profile_size,
            edge_chamfer_smooth,
            shell_thickness,
            vertices,
            indices,
        }
    }
}

/// 三角形と点の最短距離を計算
fn dot2(v: Vector3<f32>) -> f32 { v.dot(&v) }

fn dist_to_triangle(p: Vector3<f32>, v0: Vector3<f32>, v1: Vector3<f32>, v2: Vector3<f32>) -> f32 {
    let v10 = v1 - v0; let p0 = p - v0;
    let v21 = v2 - v1; let p1 = p - v1;
    let v02 = v0 - v2; let p2 = p - v2;
    let nor = v10.cross(&v02);

    let sign = v10.cross(&nor).dot(&p0).signum() +
                v21.cross(&nor).dot(&p1).signum() +
                v02.cross(&nor).dot(&p2).signum() < 2.0;

    if sign {
        let d1 = dot2(v10 * (v10.dot(&p0) / dot2(v10)).clamp(0.0, 1.0) - p0);
        let d2 = dot2(v21 * (v21.dot(&p1) / dot2(v21)).clamp(0.0, 1.0) - p1);
        let d3 = dot2(v02 * (v02.dot(&p2) / dot2(v02)).clamp(0.0, 1.0) - p2);
        d1.min(d2.min(d3)).sqrt()
    } else {
        (nor.dot(&p0).powi(2) / dot2(nor)).sqrt()
    }
}

fn rotate_aabb(min: Vector3<f32>, max: Vector3<f32>, q: UnitQuaternion<f32>) -> (Vector3<f32>, Vector3<f32>) {
    let corners = [
        Vector3::new(min.x, min.y, min.z),
        Vector3::new(max.x, min.y, min.z),
        Vector3::new(min.x, max.y, min.z),
        Vector3::new(max.x, max.y, min.z),
        Vector3::new(min.x, min.y, max.z),
        Vector3::new(max.x, min.y, max.z),
        Vector3::new(min.x, max.y, max.z),
        Vector3::new(max.x, max.y, max.z),
    ];
    let mut new_min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
    let mut new_max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
    for c in corners.iter() {
        let p = q * c;
        new_min = new_min.inf(&p);
        new_max = new_max.sup(&p);
    }
    (new_min, new_max)
}

fn calculate_primitive_sdf(local_p: Vector3<f32>, primitive: &SdfPrimitive, bvh: &Option<MeshBvh>) -> f32 {
    let s = Vector3::new(
        primitive.size[0].max(0.001f32),
        primitive.size[1].max(0.001f32),
        primitive.size[2].max(0.001f32)
    );
    // 空間をスケールで割る
    let p = Vector3::new(local_p.x / s.x, local_p.y / s.y, local_p.z / s.z);
    let s_min = s.x.min(s.y).min(s.z);

    let edge_profile = primitive.edge_profile;
    let edge_cs = primitive.edge_chamfer_smooth;
    let edge_k = primitive.edge_profile_size / s_min;

    let d = match primitive.shape_type.as_str() {
        "sphere" => {
            p.norm() - primitive.radius
        }
        "box" => {
            if edge_profile > 0 {
                let q = p.abs() - Vector3::new(1.0, 1.0, 1.0);
                let d_tmp = apply_primitive_edge(q.x, q.y, edge_profile, edge_k, edge_cs);
                apply_primitive_edge(d_tmp, q.z, edge_profile, edge_k, edge_cs)
            } else {
                let q = p.abs() - Vector3::new(1.0, 1.0, 1.0);
                q.x.max(0.0).hypot(q.y.max(0.0).hypot(q.z.max(0.0))) + q.x.max(q.y.max(q.z)).min(0.0)
            }
        }
        "rounded_box" => {
            if edge_profile > 0 {
                let q = p.abs() - Vector3::new(1.0, 1.0, 1.0);
                let d_tmp = apply_primitive_edge(q.x, q.y, edge_profile, primitive.extra_params[0], edge_cs);
                apply_primitive_edge(d_tmp, q.z, edge_profile, primitive.extra_params[0], edge_cs)
            } else {
                let r = primitive.extra_params[0];
                let q = p.abs() - Vector3::new(1.0, 1.0, 1.0) + Vector3::new(r, r, r);
                q.x.max(0.0).hypot(q.y.max(0.0).hypot(q.z.max(0.0))) + q.x.max(q.y.max(q.z)).min(0.0) - r
            }
        }
        "torus" => {
            let r1 = primitive.extra_params[0];
            let r2 = primitive.extra_params[1];
            let q_torus = Vector2::new(p.x, p.y).norm() - r1;
            Vector2::new(q_torus, p.z).norm() - r2
        }
        "cylinder" => {
            if edge_profile > 0 {
                let d_cyl = Vector2::new(p.x, p.y).norm() - primitive.extra_params[0];
                let d_slab = p.z.abs() - primitive.extra_params[1];
                apply_primitive_edge(d_cyl, d_slab, edge_profile, edge_k, edge_cs)
            } else {
                let r = primitive.extra_params[0];
                let h = primitive.extra_params[1];
                let d_cyl = Vector2::new(Vector2::new(p.x, p.y).norm() - r, p.z.abs() - h);
                d_cyl.x.max(0.0).hypot(d_cyl.y.max(0.0)) + d_cyl.x.max(d_cyl.y).min(0.0)
            }
        }
        "capsule" => {
            let r = primitive.extra_params[0];
            let h = primitive.extra_params[1];
            let pa = p - Vector3::new(0.0, 0.0, -h);
            let ba = Vector3::new(0.0, 0.0, h * 2.0);
            let h_val = (pa.dot(&ba) / ba.dot(&ba)).clamp(0.0, 1.0);
            (pa - ba * h_val).norm() - r
        }
        "hex_prism" => {
            if edge_profile > 0 {
                let k_hex = Vector3::new(-0.8660254f32, 0.5f32, 0.57735027f32);
                let h_radius = primitive.extra_params[0] * 0.8660254f32;
                let rx = 0.8660254f32 * p.x - 0.5f32 * p.y;
                let ry = 0.5f32 * p.x + 0.8660254f32 * p.y;
                let mut pp = Vector3::new(rx.abs(), ry.abs(), p.z);
                let d_dot = (k_hex.x * pp.x + k_hex.y * pp.y).min(0.0);
                pp.x -= 2.0 * d_dot * k_hex.x;
                pp.y -= 2.0 * d_dot * k_hex.y;
                let clamped_px = pp.x.clamp(-k_hex.z * h_radius, k_hex.z * h_radius);
                let d_xy = (pp.x - clamped_px).hypot(pp.y - h_radius) * (pp.y - h_radius).signum();
                let d_slab = pp.z.abs() - primitive.extra_params[1];
                apply_primitive_edge(d_xy, d_slab, edge_profile, edge_k, edge_cs)
            } else {
                let h_radius = primitive.extra_params[0] * 0.8660254f32;
                let h_half_height = primitive.extra_params[1];
                let k = Vector3::new(-0.8660254f32, 0.5f32, 0.57735027f32);
                
                // Rotate 30 degrees to match Blender Cylinder(6)
                let (sx, cx) = (0.5f32, 0.8660254f32);
                let rx = cx * p.x - sx * p.y;
                let ry = sx * p.x + cx * p.y;
                
                let mut pp = Vector3::new(rx.abs(), ry.abs(), p.z);
                let dot_val = (k.x * pp.x + k.y * pp.y).min(0.0f32);
                pp.x -= 2.0f32 * dot_val * k.x;
                pp.y -= 2.0f32 * dot_val * k.y;
                let clamped_px = pp.x.clamp(-k.z * h_radius, k.z * h_radius);
                let d_hex = Vector2::new(
                    (pp.x - clamped_px).hypot(pp.y - h_radius) * (pp.y - h_radius).signum(),
                    pp.z.abs() - h_half_height
                );
                d_hex.x.max(0.0).hypot(d_hex.y.max(0.0)) + d_hex.x.max(d_hex.y).min(0.0)
            }
        }
        "pyramid" => {
            let s_param = primitive.extra_params[0].max(0.001f32);
            let h = primitive.extra_params[1] / s_param;
            let m2 = h*h + 0.25f32;
            let mut pp = Vector3::new((p.x / s_param).abs(), (p.y / s_param).abs(), p.z / s_param);
            if pp.y > pp.x {
                let tmp = pp.x; pp.x = pp.y; pp.y = tmp;
            }
            pp.x -= 0.5f32;
            pp.y -= 0.5f32;
            let q = Vector3::new(pp.y, h*pp.z - 0.5f32*pp.x, h*pp.x + 0.5f32*pp.z);
            let s_pyr = (-q.x).max(0.0f32);
            let t = ((q.y - 0.5f32*pp.y) / (m2 + 0.25f32)).clamp(0.0f32, 1.0f32);
            let a = m2 * (q.x + s_pyr).powi(2) + q.y.powi(2);
            let b = m2 * (q.x + 0.5f32*t).powi(2) + (q.y - m2*t).powi(2);
            let d2 = if q.y.min(-q.x*m2 - q.y*0.5f32) > 0.0f32 { 0.0f32 } else { a.min(b) };
            let d_pyr = ((d2 + q.z.powi(2)) / m2).sqrt() * q.z.max(-pp.z).signum();
            d_pyr * s_param
        }
        "capped_cone" => {
            let r1 = primitive.extra_params[0];
            let r2 = primitive.extra_params[1];
            let h = primitive.extra_params[2];
            let q_cone = Vector2::new(Vector2::new(p.x, p.y).norm(), p.z);
            let k1 = Vector2::new(r2, h);
            let k2 = Vector2::new(r2 - r1, 2.0 * h);
            let ca_x = q_cone.x - q_cone.x.min(if q_cone.y < 0.0 { r1 } else { r2 });
            let ca_y = q_cone.y.abs() - h;
            let cb = q_cone - k1 + k2 * ((k1 - q_cone).dot(&k2) / k2.dot(&k2)).clamp(0.0, 1.0);
            let s = if cb.x < 0.0 && ca_y < 0.0 { -1.0 } else { 1.0 };
            s * Vector2::new(ca_x, ca_y).norm().min(cb.norm())
        }
        "ngon_prism" => {
            if edge_profile > 0 {
                let r = primitive.extra_params[0];
                let n = primitive.extra_params[1];
                let an = 3.14159265 / n;
                let cosan = an.cos();
                let mut a = p.y.atan2(p.x) + an;
                a = (a / (2.0 * an)).floor() * (2.0 * an);
                let px = a.cos() * p.x + a.sin() * p.y;
                let d_xy = px - r * cosan;
                let d_slab = p.z.abs() - primitive.extra_params[2];
                apply_primitive_edge(d_xy, d_slab, edge_profile, edge_k, edge_cs)
            } else {
                let r = primitive.extra_params[0];
                let n = primitive.extra_params[1];
                let h = primitive.extra_params[2];
                let an = 3.14159265 / n;
                let cosan = an.cos();
                let mut a = p.y.atan2(p.x) + an;
                a = (a / (2.0 * an)).floor() * (2.0 * an);
                let px = a.cos() * p.x + a.sin() * p.y;
                let d_xy = px - r * cosan;
                let d_z = p.z.abs() - h;
                d_xy.max(0.0).hypot(d_z.max(0.0)) + d_xy.max(d_z).min(0.0)
            }
        }
        "ellipsoid" => {
            let er = Vector3::new(
                primitive.extra_params[0].max(0.001f32),
                primitive.extra_params[1].max(0.001f32),
                primitive.extra_params[2].max(0.001f32),
            );
            let k0 = Vector3::new(p.x / er.x, p.y / er.y, p.z / er.z).norm();
            let k1 = Vector3::new(p.x / (er.x * er.x), p.y / (er.y * er.y), p.z / (er.z * er.z)).norm();
            k0 * (k0 - 1.0) / k1.max(0.0001f32)
        }
        "rounded_cylinder" => {
            let ra = primitive.extra_params[0];
            let rb = primitive.extra_params[1];
            let h = primitive.extra_params[2];
            let d = Vector2::new(
                Vector2::new(p.x, p.y).norm() - ra + rb,
                p.z.abs() - h,
            );
            d.x.max(0.0).hypot(d.y.max(0.0)) + d.x.max(d.y).min(0.0) - rb
        }
        "capped_torus" => {
            let ra = primitive.extra_params[0];
            let rb = primitive.extra_params[1];
            let ang = primitive.extra_params[2];
            let sc = Vector2::new((ang * 0.5).sin(), (ang * 0.5).cos());
            let pp = Vector3::new(p.x, p.y.abs(), p.z);
            let k = if sc.y * pp.x > sc.x * pp.y {
                pp.x * sc.x + pp.y * sc.y
            } else {
                Vector2::new(pp.x, pp.y).norm()
            };
            (pp.dot(&pp) + ra * ra - 2.0 * ra * k).max(0.0).sqrt() - rb
        }
        "octahedron" => {
            let s_oct = primitive.extra_params[0];
            let pp = Vector3::new(p.x.abs(), p.y.abs(), p.z.abs());
            let m = pp.x + pp.y + pp.z - s_oct;
            let q = if 3.0 * pp.x < m {
                pp
            } else if 3.0 * pp.y < m {
                Vector3::new(pp.y, pp.z, pp.x)
            } else if 3.0 * pp.z < m {
                Vector3::new(pp.z, pp.x, pp.y)
            } else {
                return m * 0.57735027 * s_min;
            };
            let k = (0.5 * (q.z - q.y + s_oct)).clamp(0.0, s_oct);
            Vector3::new(q.x, q.y - s_oct + k, q.z - k).norm()
        }
        "cut_sphere" => {
            let h_cut = primitive.extra_params[0];
            let r_sph = primitive.radius;
            let w = (r_sph * r_sph - h_cut * h_cut).max(0.0).sqrt();
            let q = Vector2::new(Vector2::new(p.x, p.y).norm(), p.z);
            let s_cut = ((h_cut - r_sph) * q.x * q.x + w * w * (h_cut + r_sph - 2.0 * q.y))
                .max(h_cut * q.x - w * q.y);
            if s_cut < 0.0 {
                q.norm() - r_sph
            } else if q.x < w {
                h_cut - q.y
            } else {
                (q - Vector2::new(w, h_cut)).norm()
            }
        }
        "mesh" => {
            if let Some(bvh_ptr) = bvh {
                return bvh_ptr.get_closest_dist(local_p);
            } else {
                0.0
            }
        }
        _ => p.norm() - 1.0,
    };

    d * s_min
}

fn hash3_rust(p: Vector3<f32>) -> f32 {
    let x = (p.x * 0.1031).fract();
    let y = (p.y * 0.1031).fract();
    let z = (p.z * 0.1031).fract();
    let dot = x * (x + 33.33) + y * (z + 33.33) + z * (y + 33.33);
    ((x + y) * z + dot).fract()
}

fn noise3_rust(p: Vector3<f32>) -> f32 {
    let i = Vector3::new(p.x.floor(), p.y.floor(), p.z.floor());
    let f = Vector3::new(p.x.fract(), p.y.fract(), p.z.fract());
    let u = f.component_mul(&f).component_mul(&(Vector3::new(3.0, 3.0, 3.0) - 2.0 * f));
    
    let h000 = hash3_rust(i + Vector3::new(0.0, 0.0, 0.0));
    let h100 = hash3_rust(i + Vector3::new(1.0, 0.0, 0.0));
    let h010 = hash3_rust(i + Vector3::new(0.0, 1.0, 0.0));
    let h110 = hash3_rust(i + Vector3::new(1.0, 1.0, 0.0));
    let h001 = hash3_rust(i + Vector3::new(0.0, 0.0, 1.0));
    let h101 = hash3_rust(i + Vector3::new(1.0, 0.0, 1.0));
    let h011 = hash3_rust(i + Vector3::new(0.0, 1.0, 1.0));
    let h111 = hash3_rust(i + Vector3::new(1.0, 1.0, 1.0));

    let res = lerp(lerp(lerp(h000, h100, u.x), lerp(h010, h110, u.x), u.y),
                   lerp(lerp(h001, h101, u.x), lerp(h011, h111, u.x), u.y), u.z);
    res
}

fn lerp(a: f32, b: f32, t: f32) -> f32 { a + (b - a) * t }

fn get_scene_sdf_with_color(p: Vector3<f32>, primitives: &[SdfPrimitive], bvhs: &[Option<MeshBvh>], symmetry: u32) -> (f32, [f32; 3], f32, f32) {
    let mut d = std::f32::MAX;
    let mut color = [1.0, 1.0, 1.0];
    let mut metallic = 0.0;
    let mut roughness = 0.5;

    let mut p_sym = p;
    if (symmetry & 1) != 0 { p_sym.x = p_sym.x.abs(); }
    if (symmetry & 2) != 0 { p_sym.y = p_sym.y.abs(); }
    if (symmetry & 4) != 0 { p_sym.z = p_sym.z.abs(); }

    for (i, prim) in primitives.iter().enumerate() {
        let q = UnitQuaternion::from_quaternion(Quaternion::new(
            prim.rotation[3], prim.rotation[0], prim.rotation[1], prim.rotation[2]
        ));
        
        // Symmetry がオンの場合、プリミティブの中心も正の象限にあるものとして評価する
        let mut center_sym = Vector3::from(prim.center);
        if (symmetry & 1) != 0 { center_sym.x = center_sym.x.abs(); }
        if (symmetry & 2) != 0 { center_sym.y = center_sym.y.abs(); }
        if (symmetry & 4) != 0 { center_sym.z = center_sym.z.abs(); }

        let local_p_orig = q.inverse() * (p_sym - center_sym);
        let mut local_p = local_p_orig;

        // V12: Individual Placement (Layout Stacking)
        let mode_flags = prim.layout_data1[0] as u32;
        let mut accum_idx = 0.0;

        // 1. Mirror (Bit 0: 1)
        if (mode_flags & 1) != 0 {
            let mask = (mode_flags >> 8) & 0xF;
            let offset = prim.layout_data1[1];
            if (mask & 1) != 0 { local_p.x = local_p.x.abs() - offset; }
            if (mask & 2) != 0 { local_p.y = local_p.y.abs() - offset; }
            if (mask & 4) != 0 { local_p.z = local_p.z.abs() - offset; }
        }

        // 2. Patterns (Radial Bit 1: 2, Spiral Bit 2: 4)
        if (mode_flags & 2) != 0 || (mode_flags & 4) != 0 {
            let count = ((mode_flags >> 12) & 0xFF) as f32;
            let axis = (mode_flags >> 20) & 3;
            let angle = 2.0 * std::f32::consts::PI / count.max(1.0);
            let radius = prim.layout_data1[2]; 
            let spiral_h = prim.layout_data1[3];
            
            let (mut x, mut y) = match axis {
                0 => (local_p.y, local_p.z),
                1 => (local_p.x, local_p.z),
                _ => (local_p.x, local_p.y),
            };
            
            let a_raw = y.atan2(x) + angle * 0.5;
            let step = (a_raw / angle).floor();
            let a = step * angle;
            let (s, c) = a.sin_cos();
            let nx = c * x + s * y;
            let ny = -s * x + c * y;
            accum_idx += step;
            
            if (mode_flags & 4) != 0 { // Spiral
                let z_offset = step * spiral_h;
                match axis {
                    0 => { local_p.x -= z_offset; }
                    1 => { local_p.y -= z_offset; }
                    _ => { local_p.z -= z_offset; }
                }
            }
            
            match axis {
                0 => { local_p.y = nx - radius; local_p.z = ny; }
                1 => { local_p.x = nx - radius; local_p.z = ny; }
                _ => { local_p.x = nx - radius; local_p.y = ny; }
            }
        }

        // 3. Grid (Bit 3: 8)
        if (mode_flags & 8) != 0 {
            let g_p = prim.layout_data2[2];
            let cz = (g_p / 10000.0).floor(); let cy = ((g_p - cz * 10000.0) / 100.0).floor(); let cx = g_p - cz * 10000.0 - cy * 100.0;
            let g_counts = Vector3::new(cx, cy, cz);
            let g_spacing = Vector3::new(prim.layout_data2[3], prim.layout_data3[0], prim.layout_data3[1]);
            let g_idx = Vector3::new((local_p.x / g_spacing.x).round(), (local_p.y / g_spacing.y).round(), (local_p.z / g_spacing.z).round());
            let g_limit = (g_counts - Vector3::new(1.0, 1.0, 1.0)) * 0.5;
            let g_actual = Vector3::new(
                g_idx.x.clamp(-g_limit.x.floor(), g_limit.x.ceil()),
                g_idx.y.clamp(-g_limit.y.floor(), g_limit.y.ceil()),
                g_idx.z.clamp(-g_limit.z.floor(), g_limit.z.ceil()),
            );
            local_p -= g_spacing.component_mul(&g_actual);
            accum_idx += g_actual.x + g_actual.y + g_actual.z;
        }

        // 4. Jitter (Bit 5: 32)
        if (mode_flags & 32) != 0 {
            let seed = prim.layout_data2[0];
            let strength = prim.layout_data2[1];
            let h = hash3_rust(local_p + Vector3::new(seed, seed, seed));
            local_p.x += (h - 0.5) * strength;
            local_p.y += (hash3_rust(local_p + Vector3::new(seed+1.0, seed+1.0, seed+1.0)) - 0.5) * strength;
            local_p.z += (hash3_rust(local_p + Vector3::new(seed+2.0, seed+2.0, seed+2.0)) - 0.5) * strength;
        }

        // 4. Step Rotation Apply (After Layout)
        let i_rot = Vector3::new(prim.layout_data3[2], prim.layout_data3[3], prim.layout_data4[0]);
        let s_rot = Vector3::new(prim.layout_data4[1], prim.layout_data4[2], prim.layout_data4[3]);
        let rot_euler = i_rot + s_rot * accum_idx;
        let q_step = UnitQuaternion::from_euler_angles(rot_euler.x, rot_euler.y, rot_euler.z);
        
        local_p = q_step.inverse() * local_p;

        // --- V15: Dynamic Deform Stack ---
        let packed_meta = prim.deform_data1[0] as u32;
        let mut df_bound_scale = 1.0_f32;
        
        // スロットパラメータを配列として読み込み
        let slot_params: [[f32; 4]; 4] = [
            [prim.deform_data1[1], prim.deform_data1[2], prim.deform_data1[3], prim.deform_data2[0]],
            [prim.deform_data2[1], prim.deform_data2[2], prim.deform_data2[3], prim.deform_data3[0]],
            [prim.deform_data3[1], prim.deform_data3[2], prim.deform_data3[3], prim.deform_data4[0]],
            [prim.deform_data4[1], prim.deform_data4[2], prim.deform_data4[3], 0.0],
        ];

        for si in 0..4u32 {
            let slot_info = (packed_meta >> (si * 6)) & 0x3F;
            let d_type = slot_info & 0xF;
            let d_axis = (slot_info >> 4) & 0x3;
            let sd = slot_params[si as usize];
            
            if d_type == 0 { continue; }
            
            if d_type == 1 {  // Elongate
                local_p = local_p - Vector3::new(
                    local_p.x.clamp(-sd[0], sd[0]),
                    local_p.y.clamp(-sd[1], sd[1]),
                    local_p.z.clamp(-sd[2], sd[2]),
                );
            }
            else if d_type == 2 {  // Bend
                let angle = sd[0];
                let ox = sd[1]; let oy = sd[2]; let oz = sd[3];
                if angle.abs() > 0.0001 {
                    let r_c = 1.0 / angle;
                    let sign_r = r_c.signum();
                    if d_axis == 2 {
                        let dx = local_p.x - ox; let dy = local_p.y - oy;
                        let radial_y = r_c - dy;
                        let theta = (dx * sign_r).atan2(radial_y * sign_r);
                        let r = radial_y.hypot(dx) * sign_r;
                        local_p.y = oy + r_c - r; local_p.x = ox + (theta / angle);
                    } else if d_axis == 1 {
                        let dz = local_p.z - oz; let dx = local_p.x - ox;
                        let radial_x = r_c - dx;
                        let theta = (dz * sign_r).atan2(radial_x * sign_r);
                        let r = radial_x.hypot(dz) * sign_r;
                        local_p.x = ox + r_c - r; local_p.z = oz + (theta / angle);
                    } else { // d_axis == 0 (X)
                        let dz = local_p.z - oz; let dy = local_p.y - oy;
                        let radial_y = r_c - dy;
                        let theta = (dz * sign_r).atan2(radial_y * sign_r);
                        let r = radial_y.hypot(dz) * sign_r;
                        local_p.y = oy + r_c - r; local_p.z = oz + (theta / angle);
                    }
                    let max_s = prim.size[0].max(prim.size[1]).max(prim.size[2]);
                    df_bound_scale *= 1.0_f32 / (1.0_f32 + (max_s * angle) * (max_s * angle)).sqrt();
                }
            }
            else if d_type == 3 {  // Twist
                let angle = sd[0];
                let ox = sd[1]; let oy = sd[2]; let oz = sd[3];
                if d_axis == 2 {
                    let a = angle * (local_p.z - oz);
                    let c = a.cos(); let s = a.sin();
                    let dx = local_p.x - ox; let dy = local_p.y - oy;
                    local_p.x = ox + c * dx - s * dy;
                    local_p.y = oy + s * dx + c * dy;
                } else if d_axis == 1 {
                    let a = angle * (local_p.y - oy);
                    let c = a.cos(); let s = a.sin();
                    let dx = local_p.x - ox; let dz = local_p.z - oz;
                    local_p.x = ox + c * dx - s * dz;
                    local_p.z = oz + s * dx + c * dz;
                } else if d_axis == 0 {
                    let a = angle * (local_p.x - ox);
                    let c = a.cos(); let s = a.sin();
                    let dy = local_p.y - oy; let dz = local_p.z - oz;
                    local_p.y = oy + c * dy - s * dz;
                    local_p.z = oz + s * dy + c * dz;
                }
                let max_s = prim.size[0].max(prim.size[1]).max(prim.size[2]);
                df_bound_scale *= 1.0_f32 / (1.0_f32 + (max_s * angle) * (max_s * angle)).sqrt();
            }
            else if d_type == 4 {  // Taper
                let factor = sd[0];
                let ox = sd[1]; let oy = sd[2]; let oz = sd[3];
                let mut scale = 1.0_f32;
                if d_axis == 2 {
                    scale = (1.0 + factor * (local_p.z - oz)).max(0.1);
                    local_p.x = ox + (local_p.x - ox) / scale;
                    local_p.y = oy + (local_p.y - oy) / scale;
                } else if d_axis == 1 {
                    scale = (1.0 + factor * (local_p.y - oy)).max(0.1);
                    local_p.x = ox + (local_p.x - ox) / scale;
                    local_p.z = oz + (local_p.z - oz) / scale;
                } else if d_axis == 0 {
                    scale = (1.0 + factor * (local_p.x - ox)).max(0.1);
                    local_p.y = oy + (local_p.y - oy) / scale;
                    local_p.z = oz + (local_p.z - oz) / scale;
                }
                df_bound_scale *= 1.0_f32.min(scale);
            }
        }

        let mut d_prim = calculate_primitive_sdf(local_p, prim, &bvhs[i]);
        d_prim *= df_bound_scale;

        // Shell（中空化）: GPU側 (common.wgsl) と同期
        if prim.shell_thickness > 0.0 {
            d_prim = d_prim.abs() - prim.shell_thickness;
        }

        if prim.noise_strength > 0.0 {
            d_prim += noise3_rust(local_p * prim.noise_scale) * prim.noise_strength;
        }

        if i == 0 {
            if prim.operation == 0 { d = d_prim; } else { d = 1e10; }
            color = prim.color;
            metallic = prim.metallic;
            roughness = prim.roughness;
        } else {
            let k = prim.smoothness.max(0.0001);
            let h: f32;
            let profile = prim.blend_profile;
            let cs = prim.chamfer_smooth;
            match prim.operation {
                0 => { // Smooth Union
                    h = (0.5 + 0.5 * (d - d_prim) / k).clamp(0.0, 1.0);
                    d = apply_profile_union_cpu(d, d_prim, profile, k, cs);
                    color = [
                        lerp(color[0], prim.color[0], h),
                        lerp(color[1], prim.color[1], h),
                        lerp(color[2], prim.color[2], h),
                    ];
                    metallic = lerp(metallic, prim.metallic, h);
                    roughness = lerp(roughness, prim.roughness, h);
                }
                1 => { // Smooth Subtract
                    h = (0.5 + 0.5 * (d + d_prim) / k).clamp(0.0, 1.0);
                    d = apply_profile_sub_cpu(d, d_prim, profile, k, cs);
                    color = [
                        lerp(prim.color[0], color[0], h),
                        lerp(prim.color[1], color[1], h),
                        lerp(prim.color[2], color[2], h),
                    ];
                    metallic = lerp(prim.metallic, metallic, h);
                    roughness = lerp(prim.roughness, roughness, h);
                }
                2 => { // Smooth Intersect
                    h = (0.5 + 0.5 * (d_prim - d) / k).clamp(0.0, 1.0);
                    d = apply_profile_int_cpu(d, d_prim, profile, k, cs);
                    color = [
                        lerp(color[0], prim.color[0], h),
                        lerp(color[1], prim.color[1], h),
                        lerp(color[2], prim.color[2], h),
                    ];
                    metallic = lerp(metallic, prim.metallic, h);
                    roughness = lerp(roughness, prim.roughness, h);
                }
                _ => {
                    h = 0.0;
                }
            }
        }
    }
    (d, color, metallic, roughness)
}

fn get_scene_gradient(p: Vector3<f32>, primitives: &[SdfPrimitive], bvhs: &[Option<MeshBvh>], symmetry: u32) -> Vector3<f32> {
    let eps = 0.001;
    let dx = Vector3::new(eps, 0.0, 0.0);
    let dy = Vector3::new(0.0, eps, 0.0);
    let dz = Vector3::new(0.0, 0.0, eps);
    
    let gx = get_scene_sdf_with_color(p + dx, primitives, bvhs, symmetry).0 - get_scene_sdf_with_color(p - dx, primitives, bvhs, symmetry).0;
    let gy = get_scene_sdf_with_color(p + dy, primitives, bvhs, symmetry).0 - get_scene_sdf_with_color(p - dy, primitives, bvhs, symmetry).0;
    let gz = get_scene_sdf_with_color(p + dz, primitives, bvhs, symmetry).0 - get_scene_sdf_with_color(p - dz, primitives, bvhs, symmetry).0;
    
    Vector3::new(gx, gy, gz) / (2.0 * eps)
}

#[derive(Clone)]
struct Triangle {
    v0: Vector3<f32>,
    v1: Vector3<f32>,
    v2: Vector3<f32>,
    normal: Vector3<f32>,
    center: Vector3<f32>,
}

#[derive(Clone)]
struct BvhNode {
    min: Vector3<f32>,
    max: Vector3<f32>,
    left: i32,  // -1 if leaf
    right: i32, // tri index if leaf, or right child index
}

struct MeshBvh {
    nodes: Vec<BvhNode>,
    triangles: Vec<Triangle>,
}

impl MeshBvh {
    fn new(vertices: &[f32], indices: &[u32]) -> Self {
        let mut triangles = Vec::new();
        for i in (0..indices.len()).step_by(3) {
            let v0 = Vector3::new(vertices[indices[i] as usize * 3], vertices[indices[i] as usize * 3 + 1], vertices[indices[i] as usize * 3 + 2]);
            let v1 = Vector3::new(vertices[indices[i+1] as usize * 3], vertices[indices[i+1] as usize * 3 + 1], vertices[indices[i+1] as usize * 3 + 2]);
            let v2 = Vector3::new(vertices[indices[i+2] as usize * 3], vertices[indices[i+2] as usize * 3 + 1], vertices[indices[i+2] as usize * 3 + 2]);
            let normal = (v1 - v0).cross(&(v2 - v0)).normalize();
            let center = (v0 + v1 + v2) / 3.0;
            triangles.push(Triangle { v0, v1, v2, normal, center });
        }

        let mut nodes = Vec::new();
        if !triangles.is_empty() {
            Self::build_recursive(&mut nodes, &triangles, &(0..triangles.len()).collect::<Vec<_>>());
        }

        Self { nodes, triangles }
    }

    fn build_recursive(nodes: &mut Vec<BvhNode>, all_tris: &[Triangle], current_indices: &[usize]) -> usize {
        let mut min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
        let mut max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
        for &idx in current_indices {
            let t = &all_tris[idx];
            min = min.inf(&t.v0.inf(&t.v1.inf(&t.v2)));
            max = max.sup(&t.v0.sup(&t.v1.sup(&t.v2)));
        }

        let node_idx = nodes.len();
        nodes.push(BvhNode { min, max, left: -1, right: -1 });

        if current_indices.len() <= 1 {
            nodes[node_idx].right = current_indices[0] as i32;
        } else {
            // 最も広がっている軸で分割
            let extent = max - min;
            let axis = if extent.x > extent.y && extent.x > extent.z { 0 } else if extent.y > extent.z { 1 } else { 2 };
            
            let mut sorted_indices = current_indices.to_vec();
            sorted_indices.sort_by(|&a, &b| all_tris[a].center[axis].partial_cmp(&all_tris[b].center[axis]).unwrap());
            
            let mid = sorted_indices.len() / 2;
            let left = Self::build_recursive(nodes, all_tris, &sorted_indices[..mid]);
            let right = Self::build_recursive(nodes, all_tris, &sorted_indices[mid..]);
            
            nodes[node_idx].left = left as i32;
            nodes[node_idx].right = right as i32;
        }
        node_idx
    }

    fn get_closest_dist(&self, p: Vector3<f32>) -> f32 {
        if self.nodes.is_empty() { return f32::MAX; }
        let mut min_dist_sq = f32::MAX;
        let mut closest_tri_idx = 0;
        self.query_recursive(0, p, &mut min_dist_sq, &mut closest_tri_idx);
        
        let tri = &self.triangles[closest_tri_idx];
        let d = dist_to_triangle(p, tri.v0, tri.v1, tri.v2);
        
        // 符号判定: 最近接三角形の法線とのドット積
        let to_p = p - (tri.v0 + tri.v1 + tri.v2) / 3.0;
        if tri.normal.dot(&to_p) < 0.0 { -d } else { d }
    }

    fn query_recursive(&self, node_idx: usize, p: Vector3<f32>, min_dist_sq: &mut f32, closest_tri_idx: &mut usize) {
        let node = &self.nodes[node_idx];
        
        // AABBへの最短距離を確認
        let dx = (node.min.x - p.x).max(0.0).max(p.x - node.max.x);
        let dy = (node.min.y - p.y).max(0.0).max(p.y - node.max.y);
        let dz = (node.min.z - p.z).max(0.0).max(p.z - node.max.z);
        let d_aabb_sq = dx*dx + dy*dy + dz*dz;
        
        if d_aabb_sq > *min_dist_sq { return; }

        if node.left == -1 {
            let tri_idx = node.right as usize;
            let tri = &self.triangles[tri_idx];
            // 正確な距離計算（二乗で比較して重い計算を避ける）
            // 簡易的に中心点への距離で枝刈り（理想的には三角形との最短距離の二乗が必要だが重いので近似）
            let d_tri_sq = (tri.center - p).norm_squared(); 
            if d_tri_sq < *min_dist_sq {
                *min_dist_sq = d_tri_sq;
                *closest_tri_idx = tri_idx;
            }
        } else {
            self.query_recursive(node.left as usize, p, min_dist_sq, closest_tri_idx);
            self.query_recursive(node.right as usize, p, min_dist_sq, closest_tri_idx);
        }
    }
}

// --- Blend Profile 関数群 (GPU側 common.wgsl / sdf.rs と同期) ---
fn apply_profile_union_cpu(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 1 { let h = (k - (d1 - d2).abs()).max(0.0) / k; d1.min(d2) - h * h * h * k * 0.166666 }
    else if profile == 2 { -k * ((-d1 / k).exp2() + (-d2 / k).exp2()).max(1e-10).log2() }
    else if profile == 3 { let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); lerp(d2, d1, h) - k * h * h * (1.0 - h) * (1.0 - h) * 2.0 }
    else if profile == 4 {
        let plane = (d1 + d2 - k) * 0.70710678;
        let m = d1.min(d2);
        if cs > 0.0 { let h = (0.5 + 0.5 * (m - plane) / cs).clamp(0.0, 1.0); lerp(m, plane, h) - cs * h * (1.0 - h) }
        else { m.min(plane) }
    } else {
        let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); lerp(d2, d1, h) - k * h * (1.0 - h)
    }
}
fn apply_profile_sub_cpu(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 1 { let h = (k - (d1 + d2).abs()).max(0.0) / k; d1.max(-d2) + h * h * h * k * 0.166666 }
    else if profile == 2 { k * ((d1 / k).exp2() + (-d2 / k).exp2()).max(1e-10).log2() }
    else if profile == 3 { let h = (0.5 + 0.5 * (-d2 - d1) / k).clamp(0.0, 1.0); lerp(-d2, d1, h) + k * h * h * (1.0 - h) * (1.0 - h) * 2.0 }
    else if profile == 4 {
        let plane = (d1 - d2 + k) * 0.70710678;
        let m = d1.max(-d2);
        if cs > 0.0 { let h = (0.5 + 0.5 * (plane - m) / cs).clamp(0.0, 1.0); lerp(m, plane, h) + cs * h * (1.0 - h) }
        else { m.max(plane) }
    } else {
        let h = (0.5 + 0.5 * (d1 + d2) / k).clamp(0.0, 1.0); lerp(-d2, d1, h) + k * h * (1.0 - h)
    }
}
fn apply_profile_int_cpu(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 1 { let h = (k - (d1 - d2).abs()).max(0.0) / k; d1.max(d2) + h * h * h * k * 0.166666 }
    else if profile == 2 { k * ((d1 / k).exp2() + (d2 / k).exp2()).max(1e-10).log2() }
    else if profile == 3 { let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); lerp(d1, d2, h) + k * h * h * (1.0 - h) * (1.0 - h) * 2.0 }
    else if profile == 4 {
        let plane = (d1 + d2 + k) * 0.70710678;
        let m = d1.max(d2);
        if cs > 0.0 { let h = (0.5 + 0.5 * (plane - m) / cs).clamp(0.0, 1.0); lerp(m, plane, h) + cs * h * (1.0 - h) }
        else { m.max(plane) }
    } else {
        let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); lerp(d1, d2, h) + k * h * (1.0 - h)
    }
}

// プリミティブエッジ（面取り）用の軽量版関数
fn apply_primitive_edge(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 4 { // Chamfer
        let plane = (d1 + d2 + k) * 0.70710678;
        let m = d1.max(d2);
        if cs > 0.0 { let h = (0.5 + 0.5 * (plane - m) / cs).clamp(0.0, 1.0); lerp(m, plane, h) + cs * h * (1.0 - h) }
        else { m.max(plane) }
    } else { // Fallback to Round
        let h = (k - (d1 - d2).abs()).max(0.0) / k; 
        d1.max(d2) + h * h * h * k * 0.166666
    }
}


#[pyfunction]
fn calculate_sdf_at_point(p: [f32; 3], primitive: &SdfPrimitive) -> PyResult<f32> {
    let p_vec = Vector3::from(p);
    let q = UnitQuaternion::from_quaternion(Quaternion::new(
        primitive.rotation[3], primitive.rotation[0], primitive.rotation[1], primitive.rotation[2]
    ));
    let local_p = q.inverse() * (p_vec - Vector3::from(primitive.center));
    
    let bvh = if primitive.shape_type == "mesh" {
        if let (Some(verts), Some(indices)) = (&primitive.vertices, &primitive.indices) {
            Some(MeshBvh::new(verts, indices))
        } else { None }
    } else { None };

    Ok(calculate_primitive_sdf(local_p, primitive, &bvh))
}

use rayon::prelude::*;

/// 頂点統合 (Weld / Merge by Distance)
fn weld_mesh(vertices: Vec<f32>, indices: Vec<u32>, threshold: f32) -> (Vec<f32>, Vec<u32>) {
    if vertices.is_empty() { return (vertices, indices); }
    
    let mut new_indices = Vec::new();
    let mut vertex_map = HashMap::new(); 
    
    // 頂点データの蓄積用: (座標の合計, 法線の合計, カウント, その他の属性)
    struct WeldData {
        sum_pos: Vector3<f32>,
        sum_normal: Vector3<f32>,
        count: usize,
        other_attr: [f32; 5], // color(3), metallic, roughness
    }
    let mut unique_verts_data: Vec<WeldData> = Vec::new();
    
    let inv_threshold = 1.0 / threshold.max(1e-9);
    
    for i in (0..indices.len()).step_by(3) {
        if i + 2 >= indices.len() { break; }
        
        let mut tri_new = [0u32; 3];
        let mut tri_valid = true;
        
        for j in 0..3 {
            let old_idx = indices[i + j];
            let v_base = old_idx as usize * 11;
            if v_base + 10 >= vertices.len() {
                tri_valid = false;
                break;
            }
            
            let p = Vector3::new(vertices[v_base], vertices[v_base+1], vertices[v_base+2]);
            let n = Vector3::new(vertices[v_base+8], vertices[v_base+9], vertices[v_base+10]);
            
            // 座標をグリッド化してキーにする
            let key = [
                (p.x * inv_threshold).round() as i32,
                (p.y * inv_threshold).round() as i32,
                (p.z * inv_threshold).round() as i32,
            ];
            
            let new_v_idx = if let Some(&idx) = vertex_map.get(&key) {
                idx
            } else {
                let idx = unique_verts_data.len() as u32;
                unique_verts_data.push(WeldData {
                    sum_pos: Vector3::new(0.0, 0.0, 0.0),
                    sum_normal: Vector3::new(0.0, 0.0, 0.0),
                    count: 0,
                    other_attr: [
                        vertices[v_base+3], vertices[v_base+4], vertices[v_base+5], // color
                        vertices[v_base+6], vertices[v_base+7]                     // met, rough
                    ],
                });
                vertex_map.insert(key, idx);
                idx
            };
            
            tri_new[j] = new_v_idx;
            
            // データを蓄積
            let data = &mut unique_verts_data[new_v_idx as usize];
            data.sum_pos += p;
            data.sum_normal += n;
            data.count += 1;
        }
        
        if tri_valid {
            // 縮退ポリゴン（面積がゼロになる面）を除去
            if tri_new[0] != tri_new[1] && tri_new[1] != tri_new[2] && tri_new[2] != tri_new[0] {
                new_indices.extend_from_slice(&tri_new);
            }
        }
    }
    
    // 蓄積されたデータから最終的な頂点リストを構築（平均化と正規化）
    let mut final_vertices = Vec::with_capacity(unique_verts_data.len() * 11);
    for data in unique_verts_data {
        let c = data.count as f32;
        let avg_p = data.sum_pos / c;
        // 法線は平均化してから再正規化することで、滑らかな面を実現
        let avg_n = if data.sum_normal.norm_squared() > 1e-6 {
            data.sum_normal.normalize()
        } else {
            Vector3::new(0.0, 0.0, 1.0)
        };
        
        final_vertices.push(avg_p.x);
        final_vertices.push(avg_p.y);
        final_vertices.push(avg_p.z);
        final_vertices.extend_from_slice(&data.other_attr);
        final_vertices.push(avg_n.x);
        final_vertices.push(avg_n.y);
        final_vertices.push(avg_n.z);
    }
    
    (final_vertices, new_indices)
}

// パニック時でも確実にフラグをリセットするためのガード (V13.3 安定化)
struct UpdatingGuard;
impl Drop for UpdatingGuard {
    fn drop(&mut self) {
        IS_UPDATING.store(false, Ordering::SeqCst);
    }
}

#[pyfunction]
#[pyo3(signature = (primitives, res, size, use_dc=false, symmetry=0, weld_threshold=0.0))]
fn request_mesh_update(primitives: Vec<SdfPrimitive>, res: usize, size: f32, use_dc: bool, symmetry: u32, weld_threshold: f32) -> PyResult<bool> {
    if IS_UPDATING.load(Ordering::SeqCst) {
        return Ok(false); // 既に更新中
    }

    IS_UPDATING.store(true, Ordering::SeqCst);
    
    std::thread::spawn(move || {
        let _guard = UpdatingGuard; // スコープを抜けるときに必ず false に戻す
        
        // GPU計算の実行
        let result = generate_sdf_mesh_internal(primitives, res, size, use_dc, symmetry, weld_threshold);
        
        if let Ok(data) = result {
            // Poisoned Mutex の回避
            let mut res_lock = match MESH_RESULT.lock() {
                Ok(lock) => lock,
                Err(poisoned) => poisoned.into_inner(),
            };
            *res_lock = Some(data);
        }
    });

    Ok(true)
}

#[pyfunction]
fn fetch_mesh_if_ready() -> PyResult<Option<(Vec<f32>, Vec<u32>)>> {
    let mut res_lock = match MESH_RESULT.lock() {
        Ok(lock) => lock,
        Err(poisoned) => poisoned.into_inner(),
    };
    if let Some(data) = res_lock.take() {
        return Ok(Some(data));
    }
    Ok(None)
}

#[pyfunction]
fn is_updating() -> bool {
    IS_UPDATING.load(Ordering::SeqCst)
}

// 内部用計算関数 (既存の generate_sdf_mesh をリネーム)
fn generate_sdf_mesh_internal(primitives: Vec<SdfPrimitive>, res: usize, size: f32, use_dc: bool, symmetry: u32, weld_threshold: f32) -> PyResult<(Vec<f32>, Vec<u32>)> {
    let start_time = Instant::now();
    println!("Rust Debug: Starting SDF generation. Layers: {}, Resolution: {}^3", primitives.len(), res);

    // BVHの事前構築
    let mesh_bvhs: Vec<Option<MeshBvh>> = primitives.iter().map(|p| {
        if p.shape_type == "mesh" {
            if let (Some(verts), Some(indices)) = (&p.vertices, &p.indices) {
                return Some(MeshBvh::new(verts, indices));
            }
        }
        None
    }).collect();

    let half_res = res as f32 / 2.0;
    let step = size / res as f32;
    let grid_size = res + 1;

    // --- メッシュデータ蓄積バッファ ---
    let mut all_tri_data: Vec<(Vec<f32>, Vec<u32>)> = Vec::new();

    // --- GPU Path ---
    let gpu_lock = GPU_CONTEXT.lock().unwrap();
    let can_use_gpu = gpu_lock.is_some() && !primitives.iter().any(|p| p.shape_type == "mesh");
    if can_use_gpu {
        let gpu_ctx = gpu_lock.as_ref().unwrap();
        let gpu_prims: Vec<gpu::GpuPrimitive> = primitives.iter().map(|p| {
            convert_to_gpu_prim(p)
        }).collect();

        // GPU-BVHの構築
        let mut prim_aabbs = Vec::new();
        for prim in &primitives {
            let center = Vector3::from(prim.center);
            let q = UnitQuaternion::from_quaternion(Quaternion::new(
                prim.rotation[3], prim.rotation[0], prim.rotation[1], prim.rotation[2]
            ));
            
            // --- 1. Base Shape AABB (Local Space) ---
            let mut local_factor = Vector3::new(1.0f32, 1.0f32, 1.0f32);
            match prim.shape_type.as_str() {
                "sphere" => {
                    local_factor = Vector3::new(prim.radius, prim.radius, prim.radius);
                }
                "torus" => {
                    let r_max = prim.extra_params[0] + prim.extra_params[1];
                    local_factor = Vector3::new(r_max, r_max, prim.extra_params[1]);
                }
                "cylinder" | "hex_prism" => {
                    local_factor = Vector3::new(prim.extra_params[0], prim.extra_params[0], prim.extra_params[1]);
                }
                "capsule" => {
                    let r = prim.extra_params[0];
                    let h = prim.extra_params[1];
                    local_factor = Vector3::new(r, r, h + r);
                }
                "pyramid" => {
                    let s_pyr = prim.extra_params[0];
                    let h = prim.extra_params[1];
                    local_factor = Vector3::new(s_pyr, s_pyr, h);
                }
                "capped_cone" => {
                    let r_max = prim.extra_params[0].max(prim.extra_params[1]);
                    local_factor = Vector3::new(r_max, r_max, prim.extra_params[2]);
                }
                "ngon_prism" => {
                    local_factor = Vector3::new(prim.extra_params[0], prim.extra_params[0], prim.extra_params[2]);
                }
                "ellipsoid" => {
                    local_factor = Vector3::new(prim.extra_params[0], prim.extra_params[1], prim.extra_params[2]);
                }
                "rounded_cylinder" => {
                    let ra = prim.extra_params[0];
                    let rb = prim.extra_params[1];
                    let h = prim.extra_params[2];
                    local_factor = Vector3::new(ra, ra, h + rb);
                }
                "capped_torus" => {
                    let r_max = prim.extra_params[0] + prim.extra_params[1];
                    local_factor = Vector3::new(r_max, r_max, r_max);
                }
                "octahedron" => {
                    let s_oct = prim.extra_params[0];
                    local_factor = Vector3::new(s_oct, s_oct, s_oct);
                }
                "cut_sphere" => {
                    let r = prim.radius;
                    local_factor = Vector3::new(r, r, r);
                }
                _ => {}
            }
            
            local_factor.x = local_factor.x.max(0.01f32);
            local_factor.y = local_factor.y.max(0.01f32);
            local_factor.z = local_factor.z.max(0.01f32);

            let half_ext = Vector3::new(
                prim.size[0] * local_factor.x,
                prim.size[1] * local_factor.y,
                prim.size[2] * local_factor.z,
            );
            let mut aabb_min = -half_ext;
            let mut aabb_max = half_ext;
            
            // Extra padding for smoothness, noise, shell thickness, and edge profile size
            let extra_pad = prim.smoothness + prim.noise_strength + prim.shell_thickness + prim.edge_profile_size;
            aabb_min -= Vector3::new(extra_pad, extra_pad, extra_pad);
            aabb_max += Vector3::new(extra_pad, extra_pad, extra_pad);
            
            let max_s = half_ext.x.max(half_ext.y).max(half_ext.z);

            // --- 2. Deform Stack AABB Expansion (Pre-Rotation/Layout) ---
            let packed_meta = prim.deform_data1[0] as u32;
            let slot_params: [[f32; 4]; 4] = [
                [prim.deform_data1[1], prim.deform_data1[2], prim.deform_data1[3], prim.deform_data2[0]],
                [prim.deform_data2[1], prim.deform_data2[2], prim.deform_data2[3], prim.deform_data3[0]],
                [prim.deform_data3[1], prim.deform_data3[2], prim.deform_data3[3], prim.deform_data4[0]],
                [prim.deform_data4[1], prim.deform_data4[2], prim.deform_data4[3], 0.0],
            ];

            for si in 0..4u32 {
                let slot_info = (packed_meta >> (si * 6)) & 0x3F;
                let d_type = slot_info & 0xF;
                let sd = slot_params[si as usize];
                if d_type == 0 { continue; }

                if d_type == 1 { // Elongate
                    let h = Vector3::new(sd[0].abs(), sd[1].abs(), sd[2].abs());
                    aabb_min -= h; aabb_max += h;
                } else if d_type == 2 { // Bend
                    let angle = sd[0];
                    if angle.abs() > 0.0001 {
                        let r_bend = (1.0 / angle).abs();
                        // Bend can move things by radius
                        aabb_min -= Vector3::new(r_bend, r_bend, r_bend);
                        aabb_max += Vector3::new(r_bend, r_bend, r_bend);
                    }
                } else if d_type == 4 { // Taper
                    let factor = sd[0];
                    if factor > 0.0 {
                        let scale = 1.0 + factor * max_s * 2.0;
                        aabb_min *= scale.max(1.0); aabb_max *= scale.max(1.0);
                    }
                }
            }

            // --- 3. Local Rotation ---
            let rot_aabb = rotate_aabb(aabb_min, aabb_max, q);
            aabb_min = rot_aabb.0; aabb_max = rot_aabb.1;

            // --- 4. Layout Stacking AABB Expansion ---
            let packed1 = prim.layout_data1[0] as u32;
            let flags = packed1 & 0xFF;

            // 4.1 Mirror (Shift both sides)
            if (flags & 1) != 0 {
                let mask = (packed1 >> 8) & 0xF;
                let m_offset = prim.layout_data1[1].abs();
                let mut m_min = aabb_min; let mut m_max = aabb_max;
                
                if (mask & 1) != 0 {
                    // Positive side shift
                    aabb_min.x += m_offset; aabb_max.x += m_offset;
                    // Negative side
                    m_min.x = -(aabb_max.x); m_max.x = -(aabb_min.x);
                    aabb_min = aabb_min.inf(&m_min); aabb_max = aabb_max.sup(&m_max);
                }
                if (mask & 2) != 0 {
                    aabb_min.y += m_offset; aabb_max.y += m_offset;
                    m_min.y = -(aabb_max.y); m_max.y = -(aabb_min.y);
                    aabb_min = aabb_min.inf(&m_min); aabb_max = aabb_max.sup(&m_max);
                }
                if (mask & 4) != 0 {
                    aabb_min.z += m_offset; aabb_max.z += m_offset;
                    m_min.z = -(aabb_max.z); m_max.z = -(aabb_min.z);
                    aabb_min = aabb_min.inf(&m_min); aabb_max = aabb_max.sup(&m_max);
                }
            }

            // 4.2 Radial / Spiral
            if (flags & 2) != 0 || (flags & 4) != 0 {
                let count = ((packed1 >> 12) & 0xFF) as f32;
                let radius = prim.layout_data1[2].abs();
                let pitch = prim.layout_data1[3].abs();
                let current_max = aabb_max.x.abs().max(aabb_min.x.abs()).max(aabb_max.y.abs()).max(aabb_min.y.abs());
                let r_total = current_max + radius;
                let spiral_total = pitch * count.max(1.0);
                let rad_extent = Vector3::new(r_total, r_total, aabb_max.z.max(aabb_min.z) + spiral_total);
                aabb_min = aabb_min.inf(&-rad_extent); aabb_max = aabb_max.sup(&rad_extent);
            }

            // 4.3 Grid
            if (flags & 8) != 0 {
                let g_p = prim.layout_data2[2];
                let cz = (g_p / 10000.0).floor(); let cy = ((g_p - cz * 10000.0) / 100.0).floor(); let cx = g_p - cz * 10000.0 - cy * 100.0;
                let sp = Vector3::new(prim.layout_data2[3].abs(), prim.layout_data3[0].abs(), prim.layout_data3[1].abs());
                let range = Vector3::new((cx-1.0)*0.5*sp.x, (cy-1.0)*0.5*sp.y, (cz-1.0)*0.5*sp.z);
                aabb_min -= range; aabb_max += range;
            }

            // --- 5. World Move & Global Symmetry ---
            aabb_min += center; aabb_max += center;
            
            // Add a final safety margin (10% of size or at least 0.2 units)
            let margin = (aabb_max - aabb_min) * 0.1;
            let safety = Vector3::new(margin.x.max(0.2), margin.y.max(0.2), margin.z.max(0.2));
            aabb_min -= safety; aabb_max += safety;

            if (symmetry & 1) != 0 {
                let x_max = aabb_min.x.abs().max(aabb_max.x.abs());
                aabb_min.x = 0.0; aabb_max.x = x_max;
            }
            if (symmetry & 2) != 0 {
                let y_max = aabb_min.y.abs().max(aabb_max.y.abs());
                aabb_min.y = 0.0; aabb_max.y = y_max;
            }
            if (symmetry & 4) != 0 {
                let z_max = aabb_min.z.abs().max(aabb_max.z.abs());
                aabb_min.z = 0.0; aabb_max.z = z_max;
            }

            prim_aabbs.push((aabb_min, aabb_max));
        }

        let mut bvh_nodes = Vec::new();
        if !gpu_prims.is_empty() {
            build_gpu_bvh_recursive(&mut bvh_nodes, &prim_aabbs, &(0..gpu_prims.len()).collect::<Vec<_>>());
        }

        let config = GpuConfig {
            res: res as u32,
            domain_size: size,
            num_primitives: gpu_prims.len() as u32,
            symmetry,
            hash_table_size: 2097152,
            block_size: 8,
            max_tris: 0,
            _pad: 0,
        };

        let (v, i) = if use_dc {
            futures::executor::block_on(gpu_ctx.generate_mesh_gpu_dc(&gpu_prims, &bvh_nodes, config))
        } else {
            futures::executor::block_on(gpu_ctx.generate_mesh_gpu(&gpu_prims, &bvh_nodes, config))
        };
        
        let (v_w, i_w) = if weld_threshold > 0.0 {
            let v_w_old_len = v.len() / 11;
            let res_weld = weld_mesh(v, i, weld_threshold);
            println!("Rust Debug: Weld Applied. Threshold: {}, Verts: {} -> {}", weld_threshold, v_w_old_len, res_weld.0.len() / 11);
            res_weld
        } else { (v, i) };

        gpu_ctx.swap_buffers();
        return Ok((v_w, i_w));
    } else {
        println!("Rust Debug: GPU Path skipped (can_use_gpu: false).");
    }

    // --- CPU Path ---
    if all_tri_data.is_empty() {
        if use_dc {
            println!("Rust Debug: [PATH] CPU Dual Contouring");
            let dc_mesh = dc::DualContouring::generate(
                res,
                size,
                |p| get_scene_sdf_with_color(p, &primitives, &mesh_bvhs, symmetry),
                |p| get_scene_gradient(p, &primitives, &mesh_bvhs, symmetry)
            );
            all_tri_data.push((dc_mesh.vertices, dc_mesh.indices));
        } else {
            // CPU Fallback (Parallelized MC)
            println!("Rust Debug: [PATH] CPU Marching Cubes");
            let mut grid = vec![0.0; grid_size * grid_size * grid_size];
            
            grid.par_chunks_mut(grid_size * grid_size).enumerate().for_each(|(x, chunk)| {
                for y in 0..grid_size {
                    for z in 0..grid_size {
                        let p = Vector3::new(
                            (x as f32 - half_res) * step,
                            (y as f32 - half_res) * step,
                            (z as f32 - half_res) * step
                        );
                        chunk[y * grid_size + z] = get_scene_sdf_with_color(p, &primitives, &mesh_bvhs, symmetry).0;
                    }
                }
            });

            let edges = [(0, 1), (1, 2), (2, 3), (3, 0), (4, 5), (5, 6), (6, 7), (7, 4), (0, 4), (1, 5), (2, 6), (3, 7)];
            let vertex_offsets = [[0,0,0],[1,0,0],[1,1,0],[0,1,0],[0,0,1],[1,0,1],[1,1,1],[0,1,1]];

            let mc_data: Vec<(Vec<f32>, Vec<u32>)> = (0..res).into_par_iter().map(|x| {
                let mut local_verts = Vec::new();
                let mut local_faces = Vec::new();
                for y in 0..res {
                    for z in 0..res {
                        let mut cube_index = 0;
                        let mut values = [0.0; 8];
                        let mut positions = [[0.0; 3]; 8];
                        for i in 0..8 {
                            let ix = x + vertex_offsets[i][0];
                            let iy = y + vertex_offsets[i][1];
                            let iz = z + vertex_offsets[i][2];
                            values[i] = grid[ix * grid_size * grid_size + iy * grid_size + iz];
                            positions[i] = [(ix as f32 - half_res) * step, (iy as f32 - half_res) * step, (iz as f32 - half_res) * step];
                            if values[i] <= 0.0 { cube_index |= 1 << i; }
                        }
                        if cube_index == 0 || cube_index == 255 { continue; }
                        let tris = get_triangles(cube_index as usize);
                        let mut edge_verts = [[0.0; 11]; 12];
                        for i in 0..12 {
                            let (v1, v2) = edges[i];
                            let (val1, val2) = (values[v1], values[v2]);
                            let (p1, p2) = (positions[v1], positions[v2]);
                            let t = if (val2 - val1).abs() < 1e-6 { 0.5 } else { -val1 / (val2 - val1) };
                            let mut p = Vector3::new(p1[0] + t*(p2[0]-p1[0]), p1[1] + t*(p2[1]-p1[1]), p1[2] + t*(p2[2]-p1[2]));
                            
                            // Newton
                            for _ in 0..2 {
                                let d = get_scene_sdf_with_color(p, &primitives, &mesh_bvhs, symmetry).0;
                                let grad = get_scene_gradient(p, &primitives, &mesh_bvhs, symmetry);
                                let gnsq = grad.norm_squared();
                                if gnsq > 1e-6 { p -= grad * (d / gnsq); }
                            }
                            let (_, col, met, rou) = get_scene_sdf_with_color(p, &primitives, &mesh_bvhs, symmetry);
                            let grad = get_scene_gradient(p, &primitives, &mesh_bvhs, symmetry);
                            // 安全な正規化と向きの反転（内向きを外向きに）
                            let normal = -grad.try_normalize(1e-6).unwrap_or(Vector3::new(0.0, 1.0, 0.0));
                            edge_verts[i] = [p.x, p.y, p.z, col[0], col[1], col[2], met, rou, normal.x, normal.y, normal.z];
                        }
                        for i in (0..tris.len()).step_by(3) {
                            for j in 0..3 {
                                let edge_idx = tris[i + j] as usize;
                                local_faces.push((local_verts.len() / 11) as u32);
                                local_verts.extend_from_slice(&edge_verts[edge_idx]);
                            }
                        }
                    }
                }
                (local_verts, local_faces)
            }).collect();
            all_tri_data.extend(mc_data);
        }
    }

    // --- 最終アセンブリと頂点統合 (Weld) ---
    let mut final_verts = Vec::new();
    let mut final_indices = Vec::new();
    let mut v_offset = 0;
    for (v, i) in all_tri_data {
        let count = (v.len() / 11) as u32;
        final_verts.extend(v);
        for idx in i {
            final_indices.push(idx + v_offset);
        }
        v_offset += count;
    }

    if weld_threshold > 0.0 && !final_verts.is_empty() {
        let step = size / res as f32;
        let actual_threshold = step * weld_threshold;
        let input_v_count = final_verts.len() / 11;
        
        let (wv, wi) = weld_mesh(final_verts, final_indices, actual_threshold);
        
        let output_v_count = wv.len() / 11;
        println!("Rust Debug: Weld Applied. Threshold: {:.6}, Verts: {} -> {}", 
            actual_threshold, input_v_count, output_v_count);
            
        final_verts = wv;
        final_indices = wi;
    } else if weld_threshold <= 0.0 {
        // println!("Rust Debug: Weld skipped (threshold is 0).");
    }

    // 最終的なインデックス数が3の倍数であることを保証する (V13.3 安定化)
    let valid_len = (final_indices.len() / 3) * 3;
    if final_indices.len() != valid_len {
        println!("Rust Warning: final_indices.len() was {}, truncating to {}.", final_indices.len(), valid_len);
        final_indices.truncate(valid_len);
    }
    
    let elapsed = start_time.elapsed().as_millis();
    println!("Rust Debug: SDF Mesh generation complete in {} ms. Verts: {}, Faces: {}", 
        elapsed, final_verts.len() / 11, final_indices.len() / 3);
        
    Ok((final_verts, final_indices))
}

#[pyfunction]
#[pyo3(signature = (cache_path=None, compile_dc=None))]
fn init_gpu(py: Python<'_>, cache_path: Option<String>, compile_dc: Option<bool>) -> PyResult<bool> {
    let mut ctx_lock = GPU_CONTEXT.lock().unwrap();
    if ctx_lock.is_some() {
        return Ok(true);
    }

    let compile_dc_val = compile_dc.unwrap_or(false);

    let cache_data = if let Some(path) = &cache_path {
        match std::fs::read(path) {
            Ok(data) => {
                println!("Rust Debug: Loading shader cache from '{}' ({} bytes)", path, data.len());
                Some(data)
            },
            Err(_) => {
                println!("Rust Debug: No shader cache found at '{}'. Initial compilation required.", path);
                None
            }
        }
    } else {
        None
    };

    // GILを解放して初期化（コンパイル）を実行
    let result = py.allow_threads(|| {
        let table = gpu_table_gen::get_marching_cubes_table();
        pollster::block_on(SdfGpuContext::new(&table, cache_data, compile_dc_val))
    });

    if let Some((new_ctx, new_cache)) = result {
        if let (Some(path), Some(data)) = (cache_path, new_cache) {
            if let Some(parent) = std::path::Path::new(&path).parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            if let Ok(_) = std::fs::write(&path, &data) {
                println!("Rust Debug: Shader cache saved to '{}' ({} bytes)", path, data.len());
            }
        }
        *ctx_lock = Some(new_ctx);
        Ok(true)
    } else {
        Ok(false)
    }
}

#[pyfunction]
fn is_gpu_available() -> bool {
    GPU_CONTEXT.lock().unwrap().is_some()
}

#[pymodule]
fn rust_gpu_sdf(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SdfPrimitive>()?;
    m.add_function(wrap_pyfunction!(calculate_sdf_at_point, m)?)?;
    m.add_function(wrap_pyfunction!(request_mesh_update, m)?)?;
    m.add_function(wrap_pyfunction!(fetch_mesh_if_ready, m)?)?;
    m.add_function(wrap_pyfunction!(is_updating, m)?)?;
    m.add_function(wrap_pyfunction!(init_gpu, m)?)?;
    m.add_function(wrap_pyfunction!(is_gpu_available, m)?)?;
    Ok(())
}
fn convert_to_gpu_prim(p: &SdfPrimitive) -> gpu::GpuPrimitive {
    let shape_type = match p.shape_type.as_str() {
        "sphere" => 0,
        "box" => 1,
        "rounded_box" => 4,
        "torus" => 2,
        "cylinder" => 3,
        "capsule" => 5,
        "hex_prism" => 6,
        "pyramid" => 7,
        "capped_cone" => 8,
        "ngon_prism" => 9,
        "ellipsoid" => 10,
        "rounded_cylinder" => 11,
        "capped_torus" => 12,
        "octahedron" => 13,
        "cut_sphere" => 14,
        _ => 0,
    };
    gpu::GpuPrimitive {
        center_and_shape: [p.center[0], p.center[1], p.center[2], shape_type as f32],
        rotation: p.rotation,
        size_and_op: [p.size[0], p.size[1], p.size[2], p.operation as f32],
        params: [p.radius, p.smoothness, p.metallic, p.roughness],
        noise_params: [p.noise_strength, p.noise_scale, p.color[0], p.color[1]],
        color_b_and_extra: [p.color[2], p.blend_profile as f32, p.chamfer_smooth, 0.0],
        layout_data1: p.layout_data1,
        layout_data2: p.layout_data2,
        layout_data3: p.layout_data3,
        layout_data4: p.layout_data4,
        extra_params: p.extra_params,
        deform_data1: p.deform_data1,
        deform_data2: p.deform_data2,
        deform_data3: p.deform_data3,
        deform_data4: p.deform_data4,
        modifier_params: [p.edge_profile as f32, p.shell_thickness, p.edge_chamfer_smooth, p.edge_profile_size],
    }
}

fn build_gpu_bvh_recursive(nodes: &mut Vec<GpuBvhNode>, aabbs: &[(Vector3<f32>, Vector3<f32>)], indices: &[usize]) -> usize {
    let mut min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
    let mut max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
    for &idx in indices {
        min = min.inf(&aabbs[idx].0);
        max = max.sup(&aabbs[idx].1);
    }

    let node_idx = nodes.len();
    nodes.push(GpuBvhNode { min: [0.0; 4], max: [0.0; 4] });

    if indices.len() <= 1 {
        nodes[node_idx].min = [min.x, min.y, min.z, indices[0] as f32];
        nodes[node_idx].max = [max.x, max.y, max.z, 1.0]; // Leaf count = 1 (positive)
    } else {
        let extent = max - min;
        let axis = if extent.x > extent.y && extent.x > extent.z { 0 } else if extent.y > extent.z { 1 } else { 2 };
        let mut sorted = indices.to_vec();
        sorted.sort_by(|&a, &b| {
            let center_a = (aabbs[a].0[axis] + aabbs[a].1[axis]) * 0.5;
            let center_b = (aabbs[b].0[axis] + aabbs[b].1[axis]) * 0.5;
            center_a.partial_cmp(&center_b).unwrap()
        });
        let mid = sorted.len() / 2;
        let left = build_gpu_bvh_recursive(nodes, aabbs, &sorted[..mid]);
        let right = build_gpu_bvh_recursive(nodes, aabbs, &sorted[mid..]);
        nodes[node_idx].min = [min.x, min.y, min.z, left as f32];
        nodes[node_idx].max = [max.x, max.y, max.z, -(right as f32)]; // Inner node: -right_idx (negative)
    }
    node_idx
}
