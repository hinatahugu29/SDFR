use wgpu::util::DeviceExt;
use std::sync::{atomic::{AtomicUsize, Ordering}, RwLock};
use nalgebra::{Vector3, Quaternion, UnitQuaternion};

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuPrimitive {
    pub center_and_shape: [f32; 4], // [x, y, z, shape_type]
    pub rotation: [f32; 4],         // [x, y, z, w]
    pub size_and_op: [f32; 4],      // [sx, sy, sz, operation]
    pub params: [f32; 4],           // [radius, smoothness, metallic, roughness]
    pub noise_params: [f32; 4],     // [strength, scale, color_r, color_g]
    pub color_b_and_extra: [f32; 4], // [color_b, unused, unused, unused]
    pub layout_data1: [f32; 4],     // [mode_flags, p1, p2, p3]
    pub layout_data2: [f32; 4],     // [p4, p5, p6, p7]
    pub layout_data3: [f32; 4],     // [p8, p9, p10, p11]
    pub layout_data4: [f32; 4],     // [p12, p13, p14, p15]
    pub extra_params: [f32; 4],     // [p1, p2, p3, p4]
    pub deform_data1: [f32; 4],     // [flags, stretch_x, stretch_y, stretch_z]
    pub deform_data2: [f32; 4],     // [bend_angle, bend_axis, bend_center, twist_angle]
    pub deform_data3: [f32; 4],     // [twist_axis, twist_center, taper_factor, taper_axis]
    pub deform_data4: [f32; 4],     // [taper_center, 0, 0, 0]
}

impl Default for GpuPrimitive {
    fn default() -> Self {
        Self {
            center_and_shape: [0.0, 0.0, 0.0, 0.0],
            rotation: [0.0, 0.0, 0.0, 1.0],
            size_and_op: [1.0, 1.0, 1.0, 0.0],
            params: [0.0, 0.05, 0.0, 0.5],
            noise_params: [0.0, 1.0, 1.0, 1.0],
            color_b_and_extra: [1.0, 0.0, 0.0, 0.0],
            layout_data1: [0.0; 4],
            layout_data2: [0.0; 4],
            layout_data3: [0.0; 4],
            layout_data4: [0.0; 4],
            extra_params: [0.0; 4],
            deform_data1: [0.0; 4],
            deform_data2: [0.0; 4],
            deform_data3: [0.0; 4],
            deform_data4: [0.0; 4],
        }
    }
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuTriangle {
    pub v0: [f32; 4],
    pub v1: [f32; 4],
    pub v2: [f32; 4],
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuConfig {
    pub res: u32,
    pub domain_size: f32,
    pub num_primitives: u32,
    pub num_triangles: u32,
    pub symmetry: u32,
    pub hash_table_size: u32,
    pub block_size: u32,
    pub max_tris: u32,
}

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct GpuBvhNode {
    pub min: [f32; 4],
    pub max: [f32; 4],
}

pub struct SdfGpuContext {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    
    pub pipeline_mc: wgpu::ComputePipeline,
    pub pipeline_detect: wgpu::ComputePipeline,
    
    pub bind_group_layout: wgpu::BindGroupLayout,
    pub main_bind_group: wgpu::BindGroup,

    pub config_buffer: wgpu::Buffer,
    pub prim_buffer: wgpu::Buffer,
    pub triangle_buffer: wgpu::Buffer,
    pub mc_table_buffer: wgpu::Buffer,
    
    pub vertex_buffers: [wgpu::Buffer; 1], // Simplified to single buffer for now
    pub index_buffers: [wgpu::Buffer; 1],
    pub counter_buffers: [wgpu::Buffer; 1],
    
    pub active_blocks_buffer: wgpu::Buffer,
    pub block_prim_info_buffer: wgpu::Buffer,
    pub global_prim_indices_buffer: wgpu::Buffer,
    pub global_counter_buffer: wgpu::Buffer,
    
    pub hash_keys_buffer: wgpu::Buffer,
    pub hash_values_buffer: wgpu::Buffer,
    pub block_data_buffer: wgpu::Buffer,
    pub read_counter_buffer: wgpu::Buffer,
    pub read_vertex_buffer: wgpu::Buffer,
    pub read_index_buffer: wgpu::Buffer,
    pub max_tris: u32,
    pub bvh_nodes_buffer: wgpu::Buffer,
}

impl SdfGpuContext {
    pub async fn new(mc_table: &[i32]) -> Self {
        let instance = wgpu::Instance::new(wgpu::InstanceDescriptor {
            backends: wgpu::Backends::PRIMARY,
            ..Default::default()
        });
        let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            ..Default::default()
        }).await.expect("Failed to find wgpu adapter");

        let (device, queue) = adapter.request_device(&wgpu::DeviceDescriptor {
            label: None,
            required_features: wgpu::Features::FLOAT32_FILTERABLE,
            required_limits: wgpu::Limits {
                max_storage_buffers_per_shader_stage: 16,
                ..wgpu::Limits::default()
            },
            memory_hints: wgpu::MemoryHints::default(),
        }, None).await.expect("Failed to create wgpu device");

        let max_tris = 500_000;
        let max_verts = max_tris * 3;
        let max_blocks = 16384;
        let hash_size = 131072;

        // Buffers
        let config_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: 64, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let prim_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (std::mem::size_of::<GpuPrimitive>() * 1024) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let triangle_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (std::mem::size_of::<GpuTriangle>() * 100_000) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let mc_table_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor { label: None, contents: bytemuck::cast_slice(mc_table), usage: wgpu::BufferUsages::STORAGE });

        let counter_buffers = [device.create_buffer(&wgpu::BufferDescriptor { label: None, size: 64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false })];
        let vertex_buffers = [device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_verts * 11 * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false })];
        let index_buffers = [device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_tris * 3 * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false })];

        let hash_keys_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (hash_size * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let hash_values_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (hash_size * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let block_data_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_blocks * 1024 * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });

        let active_blocks_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_blocks * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false });
        let block_prim_info_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_blocks * 8) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false });
        let global_prim_indices_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_blocks * 64 * 4) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC, mapped_at_creation: false });
        let global_counter_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: 16, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });

        let read_counter_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: 64, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let read_vertex_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_verts * 11 * 4) as u64, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let read_index_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: None, size: (max_tris * 3 * 4) as u64, usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });

        // Shaders
        let shader_common = include_str!("../rust_gpu_sdf_addon/shaders/common.wgsl");
        let shader_mc = include_str!("../rust_gpu_sdf_addon/shaders/marching_cubes.wgsl");
        let shader_detect = include_str!("../rust_gpu_sdf_addon/shaders/detect.wgsl");

        let mod_mc = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: None, source: wgpu::ShaderSource::Wgsl(format!("{}\n{}", shader_common, shader_mc).into()) });
        let mod_detect = device.create_shader_module(wgpu::ShaderModuleDescriptor { label: None, source: wgpu::ShaderSource::Wgsl(format!("{}\n{}", shader_common, shader_detect).into()) });

        // Bind Group Layout
        let bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: None,
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
                wgpu::BindGroupLayoutEntry { binding: 14, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Texture { multisampled: false, view_dimension: wgpu::TextureViewDimension::D3, sample_type: wgpu::TextureSampleType::Float { filterable: true } }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 15, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Sampler(wgpu::SamplerBindingType::Filtering), count: None },
                wgpu::BindGroupLayoutEntry { binding: 16, visibility: wgpu::ShaderStages::COMPUTE, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None },
            ],
        });

        let bvh_nodes_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: Some("BVH Nodes Buffer"), size: (100000 * 32) as u64, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        
        let volume_texture = device.create_texture(&wgpu::TextureDescriptor {
            label: Some("MeshVolume"),
            size: wgpu::Extent3d { width: 256, height: 256, depth_or_array_layers: 256 },
            mip_level_count: 1,
            sample_count: 1,
            dimension: wgpu::TextureDimension::D3,
            format: wgpu::TextureFormat::R32Float,
            usage: wgpu::TextureUsages::STORAGE_BINDING | wgpu::TextureUsages::TEXTURE_BINDING | wgpu::TextureUsages::COPY_DST,
            view_formats: &[],
        });
        let volume_view = volume_texture.create_view(&wgpu::TextureViewDescriptor::default());
        let volume_sampler = device.create_sampler(&wgpu::SamplerDescriptor {
            address_mode_u: wgpu::AddressMode::ClampToEdge,
            address_mode_v: wgpu::AddressMode::ClampToEdge,
            address_mode_w: wgpu::AddressMode::ClampToEdge,
            mag_filter: wgpu::FilterMode::Linear,
            min_filter: wgpu::FilterMode::Linear,
            ..Default::default()
        });

        let main_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: None,
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
                wgpu::BindGroupEntry { binding: 14, resource: wgpu::BindingResource::TextureView(&volume_view) },
                wgpu::BindGroupEntry { binding: 15, resource: wgpu::BindingResource::Sampler(&volume_sampler) },
                wgpu::BindGroupEntry { binding: 16, resource: triangle_buffer.as_entire_binding() },
            ],
        });

        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor { label: None, bind_group_layouts: &[&bind_group_layout], push_constant_ranges: &[] });
        let pipeline_mc = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: None,
            layout: Some(&pipeline_layout),
            module: &mod_mc,
            entry_point: Some("main"),
            compilation_options: wgpu::PipelineCompilationOptions::default(),
            cache: None,
        });
        let pipeline_detect = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: None,
            layout: Some(&pipeline_layout),
            module: &mod_detect,
            entry_point: Some("detect_pass"),
            compilation_options: wgpu::PipelineCompilationOptions::default(),
            cache: None,
        });

        Self {
            device,
            queue,
            pipeline_mc,
            pipeline_detect,
            bind_group_layout,
            main_bind_group,
            config_buffer,
            prim_buffer,
            triangle_buffer,
            mc_table_buffer,
            vertex_buffers,
            index_buffers,
            counter_buffers,
            active_blocks_buffer,
            block_prim_info_buffer,
            global_prim_indices_buffer,
            global_counter_buffer,
            hash_keys_buffer,
            hash_values_buffer,
            block_data_buffer,
            read_counter_buffer,
            read_vertex_buffer,
            read_index_buffer,
            max_tris,
            bvh_nodes_buffer,
        }
    }

    pub async fn run_pipeline_with_bvh(&mut self, prims: &[GpuPrimitive], tris: &[GpuTriangle], bvh: &[GpuBvhNode], config: &GpuConfig) -> (Vec<f32>, Vec<u32>) {
        // Safety check for BVH nodes buffer
        let bvh_to_write = if bvh.len() > 100000 {
            println!("Monster Engine Warning: BVH nodes ({}) exceeds buffer capacity (100000). Truncating.", bvh.len());
            &bvh[0..100000]
        } else {
            bvh
        };
        self.queue.write_buffer(&self.bvh_nodes_buffer, 0, bytemuck::cast_slice(bvh_to_write));
        self.run_pipeline(prims, tris, config).await
    }

    fn get_dispatch_dims(&self, count: u32) -> (u32, u32) {
        if count <= 65535 { (count, 1) }
        else { (65535, (count + 65534) / 65535) }
    }

    pub async fn run_pipeline(&mut self, prims: &[GpuPrimitive], tris: &[GpuTriangle], config: &GpuConfig) -> (Vec<f32>, Vec<u32>) {
        self.queue.write_buffer(&self.config_buffer, 0, bytemuck::bytes_of(config));
        self.queue.write_buffer(&self.prim_buffer, 0, bytemuck::cast_slice(prims));
        if !tris.is_empty() {
            // Safety check for Triangle buffer
        let tris_to_write = if tris.len() > 100000 {
            println!("Monster Engine Warning: Triangles ({}) exceeds buffer capacity (100000). Truncating.", tris.len());
            &tris[0..100000]
        } else {
            tris
        };
        self.queue.write_buffer(&self.triangle_buffer, 0, bytemuck::cast_slice(tris_to_write));
        }

        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        
        // Reset counters
        encoder.clear_buffer(&self.counter_buffers[0], 0, None);
        encoder.clear_buffer(&self.global_counter_buffer, 0, None);

        let blocks_per_dim = (config.res + 7) / 8;

        {
            let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: None, timestamp_writes: None });
            cpass.set_pipeline(&self.pipeline_detect);
            cpass.set_bind_group(0, &self.main_bind_group, &[]);
            cpass.dispatch_workgroups(blocks_per_dim, blocks_per_dim, blocks_per_dim);
        }

        // Active Blocks を読み戻して Dispatch 数を決定する
        encoder.copy_buffer_to_buffer(&self.counter_buffers[0], 0, &self.read_counter_buffer, 0, 64);
        self.queue.submit(Some(encoder.finish()));
        
        let active_count = {
            let (tx, rx) = std::sync::mpsc::channel();
            let slice = self.read_counter_buffer.slice(..);
            slice.map_async(wgpu::MapMode::Read, move |v| tx.send(v).unwrap());
            self.device.poll(wgpu::Maintain::Wait);
            rx.recv().unwrap().expect("Failed to map counter buffer");
            let view = slice.get_mapped_range();
            let data: &[u32] = bytemuck::cast_slice(&view);
            let count = data[3]; // counters[3] = active_blocks
            drop(view);
            self.read_counter_buffer.unmap();
            count
        };

        if active_count == 0 { return (vec![], vec![]); }

        let mut encoder = self.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
        {
            let (gx, gy) = self.get_dispatch_dims(active_count);
            let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor { label: None, timestamp_writes: None });
            cpass.set_pipeline(&self.pipeline_mc);
            cpass.set_bind_group(0, &self.main_bind_group, &[]);
            cpass.dispatch_workgroups(gx, gy, 1); 
        }

        encoder.copy_buffer_to_buffer(&self.counter_buffers[0], 0, &self.read_counter_buffer, 0, 64);
        encoder.copy_buffer_to_buffer(&self.vertex_buffers[0], 0, &self.read_vertex_buffer, 0, (self.max_tris * 3 * 11 * 4) as u64);
        encoder.copy_buffer_to_buffer(&self.index_buffers[0], 0, &self.read_index_buffer, 0, (self.max_tris * 3 * 4) as u64);

        self.queue.submit(Some(encoder.finish()));

        let (tx, rx) = std::sync::mpsc::channel();
        let counter_slice = self.read_counter_buffer.slice(..);
        counter_slice.map_async(wgpu::MapMode::Read, move |v| tx.send(v).unwrap());
        self.device.poll(wgpu::Maintain::Wait);
        rx.recv().unwrap().expect("Failed to map counter buffer");

        let counts: [u32; 8] = {
            let view = counter_slice.get_mapped_range();
            let data: &[u32] = bytemuck::cast_slice(&view);
            [data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7]]
        };
        self.read_counter_buffer.unmap();

        let tri_count = counts[0];
        let active_blocks = counts[3];
        let productive_blocks = counts[4];
        let i_count = tri_count * 3;

        println!("Monster Engine Runtime Stats:");
        println!("  - Active Blocks: {}", active_blocks);
        println!("  - Productive Blocks: {}", productive_blocks);
        println!("  - Triangles: {}", tri_count);

        if tri_count == 0 { return (vec![], vec![]); }

        let v_slice = self.read_vertex_buffer.slice(0..(tri_count as u64 * 3 * 11 * 4));
        let i_slice = self.read_index_buffer.slice(0..(i_count as u64 * 4));

        let (v_tx, v_rx) = std::sync::mpsc::channel();
        let (i_tx, i_rx) = std::sync::mpsc::channel();
        
        v_slice.map_async(wgpu::MapMode::Read, move |v| v_tx.send(v).unwrap());
        i_slice.map_async(wgpu::MapMode::Read, move |v| i_tx.send(v).unwrap());
        self.device.poll(wgpu::Maintain::Wait);
        
        v_rx.recv().unwrap().expect("Failed to map vertex buffer");
        i_rx.recv().unwrap().expect("Failed to map index buffer");

        let vertices: Vec<f32> = bytemuck::cast_slice(&v_slice.get_mapped_range()).to_vec();
        let indices: Vec<u32> = bytemuck::cast_slice(&i_slice.get_mapped_range()).to_vec();

        self.read_vertex_buffer.unmap();
        self.read_index_buffer.unmap();

        (vertices, indices)
    }
}
