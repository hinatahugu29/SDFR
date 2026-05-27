// V15.9.6.2 Optimized Marching Cubes Pass (Direct Indexing + local subcell recovery)
// Headers provided by common.wgsl

fn emit_mc_cell(cell_min: vec3<f32>, cell_step: f32, b_ptr_u: u32) -> bool {
    var vals: array<f32, 8>;
    var cube_idx = 0u;
    for (var i = 0u; i < 8u; i++) {
        vals[i] = get_scene_dist_indexed(cell_min + CORNERS[i] * cell_step, b_ptr_u);
        if (vals[i] <= 0.0) {
            cube_idx |= (1u << i);
        }
    }
    if (cube_idx == 0u || cube_idx == 255u) { return false; }

    if (atomicLoad(&counters[0]) + 1u >= config.max_tris) { return true; }
    for (var i = 0u; mc_table[cube_idx * 16u + i] != -1; i += 3u) {
        let tri_idx = atomicAdd(&counters[0], 1u);
        if (tri_idx >= config.max_tris) { return true; }

        for (var j = 0u; j < 3u; j++) {
            let edge_idx = u32(mc_table[cube_idx * 16u + i + j]);
            let e1 = array<u32,12>(0,1,2,3,4,5,6,7,0,1,2,3)[edge_idx];
            let e2 = array<u32,12>(1,2,3,0,5,6,7,4,4,5,6,7)[edge_idx];
            let v1_val = vals[e1];
            let v2_val = vals[e2];
            let t = clamp(v1_val / (v1_val - v2_val + 1e-10), 0.0, 1.0);
            var p_tri = cell_min + mix(CORNERS[e1], CORNERS[e2], t) * cell_step;

            let res_v = get_scene_sdf_indexed(p_tri, b_ptr_u);
            var normal = get_scene_normal(p_tri, b_ptr_u);

            if (config.res <= 512u && abs(res_v.d) > 0.001) {
                p_tri -= normal * res_v.d * 0.5;
            }

            let off = tri_idx * 33u + j * 11u;
            vertices[off+0]=p_tri.x; vertices[off+1]=p_tri.y; vertices[off+2]=p_tri.z;
            vertices[off+3]=res_v.color.x; vertices[off+4]=res_v.color.y; vertices[off+5]=res_v.color.z;
            vertices[off+6]=res_v.metallic; vertices[off+7]=res_v.roughness;
            vertices[off+8]=normal.x; vertices[off+9]=normal.y; vertices[off+10]=normal.z;
            indices[tri_idx * 3u + j] = tri_idx * 3u + j;
        }
    }

    return true;
}

fn should_refine_empty_cell(cell_min: vec3<f32>, cell_step: f32, b_ptr_u: u32, parent_inside: bool) -> bool {
    var min_abs = abs(get_scene_dist_indexed(cell_min + CORNERS[0] * cell_step, b_ptr_u));
    for (var i = 1u; i < 8u; i++) {
        let v = abs(get_scene_dist_indexed(cell_min + CORNERS[i] * cell_step, b_ptr_u));
        min_abs = min(min_abs, v);
    }

    let center_val = get_scene_dist_indexed(cell_min + vec3<f32>(0.5) * cell_step, b_ptr_u);
    var refine = ((center_val <= 0.0) != parent_inside) || abs(center_val) < cell_step * 1.25 || min_abs < cell_step * 2.0;

    if (!refine && min_abs < cell_step * 3.5) {
        let probes = array<vec3<f32>, 6>(
            vec3<f32>(0.5, 0.0, 0.5),
            vec3<f32>(0.5, 1.0, 0.5),
            vec3<f32>(0.0, 0.5, 0.5),
            vec3<f32>(1.0, 0.5, 0.5),
            vec3<f32>(0.5, 0.5, 0.0),
            vec3<f32>(0.5, 0.5, 1.0)
        );

        for (var i = 0u; i < 6u; i++) {
            let probe_val = get_scene_dist_indexed(cell_min + probes[i] * cell_step, b_ptr_u);
            if (((probe_val <= 0.0) != parent_inside) || abs(probe_val) < cell_step * 1.25) {
                refine = true;
                break;
            }
        }
    }

    return refine;
}

@compute @workgroup_size(8, 8, 4)
fn main(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    let b_ptr_u = wid.y * 65535u + wid.x;
    let active_count = atomicLoad(&counters[3]);

    if (b_ptr_u >= active_count) { return; }

    let packed = active_blocks[b_ptr_u];
    let block_coord = vec3<i32>(i32(packed & 0x7FFu), i32((packed >> 11u) & 0x7FFu), i32((packed >> 22u) & 0x3FFu));

    let res = config.res;
    let step = config.domain_size / f32(res);

    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let lid_z = lid.z + z_off;
        let id = vec3<u32>(vec3<i32>(block_coord * 8)) + vec3<u32>(lid.x, lid.y, lid_z);

        if (id.x >= res || id.y >= res || id.z >= res) { continue; }

        let p_min = (vec3<f32>(id) - f32(res)/2.0) * step;
        var vals: array<f32, 8>;
        var cube_idx = 0u;

        for (var i = 0u; i < 8u; i++) {
            vals[i] = get_scene_dist_indexed(p_min + CORNERS[i] * step, b_ptr_u);
            if (vals[i] <= 0.0) { cube_idx |= (1u << i); }
        }

        if (cube_idx == 0u || cube_idx == 255u) {
            let parent_inside = cube_idx == 255u;
            if (should_refine_empty_cell(p_min, step, b_ptr_u, parent_inside)) {
                let half_step = step * 0.5;
                var emitted = false;

                for (var sx = 0u; sx < 2u; sx++) {
                    for (var sy = 0u; sy < 2u; sy++) {
                        for (var sz = 0u; sz < 2u; sz++) {
                            let child_min = p_min + vec3<f32>(f32(sx), f32(sy), f32(sz)) * half_step;
                            if (emit_mc_cell(child_min, half_step, b_ptr_u)) {
                                emitted = true;
                            }
                        }
                    }
                }

                if (!emitted) {
                    atomicAdd(&counters[5], 1u);
                }
            } else {
                atomicAdd(&counters[5], 1u);
            }
            continue;
        }

        if (!emit_mc_cell(p_min, step, b_ptr_u)) {
            atomicAdd(&counters[5], 1u);
        }
    }
}
