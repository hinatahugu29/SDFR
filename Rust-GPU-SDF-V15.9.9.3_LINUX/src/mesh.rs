use nalgebra::Vector3;
use std::collections::HashMap;
use rayon::prelude::*;

use rayon::prelude::*;

/// 頂点統合 (Weld / Merge by Distance)
fn weld_mesh(vertices: Vec<f32>, indices: Vec<u32>, threshold: f32) -> (Vec<f32>, Vec<u32>) {
    if vertices.is_empty() { return (vertices, indices); }
    
    let mut new_indices = Vec::new();
    let mut vertex_map = HashMap::new(); 
    
    // 頂点データの蓄積用: (座標の合計, 法線の合計, カウント, その他の属性)
    struct WeldData {
        sum_pos: Vector3<f32>,
        sum_normal: Vector3<f32>,
        count: usize,
        other_attr: [f32; 5], // color(3), metallic, roughness
    }
    let mut unique_verts_data: Vec<WeldData> = Vec::new();
    
    let inv_threshold = 1.0 / threshold.max(1e-9);
    
    for i in (0..indices.len()).step_by(3) {
        if i + 2 >= indices.len() { break; }
        
        let mut tri_new = [0u32; 3];
        let mut tri_valid = true;
        
        for j in 0..3 {
            let old_idx = indices[i + j];
            let v_base = old_idx as usize * 11;
            if v_base + 10 >= vertices.len() {
                tri_valid = false;
                break;
            }
            
            let p = Vector3::new(vertices[v_base], vertices[v_base+1], vertices[v_base+2]);
            let n = Vector3::new(vertices[v_base+8], vertices[v_base+9], vertices[v_base+10]);
            
            // 座標をグリッド化してキーにする
            let key = [
                (p.x * inv_threshold).round() as i32,
                (p.y * inv_threshold).round() as i32,
                (p.z * inv_threshold).round() as i32,
            ];
            
            let new_v_idx = if let Some(&idx) = vertex_map.get(&key) {
                idx
            } else {
                let idx = unique_verts_data.len() as u32;
                unique_verts_data.push(WeldData {
                    sum_pos: Vector3::new(0.0, 0.0, 0.0),
                    sum_normal: Vector3::new(0.0, 0.0, 0.0),
                    count: 0,
                    other_attr: [
                        vertices[v_base+3], vertices[v_base+4], vertices[v_base+5], // color
                        vertices[v_base+6], vertices[v_base+7]                     // met, rough
                    ],
                });
                vertex_map.insert(key, idx);
                idx
            };
            
            tri_new[j] = new_v_idx;
            
            // データを蓄積
            let data = &mut unique_verts_data[new_v_idx as usize];
            data.sum_pos += p;
            data.sum_normal += n;
            data.count += 1;
        }
        
        if tri_valid {
            // 縮退ポリゴン（面積がゼロになる面）を除去
            if tri_new[0] != tri_new[1] && tri_new[1] != tri_new[2] && tri_new[2] != tri_new[0] {
                new_indices.extend_from_slice(&tri_new);
            }
        }
    }
    
    // 蓄積されたデータから最終的な頂点リストを構築（平均化と正規化）
    let mut final_vertices = Vec::with_capacity(unique_verts_data.len() * 11);
    for data in unique_verts_data {
        let c = data.count as f32;
        let avg_p = data.sum_pos / c;
        // 法線は平均化してから再正規化することで、滑らかな面を実現
        let avg_n = if data.sum_normal.norm_squared() > 1e-6 {
            data.sum_normal.normalize()
        } else {
            Vector3::new(0.0, 0.0, 1.0)
        };
        
        final_vertices.push(avg_p.x);
        final_vertices.push(avg_p.y);
        final_vertices.push(avg_p.z);
        final_vertices.extend_from_slice(&data.other_attr);
        final_vertices.push(avg_n.x);
        final_vertices.push(avg_n.y);
        final_vertices.push(avg_n.z);
    }
    
    (final_vertices, new_indices)
}

// パニック時でも確実にフラグをリセットするためのガード (V13.3 安定化)
