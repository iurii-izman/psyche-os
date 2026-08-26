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

#[cfg(feature = "personal-product")]
fn personal_release_identity() -> (String, String) {
    const BUILD_ID: &str = "PSYCHE_OS_PERSONAL_BUILD_ID";
    const PROFILE_DIGEST: &str = "PSYCHE_OS_PERSONAL_PROFILE_DIGEST";

    // These values are compile-time launcher identity, not ordinary runtime
    // configuration.  Without these dependencies Cargo can reuse a stale
    // Personal binary after the packaging script computes new identities.
    println!("cargo:rerun-if-env-changed={BUILD_ID}");
    println!("cargo:rerun-if-env-changed={PROFILE_DIGEST}");

    let build_id = std::env::var(BUILD_ID).ok();
    let profile_digest = std::env::var(PROFILE_DIGEST).ok();
    let release = std::env::var("PROFILE").as_deref() == Ok("release");
    let valid_build_id = build_id.as_deref().is_some_and(|value| {
        value.len() == 40
            && value
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    });
    let valid_profile_digest = profile_digest.as_deref().is_some_and(|value| {
        value.len() == 64
            && value
                .bytes()
                .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
    });

    if release && (!valid_build_id || !valid_profile_digest) {
        panic!("Personal release builds require valid PSYCHE_OS_PERSONAL_BUILD_ID and PSYCHE_OS_PERSONAL_PROFILE_DIGEST");
    }
    if !release
        && ((build_id.is_some() && !valid_build_id && build_id.as_deref() != Some("UNBOUND"))
            || (profile_digest.is_some()
                && !valid_profile_digest
                && profile_digest.as_deref() != Some("UNBOUND")))
    {
        panic!("Personal build identity must be lowercase hexadecimal or explicit debug UNBOUND");
    }

    // Debug builds remain usable without a package identity, but `env!` below
    // means every compiled launcher always receives a build-script value.
    (
        build_id.unwrap_or_else(|| "UNBOUND".to_owned()),
        profile_digest.unwrap_or_else(|| "UNBOUND".to_owned()),
    )
}

fn main() {
    #[cfg(feature = "personal-product")]
    {
        let (build_id, profile_digest) = personal_release_identity();
        println!("cargo:rustc-env=PSYCHE_OS_PERSONAL_BUILD_ID={build_id}");
        println!("cargo:rustc-env=PSYCHE_OS_PERSONAL_PROFILE_DIGEST={profile_digest}");
    }
    // `generate_context!` validates this path even for Rust-only tests.  The
    // production bundle still requires Vite to populate it before packaging.
    let frontend_dist = if cfg!(feature = "personal-product") {
        "../dist-personal"
    } else {
        "../dist"
    };
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
    #[cfg(feature = "personal-product")]
    let commands: &'static [&'static str] = Box::leak(
        [
            command_manifest::SHIPPED_COMMANDS,
            full_command_manifest::SHIPPED_COMMANDS,
        ]
        .concat()
        .into_boxed_slice(),
    );
    #[cfg(not(feature = "personal-product"))]
    let commands: &'static [&'static str] = command_manifest::SHIPPED_COMMANDS;

    let attributes = tauri_build::Attributes::new()
        .app_manifest(tauri_build::AppManifest::new().commands(&commands));
    tauri_build::try_build(attributes).expect("failed to build Tauri command permissions");
}
