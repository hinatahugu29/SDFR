#[test]
fn test_wgsl_compile() {
    let source = include_str!("common.wgsl");
    let mut frontend = naga::front::wgsl::Frontend::new();
    match frontend.parse(source) {
        Ok(_) => println!("WGSL parsed successfully!"),
        Err(e) => {
            println!("WGSL parse error: {:?}", e);
            e.emit_to_stderr_with_path(source, "common.wgsl");
            panic!("WGSL parse failed");
        }
    }
}
