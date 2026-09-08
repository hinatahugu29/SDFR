// gpu.rs が実行時に組み立てるのと同じ連結ソースを検証する。
// common.wgsl 単体を見る test_wgsl2 / test_wgsl_spv では detect / marching_cubes /
// dual_contouring 側の参照ミスを取りこぼす
fn main() {
    let source = format!(
        "{}\n{}\n{}\n{}",
        include_str!("common.wgsl"),
        include_str!("detect.wgsl"),
        include_str!("marching_cubes.wgsl"),
        include_str!("dual_contouring.wgsl"),
    );
    let mut frontend = naga::front::wgsl::Frontend::new();
    let module = match frontend.parse(&source) {
        Ok(m) => m,
        Err(e) => {
            println!("WGSL parse error: {}", e.emit_to_string(&source));
            std::process::exit(1);
        }
    };
    let mut validator = naga::valid::Validator::new(
        naga::valid::ValidationFlags::all(),
        naga::valid::Capabilities::all(),
    );
    match validator.validate(&module) {
        Ok(_) => println!("Combined WGSL validated successfully!"),
        Err(e) => {
            println!("Validation error: {}", e.emit_to_string(&source));
            std::process::exit(1);
        }
    }
}
