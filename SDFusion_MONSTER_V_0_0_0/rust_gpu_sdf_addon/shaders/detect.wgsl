// V15.7 Robust Detect Pass (Generous Margin & Exact Binning)
// Headers provided by common.wgsl

var<workgroup> block_intersected: atomic<u32>;
var<workgroup> temp_prim_list: array<u32, 64>;
var<workgroup> temp_prim_count: atomic<u32>;

@compute @workgroup_size(8, 8, 4)
fn detect_pass(@builtin(workgroup_id) wid: vec3<u32>, @builtin(local_invocation_id) lid: vec3<u32>) {
    if (all(lid == vec3<u32>(0u))) {
        atomicStore(&block_intersected, 0u);
        atomicStore(&temp_prim_count, 0u);
    }
    workgroupBarrier();

    let res = config.res;
    let step = config.domain_size / f32(res);
    
    // ブロックの物理的な中心と範囲
    var b_min = (vec3<f32>(wid * 8u) - f32(res)/2.0) * step - 0.05;
    var b_max = b_min + (step * 8.0 + 0.1);

    // 対称性の考慮
    if ((config.symmetry & 1u) != 0u) {
        if (b_max.x < 0.0) {
            let tmp = b_min.x; b_min.x = -b_max.x; b_max.x = -tmp;
        } else if (b_min.x < 0.0) {
            b_min.x = 0.0; b_max.x = max(abs(b_min.x), abs(b_max.x));
        }
    }
    if ((config.symmetry & 2u) != 0u) {
        if (b_max.y < 0.0) {
            let tmp = b_min.y; b_min.y = -b_max.y; b_max.y = -tmp;
        } else if (b_min.y < 0.0) {
            b_min.y = 0.0; b_max.y = max(abs(b_min.y), abs(b_max.y));
        }
    }
    if ((config.symmetry & 4u) != 0u) {
        if (b_max.z < 0.0) {
            let tmp = b_min.z; b_min.z = -b_max.z; b_max.z = -tmp;
        } else if (b_min.z < 0.0) {
            b_min.z = 0.0; b_max.z = max(abs(b_min.z), abs(b_max.z));
        }
    }

    if (all(lid == vec3<u32>(0u))) {
        let num_prims = config.num_primitives;
        let eps = 1e-4;

        for (var i = 0u; i < num_prims; i++) {
            let prim = primitives[i];
            let center = prim.center_and_shape.xyz;
            let size = prim.size_and_op.xyz;
            let shape = prim.center_and_shape.w;
            var bound: f32 = 0.0;
            
            if (shape == 0.0) { // Sphere
                bound = prim.params.x;
            } else if (shape == 1.0 || shape == 4.0 || shape == 100.0) { // Box / Rounded Box / Mesh
                bound = 0.0; // Use explicit AABB check below
            } else {
                bound = length(size) + prim.params.x; // Fallback
            }
            
            bound += prim.params.y + prim.noise_params.x; // Smoothness + Noise
            
            var p_min: vec3<f32>;
            var p_max: vec3<f32>;
            
            if (shape == 1.0 || shape == 4.0 || shape == 100.0) {
                p_min = center - (size + bound + 0.1);
                p_max = center + (size + bound + 0.1);
            } else {
                p_min = center - (bound + 0.1);
                p_max = center + (bound + 0.1);
            }

            if (all(b_min < p_max + eps) && all(b_max > p_min - eps)) {
                let pos = atomicAdd(&temp_prim_count, 1u);
                if (pos < 64u) {
                    temp_prim_list[pos] = i;
                    atomicStore(&block_intersected, 1u);
                }
            }
        }
    }
    workgroupBarrier();

    if (atomicLoad(&block_intersected) == 1u && all(lid == vec3<u32>(0u))) {
        // Simple packing (8 bits each for x, y, z)
        let packed_id = wid.x | (wid.y << 8u) | (wid.z << 16u);
        
        var p_count = atomicLoad(&temp_prim_count);
        if (p_count > 64u) { p_count = 64u; }

        let b_ptr = atomicAdd(&counters[3], 1u);
        let p_offset = atomicAdd(&global_counter[0], p_count);
        
        block_prim_info[b_ptr].offset = p_offset;
        block_prim_info[b_ptr].count = p_count;
        for (var pi = 0u; pi < p_count; pi++) {
            global_prim_indices[p_offset + pi] = temp_prim_list[pi];
        }
        active_blocks[b_ptr] = packed_id;
    }
}
