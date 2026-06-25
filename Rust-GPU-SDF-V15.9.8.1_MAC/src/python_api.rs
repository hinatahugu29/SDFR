use pyo3::prelude::*;
use crate::primitive::SdfPrimitive;
use crate::sdf::{calculate_sdf_at_point as calc_sdf_impl};
use crate::mesh::weld_mesh;
use once_cell::sync::Lazy;
use std::sync::Mutex;
use std::sync::atomic::{AtomicBool, Ordering};
use std::time::Instant;

static GPU_CONTEXT: Mutex<Option<SdfGpuContext>> = Mutex::new(None);

// V10.3: 非同期ステート管理
static MESH_RESULT: Lazy<Mutex<Option<(Vec<f32>, Vec<u32>)>>> = Lazy::new(|| Mutex::new(None));
static IS_UPDATING: AtomicBool = AtomicBool::new(false);

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
            let mut max_s = prim.size[0].max(prim.size[1]).max(prim.size[2]);
            let mut aabb_min = Vector3::new(-prim.size[0], -prim.size[1], -prim.size[2]);
            let mut aabb_max = Vector3::new(prim.size[0], prim.size[1], prim.size[2]);
            
            // Extra parameters (Radius, etc.)
            let extra_pad = prim.radius + prim.smoothness + prim.noise_strength + prim.shell_thickness + prim.edge_profile_size;
            aabb_min -= Vector3::new(extra_pad, extra_pad, extra_pad);
            aabb_max += Vector3::new(extra_pad, extra_pad, extra_pad);

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
