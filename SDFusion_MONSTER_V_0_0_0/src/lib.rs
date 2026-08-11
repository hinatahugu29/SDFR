use pyo3::prelude::*;
use nalgebra::{Vector3, Quaternion, UnitQuaternion};
use std::sync::Mutex;
use once_cell::sync::Lazy;

mod tables;
mod gpu;
mod dc;
mod gpu_table_gen;

use gpu::{SdfGpuContext, GpuPrimitive, GpuConfig};

static GPU_CONTEXT: Mutex<Option<SdfGpuContext>> = Mutex::new(None);

#[pyclass]
#[derive(Clone)]
pub struct SdfPrimitive {
    pub shape_type: String,
    pub center: [f32; 3],
    pub rotation: [f32; 4],
    pub radius: f32,
    pub size: [f32; 3],
    pub operation: i32,
    pub smoothness: f32,
    pub color: [f32; 3],
    pub metallic: f32,
    pub roughness: f32,
    pub noise_strength: f32,
    pub noise_scale: f32,
    pub layout_data1: [f32; 4],
    pub layout_data2: [f32; 4],
    pub layout_data3: [f32; 4],
    pub layout_data4: [f32; 4],
    pub extra_params: [f32; 4],
    pub deform_data1: [f32; 4],
    pub deform_data2: [f32; 4],
    pub deform_data3: [f32; 4],
    pub deform_data4: [f32; 4],
    pub vertices: Option<Vec<f32>>,
    pub indices: Option<Vec<u32>>,
}

#[pymethods]
impl SdfPrimitive {
    #[new]
    #[pyo3(signature = (shape_type, center, rotation, radius, size, operation, smoothness, color, metallic, roughness, noise_strength, noise_scale, layout_data1=[0.0,0.0,0.0,0.0], layout_data2=[0.0,0.0,0.0,0.0], layout_data3=[0.0,0.0,0.0,0.0], layout_data4=[0.0,0.0,0.0,0.0], extra_params=[0.0,0.0,0.0,0.0], deform_data1=[0.0,0.0,0.0,0.0], deform_data2=[0.0,0.0,0.0,0.0], deform_data3=[0.0,0.0,0.0,0.0], deform_data4=[0.0,0.0,0.0,0.0], vertices=None, indices=None))]
    fn new(
        shape_type: String,
        center: [f32; 3],
        rotation: [f32; 4],
        radius: f32,
        size: [f32; 3],
        operation: i32,
        smoothness: f32,
        color: [f32; 3],
        metallic: f32,
        roughness: f32,
        noise_strength: f32,
        noise_scale: f32,
        layout_data1: [f32; 4],
        layout_data2: [f32; 4],
        layout_data3: [f32; 4],
        layout_data4: [f32; 4],
        extra_params: [f32; 4],
        deform_data1: [f32; 4],
        deform_data2: [f32; 4],
        deform_data3: [f32; 4],
        deform_data4: [f32; 4],
        vertices: Option<Vec<f32>>,
        indices: Option<Vec<u32>>,
    ) -> Self {
        Self {
            shape_type,
            center,
            rotation,
            radius,
            size,
            operation,
            smoothness,
            color,
            metallic,
            roughness,
            noise_strength,
            noise_scale,
            layout_data1,
            layout_data2,
            layout_data3,
            layout_data4,
            extra_params,
            deform_data1,
            deform_data2,
            deform_data3,
            deform_data4,
            vertices,
            indices,
        }
    }
}

#[pyfunction]
fn init_gpu() -> PyResult<String> {
    let mut ctx_lock = GPU_CONTEXT.lock().unwrap();
    if ctx_lock.is_none() {
        let mc_table = gpu_table_gen::get_marching_cubes_table();
        let ctx = pollster::block_on(SdfGpuContext::new(&mc_table));
        *ctx_lock = Some(ctx);
        Ok("GPU Initialized".to_string())
    } else {
        Ok("GPU Already Initialized".to_string())
    }
}

#[pyfunction]
fn generate_mesh_gpu(
    primitives: Vec<SdfPrimitive>,
    resolution: u32,
    domain_size: f32,
    domain_center: [f32; 3],
    symmetry: u32,
) -> PyResult<(Vec<f32>, Vec<u32>)> {
    let mut ctx_lock = GPU_CONTEXT.lock().unwrap();
    let ctx = ctx_lock.as_mut().expect("GPU not initialized");

    let mut gpu_prims: Vec<GpuPrimitive> = primitives.iter().map(|p| p.into()).collect();
    let mut gpu_tris: Vec<gpu::GpuTriangle> = Vec::new();
    
    let config = GpuConfig {
        res: resolution,
        domain_size,
        num_primitives: gpu_prims.len() as u32,
        num_triangles: gpu_tris.len() as u32,
        symmetry,
        hash_table_size: 131072,
        block_size: 8,
        max_tris: 500000,
    };

    for p in &primitives {
        if p.shape_type == "mesh" {
            if let (Some(verts), Some(indices)) = (&p.vertices, &p.indices) {
                let bvh = MeshBvh::new(verts, indices);
                let gpu_bvh_nodes: Vec<gpu::GpuBvhNode> = bvh.nodes.iter().map(|n| gpu::GpuBvhNode {
                    min: [n.min.x, n.min.y, n.min.z, n.left as f32],
                    max: [n.max.x, n.max.y, n.max.z, n.right as f32],
                }).collect();
                
                return generate_with_bvh(ctx, &gpu_prims, &gpu_bvh_nodes, verts, indices, &config);
            }
        }
    }

    let result = pollster::block_on(ctx.run_pipeline(&gpu_prims, &gpu_tris, &config));
    Ok(result)
}

fn generate_with_bvh(
    ctx: &mut SdfGpuContext,
    prims: &[GpuPrimitive],
    bvh_nodes: &[gpu::GpuBvhNode],
    verts: &[f32],
    indices: &[u32],
    config: &GpuConfig,
) -> PyResult<(Vec<f32>, Vec<u32>)> {
    let mut gpu_tris = Vec::new();
    for i in (0..indices.len()).step_by(3) {
        let i0 = indices[i] as usize;
        let i1 = indices[i+1] as usize;
        let i2 = indices[i+2] as usize;
        gpu_tris.push(gpu::GpuTriangle {
            v0: [verts[i0*4], verts[i0*4+1], verts[i0*4+2], verts[i0*4+3]],
            v1: [verts[i1*4], verts[i1*4+1], verts[i1*4+2], verts[i1*4+3]],
            v2: [verts[i2*4], verts[i2*4+1], verts[i2*4+2], verts[i2*4+3]],
        });
    }
    
    // BVHをGPUへ送るための拡張が必要
    let result = pollster::block_on(ctx.run_pipeline_with_bvh(prims, &gpu_tris, bvh_nodes, config));
    Ok(result)
}

// BVH 構築用ロジック
struct Triangle {
    v0: Vector3<f32>, v1: Vector3<f32>, v2: Vector3<f32>,
    center: Vector3<f32>,
}
struct BvhNode {
    min: Vector3<f32>, max: Vector3<f32>,
    left: i32, right: i32,
}
struct MeshBvh {
    nodes: Vec<BvhNode>,
}
impl MeshBvh {
    fn new(vertices: &[f32], indices: &[u32]) -> Self {
        let mut triangles = Vec::new();
        for i in (0..indices.len()).step_by(3) {
            let v0 = Vector3::new(vertices[indices[i] as usize * 4], vertices[indices[i] as usize * 4 + 1], vertices[indices[i] as usize * 4 + 2]);
            let v1 = Vector3::new(vertices[indices[i+1] as usize * 4], vertices[indices[i+1] as usize * 4 + 1], vertices[indices[i+1] as usize * 4 + 2]);
            let v2 = Vector3::new(vertices[indices[i+2] as usize * 4], vertices[indices[i+2] as usize * 4 + 1], vertices[indices[i+2] as usize * 4 + 2]);
            triangles.push(Triangle { v0, v1, v2, center: (v0+v1+v2)/3.0 });
        }
        let mut nodes = Vec::new();
        if !triangles.is_empty() {
            Self::build_recursive(&mut nodes, &triangles, &(0..triangles.len()).collect::<Vec<_>>());
        }
        Self { nodes }
    }
    fn build_recursive(nodes: &mut Vec<BvhNode>, all: &[Triangle], idxs: &[usize]) -> usize {
        let mut min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
        let mut max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
        for &i in idxs {
            let t = &all[i];
            min = min.inf(&t.v0.inf(&t.v1.inf(&t.v2)));
            max = max.sup(&t.v0.sup(&t.v1.sup(&t.v2)));
        }
        let node_idx = nodes.len();
        nodes.push(BvhNode { min, max, left: -1, right: -1 });
        if idxs.is_empty() { return node_idx; }
        if idxs.len() <= 1 {
            nodes[node_idx].right = idxs[0] as i32;
        } else {
            let extent = max - min;
            let axis = if extent.x > extent.y && extent.x > extent.z { 0 } else if extent.y > extent.z { 1 } else { 2 };
            let mut sorted = idxs.to_vec();
            sorted.sort_by(|&a, &b| all[a].center[axis].partial_cmp(&all[b].center[axis]).unwrap());
            let mid = sorted.len() / 2;
            let l = Self::build_recursive(nodes, all, &sorted[..mid]);
            let r = Self::build_recursive(nodes, all, &sorted[mid..]);
            nodes[node_idx].left = l as i32;
            nodes[node_idx].right = r as i32;
        }
        node_idx
    }
}

#[pymodule]
fn sdfusion_monster(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_class::<SdfPrimitive>()?;
    m.add_function(wrap_pyfunction!(init_gpu, m)?)?;
    m.add_function(wrap_pyfunction!(generate_mesh_gpu, m)?)?;
    Ok(())
}

impl From<&SdfPrimitive> for GpuPrimitive {
    fn from(p: &SdfPrimitive) -> Self {
        let shape_type = match p.shape_type.as_str() {
            "sphere" => 0.0,
            "box" => 1.0,
            "torus" => 2.0,
            "cylinder" => 3.0,
            "rounded_box" => 4.0,
            "capsule" => 5.0,
            "hex_prism" => 6.0,
            "pyramid" => 7.0,
            "capped_cone" => 8.0,
            "ngon_prism" => 9.0,
            "mesh" => 100.0,
            _ => 0.0,
        };

        Self {
            center_and_shape: [p.center[0], p.center[1], p.center[2], shape_type],
            rotation: p.rotation,
            size_and_op: [p.size[0], p.size[1], p.size[2], p.operation as f32],
            params: [p.radius, p.smoothness, p.metallic, p.roughness],
            noise_params: [p.noise_strength, p.noise_scale, p.color[0], p.color[1]],
            color_b_and_extra: [p.color[2], 0.0, 0.0, 0.0],
            layout_data1: p.layout_data1,
            layout_data2: p.layout_data2,
            layout_data3: p.layout_data3,
            layout_data4: p.layout_data4,
            extra_params: p.extra_params,
            deform_data1: p.deform_data1,
            deform_data2: p.deform_data2,
            deform_data3: p.deform_data3,
            deform_data4: p.deform_data4,
        }
    }
}
