fn apply_profile_union(d1: f32, d2: f32, profile: u32, k: f32, cs: f32) -> f32 {
    switch (profile) {
        case 1u: { let h = max(k - abs(d1 - d2), 0.0) / k; return min(d1, d2) - h * h * h * k * 0.166666; }
        case 2u: { return -k * log2(max(exp2(-d1 / k) + exp2(-d2 / k), 1e-10)); }
        case 3u: { let h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0); return mix(d2, d1, h) - k * h * h * (1.0 - h) * (1.0 - h) * 2.0; }
        case 4u: {
            let ch = min(min(d1, d2), (d1 + d2 - k) * 0.70710678);
            if (cs > 0.0) { let h = clamp(0.5 + 0.5 * (ch - min(d1, d2)) / cs, 0.0, 1.0); return mix(ch, min(d1, d2), h) - cs * h * (1.0 - h); }
            return ch;
        }
        default: { let h = clamp(0.5 + 0.5 * (d2 - d1) / k, 0.0, 1.0); return mix(d2, d1, h) - k * h * (1.0 - h); }
    }
}
@compute @workgroup_size(1) fn main() {}
