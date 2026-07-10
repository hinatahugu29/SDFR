use nalgebra::{Vector2, Vector3, Quaternion, UnitQuaternion};
use crate::primitive::SdfPrimitive;
use crate::bvh::MeshBvh;
use crate::math::lerp;
use crate::noise::{hash3_rust, noise3_rust};

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

fn calculate_primitive_sdf(local_p: Vector3<f32>, primitive: &SdfPrimitive, bvh: &Option<MeshBvh>) -> f32 {
    let abs_s = Vector3::new(
        primitive.size[0].abs().max(0.001f32),
        primitive.size[1].abs().max(0.001f32),
        primitive.size[2].abs().max(0.001f32)
    );
    // 符号を復元
    let s_signed = Vector3::new(
        abs_s.x * if primitive.size[0] < 0.0 { -1.0 } else { 1.0 },
        abs_s.y * if primitive.size[1] < 0.0 { -1.0 } else { 1.0 },
        abs_s.z * if primitive.size[2] < 0.0 { -1.0 } else { 1.0 }
    );
    // 空間をスケールで割る
    let p = Vector3::new(local_p.x / s_signed.x, local_p.y / s_signed.y, local_p.z / s_signed.z);
    let s_min = abs_s.x.min(abs_s.y).min(abs_s.z);

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

fn apply_profile_union(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 1 { let h = (k - (d1 - d2).abs()).max(0.0) / k; d1.min(d2) - h * h * h * k * 0.166666 }
    else if profile == 2 { -k * ((-d1 / k).exp2() + (-d2 / k).exp2()).max(1e-10).log2() }
    else if profile == 3 { let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); crate::math::lerp(d2, d1, h) - k * h * h * (1.0 - h) * (1.0 - h) * 2.0 }
    else if profile == 4 {
        let ch = d1.min(d2).min((d1 + d2 - k) * 0.70710678);
        if cs > 0.0 { let h = (0.5 + 0.5 * (ch - d1.min(d2)) / cs).clamp(0.0, 1.0); crate::math::lerp(ch, d1.min(d2), h) - cs * h * (1.0 - h) }
        else { ch }
    } else {
        let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); crate::math::lerp(d2, d1, h) - k * h * (1.0 - h)
    }
}
fn apply_profile_sub(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 1 { let h = (k - (d1 + d2).abs()).max(0.0) / k; d1.max(-d2) + h * h * h * k * 0.166666 }
    else if profile == 2 { k * ((d1 / k).exp2() + (-d2 / k).exp2()).max(1e-10).log2() }
    else if profile == 3 { let h = (0.5 + 0.5 * (-d2 - d1) / k).clamp(0.0, 1.0); crate::math::lerp(-d2, d1, h) + k * h * h * (1.0 - h) * (1.0 - h) * 2.0 }
    else if profile == 4 {
        let ch = d1.max(-d2).max((d1 - d2 + k) * 0.70710678);
        if cs > 0.0 { let h = (0.5 + 0.5 * (ch - d1.max(-d2)) / cs).clamp(0.0, 1.0); crate::math::lerp(ch, d1.max(-d2), 1.0 - h) + cs * h * (1.0 - h) }
        else { ch }
    } else {
        let h = (0.5 + 0.5 * (d1 + d2) / k).clamp(0.0, 1.0); crate::math::lerp(-d2, d1, h) + k * h * (1.0 - h)
    }
}
fn apply_profile_int(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    if profile == 1 { let h = (k - (d1 - d2).abs()).max(0.0) / k; d1.max(d2) + h * h * h * k * 0.166666 }
    else if profile == 2 { k * ((d1 / k).exp2() + (d2 / k).exp2()).max(1e-10).log2() }
    else if profile == 3 { let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); crate::math::lerp(d1, d2, h) + k * h * h * (1.0 - h) * (1.0 - h) * 2.0 }
    else if profile == 4 {
        let ch = d1.max(d2).max((d1 + d2 + k) * 0.70710678);
        if cs > 0.0 { let h = (0.5 + 0.5 * (ch - d1.max(d2)) / cs).clamp(0.0, 1.0); crate::math::lerp(ch, d1.max(d2), 1.0 - h) + cs * h * (1.0 - h) }
        else { ch }
    } else {
        let h = (0.5 + 0.5 * (d2 - d1) / k).clamp(0.0, 1.0); crate::math::lerp(d1, d2, h) + k * h * (1.0 - h)
    }
}

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
                1 => (local_p.z, local_p.x),
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
                1 => { local_p.z = nx - radius; local_p.x = ny; }
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
                    let max_s = prim.size[0].abs().max(prim.size[1].abs()).max(prim.size[2].abs());
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
                let max_s = prim.size[0].abs().max(prim.size[1].abs()).max(prim.size[2].abs());
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
            match prim.operation {
                0 => { // Smooth Union
                    h = (0.5 + 0.5 * (d - d_prim) / k).clamp(0.0, 1.0);
                    d = apply_profile_union(d, d_prim, prim.blend_profile, k, prim.chamfer_smooth);
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
                    d = apply_profile_sub(d, d_prim, prim.blend_profile, k, prim.chamfer_smooth);
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
                    d = apply_profile_int(d, d_prim, prim.blend_profile, k, prim.chamfer_smooth);
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

#[pyfunction]
