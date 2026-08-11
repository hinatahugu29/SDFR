// Marching Cubes Lookup Table (256 entries * 16 values)
// This will be uploaded to GPU Storage Buffer
pub fn get_marching_cubes_table() -> Vec<i32> {
    let mut table = Vec::with_capacity(256 * 16);
    for i in 0..256 {
        let tris = crate::tables::get_triangles(i);
        let mut entry = [-1i32; 16];
        for (j, &val) in tris.iter().enumerate() {
            if j < 16 { entry[j] = val; }
        }
        table.extend_from_slice(&entry);
    }
    table
}
