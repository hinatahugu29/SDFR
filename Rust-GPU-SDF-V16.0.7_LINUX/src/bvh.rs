use nalgebra::Vector3;
use crate::math::dist_to_triangle;

#[derive(Clone)]
struct Triangle {
    v0: Vector3<f32>,
    v1: Vector3<f32>,
    v2: Vector3<f32>,
    normal: Vector3<f32>,
    center: Vector3<f32>,
}

#[derive(Clone)]
struct BvhNode {
    min: Vector3<f32>,
    max: Vector3<f32>,
    left: i32,  // -1 if leaf
    right: i32, // tri index if leaf, or right child index
}

struct MeshBvh {
    nodes: Vec<BvhNode>,
    triangles: Vec<Triangle>,
}

impl MeshBvh {
    fn new(vertices: &[f32], indices: &[u32]) -> Self {
        let mut triangles = Vec::new();
        for i in (0..indices.len()).step_by(3) {
            let v0 = Vector3::new(vertices[indices[i] as usize * 3], vertices[indices[i] as usize * 3 + 1], vertices[indices[i] as usize * 3 + 2]);
            let v1 = Vector3::new(vertices[indices[i+1] as usize * 3], vertices[indices[i+1] as usize * 3 + 1], vertices[indices[i+1] as usize * 3 + 2]);
            let v2 = Vector3::new(vertices[indices[i+2] as usize * 3], vertices[indices[i+2] as usize * 3 + 1], vertices[indices[i+2] as usize * 3 + 2]);
            let normal = (v1 - v0).cross(&(v2 - v0)).normalize();
            let center = (v0 + v1 + v2) / 3.0;
            triangles.push(Triangle { v0, v1, v2, normal, center });
        }

        let mut nodes = Vec::new();
        if !triangles.is_empty() {
            Self::build_recursive(&mut nodes, &triangles, &(0..triangles.len()).collect::<Vec<_>>());
        }

        Self { nodes, triangles }
    }

    fn build_recursive(nodes: &mut Vec<BvhNode>, all_tris: &[Triangle], current_indices: &[usize]) -> usize {
        let mut min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
        let mut max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
        for &idx in current_indices {
            let t = &all_tris[idx];
            min = min.inf(&t.v0.inf(&t.v1.inf(&t.v2)));
            max = max.sup(&t.v0.sup(&t.v1.sup(&t.v2)));
        }

        let node_idx = nodes.len();
        nodes.push(BvhNode { min, max, left: -1, right: -1 });

        if current_indices.len() <= 1 {
            nodes[node_idx].right = current_indices[0] as i32;
        } else {
            // 最も広がっている軸で分割
            let extent = max - min;
            let axis = if extent.x > extent.y && extent.x > extent.z { 0 } else if extent.y > extent.z { 1 } else { 2 };
            
            let mut sorted_indices = current_indices.to_vec();
            sorted_indices.sort_by(|&a, &b| all_tris[a].center[axis].partial_cmp(&all_tris[b].center[axis]).unwrap());
            
            let mid = sorted_indices.len() / 2;
            let left = Self::build_recursive(nodes, all_tris, &sorted_indices[..mid]);
            let right = Self::build_recursive(nodes, all_tris, &sorted_indices[mid..]);
            
            nodes[node_idx].left = left as i32;
            nodes[node_idx].right = right as i32;
        }
        node_idx
    }

    fn get_closest_dist(&self, p: Vector3<f32>) -> f32 {
        if self.nodes.is_empty() { return f32::MAX; }
        let mut min_dist_sq = f32::MAX;
        let mut closest_tri_idx = 0;
        self.query_recursive(0, p, &mut min_dist_sq, &mut closest_tri_idx);
        
        let tri = &self.triangles[closest_tri_idx];
        let d = dist_to_triangle(p, tri.v0, tri.v1, tri.v2);
        
        // 符号判定: 最近接三角形の法線とのドット積
        let to_p = p - (tri.v0 + tri.v1 + tri.v2) / 3.0;
        if tri.normal.dot(&to_p) < 0.0 { -d } else { d }
    }

    fn query_recursive(&self, node_idx: usize, p: Vector3<f32>, min_dist_sq: &mut f32, closest_tri_idx: &mut usize) {
        let node = &self.nodes[node_idx];
        
        // AABBへの最短距離を確認
        let dx = (node.min.x - p.x).max(0.0).max(p.x - node.max.x);
        let dy = (node.min.y - p.y).max(0.0).max(p.y - node.max.y);
        let dz = (node.min.z - p.z).max(0.0).max(p.z - node.max.z);
        let d_aabb_sq = dx*dx + dy*dy + dz*dz;
        
        if d_aabb_sq > *min_dist_sq { return; }

        if node.left == -1 {
            let tri_idx = node.right as usize;
            let tri = &self.triangles[tri_idx];
            // 正確な距離計算（二乗で比較して重い計算を避ける）
            // 簡易的に中心点への距離で枝刈り（理想的には三角形との最短距離の二乗が必要だが重いので近似）
            let d_tri_sq = (tri.center - p).norm_squared(); 
            if d_tri_sq < *min_dist_sq {
                *min_dist_sq = d_tri_sq;
                *closest_tri_idx = tri_idx;
            }
        } else {
            self.query_recursive(node.left as usize, p, min_dist_sq, closest_tri_idx);
            self.query_recursive(node.right as usize, p, min_dist_sq, closest_tri_idx);
        }
    }
}

