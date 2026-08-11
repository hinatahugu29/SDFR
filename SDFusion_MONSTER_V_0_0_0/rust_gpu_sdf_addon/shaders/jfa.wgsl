// Jump Flooding Algorithm for SDF generation
@group(0) @binding(0) var<uniform> config: Config;
@group(0) @binding(1) var<storage, read> volume_in: array<u32>;
@group(0) @binding(2) var<storage, read_write> jfa_buffer_a: array<vec4<i32>>; // [x, y, z, unused]
@group(0) @binding(3) var<storage, read_write> jfa_buffer_b: array<vec4<i32>>;

@compute @workgroup_size(8, 8, 4)
fn init(@builtin(global_invocation_id) gid: vec3<u32>) {
    let res = 256u;
    if (any(gid >= vec3<u32>(res))) { return; }
    let idx = gid.x + gid.y * res + gid.z * res * res;
    
    if (volume_in[idx] > 0u) {
        jfa_buffer_a[idx] = vec4<i32>(vec3<i32>(gid), 1);
    } else {
        jfa_buffer_a[idx] = vec4<i32>(-1000, -1000, -1000, 0);
    }
}

struct JfaParams {
    step: i32,
}
@group(1) @binding(0) var<uniform> jfa_config: JfaParams;

@compute @workgroup_size(8, 8, 4)
fn step_a_to_b(@builtin(global_invocation_id) gid: vec3<u32>) {
    let res = 256i;
    let igid = vec3<i32>(gid);
    if (any(igid >= vec3<i32>(res))) { return; }
    
    let k = jfa_config.step;
    var best_seed = vec3<i32>(-1000);
    var min_dist_sq = 2000000000; // Large
    
    for (var x = -1; x <= 1; x++) {
        for (var y = -1; y <= 1; y++) {
            for (var z = -1; z <= 1; z++) {
                let neighbor = igid + vec3<i32>(x, y, z) * k;
                if (all(neighbor >= vec3<i32>(0)) && all(neighbor < vec3<i32>(res))) {
                    let n_idx = u32(neighbor.x + neighbor.y * res + neighbor.z * res * res);
                    let seed = jfa_buffer_a[n_idx].xyz;
                    if (seed.x >= 0) {
                        let diff = seed - igid;
                        let d2 = dot(diff, diff);
                        if (d2 < min_dist_sq) {
                            min_dist_sq = d2;
                            best_seed = seed;
                        }
                    }
                }
            }
        }
    }
    
    let idx = u32(igid.x + igid.y * res + igid.z * res * res);
    jfa_buffer_b[idx] = vec4<i32>(best_seed, 1);
}

@compute @workgroup_size(8, 8, 4)
fn step_b_to_a(@builtin(global_invocation_id) gid: vec3<u32>) {
    let res = 256i;
    let igid = vec3<i32>(gid);
    if (any(igid >= vec3<i32>(res))) { return; }
    
    let k = jfa_config.step;
    var best_seed = vec3<i32>(-1000);
    var min_dist_sq = 2000000000;
    
    for (var x = -1; x <= 1; x++) {
        for (var y = -1; y <= 1; y++) {
            for (var z = -1; z <= 1; z++) {
                let neighbor = igid + vec3<i32>(x, y, z) * k;
                if (all(neighbor >= vec3<i32>(0)) && all(neighbor < vec3<i32>(res))) {
                    let n_idx = u32(neighbor.x + neighbor.y * res + neighbor.z * res * res);
                    let seed = jfa_buffer_b[n_idx].xyz;
                    if (seed.x >= 0) {
                        let diff = seed - igid;
                        let d2 = dot(diff, diff);
                        if (d2 < min_dist_sq) {
                            min_dist_sq = d2;
                            best_seed = seed;
                        }
                    }
                }
            }
        }
    }
    
    let idx = u32(igid.x + igid.y * res + igid.z * res * res);
    jfa_buffer_a[idx] = vec4<i32>(best_seed, 1);
}
