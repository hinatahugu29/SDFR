// V15.7 Optimized Marching Cubes Pass (Direct Indexing)
// Headers provided by common.wgsl

var<workgroup> block_made_tri: atomic<u32>;

@compute @workgroup_size(8, 8, 4)
fn main(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    if (all(lid == vec3<u32>(0u))) {
        atomicStore(&block_made_tri, 0u);
    }
    workgroupBarrier();

    // 2D dispatch を 1D インデックスに変換
    let b_ptr_u = wid.y * 65535u + wid.x;
    let active_count = atomicLoad(&counters[3]);
    
    if (b_ptr_u >= active_count) { return; }

    // active_blocks から直接座標を復元 (x | y << 8 | z << 16)
    let packed = active_blocks[b_ptr_u];
    let block_coord = vec3<u32>(packed & 0xFFu, (packed >> 8u) & 0xFFu, (packed >> 16u) & 0xFFu);
    
    let res = config.res; 
    let step = config.domain_size / f32(res);

    for (var z_off = 0u; z_off < 8u; z_off += 4u) {
        let lid_z = lid.z + z_off;
        let id = (block_coord * 8u) + vec3<u32>(lid.x, lid.y, lid_z);
        
        if (id.x >= res || id.y >= res || id.z >= res) { continue; }

        let p_min = (vec3<f32>(id) - f32(res)/2.0) * step;
        var vals: array<f32, 8>; 
        var cube_idx = 0u;

        for (var i = 0u; i < 8u; i++) {
            vals[i] = get_scene_dist_indexed(p_min + CORNERS[i] * step, b_ptr_u);
            if (vals[i] <= 0.0) { cube_idx |= (1u << i); }
        }

        if (cube_idx == 0u || cube_idx == 255u) { continue; }

        atomicStore(&block_made_tri, 1u);

        if (atomicLoad(&counters[0]) + 1u >= config.max_tris) { return; }

        for (var i = 0u; mc_table[cube_idx * 16u + i] != -1; i += 3u) {
            let tri_idx = atomicAdd(&counters[0], 1u);
            atomicAdd(&counters[1], 3u);
            for (var j = 0u; j < 3u; j++) {
                let edge_idx = u32(mc_table[cube_idx * 16u + i + j]);
                let e1 = array<u32,12>(0,1,2,3,4,5,6,7,0,1,2,3)[edge_idx];
                let e2 = array<u32,12>(1,2,3,0,5,6,7,4,4,5,6,7)[edge_idx];
                let v1_val = vals[e1]; 
                let v2_val = vals[e2];
                let t = clamp(v1_val / (v1_val - v2_val + 1e-10), 0.0, 1.0);
                var p_tri = p_min + mix(CORNERS[e1], CORNERS[e2], t) * step;
                
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
    }

    workgroupBarrier();
    if (all(lid == vec3<u32>(0u))) {
        if (atomicLoad(&block_made_tri) == 1u) {
            atomicAdd(&counters[4], 1u);
        }
    }
}
