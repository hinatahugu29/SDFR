use nalgebra::Vector3;
use crate::math::lerp;

fn hash3_rust(p: Vector3<f32>) -> f32 {
    let x = (p.x * 0.1031).fract();
    let y = (p.y * 0.1031).fract();
    let z = (p.z * 0.1031).fract();
    let dot = x * (x + 33.33) + y * (z + 33.33) + z * (y + 33.33);
    ((x + y) * z + dot).fract()
}

fn noise3_rust(p: Vector3<f32>) -> f32 {
    let i = Vector3::new(p.x.floor(), p.y.floor(), p.z.floor());
    let f = Vector3::new(p.x.fract(), p.y.fract(), p.z.fract());
    let u = f.component_mul(&f).component_mul(&(Vector3::new(3.0, 3.0, 3.0) - 2.0 * f));
    
    let h000 = hash3_rust(i + Vector3::new(0.0, 0.0, 0.0));
    let h100 = hash3_rust(i + Vector3::new(1.0, 0.0, 0.0));
    let h010 = hash3_rust(i + Vector3::new(0.0, 1.0, 0.0));
    let h110 = hash3_rust(i + Vector3::new(1.0, 1.0, 0.0));
    let h001 = hash3_rust(i + Vector3::new(0.0, 0.0, 1.0));
    let h101 = hash3_rust(i + Vector3::new(1.0, 0.0, 1.0));
    let h011 = hash3_rust(i + Vector3::new(0.0, 1.0, 1.0));
    let h111 = hash3_rust(i + Vector3::new(1.0, 1.0, 1.0));

    let res = lerp(lerp(lerp(h000, h100, u.x), lerp(h010, h110, u.x), u.y),
                   lerp(lerp(h001, h101, u.x), lerp(h011, h111, u.x), u.y), u.z);
    res
}

