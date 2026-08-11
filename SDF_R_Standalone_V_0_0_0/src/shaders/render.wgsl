struct Camera {
    view_proj: mat4x4<f32>,
    view_inv: mat4x4<f32>,
    proj_inv: mat4x4<f32>,
    camera_pos: vec4<f32>,
    screen_size: vec4<f32>,
}

@group(0) @binding(14) var<uniform> camera: Camera;

struct VertexOutput {
    @builtin(position) position: vec4<f32>,
    @location(0) uv: vec2<f32>,
}

@vertex
fn vs_main(@builtin(vertex_index) vertex_index: u32) -> VertexOutput {
    var out: VertexOutput;
    let x = f32(i32(vertex_index == 1u) * 4 - 1);
    let y = f32(i32(vertex_index == 2u) * 4 - 1);
    out.uv = vec2<f32>(x, y) * 0.5 + 0.5;
    out.position = vec4<f32>(x, y, 0.0, 1.0);
    return out;
}

struct SceneResult {
    dist: f32,
    color: vec3<f32>,
    metallic: f32,
    roughness: f32,
    emission: f32,
}

fn get_scene(p: vec3<f32>) -> SceneResult {
    var res: SceneResult;
    res.dist = 1e10;
    res.color = vec3<f32>(0.5);
    res.metallic = 0.0;
    res.roughness = 0.5;
    res.emission = 0.0;
    
    var first = true;
    let num = min(config.num_primitives, 128u); 
    for (var i = 0u; i < num; i++) {
        let prim = primitives[i];
        let op = u32(prim.size_and_op.w);
        if (op == 15u) { continue; } // Hidden
        
        let lp_layout = evaluate_layout(p, prim, 0.0);
        let d = evaluate_shape(lp_layout, prim);
        
        let k = max(prim.params.y, 0.001); // Smoothness
        let col = vec3<f32>(prim.noise_params.z, prim.noise_params.w, prim.color_b_and_extra.x);
        let met = prim.params.z;
        let roug = prim.params.w;
        
        if (first) {
            res.dist = d;
            res.color = col;
            res.metallic = met;
            res.roughness = roug;
            res.emission = prim.color_b_and_extra.y;
            first = false;
        } else {
            // Boolean color blending based on contribution
            let h_union = clamp(0.5 + 0.5 * (d - res.dist) / k, 0.0, 1.0);
            let h_sub = clamp(0.5 - 0.5 * (res.dist + d) / k, 0.0, 1.0);
            let h_int = clamp(0.5 - 0.5 * (res.dist - d) / k, 0.0, 1.0);

            switch (op) {
                case 0u: { // Union
                    res.dist = mix(d, res.dist, h_union) - k * h_union * (1.0 - h_union);
                    let influence = prim.color_b_and_extra.z;
                    let weight = h_union + (1.0 - h_union) * (1.0 - influence);
                    res.color = mix(col, res.color, weight);
                    res.metallic = mix(met, res.metallic, weight);
                    res.roughness = mix(roug, res.roughness, weight);
                    res.emission = mix(prim.color_b_and_extra.y, res.emission, weight);
                }
                case 1u: { // Subtract
                    res.dist = mix(res.dist, -d, h_sub) + k * h_sub * (1.0 - h_sub);
                    let influence = prim.color_b_and_extra.z;
                    res.color = mix(res.color, col, h_sub * influence); 
                }
                case 2u: { // Intersect
                    res.dist = mix(res.dist, d, h_int) + k * h_int * (1.0 - h_int);
                    let influence = prim.color_b_and_extra.z;
                    let weight = (1.0 - h_int) * influence;
                    res.color = mix(res.color, col, weight);
                    res.metallic = mix(res.metallic, met, weight);
                    res.roughness = mix(res.roughness, roug, weight);
                    res.emission = mix(res.emission, prim.color_b_and_extra.y, weight);
                }
                default: {}
            }
        }
    }
    return res;
}

fn get_scene_dist(p: vec3<f32>) -> f32 {
    return get_scene(p).dist;
}

fn get_soft_shadow(ro: vec3<f32>, rd: vec3<f32>, mint: f32, maxt: f32, k: f32) -> f32 {
    var res = 1.0;
    var t = mint;
    for (var i = 0i; i < 32; i++) {
        let h = get_scene_dist(ro + rd * t);
        if (h < 0.001) { return 0.0; }
        res = min(res, k * h / t);
        t += clamp(h, 0.01, 0.5);
        if (t > maxt) { break; }
    }
    return clamp(res, 0.0, 1.0);
}

fn get_ao(p: vec3<f32>, n: vec3<f32>, strength: f32) -> f32 {
    var occ = 0.0;
    var sca = 1.0;
    for (var i = 1i; i < 6; i++) {
        let h = 0.01 + 0.12 * f32(i) / 5.0;
        let d = get_scene_dist(p + n * h);
        occ += (h - d) * sca;
        sca *= 0.95;
    }
    return clamp(1.0 - strength * occ, 0.0, 1.0);
}

fn get_normal(p: vec3<f32>) -> vec3<f32> {
    let e = vec2<f32>(0.0005, 0.0);
    return normalize(vec3<f32>(
        get_scene_dist(p + e.xyy) - get_scene_dist(p - e.xyy),
        get_scene_dist(p + e.yxy) - get_scene_dist(p - e.yxy),
        get_scene_dist(p + e.yyx) - get_scene_dist(p - e.yyx)
    ));
}

fn get_selected_dist(p: vec3<f32>) -> f32 {
    if (config.selected_idx < 0) { return 1e10; }
    let prim = primitives[config.selected_idx];
    let lp = evaluate_layout(p, prim, 0.0);
    return evaluate_shape(lp, prim);
}

@fragment
fn fs_main(in: VertexOutput) -> @location(0) vec4<f32> {
    let uv = in.uv * 2.0 - 1.0;
    let ray_target = camera.proj_inv * vec4<f32>(uv.x, -uv.y, 1.0, 1.0);
    let ray_dir = normalize((camera.view_inv * vec4<f32>(normalize(ray_target.xyz / ray_target.w), 0.0)).xyz);
    let ray_origin = camera.camera_pos.xyz;

    var t = 0.0;
    var p = ray_origin;
    var res: SceneResult;
    var hit = false;
    var min_d_selected = 1e10;

    for (var i = 0i; i < 128; i++) {
        p = ray_origin + ray_dir * t;
        res = get_scene(p);
        
        // Track distance to selected object for glow
        let d_sel = get_selected_dist(p);
        min_d_selected = min(min_d_selected, d_sel);

        if (res.dist < 0.001) {
            hit = true;
            break;
        }
        
        // Adaptive step size: slow down near selected object for smooth glow
        var step = res.dist;
        if (d_sel < 1.0) {
            step = min(step, 0.05); // Limit step size to capture smooth glow
        }
        t += step;
        
        if (t > 100.0) { break; }
    }

    var final_color = vec3<f32>(0.0);

    if (hit) {
        let normal = get_normal(p);
        let view_dir = normalize(ray_origin - p);
        let light_dir = normalize(vec3<f32>(1.0, 2.0, 1.0)); // Slightly higher light
        let half_dir = normalize(light_dir + view_dir);
        
        // Environment / AO
        let ao = get_ao(p, normal, config.ao_strength);
        let env = vec3<f32>(0.2, 0.25, 0.3) * config.env_intensity * ao; // Blue-ish sky
        
        let soft_shadow = get_soft_shadow(p + normal * 0.01, light_dir, 0.01, 10.0, config.shadow_softness);
        let diff = max(dot(normal, light_dir), 0.0) * soft_shadow;
        let spec = pow(max(dot(normal, half_dir), 0.0), mix(10.0, 250.0, 1.0 - res.roughness)) * soft_shadow * res.metallic;
        
        final_color = res.color * (diff * 0.8 + env) + spec;
        final_color += res.color * res.emission * 3.0; // Boost emission
    } else {
        // Background and Grid
        let show_grid = (config.symmetry & 256u) != 0u;
        let show_axes = (config.symmetry & 512u) != 0u;
        
        let is_below = ray_origin.y < 0.0;
        var bg_color = config.bg_color;
        
        if (show_grid || show_axes) && ((!is_below && ray_dir.y < 0.0) || (is_below && ray_dir.y > 0.0)) {
            let t_ground = -ray_origin.y / ray_dir.y;
            if (t_ground > 0.0 && t_ground < 100.0) {
                let p_ground = ray_origin + ray_dir * t_ground;
                var floor_col = config.floor_color;
                
                // Ground Shadow
                let ground_shadow = get_soft_shadow(p_ground + vec3<f32>(0.0, 0.01, 0.0), normalize(vec3<f32>(1.0, 2.0, 1.0)), 0.01, 10.0, config.shadow_softness * 0.5);
                floor_col *= mix(0.3, 1.0, ground_shadow);

                if (show_grid) {
                    let grid_size = 1.0;
                    let a_grid = abs(fract(p_ground.xz / grid_size + 0.5) - 0.5) / (fwidth(p_ground.xz) + 0.001);
                    let grid_line = 1.0 - smoothstep(0.0, 1.5, min(a_grid.x, a_grid.y));
                    floor_col = mix(floor_col, vec3<f32>(0.4), grid_line * ground_shadow);
                }
                if (show_axes) {
                    let x_axis = 1.0 - smoothstep(0.0, 0.05 / (t_ground * 0.1 + 1.0), abs(p_ground.z));
                    floor_col = mix(floor_col, vec3<f32>(0.6, 0.1, 0.1), x_axis * ground_shadow);
                    let z_axis = 1.0 - smoothstep(0.0, 0.05 / (t_ground * 0.1 + 1.0), abs(p_ground.x));
                    floor_col = mix(floor_col, vec3<f32>(0.1, 0.1, 0.6), z_axis * ground_shadow);
                }
                let fade = 1.0 - smoothstep(15.0, 80.0, t_ground);
                bg_color = mix(config.bg_color, floor_col, fade);
            }
        }
        final_color = bg_color;
    }

    // Selection Glow Overlay
    let show_selection_highlight = (config.symmetry & 1024u) != 0u;
    if (config.selected_idx >= 0 && show_selection_highlight) {
        let glow = exp(-max(min_d_selected, 0.0) * 4.0);
        let rim = smoothstep(0.03, 0.0, abs(min_d_selected)) * 0.5;
        let selection_col = vec3<f32>(0.0, 1.0, 0.85); // Vibrant Cyan
        
        // Add a bit of pulse or intensity control here if needed
        final_color = mix(final_color, selection_col, glow * 0.3 + rim);
    }

    // Contrast and Gamma correction
    final_color = pow(final_color, vec3<f32>(1.0 / 2.2));
    
    return vec4<f32>(final_color, 1.0);
}
