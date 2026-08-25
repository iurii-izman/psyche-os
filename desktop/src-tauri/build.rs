#[cfg(feature = "personal-product")]
mod command_manifest {
    include!("src/personal_command_manifest.rs");
}
#[cfg(not(feature = "personal-product"))]
mod command_manifest {
    include!("src/command_manifest.rs");
}
#[cfg(feature = "personal-product")]
#[path = "src/command_manifest.rs"]
mod full_command_manifest;

fn main() {
    // `generate_context!` validates this path even for Rust-only tests.  The
    // production bundle still requires Vite to populate it before packaging.
    let frontend_dist = if cfg!(feature = "personal-product") { "../dist-personal" } else { "../dist" };
    std::fs::create_dir_all(frontend_dist).expect("failed to prepare frontendDist");
    let manifest_path = std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR is missing");
    let manifest_dir = std::path::Path::new(&manifest_path);
    let sidecar = manifest_dir
        .join("binaries")
        .join("psyche-os-sidecar-x86_64-pc-windows-msvc.exe");
    let personal_sidecar = manifest_dir
        .join("binaries")
        .join("psyche-os-personal-sidecar-x86_64-pc-windows-msvc.exe");
    let sidecar_ready = if cfg!(feature = "personal-product") {
        personal_sidecar.is_file()
    } else {
        sidecar.is_file() && personal_sidecar.is_file()
    };
    if !sidecar_ready {
        let builder = manifest_dir.join("../../scripts/dev/build_desktop_sidecar.py");
        let status = std::process::Command::new("uv")
            .args(["run", "python"])
            .arg(builder)
            .status()
            .expect("uv is required to build the fixed Python sidecar");
        assert!(status.success(), "fixed Python sidecar build failed");
    }
    // Tauri validates every checked-in capability file at build time, including
    // the main-product capability that is not granted by the Personal config.
    // Define its permissions here without granting them to the Personal binary.
    let commands: &'static [&'static str] = if cfg!(feature = "personal-product") {
        Box::leak(
            [
            command_manifest::SHIPPED_COMMANDS,
            full_command_manifest::SHIPPED_COMMANDS,
            ]
            .concat()
            .into_boxed_slice(),
        )
    } else {
        command_manifest::SHIPPED_COMMANDS
    };
    let attributes = tauri_build::Attributes::new()
        .app_manifest(tauri_build::AppManifest::new().commands(&commands));
    tauri_build::try_build(attributes).expect("failed to build Tauri command permissions");
}
