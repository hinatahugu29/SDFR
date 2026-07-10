use nalgebra::{Vector3, Matrix3, Vector4, Matrix4};
use std::collections::HashMap;

/// QEF (Quadratic Error Function) ソルバー
/// エッジ上の交差位置(p)と法線(n)から、誤差を最小化するセル内頂点を求める
pub struct QefSolver {
    pub ata: Matrix3<f32>,
    pub atb: Vector3<f32>,
    pub btb: f32,
    pub mass_point: Vector3<f32>,
    pub count: f32,
}

impl QefSolver {
    pub fn new() -> Self {
        Self {
            ata: Matrix3::zeros(),
            atb: Vector3::zeros(),
            btb: 0.0,
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

        self.btb += dot * dot;
        self.mass_point += p;
        self.count += 1.0;
    }

    pub fn solve(&self, step: f32) -> Vector3<f32> {
        if self.count == 0.0 {
            return Vector3::zeros();
        }

        let mp = self.mass_point / self.count;
        
        // 正則化項 (Levenberg-Marquardt風)
        // 面が平坦な場合に計算が不安定になるのを防ぐ
        let lambda = 0.05; 
        let mut ata_reg = self.ata;
        for i in 0..3 {
            ata_reg[(i, i)] += lambda;
        }
        
        // mp 方向への引き込み
        let atb_reg = self.atb + lambda * mp;

        // SVDによる擬似逆行列を用いた解法
        let svd = ata_reg.svd(true, true);
        let mut inv_s = Matrix3::zeros();
        let eps = 1e-4;
        for i in 0..3 {
            if svd.singular_values[i] > eps {
                inv_s[(i, i)] = 1.0 / svd.singular_values[i];
            }
        }

        let u = svd.u.unwrap();
        let v_t = svd.v_t.unwrap();
        let pseudo_inv = v_t.transpose() * inv_s * u.transpose();
        
        let x = pseudo_inv * atb_reg;
        
        // 求まった解 x がセルの中心(mp)から離れすぎている場合は mp を返す
        let dist_sq = (x - mp).norm_squared();
        let limit = step * step * 1.0; 
        if dist_sq > limit {
            mp
        } else {
            x
        }
    }
}

/// セルを特定するためのキー
#[derive(Hash, Eq, PartialEq, Clone, Copy)]
pub struct CellKey(pub i32, pub i32, pub i32);

pub struct DualContouring {
    pub vertices: Vec<f32>,
    pub indices: Vec<u32>,
}

impl DualContouring {
    pub fn generate(
        res: usize,
        size: f32,
        sdf_func: impl Fn(Vector3<f32>) -> (f32, [f32; 3], f32, f32),
        grad_func: impl Fn(Vector3<f32>) -> Vector3<f32>
    ) -> Self {
        let step = size / res as f32;
        let half_res = res as f32 / 2.0;
        
        // (pos, [r,g,b], metallic, roughness)
        let mut cell_vertices: HashMap<CellKey, (Vector3<f32>, [f32; 3], f32, f32)> = HashMap::new();
        
        // 1. 各セル内の頂点を QEF で決定
        for x in 0..res {
            for y in 0..res {
                for z in 0..res {
                    let mut qef = QefSolver::new();
                    let mut has_intersection = false;
                    let mut avg_color = [0.0; 3];
                    let mut avg_met = 0.0;
                    let mut avg_rou = 0.0;
                    let mut color_count = 0.0;

                    // セルの12本のエッジをチェック
                    let edges = [
                        // X軸方向
                        ((0,0,0), (1,0,0)), ((0,1,0), (1,1,0)), ((0,0,1), (1,0,1)), ((0,1,1), (1,1,1)),
                        // Y軸方向
                        ((0,0,0), (0,1,0)), ((1,0,0), (1,1,0)), ((0,0,1), (0,1,1)), ((1,0,1), (1,1,1)),
                        // Z軸方向
                        ((0,0,0), (0,0,1)), ((1,0,0), (1,0,1)), ((0,1,0), (0,1,1)), ((1,1,0), (1,1,1)),
                    ];

                    for (v1_off, v2_off) in edges {
                        let p1_grid = Vector3::new((x + v1_off.0) as f32, (y + v1_off.1) as f32, (z + v1_off.2) as f32);
                        let p2_grid = Vector3::new((x + v2_off.0) as f32, (y + v2_off.1) as f32, (z + v2_off.2) as f32);
                        let p1 = (p1_grid - Vector3::new(half_res, half_res, half_res)) * step;
                        let p2 = (p2_grid - Vector3::new(half_res, half_res, half_res)) * step;

                        let (d1, c1, m1, r1) = sdf_func(p1);
                        let (d2, _, _, _) = sdf_func(p2);

                        if (d1 < 0.0) != (d2 < 0.0) {
                            has_intersection = true;
                            // 線形補間で交差位置を推定
                            let t = -d1 / (d2 - d1);
                            let mut p_interp = p1 + (p2 - p1) * t;
                            
                            // ニュートン法でさらに精度向上
                            for _ in 0..2 {
                                let (d, _, _, _) = sdf_func(p_interp);
                                let g = grad_func(p_interp);
                                let g_norm_sq = g.norm_squared();
                                if g_norm_sq > 1e-6 {
                                    p_interp -= g * (d / g_norm_sq);
                                }
                            }

                            let normal = grad_func(p_interp);
                            qef.add(p_interp, normal);
                            
                            avg_color[0] += c1[0];
                            avg_color[1] += c1[1];
                            avg_color[2] += c1[2];
                            avg_met += m1;
                            avg_rou += r1;
                            color_count += 1.0;
                        }
                    }

                    if has_intersection {
                        let mut v_pos = qef.solve(step);
                        // 解をセル内に拘束 (AABB)
                        let min_p = (Vector3::new(x as f32, y as f32, z as f32) - Vector3::new(half_res, half_res, half_res)) * step;
                        let max_p = min_p + Vector3::new(step, step, step);
                        v_pos.x = v_pos.x.clamp(min_p.x, max_p.x);
                        v_pos.y = v_pos.y.clamp(min_p.y, max_p.y);
                        v_pos.z = v_pos.z.clamp(min_p.z, max_p.z);

                        cell_vertices.insert(CellKey(x as i32, y as i32, z as i32), (v_pos, [avg_color[0]/color_count, avg_color[1]/color_count, avg_color[2]/color_count], avg_met/color_count, avg_rou/color_count));
                    }
                }
            }
        }

        // 2. フェイス生成
        let mut final_verts = Vec::new();
        let mut final_indices = Vec::new();
        let mut cell_to_vert_idx = HashMap::new();

        // X, Y, Z 各方向のエッジをスキャン
        // エッジを共有する4つのセルの頂点を繋いでクアッドを作る
        for x in 0..res {
            for y in 0..res {
                for z in 0..res {
                    // X-edge, Y-edge, Z-edge
                    let directions = [
                        ((0,0,0), (1,0,0), 0), // X-edge
                        ((0,0,0), (0,1,0), 1), // Y-edge
                        ((0,0,0), (0,0,1), 2), // Z-edge
                    ];

                    for (v1_off, v2_off, axis) in directions {
                        let ix = x as i32; let iy = y as i32; let iz = z as i32;
                        let (d1, _, _, _) = sdf_func((Vector3::new((ix+v1_off.0) as f32, (iy+v1_off.1) as f32, (iz+v1_off.2) as f32) - Vector3::new(half_res, half_res, half_res)) * step);
                        let (d2, _, _, _) = sdf_func((Vector3::new((ix+v2_off.0) as f32, (iy+v2_off.1) as f32, (iz+v2_off.2) as f32) - Vector3::new(half_res, half_res, half_res)) * step);
                        
                        if (d1 < 0.0) != (d2 < 0.0) {
                            // このエッジを囲む4つのセルを取得
                            let cells = match axis {
                                0 => [(ix, iy, iz), (ix, iy-1, iz), (ix, iy-1, iz-1), (ix, iy, iz-1)],
                                1 => [(ix, iy, iz), (ix-1, iy, iz), (ix-1, iy, iz-1), (ix, iy, iz-1)],
                                2 => [(ix, iy, iz), (ix-1, iy, iz), (ix-1, iy-1, iz), (ix, iy-1, iz)],
                                _ => unreachable!(),
                            };

                            let mut quad_indices = Vec::new();
                            for (cx, cy, cz) in cells {
                                let key = CellKey(cx, cy, cz);
                                if let Some((pos, col, met, rou)) = cell_vertices.get(&key) {
                                    let v_idx = *cell_to_vert_idx.entry(key).or_insert_with(|| {
                                        let idx = (final_verts.len() / 11) as u32;
                                        // 法線の計算
                                        let grad = grad_func(*pos);
                                        let normal = -grad.try_normalize(1e-6).unwrap_or(Vector3::new(0.0, 1.0, 0.0));
                                        final_verts.extend_from_slice(&[
                                            pos.x, pos.y, pos.z, 
                                            col[0], col[1], col[2], 
                                            *met, *rou,
                                            normal.x, normal.y, normal.z
                                        ]);
                                        idx
                                    });
                                    quad_indices.push(v_idx);
                                }
                            }

                            if quad_indices.len() == 4 {
                                // 面の向きを考慮
                                if d1 < 0.0 {
                                    final_indices.extend_from_slice(&[quad_indices[0], quad_indices[1], quad_indices[2]]);
                                    final_indices.extend_from_slice(&[quad_indices[0], quad_indices[2], quad_indices[3]]);
                                } else {
                                    final_indices.extend_from_slice(&[quad_indices[0], quad_indices[2], quad_indices[1]]);
                                    final_indices.extend_from_slice(&[quad_indices[0], quad_indices[3], quad_indices[2]]);
                                }
                            }
                        }
                    }
                }
            }
        }

        Self { vertices: final_verts, indices: final_indices }
    }
}
