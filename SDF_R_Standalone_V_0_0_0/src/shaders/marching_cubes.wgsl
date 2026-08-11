// V15.5 Marching Cubes Main Pass (Bitmask Culling)

const CORNERS = array<vec3<f32>, 8>(
    vec3<f32>(0,0,0), vec3<f32>(1,0,0), vec3<f32>(1,1,0), vec3<f32>(0,1,0),
    vec3<f32>(0,0,1), vec3<f32>(1,0,1), vec3<f32>(1,1,1), vec3<f32>(0,1,1)
);

fn get_scene_normal(p: vec3<f32>, b_ptr: u32) -> vec3<f32> {
    let step = config.domain_size / f32(config.res);
    let e = max(step * 0.1, 0.00001); 
    let gx = get_scene_dist_indexed(p + vec3<f32>(e, 0, 0), b_ptr) - get_scene_dist_indexed(p - vec3<f32>(e, 0, 0), b_ptr);
    let gy = get_scene_dist_indexed(p + vec3<f32>(0, e, 0), b_ptr) - get_scene_dist_indexed(p - vec3<f32>(0, e, 0), b_ptr);
    let gz = get_scene_dist_indexed(p + vec3<f32>(0, 0, e), b_ptr) - get_scene_dist_indexed(p - vec3<f32>(0, 0, e), b_ptr);
    let g = vec3<f32>(gx, gy, gz);
    let len = length(g);
    return select(-g / len, vec3<f32>(0, 1, 0), len < 1e-6);
}

@compute @workgroup_size(8, 8, 4)
fn main(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    let block_list_idx = wid.y * 65535u + wid.x;
    let active_count = atomicLoad(&counters[3]);
    if (block_list_idx >= active_count) { return; }
    let packed = active_blocks[block_list_idx];
    let block_coord = vec3<i32>(i32(packed & 0x7FFu), i32((packed >> 11u) & 0x7FFu), i32((packed >> 22u) & 0x3FFu));
    
    let key = i32((u32(block_coord.x) & 0x7FFu) | ((u32(block_coord.y) & 0x7FFu) << 11u) | ((u32(block_coord.z) & 0x3FFu) << 22u));
    var h = u32(key) % config.hash_table_size;
    var b_ptr = -1;
    for (var i = 0u; i < 32u; i++) {
        if (hash_keys[h] == key) { b_ptr = i32(atomicLoad(&hash_values[h])); break; }
        h = (h + 1u) % config.hash_table_size;
    }
    if (b_ptr < 0) { return; }
    let b_ptr_u = u32(b_ptr);

    let res = config.res; let step = config.domain_size / f32(res);
    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let lid_z = lid.z + z_off;
        let id = vec3<u32>(block_coord * 8) + vec3<u32>(lid.x, lid.y, lid_z);
        if (id.x >= res - 1u || id.y >= res - 1u || id.z >= res - 1u) { continue; }
        let p_min = (vec3<f32>(id) - f32(res)/2.0) * step;
        var vals: array<f32, 8>; var cube_idx = 0u;
        for (var i = 0u; i < 8u; i++) {
            vals[i] = get_scene_dist_indexed(p_min + CORNERS[i] * step, b_ptr_u);
            if (vals[i] <= 0.0) { cube_idx |= (1u << i); }
        }
        if (cube_idx == 0u || cube_idx == 255u) { continue; }
        if (atomicLoad(&counters[0]) + 1u >= config.max_tris) { return; }
        for (var i = 0u; mc_table[cube_idx * 16u + i] != -1; i += 3u) {
            let tri_idx = atomicAdd(&counters[0], 1u);
            for (var j = 0u; j < 3u; j++) {
                let edge_idx = u32(mc_table[cube_idx * 16u + i + j]);
                let e1 = array<u32,12>(0,1,2,3,4,5,6,7,0,1,2,3)[edge_idx];
                let e2 = array<u32,12>(1,2,3,0,5,6,7,4,4,5,6,7)[edge_idx];
                let v1_val = vals[e1]; let v2_val = vals[e2];
                let t = clamp(v1_val / (v1_val - v2_val + 1e-10), 0.0, 1.0);
                var p_tri = p_min + mix(CORNERS[e1], CORNERS[e2], t) * step;
                
                if (config.res <= 400u) {
                    let d = get_scene_dist_indexed(p_tri, b_ptr_u);
                    let n = get_scene_normal(p_tri, b_ptr_u);
                    p_tri -= n * d * 0.8;
                }
                let res_v = get_scene_sdf_indexed(p_tri, b_ptr_u);
                let normal = get_scene_normal(p_tri, b_ptr_u);
                let off = tri_idx * 33u + j * 11u;
                vertices[off+0]=p_tri.x; vertices[off+1]=p_tri.y; vertices[off+2]=p_tri.z;
                vertices[off+3]=res_v.color.x; vertices[off+4]=res_v.color.y; vertices[off+5]=res_v.color.z;
                vertices[off+6]=res_v.metallic; vertices[off+7]=res_v.roughness;
                vertices[off+8]=normal.x; vertices[off+9]=normal.y; vertices[off+10]=normal.z;
                indices[tri_idx * 3u + j] = tri_idx * 3u + j;
            }
        }
    }
}
