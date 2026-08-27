# Personal build ID release verification

Candidate: `654633e601778ca6b872b662f1f3480f360e6de6`
Profile: `local_personal_bounded_openai_reflection_windows_v1`
Profile digest: `1b91fad63ad04e02e90f9cae70d8d5d36a9a66ec9f00d1002cded853726ca99a`

The successor reuses the accepted `personal-data-safety-1cfca99` evidence. The
only runtime change is trusted build-identity visibility; it changes no
storage, schema, cryptography, recovery, network, or AI behavior.

Observed deterministic checks:

- `cargo test --manifest-path desktop/src-tauri/Cargo.toml --locked --features personal-product trusted_launcher_build_id`: 2 passed.
- `uv run python scripts/dev/verify_personal_package_inventory.py --installer artifacts/e11/personal-build-id-654633e/PSYCHE OS Personal_0.2.0_x64-setup.exe --profile local_personal_bounded_openai_reflection_windows_v1`: PASS.
- SHA-256 of the NSIS installer: `bd93bf5b4254ef8f830f18ff0368927485465c322bdadc7264f84fdee540b71b`.
- NSIS inventory contains `psyche-os-personal-sidecar.exe` and no `psyche-os-sidecar.exe`.

The launcher defines its trusted value through compile-time
`PSYCHE_OS_PERSONAL_BUILD_ID`; `desktop_status` inserts it after the sidecar
response is validated as an object. The two targeted Rust tests prove that a
sidecar `build_id` is overwritten and a non-object status fails closed. The
renderer's `PersonalStatus` accepts the returned optional `build_id`.
