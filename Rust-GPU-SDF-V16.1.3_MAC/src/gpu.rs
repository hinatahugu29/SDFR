use wgpu::util::DeviceExt;
use std::sync::{atomic::{AtomicUsize, Ordering}, RwLock};

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuPrimitive {
    pub center_and_shape: [f32; 4], // [x, y, z, shape_type]
    pub rotation: [f32; 4],         // [x, y, z, w]
    pub size_and_op: [f32; 4],      // [sx, sy, sz, operation]
    pub params: [f32; 4],           // [radius, smoothness, metallic, roughness]
    pub noise_params: [f32; 4],     // [strength, scale, color_r, color_g]
    pub color_b_and_extra: [f32; 4], // [color_b, blend_profile, chamfer_smooth, layer_id]
    pub layout_data1: [f32; 4],     // [mode_flags, p1, p2, p3]
    pub layout_data2: [f32; 4],     // [p4, p5, p6, p7]
    pub layout_data3: [f32; 4],     // [p8, p9, p10, p11]
    pub layout_data4: [f32; 4],     // [p12, p13, p14, p15]
    pub extra_params: [f32; 4],     // [p1, p2, p3, p4] (V13)
    pub deform_data1: [f32; 4],     // [flags, stretch_x, stretch_y, stretch_z]
    pub deform_data2: [f32; 4],     // [bend_angle, bend_axis, bend_center, twist_angle]
    pub deform_data3: [f32; 4],     // [twist_axis, twist_center, taper_factor, taper_axis]
    pub deform_data4: [f32; 4],     // [taper_center, 0, 0, 0]
    pub modifier_params: [f32; 4],  // [edge_profile, shell_thickness, edge_chamfer_smooth, free]
    pub gyroid_params: [f32; 4],     // [phase, axis_x, axis_y, axis_z]
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuBvhNode {
    pub min: [f32; 4], // [x, y, z, child_or_prim_idx]
    pub max: [f32; 4], // [x, y, z, count] (count > 0 means leaf)
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuConfig {
    pub res: u32,
    pub domain_size: f32,
    pub num_primitives: u32,
    pub symmetry: u32, // Bitmask: X=1, Y=2, Z=4
    pub hash_table_size: u32,
    pub block_size: u32,
    pub max_tris: u32,
    pub _pad: u32,
    pub domain_origin: [f32; 4],
}

#[derive(Clone, Debug, Default)]
pub struct GpuMeshStats {
    pub algo: &'static str,
    pub active_blocks: u32,
    pub active_blocks_raw: u32,
    pub tris_or_faces: u32,
    pub tris_or_faces_raw: u32,
    pub verts: u32,
    pub verts_raw: u32,
    pub indices: u32,
    pub indices_raw: u32,
    pub missing_ptrs: u32,
    pub empty_voxels: u32,
    pub chunks_total: u32,
    pub chunks_nonempty: u32,
    pub chunks_empty: u32,
    pub chunks_problem: u32,
    pub filtered_tris: u32,
    pub max_blocks: u32,
    pub max_tris: u32,
    pub max_verts: u32,
    pub max_indices: u32,
}

impl GpuMeshStats {
    pub fn health(&self) -> &'static str {
        if self.active_blocks_raw > self.max_blocks
            || self.tris_or_faces_raw > self.max_tris
            || self.verts_raw > self.max_verts
            || self.indices_raw > self.max_indices
            || self.tris_or_faces >= self.max_tris
            || self.verts >= self.max_verts
            || self.indices >= self.max_indices
        {
            "CAPACITY_LIMITED"
        } else if self.missing_ptrs > 0 {
            "BLOCK_OR_PRIM_FALLBACK"
        } else if self.tris_or_faces == 0 && self.verts == 0 {
            "EMPTY_RESULT"
        } else if self.empty_voxels > 0 {
            "SURFACE_UNDER_SAMPLED"
        } else {
            "OK"
        }
    }

    pub fn summary(&self) -> String {
        format!(
            "health={}; algo={}; active_blocks={}/{}; faces={}/{}; verts={}/{}; indices={}/{}; missing_ptrs={}; empty_voxels={}; chunks={}/{}/{}/{}; filtered_tris={}; caps=max_blocks:{}, max_tris:{}, max_verts:{}, max_indices:{}",
            self.health(),
            self.algo,
            self.active_blocks_raw,
            self.active_blocks,
            self.tris_or_faces_raw,
            self.tris_or_faces,
            self.verts_raw,
            self.verts,
            self.indices_raw,
            self.indices,
            self.missing_ptrs,
            self.empty_voxels,
            self.chunks_total,
            self.chunks_nonempty,
            self.chunks_empty,
            self.chunks_problem,
            self.filtered_tris,
            self.max_blocks,
            self.max_tris,
            self.max_verts,
            self.max_indices,
        )
    }

    pub fn merge_from(&mut self, other: &GpuMeshStats) {
        self.active_blocks = self.active_blocks.saturating_add(other.active_blocks);
        self.active_blocks_raw = self.active_blocks_raw.saturating_add(other.active_blocks_raw);
        self.tris_or_faces = self.tris_or_faces.saturating_add(other.tris_or_faces);
        self.tris_or_faces_raw = self.tris_or_faces_raw.saturating_add(other.tris_or_faces_raw);
        self.verts = self.verts.saturating_add(other.verts);
        self.verts_raw = self.verts_raw.saturating_add(other.verts_raw);
        self.indices = self.indices.saturating_add(other.indices);
        self.indices_raw = self.indices_raw.saturating_add(other.indices_raw);
        self.missing_ptrs = self.missing_ptrs.saturating_add(other.missing_ptrs);
        self.empty_voxels = self.empty_voxels.saturating_add(other.empty_voxels);
        self.chunks_total = self.chunks_total.saturating_add(other.chunks_total);
        self.chunks_nonempty = self.chunks_nonempty.saturating_add(other.chunks_nonempty);
        self.chunks_empty = self.chunks_empty.saturating_add(other.chunks_empty);
        self.chunks_problem = self.chunks_problem.saturating_add(other.chunks_problem);
        self.filtered_tris = self.filtered_tris.saturating_add(other.filtered_tris);
    }
}

fn filter_mesh_to_core_bounds(
    verts: Vec<f32>,
    indices: Vec<u32>,
    min_bound: [f32; 3],
    max_bound: [f32; 3],
    include_max: [bool; 3],
) -> (Vec<f32>, Vec<u32>, u32) {
    let mut out_verts = Vec::new();
    let mut out_indices = Vec::new();
    let mut kept = vec![u32::MAX; verts.len() / 11];
    let mut dropped_tris = 0u32;
    let eps = 1e-5f32;

    for tri in indices.chunks(3) {
        if tri.len() != 3 {
            continue;
        }

        let mut centroid = [0.0f32; 3];
        let mut valid = true;
        for &idx in tri {
            let base = idx as usize * 11;
            if base + 10 >= verts.len() {
                valid = false;
                break;
            }
            centroid[0] += verts[base];
            centroid[1] += verts[base + 1];
            centroid[2] += verts[base + 2];
        }
        if !valid {
            dropped_tris = dropped_tris.saturating_add(1);
            continue;
        }
        centroid[0] /= 3.0;
        centroid[1] /= 3.0;
        centroid[2] /= 3.0;

        let inside = (0..3).all(|axis| {
            let lower_ok = centroid[axis] >= min_bound[axis] - eps;
            let upper_ok = if include_max[axis] {
                centroid[axis] <= max_bound[axis] + eps
            } else {
                centroid[axis] < max_bound[axis] - eps
            };
            lower_ok && upper_ok
        });
        if !inside {
            dropped_tris = dropped_tris.saturating_add(1);
            continue;
        }

        for &idx in tri {
            let idx_usize = idx as usize;
            if idx_usize >= kept.len() {
                continue;
            }
            if kept[idx_usize] == u32::MAX {
                let new_idx = (out_verts.len() / 11) as u32;
                let base = idx_usize * 11;
                out_verts.extend_from_slice(&verts[base..base + 11]);
                kept[idx_usize] = new_idx;
            }
            out_indices.push(kept[idx_usize]);
        }
    }

    (out_verts, out_indices, dropped_tris)
}


pub struct SdfGpuContext {
    device: wgpu::Device,
    queue: wgpu::Queue,
    
    // Shared pipeline objects
    pipeline_layout: wgpu::PipelineLayout,
    shader_module: wgpu::ShaderModule,
    pipeline_cache: Option<wgpu::PipelineCache>,
    
    // Eagerly compiled compute pipelines
    pipeline_mc: wgpu::ComputePipeline,
    pipeline_detect: wgpu::ComputePipeline,
    // Dual Contouring pipelines are lazily compiled
    pipeline_dc_vertex: RwLock<Option<wgpu::ComputePipeline>>,
    pipeline_dc_face: RwLock<Option<wgpu::ComputePipeline>>,
    // V15.9.9.1: Stores the latest DC pipeline compile diagnostic, if any.
    dc_last_error: RwLock<Option<String>>,

    config_buffer: wgpu::Buffer,
    prim_buffer: wgpu::Buffer,
    mc_table_buffer: wgpu::Buffer,
    
    // V10.3: double buffering
    vertex_buffers: [wgpu::Buffer; 2],
    index_buffers: [wgpu::Buffer; 2],
    counter_buffers: [wgpu::Buffer; 2],
    
    hash_keys_buffer: wgpu::Buffer,
    hash_values_buffer: wgpu::Buffer,
    block_data_buffer: wgpu::Buffer,
    clear_values_buffer: wgpu::Buffer,
    
    // V10.4: Sparse dispatch buffer
    active_blocks_buffer: wgpu::Buffer,
    
    // V15.6: Per-block primitive index list buffers
    block_prim_info_buffer: wgpu::Buffer,
    global_prim_indices_buffer: wgpu::Buffer,
    global_counter_buffer: wgpu::Buffer,
    bvh_nodes_buffer: wgpu::Buffer,
    
    // Staging buffers for CPU readback
    read_counter_buffer: wgpu::Buffer,
    read_vertex_buffer: wgpu::Buffer,
    read_index_buffer: wgpu::Buffer,
    
    // current write/read backbuffer index (0 or 1)
    pub back_buffer_index: AtomicUsize,
    pub max_verts: u32,
    pub max_indices: u32,
    pub max_blocks: u32,
    pub max_tris: u32,
    _clear_buffer: wgpu::Buffer,
}

fn get_dispatch_dims(count: u32) -> (u32, u32) {
    if count <= 65535 { (count, 1) }
    else { (65535, (count + 65534) / 65535) }
}

impl SdfGpuContext {
    pub async fn new(mc_table: &[i32], cache_data: Option<Vec<u8>>, compile_dc: bool) -> Option<(Self, Option<Vec<u8>>)> {
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            // Use the best native backend available (Vulkan/Dx12/Metal).
            backends: wgpu::Backends::PRIMARY,
            ..Default::default()
        });
        
        let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            compatible_surface: None,
            force_fallback_adapter: false,
        }).await?;

        let info = adapter.get_info();
        let is_integrated_gpu = matches!(
            info.device_type,
            wgpu::DeviceType::IntegratedGpu | wgpu::DeviceType::Cpu | wgpu::DeviceType::Other
        );
        println!("Rust Debug: GPU Context Initializing... Adapter: '{}', Backend: {:?}", info.name, info.backend);
        println!("Rust Debug: Adapter Features: {:?}", adapter.features());

        let (device, queue) = adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: Some("SDF Compute Device"),
                required_features: adapter.features() & wgpu::Features::PIPELINE_CACHE,
                required_limits: adapter.limits(), 
                memory_hints: wgpu::MemoryHints::default(),
            },
            None,
        ).await.expect("Failed to create device");

        let limits = device.limits();
        
        // Restore a driver pipeline cache when supported by wgpu/device features.
        let has_cache_feature = device.features().contains(wgpu::Features::PIPELINE_CACHE);
        let pipeline_cache = if has_cache_feature {
            // wgpu's `fallback: true` is documented to silently discard mismatched cache
            // data, but on some driver/wgpu combinations a validation failure here (e.g.
            // cache data captured on a different GPU) surfaces as a hard `panic!` instead
            // of falling back. Guard the call so a stale/incompatible cache can never take
            // the whole init thread down; on panic, retry once with no cache data.
            let attempt = std::panic::catch_unwind(std::panic::AssertUnwindSafe(|| unsafe {
                device.create_pipeline_cache(&wgpu::PipelineCacheDescriptor {
                    label: Some("SDF Pipeline Cache"),
                    data: cache_data.as_deref(),
                    fallback: true,
                })
            }));
            Some(match attempt {
                Ok(cache) => cache,
                Err(_) => {
                    println!("Rust Debug: Pipeline cache data incompatible with this device; rebuilding from scratch.");
                    unsafe {
                        device.create_pipeline_cache(&wgpu::PipelineCacheDescriptor {
                            label: Some("SDF Pipeline Cache"),
                            data: None,
                            fallback: true,
                        })
                    }
                }
            })
        } else {
            None
        };

        // --- Buffer size tuning (V15.9.5) ---
        let vertex_stride = 11 * 4;
        let max_v_by_limit = (limits.max_storage_buffer_binding_size as u64 / vertex_stride as u64) as u32;
        let max_i_by_limit = (limits.max_storage_buffer_binding_size as u64 / 4) as u32;

        let mut max_verts = 10_000_000;
        let mut max_indices = 30_000_000;

        if max_verts > max_v_by_limit || max_indices > max_i_by_limit {
            println!("Rust Debug: Adjusting max_verts/indices due to GPU binding limits.");
            max_verts = max_verts.min(max_v_by_limit);
            max_indices = max_indices.min(max_i_by_limit);
        }

        if is_integrated_gpu {
            max_verts = max_verts.min(2_500_000);
            max_indices = max_indices.min(7_500_000);
            println!(
                "Rust Debug: Integrated/UMA GPU detected. Applying conservative mesh caps: max_verts={}, max_indices={}",
                max_verts, max_indices
            );
        }

        // keep headroom for additional buffers
        max_verts = (max_verts as f64 * 0.9) as u32;
        max_indices = (max_indices as f64 * 0.9) as u32;
        let max_tris = (max_indices / 3).min(max_verts / 3);
        let v_size = (max_verts as u64 * vertex_stride as u64) as wgpu::BufferAddress;
        let i_size = (max_indices as u64 * 4) as wgpu::BufferAddress;

        println!("Rust Debug: Configured Max Verts: {}, Max Indices: {} (Total Buffer Size: {:.1} MB)", 
            max_verts, max_indices, (v_size + i_size) as f64 / 1024.0 / 1024.0);

        // Ensure configured mesh buffers still fit within GPU binding limits.
        if v_size > limits.max_storage_buffer_binding_size as u64 || i_size > limits.max_storage_buffer_binding_size as u64 {
            println!("Rust Error: Requested buffer size exceeds GPU limits even after adjustment.");
            return None;
        }

        let bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("SDF Bind Group Layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry { binding: 0, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 1, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 2, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 3, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 4, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 5, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 6, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 7, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 8, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 9, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 10, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 11, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 12, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: false }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 13, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None },
            ],
        });

        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("SDF Pipeline Layout"),
            bind_group_layouts: &[&bind_group_layout],
            push_constant_ranges: &[],
        });

        let mc_table_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("MC Table Buffer"),
            contents: bytemuck::cast_slice(mc_table),
            usage: wgpu::BufferUsages::STORAGE,
        });
        
        let config_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Config Buffer"), size: 64, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let prim_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Prim Buffer"), size: 1024 * 512, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        
        let vertex_buffers = [
            device.create_buffer(&wgpu::BufferDescriptor { label: Some("Vertex Buffer A"), size: v_size, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false }),
            device.create_buffer(&wgpu::BufferDescriptor { label: Some("Vertex Buffer B"), size: v_size, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false }),
        ];
        let index_buffers = [
            device.create_buffer(&wgpu::BufferDescriptor { label: Some("Index Buffer A"), size: i_size, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false }),
            device.create_buffer(&wgpu::BufferDescriptor { label: Some("Index Buffer B"), size: i_size, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false }),
        ];
        let counter_buffers = [
            device.create_buffer(&wgpu::BufferDescriptor { label: Some("Counter Buffer A"), size: 32, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false }),
            device.create_buffer(&wgpu::BufferDescriptor { label: Some("Counter Buffer B"), size: 32, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false }),
        ];
        
        let hash_table_size = 2097152; 
        
        let max_allowed_by_gpu = (limits.max_storage_buffer_binding_size as u64 / 4096) as u32;
        let block_budget_bytes: u64 = if is_integrated_gpu { 128 * 1024 * 1024 } else { 384 * 1024 * 1024 };
        let max_allowed_by_budget = (block_budget_bytes / 4096) as u32;
        let mut max_blocks = 520000;

        if max_blocks > max_allowed_by_gpu {
            println!("Rust Debug: Adjusting max_blocks from {} to {} due to GPU limits (max_storage_buffer_binding_size: {}).",
                max_blocks, max_allowed_by_gpu, limits.max_storage_buffer_binding_size);
            max_blocks = max_allowed_by_gpu;
        }
        if max_blocks > max_allowed_by_budget {
            println!(
                "Rust Debug: Adjusting max_blocks from {} to {} due to memory budget ({} MB).",
                max_blocks,
                max_allowed_by_budget,
                block_budget_bytes / (1024 * 1024)
            );
            max_blocks = max_allowed_by_budget;
        }
        let hash_keys_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Hash Keys Buffer"), size: (hash_table_size as u64 * 4), usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let hash_values_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Hash Values Buffer"), size: (hash_table_size as u64 * 4), usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false,
        });
        let clear_values_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Clear Values Buffer"),
            contents: bytemuck::cast_slice(&vec![0xFFFFFFFFu32; hash_table_size as usize]),
            usage: wgpu::BufferUsages::COPY_SRC,
        });
        let block_data_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Block Data Buffer"), size: (max_blocks as u64 * 1024 * 4), usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let active_blocks_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Active Blocks Buffer"), size: (max_blocks * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false,
        });
        let block_prim_info_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Block Prim Info Buffer"), size: (max_blocks * 8) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let global_prim_indices_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Global Prim Indices Buffer"), size: (16 * 1024 * 1024 * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let global_counter_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Global Counter Buffer"), size: 32, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let bvh_nodes_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("BVH Nodes Buffer"), size: (8192 * 32) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        
        let read_counter_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Read Counter"), size: 32, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let read_vertex_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Read Vertex"), size: v_size, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });
        let read_index_buffer = device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("Read Index"), size: i_size, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false,
        });

        // Build one combined shader module from shared WGSL sources.
        let common_src = include_str!("common.wgsl");
        let detect_src = include_str!("detect.wgsl");
        let mc_src = include_str!("marching_cubes.wgsl");
        let dc_src = include_str!("dual_contouring.wgsl");

        let start_comp = std::time::Instant::now();
        println!("Rust Debug: Compiling Shader Module (Unified)...");
        let combined_src = format!("{}\n{}\n{}\n{}", common_src, detect_src, mc_src, dc_src);
        device.push_error_scope(wgpu::ErrorFilter::Validation);
        let shader_module = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("SDF Combined Shader"),
            source: wgpu::ShaderSource::Wgsl(combined_src.into()),
        });
        if let Some(err) = device.pop_error_scope().await {
            crate::log_util::log_line(&format!("Rust Error: Combined shader module validation error: {}", err));
        }
        let compilation_info = shader_module.get_compilation_info().await;
        if !compilation_info.messages.is_empty() {
            for msg in &compilation_info.messages {
                crate::log_util::log_line(&format!(
                    "Rust Shader Diagnostic [{:?}]: {}", msg.message_type, msg.message
                ));
            }
        }
        println!("Rust Debug: Shader Module created in {:.2}s", start_comp.elapsed().as_secs_f32());

        // Compile compute pipelines and log progress to make stalls visible.
        println!("Rust Debug: Compiling Compute Pipelines...");
        
        let p_start = std::time::Instant::now();
        print!("Rust Debug:   -> Compiling MC Pipeline... ");
        use std::io::{Write}; std::io::stdout().flush().unwrap();
        device.push_error_scope(wgpu::ErrorFilter::Validation);
        let pipeline_mc = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("SDF MC Pipeline"), layout: Some(&pipeline_layout), module: &shader_module, entry_point: Some("main"), compilation_options: Default::default(), cache: pipeline_cache.as_ref(),
        });
        if let Some(err) = device.pop_error_scope().await {
            crate::log_util::log_line(&format!("Rust Error: MC Pipeline compile error: {}", err));
        }
        println!("Done ({:.2}s)", p_start.elapsed().as_secs_f32());

        let p_start = std::time::Instant::now();
        print!("Rust Debug:   -> Compiling Detect Pipeline... ");
        std::io::stdout().flush().unwrap();
        device.push_error_scope(wgpu::ErrorFilter::Validation);
        let pipeline_detect = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("DC Detect Pipeline"), layout: Some(&pipeline_layout), module: &shader_module, entry_point: Some("detect_pass"), compilation_options: Default::default(), cache: pipeline_cache.as_ref(),
        });
        if let Some(err) = device.pop_error_scope().await {
            crate::log_util::log_line(&format!("Rust Error: Detect Pipeline compile error: {}", err));
        }
        println!("Done ({:.2}s)", p_start.elapsed().as_secs_f32());

        let pipeline_dc_vertex = RwLock::new(None);
        let pipeline_dc_face = RwLock::new(None);
        let dc_last_error = RwLock::new(None);

        if compile_dc {
            let p_start = std::time::Instant::now();
            print!("Rust Debug:   -> Compiling DC Vertex Pipeline... ");
            std::io::stdout().flush().unwrap();
            device.push_error_scope(wgpu::ErrorFilter::Validation);
            let dc_v = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some("DC Vertex Pipeline"), layout: Some(&pipeline_layout), module: &shader_module, entry_point: Some("vertex_pass"), compilation_options: Default::default(), cache: pipeline_cache.as_ref(),
            });
            let vertex_err = device.pop_error_scope().await;
            *pipeline_dc_vertex.write().unwrap() = Some(dc_v);
            println!("Done ({:.2}s)", p_start.elapsed().as_secs_f32());

            let p_start = std::time::Instant::now();
            print!("Rust Debug:   -> Compiling DC Face Pipeline... ");
            std::io::stdout().flush().unwrap();
            device.push_error_scope(wgpu::ErrorFilter::Validation);
            let dc_f = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
                label: Some("DC Face Pipeline"), layout: Some(&pipeline_layout), module: &shader_module, entry_point: Some("face_pass"), compilation_options: Default::default(), cache: pipeline_cache.as_ref(),
            });
            let face_err = device.pop_error_scope().await;
            *pipeline_dc_face.write().unwrap() = Some(dc_f);
            println!("Done ({:.2}s)", p_start.elapsed().as_secs_f32());

            if let Some(err) = vertex_err {
                let msg = format!("Rust Error: DC Vertex Pipeline compile failed (eager): {}", err);
                crate::log_util::log_line(&msg);
                *dc_last_error.write().unwrap() = Some(msg);
            } else if let Some(err) = face_err {
                let msg = format!("Rust Error: DC Face Pipeline compile failed (eager): {}", err);
                crate::log_util::log_line(&msg);
                *dc_last_error.write().unwrap() = Some(msg);
            }
        } else {
            println!("Rust Debug: DC Pipelines compilation skipped (Deferred)");
        }

        // V15.9: Force a warm-up pass so the driver materializes the cache early.
        if cache_data.is_none() && pipeline_cache.is_some() {
            println!("Rust Debug: Executing dummy pass to force driver optimization...");
            let dummy_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
                label: Some("Warm-up Bind Group"),
                layout: &bind_group_layout,
                entries: &[
                    wgpu::BindGroupEntry { binding: 0, resource: config_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 1, resource: prim_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 2, resource: mc_table_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 3, resource: counter_buffers[0].as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 4, resource: vertex_buffers[0].as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 5, resource: index_buffers[0].as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 6, resource: hash_keys_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 7, resource: hash_values_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 8, resource: block_data_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 9, resource: active_blocks_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 10, resource: block_prim_info_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 11, resource: global_prim_indices_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 12, resource: global_counter_buffer.as_entire_binding() },
                    wgpu::BindGroupEntry { binding: 13, resource: bvh_nodes_buffer.as_entire_binding() },
                ],
            });

            let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("Warm-up Encoder") });
            {
                let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("Warm-up Pass"), timestamp_writes: None });
                cpass.set_pipeline(&pipeline_mc);
                cpass.set_bind_group(0, &dummy_bind_group, &[]);
                cpass.dispatch_workgroups(1, 1, 1);
            }
            queue.submit(Some(encoder.finish()));
            device.poll(wgpu::Maintain::Wait);
            println!("Rust Debug: Warm-up pass submitted.");
        }

        // Wait for compilation/cache finalization before reading pipeline cache data.
        let p_start = std::time::Instant::now();
        print!("Rust Debug: Waiting for driver to finalize compilation... ");
        std::io::stdout().flush().unwrap();
        
        device.poll(wgpu::Maintain::Wait);
        
        // Some Dx12 drivers finalize cache data asynchronously; retry a few times.
        let mut new_cache_data = None;
        for i in 0..5 {
            std::thread::sleep(std::time::Duration::from_millis(100 + i * 200));
            new_cache_data = pipeline_cache.as_ref().and_then(|c| c.get_data());
            if new_cache_data.is_some() { break; }
        }
        println!("Done in {:.2}s", p_start.elapsed().as_secs_f32());
        
        if let Some(data) = &new_cache_data {
            println!("Rust Debug: PipelineCache data retrieved ({} bytes)", data.len());
        } else {
            println!("Rust Debug: PipelineCache data size: None (Possible driver restriction or Dx12 optimization delay)");
        }

        let clear_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
            label: Some("Clear Buffer (Zeros)"),
            contents: bytemuck::cast_slice(&[0u32; 128]),
            usage: wgpu::BufferUsages::COPY_SRC,
        });

        Some((Self { 
            device, queue, 
            pipeline_layout, shader_module, pipeline_cache,
            pipeline_mc, pipeline_detect, pipeline_dc_vertex, pipeline_dc_face, dc_last_error,
            config_buffer, prim_buffer, mc_table_buffer, 
            vertex_buffers, index_buffers, counter_buffers,
            hash_keys_buffer, hash_values_buffer, block_data_buffer, clear_values_buffer,
            active_blocks_buffer,
            block_prim_info_buffer, global_prim_indices_buffer, global_counter_buffer,
            bvh_nodes_buffer,
            read_counter_buffer, read_vertex_buffer, read_index_buffer,
            back_buffer_index: AtomicUsize::new(0),
            max_verts,
            max_indices,
            max_blocks,
            max_tris,
            _clear_buffer: clear_buffer,
        }, new_cache_data))
    }

    pub async fn ensure_dc_ready(&self) {
        // Lazily compile DC pipelines on first use.
        if self.pipeline_dc_vertex.read().unwrap().is_some() { return; }

        let mut lock_v = self.pipeline_dc_vertex.write().unwrap();
        let mut lock_f = self.pipeline_dc_face.write().unwrap();

        if lock_v.is_some() { return; }

        crate::log_util::log_line("Rust Debug: Compiling DC Pipelines on-demand...");
        let p_start = std::time::Instant::now();

        self.device.push_error_scope(wgpu::ErrorFilter::Validation);
        crate::log_util::log_line("Rust Debug:   -> About to create DC Vertex Pipeline (entry_point=vertex_pass)...");
        let dc_v = self.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("DC Vertex Pipeline"), layout: Some(&self.pipeline_layout), module: &self.shader_module, entry_point: Some("vertex_pass"), compilation_options: Default::default(), cache: self.pipeline_cache.as_ref(),
        });
        crate::log_util::log_line("Rust Debug:   <- DC Vertex Pipeline create_compute_pipeline() returned.");
        let vertex_err = self.device.pop_error_scope().await;
        crate::log_util::log_line(&format!("Rust Debug: DC Vertex Pipeline created in {:.2}s", p_start.elapsed().as_secs_f32()));

        let p_start = std::time::Instant::now();
        self.device.push_error_scope(wgpu::ErrorFilter::Validation);
        crate::log_util::log_line("Rust Debug:   -> About to create DC Face Pipeline (entry_point=face_pass)...");
        let dc_f = self.device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("DC Face Pipeline"), layout: Some(&self.pipeline_layout), module: &self.shader_module, entry_point: Some("face_pass"), compilation_options: Default::default(), cache: self.pipeline_cache.as_ref(),
        });
        crate::log_util::log_line("Rust Debug:   <- DC Face Pipeline create_compute_pipeline() returned.");
        let face_err = self.device.pop_error_scope().await;
        crate::log_util::log_line(&format!("Rust Debug: DC Face Pipeline created in {:.2}s", p_start.elapsed().as_secs_f32()));

        let mut last_error = self.dc_last_error.write().unwrap();
        if let Some(err) = vertex_err {
            let msg = format!("Rust Error: DC Vertex Pipeline compile failed (on-demand): {}", err);
            crate::log_util::log_line(&msg);
            *last_error = Some(msg);
        } else if let Some(err) = face_err {
            let msg = format!("Rust Error: DC Face Pipeline compile failed (on-demand): {}", err);
            crate::log_util::log_line(&msg);
            *last_error = Some(msg);
        } else {
            *last_error = None;
        }

        *lock_v = Some(dc_v);
        *lock_f = Some(dc_f);
    }

    /// V15.9.9.1: Returns the latest DC pipeline compile diagnostic, if any.
    pub fn get_dc_last_error(&self) -> Option<String> {
        self.dc_last_error.read().unwrap().clone()
    }

    pub async fn generate_mesh_gpu(&self, primitives: &[GpuPrimitive], bvh_nodes: &[GpuBvhNode], mut config: GpuConfig) -> (Vec<f32>, Vec<u32>, GpuMeshStats) {
        config.max_tris = self.max_tris;
        config.hash_table_size = 2097152;
        let bb_idx = self.back_buffer_index.load(Ordering::SeqCst);

        self.queue.write_buffer(&self.config_buffer, 0, bytemuck::cast_slice(&[config]));
        self.queue.write_buffer(&self.prim_buffer, 0, bytemuck::cast_slice(primitives));
        self.queue.write_buffer(&self.bvh_nodes_buffer, 0, bytemuck::cast_slice(bvh_nodes));
        
        self.queue.write_buffer(&self.counter_buffers[bb_idx], 0, bytemuck::cast_slice(&[0u32; 8]));
        self.queue.write_buffer(&self.global_counter_buffer, 0, bytemuck::cast_slice(&[0u32; 4]));

        let bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("SDF Bind Group"),
            layout: &self.pipeline_mc.get_bind_group_layout(0),
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: self.config_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: self.prim_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 2, resource: self.mc_table_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 3, resource: self.counter_buffers[bb_idx].as_entire_binding() },
                wgpu::BindGroupEntry { binding: 4, resource: self.vertex_buffers[bb_idx].as_entire_binding() },
                wgpu::BindGroupEntry { binding: 5, resource: self.index_buffers[bb_idx].as_entire_binding() },
                wgpu::BindGroupEntry { binding: 6, resource: self.hash_keys_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 7, resource: self.hash_values_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 8, resource: self.block_data_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 9, resource: self.active_blocks_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 10, resource: self.block_prim_info_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 11, resource: self.global_prim_indices_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 12, resource: self.global_counter_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 13, resource: self.bvh_nodes_buffer.as_entire_binding() },
            ],
        });

        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        // V15.9.9.2: Clear only hash_values; hash_keys is no longer read by shaders.
        encoder.copy_buffer_to_buffer(&self.clear_values_buffer, 0, &self.hash_values_buffer, 0, config.hash_table_size as u64 * 4);

        {
            // 1. Detect Pass
            let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("SDF Detect Pass"), timestamp_writes: None });
            compute_pass.set_pipeline(&self.pipeline_detect);
            compute_pass.set_bind_group(0, &bind_group, &[]);
            let d = (config.res + 7) / 8;
            compute_pass.dispatch_workgroups(d, d, d);
        }

        encoder.copy_buffer_to_buffer(&self.counter_buffers[bb_idx], 0, &self.read_counter_buffer, 0, 32);
        self.queue.submit(Some(encoder.finish()));

        let active_count_raw = {
            let buffer_slice = self.read_counter_buffer.slice(..32);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let count = bytemuck::cast_slice::<u8, u32>(&data)[3]; // fourth u32
                drop(data); self.read_counter_buffer.unmap(); count
            } else { 0 }
        };
        let mut active_count = active_count_raw;
        if active_count > self.max_blocks {
            println!(
                "Rust Warning: Active block count {} exceeded capacity {}. Clamping.",
                active_count, self.max_blocks
            );
            active_count = self.max_blocks;
        }

        if active_count == 0 {
            return (vec![], vec![], GpuMeshStats {
                algo: "MC",
                active_blocks: active_count,
                active_blocks_raw: active_count_raw,
                max_blocks: self.max_blocks,
                max_tris: self.max_tris,
                max_verts: self.max_verts,
                max_indices: self.max_indices,
                ..Default::default()
            });
        }

        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        
        let use_dc = (config.symmetry & 0x10u32) != 0u32; // UI flag for DC mode
        if use_dc {
            self.ensure_dc_ready().await;
            let dc_v_lock = self.pipeline_dc_vertex.read().unwrap();
            let dc_f_lock = self.pipeline_dc_face.read().unwrap();
            
            if let (Some(dc_v), Some(dc_f)) = (&*dc_v_lock, &*dc_f_lock) {
                {
                    // 2. Dual Contouring Vertex Pass
                    let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("DC Vertex Pass"), timestamp_writes: None });
                    compute_pass.set_pipeline(dc_v);
                    compute_pass.set_bind_group(0, &bind_group, &[]);
                    let (gx, gy) = get_dispatch_dims(active_count);
                    compute_pass.dispatch_workgroups(gx, gy, 1);
                }
                {
                    // 3. Dual Contouring Face Pass
                    let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("DC Face Pass"), timestamp_writes: None });
                    compute_pass.set_pipeline(dc_f);
                    compute_pass.set_bind_group(0, &bind_group, &[]);
                    let (gx, gy) = get_dispatch_dims(active_count);
                    compute_pass.dispatch_workgroups(gx, gy, 1);
                }
            }
        } else {
            {
                // 2. Sparse MC Pass
                let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("Sparse MC Pass"), timestamp_writes: None });
                compute_pass.set_pipeline(&self.pipeline_mc);
                compute_pass.set_bind_group(0, &bind_group, &[]);
                let (gx, gy) = get_dispatch_dims(active_count);
                compute_pass.dispatch_workgroups(gx, gy, 1);
            }
        }

        encoder.copy_buffer_to_buffer(&self.counter_buffers[bb_idx], 0, &self.read_counter_buffer, 0, 32);
        self.queue.submit(Some(encoder.finish()));

        let counts = {
            let buffer_slice = self.read_counter_buffer.slice(..32);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let c = bytemuck::cast_slice::<u8, u32>(&data).to_vec();
                drop(data); self.read_counter_buffer.unmap(); c
            } else { vec![0; 8] }
        };

        let tri_count_raw = counts[0];
        let tri_count = tri_count_raw.min(self.max_tris);
        let missing_blocks = counts[4];
        let empty_voxels = counts[5];

        let stats = GpuMeshStats {
            algo: "MC",
            active_blocks: active_count,
            active_blocks_raw: active_count_raw,
            tris_or_faces: tri_count,
            tris_or_faces_raw: tri_count_raw,
            verts: tri_count * 3,
            verts_raw: tri_count_raw.saturating_mul(3),
            indices: tri_count * 3,
            indices_raw: tri_count_raw.saturating_mul(3),
            missing_ptrs: missing_blocks,
            empty_voxels,
            max_blocks: self.max_blocks,
            max_tris: self.max_tris,
            max_verts: self.max_verts,
            max_indices: self.max_indices,
            ..Default::default()
        };

        println!("Rust Debug: Sparse MC Complete. {}", stats.summary());

        if tri_count == 0 { return (vec![], vec![], stats); }

        let read_v_size = (tri_count * 3 * 11 * 4) as wgpu::BufferAddress;
        let read_i_size = (tri_count * 3 * 4) as wgpu::BufferAddress;
        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        encoder.copy_buffer_to_buffer(&self.vertex_buffers[bb_idx], 0, &self.read_vertex_buffer, 0, read_v_size);
        encoder.copy_buffer_to_buffer(&self.index_buffers[bb_idx], 0, &self.read_index_buffer, 0, read_i_size);
        self.queue.submit(Some(encoder.finish()));

        let verts = {
            let buffer_slice = self.read_vertex_buffer.slice(..read_v_size);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let v = bytemuck::cast_slice::<u8, f32>(&data).to_vec();
                drop(data); self.read_vertex_buffer.unmap(); v
            } else { vec![] }
        };

        let indices = {
            let buffer_slice = self.read_index_buffer.slice(..read_i_size);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let i = bytemuck::cast_slice::<u8, u32>(&data).to_vec();
                drop(data); self.read_index_buffer.unmap(); i
            } else { vec![] }
        };

        (verts, indices, stats)
    }

    pub async fn generate_mesh_gpu_chunked_mc(
        &self,
        primitives: &[GpuPrimitive],
        bvh_nodes: &[GpuBvhNode],
        base_config: GpuConfig,
        chunk_cells: u32,
    ) -> (Vec<f32>, Vec<u32>, GpuMeshStats) {
        let full_res = base_config.res.max(1);
        let chunk_cells = chunk_cells.max(8).min(full_res);
        let world_step = base_config.domain_size / full_res as f32;
        let full_min = -base_config.domain_size * 0.5;

        let mut all_verts = Vec::new();
        let mut all_indices = Vec::new();
        let mut v_offset = 0u32;
        let mut merged_stats = GpuMeshStats {
            algo: "GPU_CHUNKED_MC",
            max_blocks: u32::MAX,
            max_tris: u32::MAX,
            max_verts: u32::MAX,
            max_indices: u32::MAX,
            ..Default::default()
        };

        let mut x0 = 0u32;
        while x0 < full_res {
            let x_cells = (full_res - x0).min(chunk_cells);
            let mut y0 = 0u32;
            while y0 < full_res {
                let y_cells = (full_res - y0).min(chunk_cells);
                let mut z0 = 0u32;
                while z0 < full_res {
                    let z_cells = (full_res - z0).min(chunk_cells);
                    let local_cells = x_cells.max(y_cells).max(z_cells).saturating_add(2);
                    let local_domain = world_step * local_cells as f32;
                    let center = [
                        full_min + (x0 as f32 + x_cells as f32 * 0.5) * world_step,
                        full_min + (y0 as f32 + y_cells as f32 * 0.5) * world_step,
                        full_min + (z0 as f32 + z_cells as f32 * 0.5) * world_step,
                        0.0,
                    ];
                    let mut cfg = base_config;
                    cfg.res = local_cells;
                    cfg.domain_size = local_domain;
                    cfg.domain_origin = center;

                    let (verts, indices, stats) = self.generate_mesh_gpu(primitives, bvh_nodes, cfg).await;
                    let core_min = [
                        full_min + x0 as f32 * world_step,
                        full_min + y0 as f32 * world_step,
                        full_min + z0 as f32 * world_step,
                    ];
                    let core_max = [
                        full_min + (x0 + x_cells) as f32 * world_step,
                        full_min + (y0 + y_cells) as f32 * world_step,
                        full_min + (z0 + z_cells) as f32 * world_step,
                    ];
                    let include_max = [
                        x0 + x_cells == full_res,
                        y0 + y_cells == full_res,
                        z0 + z_cells == full_res,
                    ];
                    let (verts, indices, dropped_tris) = filter_mesh_to_core_bounds(verts, indices, core_min, core_max, include_max);
                    merged_stats.filtered_tris = merged_stats.filtered_tris.saturating_add(dropped_tris);
                    merged_stats.chunks_total = merged_stats.chunks_total.saturating_add(1);
                    if !verts.is_empty() || !indices.is_empty() {
                        merged_stats.chunks_nonempty = merged_stats.chunks_nonempty.saturating_add(1);
                    } else {
                        merged_stats.chunks_empty = merged_stats.chunks_empty.saturating_add(1);
                    }
                    if matches!(stats.health(), "CAPACITY_LIMITED" | "BLOCK_OR_PRIM_FALLBACK") {
                        merged_stats.chunks_problem = merged_stats.chunks_problem.saturating_add(1);
                    }
                    merged_stats.merge_from(&stats);
                    all_verts.extend(verts);
                    for idx in indices {
                        all_indices.push(idx + v_offset);
                    }
                    v_offset = (all_verts.len() / 11) as u32;

                    z0 += z_cells;
                }
                y0 += y_cells;
            }
            x0 += x_cells;
        }

        merged_stats.tris_or_faces = (all_indices.len() / 3) as u32;
        merged_stats.verts = (all_verts.len() / 11) as u32;
        merged_stats.indices = all_indices.len() as u32;
        merged_stats.tris_or_faces_raw = merged_stats.tris_or_faces;
        merged_stats.verts_raw = merged_stats.verts;
        merged_stats.indices_raw = merged_stats.indices;

        (all_verts, all_indices, merged_stats)
    }

    pub async fn generate_mesh_gpu_dc(&self, primitives: &[GpuPrimitive], bvh_nodes: &[GpuBvhNode], mut config: GpuConfig) -> (Vec<f32>, Vec<u32>, GpuMeshStats) {
        let bb_idx = self.back_buffer_index.load(Ordering::SeqCst);

        config.max_tris = self.max_tris;
        config.hash_table_size = 2097152;

        self.queue.write_buffer(&self.config_buffer, 0, bytemuck::cast_slice(&[config]));
        self.queue.write_buffer(&self.prim_buffer, 0, bytemuck::cast_slice(primitives));
        self.queue.write_buffer(&self.bvh_nodes_buffer, 0, bytemuck::cast_slice(bvh_nodes));
        self.queue.write_buffer(&self.counter_buffers[bb_idx], 0, bytemuck::cast_slice(&[0u32; 8]));
        self.queue.write_buffer(&self.global_counter_buffer, 0, bytemuck::cast_slice(&[0u32; 4]));
        
        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        // V15.9.9.2: Clear only hash_values; hash_keys is no longer read by shaders.
        encoder.copy_buffer_to_buffer(&self.clear_values_buffer, 0, &self.hash_values_buffer, 0, config.hash_table_size as u64 * 4);

        self.ensure_dc_ready().await;
        let dc_v_lock = self.pipeline_dc_vertex.read().unwrap();
        let dc_f_lock = self.pipeline_dc_face.read().unwrap();

        let (dc_v, dc_f) = if let (Some(v), Some(f)) = (&*dc_v_lock, &*dc_f_lock) {
            (v, f)
        } else {
            return (vec![], vec![], GpuMeshStats {
                algo: "DC",
                max_blocks: self.max_blocks,
                max_tris: self.max_tris,
                max_verts: self.max_verts,
                max_indices: self.max_indices,
                ..Default::default()
            });
        };

        let bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("DC Bind Group"),
            layout: &dc_v.get_bind_group_layout(0),
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: self.config_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: self.prim_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 2, resource: self.mc_table_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 3, resource: self.counter_buffers[bb_idx].as_entire_binding() },
                wgpu::BindGroupEntry { binding: 4, resource: self.vertex_buffers[bb_idx].as_entire_binding() },
                wgpu::BindGroupEntry { binding: 5, resource: self.index_buffers[bb_idx].as_entire_binding() },
                wgpu::BindGroupEntry { binding: 6, resource: self.hash_keys_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 7, resource: self.hash_values_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 8, resource: self.block_data_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 9, resource: self.active_blocks_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 10, resource: self.block_prim_info_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 11, resource: self.global_prim_indices_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 12, resource: self.global_counter_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 13, resource: self.bvh_nodes_buffer.as_entire_binding() },
            ],
        });

        {
            let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("DC Detect Pass"), timestamp_writes: None });
            compute_pass.set_pipeline(&self.pipeline_detect);
            compute_pass.set_bind_group(0, &bind_group, &[]);
            let d = (config.res + 7) / 8;
            println!("Rust Debug: Dispatching DC Detect Pass. Res: {}, Groups: ({}, {}, {})", config.res, d, d, d);
            compute_pass.dispatch_workgroups(d, d, d);
        }

        encoder.copy_buffer_to_buffer(&self.counter_buffers[bb_idx], 0, &self.read_counter_buffer, 0, 32);
        self.queue.submit(Some(encoder.finish()));

        // At this point only Detect Pass has run, so only active_count (counters[3]) is valid.
        // Vertex/index counters are read after the Vertex/Face passes below.
        let active_count_raw = {
            let buffer_slice = self.read_counter_buffer.slice(..);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let c = bytemuck::cast_slice::<u8, u32>(&data);
                let res = c[3];
                drop(data); self.read_counter_buffer.unmap(); res
            } else { 0 }
        };
        let mut active_count = active_count_raw;
        if active_count > self.max_blocks {
            println!(
                "Rust Warning: DC active block count {} exceeded capacity {}. Clamping.",
                active_count, self.max_blocks
            );
            active_count = self.max_blocks;
        }

        if active_count == 0 {
            println!("Rust Debug: GPU DC returned empty (Active Blocks: 0). Falling back to CPU...");
            return (vec![], vec![], GpuMeshStats {
                algo: "DC",
                active_blocks: active_count,
                active_blocks_raw: active_count_raw,
                max_blocks: self.max_blocks,
                max_tris: self.max_tris,
                max_verts: self.max_verts,
                max_indices: self.max_indices,
                ..Default::default()
            });
        }

        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        {
            let mut compute_pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: Some("DC Sparse Pass"), timestamp_writes: None });
            compute_pass.set_pipeline(dc_v);
            compute_pass.set_bind_group(0, &bind_group, &[]);
            let (gx, gy) = get_dispatch_dims(active_count);
            println!("Rust Debug: Dispatching DC Vertex/Face Pass. Active Blocks: {}, Groups: ({}, {})", active_count, gx, gy);
            compute_pass.dispatch_workgroups(gx, gy, 1);
            compute_pass.set_pipeline(dc_f);
            compute_pass.dispatch_workgroups(gx, gy, 1);
        }

        // After Vertex/Face Passes, read counters[0]/[1] as vertex/index counts.
        encoder.copy_buffer_to_buffer(&self.counter_buffers[bb_idx], 0, &self.read_counter_buffer, 0, 32);
        self.queue.submit(Some(encoder.finish()));

        let (v_count_raw, i_count_raw) = {
            let buffer_slice = self.read_counter_buffer.slice(..);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let c = bytemuck::cast_slice::<u8, u32>(&data);
                let res = (c[0], c[1]);
                drop(data); self.read_counter_buffer.unmap(); res
            } else { (0, 0) }
        };
        let v_count = v_count_raw.min(self.max_verts);
        let i_count = i_count_raw.min(self.max_indices);
        if v_count != v_count_raw || i_count != i_count_raw {
            println!(
                "Rust Warning: DC vertex/index count clamped. V: {} -> {}, I: {} -> {}",
                v_count_raw, v_count, i_count_raw, i_count
            );
        }

        if v_count == 0 || i_count == 0 {
            println!("Rust Debug: GPU DC returned empty (Active Blocks: {}, Verts: {}, Indices: {}). Falling back to CPU...", active_count, v_count, i_count);
            return (vec![], vec![], GpuMeshStats {
                algo: "DC",
                active_blocks: active_count,
                active_blocks_raw: active_count_raw,
                verts: v_count,
                verts_raw: v_count_raw,
                indices: i_count,
                indices_raw: i_count_raw,
                max_blocks: self.max_blocks,
                max_tris: self.max_tris,
                max_verts: self.max_verts,
                max_indices: self.max_indices,
                ..Default::default()
            });
        }

        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        let read_v_size = (v_count * 11 * 4) as wgpu::BufferAddress;
        let read_i_size = (i_count * 4) as wgpu::BufferAddress;
        encoder.copy_buffer_to_buffer(&self.vertex_buffers[bb_idx], 0, &self.read_vertex_buffer, 0, read_v_size);
        encoder.copy_buffer_to_buffer(&self.index_buffers[bb_idx], 0, &self.read_index_buffer, 0, read_i_size);
        self.queue.submit(Some(encoder.finish()));

        let stats = GpuMeshStats {
            algo: "DC",
            active_blocks: active_count,
            active_blocks_raw: active_count_raw,
            tris_or_faces: i_count / 3,
            tris_or_faces_raw: i_count_raw / 3,
            verts: v_count,
            verts_raw: v_count_raw,
            indices: i_count,
            indices_raw: i_count_raw,
            max_blocks: self.max_blocks,
            max_tris: self.max_tris,
            max_verts: self.max_verts,
            max_indices: self.max_indices,
            ..Default::default()
        };

        println!("Rust Debug: Sparse DC Complete. {}", stats.summary());

        let verts = {
            let buffer_slice = self.read_vertex_buffer.slice(..read_v_size);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let v = bytemuck::cast_slice::<u8, f32>(&data).to_vec();
                drop(data); self.read_vertex_buffer.unmap(); v
            } else { vec![] }
        };

        let indices = {
            let buffer_slice = self.read_index_buffer.slice(..read_i_size);
            let (sender, receiver) = futures_intrusive::channel::shared::oneshot_channel();
            buffer_slice.map_async(wgpu::MapMode::Read, move |v| sender.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            if let Some(Ok(())) = receiver.receive().await {
                let data = buffer_slice.get_mapped_range();
                let i = bytemuck::cast_slice::<u8, u32>(&data).to_vec();
                drop(data); self.read_index_buffer.unmap(); i
            } else { vec![] }
        };

        (verts, indices, stats)
    }

    pub async fn generate_mesh_gpu_chunked_dc(
        &self,
        primitives: &[GpuPrimitive],
        bvh_nodes: &[GpuBvhNode],
        base_config: GpuConfig,
        chunk_cells: u32,
    ) -> (Vec<f32>, Vec<u32>, GpuMeshStats) {
        let full_res = base_config.res.max(1);
        let chunk_cells = chunk_cells.max(8).min(full_res);
        let world_step = base_config.domain_size / full_res as f32;
        let full_min = -base_config.domain_size * 0.5;

        let mut all_verts = Vec::new();
        let mut all_indices = Vec::new();
        let mut v_offset = 0u32;
        let mut merged_stats = GpuMeshStats {
            algo: "GPU_CHUNKED_DC",
            max_blocks: u32::MAX,
            max_tris: u32::MAX,
            max_verts: u32::MAX,
            max_indices: u32::MAX,
            ..Default::default()
        };

        let mut x0 = 0u32;
        while x0 < full_res {
            let x_cells = (full_res - x0).min(chunk_cells);
            let mut y0 = 0u32;
            while y0 < full_res {
                let y_cells = (full_res - y0).min(chunk_cells);
                let mut z0 = 0u32;
                while z0 < full_res {
                    let z_cells = (full_res - z0).min(chunk_cells);
                    let local_cells = x_cells.max(y_cells).max(z_cells).saturating_add(2);
                    let local_domain = world_step * local_cells as f32;
                    let center = [
                        full_min + (x0 as f32 + x_cells as f32 * 0.5) * world_step,
                        full_min + (y0 as f32 + y_cells as f32 * 0.5) * world_step,
                        full_min + (z0 as f32 + z_cells as f32 * 0.5) * world_step,
                        0.0,
                    ];
                    let mut cfg = base_config;
                    cfg.res = local_cells;
                    cfg.domain_size = local_domain;
                    cfg.domain_origin = center;

                    let (verts, indices, stats) = self.generate_mesh_gpu_dc(primitives, bvh_nodes, cfg).await;
                    let core_min = [
                        full_min + x0 as f32 * world_step,
                        full_min + y0 as f32 * world_step,
                        full_min + z0 as f32 * world_step,
                    ];
                    let core_max = [
                        full_min + (x0 + x_cells) as f32 * world_step,
                        full_min + (y0 + y_cells) as f32 * world_step,
                        full_min + (z0 + z_cells) as f32 * world_step,
                    ];
                    let include_max = [
                        x0 + x_cells == full_res,
                        y0 + y_cells == full_res,
                        z0 + z_cells == full_res,
                    ];
                    let (verts, indices, dropped_tris) = filter_mesh_to_core_bounds(verts, indices, core_min, core_max, include_max);
                    merged_stats.filtered_tris = merged_stats.filtered_tris.saturating_add(dropped_tris);
                    merged_stats.chunks_total = merged_stats.chunks_total.saturating_add(1);
                    if !verts.is_empty() || !indices.is_empty() {
                        merged_stats.chunks_nonempty = merged_stats.chunks_nonempty.saturating_add(1);
                    } else {
                        merged_stats.chunks_empty = merged_stats.chunks_empty.saturating_add(1);
                    }
                    if matches!(stats.health(), "CAPACITY_LIMITED" | "BLOCK_OR_PRIM_FALLBACK") {
                        merged_stats.chunks_problem = merged_stats.chunks_problem.saturating_add(1);
                    }
                    merged_stats.merge_from(&stats);
                    all_verts.extend(verts);
                    for idx in indices {
                        all_indices.push(idx + v_offset);
                    }
                    v_offset = (all_verts.len() / 11) as u32;

                    z0 += z_cells;
                }
                y0 += y_cells;
            }
            x0 += x_cells;
        }

        merged_stats.tris_or_faces = (all_indices.len() / 3) as u32;
        merged_stats.verts = (all_verts.len() / 11) as u32;
        merged_stats.indices = all_indices.len() as u32;
        merged_stats.tris_or_faces_raw = merged_stats.tris_or_faces;
        merged_stats.verts_raw = merged_stats.verts;
        merged_stats.indices_raw = merged_stats.indices;

        (all_verts, all_indices, merged_stats)
    }

    pub fn swap_buffers(&self) {
        let current = self.back_buffer_index.load(Ordering::SeqCst);
        self.back_buffer_index.store(1 - current, Ordering::SeqCst);
    }
}

