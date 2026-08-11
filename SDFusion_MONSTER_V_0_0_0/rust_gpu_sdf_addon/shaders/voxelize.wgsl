// Voxelize Pass: Rasterize triangles into a volume shell
struct Triangle {
    v0: vec4<f32>,
    v1: vec4<f32>,
    v2: vec4<f32>,
}

@group(0) @binding(0) var<uniform> config: Config;
@group(0) @binding(1) var<storage, read> triangles: array<Triangle>;
@group(0) @binding(2) var<storage, read_write> volume: array<atomic<u32>>; // 256^3 bits or bytes

// 128 threads per triangle or one thread per triangle?
// For many triangles, one thread per triangle scanning its AABB is simple.
@compute @workgroup_size(64)
fn main(@builtin(global_invocation_id) gid: vec3<u32>) {
    let tri_idx = gid.x;
    if (tri_idx >= config.num_triangles) { return; }
    
    let tri = triangles[tri_idx];
    let res = 256u; // Fixed monster resolution for mesh
    let step = config.domain_size / f32(res);
    
    // Triangle AABB in grid space
    let b_min = floor((min(tri.v0.xyz, min(tri.v1.xyz, tri.v2.xyz)) + f32(res)/2.0 * step) / step);
    let b_max = ceil((max(tri.v0.xyz, max(tri.v1.xyz, tri.v2.xyz)) + f32(res)/2.0 * step) / step);
    
    let g_min = vec3<u32>(clamp(vec3<i32>(b_min), vec3<i32>(0), vec3<i32>(i32(res)-1)));
    let g_max = vec3<u32>(clamp(vec3<i32>(b_max), vec3<i32>(0), vec3<i32>(i32(res)-1)));
    
    for (var x = g_min.x; x <= g_max.x; x++) {
        for (var y = g_min.y; y <= g_max.y; y++) {
            for (var z = g_min.z; z <= g_max.z; z++) {
                let p = (vec3<f32>(f32(x), f32(y), f32(z)) - f32(res)/2.0) * step;
                // Simple point-triangle distance or intersection test
                // For a shell, we just need to know if the triangle passes through the voxel
                if (triangle_voxel_intersection(tri, p, step)) {
                    let idx = x + y * res + z * res * res;
                    atomicStore(&volume[idx], 1u);
                }
            }
        }
    }
}

fn triangle_voxel_intersection(tri: Triangle, p: vec3<f32>, h: f32) -> bool {
    // Basic AABB-Triangle intersection (simplified for shell)
    // For now, just check if any vertex is inside or if center is close
    let c = p + h * 0.5;
    let d = dist_point_triangle(c, tri.v0.xyz, tri.v1.xyz, tri.v2.xyz);
    return d < h * 0.866; // approx voxel radius
}

fn dist_point_triangle(p: vec3<f32>, a: vec3<f32>, b: vec3<f32>, c: vec3<f32>) -> f32 {
    let ab = b - a; let bc = c - b; let ca = a - c;
    let ap = p - a; let bp = p - b; let cp = p - c;
    let n = cross(ab, -ca);
    
    let sn = sign(dot(cross(ab, n), ap)) + sign(dot(cross(bc, n), bp)) + sign(dot(cross(ca, n), cp));
    if (abs(sn) < 2.0) {
        let v = p - (a + ab * clamp(dot(ap, ab)/dot(ab, ab), 0.0, 1.0));
        let v2 = p - (b + bc * clamp(dot(bp, bc)/dot(bc, bc), 0.0, 1.0));
        let v3 = p - (c + ca * clamp(dot(cp, ca)/dot(ca, ca), 0.0, 1.0));
        return sqrt(min(dot(v,v), min(dot(v2,v2), dot(v3,v3))));
    }
    let d2 = dot(n, ap) * dot(n, ap) / dot(n, n);
    return sqrt(d2);
}
