// V15.4 Common Headers and Utilities
const CORNERS = array<vec3<f32>, 8>(
    vec3<f32>(0,0,0), vec3<f32>(1,0,0), vec3<f32>(1,1,0), vec3<f32>(0,1,0),
    vec3<f32>(0,0,1), vec3<f32>(1,0,1), vec3<f32>(1,1,1), vec3<f32>(0,1,1)
);
struct Config {
    res: u32,
    domain_size: f32,
    num_primitives: u32,
    num_triangles: u32,
    symmetry: u32,
    hash_table_size: u32,
    block_size: u32,
    max_tris: u32,
}

struct Primitive {
    center_and_shape: vec4<f32>,
    rotation: vec4<f32>,
    size_and_op: vec4<f32>,
    params: vec4<f32>,
    noise_params: vec4<f32>,
    color_b_and_extra: vec4<f32>,
    layout_data1: vec4<f32>,
    layout_data2: vec4<f32>,
    layout_data3: vec4<f32>,
    layout_data4: vec4<f32>,
    extra_params: vec4<f32>,
    deform_data1: vec4<f32>,
    deform_data2: vec4<f32>,
    deform_data3: vec4<f32>,
    deform_data4: vec4<f32>,
}

@group(0) @binding(0) var<uniform> config: Config;
@group(0) @binding(1) var<storage, read> primitives: array<Primitive>;
@group(0) @binding(2) var<storage, read_write> mc_table: array<i32>;
@group(0) @binding(3) var<storage, read_write> counters: array<atomic<u32>>; // [v, i, b_ptr, active_b]
@group(0) @binding(4) var<storage, read_write> vertices: array<f32>;
@group(0) @binding(5) var<storage, read_write> indices: array<u32>;
@group(0) @binding(6) var<storage, read_write> hash_keys: array<i32>;
@group(0) @binding(7) var<storage, read_write> hash_values: array<atomic<u32>>;
@group(0) @binding(8) var<storage, read_write> block_data: array<u32>;
@group(0) @binding(9) var<storage, read_write> active_blocks: array<u32>;

struct BlockPrimInfo {
    offset: u32,
    count: u32,
}
@group(0) @binding(10) var<storage, read_write> block_prim_info: array<BlockPrimInfo>;
@group(0) @binding(11) var<storage, read_write> global_prim_indices: array<u32>;
@group(0) @binding(12) var<storage, read_write> global_counter: array<atomic<u32>>;

struct GpuTriangle {
    v0: vec4<f32>,
    v1: vec4<f32>,
    v2: vec4<f32>,
}
@group(0) @binding(16) var<storage, read> mesh_triangles: array<GpuTriangle>;

struct BvhNode {
    min: vec4<f32>, // [x, y, z, left]
    max: vec4<f32>, // [x, y, z, right]
}
@group(0) @binding(13) var<storage, read> bvh_nodes: array<BvhNode>;
@group(0) @binding(14) var mesh_sdf_volume: texture_3d<f32>;
@group(0) @binding(15) var volume_sampler: sampler;

fn dist_to_triangle(p: vec3<f32>, v0: vec3<f32>, v1: vec3<f32>, v2: vec3<f32>) -> f32 {
    let ba = v1 - v0; let pa = p - v0;
    let cb = v2 - v1; let pb = p - v1;
    let ac = v0 - v2; let pc = p - v2;
    let nor = cross(ba, v2 - v0);

    let d_sq = select(
        select(
            select(
                dot(nor, pa) * dot(nor, pa) / dot(nor, nor),
                dot(pc - ac * clamp(dot(pc, ac) / dot(ac, ac), 0.0, 1.0), pc - ac * clamp(dot(pc, ac) / dot(ac, ac), 0.0, 1.0)),
                sign(dot(cross(ac, nor), pc)) + sign(dot(cross(ba, nor), pa)) + sign(dot(cross(cb, nor), pb)) < 2.0
            ),
            dot(pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0), pa - ba * clamp(dot(pa, ba) / dot(ba, ba), 0.0, 1.0)),
            sign(dot(cross(ba, nor), pa)) + sign(dot(cross(cb, nor), pb)) + sign(dot(cross(ac, nor), pc)) < 2.0
        ),
        dot(pb - cb * clamp(dot(pb, cb) / dot(cb, cb), 0.0, 1.0), pb - cb * clamp(dot(pb, cb) / dot(cb, cb), 0.0, 1.0)),
        sign(dot(cross(cb, nor), pb)) + sign(dot(cross(ac, nor), pc)) + sign(dot(cross(ba, nor), pa)) < 2.0
    );
    return sqrt(max(d_sq, 0.0));
}

fn sd_mesh(p: vec3<f32>) -> f32 {
    if (config.num_triangles == 0u) { return 1e10; }
    
    var stack = array<i32, 24>();
    var stack_ptr = 0;
    stack[stack_ptr] = 0;
    stack_ptr++;
    
    var min_dist = 1e10;
    var side = 1.0;
    
    while (stack_ptr > 0) {
        stack_ptr--;
        let node_idx = stack[stack_ptr];
        let node = bvh_nodes[node_idx];
        
        let center_aabb = (node.min.xyz + node.max.xyz) * 0.5;
        let half_ext = (node.max.xyz - node.min.xyz) * 0.5;
        let d_aabb = sd_box(p - center_aabb, half_ext);
        
        if (d_aabb > min_dist + 0.01) { continue; }
        
        let left = i32(node.min.w);
        let right = i32(node.max.w);
        
        if (left < 0) {
            let start = u32(right);
            let count = u32(-left);
            for (var i = 0u; i < count; i++) {
                let tri = mesh_triangles[start + i];
                let d_tri = dist_to_triangle(p, tri.v0.xyz, tri.v1.xyz, tri.v2.xyz);
                if (d_tri < min_dist) {
                    min_dist = d_tri;
                    let nor = cross(tri.v1.xyz - tri.v0.xyz, tri.v2.xyz - tri.v0.xyz);
                    side = sign(dot(p - tri.v0.xyz, nor));
                }
            }
        } else {
            if (stack_ptr < 22) {
                stack[stack_ptr] = left; stack_ptr++;
                stack[stack_ptr] = right; stack_ptr++;
            }
        }
    }
    return min_dist * side;
}

fn sdf_hash3(p: vec3<f32>) -> f32 {
    var q = fract(p * 0.1031);
    q += dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}
fn sdf_noise3(p: vec3<f32>) -> f32 {
    let i = floor(p);
    let f = fract(p);
    let u = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(sdf_hash3(i + vec3<f32>(0.0,0.0,0.0)), sdf_hash3(i + vec3<f32>(1.0,0.0,0.0)), u.x),
                   mix(sdf_hash3(i + vec3<f32>(0.0,1.0,0.0)), sdf_hash3(i + vec3<f32>(1.0,1.0,0.0)), u.x), u.y),
               mix(mix(sdf_hash3(i + vec3<f32>(0.0,0.0,1.0)), sdf_hash3(i + vec3<f32>(1.0,0.0,1.0)), u.x),
                   mix(sdf_hash3(i + vec3<f32>(0.0,1.0,1.0)), sdf_hash3(i + vec3<f32>(1.0,1.0,1.0)), u.x), u.y), u.z);
}

fn q_rotate(v: vec3<f32>, q: vec4<f32>) -> vec3<f32> { return v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v); }
fn q_conj(q: vec4<f32>) -> vec4<f32> { return vec4<f32>(-q.xyz, q.w); }
fn q_from_euler(e: vec3<f32>) -> vec4<f32> {
    let e_rad = e;
    let c = cos(e_rad * 0.5); let s = sin(e_rad * 0.5);
    return vec4<f32>(
        s.x * c.y * c.z - c.x * s.y * s.z,
        c.x * s.y * c.z + s.x * c.y * s.z,
        c.x * c.y * s.z - s.x * s.y * c.z,
        c.x * c.y * c.z + s.x * s.y * s.z
    );
}

fn sd_sphere(p: vec3<f32>, r: f32) -> f32 { return length(p) - r; }
fn sd_box(p: vec3<f32>, b: vec3<f32>) -> f32 {
    let q = abs(p) - b;
    return length(max(q, vec3<f32>(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0);
}
fn sd_torus(p: vec3<f32>, t: vec2<f32>) -> f32 {
    let q = vec2<f32>(length(p.xy) - t.x, p.z);
    return length(q) - t.y;
}
fn sd_cylinder(p: vec3<f32>, h: vec2<f32>) -> f32 {
    let d = abs(vec2<f32>(length(p.xy), p.z)) - h;
    return min(max(d.x, d.y), 0.0) + length(max(d, vec2<f32>(0.0)));
}
fn sd_rounded_box(p: vec3<f32>, b: vec3<f32>, r: f32) -> f32 {
    let q = abs(p) - b + r;
    return length(max(q, vec3<f32>(0.0))) + min(max(q.x, max(q.y, q.z)), 0.0) - r;
}
fn sd_capsule(p: vec3<f32>, h: f32, r: f32) -> f32 {
    var pp = p;
    pp.z -= clamp(p.z, -h, h);
    return length(pp) - r;
}
fn sd_hex_prism(p: vec3<f32>, h_ext: vec2<f32>) -> f32 {
    let k = vec3<f32>(-0.866025404, 0.5, 0.577350269);
    let h_radius = h_ext.x * 0.8660254; 
    let rx = 0.8660254 * p.x - 0.5 * p.y;
    let ry = 0.5 * p.x + 0.8660254 * p.y;
    var pp = abs(vec3<f32>(rx, ry, p.z));
    let d_dot = dot(k.xy, pp.xy);
    pp.x -= 2.0 * min(d_dot, 0.0) * k.x;
    pp.y -= 2.0 * min(d_dot, 0.0) * k.y;
    let d = vec2<f32>(length(pp.xy - vec2<f32>(clamp(pp.x, -k.z * h_radius, k.z * h_radius), h_radius)) * sign(pp.y - h_radius), pp.z - h_ext.y);
    return min(max(d.x, d.y), 0.0) + length(max(d, vec2<f32>(0.0, 0.0)));
}
fn sd_pyramid(p: vec3<f32>, h_ext: vec2<f32>) -> f32 {
    let s_val = max(h_ext.x, 0.001);
    let h = h_ext.y / s_val;
    let m2 = h * h + 0.25;
    var pp = vec3<f32>(abs(p.x / s_val), abs(p.y / s_val), p.z / s_val);
    if (pp.y > pp.x) { let tmp = pp.x; pp.x = pp.y; pp.y = tmp; }
    pp.x -= 0.5; pp.y -= 0.5;
    let q = vec3<f32>(pp.y, h * pp.z - 0.5 * pp.x, h * pp.x + 0.5 * pp.z);
    let ss = max(-q.x, 0.0);
    let t = clamp((q.y - 0.5 * pp.y) / (m2 + 0.25), 0.0, 1.0);
    let a = m2 * (q.x + ss) * (q.x + ss) + q.y * q.y;
    let b = m2 * (q.x + 0.5 * t) * (q.x + 0.5 * t) + (q.y - m2 * t) * (q.y - m2 * t);
    var d2 = 0.0;
    if (min(q.y, -q.x * m2 - q.y * 0.5) > 0.0) { d2 = 0.0; } else { d2 = min(a, b); }
    let d = sqrt((d2 + q.z * q.z) / m2) * sign(max(q.z, -pp.z));
    return d * s_val;
}
fn sd_capped_cone(p: vec3<f32>, h: f32, r1: f32, r2: f32) -> f32 {
    let q = vec2<f32>(length(p.xy), p.z);
    let k1 = vec2<f32>(r2, h);
    let k2 = vec2<f32>(r2 - r1, 2.0 * h);
    let ca = vec2<f32>(q.x - min(q.x, select(r2, r1, q.y < 0.0)), abs(q.y) - h);
    let cb = q - k1 + k2 * clamp(dot(k1 - q, k2) / dot(k2, k2), 0.0, 1.0);
    let s = select(1.0, -1.0, cb.x < 0.0 && ca.y < 0.0);
    return s * sqrt(min(dot(ca,ca), dot(cb,cb)));
}
fn sd_ngon_prism(p: vec3<f32>, r: f32, n: f32, h: f32) -> f32 {
    let an = 3.14159265 / n;
    let cosan = cos(an); let sinan = sin(an);
    var a = atan2(p.y, p.x) + an;
    a = floor(a / (2.0 * an)) * (2.0 * an);
    let c = cos(a); let s = sin(a);
    let px = c * p.x + s * p.y;
    let py = -s * p.x + c * p.y;
    let d_xy = px - r * cosan;
    let d_z = abs(p.z) - h;
    return min(max(d_xy, d_z), 0.0) + length(max(vec2<f32>(d_xy, d_z), vec2<f32>(0.0)));
}

struct SdfResult { d: f32, color: vec3<f32>, metallic: f32, roughness: f32 }

struct DeformResult {
    p: vec3<f32>,
    scale: f32,
}

fn apply_deform(p_in: vec3<f32>, slot_info: u32, sd: vec4<f32>, prim_max_s: f32, scale_in: f32) -> DeformResult {
    let dt = slot_info & 0xFu; 
    if (dt == 0u) { return DeformResult(p_in, scale_in); }
    
    let da = (slot_info >> 4u) & 0x3u;
    var lp = p_in;
    var sc = scale_in;

    if (dt == 1u) { lp = lp - clamp(lp, -sd.xyz, sd.xyz); }
    else if (dt == 2u) { 
        if (abs(sd.x) > 0.0001) { 
            let R=1.0/sd.x; 
            if(da==2u){let dx=lp.x-sd.y;let dy=lp.y-sd.z;let ry=R-dy;let th=atan2(dx*sign(R),ry*sign(R));let r=length(vec2<f32>(ry,dx))*sign(R);lp.y=sd.z+R-r;lp.x=sd.y+th/sd.x;}
            else if(da==1u){let dz=lp.z-sd.w;let dx=lp.x-sd.y;let rx=R-dx;let th=atan2(dz*sign(R),rx*sign(R));let r=length(vec2<f32>(rx,dz))*sign(R);lp.x=sd.y+R-r;lp.z=sd.w+th/sd.x;}
            else{let dz=lp.z-sd.w;let dy=lp.y-sd.z;let ry=R-dy;let th=atan2(dz*sign(R),ry*sign(R));let r=length(vec2<f32>(ry,dz))*sign(R);lp.y=sd.z+R-r;lp.z=sd.w+th/sd.x;} 
            sc *= max(0.1, 1.0 - prim_max_s * abs(sd.x)); 
        } 
    }
    else if (dt == 3u) { 
        if(da==2u){let a=sd.x*(lp.z-sd.w);let c=cos(a);let s=sin(a);let dx=lp.x-sd.y;let dy=lp.y-sd.z;lp.x=sd.y+c*dx+s*dy;lp.y=sd.z-s*dx+c*dy;}
        else if(da==1u){let a=sd.x*(lp.y-sd.z);let c=cos(a);let s=sin(a);let dz=lp.z-sd.w;let dx=lp.x-sd.y;let l_z=sd.w+c*dz+s*dx;lp.x=sd.y-s*dz+c*dx;lp.z=l_z;}
        else{let a=sd.x*(lp.x-sd.y);let c=cos(a);let s=sin(a);let dy=lp.y-sd.z;let dz=lp.z-sd.w;let l_y=sd.z+c*dy+s*dz;lp.z=sd.w-s*dy+c*dz;lp.y=l_y;} 
        sc *= 1.0 / sqrt(1.0 + (prim_max_s * sd.x) * (prim_max_s * sd.x)); 
    }
    else if (dt == 4u) { 
        var s_val=1.0; 
        if(da==2u){s_val=max(0.1,1.0+sd.x*(lp.z-sd.w));lp.x=sd.y+(lp.x-sd.y)/s_val;lp.y=sd.z+(lp.y-sd.z)/s_val;}
        else if(da==1u){s_val=max(0.1,1.0+sd.x*(lp.y-sd.z));lp.x=sd.y+(lp.x-sd.y)/s_val;lp.z=sd.w+(lp.z-sd.w)/s_val;}
        else{s_val=max(0.1,1.0+sd.x*(lp.x-sd.y));lp.y=sd.z+(lp.y-sd.z)/s_val;lp.z=sd.w+(lp.z-sd.w)/s_val;} 
        sc *= min(1.0, s_val); 
    }
    return DeformResult(lp, sc);
}

fn evaluate_layout(p_in: vec3<f32>, prim: Primitive, accum_idx_in: f32) -> vec3<f32> {
    var lp = q_rotate(p_in - prim.center_and_shape.xyz, q_conj(prim.rotation));
    var accum_idx = accum_idx_in;
    
    let packed1 = u32(prim.layout_data1.x);
    let flags = packed1 & 0xFFu;

    if ((flags & 1u) != 0u) {
        let mask = (packed1 >> 8u) & 0xFu;
        let m_offset = prim.layout_data1.y;
        if ((mask & 1u) != 0u) { lp.x = abs(lp.x) - m_offset; }
        if ((mask & 2u) != 0u) { lp.y = abs(lp.y) - m_offset; }
        if ((mask & 4u) != 0u) { lp.z = abs(lp.z) - m_offset; }
    }
    
    if ((flags & 2u) != 0u || (flags & 4u) != 0u) {
        let count = f32((packed1 >> 12u) & 0xFFu);
        let axis = (packed1 >> 20u) & 3u;
        let angle = 6.283185307 / max(count, 1.0);
        let radius = prim.layout_data1.z;
        let pitch = prim.layout_data1.w;
        
        var x: f32; var y: f32;
        if (axis == 0u) { x = lp.y; y = lp.z; }
        else if (axis == 1u) { x = lp.x; y = lp.z; }
        else { x = lp.x; y = lp.y; }
        
        let a_raw = atan2(y, x) + angle * 0.5;
        let step = floor(a_raw / angle);
        let a = step * angle;
        let s = sin(a); let c = cos(a);
        let nx = c * x + s * y;
        let ny = -s * x + c * y;
        accum_idx += step;
        
        if ((flags & 4u) != 0u) {
            let z_offset = step * pitch;
            if (axis == 0u) { lp.x -= z_offset; }
            else if (axis == 1u) { lp.y -= z_offset; }
            else { lp.z -= z_offset; }
        }
        
        if (axis == 0u) { lp.y = nx - radius; lp.z = ny; }
        else if (axis == 1u) { lp.x = nx - radius; lp.z = ny; }
        else { lp.x = nx - radius; lp.y = ny; }
    }

    if ((flags & 8u) != 0u) {
        let g_p = prim.layout_data2.z;
        let cz = floor(g_p / 10000.0); let cy = floor((g_p - cz * 10000.0) / 100.0); let cx = g_p - cz * 10000.0 - cy * 100.0;
        let g_counts = vec3<f32>(cx, cy, cz);
        let sp = vec3<f32>(prim.layout_data2.w, prim.layout_data3.x, prim.layout_data3.y);
        let g_limit = (g_counts - vec3<f32>(1.0)) * 0.5;
        let g_idx = round(lp / sp);
        let g_actual = clamp(g_idx, -floor(g_limit), ceil(g_limit));
        lp = lp - sp * g_actual;
        accum_idx += g_actual.x + g_actual.y + g_actual.z;
    }
    
    if ((flags & 32u) != 0u) {
        let seed = prim.layout_data2.x;
        let strength = prim.layout_data2.y;
        let h = sdf_hash3(lp + vec3<f32>(seed));
        lp.x += (h - 0.5) * strength;
        lp.y += (sdf_hash3(lp + vec3<f32>(seed + 1.0)) - 0.5) * strength;
        lp.z += (sdf_hash3(lp + vec3<f32>(seed + 2.0)) - 0.5) * strength;
    }
    
    lp = q_rotate(lp, q_from_euler(vec3<f32>(prim.layout_data3.zw, prim.layout_data4.x) + prim.layout_data4.yzw * accum_idx));
    
    return lp;
}

fn evaluate_shape(lp_in: vec3<f32>, prim: Primitive) -> f32 {
    var lp = lp_in;
    let packed_meta = u32(prim.deform_data1.x);
    let prim_max_s = max(prim.size_and_op.x, max(prim.size_and_op.y, prim.size_and_op.z));
    var df_scale = 1.0;
    
    var d_res = apply_deform(lp, packed_meta & 0x3Fu, vec4<f32>(prim.deform_data1.yzw, prim.deform_data2.x), prim_max_s, df_scale);
    lp = d_res.p; df_scale = d_res.scale;
    d_res = apply_deform(lp, (packed_meta >> 6u) & 0x3Fu, vec4<f32>(prim.deform_data2.yzw, prim.deform_data3.x), prim_max_s, df_scale);
    lp = d_res.p; df_scale = d_res.scale;
    d_res = apply_deform(lp, (packed_meta >> 12u) & 0x3Fu, vec4<f32>(prim.deform_data3.yzw, prim.deform_data4.x), prim_max_s, df_scale);
    lp = d_res.p; df_scale = d_res.scale;
    d_res = apply_deform(lp, (packed_meta >> 18u) & 0x3Fu, vec4<f32>(prim.deform_data4.yzw, 0.0), prim_max_s, df_scale);
    lp = d_res.p; df_scale = d_res.scale;

    let shape = u32(prim.center_and_shape.w);
    let s = max(prim.size_and_op.xyz, vec3<f32>(0.001));
    let s_min = min(s.x, min(s.y, s.z));
    let lp_s = lp / s;
    var dp: f32 = 1e10;
    
    if (shape == 100u) { 
        dp = sd_mesh(lp); 
    } else if (shape == 0u) { 
        dp = length(lp_s) - prim.params.x; 
    } else if (shape == 1u) { 
        dp = sd_box(lp_s, vec3<f32>(1.0)); 
    } else if (shape == 2u) { 
        dp = sd_torus(lp_s, prim.extra_params.xy); 
    } else if (shape == 3u) {
        dp = sd_cylinder(lp_s, prim.extra_params.xy);
    } else if (shape == 4u) {
        dp = sd_rounded_box(lp_s, vec3<f32>(1.0), prim.extra_params.x);
    } else if (shape == 5u) {
        dp = sd_capsule(lp_s, prim.extra_params.y, prim.extra_params.x);
    } else if (shape == 6u) {
        dp = sd_hex_prism(lp_s, prim.extra_params.xy);
    } else if (shape == 7u) {
        dp = sd_pyramid(lp_s, prim.extra_params.xy);
    } else if (shape == 8u) {
        dp = sd_capped_cone(lp_s, prim.extra_params.z, prim.extra_params.x, prim.extra_params.y);
    } else if (shape == 9u) {
        dp = sd_ngon_prism(lp_s, prim.extra_params.x, prim.extra_params.y, prim.extra_params.z);
    }

    if (prim.noise_params.x > 0.0) {
        dp += (sdf_noise3(lp * prim.noise_params.y) * 2.0 - 1.0) * prim.noise_params.x;
    }

    return dp * s_min * df_scale;
}

fn get_scene_dist_indexed(p: vec3<f32>, b_ptr: u32) -> f32 {
    let info = block_prim_info[b_ptr];
    var d_total = 1e10;
    var p_sym = p;
    if ((config.symmetry & 1u) != 0u) { p_sym.x = abs(p_sym.x); }
    if ((config.symmetry & 2u) != 0u) { p_sym.y = abs(p_sym.y); }
    if ((config.symmetry & 4u) != 0u) { p_sym.z = abs(p_sym.z); }

    var first = true;
    for (var i = 0u; i < info.count; i++) {
        let prim_idx = global_prim_indices[info.offset + i];
        let prim = primitives[prim_idx];
        let op = u32(prim.size_and_op.w);
        let lp_layout = evaluate_layout(p_sym, prim, 0.0);
        let d_prim = evaluate_shape(lp_layout, prim);
        
        let k = max(prim.params.y, 0.0001);
        if (first) { d_total = select(1e10, d_prim, op == 0u); first = false; }
        else {
            switch (op) {
                case 0u: { let h = clamp(0.5 + 0.5 * (d_total - d_prim) / k, 0.0, 1.0); d_total = mix(d_total, d_prim, h) - k * h * (1.0 - h); }
                case 1u: { let h = clamp(0.5 + 0.5 * (d_total + d_prim) / k, 0.0, 1.0); d_total = mix(-d_prim, d_total, h) + k * h * (1.0 - h); }
                case 2u: { let h = clamp(0.5 + 0.5 * (d_prim - d_total) / k, 0.0, 1.0); d_total = mix(d_total, d_prim, h) + k * h * (1.0 - h); }
                default: {}
            }
        }
    }
    return d_total;
}

fn get_scene_sdf_indexed(p: vec3<f32>, b_ptr: u32) -> SdfResult {
    let info = block_prim_info[b_ptr];
    var res: SdfResult;
    res.d = 1e10; res.color = vec3<f32>(1.0); res.metallic = 0.0; res.roughness = 0.5;
    var p_sym = p;
    if ((config.symmetry & 1u) != 0u) { p_sym.x = abs(p_sym.x); }
    if ((config.symmetry & 2u) != 0u) { p_sym.y = abs(p_sym.y); }
    if ((config.symmetry & 4u) != 0u) { p_sym.z = abs(p_sym.z); }

    var first = true;
    for (var i = 0u; i < info.count; i++) {
        let prim_idx = global_prim_indices[info.offset + i];
        let prim = primitives[prim_idx];
        let op = u32(prim.size_and_op.w);
        let lp_layout = evaluate_layout(p_sym, prim, 0.0);
        let d_prim = evaluate_shape(lp_layout, prim);
        let k = max(prim.params.y, 0.0001);
        let noise_val = select(0.0, (sdf_noise3(lp_layout * prim.noise_params.y) * 2.0 - 1.0) * prim.noise_params.x, prim.noise_params.x > 0.0);
        let dp_final = d_prim + noise_val;
        let color = vec3<f32>(prim.noise_params.zw, prim.color_b_and_extra.x);
        
        if (first) { 
            res.d = dp_final; 
            res.color = color; res.metallic = prim.params.z; res.roughness = prim.params.w;
            first = false; 
        } else {
            switch (op) {
                case 0u: {
                    let h = clamp(0.5 + 0.5 * (res.d - dp_final) / k, 0.0, 1.0); 
                    res.d = mix(res.d, dp_final, h) - k * h * (1.0 - h); 
                    res.color = mix(res.color, color, h); 
                    res.metallic = mix(res.metallic, prim.params.z, h);
                    res.roughness = mix(res.roughness, prim.params.w, h);
                }
                case 1u: {
                    let h = clamp(0.5 + 0.5 * (res.d + dp_final) / k, 0.0, 1.0); 
                    res.d = mix(res.d, -dp_final, 1.0 - h) + k * h * (1.0 - h); 
                    res.color = mix(color, res.color, h);
                    res.metallic = mix(prim.params.z, res.metallic, h);
                    res.roughness = mix(prim.params.w, res.roughness, h);
                }
                case 2u: {
                    let h = clamp(0.5 + 0.5 * (dp_final - res.d) / k, 0.0, 1.0); 
                    res.d = mix(res.d, dp_final, h) + k * h * (1.0 - h); 
                    res.color = mix(res.color, color, h);
                    res.metallic = mix(res.metallic, prim.params.z, h);
                    res.roughness = mix(res.roughness, prim.params.w, h);
                }
                default: {}
            }
        }
    }
    return res;
}

fn get_scene_normal(p: vec3<f32>, b_ptr: u32) -> vec3<f32> {
    let step = config.domain_size / f32(config.res);
    let e = max(step * 0.1, 0.0005);
    let gx = get_scene_dist_indexed(p + vec3<f32>(e, 0, 0), b_ptr) - get_scene_dist_indexed(p - vec3<f32>(e, 0, 0), b_ptr);
    let gy = get_scene_dist_indexed(p + vec3<f32>(0, e, 0), b_ptr) - get_scene_dist_indexed(p - vec3<f32>(0, e, 0), b_ptr);
    let gz = get_scene_dist_indexed(p + vec3<f32>(0, 0, e), b_ptr) - get_scene_dist_indexed(p - vec3<f32>(0, 0, e), b_ptr);
    let g = vec3<f32>(gx, gy, gz);
    let len = length(g);
    return select(g / len, vec3<f32>(0, 1, 0), len < 1e-6);
}
