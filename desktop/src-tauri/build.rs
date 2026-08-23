mod command_manifest {
    include!("src/command_manifest.rs");
}

fn main() {
    // `generate_context!` validates this path even for Rust-only tests.  The
    // production bundle still requires Vite to populate it before packaging.
    std::fs::create_dir_all("../dist").expect("failed to prepare frontendDist");
    let manifest_path = std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR is missing");
    let manifest_dir = std::path::Path::new(&manifest_path);
    let sidecar = manifest_dir
        .join("binaries")
        .join("psyche-os-sidecar-x86_64-pc-windows-msvc.exe");
    if !sidecar.is_file() {
        let builder = manifest_dir.join("../../scripts/dev/build_desktop_sidecar.py");
        let status = std::process::Command::new("uv")
            .args(["run", "python"])
            .arg(builder)
            .status()
            .expect("uv is required to build the fixed Python sidecar");
        assert!(status.success(), "fixed Python sidecar build failed");
    }
    let attributes = tauri_build::Attributes::new()
        .app_manifest(tauri_build::AppManifest::new().commands(command_manifest::SHIPPED_COMMANDS));
    tauri_build::try_build(attributes).expect("failed to build Tauri command permissions");
}
