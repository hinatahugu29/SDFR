fn main() {
    let source = include_str!("common.wgsl");
    let mut frontend = naga::front::wgsl::Frontend::new();
    let module = match frontend.parse(source) {
        Ok(m) => m,
        Err(e) => {
            println!("WGSL parse error: {:?}", e);
            println!("{}", e.emit_to_string(source));
            std::process::exit(1);
        }
    };
    let mut validator = naga::valid::Validator::new(
        naga::valid::ValidationFlags::all(),
        naga::valid::Capabilities::all(),
    );
    let info = match validator.validate(&module) {
        Ok(info) => info,
        Err(e) => {
            println!("Validation error: {:?}", e);
            println!("{}", e.emit_to_string(source));
            std::process::exit(1);
        }
    };
    let options = naga::back::spv::Options::default();
    match naga::back::spv::write_vec(&module, &info, &options, None) {
        Ok(words) => println!("SPIR-V generated OK: {} words", words.len()),
        Err(e) => {
            println!("SPIR-V codegen error: {:?}", e);
            std::process::exit(1);
        }
    }
}
