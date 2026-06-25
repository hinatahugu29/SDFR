use pyo3::prelude::*;

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

