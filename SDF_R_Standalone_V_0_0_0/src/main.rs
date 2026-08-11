use egui;
use glam::{Vec3, Quat};



use winit::event::{Event, WindowEvent, ElementState, MouseButton};
use winit::event_loop::EventLoop;
use winit::window::{Window, WindowBuilder};

mod engine;
use engine::SdfEngine;
use engine::primitive::{SdfPrimitive, SdfPrimitiveSerial};

struct Camera {
    eye: Vec3,
    target: Vec3,
    up: Vec3,
    aspect: f32,
    fovy: f32,
    znear: f32,
    zfar: f32,
}

struct CameraController {
    distance: f32,
    yaw: f32,
    pitch: f32,
    is_mouse_pressed: bool,
    is_shift_pressed: bool,
    is_ctrl_pressed: bool,
    mouse_last_pos: Option<winit::dpi::PhysicalPosition<f64>>,
}

impl CameraController {
    fn new(distance: f32) -> Self {
        Self {
            distance,
            yaw: 45.0f32,
            pitch: -20.0f32,
            is_mouse_pressed: false,
            is_shift_pressed: false,
            is_ctrl_pressed: false,
            mouse_last_pos: None,
        }
    }

    fn process_events(&mut self, event: &WindowEvent, camera: &mut Camera) -> bool {
        match event {
            WindowEvent::MouseInput { state, button, .. } => {
                if *button == MouseButton::Right {
                    self.is_mouse_pressed = *state == ElementState::Pressed;
                    if !self.is_mouse_pressed { self.mouse_last_pos = None; }
                    return true;
                }
            }
            WindowEvent::CursorMoved { position, .. } => {
                if self.is_mouse_pressed {
                    if let Some(last_pos) = self.mouse_last_pos {
                        let dx = (position.x - last_pos.x) as f32;
                        let dy = (position.y - last_pos.y) as f32;
                        
                        if self.is_shift_pressed {
                            // PAN
                            let yaw_rad = self.yaw.to_radians();
                            let pitch_rad = self.pitch.to_radians();
                            let dir_to_eye = Vec3::new(
                                yaw_rad.cos() * pitch_rad.cos(),
                                pitch_rad.sin(),
                                yaw_rad.sin() * pitch_rad.cos()
                            ).normalize();
                            
                            let right = Vec3::Y.cross(dir_to_eye).normalize();
                            let up = dir_to_eye.cross(right).normalize();
                            
                            let sensitivity = self.distance * 0.001;
                            camera.target += right * (-dx * sensitivity) + up * (dy * sensitivity);
                        } else {
                            // ORBIT
                            self.yaw += dx * 0.2;
                            self.pitch += dy * 0.2;
                            self.pitch = self.pitch.clamp(-89.0, 89.0);
                        }
                    }
                }
                self.mouse_last_pos = Some(*position);
                return true;
            }
            WindowEvent::KeyboardInput { event: kb_event, .. } => {
                if let winit::keyboard::PhysicalKey::Code(code) = kb_event.physical_key {
                    let is_pressed = kb_event.state == ElementState::Pressed;
                    match code {
                        winit::keyboard::KeyCode::ShiftLeft | winit::keyboard::KeyCode::ShiftRight => { self.is_shift_pressed = is_pressed; }
                        winit::keyboard::KeyCode::ControlLeft | winit::keyboard::KeyCode::ControlRight => { self.is_ctrl_pressed = is_pressed; }
                        _ => {}
                    }
                }
            }
            WindowEvent::MouseWheel { delta, .. } => {
                let scroll = match delta {
                    winit::event::MouseScrollDelta::LineDelta(_, y) => *y,
                    winit::event::MouseScrollDelta::PixelDelta(pos) => pos.y as f32 * 0.05,
                };
                self.distance -= scroll * 0.5;
                self.distance = self.distance.clamp(0.1, 100.0);
                return true;
            }
            _ => {}
        }
        false
    }

    fn update_camera(&self, camera: &mut Camera) {
        let yaw_rad = self.yaw.to_radians();
        let pitch_rad = self.pitch.to_radians();
        let x = self.distance * yaw_rad.cos() * pitch_rad.cos();
        let y = self.distance * pitch_rad.sin();
        let z = self.distance * yaw_rad.sin() * pitch_rad.cos();
        camera.eye = Vec3::new(x, y, z) + camera.target;
    }
}

#[derive(PartialEq, Clone, Copy)]
enum TransformMode {
    Move,
    Rotate,
    Scale,
}

struct App {
    window: Window,
    surface: wgpu::Surface<'static>,
    engine: engine::SdfEngine,
    config: wgpu::SurfaceConfiguration,
    
    egui_ctx: egui::Context,
    egui_state: egui_winit::State,
    egui_renderer: egui_wgpu::Renderer,
    
    camera: Camera,
    camera_controller: CameraController,
    
    primitives: Vec<SdfPrimitive>,
    selected_idx: Option<usize>,
    transform_mode: TransformMode,
    next_id: u32,
    collapsed_groups: std::collections::HashSet<u32>,
    
    // Dragging State
    is_dragging: bool,
    drag_plane_normal: Vec3,
    drag_start_pos: Vec3,
    drag_object_start_center: Vec3,
    drag_object_start_rotation: Quat,
    drag_object_start_size: Vec3,
    
    // Axis constraint
    axis_constraint: Option<Vec3>,
    is_shift_pressed: bool,
    is_ctrl_pressed: bool,
    is_alt_pressed: bool,
    
    // Viewport settings
    show_grid: bool,
    show_axes: bool,
    show_selection_highlight: bool,
    show_left_panel: bool,
    show_right_panel: bool,
    show_help: bool,
    
    // Undo/Redo
    undo_stack: Vec<Vec<SdfPrimitive>>,
    redo_stack: Vec<Vec<SdfPrimitive>>,
    
    // Global Settings
    symmetry_x: bool,
    symmetry_y: bool,
    symmetry_z: bool,
    
    // Rendering Settings
    bg_color: [f32; 3],
    ao_strength: f32,
    shadow_softness: f32,
    floor_color: [f32; 3],
    env_intensity: f32,
    domain_size: f32,
    render_res: u32,
    
    fps: f32,
    last_time: std::time::Instant,
}

impl App {
    async fn new(window: Window) -> anyhow::Result<Self> {
        let instance = wgpu::Instance::default();
        let surface = instance.create_surface(unsafe { std::mem::transmute::<&Window, &'static Window>(&window) }).unwrap();
        let adapter = instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            compatible_surface: Some(&surface),
            force_fallback_adapter: false,
        }).await.unwrap();

        let (device, queue) = adapter.request_device(
            &wgpu::DeviceDescriptor {
                label: None,
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::default().using_resolution(adapter.limits()),
            },
            None,
        ).await?;
        let size = window.inner_size();
        let caps = surface.get_capabilities(&adapter);
        let format = caps.formats[0];
        let config = wgpu::SurfaceConfiguration {
            usage: wgpu::TextureUsages::RENDER_ATTACHMENT,
            format,
            width: size.width,
            height: size.height,
            present_mode: wgpu::PresentMode::Fifo,
            alpha_mode: caps.alpha_modes[0],
            view_formats: vec![],
            desired_maximum_frame_latency: 2,
        };
        surface.configure(&device, &config);

        let engine = engine::SdfEngine::new(device, queue, format).await?;
        
        let egui_ctx = egui::Context::default();
        let egui_state = egui_winit::State::new(
            egui_ctx.clone(),
            egui::viewport::ViewportId::ROOT,
            &window,
            Some(window.scale_factor() as f32),
            None,
        );
        let egui_renderer = egui_wgpu::Renderer::new(&engine.ctx.device, format, None, 1);

        let camera = Camera {
            eye: Vec3::new(5.0, 5.0, 5.0),
            target: Vec3::ZERO,
            up: Vec3::Y,
            aspect: size.width as f32 / size.height as f32,
            fovy: 45.0,
            znear: 0.1,
            zfar: 100.0,
        };

        let mut primitives = vec![
            SdfPrimitive::new_sphere(Vec3::ZERO, 1.0),
        ];
        primitives[0].id = 0;

        Ok(Self {
            window,
            surface,
            engine,
            config,
            egui_ctx,
            egui_state,
            egui_renderer,
            camera,
            camera_controller: CameraController::new(8.0),
            primitives,
            selected_idx: Some(0),
            transform_mode: TransformMode::Move,
            next_id: 1,
            collapsed_groups: std::collections::HashSet::new(),
            is_dragging: false,
            drag_plane_normal: Vec3::ZERO,
            drag_start_pos: Vec3::ZERO,
            drag_object_start_center: Vec3::ZERO,
            drag_object_start_rotation: Quat::IDENTITY,
            drag_object_start_size: Vec3::ONE,
            axis_constraint: None,
            is_shift_pressed: false,
            is_ctrl_pressed: false,
            is_alt_pressed: false,
            show_grid: true,
            show_axes: true,
            show_selection_highlight: true,
            show_left_panel: true,
            show_right_panel: true,
            show_help: false,
            undo_stack: Vec::new(),
            redo_stack: Vec::new(),
            symmetry_x: false,
            symmetry_y: false,
            symmetry_z: false,
            bg_color: [0.03, 0.03, 0.05],
            ao_strength: 0.5,
            shadow_softness: 16.0,
            floor_color: [0.1, 0.1, 0.12],
            env_intensity: 0.5,
            domain_size: 10.0,
            render_res: 128,
            fps: 0.0,
            last_time: std::time::Instant::now(),
        })
    }

    fn get_mouse_ray(&self, mouse_pos: winit::dpi::PhysicalPosition<f64>) -> (Vec3, Vec3) {
        let x = (mouse_pos.x as f32 / self.config.width as f32) * 2.0 - 1.0;
        let y = (mouse_pos.y as f32 / self.config.height as f32) * 2.0 - 1.0; // Flipped to match viewport
        
        let view = glam::Mat4::look_at_rh(self.camera.eye, self.camera.target, self.camera.up);
        let proj = glam::Mat4::perspective_rh(self.camera.fovy.to_radians(), self.camera.aspect, self.camera.znear, self.camera.zfar);
        let inv_vp = (proj * view).inverse();
        
        let near = inv_vp.project_point3(Vec3::new(x, y, 0.0));
        let far = inv_vp.project_point3(Vec3::new(x, y, 1.0));
        let dir = (far - near).normalize();
        (near, dir)
    }

    fn handle_input(&mut self, event: &WindowEvent) {
        match event {
            WindowEvent::KeyboardInput { event: kb_event, .. } => {
                if let winit::keyboard::PhysicalKey::Code(code) = kb_event.physical_key {
                    let is_pressed = kb_event.state == ElementState::Pressed;
                    match code {
                        winit::keyboard::KeyCode::ShiftLeft | winit::keyboard::KeyCode::ShiftRight => { self.is_shift_pressed = is_pressed; }
                        winit::keyboard::KeyCode::ControlLeft | winit::keyboard::KeyCode::ControlRight => { self.is_ctrl_pressed = is_pressed; }
                        winit::keyboard::KeyCode::AltLeft | winit::keyboard::KeyCode::AltRight => { self.is_alt_pressed = is_pressed; }
                        winit::keyboard::KeyCode::KeyX => { self.axis_constraint = if is_pressed { Some(Vec3::X) } else { None }; }
                        winit::keyboard::KeyCode::KeyY => { self.axis_constraint = if is_pressed { Some(Vec3::Y) } else { None }; }
                        winit::keyboard::KeyCode::KeyZ => { self.axis_constraint = if is_pressed { Some(Vec3::Z) } else { None }; }
                        _ => {
                            if is_pressed {
                                match code {
                                    winit::keyboard::KeyCode::KeyG => self.transform_mode = TransformMode::Move,
                                    winit::keyboard::KeyCode::KeyR => self.transform_mode = TransformMode::Rotate,
                                    winit::keyboard::KeyCode::KeyS => self.transform_mode = TransformMode::Scale,
                                    winit::keyboard::KeyCode::KeyT => self.show_left_panel = !self.show_left_panel,
                                    winit::keyboard::KeyCode::KeyN => self.show_right_panel = !self.show_right_panel,
                                    winit::keyboard::KeyCode::KeyZ if self.is_ctrl_pressed => {
                                        if self.is_shift_pressed { self.redo(); }
                                        else { self.undo(); }
                                    }
                                    winit::keyboard::KeyCode::KeyY if self.is_ctrl_pressed => {
                                        self.redo();
                                    }
                                    winit::keyboard::KeyCode::F1 => self.show_help = !self.show_help,
                                    winit::keyboard::KeyCode::Escape => self.selected_idx = None,
                                    winit::keyboard::KeyCode::Delete | winit::keyboard::KeyCode::KeyX => {
                                        if let Some(idx) = self.selected_idx {
                                            self.primitives.remove(idx);
                                            self.selected_idx = None;
                                        }
                                    }
                                    winit::keyboard::KeyCode::KeyH => {
                                        if self.is_alt_pressed {
                                            for p in &mut self.primitives { p.visible = true; }
                                        } else if let Some(idx) = self.selected_idx {
                                            self.primitives[idx].visible = !self.primitives[idx].visible;
                                        }
                                    }
                                    winit::keyboard::KeyCode::KeyD if self.is_shift_pressed => {
                                        if let Some(idx) = self.selected_idx {
                                            self.duplicate_object(idx);
                                        }
                                    }
                                    _ => {}
                                }
                            }
                        }
                    }
                }
            }
            WindowEvent::MouseInput { state, button, .. } => {
                if !self.egui_state.on_window_event(&self.window, event).consumed {
                    if *button == MouseButton::Left {
                        if *state == ElementState::Pressed {
                            self.push_undo();
                            self.is_dragging = true;
                            if let (Some(idx), Some(pos)) = (self.selected_idx, self.camera_controller.mouse_last_pos) {
                                let (ray_origin, ray_dir) = self.get_mouse_ray(pos);
                                let prim = &self.primitives[idx];
                                self.drag_plane_normal = (self.camera.eye - self.camera.target).normalize();
                                let denom = self.drag_plane_normal.dot(ray_dir);
                                if denom.abs() > 1e-6 {
                                    let t = (prim.center - ray_origin).dot(self.drag_plane_normal) / denom;
                                    self.drag_start_pos = ray_origin + ray_dir * t;
                                    self.drag_object_start_center = prim.center;
                                    self.drag_object_start_rotation = prim.rotation;
                                    self.drag_object_start_size = prim.size;
                                    self.is_dragging = true;
                                }
                            }
                        } else {
                            self.is_dragging = false;
                        }
                    }
                }
            }
            WindowEvent::CursorMoved { position, .. } => {
                if self.is_dragging {
                    if let Some(idx) = self.selected_idx {
                        match self.transform_mode {
                            TransformMode::Move => {
                                let (ray_origin, ray_dir) = self.get_mouse_ray(*position);
                                let denom = self.drag_plane_normal.dot(ray_dir);
                                if denom.abs() > 1e-6 {
                                    let t = (self.drag_object_start_center - ray_origin).dot(self.drag_plane_normal) / denom;
                                    let current_pos = ray_origin + ray_dir * t;
                                    let mut delta = current_pos - self.drag_start_pos;
                                    
                                    if let Some(axis) = self.axis_constraint {
                                        if self.is_shift_pressed {
                                            // Plane constraint: project delta onto plane perpendicular to axis
                                            delta = delta - axis * delta.dot(axis);
                                        } else {
                                            // Axis constraint
                                            delta = axis * delta.dot(axis);
                                        }
                                    }
                                    
                                    let new_pos = self.drag_object_start_center + delta;
                                    let old_pos = self.primitives[idx].center;
                                    let old_rot = self.primitives[idx].rotation;
                                    self.primitives[idx].center = new_pos;
                                    self.apply_parent_transform(idx, old_pos, new_pos, old_rot, old_rot);
                                }
                            }
                            TransformMode::Rotate => {
                                if let Some(last_pos) = self.camera_controller.mouse_last_pos {
                                    let dx = position.x - last_pos.x;
                                    let dy = position.y - last_pos.y;
                                    
                                    if let Some(axis) = self.axis_constraint {
                                        // Constrained rotation: use mouse movement to rotate around global axis
                                        let amount = (dx + dy) as f32 * 0.01;
                                        let rot = Quat::from_axis_angle(axis, amount);
                                        self.primitives[idx].rotation = rot * self.primitives[idx].rotation;
                                    } else {
                                        // Free rotation relative to view
                                        let view_dir = (self.camera.target - self.camera.eye).normalize();
                                        let right = view_dir.cross(self.camera.up).normalize();
                                        let up = right.cross(view_dir).normalize();
                                        let rot_y = Quat::from_axis_angle(up, dx as f32 * 0.01);
                                        let rot_x = Quat::from_axis_angle(right, -dy as f32 * 0.01);
                                        let new_rot = rot_y * rot_x * self.primitives[idx].rotation;
                                        let old_pos = self.primitives[idx].center;
                                        let old_rot = self.primitives[idx].rotation;
                                        self.primitives[idx].rotation = new_rot;
                                        self.apply_parent_transform(idx, old_pos, old_pos, old_rot, new_rot);
                                    }
                                }
                            }
                            TransformMode::Scale => {
                                if let Some(last_pos) = self.camera_controller.mouse_last_pos {
                                    let dy = (position.y - last_pos.y) as f32;
                                    let scale_factor = 1.0 - dy * 0.01;
                                    
                                    if let Some(axis) = self.axis_constraint {
                                        if self.is_shift_pressed {
                                            // Scale everything EXCEPT this axis
                                            let mut s = Vec3::ONE * scale_factor;
                                            if axis == Vec3::X { s.x = 1.0; }
                                            if axis == Vec3::Y { s.y = 1.0; }
                                            if axis == Vec3::Z { s.z = 1.0; }
                                            self.primitives[idx].size *= s;
                                        } else {
                                            // Scale ONLY this axis
                                            let mut s = Vec3::ONE;
                                            if axis == Vec3::X { s.x = scale_factor; }
                                            if axis == Vec3::Y { s.y = scale_factor; }
                                            if axis == Vec3::Z { s.z = scale_factor; }
                                            self.primitives[idx].size *= s;
                                        }
                                    } else {
                                        // Uniform scale
                                        self.primitives[idx].size *= scale_factor;
                                    }
                                }
                            }
                        }
                    }
                }
            }
            _ => {}
        }
    }

    fn resize(&mut self, size: winit::dpi::PhysicalSize<u32>) {
        if size.width > 0 && size.height > 0 {
            self.config.width = size.width;
            self.config.height = size.height;
            self.camera.aspect = size.width as f32 / size.height as f32;
            self.surface.configure(&self.engine.ctx.device, &self.config);
        }
    }

    fn update(&mut self) {
        let now = std::time::Instant::now();
        let dt = now.duration_since(self.last_time).as_secs_f32();
        self.fps = 0.9 * self.fps + 0.1 * (1.0 / dt.max(0.001));
        self.last_time = now;

        self.camera_controller.update_camera(&mut self.camera);
    }

    fn render(&mut self) -> anyhow::Result<()> {
        let output = self.surface.get_current_texture()?;
        let view = output.texture.create_view(&wgpu::TextureViewDescriptor::default());
        self.engine.update_camera(&self.camera, self.config.width, self.config.height);
        
        let symmetry_mask = (if self.symmetry_x { 1 } else { 0 }) |
                            (if self.symmetry_y { 2 } else { 0 }) |
                            (if self.symmetry_z { 4 } else { 0 });
        
        let gpu_config = engine::primitive::GpuConfig {
            res: self.render_res,
            domain_size: self.domain_size,
            num_primitives: self.primitives.len() as u32,
            symmetry: symmetry_mask,
            bg_color: self.bg_color,
            ao_strength: self.ao_strength,
            shadow_softness: self.shadow_softness,
            _pad1: [0; 3],
            floor_color: self.floor_color,
            env_intensity: self.env_intensity,
            selected_idx: self.selected_idx.map(|i| i as i32).unwrap_or(-1),
            _pad2: [0; 3],
        };

        self.engine.update_scene_with_config(&self.primitives, self.selected_idx, self.show_grid, self.show_axes, self.show_selection_highlight, gpu_config);

        let mut encoder = self.engine.ctx.device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: Some("Render Encoder") });

        {
            let mut rpass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("SDF Render Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations { load: wgpu::LoadOp::Clear(wgpu::Color::BLACK), store: wgpu::StoreOp::Store },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            rpass.set_pipeline(&self.engine.ctx.render_pipeline);
            rpass.set_bind_group(0, &self.engine.ctx.render_bind_group, &[]);
            rpass.draw(0..3, 0..1);
        }

        let ui_input = self.egui_state.take_egui_input(&self.window);
        self.egui_ctx.begin_frame(ui_input);
        
        let egui_ctx = self.egui_ctx.clone();

        egui::TopBottomPanel::top("top_panel").show(&egui_ctx, |ui| {
            ui.horizontal(|ui| {
                ui.heading("🚀 SDF.R Standalone");
                ui.separator();
                
                if ui.button(if self.show_help { "📖 Close Help" } else { "❓ Help (F1)" }).clicked() {
                    self.show_help = !self.show_help;
                }
                
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    ui.checkbox(&mut self.show_left_panel, "Outliner (T)");
                    ui.checkbox(&mut self.show_right_panel, "Properties (N)");
                });
            });
        });

        if self.show_help {
            egui::Window::new("⌨️ Operation Guide")
                .collapsible(false)
                .resizable(false)
                .anchor(egui::Align2::CENTER_CENTER, [0.0, 0.0])
                .show(&egui_ctx, |ui| {
                    ui.set_max_width(400.0);
                    
                    ui.collapsing("🖱 Camera Controls", |ui| {
                        ui.label("• Rotate: Middle Mouse Button");
                        ui.label("• Pan: Shift + Middle Mouse Button");
                        ui.label("• Zoom: Mouse Wheel");
                    });
                    
                    ui.collapsing("📐 Transformation", |ui| {
                        ui.label("• Move: G");
                        ui.label("• Rotate: R");
                        ui.label("• Scale: S");
                        ui.label("• Axis Constraints: X / Y / Z (during transform)");
                        ui.label("• Cancel: Escape / Right Click");
                        ui.label("• Confirm: Left Click / Enter");
                    });
                    
                    ui.collapsing("📝 Editing", |ui| {
                        ui.label("• Delete: Delete / X");
                        ui.label("• Duplicate: Shift + D");
                        ui.label("• Undo: Ctrl + Z");
                        ui.label("• Redo: Ctrl + Y");
                        ui.label("• Toggle Outliner: T");
                        ui.label("• Toggle Properties: N");
                    });

                    ui.separator();
                    if ui.button("Got it!").clicked() {
                        self.show_help = false;
                    }
                });
        }

        if self.show_left_panel {
            egui::SidePanel::left("outliner").resizable(true).default_width(200.0).show(&egui_ctx, |ui: &mut egui::Ui| {
                ui.heading("Scene Outliner");
                ui.separator();

                ui.collapsing("Global Symmetry", |ui| {
                    ui.horizontal(|ui| {
                        ui.checkbox(&mut self.symmetry_x, "X");
                        ui.checkbox(&mut self.symmetry_y, "Y");
                        ui.checkbox(&mut self.symmetry_z, "Z");
                    });
                });

                ui.collapsing("Scene Settings", |ui| {
                    ui.checkbox(&mut self.show_grid, "Show Floor Grid");
                    ui.checkbox(&mut self.show_axes, "Show Axes");
                    ui.checkbox(&mut self.show_selection_highlight, "Selection Glow");
                    
                    ui.separator();
                    ui.label("Background Color");
                    ui.color_edit_button_rgb(&mut self.bg_color);
                    
                    ui.label("Floor Color");
                    ui.color_edit_button_rgb(&mut self.floor_color);
                    
                    ui.label("AO Strength");
                    ui.add(egui::Slider::new(&mut self.ao_strength, 0.0..=2.0));
                    
                    ui.label("Shadow Softness");
                    ui.add(egui::Slider::new(&mut self.shadow_softness, 1.0..=64.0));
                    
                    ui.label("Environment Intensity");
                    ui.add(egui::Slider::new(&mut self.env_intensity, 0.0..=2.0));

                    ui.separator();
                    ui.label("World Scale");
                    ui.add(egui::Slider::new(&mut self.domain_size, 1.0..=50.0));
                    
                    ui.label("Render Resolution");
                    ui.add(egui::Slider::new(&mut self.render_res, 32..=256).text("voxels"));
                });
                
                ui.separator();

                ui.horizontal_wrapped(|ui: &mut egui::Ui| {
                    if ui.button("+ Add Sphere").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_sphere(Vec3::ZERO, 1.0)); }
                    if ui.button("+ Add Cube").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_cube(Vec3::ZERO, Vec3::ONE)); }
                    if ui.button("+ Add Torus").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_torus(Vec3::ZERO, 0.8, 0.2)); }
                    if ui.button("+ Add Cylinder").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_cylinder(Vec3::ZERO, 0.5, 1.0)); }
                    if ui.button("+ Add Capsule").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_capsule(Vec3::ZERO, 0.5, 1.0)); }
                    if ui.button("+ Add Rounded Box").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_rounded_box(Vec3::ZERO, Vec3::ONE, 0.2)); }
                    if ui.button("+ Add Hex Prism").clicked() { self.push_undo(); self.primitives.push(SdfPrimitive::new_hex_prism(Vec3::ZERO, 0.8, 0.5)); }
                    if ui.button("+ Add Group").clicked() { self.push_undo(); self.add_group(); }
                });

                ui.separator();

                ui.horizontal(|ui| {
                    if ui.button("📁 Save").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("SDF Scene", &["json"])
                            .set_file_name("scene.json")
                            .save_file() {
                            let serial_prims: Vec<SdfPrimitiveSerial> = self.primitives.iter()
                                .map(SdfPrimitiveSerial::from_primitive)
                                .collect();
                            if let Ok(json) = serde_json::to_string_pretty(&serial_prims) {
                                let _ = std::fs::write(path, json);
                            }
                        }
                    }
                    if ui.button("📂 Load").clicked() {
                        if let Some(path) = rfd::FileDialog::new()
                            .add_filter("SDF Scene", &["json"])
                            .pick_file() {
                            if let Ok(json) = std::fs::read_to_string(path) {
                                if let Ok(serial_prims) = serde_json::from_str::<Vec<SdfPrimitiveSerial>>(&json) {
                                    self.primitives = serial_prims.iter()
                                        .map(|p: &SdfPrimitiveSerial| p.to_primitive())
                                        .collect();
                                    self.selected_idx = None;
                                    self.next_id = self.primitives.iter().map(|p| p.id).max().unwrap_or(0) + 1;
                                }
                            }
                        }
                    }
                });
                ui.label(format!("FPS: {:.1}", self.fps));
            ui.separator();

            ui.horizontal(|ui: &mut egui::Ui| {
                ui.checkbox(&mut self.show_grid, "Grid");
                ui.checkbox(&mut self.show_axes, "Axes");
                ui.checkbox(&mut self.show_selection_highlight, "Highlight");
            });
            ui.separator();

            ui.horizontal(|ui: &mut egui::Ui| {
                ui.selectable_value(&mut self.transform_mode, TransformMode::Move, "Move [G]");
                ui.selectable_value(&mut self.transform_mode, TransformMode::Rotate, "Rotate [R]");
                ui.selectable_value(&mut self.transform_mode, TransformMode::Scale, "Scale [S]");
            });
            ui.separator();
            
            egui::ScrollArea::vertical().show(ui, |ui: &mut egui::Ui| {
                let mut swap_req = None;
                let mut reparent_req = None;
                let num_prims = self.primitives.len();
                
                let group_candidates: Vec<(u32, String)> = self.primitives.iter()
                    .filter(|p| p.is_group)
                    .map(|p| (p.id, format!("📁 Group (ID:{})", p.id)))
                    .collect();

                fn render_item(
                    ui: &mut egui::Ui,
                    idx: usize,
                    depth: usize,
                    is_last: bool,
                    parent_hidden: bool,
                    primitives: &mut [SdfPrimitive],
                    selected_idx: &mut Option<usize>,
                    collapsed_groups: &mut std::collections::HashSet<u32>,
                    swap_req: &mut Option<(usize, usize)>,
                    reparent_req: &mut Option<(usize, Option<u32>)>,
                    num_prims: usize,
                    group_candidates: &[(u32, String)],
                ) {
                    let id = primitives[idx].id;
                    let is_group = primitives[idx].is_group;
                    let is_selected = *selected_idx == Some(idx);
                    let is_collapsed = collapsed_groups.contains(&id);
                    let parent_id = primitives[idx].parent_id;
                    
                    if parent_hidden {
                        primitives[idx].visible = false;
                    }

                    let response = ui.horizontal(|ui| {
                        for _ in 0..depth {
                            ui.label("  │");
                        }
                        if depth > 0 {
                            ui.label(if is_last { "  └─" } else { "  ├─" });
                        }

                        if is_group {
                            let icon = if is_collapsed { "▶" } else { "▼" };
                            if ui.selectable_label(false, icon).clicked() {
                                if is_collapsed { collapsed_groups.remove(&id); }
                                else { collapsed_groups.insert(id); }
                            }
                        } else {
                            ui.add_space(14.0);
                        }

                        let vis_icon = if primitives[idx].visible { "👁" } else { "❌" };
                        if ui.button(vis_icon).clicked() {
                            primitives[idx].visible = !primitives[idx].visible;
                        }
                        
                        let op_icon = match primitives[idx].operation {
                            1 => "➖ ",
                            2 => "✖ ",
                            _ => "➕ ",
                        };
                        
                        let name = if is_group {
                            format!("📁 Group (ID:{})", primitives[idx].id)
                        } else {
                            match primitives[idx].shape_type {
                                0 => format!("{}{} Sphere", idx, op_icon),
                                1 => format!("{}{} Cube", idx, op_icon),
                                2 => format!("{}{} Torus", idx, op_icon),
                                3 => format!("{}{} Cylinder", idx, op_icon),
                                4 => format!("{}{} RoundBox", idx, op_icon),
                                5 => format!("{}{} Capsule", idx, op_icon),
                                6 => format!("{}{} HexPrism", idx, op_icon),
                                _ => format!("{}{} Unknown", idx, op_icon),
                            }
                        };
                        
                        let mut text = egui::RichText::new(name);
                        if is_group { text = text.color(egui::Color32::from_rgb(255, 215, 0)); }
                        if is_selected { text = text.strong().background_color(egui::Color32::from_gray(60)); }

                        let label = ui.selectable_label(false, text);
                        if label.clicked() {
                            *selected_idx = Some(idx);
                        }

                        ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                            if idx > 0 {
                                if ui.small_button("↑").clicked() { *swap_req = Some((idx, idx - 1)); }
                            }
                            if idx < num_prims - 1 {
                                if ui.small_button("↓").clicked() { *swap_req = Some((idx, idx + 1)); }
                            }
                            if parent_id.is_some() {
                                if ui.button("📤").on_hover_text("Unparent (Move to top)").clicked() {
                                    *reparent_req = Some((idx, None));
                                }
                            }
                        });
                        label
                    }).inner;

                    response.context_menu(|ui| {
                        if ui.button("🗑 Delete").clicked() {
                            ui.close_menu();
                        }
                        
                        ui.separator();
                        
                        if parent_id.is_some() {
                            if ui.button("📤 Unparent").clicked() {
                                *reparent_req = Some((idx, None));
                                ui.close_menu();
                            }
                        }

                        ui.menu_button("📁 Move to Group", |ui| {
                            for (gid, gname) in group_candidates {
                                if *gid != id {
                                    if ui.button(gname).clicked() {
                                        *reparent_req = Some((idx, Some(*gid)));
                                        ui.close_menu();
                                    }
                                }
                            }
                        });
                    });
                    
                    if is_group && !is_collapsed {
                        let children_indices: Vec<usize> = primitives.iter().enumerate()
                            .filter(|(_, p)| p.parent_id == Some(id))
                            .map(|(i, _)| i)
                            .collect();
                        
                        let child_count = children_indices.len();
                        for (c_idx, &child_idx) in children_indices.iter().enumerate() {
                            render_item(
                                ui, 
                                child_idx, 
                                depth + 1, 
                                c_idx == child_count - 1,
                                !primitives[idx].visible,
                                primitives, 
                                selected_idx, 
                                collapsed_groups,
                                swap_req,
                                reparent_req,
                                num_prims,
                                group_candidates,
                            );
                        }
                    }
                }

                let top_level_indices: Vec<usize> = self.primitives.iter().enumerate()
                    .filter(|(_, p)| p.parent_id.is_none())
                    .map(|(i, _)| i)
                    .collect();

                let top_count = top_level_indices.len();
                for (i, &idx) in top_level_indices.iter().enumerate() {
                    render_item(
                        ui, 
                        idx, 
                        0, 
                        i == top_count - 1,
                        false,
                        &mut self.primitives, 
                        &mut self.selected_idx, 
                        &mut self.collapsed_groups,
                        &mut swap_req,
                        &mut reparent_req,
                        num_prims,
                        &group_candidates,
                    );
                }
                
                if let Some((src, dst)) = swap_req {
                    self.primitives.swap(src, dst);
                    if self.selected_idx == Some(src) { self.selected_idx = Some(dst); }
                    else if self.selected_idx == Some(dst) { self.selected_idx = Some(src); }
                }

                if let Some((idx, new_parent)) = reparent_req {
                    self.primitives[idx].parent_id = new_parent;
                }
            });
        });
    }

        if self.show_right_panel {
            if let Some(idx) = self.selected_idx {
            if idx < self.primitives.len() {
                let group_candidates: Vec<(u32, String)> = self.primitives.iter()
                    .filter(|p| p.is_group && p.id != self.primitives[idx].id)
                    .map(|p| (p.id, format!("Group (ID:{})", p.id)))
                    .collect();

                egui::SidePanel::right("properties").resizable(true).default_width(250.0).show(&egui_ctx, |ui: &mut egui::Ui| {
                    let prim = &mut self.primitives[idx];
                    ui.heading("Properties");
                    ui.separator();

                    ui.group(|ui: &mut egui::Ui| {
                        ui.checkbox(&mut prim.visible, "Object Visible");
                        
                        ui.horizontal(|ui| {
                            ui.label("Parent Group");
                            let mut current_parent = prim.parent_id;
                            egui::ComboBox::from_id_source("parent_select")
                                .selected_text(if let Some(pid) = current_parent { format!("Group ID: {}", pid) } else { "None".to_string() })
                                .show_ui(ui, |ui| {
                                    ui.selectable_value(&mut current_parent, None, "None");
                                    for (gid, gname) in &group_candidates {
                                        ui.selectable_value(&mut current_parent, Some(*gid), gname);
                                    }
                                });
                            prim.parent_id = current_parent;
                        });
                        
                        ui.label("Boolean Operation");
                        ui.horizontal(|ui: &mut egui::Ui| {
                            ui.selectable_value(&mut prim.operation, 0, "Union");
                            ui.selectable_value(&mut prim.operation, 1, "Subtract");
                            ui.selectable_value(&mut prim.operation, 2, "Intersect");
                        });
                    });

                    ui.collapsing("Transform", |ui: &mut egui::Ui| {
                        ui.label("Position");
                        ui.horizontal(|ui| {
                            ui.add(egui::DragValue::new(&mut prim.center.x).speed(0.1).prefix("X:"));
                            ui.add(egui::DragValue::new(&mut prim.center.y).speed(0.1).prefix("Y:"));
                            ui.add(egui::DragValue::new(&mut prim.center.z).speed(0.1).prefix("Z:"));
                        });

                        ui.label("Rotation (Euler)");
                        let (rx, ry, rz) = prim.rotation.to_euler(glam::EulerRot::XYZ);
                        let mut rx = rx.to_degrees() as f32;
                        let mut ry = ry.to_degrees() as f32;
                        let mut rz = rz.to_degrees() as f32;
                        
                        let mut changed = false;
                        ui.horizontal(|ui| {
                            if ui.add(egui::DragValue::new(&mut rx).speed(1.0).suffix("°").prefix("X:")).changed() { changed = true; }
                            if ui.add(egui::DragValue::new(&mut ry).speed(1.0).suffix("°").prefix("Y:")).changed() { changed = true; }
                            if ui.add(egui::DragValue::new(&mut rz).speed(1.0).suffix("°").prefix("Z:")).changed() { changed = true; }
                        });
                        
                        if changed {
                            prim.rotation = Quat::from_euler(glam::EulerRot::XYZ, rx.to_radians(), ry.to_radians(), rz.to_radians());
                        }

                        ui.label("Scale");
                        ui.horizontal(|ui| {
                            ui.add(egui::DragValue::new(&mut prim.size.x).speed(0.1).prefix("X:"));
                            ui.add(egui::DragValue::new(&mut prim.size.y).speed(0.1).prefix("Y:"));
                            ui.add(egui::DragValue::new(&mut prim.size.z).speed(0.1).prefix("Z:"));
                        });
                    });

                    ui.collapsing("Shape", |ui: &mut egui::Ui| {
                        match prim.shape_type {
                            0 => { ui.add(egui::Slider::new(&mut prim.radius, 0.0..=5.0).text("Radius")); }
                            2 => { 
                                ui.add(egui::Slider::new(&mut prim.extra_params[0], 0.1..=5.0).text("Major R"));
                                ui.add(egui::Slider::new(&mut prim.extra_params[1], 0.01..=2.0).text("Minor R"));
                            }
                            3 | 5 | 6 => { 
                                ui.add(egui::Slider::new(&mut prim.extra_params[0], 0.1..=5.0).text("Radius"));
                                ui.add(egui::Slider::new(&mut prim.extra_params[1], 0.1..=5.0).text("Height"));
                            }
                            4 => { ui.add(egui::Slider::new(&mut prim.extra_params[0], 0.0..=2.0).text("Roundness")); }
                            _ => {}
                        }
                        ui.add(egui::Slider::new(&mut prim.smoothness, 0.0..=2.0).text("Smoothness"));
                    });

                    ui.collapsing("Material", |ui: &mut egui::Ui| {
                        ui.color_edit_button_rgb(bytemuck::cast_mut(&mut prim.color));
                        ui.add(egui::Slider::new(&mut prim.metallic, 0.0..=1.0).text("Metallic"));
                        ui.add(egui::Slider::new(&mut prim.roughness, 0.0..=1.0).text("Roughness"));
                        ui.add(egui::Slider::new(&mut prim.emission, 0.0..=10.0).text("Emission"));
                        ui.add(egui::Slider::new(&mut prim.color_influence, 0.0..=1.0).text("Col Influence"));
                        ui.add(egui::Slider::new(&mut prim.shell_thickness, 0.0..=1.0).text("Shell (Hollow)"));
                    });

                    ui.collapsing("Layout (Mirror / Grid)", |ui: &mut egui::Ui| {
                        let mut mirror_enabled = (prim.layout_flags & engine::primitive::LAYOUT_FLAG_MIRROR) != 0;
                        if ui.checkbox(&mut mirror_enabled, "Mirror").changed() {
                            if mirror_enabled { prim.layout_flags |= engine::primitive::LAYOUT_FLAG_MIRROR; }
                            else { prim.layout_flags &= !engine::primitive::LAYOUT_FLAG_MIRROR; }
                        }
                        
                        if mirror_enabled {
                            ui.indent("mirror_indent", |ui| {
                                let mut packed = prim.layout_params[0][0] as u32;
                                let mut mask = (packed >> 8) & 0xF;
                                let mut mx = (mask & 1) != 0; let mut my = (mask & 2) != 0; let mut mz = (mask & 4) != 0;
                                
                                ui.horizontal(|ui| {
                                    ui.checkbox(&mut mx, "X");
                                    ui.checkbox(&mut my, "Y");
                                    ui.checkbox(&mut mz, "Z");
                                });
                                
                                mask = (if mx {1} else {0}) | (if my {2} else {0}) | (if mz {4} else {0});
                                packed = (packed & !0x0F00) | (mask << 8);
                                prim.layout_params[0][0] = packed as f32;
                                
                                ui.add(egui::Slider::new(&mut prim.layout_params[0][1], 0.0..=10.0).text("Offset"));
                            });
                        }
                        
                        ui.separator();

                        // 2. Grid
                        let mut grid_enabled = (prim.layout_flags & engine::primitive::LAYOUT_FLAG_GRID) != 0;
                        if ui.checkbox(&mut grid_enabled, "Grid Repeat").changed() {
                            if grid_enabled { prim.layout_flags |= engine::primitive::LAYOUT_FLAG_GRID; }
                            else { prim.layout_flags &= !engine::primitive::LAYOUT_FLAG_GRID; }
                        }
                        
                        if grid_enabled {
                            ui.indent("grid_indent", |ui| {
                                let g_p = prim.layout_params[1][2];
                                let cz = (g_p / 10000.0).floor();
                                let cy = ((g_p - cz * 10000.0) / 100.0).floor();
                                let cx = g_p - cz * 10000.0 - cy * 100.0;
                                
                                let mut counts = [cx as i32, cy as i32, cz as i32];
                                ui.horizontal(|ui| {
                                    ui.label("Counts");
                                    ui.add(egui::DragValue::new(&mut counts[0]).clamp_range(1..=50));
                                    ui.add(egui::DragValue::new(&mut counts[1]).clamp_range(1..=50));
                                    ui.add(egui::DragValue::new(&mut counts[2]).clamp_range(1..=50));
                                });
                                prim.layout_params[1][2] = (counts[2] * 10000 + counts[1] * 100 + counts[0]) as f32;
                                
                                ui.horizontal(|ui| {
                                    ui.label("Spacing");
                                    ui.add(egui::DragValue::new(&mut prim.layout_params[1][3]).speed(0.1).prefix("X:"));
                                    ui.add(egui::DragValue::new(&mut prim.layout_params[2][0]).speed(0.1).prefix("Y:"));
                                    ui.add(egui::DragValue::new(&mut prim.layout_params[2][1]).speed(0.1).prefix("Z:"));
                                });
                            });
                        }
                        
                        ui.separator();

                        // 3. Radial
                        let mut radial_enabled = (prim.layout_flags & engine::primitive::LAYOUT_FLAG_RADIAL) != 0;
                        if ui.checkbox(&mut radial_enabled, "Radial Pattern").changed() {
                            if radial_enabled { prim.layout_flags |= engine::primitive::LAYOUT_FLAG_RADIAL; }
                            else { prim.layout_flags &= !engine::primitive::LAYOUT_FLAG_RADIAL; }
                        }
                        
                        if radial_enabled {
                            ui.indent("radial_indent", |ui| {
                                let mut packed = prim.layout_params[0][0] as u32;
                                let mut count = (packed >> 12) & 0xFF;
                                let mut axis = (packed >> 20) & 0x3;
                                
                                ui.horizontal(|ui| {
                                    ui.label("Count");
                                    ui.add(egui::DragValue::new(&mut count).clamp_range(1..=64));
                                });
                                ui.horizontal(|ui| {
                                    ui.label("Axis");
                                    ui.selectable_value(&mut axis, 0, "X");
                                    ui.selectable_value(&mut axis, 1, "Y");
                                    ui.selectable_value(&mut axis, 2, "Z");
                                });
                                
                                packed = (packed & !0x00FF_F000) | (count << 12) | (axis << 20);
                                prim.layout_params[0][0] = packed as f32;
                                
                                ui.add(egui::Slider::new(&mut prim.layout_params[0][2], 0.0..=10.0).text("Radius"));
                                ui.add(egui::Slider::new(&mut prim.layout_params[0][3], -2.0..=2.0).text("Pitch (Spiral)"));
                            });
                        }
                    });

                    ui.collapsing("Deformers", |ui: &mut egui::Ui| {
                        let mut flags = prim.deform_flags;
                        for slot in 0..2 {
                            ui.group(|ui| {
                                ui.label(format!("Slot {}", slot + 1));
                                let mut current_type = (flags >> (slot * 6)) & 0xF;
                                let mut axis = (flags >> (slot * 6 + 4)) & 0x3;
                                
                                ui.horizontal(|ui| {
                                    ui.selectable_value(&mut current_type, engine::primitive::DEFORM_TYPE_NONE, "None");
                                    ui.selectable_value(&mut current_type, engine::primitive::DEFORM_TYPE_ELONGATE, "Elongate");
                                    ui.selectable_value(&mut current_type, engine::primitive::DEFORM_TYPE_TWIST, "Twist");
                                    ui.selectable_value(&mut current_type, engine::primitive::DEFORM_TYPE_BEND, "Bend");
                                    ui.selectable_value(&mut current_type, engine::primitive::DEFORM_TYPE_TAPER, "Taper");
                                });
                                
                                if current_type != engine::primitive::DEFORM_TYPE_NONE {
                                    ui.horizontal(|ui| {
                                        ui.label("Axis");
                                        ui.selectable_value(&mut axis, 0, "X");
                                        ui.selectable_value(&mut axis, 1, "Y");
                                        ui.selectable_value(&mut axis, 2, "Z");
                                    });
                                    
                                    match current_type {
                                        engine::primitive::DEFORM_TYPE_ELONGATE => {
                                            ui.label("Limits");
                                            ui.horizontal(|ui| {
                                                ui.add(egui::DragValue::new(&mut prim.deform_params[slot][0]).speed(0.1).prefix("X:"));
                                                ui.add(egui::DragValue::new(&mut prim.deform_params[slot][1]).speed(0.1).prefix("Y:"));
                                                ui.add(egui::DragValue::new(&mut prim.deform_params[slot][2]).speed(0.1).prefix("Z:"));
                                            });
                                        }
                                        engine::primitive::DEFORM_TYPE_TAPER => {
                                            ui.add(egui::Slider::new(&mut prim.deform_params[slot][0], -2.0..=2.0).text("Factor"));
                                        }
                                        _ => {
                                            ui.add(egui::Slider::new(&mut prim.deform_params[slot][0], -5.0..=5.0).text("Strength"));
                                        }
                                    }

                                    if current_type != engine::primitive::DEFORM_TYPE_ELONGATE {
                                        ui.label("Pivot Offset");
                                        ui.horizontal(|ui| {
                                            ui.add(egui::DragValue::new(&mut prim.deform_params[slot][1]).speed(0.1).prefix("X:"));
                                            ui.add(egui::DragValue::new(&mut prim.deform_params[slot][2]).speed(0.1).prefix("Y:"));
                                            ui.add(egui::DragValue::new(&mut prim.deform_params[slot][3]).speed(0.1).prefix("Z:"));
                                        });
                                    }
                                }
                                
                                flags = (flags & !(0x3F << (slot * 6))) | (current_type << (slot * 6)) | (axis << (slot * 6 + 4));
                            });
                        }
                        prim.deform_flags = flags;
                    });

                    if ui.button("🗑 Delete Primitive").clicked() {
                        self.primitives.remove(idx);
                        self.selected_idx = None;
                    }
                });
            }
        }
    }

        let full_output = self.egui_ctx.end_frame();
        let paint_jobs = self.egui_ctx.tessellate(full_output.shapes, full_output.pixels_per_point);
        
        for (id, image_delta) in &full_output.textures_delta.set {
            self.egui_renderer.update_texture(&self.engine.ctx.device, &self.engine.ctx.queue, *id, image_delta);
        }
        for id in &full_output.textures_delta.free {
            self.egui_renderer.free_texture(id);
        }
        self.egui_state.handle_platform_output(&self.window, full_output.platform_output);

        let screen_descriptor = egui_wgpu::ScreenDescriptor { size_in_pixels: [self.config.width, self.config.height], pixels_per_point: self.window.scale_factor() as f32 };
        self.egui_renderer.update_buffers(&self.engine.ctx.device, &self.engine.ctx.queue, &mut encoder, &paint_jobs, &screen_descriptor);

        {
            let mut rpass = encoder.begin_render_pass(&wgpu::RenderPassDescriptor {
                label: Some("UI Render Pass"),
                color_attachments: &[Some(wgpu::RenderPassColorAttachment {
                    view: &view,
                    resolve_target: None,
                    ops: wgpu::Operations { load: wgpu::LoadOp::Load, store: wgpu::StoreOp::Store },
                })],
                depth_stencil_attachment: None,
                timestamp_writes: None,
                occlusion_query_set: None,
            });
            self.egui_renderer.render(&mut rpass, &paint_jobs, &screen_descriptor);
        }

        self.engine.ctx.queue.submit(Some(encoder.finish()));
        output.present();
        Ok(())
    }

    fn duplicate_object(&mut self, idx: usize) {
        let mut new_prim = self.primitives[idx].clone();
        let old_id = new_prim.id;
        new_prim.id = self.next_id;
        self.next_id += 1;
        
        // Change color slightly or move it to show it was duplicated
        new_prim.center += Vec3::new(0.5, 0.5, 0.0);

        // For groups, we need to duplicate all children recursively
        // A simple way is to find all children of the old group and duplicate them with the new parent_id
        let mut children_to_dup = Vec::new();
        for p in self.primitives.iter() {
            if p.parent_id == Some(old_id) {
                children_to_dup.push(p.clone());
            }
        }

        self.primitives.push(new_prim);
        let new_parent_id = self.primitives.last().unwrap().id;
        let new_parent_idx = self.primitives.len() - 1;

        for mut child in children_to_dup {
            child.id = self.next_id;
            self.next_id += 1;
            child.parent_id = Some(new_parent_id);
            self.primitives.push(child);
        }
        
        self.selected_idx = Some(new_parent_idx);
    }

    fn add_group(&mut self) {
        let mut p = SdfPrimitive::new_group(Vec3::ZERO);
        p.id = self.next_id;
        self.next_id += 1;
        self.primitives.push(p);
        self.selected_idx = Some(self.primitives.len() - 1);
    }

    fn push_undo(&mut self) {
        self.undo_stack.push(self.primitives.clone());
        if self.undo_stack.len() > 50 {
            self.undo_stack.remove(0);
        }
        self.redo_stack.clear();
    }

    fn undo(&mut self) {
        if let Some(prev) = self.undo_stack.pop() {
            self.redo_stack.push(self.primitives.clone());
            self.primitives = prev;
            self.selected_idx = None;
        }
    }

    fn redo(&mut self) {
        if let Some(next) = self.redo_stack.pop() {
            self.undo_stack.push(self.primitives.clone());
            self.primitives = next;
            self.selected_idx = None;
        }
    }

    fn apply_parent_transform(&mut self, parent_idx: usize, old_pos: Vec3, new_pos: Vec3, old_rot: Quat, new_rot: Quat) {
        let parent_id = self.primitives[parent_idx].id;
        let pos_delta = new_pos - old_pos;
        if pos_delta.length_squared() < 1e-8 && (new_rot.dot(old_rot)).abs() > 0.999999 { return; }
        let rot_relative = new_rot * old_rot.inverse();
        for i in 0..self.primitives.len() {
            if i == parent_idx { continue; }
            if self.primitives[i].parent_id == Some(parent_id) {
                let to_child = self.primitives[i].center - old_pos;
                let new_child_pos = new_pos + rot_relative * to_child;
                let child_old_pos = self.primitives[i].center;
                let child_old_rot = self.primitives[i].rotation;
                self.primitives[i].center = new_child_pos;
                self.primitives[i].rotation = rot_relative * self.primitives[i].rotation;
                self.apply_parent_transform(i, child_old_pos, self.primitives[i].center, child_old_rot, self.primitives[i].rotation);
            }
        }
    }
}

pub fn main() {
    let event_loop = EventLoop::new().unwrap();
    let window = WindowBuilder::new().with_title("SDF.R Desktop Modeler V0.1.0").with_inner_size(winit::dpi::PhysicalSize::new(1280, 720)).build(&event_loop).unwrap();
    let mut app = pollster::block_on(App::new(window)).unwrap();

    let _ = event_loop.run(move |event, elwt| {
        match event {
            Event::WindowEvent { event, .. } => {
                if app.egui_state.on_window_event(&app.window, &event).consumed { return; }
                app.handle_input(&event);
                if app.camera_controller.process_events(&event, &mut app.camera) { return; }
                match event {
                    WindowEvent::CloseRequested => elwt.exit(),
                    WindowEvent::Resized(size) => app.resize(size),
                    WindowEvent::RedrawRequested => {
                        app.update();
                        if let Err(e) = app.render() {
                            eprintln!("Render error: {:?}", e);
                        }
                    }
                    _ => {}
                }
            }
            Event::AboutToWait => { app.window.request_redraw(); }
            _ => {}
        }
    });
}
