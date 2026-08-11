use super::primitive::*;

#[repr(C)]
#[derive(Copy, Clone, Debug, bytemuck::Pod, bytemuck::Zeroable)]
pub struct CameraUniform {
    pub view_proj: [[f32; 4]; 4],
    pub view_inv: [[f32; 4]; 4],
    pub proj_inv: [[f32; 4]; 4],
    pub camera_pos: [f32; 4],
    pub screen_size: [f32; 4],
}

pub struct SdfGpuContext {
    pub device: wgpu::Device,
    pub queue: wgpu::Queue,
    pub render_bind_group: wgpu::BindGroup,
    pub primitives_buffer: wgpu::Buffer,
    pub config_buffer: wgpu::Buffer,
    pub camera_buffer: wgpu::Buffer,
    pub render_pipeline: wgpu::RenderPipeline,
}

pub struct SdfEngine {
    pub ctx: SdfGpuContext,
}

impl SdfEngine {
    pub async fn new(device: wgpu::Device, queue: wgpu::Queue, format: wgpu::TextureFormat) -> anyhow::Result<Self> {
        let common_src = include_str!("../shaders/common.wgsl");
        let render_src = include_str!("../shaders/render.wgsl");

        let shader_render = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("Render Shader"),
            source: wgpu::ShaderSource::Wgsl(format!("{}\n{}", common_src, render_src).into()),
        });

        let render_bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("SDF Render Bind Group Layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry { binding: 0, visibility: wgpu::ShaderStages::VERTEX_FRAGMENT, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 1, visibility: wgpu::ShaderStages::VERTEX_FRAGMENT, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Storage { read_only: true }, has_dynamic_offset: false, min_binding_size: None }, count: None },
                wgpu::BindGroupLayoutEntry { binding: 14, visibility: wgpu::ShaderStages::VERTEX_FRAGMENT, ty: wgpu::BindingType::Buffer { ty: wgpu::BufferBindingType::Uniform, has_dynamic_offset: false, min_binding_size: None }, count: None },
            ],
        });

        let render_pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("SDF Render Pipeline Layout"),
            bind_group_layouts: &[&render_bind_group_layout],
            push_constant_ranges: &[],
        });

        let render_pipeline = device.create_render_pipeline(&wgpu::RenderPipelineDescriptor {
            label: Some("Render Pipeline"),
            layout: Some(&render_pipeline_layout),
            vertex: wgpu::VertexState { module: &shader_render, entry_point: "vs_main", buffers: &[] },
            fragment: Some(wgpu::FragmentState {
                module: &shader_render,
                entry_point: "fs_main",
                targets: &[Some(wgpu::ColorTargetState { format, blend: Some(wgpu::BlendState::REPLACE), write_mask: wgpu::ColorWrites::ALL })],
            }),
            primitive: wgpu::PrimitiveState::default(),
            depth_stencil: None,
            multisample: wgpu::MultisampleState::default(),
            multiview: None,
        });

        let config_buffer = device.create_buffer(&wgpu::BufferDescriptor { 
            label: Some("Config Buffer"), 
            size: std::mem::size_of::<GpuConfig>() as u64, 
            usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, 
            mapped_at_creation: false 
        });
        let primitives_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: Some("Prims Buffer"), size: 1024 * 1024, usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        let camera_buffer = device.create_buffer(&wgpu::BufferDescriptor { label: Some("Camera Buffer"), size: std::mem::size_of::<CameraUniform>() as u64, usage: wgpu::BufferUsages::UNIFORM | wgpu::BufferUsages::COPY_DST, mapped_at_creation: false });
        
        let render_bind_group = device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("SDF Render Bind Group"),
            layout: &render_bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry { binding: 0, resource: config_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 1, resource: primitives_buffer.as_entire_binding() },
                wgpu::BindGroupEntry { binding: 14, resource: camera_buffer.as_entire_binding() },
            ],
        });

        Ok(Self {
            ctx: SdfGpuContext {
                device,
                queue,
                render_bind_group,
                primitives_buffer,
                config_buffer,
                camera_buffer,
                render_pipeline,
            }
        })
    }

    pub fn update_camera(&self, camera: &super::super::Camera, width: u32, height: u32) {
        let view = glam::Mat4::look_at_rh(camera.eye, camera.target, camera.up);
        let proj = glam::Mat4::perspective_rh(camera.fovy.to_radians(), camera.aspect, camera.znear, camera.zfar);
        let view_proj = proj * view;

        let uniform = CameraUniform {
            view_proj: view_proj.to_cols_array_2d(),
            view_inv: view.inverse().to_cols_array_2d(),
            proj_inv: proj.inverse().to_cols_array_2d(),
            camera_pos: [camera.eye.x, camera.eye.y, camera.eye.z, 1.0],
            screen_size: [width as f32, height as f32, 0.0, 0.0],
        };
        self.ctx.queue.write_buffer(&self.ctx.camera_buffer, 0, bytemuck::cast_slice(&[uniform]));
    }

    pub fn update_scene_with_config(&self, primitives: &[SdfPrimitive], selected_idx: Option<usize>, show_grid: bool, show_axes: bool, show_selection_highlight: bool, mut config: GpuConfig) {
        let gpu_prims: Vec<GpuPrimitive> = primitives.iter().enumerate()
            .map(|(i, p)| p.to_gpu(selected_idx == Some(i)))
            .collect();
        self.ctx.queue.write_buffer(&self.ctx.primitives_buffer, 0, bytemuck::cast_slice(&gpu_prims));

        if show_grid { config.symmetry |= 256; }
        if show_axes { config.symmetry |= 512; }
        if show_selection_highlight { config.symmetry |= 1024; }

        self.ctx.queue.write_buffer(&self.ctx.config_buffer, 0, bytemuck::cast_slice(&[config]));
    }

    pub fn update_scene(&self, primitives: &[SdfPrimitive], selected_idx: Option<usize>, show_grid: bool, show_axes: bool, show_selection_highlight: bool, symmetry_mask_in: u32) {
        let mut config = GpuConfig {
            res: 128, // Default or previous
            domain_size: 10.0,
            num_primitives: primitives.len() as u32,
            symmetry: symmetry_mask_in,
            bg_color: [0.03, 0.03, 0.05],
            ao_strength: 0.5,
            shadow_softness: 16.0,
            _pad1: [0; 3],
            floor_color: [0.1, 0.1, 0.1],
            env_intensity: 0.5,
            selected_idx: selected_idx.map(|i| i as i32).unwrap_or(-1),
            _pad2: [0; 3],
        };
        self.update_scene_with_config(primitives, selected_idx, show_grid, show_axes, show_selection_highlight, config);
    }

    #[allow(dead_code)]
    pub fn render(&self, view: &wgpu::TextureView, encoder: &mut wgpu::CommandEncoder) {
        let mut rpass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
            label: Some("SDF Render Pass"),
            color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                view,
                resolve_target: None,
                ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color::BLACK), store: wgpu::StoreOp::Store },
            })],
            depth_stencil_attachment: None,
            occlusion_query_set: None,
            timestamp_writes: None,
        });
        rpass.set_pipeline(&self.ctx.render_pipeline);
        rpass.set_bind_group(0, &self.ctx.render_bind_group, &[]);
        rpass.draw(0..3, 0..1);
    }
}
