use nalgebra::Vector3;
use crate::primitive::SdfPrimitive;
use crate::gpu::{GpuPrimitive, GpuBvhNode, SdfGpuContext};
use pyo3::prelude::*;

fn init_gpu(py: Python<'_>, cache_path: Option<String>, compile_dc: Option<bool>) -> PyResult<bool> {
    let mut ctx_lock = GPU_CONTEXT.lock().unwrap();
    if ctx_lock.is_some() {
        return Ok(true);
    }

    let compile_dc_val = compile_dc.unwrap_or(false);

    let cache_data = if let Some(path) = &cache_path {
        match std::fs::read(path) {
            Ok(data) => {
                println!("Rust Debug: Loading shader cache from '{}' ({} bytes)", path, data.len());
                Some(data)
            },
            Err(_) => {
                println!("Rust Debug: No shader cache found at '{}'. Initial compilation required.", path);
                None
            }
        }
    } else {
        None
    };

    // GILを解放して初期化（コンパイル）を実行
    let result = py.allow_threads(|| {
        let table = gpu_table_gen::get_marching_cubes_table();
        pollster::block_on(SdfGpuContext::new(&table, cache_data, compile_dc_val))
    });

    if let Some((new_ctx, new_cache)) = result {
        if let (Some(path), Some(data)) = (cache_path, new_cache) {
            if let Some(parent) = std::path::Path::new(&path).parent() {
                let _ = std::fs::create_dir_all(parent);
            }
            if let Ok(_) = std::fs::write(&path, &data) {
                println!("Rust Debug: Shader cache saved to '{}' ({} bytes)", path, data.len());
            }
        }
        *ctx_lock = Some(new_ctx);
        Ok(true)
    } else {
        Ok(false)
    }
}

#[pyfunction]
fn is_gpu_available() -> bool {
    GPU_CONTEXT.lock().unwrap().is_some()
}

fn convert_to_gpu_prim(p: &SdfPrimitive) -> gpu::GpuPrimitive {
    let shape_type = match p.shape_type.as_str() {
        "sphere" => 0,
        "box" => 1,
        "rounded_box" => 4,
        "torus" => 2,
        "cylinder" => 3,
        "capsule" => 5,
        "hex_prism" => 6,
        "pyramid" => 7,
        "capped_cone" => 8,
        "ngon_prism" => 9,
        "ellipsoid" => 10,
        "rounded_cylinder" => 11,
        "capped_torus" => 12,
        "octahedron" => 13,
        "cut_sphere" => 14,
        _ => 0,
    };
    gpu::GpuPrimitive {
        center_and_shape: [p.center[0], p.center[1], p.center[2], shape_type as f32],
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

fn build_gpu_bvh_recursive(nodes: &mut Vec<GpuBvhNode>, aabbs: &[(Vector3<f32>, Vector3<f32>)], indices: &[usize]) -> usize {
    let mut min = Vector3::new(f32::MAX, f32::MAX, f32::MAX);
    let mut max = Vector3::new(f32::MIN, f32::MIN, f32::MIN);
    for &idx in indices {
        min = min.inf(&aabbs[idx].0);
        max = max.sup(&aabbs[idx].1);
    }

    let node_idx = nodes.len();
    nodes.push(GpuBvhNode { min: [0.0; 4], max: [0.0; 4] });

    if indices.len() <= 1 {
        nodes[node_idx].min = [min.x, min.y, min.z, indices[0] as f32];
        nodes[node_idx].max = [max.x, max.y, max.z, 1.0]; // Leaf count = 1 (positive)
    } else {
        let extent = max - min;
        let axis = if extent.x > extent.y && extent.x > extent.z { 0 } else if extent.y > extent.z { 1 } else { 2 };
        let mut sorted = indices.to_vec();
        sorted.sort_by(|&a, &b| {
            let center_a = (aabbs[a].0[axis] + aabbs[a].1[axis]) * 0.5;
            let center_b = (aabbs[b].0[axis] + aabbs[b].1[axis]) * 0.5;
            center_a.partial_cmp(&center_b).unwrap()
        });
        let mid = sorted.len() / 2;
        let left = build_gpu_bvh_recursive(nodes, aabbs, &sorted[..mid]);
        let right = build_gpu_bvh_recursive(nodes, aabbs, &sorted[mid..]);
        nodes[node_idx].min = [min.x, min.y, min.z, left as f32];
        nodes[node_idx].max = [max.x, max.y, max.z, -(right as f32)]; // Inner node: -right_idx (negative)
    }
    node_idx
}
