// V15.9 Detection Pass (Merged with Common)

fn insert_block_ptr(coord: vec3<i32>, b_ptr: i32) {
    let key = i32((u32(coord.x) & 0x7FFu) | ((u32(coord.y) & 0x7FFu) << 11u) | ((u32(coord.z) & 0x3FFu) << 22u));
    var h = u32(key) % config.hash_table_size;
    let val = u32(b_ptr);
    for (var i = 0u; i < 32u; i++) {
        let old = atomicMin(&hash_values[h], val);
        if (old == 0xFFFFFFFFu) {
            hash_keys[h] = key; return;
        }
        if (hash_keys[h] == key) { return; }
        h = (h + 1u) % config.hash_table_size;
    }
}

fn dist_sq_point_aabb(p: vec3<f32>, b_min: vec3<f32>, b_max: vec3<f32>) -> f32 {
    let d = max(max(b_min - p, vec3<f32>(0.0)), p - b_max);
    return dot(d, d);
}

@compute @workgroup_size(8, 8, 4)
fn detect_pass(@builtin(global_invocation_id) id: vec3<u32>) {
    let res = config.res; let b_size = config.block_size;
    let block_coord = vec3<i32>(id);
    if (any(block_coord >= vec3<i32>(res / b_size))) { return; }

    let step = config.domain_size / f32(res);
    let p_min = (vec3<f32>(block_coord * i32(b_size)) - f32(res)/2.0) * step;
    let p_max = p_min + f32(b_size) * step;
    let p_center = (p_min + p_max) * 0.5;

    var p_sym = p_center;
    if ((config.symmetry & 1u) != 0u) { p_sym.x = abs(p_sym.x); }
    if ((config.symmetry & 2u) != 0u) { p_sym.y = abs(p_sym.y); }
    if ((config.symmetry & 4u) != 0u) { p_sym.z = abs(p_sym.z); }

    let block_radius = length(vec3<f32>(f32(b_size) * step)) * 0.5;

    // 動的インデックスリストの生成
    var local_indices: array<u32, 128>;
    var local_count = 0u;
    
    // BVH Traversal (Stack-based)
    var stack: array<u32, 32>;
    var stack_ptr = 0u;
    stack[stack_ptr] = 0u; // Root index
    stack_ptr++;

    while (stack_ptr > 0u) {
        stack_ptr--;
        let node_idx = stack[stack_ptr];
        let node = bvh_nodes[node_idx];
        
        let n_min = node.min.xyz;
        let n_max = node.max.xyz;
        
        // AABB test with block sphere
        let d2 = dist_sq_point_aabb(p_sym, n_min, n_max);
        let r_limit = block_radius + 0.05; // Small margin for safety
        
        if (d2 < r_limit * r_limit) {
            let count_or_right = node.max.w;
            if (count_or_right > 0.0) {
                // Leaf Node
                let prim_idx = u32(node.min.w);
                if (local_count < 128u) {
                    local_indices[local_count] = prim_idx;
                    local_count++;
                }
            } else {
                // Inner Node
                let left = u32(node.min.w);
                let right = u32(-count_or_right);
                
                // Push children to stack
                if (stack_ptr < 30u) {
                    stack[stack_ptr] = left; stack_ptr++;
                    stack[stack_ptr] = right; stack_ptr++;
                }
            }
        }
    }

    if (local_count > 0u) {
        let b_ptr = i32(atomicAdd(&counters[2], 1u));
        insert_block_ptr(block_coord, b_ptr);
        
        // グローバルリストへの動的割当
        let offset = atomicAdd(&global_counter[0], local_count);
        for (var j = 0u; j < local_count; j++) {
            global_prim_indices[offset + j] = local_indices[j];
        }
        
        block_prim_info[b_ptr].offset = offset;
        block_prim_info[b_ptr].count = local_count;
        
        let idx = atomicAdd(&counters[3], 1u);
        active_blocks[idx] = (u32(block_coord.x) & 0x7FFu) | ((u32(block_coord.y) & 0x7FFu) << 11u) | ((u32(block_coord.z) & 0x3FFu) << 22u);
    }
}
