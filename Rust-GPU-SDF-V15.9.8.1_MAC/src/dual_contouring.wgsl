// V15.5 Dual Contouring Main Pass (Bitmask Culling)



fn spatial_hash(p: vec3<i32>) -> u32 {
    let h = u32(p.x) * 73856093u ^ u32(p.y) * 19349663u ^ u32(p.z) * 83492791u;
    return h % config.hash_table_size;
}

fn get_block_ptr(p: vec3<i32>) -> i32 {
    let key = i32((u32(p.x) & 0x7FFu) | ((u32(p.y) & 0x7FFu) << 11u) | ((u32(p.z) & 0x3FFu) << 22u));
    var h = u32(key) % config.hash_table_size;
    for (var i = 0u; i < 32u; i = i + 1u) {
        if (hash_keys[h] == key) { return i32(atomicLoad(&hash_values[h])); }
        h = (h + 1u) % config.hash_table_size;
    }
    return -1;
}

var<workgroup> wg_b_ptr: i32;

@compute @workgroup_size(8, 8, 4)
fn vertex_pass(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    if (lid.x == 0u && lid.y == 0u && lid.z == 0u) {
        let block_list_idx = wid.y * 65535u + wid.x;
        let active_count = atomicLoad(&counters[3]);
        if (block_list_idx < active_count) {
            let packed = active_blocks[block_list_idx];
            let block_coord = vec3<i32>(i32(packed & 0x7FFu), i32((packed >> 11u) & 0x7FFu), i32((packed >> 22u) & 0x3FFu));
            wg_b_ptr = get_block_ptr(block_coord);
        } else { wg_b_ptr = -1; }
    }
    workgroupBarrier();
    let b_ptr = wg_b_ptr; if (b_ptr < 0) { return; }
    let b_ptr_u = u32(b_ptr);
    
    let block_list_idx_sync = wid.y * 65535u + wid.x;
    let packed_val = active_blocks[block_list_idx_sync];
    let block_coord = vec3<i32>(i32(packed_val & 0x7FFu), i32((packed_val >> 11u) & 0x7FFu), i32((packed_val >> 22u) & 0x3FFu));
    let clear_base = u32(b_ptr) * 1024u; let tid = lid.x + lid.y * 8u + lid.z * 64u;
    block_data[clear_base + tid] = 0u; block_data[clear_base + tid + 256u] = 0u;
    block_data[clear_base + tid + 512u] = 0u; block_data[clear_base + tid + 768u] = 0u;
    storageBarrier();
    let res = config.res; let step = config.domain_size / f32(res);
    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let local_id = vec3<u32>(lid.x, lid.y, lid.z + z_off);
        let id = vec3<u32>(block_coord * 8) + local_id;
        if (any(id >= vec3<u32>(res))) { continue; }
        let p_min = (vec3<f32>(id) - f32(res)/2.0) * step;
        var vals: array<f32, 8>; var cube_idx = 0u;
        for (var i = 0u; i < 8u; i++) {
            vals[i] = get_scene_dist_indexed(p_min + CORNERS[i] * step, b_ptr_u);
            if (vals[i] <= 0.0) { cube_idx |= (1u << i); }
        }
        if (cube_idx == 0u || cube_idx == 255u) { continue; }
        var ATA_0 = 0.0; var ATA_1 = 0.0; var ATA_2 = 0.0;
        var ATA_3 = 0.0; var ATA_4 = 0.0; var ATA_5 = 0.0;
        var ATB = vec3<f32>(0.0);
        var avg_p = vec3<f32>(0.0);
        var count = 0.0;
        
        let edges = array<vec2<u32>, 12>(vec2<u32>(0,1), vec2<u32>(1,2), vec2<u32>(2,3), vec2<u32>(3,0), vec2<u32>(4,5), vec2<u32>(5,6), vec2<u32>(6,7), vec2<u32>(7,4), vec2<u32>(0,4), vec2<u32>(1,5), vec2<u32>(2,6), vec2<u32>(3,7));
        for (var i = 0u; i < 12u; i++) {
            let v1 = edges[i].x; let v2 = edges[i].y;
            if ((vals[v1] <= 0.0) != (vals[v2] <= 0.0)) {
                let t = clamp(vals[v1] / (vals[v1] - vals[v2] + 1e-10), 0.0, 1.0);
                let p = p_min + mix(CORNERS[v1], CORNERS[v2], t) * step;
                let n = get_scene_normal(p, b_ptr_u);
                
                ATA_0 += n.x * n.x; ATA_1 += n.x * n.y; ATA_2 += n.x * n.z;
                ATA_3 += n.y * n.y; ATA_4 += n.y * n.z; ATA_5 += n.z * n.z;
                let b = dot(n, p);
                ATB += n * b;
                avg_p += p; count += 1.0;
            }
        }
        
        // 正則化 (Regularization)
        let weight = 1e-4;
        ATA_0 += weight; ATA_3 += weight; ATA_5 += weight;
        ATB += (avg_p / max(count, 1.0)) * weight;
        
        if (count > 0.0) {
            let det = ATA_0 * (ATA_3 * ATA_5 - ATA_4 * ATA_4) - ATA_1 * (ATA_1 * ATA_5 - ATA_2 * ATA_4) + ATA_2 * (ATA_1 * ATA_4 - ATA_2 * ATA_3);
            var pos = avg_p / count;
            
            if (abs(det) > 1e-6) {
                let inv_det = 1.0 / det;
                let m0 = (ATA_3 * ATA_5 - ATA_4 * ATA_4) * inv_det;
                let m1 = (ATA_2 * ATA_4 - ATA_1 * ATA_5) * inv_det;
                let m2 = (ATA_1 * ATA_4 - ATA_2 * ATA_3) * inv_det;
                let m3 = (ATA_0 * ATA_5 - ATA_2 * ATA_2) * inv_det;
                let m4 = (ATA_1 * ATA_2 - ATA_0 * ATA_4) * inv_det;
                let m5 = (ATA_0 * ATA_3 - ATA_1 * ATA_1) * inv_det;
                
                let qef_x = m0 * ATB.x + m1 * ATB.y + m2 * ATB.z;
                let qef_y = m1 * ATB.x + m3 * ATB.y + m4 * ATB.z;
                let qef_z = m2 * ATB.x + m4 * ATB.y + m5 * ATB.z;
                
                // Clamp to cell to prevent artifacts
                pos = clamp(vec3<f32>(qef_x, qef_y, qef_z), p_min, p_min + step);
            }
            
            // Surface snap iteration (Safe)
            let n_snap = get_scene_normal(pos, b_ptr_u);
            let d_snap = get_scene_dist_indexed(pos, b_ptr_u);
            pos -= n_snap * d_snap * 0.5; // 0.9 -> 0.5 (More stable)
            let v_idx = atomicAdd(&counters[0], 1u);
            let b_idx = local_id.x | (local_id.y << 3u) | (local_id.z << 6u);
            block_data[u32(b_ptr) * 1024u + b_idx] = v_idx + 1u;
            let res_v = get_scene_sdf_indexed(pos, b_ptr_u); let normal = get_scene_normal(pos, b_ptr_u);
            let base = v_idx * 11u;
            vertices[base+0]=pos.x; vertices[base+1]=pos.y; vertices[base+2]=pos.z;
            vertices[base+3]=res_v.color.x; vertices[base+4]=res_v.color.y; vertices[base+5]=res_v.color.z;
            vertices[base+6]=res_v.metallic; vertices[base+7]=res_v.roughness;
            vertices[base+8]=normal.x; vertices[base+9]=normal.y; vertices[base+10]=normal.z;
        }
    }
}

@compute @workgroup_size(8, 8, 4)
fn face_pass(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    let block_list_idx = wid.y * 65535u + wid.x;
    let active_count = atomicLoad(&counters[3]);
    if (block_list_idx >= active_count) { return; }
    let packed = active_blocks[block_list_idx];
    let block_coord = vec3<i32>(i32(packed & 0x7FFu), i32((packed >> 11u) & 0x7FFu), i32((packed >> 22u) & 0x3FFu));
    let b_ptr_main = get_block_ptr(block_coord);
    if (b_ptr_main < 0) { return; }
    let b_ptr_u = u32(b_ptr_main);

    let res = config.res; let step = config.domain_size / f32(res);
    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let local_id = vec3<u32>(lid.x, lid.y, lid.z + z_off);
        let id = vec3<u32>(block_coord * 8) + local_id;
        if (any(id >= vec3<u32>(res - 1u))) { continue; }
        for (var axis = 0u; axis < 3u; axis++) {
            let p1 = (vec3<f32>(id) - f32(res)/2.0) * step; var p2_off = vec3<f32>(0, 0, 0);
            if (axis == 0u) { p2_off.x = 1.0; } else if (axis == 1u) { p2_off.y = 1.0; } else { p2_off.z = 1.0; }
            if ((get_scene_dist_indexed(p1, b_ptr_u) <= 0.0) != (get_scene_dist_indexed(p1 + p2_off * step, b_ptr_u) <= 0.0)) {
                var v_indices: array<u32, 4>; var valid = true;
                for (var i = 0u; i < 4u; i++) {
                    var q = vec3<i32>(id);
                    if (axis == 0u) { q.y -= i32(i & 1u); q.z -= i32((i >> 1u) & 1u); }
                    else if (axis == 1u) { q.x -= i32(i & 1u); q.z -= i32((i >> 1u) & 1u); }
                    else { q.x -= i32(i & 1u); q.y -= i32((i >> 1u) & 1u); }
                    if (any(q < vec3<i32>(0))) { valid = false; break; }
                    let b_ptr_q = get_block_ptr(q / 8);
                    if (b_ptr_q < 0) { valid = false; break; }
                    let v_val = block_data[u32(b_ptr_q) * 1024u + (u32(q.x % 8) | (u32(q.y % 8) << 3u) | (u32(q.z % 8) << 6u))];
                    if (v_val == 0u) { valid = false; break; }
                    v_indices[i] = v_val - 1u;
                }
                if (valid) {
                    let base = atomicAdd(&counters[1], 6u);
                    if (get_scene_dist_indexed(p1, b_ptr_u) <= 0.0) {
                        indices[base+0]=v_indices[0]; indices[base+1]=v_indices[1]; indices[base+2]=v_indices[2];
                        indices[base+3]=v_indices[1]; indices[base+4]=v_indices[3]; indices[base+5]=v_indices[2];
                    } else {
                        indices[base+0]=v_indices[0]; indices[base+1]=v_indices[2]; indices[base+2]=v_indices[1];
                        indices[base+3]=v_indices[1]; indices[base+4]=v_indices[2]; indices[base+5]=v_indices[3];
                    }
                }
            }
        }
    }
}
