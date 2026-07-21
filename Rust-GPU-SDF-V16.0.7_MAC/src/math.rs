use nalgebra::{Vector3, UnitQuaternion};

/// 三角形と点の最短距離を計算
fn dot2(v: Vector3<f32>) -> f32 { v.dot(&v) }

fn dist_to_triangle(p: Vector3<f32>, v0: Vector3<f32>, v1: Vector3<f32>, v2: Vector3<f32>) -> f32 {
    let v10 = v1 - v0; let p0 = p - v0;
    let v21 = v2 - v1; let p1 = p - v1;
    let v02 = v0 - v2; let p2 = p - v2;
    let nor = v10.cross(&v02);

    let sign = v10.cross(&nor).dot(&p0).signum() +
                v21.cross(&nor).dot(&p1).signum() +
                v02.cross(&nor).dot(&p2).signum() < 2.0;

    if sign {
        let d1 = dot2(v10 * (v10.dot(&p0) / dot2(v10)).clamp(0.0, 1.0) - p0);
        let d2 = dot2(v21 * (v21.dot(&p1) / dot2(v21)).clamp(0.0, 1.0) - p1);
        let d3 = dot2(v02 * (v02.dot(&p2) / dot2(v02)).clamp(0.0, 1.0) - p2);
        d1.min(d2.min(d3)).sqrt()
    } else {
        (nor.dot(&p0).powi(2) / dot2(nor)).sqrt()
    }
}

fn rotate_aabb(min: Vector3<f32>, max: Vector3<f32>, q: UnitQuaternion<f32>) -> (Vector3<f32>, Vector3<f32>) {
    let corners = [
        Vector3::new(min.x, min.y, min.z),
        Vector3::new(max.x, min.y, min.z),
        Vector3::new(min.x, max.y, min.z),
        Vector3::new(max.x, max.y, min.z),
        Vector3::new(min.x, min.y, max.z),
        Vector3::new(max.x, min.y, max.z),
        Vector3::new(min.x, max.y, max.z),
        Vector3::new(max.x, max.y, max.z),
    ];
    let mut new_min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
    let mut new_max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
    for c in corners.iter() {
        let p = q * c;
        new_min = new_min.inf(&p);
        new_max = new_max.sup(&p);
    }
    (new_min, new_max)
}

fn lerp(a: f32, b: f32, t: f32) -> f32 { a + (b - a) * t }

