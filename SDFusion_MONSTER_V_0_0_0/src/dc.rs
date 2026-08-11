use nalgebra::{Vector3, Matrix3};
use std::collections::HashMap;

pub struct QefSolver {
    pub ata: Matrix3<f32>,
    pub atb: Vector3<f32>,
    pub mass_point: Vector3<f32>,
    pub count: f32,
}

impl QefSolver {
    pub fn new() -> Self {
        Self {
            ata: Matrix3::zeros(),
            atb: Vector3::zeros(),
            mass_point: Vector3::zeros(),
            count: 0.0,
        }
    }

    pub fn add(&mut self, p: Vector3<f32>, n: Vector3<f32>) {
        let n_vec = n.normalize();
        let dot = n_vec.dot(&p);

        self.ata.m11 += n_vec.x * n_vec.x;
        self.ata.m12 += n_vec.x * n_vec.y;
        self.ata.m13 += n_vec.x * n_vec.z;
        self.ata.m21 += n_vec.y * n_vec.x;
        self.ata.m22 += n_vec.y * n_vec.y;
        self.ata.m23 += n_vec.y * n_vec.z;
        self.ata.m31 += n_vec.z * n_vec.x;
        self.ata.m32 += n_vec.z * n_vec.y;
        self.ata.m33 += n_vec.z * n_vec.z;

        self.atb.x += n_vec.x * dot;
        self.atb.y += n_vec.y * dot;
        self.atb.z += n_vec.z * dot;

        self.mass_point += p;
        self.count += 1.0;
    }

    pub fn solve(&self, step: f32) -> Vector3<f32> {
        if self.count == 0.0 { return Vector3::zeros(); }
        let mp = self.mass_point / self.count;
        let lambda = 0.05; 
        let mut ata_reg = self.ata;
        for i in 0..3 { ata_reg[(i, i)] += lambda; }
        let atb_reg = self.atb + lambda * mp;
        let svd = ata_reg.svd(true, true);
        let mut inv_s = Matrix3::zeros();
        for i in 0..3 { if svd.singular_values[i] > 1e-4 { inv_s[(i, i)] = 1.0 / svd.singular_values[i]; } }
        let pseudo_inv = svd.v_t.unwrap().transpose() * inv_s * svd.u.unwrap().transpose();
        let x = pseudo_inv * atb_reg;
        if (x - mp).norm_squared() > step * step { mp } else { x }
    }
}

#[derive(Hash, Eq, PartialEq, Clone, Copy)]
pub struct CellKey(pub i32, pub i32, pub i32);

pub struct DualContouring {
    pub vertices: Vec<f32>,
    pub indices: Vec<u32>,
}

impl DualContouring {
    pub fn generate(
        res: u32,
        size: f32,
        sdf_func: impl Fn(Vector3<f32>) -> (f32, [f32; 3], f32, f32),
        grad_func: impl Fn(Vector3<f32>) -> Vector3<f32>
    ) -> Self {
        // Simplified implementation for structure parity
        Self { vertices: vec![], indices: vec![] }
    }
}
