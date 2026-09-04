import gpu

# -------------------------------------------------------------------------
# Raymarching Overlay（GLSL Sources）
# -------------------------------------------------------------------------

VERT_SRC = '''
void main() {
    v_uv = pos.xy * 0.5 + 0.5;
    gl_Position = vec4(pos.xy, 0.999, 1.0);
}
'''

FRAG_SRC = '''
float sdf_smin(float a,float b,float k){if(k<0.001)return min(a,b);float h=max(k-abs(a-b),0.0)/k;return min(a,b)-h*h*h*k*(1.0/6.0);}
float sdf_smax(float a,float b,float k){if(k<0.001)return max(a,b);float h=max(k-abs(a-b),0.0)/k;return max(a,b)+h*h*h*k*(1.0/6.0);}

vec3 q_rotate(vec3 p, vec4 q){
    return p + 2.0 * cross(q.xyz, cross(q.xyz, p) + q.w * p);
}
vec4 q_conj(vec4 q) { return vec4(-q.xyz, q.w); }
vec4 q_from_euler(vec3 e){
    vec3 c = cos(e * 0.5); vec3 s = sin(e * 0.5);
    return vec4(
        s.x * c.y * c.z - c.x * s.y * s.z,
        c.x * s.y * c.z + s.x * c.y * s.z,
        c.x * c.y * s.z - s.x * s.y * c.z,
        c.x * c.y * c.z + s.x * s.y * s.z
    );
}

float apply_primitive_edge(float d1, float d2, uint profile, float k, float cs) {
    if (profile == 4u) { // Chamfer
        float plane = (d1 + d2 + k) * 0.70710678;
        float m = max(d1, d2);
        if (cs > 0.0) { float h = clamp(0.5 + 0.5 * (plane - m) / cs, 0.0, 1.0); return mix(m, plane, h) + cs * h * (1.0 - h); }
        return max(m, plane);
    } else { // Fallback to Round for primitive edges
        float h = max(k - abs(d1 - d2), 0.0) / k; 
        return max(d1, d2) + h * h * h * k * 0.166666;
    }
}

float sdf_eval_shape(vec3 p_in, float t, vec3 size, float r, vec4 extra, vec4 mod_p, vec4 gyro_p){
    vec3 abs_s = max(abs(size), vec3(0.001));
    float s_min = min(abs_s.x, min(abs_s.y, abs_s.z));
    vec3 s_signed = abs_s * (step(0.0, size) * 2.0 - 1.0);
    vec3 p_s = p_in / s_signed;
    vec3 unit_size = vec3(1.0);
    float res_d = 0.0;
    
    uint edge_profile = uint(mod_p.x);
    float shell_thickness = mod_p.y;
    float edge_cs = mod_p.z;
    float edge_k = mod_p.w / s_min;

    if(t<0.5) { res_d = length(p_s) - r; } // Sphere
    else if(t<1.5){ // Box
        if(edge_profile > 0u){
            vec3 q = abs(p_s) - unit_size;
            float d_tmp = apply_primitive_edge(q.x, q.y, edge_profile, edge_k, edge_cs);
            res_d = apply_primitive_edge(d_tmp, q.z, edge_profile, edge_k, edge_cs);
        } else {
            vec3 q = abs(p_s) - unit_size; res_d = length(max(q,0.0)) + min(max(q.x,max(q.y,q.z)),0.0); 
        }
    }
    else if(t<2.5){ vec2 q = vec2(length(p_s.xy) - extra.x, p_s.z); res_d = length(q) - extra.y; } // Torus
    else if(t<3.5){ // Cylinder
        if (edge_profile > 0u) {
            float d_cyl = length(p_s.xy) - extra.x;
            float d_slab = abs(p_s.z) - extra.y;
            res_d = apply_primitive_edge(d_cyl, d_slab, edge_profile, edge_k, edge_cs);
        } else {
            vec2 q = abs(vec2(length(p_s.xy), p_s.z)) - extra.xy;
            res_d = min(max(q.x, q.y), 0.0) + length(max(q, 0.0));
        }
    }
    else if(t<4.5){ // Rounded Box
        if (edge_profile > 0u) {
            vec3 q = abs(p_s) - unit_size;
            float d_tmp = apply_primitive_edge(q.x, q.y, edge_profile, extra.x, edge_cs);
            res_d = apply_primitive_edge(d_tmp, q.z, edge_profile, extra.x, edge_cs);
        } else {
            vec3 q = abs(p_s) - unit_size + extra.x;
            res_d = length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0) - extra.x;
        }
    }
    else if(t<5.5){ // Capsule
        vec3 pp = p_s; pp.z -= clamp(p_s.z, -extra.y, extra.y);
        res_d = length(pp) - extra.x;
    }
    else if(t<6.5){ // Hex Prism
        if (edge_profile > 0u) {
            vec3 k_hex = vec3(-0.866025404, 0.5, 0.577350269);
            float h_radius = extra.x * 0.8660254; 
            float rx = 0.8660254 * p_s.x - 0.5 * p_s.y;
            float ry = 0.5 * p_s.x + 0.8660254 * p_s.y;
            vec3 pp = abs(vec3(rx, ry, p_s.z));
            float d_dot = dot(k_hex.xy, pp.xy);
            pp.x -= 2.0 * min(d_dot, 0.0) * k_hex.x;
            pp.y -= 2.0 * min(d_dot, 0.0) * k_hex.y;
            float d_xy = length(pp.xy - vec2(clamp(pp.x, -k_hex.z * h_radius, k_hex.z * h_radius), h_radius)) * sign(pp.y - h_radius);
            float d_slab = pp.z - extra.y;
            res_d = apply_primitive_edge(d_xy, d_slab, edge_profile, edge_k, edge_cs);
        } else {
            vec3 k = vec3(-0.866025404, 0.5, 0.577350269);
            float h_radius = extra.x * 0.8660254; 
            float rx = 0.8660254 * p_s.x - 0.5 * p_s.y;
            float ry = 0.5 * p_s.x + 0.8660254 * p_s.y;
            vec3 pp = abs(vec3(rx, ry, p_s.z));
            pp.xy -= 2.0 * min(dot(k.xy, pp.xy), 0.0) * k.xy;
            vec2 d = vec2(length(pp.xy - vec2(clamp(pp.x, -k.z * h_radius, k.z * h_radius), h_radius)) * sign(pp.y - h_radius), pp.z - extra.y);
            res_d = min(max(d.x, d.y), 0.0) + length(max(d, 0.0));
        }
    }
    else if(t<7.5){ // Pyramid
        float s_val = max(extra.x, 0.001);
        float h = extra.y / s_val; float m2 = h*h + 0.25;
        vec3 pp = vec3(abs(p_s.x / s_val), abs(p_s.y / s_val), p_s.z / s_val);
        if(pp.y > pp.x) {
            float tmp = pp.x; pp.x = pp.y; pp.y = tmp;
        }
        pp.x -= 0.5; pp.y -= 0.5;
        vec3 q = vec3(pp.y, h*pp.z - 0.5*pp.x, h*pp.x + 0.5*pp.z);
        float ss_val = max(-q.x, 0.0);
        float t_val = clamp((q.y - 0.5*pp.y)/(m2 + 0.25), 0.0, 1.0);
        float a = m2*(q.x+ss_val)*(q.x+ss_val) + q.y*q.y;
        float b = m2*(q.x+0.5*t_val)*(q.x+0.5*t_val) + (q.y-m2*t_val)*(q.y-m2*t_val);
        float d2 = 0.0;
        if(min(q.y, -q.x*m2 - q.y*0.5) > 0.0) d2 = 0.0;
        else d2 = min(a, b);
        float d = sqrt((d2 + q.z*q.z)/m2) * sign(max(q.z, -pp.z));
        res_d = d * s_val;
    }
    else if(t<8.5){ // Capped Cone
        vec2 q = vec2(length(p_s.xy), p_s.z);
        float h = extra.z; float r1 = extra.x; float r2 = extra.y;
        vec2 k1 = vec2(r2, h);
        vec2 k2 = vec2(r2 - r1, 2.0 * h);
        vec2 ca = vec2(q.x - min(q.x, (q.y < 0.0) ? r1 : r2), abs(q.y) - h);
        vec2 cb = q - k1 + k2 * clamp(dot(k1 - q, k2) / dot(k2, k2), 0.0, 1.0);
        float s = (cb.x < 0.0 && ca.y < 0.0) ? -1.0 : 1.0;
        res_d = s * sqrt(min(dot(ca, ca), dot(cb, cb)));
    }
    else if(t<9.5){ // Ngon Prism
        if (edge_profile > 0u) {
            float r = extra.x; float n = extra.y; float h = extra.z;
            float an = 3.14159265 / n;
            float cosan = cos(an);
            float a = atan(p_s.y, p_s.x) + an;
            a = floor(a / (2.0 * an)) * (2.0 * an);
            float c = cos(a); float s_tr = sin(a);
            float px = c * p_s.x + s_tr * p_s.y;
            float py = -s_tr * p_s.x + c * p_s.y;
            float d_xy = px - r * cosan;
            float d_z = abs(p_s.z) - h;
            res_d = apply_primitive_edge(d_xy, d_z, edge_profile, edge_k, edge_cs);
        } else {
            float r = extra.x; float n = extra.y; float h = extra.z;
            float an = 3.14159265 / n;
            float cosan = cos(an);
            float a = atan(p_s.y, p_s.x) + an;
            a = floor(a / (2.0 * an)) * (2.0 * an);
            float c = cos(a); float s = sin(a);
            float px = c * p_s.x + s * p_s.y;
            float d_xy = px - r * cosan;
            float d_z = abs(p_s.z) - h;
            res_d = min(max(d_xy, d_z), 0.0) + length(max(vec2(d_xy, d_z), 0.0));
        }
    }
    else if(t<10.5){ // Ellipsoid
        vec3 er = max(extra.xyz, vec3(0.001));
        float k0 = length(p_s / er);
        float k1 = length(p_s / (er * er));
        res_d = k0 * (k0 - 1.0) / max(k1, 0.0001);
    }
    else if(t<11.5){ // Rounded Cylinder
        float ra = extra.x; float rb = extra.y; float h = extra.z;
        vec2 d = vec2(length(p_s.xy) - ra + rb, abs(p_s.z) - h);
        res_d = min(max(d.x, d.y), 0.0) + length(max(d, 0.0)) - rb;
    }
    else if(t<12.5){ // Capped Torus
        float ra = extra.x; float rb = extra.y; float ang = extra.z;
        vec2 sc = vec2(sin(ang * 0.5), cos(ang * 0.5));
        vec3 pp = vec3(p_s.x, abs(p_s.y), p_s.z);
        float k = (sc.y * pp.x > sc.x * pp.y) ? dot(pp.xy, sc) : length(pp.xy);
        res_d = sqrt(dot(pp,pp) + ra*ra - 2.0*ra*k) - rb;
    }
    else if(t<13.5){ // Octahedron (exact)
        float s = extra.x;
        vec3 pp = abs(p_s);
        float m = pp.x + pp.y + pp.z - s;
        vec3 q;
        if(3.0*pp.x < m) q = pp.xyz;
        else if(3.0*pp.y < m) q = pp.yzx;
        else if(3.0*pp.z < m) q = pp.zxy;
        else return m * 0.57735027 * s_min;
        float k = clamp(0.5*(q.z-q.y+s), 0.0, s);
        res_d = length(vec3(q.x, q.y-s+k, q.z-k));
    }
    else if(t<14.5){ // Cut Sphere
        float h = extra.x;
        float w = sqrt(max(r*r - h*h, 0.0));
        vec2 q = vec2(length(p_s.xy), p_s.z);
        float s_cut = max((h-r)*q.x*q.x + w*w*(h+r-2.0*q.y), h*q.x - w*q.y);
        if(s_cut < 0.0) res_d = length(q) - r;
        else if(q.x < w) res_d = h - q.y;
        else res_d = length(q - vec2(w, h));
    }
    else if(t<15.5){ // Math Field (TPMS)
        float freq = max(extra.x, 0.001);
        float thick = max(extra.y, 0.001);
        vec3 axis_scale = max(gyro_p.yzw, vec3(0.05));
        vec3 q = (p_s * axis_scale) * freq + vec3(gyro_p.x);
        // mod_p.x: field_type (0=Gyroid, 1=Schwarz P, 2=Schwarz D)。式を足す場合はここに1分岐追加するだけでよい。
        float g;
        if (mod_p.x >= 1.5) {
            g = sin(q.x)*sin(q.y)*sin(q.z) + sin(q.x)*cos(q.y)*cos(q.z) + cos(q.x)*sin(q.y)*cos(q.z) + cos(q.x)*cos(q.y)*sin(q.z) + extra.z; // Schwarz D
        } else if (mod_p.x >= 0.5) {
            g = cos(q.x) + cos(q.y) + cos(q.z) + extra.z; // Schwarz P
        } else {
            g = sin(q.x) * cos(q.y) + sin(q.y) * cos(q.z) + sin(q.z) * cos(q.x) + extra.z; // Gyroid
        }
        float field = abs(g) / freq - thick;
        float e = max(extra.w, 0.01);
        float mask_d;
        if(mod_p.z >= 1.5) {
            vec2 d = vec2(length(p_s.xy) - e, abs(p_s.z) - e);
            mask_d = length(max(d, vec2(0.0))) + min(max(d.x, d.y), 0.0);
        } else if(mod_p.z >= 0.5) {
            mask_d = length(p_s) - e;
        } else {
            vec3 b = abs(p_s) - vec3(e);
            mask_d = length(max(b, vec3(0.0))) + min(max(b.x, max(b.y, b.z)), 0.0);
        }
        float wall = -mask_d;
        if(mod_p.w >= 1.5) {
            res_d = max(field, mask_d);
        }
        else
        if(wall < 0.0) {
            res_d = -wall + thick;
        } else if(mod_p.w >= 0.5) {
            res_d = field;
        } else {
            float fade_width = clamp(0.9 / freq, 0.08, e * 0.45);
            float fade_t = clamp(wall / fade_width, 0.0, 1.0);
            float fade = fade_t * fade_t * (3.0 - 2.0 * fade_t);
            res_d = field + (1.0 - fade) * (thick * 2.0 + 0.02);
        }
    }
    else if(t<16.5){ // Extrude
        vec2 size_xy = extra.xy; float depth = extra.z; float corner_r = extra.w; float chamfer = edge_cs;
        float d_2d = (edge_profile == 1u) ? (length(p_s.xy) - max(size_xy.x, 0.001)) : (length(max(abs(p_s.xy) - (size_xy - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y))), 0.0)) + min(max(abs(p_s.xy).x - (size_xy.x - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y))), abs(p_s.xy).y - (size_xy.y - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y)))), 0.0) - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y)));
        float d_z = abs(p_s.z) - depth;
        float d_ext = min(max(d_2d, d_z), 0.0) + length(max(vec2(d_2d, d_z), vec2(0.0)));
        res_d = (chamfer > 0.0) ? (d_ext - chamfer) : d_ext;
    }
    else if(t<17.5){ // Lathe
        vec2 size_xy = extra.xy; float offset = extra.z; float corner_r = extra.w;
        vec2 q = vec2(length(p_s.xz) - offset, p_s.y);
        res_d = (edge_profile == 1u) ? (length(q) - max(size_xy.x, 0.001)) : (length(max(abs(q) - (size_xy - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y))), 0.0)) + min(max(abs(q).x - (size_xy.x - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y))), abs(q).y - (size_xy.y - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y)))), 0.0) - clamp(corner_r, 0.0, min(size_xy.x, size_xy.y)));
    }
    else if(t<18.5){ // Bezier Curve (3D)
        vec3 A = vec3(0.0); vec3 B = extra.xyz; vec3 C = gyro_p.xyz; float r1 = extra.w; float r2 = gyro_p.w;
        vec3 a = B - A; vec3 b = A - 2.0*B + C; vec3 c = a * 2.0; vec3 d = A - p_s;
        float kk = 1.0 / max(dot(b,b), 0.00001);
        float kx = kk * dot(a,b); float ky = kk * (2.0*dot(a,a) + dot(d,b)) / 3.0; float kz = kk * dot(d,a);
        float p_val = ky - kx*kx; float p3 = p_val*p_val*p_val; float q_val = kx*(2.0*kx*kx - 3.0*ky) + kz;
        float h = q_val*q_val + 4.0*p3;
        float res_t = 0.0;
        if (h >= 0.0) {
            // 実数解は (-q + sqrt(h))/2 と (-q - sqrt(h))/2
            float h_sqrt = sqrt(h); vec2 x = (vec2(-q_val, -q_val) + vec2(h_sqrt, -h_sqrt)) * 0.5;
            vec2 uv = sign(x) * pow(abs(x), vec2(1.0/3.0));
            res_t = clamp(uv.x + uv.y - kx, 0.0, 1.0);
        } else {
            float z = sqrt(-p_val); float v = acos(clamp(q_val / (p_val*z*2.0), -1.0, 1.0)) / 3.0;
            float m = cos(v); float n = sin(v) * 1.732050808;
            vec2 t_cand = clamp(vec2(m+m, -m-n)*z - vec2(kx), vec2(0.0), vec2(1.0));
            vec3 pos1 = A + (c + b*t_cand.x)*t_cand.x - p_s; vec3 pos2 = A + (c + b*t_cand.y)*t_cand.y - p_s;
            res_t = (dot(pos1, pos1) < dot(pos2, pos2)) ? t_cand.x : t_cand.y;
        }
        vec3 pos_on_curve = A + (c + b*res_t)*res_t - p_s;
        res_d = length(pos_on_curve) - mix(r1, r2, res_t);
    }
    
    if (shell_thickness > 0.0) {
        res_d = abs(res_d) - shell_thickness;
    }
    
    return res_d * s_min;
}

float sdf_hash3(vec3 p){
    vec3 q = fract(p * 0.1031);
    q += dot(q, q.yzx + 33.33);
    return fract((q.x + q.y) * q.z);
}
float sdf_noise3(vec3 p){
    vec3 i = floor(p); vec3 f = fract(p);
    vec3 u = f * f * (3.0 - 2.0 * f);
    return mix(mix(mix(sdf_hash3(i + vec3(0,0,0)), sdf_hash3(i + vec3(1,0,0)), u.x),
                   mix(sdf_hash3(i + vec3(0,1,0)), sdf_hash3(i + vec3(1,1,0)), u.x), u.y),
               mix(mix(sdf_hash3(i + vec3(0,0,1)), sdf_hash3(i + vec3(1,0,1)), u.x),
                   mix(sdf_hash3(i + vec3(0,1,1)), sdf_hash3(i + vec3(1,1,1)), u.x), u.y), u.z);
}

vec4 map_impl(vec3 p){
    float d=1e10; vec3 col=vec3(1.0); float met=0.0, rou=0.5; bool sceneInit=false;
    float layerD=1e10; vec3 layerCol=vec3(1.0); float layerMet=0.0, layerRou=0.5; bool layerInit=false;
    float currentLayerId=0.0; float layerK=0.0001; float layerProfile=0.0; float layerCS=0.0;
    vec3 q_dom = abs(p) - vec3(domainSize * 0.5);
    float d_clip = length(max(q_dom, 0.0)) + min(max(q_dom.x, max(q_dom.y, q_dom.z)), 0.0);
    
    for(int i=0; i<primCount; i++){
        vec4 c0 = texelFetch(primTex,ivec2(0,i),0); // center_and_shape
        vec4 c1 = texelFetch(primTex,ivec2(1,i),0); // rotation
        vec4 c2 = texelFetch(primTex,ivec2(2,i),0); // size_and_op
        vec4 c3 = texelFetch(primTex,ivec2(3,i),0); // params [radius, smoothness, metallic, roughness]
        vec4 c4 = texelFetch(primTex,ivec2(4,i),0); // noise_params [str, scale, r, g]
        vec4 c5 = texelFetch(primTex,ivec2(5,i),0); // color_b_and_extra [b, blend_profile, chamfer_smooth, layer_id]
        vec4 ld1 = texelFetch(primTex,ivec2(6,i),0); 
        vec4 ld2 = texelFetch(primTex,ivec2(7,i),0); 
        vec4 ld3 = texelFetch(primTex,ivec2(8,i),0); 
        vec4 ld4 = texelFetch(primTex,ivec2(9,i),0); 
        vec4 extra = texelFetch(primTex,ivec2(10,i),0); 
        vec4 dd1 = texelFetch(primTex,ivec2(11,i),0); 
        vec4 dd2 = texelFetch(primTex,ivec2(12,i),0); 
        vec4 dd3 = texelFetch(primTex,ivec2(13,i),0); 
        vec4 dd4 = texelFetch(primTex,ivec2(14,i),0); 
        vec4 mod_p = texelFetch(primTex,ivec2(15,i),0); 
        vec4 gyro_p = texelFetch(primTex,ivec2(16,i),0);
        vec4 layer_p = texelFetch(primTex,ivec2(17,i),0); // [layer_smoothness, layer_blend_profile, layer_chamfer_smooth, unused] 
        
        vec3 lp = q_rotate(p - c0.xyz, q_conj(c1));
        float k=max(c3.y, 0.0001);
        float op=c2.w;
        vec3 color = vec3(c4.zw, c5.x);
        
        uint packed1 = uint(ld1.x);
        uint flags = packed1 & 0xFFu;
        
        float accum_idx = 0.0;

        // 1. Mirror
        if((flags & 1u) != 0u){
            uint mask = (packed1 >> 8u) & 0xFu;
            float offset = ld1.y;
            if((mask & 1u) != 0u) lp.x = abs(lp.x) - offset;
            if((mask & 2u) != 0u) lp.y = abs(lp.y) - offset;
            if((mask & 4u) != 0u) lp.z = abs(lp.z) - offset;
        }

        // 2. Radial / Spiral
        if((flags & 2u) != 0u || (flags & 4u) != 0u){
            float radial_count = float((packed1 >> 12u) & 0xFFu);
            uint axis = (packed1 >> 20u) & 3u;
            float angle = 6.2831853 / max(radial_count, 1.0);
            float radius = ld1.z;
            float spiral_h = ld1.w; // Engine side alignment
            
            vec3 p_rot = lp;
            if (axis == 0u) { // X axis
                float r = length(p_rot.yz);
                float a = atan(p_rot.z, p_rot.y) + angle * 0.5;
                float step_idx = floor(a / angle);
                a = (fract(a / angle) - 0.5) * angle;
                p_rot.y = r * cos(a) - radius;
                p_rot.z = r * sin(a);
                p_rot.x -= spiral_h * step_idx; // Spiral pitch
                accum_idx += step_idx;
            } else if (axis == 1u) { // Y axis
                float r = length(p_rot.xz);
                float a = atan(p_rot.x, p_rot.z) + angle * 0.5;
                float step_idx = floor(a / angle);
                a = (fract(a / angle) - 0.5) * angle;
                p_rot.z = r * cos(a) - radius;
                p_rot.x = r * sin(a);
                p_rot.y -= spiral_h * step_idx;
                accum_idx += step_idx;
            } else { // Z axis
                float r = length(p_rot.xy);
                float a = atan(p_rot.y, p_rot.x) + angle * 0.5;
                float step_idx = floor(a / angle);
                a = (fract(a / angle) - 0.5) * angle;
                p_rot.x = r * cos(a) - radius;
                p_rot.y = r * sin(a);
                p_rot.z -= spiral_h * step_idx;
                accum_idx += step_idx;
            }
            lp = p_rot;
        }

        // 3. Grid
        if((flags & 8u) != 0u){
            float g_p = ld2.z;
            float cz = floor(g_p / 10000.0);
            float cy = floor((g_p - cz * 10000.0) / 100.0);
            float cx = g_p - cz * 10000.0 - cy * 100.0;
            vec3 g_spacing = vec3(ld2.w, ld3.x, ld3.y);
            vec3 g_counts = vec3(cx, cy, cz);
            vec3 g_limit = (g_counts - vec3(1.0)) * 0.5;
            vec3 g_idx = round(lp / g_spacing);
            vec3 g_actual = clamp(g_idx, -floor(g_limit), ceil(g_limit));
            lp = lp - g_spacing * g_actual;
            accum_idx += g_actual.x + g_actual.y + g_actual.z;
        }

        if((flags & 32u) != 0u){
            float seed = ld2.x; float strength = ld2.y;
            lp += (vec3(sdf_hash3(lp+seed), sdf_hash3(lp+seed+1.0), sdf_hash3(lp+seed+2.0)) - 0.5) * strength;
        }

        vec3 i_rot = vec3(ld3.z, ld3.w, ld4.x);
        vec3 s_rot = vec3(ld4.y, ld4.z, ld4.w);
        lp = q_rotate(lp, q_from_euler(i_rot + s_rot * accum_idx));

        // --- V15: Dynamic Deform Stack ---
        uint packed_meta = uint(dd1.x);
        float df_bound_scale = 1.0;
        vec4 slot_data[4];
        slot_data[0] = vec4(dd1.y, dd1.z, dd1.w, dd2.x);
        slot_data[1] = vec4(dd2.y, dd2.z, dd2.w, dd3.x);
        slot_data[2] = vec4(dd3.y, dd3.z, dd3.w, dd4.x);
        slot_data[3] = vec4(dd4.y, dd4.z, dd4.w, 0.0);

        for(int si = 0; si < 4; si++){
            uint slot_info = (packed_meta >> uint(si * 6)) & 0x3Fu;
            uint d_type = slot_info & 0xFu;
            uint d_axis = (slot_info >> 4u) & 0x3u;
            vec4 sd = slot_data[si];
            
            if(d_type == 0u) continue;
            
            if(d_type == 1u){  // Elongate
                vec3 h = sd.xyz;
                lp = lp - clamp(lp, -h, h);
            }
            else if(d_type == 2u){  // Bend
                float angle = sd.x;
                float ox = sd.y; float oy = sd.z; float oz = sd.w;
                if(abs(angle) > 0.0001){
                    float R = 1.0 / angle;
                    if(d_axis == 2u){
                        float dx = lp.x - ox; float dy = lp.y - oy;
                        float radial_y = R - dy;
                        float theta = atan(dx * sign(R), radial_y * sign(R));
                        float r = length(vec2(radial_y, dx)) * sign(R);
                        lp.y = oy + R - r; lp.x = ox + (theta / angle);
                    } else if(d_axis == 1u){
                        float dz = lp.z - oz; float dx = lp.x - ox;
                        float radial_x = R - dx;
                        float theta = atan(dz * sign(R), radial_x * sign(R));
                        float r = length(vec2(radial_x, dz)) * sign(R);
                        lp.x = ox + R - r; lp.z = oz + (theta / angle);
                    } else if(d_axis == 0u){
                        float dz = lp.z - oz; float dy = lp.y - oy;
                        float radial_y = R - dy;
                        float theta = atan(dz * sign(R), radial_y * sign(R));
                        float r = length(vec2(radial_y, dz)) * sign(R);
                        lp.y = oy + R - r; lp.z = oz + (theta / angle);
                    }
                    vec3 abs_c2 = abs(c2.xyz);
                    float max_s = max(abs_c2.x, max(abs_c2.y, abs_c2.z));
                    df_bound_scale *= 1.0 / sqrt(1.0 + (max_s * angle) * (max_s * angle));
                }
            }
            else if(d_type == 3u){  // Twist
                float angle = sd.x;
                float ox = sd.y; float oy = sd.z; float oz = sd.w;
                if(d_axis == 2u){
                    float a = angle * (lp.z - oz);
                    float c = cos(a); float s = sin(a);
                    float dx = lp.x - ox; float dy = lp.y - oy;
                    lp.x = ox + c * dx + s * dy; lp.y = oy - s * dx + c * dy;
                } else if(d_axis == 1u){
                    float a = angle * (lp.y - oy);
                    float c = cos(a); float s = sin(a);
                    float dz = lp.z - oz; float dx = lp.x - ox;
                    lp.z = oz + c * dz + s * dx; lp.x = ox - s * dz + c * dx;
                } else if(d_axis == 0u){
                    float a = angle * (lp.x - ox);
                    float c = cos(a); float s = sin(a);
                    float dy = lp.y - oy; float dz = lp.z - oz;
                    lp.y = oy + c * dy + s * dz; lp.z = oz - s * dy + c * dz;
                }
                vec3 abs_c2 = abs(c2.xyz);
                float max_s = max(abs_c2.x, max(abs_c2.y, abs_c2.z));
                df_bound_scale *= 1.0 / sqrt(1.0 + (max_s * angle) * (max_s * angle));
            }
            else if(d_type == 4u){  // Taper
                float factor = sd.x;
                float ox = sd.y; float oy = sd.z; float oz = sd.w;
                float scale = 1.0;
                if(d_axis == 2u){
                    scale = max(0.1, 1.0 + factor * (lp.z - oz));
                    lp.x = ox + (lp.x - ox) / scale; lp.y = oy + (lp.y - oy) / scale;
                } else if(d_axis == 1u){
                    scale = max(0.1, 1.0 + factor * (lp.y - oy));
                    lp.x = ox + (lp.x - ox) / scale; lp.z = oz + (lp.z - oz) / scale;
                } else if(d_axis == 0u){
                    scale = max(0.1, 1.0 + factor * (lp.x - ox));
                    lp.y = oy + (lp.y - oy) / scale; lp.z = oz + (lp.z - oz) / scale;
                }
                df_bound_scale *= min(1.0, scale);
            }
        }

        float dd = sdf_eval_shape(lp, c0.w, c2.xyz, c3.x, extra, mod_p, gyro_p);
        dd *= df_bound_scale;
        if(c4.x > 0.0) dd += (sdf_noise3(lp * c4.y) * 2.0 - 1.0) * c4.x;

        float layerId = floor(c5.w + 0.5);
        if(layerId > 0.5){
            if(abs(currentLayerId - layerId) > 0.5){
                if(currentLayerId > 0.5 && layerInit){
                    if(!sceneInit){
                        d=layerD; col=layerCol; met=layerMet; rou=layerRou; sceneInit=true;
                    }else{
                        float h=clamp(0.5+0.5*(d-layerD)/layerK, 0.0, 1.0);
                        d=mix(d,layerD,h)-layerK*h*(1.0-h);
                        col=mix(col,layerCol,h); met=mix(met,layerMet,h); rou=mix(rou,layerRou,h);
                    }
                }
                currentLayerId=layerId; layerD=1e10; layerCol=vec3(1.0); layerMet=0.0; layerRou=0.5; layerInit=false;
                // 合流の強さは仕切りの設定から。プリミティブ自身の smoothness ではない
                layerK=max(layer_p.x, 0.0001); layerProfile=layer_p.y; layerCS=layer_p.z;
            }
            if(!layerInit){
                if(op > 0.5) layerD = 1e10; else layerD = dd;
                layerCol=color; layerMet=c3.z; layerRou=c3.w; layerInit=true;
            }else{
                float h=0.0;
                if(op<0.5){
                    h=clamp(0.5+0.5*(layerD-dd)/k, 0.0, 1.0);
                    layerD=mix(layerD,dd,h)-k*h*(1.0-h);
                    layerCol=mix(layerCol,color,h); layerMet=mix(layerMet,c3.z,h); layerRou=mix(layerRou,c3.w,h);
                } else if(op<1.5){
                    h=clamp(0.5+0.5*(layerD+dd)/k, 0.0, 1.0);
                    layerD=mix(-dd,layerD,h)+k*h*(1.0-h);
                    layerCol=mix(color,layerCol,h); layerMet=mix(c3.z,layerMet,h); layerRou=mix(layerRou,c3.w,h);
                } else {
                    h=clamp(0.5+0.5*(dd-layerD)/k, 0.0, 1.0);
                    layerD=mix(layerD,dd,h)+k*h*(1.0-h);
                    layerCol=mix(layerCol,color,h); layerMet=mix(layerMet,c3.z,h); layerRou=mix(layerRou,c3.w,h);
                }
            }
        }else{
            if(currentLayerId > 0.5 && layerInit){
                if(!sceneInit){
                    d=layerD; col=layerCol; met=layerMet; rou=layerRou; sceneInit=true;
                }else{
                    float h=clamp(0.5+0.5*(d-layerD)/layerK, 0.0, 1.0);
                    d=mix(d,layerD,h)-layerK*h*(1.0-h);
                    col=mix(col,layerCol,h); met=mix(met,layerMet,h); rou=mix(rou,layerRou,h);
                }
                currentLayerId=0.0; layerInit=false;
            }
            if(!sceneInit){
                if(op > 0.5) d = 1e10; else d = dd;
                col=color; met=c3.z; rou=c3.w; sceneInit=true;
            }else{
                float h=0.0;
                if(op<0.5){
                    h=clamp(0.5+0.5*(d-dd)/k, 0.0, 1.0);
                    d=mix(d,dd,h)-k*h*(1.0-h);
                    col=mix(col,color,h); met=mix(met,c3.z,h); rou=mix(rou,c3.w,h);
                } else if(op<1.5){
                    h=clamp(0.5+0.5*(d+dd)/k, 0.0, 1.0);
                    d=mix(-dd,d,h)+k*h*(1.0-h);
                    col=mix(color,col,h); met=mix(c3.z,met,h); rou=mix(rou,c3.w,h);
                } else {
                    h=clamp(0.5+0.5*(dd-d)/k, 0.0, 1.0);
                    d=mix(d,dd,h)+k*h*(1.0-h);
                    col=mix(col,color,h); met=mix(met,c3.z,h); rou=mix(rou,c3.w,h);
                }
            }
        }
    }
    if(currentLayerId > 0.5 && layerInit){
        if(!sceneInit){
            d=layerD; col=layerCol; met=layerMet; rou=layerRou;
        }else{
            float h=clamp(0.5+0.5*(d-layerD)/layerK, 0.0, 1.0);
            d=mix(d,layerD,h)-layerK*h*(1.0-h);
            col=mix(col,layerCol,h); met=mix(met,layerMet,h); rou=mix(rou,layerRou,h);
        }
    }
    return vec4(col, max(d, d_clip));
}

vec4 map(vec3 p){
    vec3 p_sym = p;
    if ((symmetryFlags & 1) != 0) { p_sym.x = abs(p_sym.x); }
    if ((symmetryFlags & 2) != 0) { p_sym.y = abs(p_sym.y); }
    if ((symmetryFlags & 4) != 0) { p_sym.z = abs(p_sym.z); }
    return map_impl(p_sym);
}

void main(){
    vec2 ndc=v_uv*2.0-1.0;
    vec4 nr_l = invProjViewLocal * vec4(ndc, -1.0, 1.0);
    vec4 fr_l = invProjViewLocal * vec4(ndc, 1.0, 1.0);
    nr_l /= nr_l.w;
    fr_l /= fr_l.w;
    
    vec3 ro = nr_l.xyz;
    vec3 rd = normalize(fr_l.xyz - nr_l.xyz);
    
    float t=0.0;
    for(int i=0; i<maxSteps; i++){
        vec3 p=ro+rd*t;vec4 r=map(p);
        if(r.a<0.001){
            vec2 e=vec2(0.002,0.0);
            vec3 n;
            // V16.1.1: 法線は通常6タップの中央差分だが、視点操作/変形の最中は
            // 3タップの前方差分に切り替える（map()の呼び出しを半減させる）。
            // 手前の r.a を基準値として再利用するため追加コストは3回のみ。
            if (fastNormal != 0) {
                n=normalize(vec3(map(p+e.xyy).a-r.a, map(p+e.yxy).a-r.a, map(p+e.yyx).a-r.a));
            } else {
                n=normalize(vec3(map(p+e.xyy).a-map(p-e.xyy).a,map(p+e.yxy).a-map(p-e.yxy).a,map(p+e.yyx).a-map(p-e.yyx).a));
            }
            float df=max(0.0,dot(n,normalize(vec3(1,2,1.5)))),rm=pow(1.0-max(0.0,dot(n,-rd)),3.0);
            fragColor=vec4(r.rgb*(df*0.65+0.15)+rm*0.25,0.85);return;
        }t+=r.a*0.95;if(t>10000.0)break;
    }discard;
}
'''

_shader = None
_shader_failed = False

def get_shader():
    """テクスチャベースのシェーダーを構築"""
    global _shader, _shader_failed
    if _shader is not None: return _shader
    if _shader_failed: return None
    try:
        info = gpu.types.GPUShaderCreateInfo()
        info.vertex_in(0, 'VEC3', "pos")
        
        info.push_constant('MAT4', "invProjViewLocal")
        info.push_constant('FLOAT', "domainSize")
        info.push_constant('INT', "primCount")
        info.push_constant('INT', "symmetryFlags")
        info.push_constant('INT', "maxSteps")
        info.push_constant('INT', "fastNormal")
        
        info.sampler(0, 'FLOAT_2D', "primTex")
        info.fragment_out(0, 'VEC4', "fragColor")
        iface = gpu.types.GPUStageInterfaceInfo("sdf_iface")
        iface.smooth('VEC2', "v_uv")
        info.vertex_out(iface)
        info.vertex_source(VERT_SRC)
        info.fragment_source(FRAG_SRC)
        _shader = gpu.shader.create_from_info(info)
        print("SDF Raymarching shader compiled successfully!")
        return _shader
    except Exception as e:
        print(f"SDF Shader Compilation Error: {e}")
        import traceback; traceback.print_exc()
        _shader_failed = True
        return None

BLIT_VERT_SRC = '''
void main() {
    blit_uv = pos.xy * 0.5 + 0.5;
    // 深度はレイマーチ本体(VERT_SRC)と同じ 0.999 に揃える。
    // 0.0 にすると深度バッファへ最手前の値を書き込み、後続の描画を隠しうる。
    gl_Position = vec4(pos.xy, 0.999, 1.0);
}
'''

BLIT_FRAG_SRC = '''
void main() {
    fragColor = texture(image, blit_uv);
}
'''

_blit_shader = None
_blit_shader_failed = False


def get_blit_shader():
    """低解像度オフスクリーンを画面へ等倍転送するためのパススルーシェーダ。

    V16.1.1: 組み込みの 'IMAGE' シェーダは ModelViewProjectionMatrix を掛けるため、
    POST_VIEW の描画ハンドラ内で使うと、画面全体を覆うつもりのクアッドが
    3D空間内の小さな板として描かれてしまう。レイマーチ本体の頂点シェーダと同様、
    NDCをそのまま出力するパススルーを自前で用意する。
    """
    global _blit_shader, _blit_shader_failed
    if _blit_shader is not None:
        return _blit_shader
    if _blit_shader_failed:
        return None
    try:
        info = gpu.types.GPUShaderCreateInfo()
        info.vertex_in(0, 'VEC3', "pos")
        info.sampler(0, 'FLOAT_2D', "image")
        info.fragment_out(0, 'VEC4', "fragColor")
        iface = gpu.types.GPUStageInterfaceInfo("sdf_blit_iface")
        iface.smooth('VEC2', "blit_uv")
        info.vertex_out(iface)
        info.vertex_source(BLIT_VERT_SRC)
        info.fragment_source(BLIT_FRAG_SRC)
        _blit_shader = gpu.shader.create_from_info(info)
        print("SDF Blit shader compiled successfully!")
        return _blit_shader
    except Exception as e:
        print(f"SDF Blit Shader Compilation Error: {e}")
        import traceback; traceback.print_exc()
        _blit_shader_failed = True
        return None


def clear_shader():
    global _shader, _shader_failed, _blit_shader, _blit_shader_failed
    _shader = None
    _shader_failed = False
    _blit_shader = None
    _blit_shader_failed = False
