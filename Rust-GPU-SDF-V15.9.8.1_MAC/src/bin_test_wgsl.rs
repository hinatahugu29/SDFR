fn main() {
    let source = include_str!("common.wgsl");
    let mut frontend = naga::front::wgsl::Frontend::new();
    match frontend.parse(source) {
        Ok(_) => println!("WGSL parsed successfully!"),
        Err(e) => {
            println!("WGSL parse error: {:?}", e);
            println!("{}", e.emit_to_string(source));
            std::process::exit(1);
        }
    }
}
