# E02 desktop-shell preflight

**Preflight date:** 2026-08-13
**Verdict:** `READY_TO_IMPLEMENT`
**Scope:** architecture and development workflow only; no E02 product code

## State

- E01 is `ACCEPTED` at `eac9031` and remains reachable unchanged.
- E02 was prepared at `a69a5b1` and remains `READY / NOT_STARTED`.
- `REAL_DATA_GATE` is `CLOSED`; this preflight does not provide authority to
  change it.

## Git workflow

- Canonical accepted/prepared branch: `main`.
- E02 implementation branch: `codex/e02-secure-desktop-shell`, created from
  the final preflight commit.
- High-risk implementation occurs on the candidate branch, not `main`.
- A pushed branch or PR is a candidate for review, not acceptance. Meaningful
  E02 commits may be pushed and one draft PR may target `main`; the PR must not
  be merged and E02 must not enter `accepted_epics` until the independent E02
  review and fresh authoritative post-fix gate pass.

## Desktop decision

ADR-022 selects Tauri 2, Microsoft Edge WebView2, a minimal TypeScript/Vite
renderer, Rust-owned allowlisted commands, and the existing Python core as a
fixed sidecar over bounded framed stdin/stdout. Exact resolved dependencies are
locked during E02; `tauri` must be `>=2.11.1,<3`. The reference versions probed
on 2026-08-13 are core 2.11.5, CLI 2.11.4, API 2.11.1, Vite 8.2.1 and
TypeScript 7.0.2.

| Candidate | Process/renderer and Python integration | Network / privilege model | Packaging / license | Conclusion |
| --- | --- | --- | --- | --- |
| **Tauri 2** | WebView2 renderer → typed Tauri IPC → trusted Rust shell → fixed Python sidecar over stdin/stdout | No TCP/HTTP listener; local packaged origin; per-webview capabilities; no renderer shell/filesystem/SQL/sidecar access | Cargo + npm + fixed Python binary; Windows MSI/NSIS feasible; Apache-2.0 OR MIT | **Selected:** clearest least-authority and origin/command boundary while retaining Python authority |
| Electron | Chromium sandboxed renderer → per-message context bridge → Node main → Python child over stdin/stdout | Can avoid a listener and disable Node in renderer, but trusted main/preload and bundled Chromium/Node surface are broader | Standard Electron Windows packaging; MIT, with larger dependency/update burden | Viable but rejected |
| PySide6 / Qt WebEngine | Chromium-based WebEngine → narrow `QWebChannel` QObject → Python core in trusted application | Can avoid a listener; published QObject slots define the privileged surface | `pyside6-deploy`/Nuitka feasible; LGPLv3/GPLv3/commercial plus Chromium obligations | Viable but rejected: less explicit capability control and heavier license/deployment review |

Official evidence is registered as ARCH-056–ARCH-068 in
`docs/research/SOURCE_REGISTRY.yaml`. It covers Tauri prerequisites,
capabilities/runtime authority, CSP, sidecars, Windows packaging and the
2.11.1 origin/ACL fixes, plus the official Electron and Qt alternative facts.

## Boundary

- **Renderer authority:** packaged local presentation assets and named view
  commands only. No remote origin/capability, navigation, popup, production
  devtools, raw HTML, Node, shell, filesystem, SQL, vault path, key, recovery
  material, process handle or generic dispatch.
- **Trusted Rust shell:** owns WebView2/window policy, Tauri capabilities,
  strict request/response validation, origin/session/confirmation checks,
  fixed sidecar lifecycle and content-free error mapping. It does not own
  domain, storage, crypto, backup, recovery or export semantics.
- **Trusted Python backend:** remains the authoritative E00/E01
  application/domain/policy/storage/crypto/backup/export core. New E02
  application services adapt accepted ports rather than arbitrary CLI strings.
- **Typed IPC:** versioned command-specific schemas with limits and unknown
  field rejection on both renderer→Rust and Rust→Python boundaries. Python
  messages use bounded framing over inherited stdin/stdout only.
- **No listener:** no TCP, HTTP, local socket, remote origin or cloud runtime.
  WebView2's Tauri `.localhost` custom-protocol URLs are in-process virtual
  origins/IPC transport and do not create a network listener.

## Toolchain

Verified locally:

- Windows 10 Pro profile, build 26200, x64;
- Python 3.12.10 and uv 0.9.30;
- Node 24.18.0, npm 11.16.0 and pnpm 11.1.1 (npm selected);
- Rust/Cargo 1.94.1, stable `x86_64-pc-windows-msvc`;
- Microsoft Edge WebView2 151.0.4129.78;
- Microsoft C++ Build Tools with “Desktop development with C++” are **not
  installed** and are a required prerequisite before the first E02 build.

Expected targeted desktop commands, fixed by ADR-022:

```powershell
uv sync --frozen
uv run pytest -q tests/<E02-targeted-paths>
npm --prefix desktop ci
npm --prefix desktop run typecheck
npm --prefix desktop run lint
npm --prefix desktop run test:unit
cargo fmt --check --manifest-path desktop/src-tauri/Cargo.toml
cargo clippy --manifest-path desktop/src-tauri/Cargo.toml --all-targets -- -D warnings
cargo test --manifest-path desktop/src-tauri/Cargo.toml
npm --prefix desktop run test:desktop
npm --prefix desktop run build
npm --prefix desktop run tauri:build -- --debug
```

The E02 implementation must define the referenced npm scripts. Dependency
installation produces committed npm/Cargo locks and a fixed Python-sidecar
build specification. The repository FULL gate remains exactly the six commands
in the calibrated E02 prompt and runs once after targeted evidence is ready.

## Residual uncertainties

- The missing Microsoft C++ Build Tools prerequisite must be installed before
  compilation; it was not installed or mutated during this preflight.
- Actual Windows tests must prove WebView2 CSP/origin/navigation/popup behavior,
  sidecar framing/backpressure/crash handling, secret-free renderer surfaces,
  and the debug packaging of SQLCipher plus the Python sidecar.
- Exact compatible dependency versions and transitive licenses are frozen in
  lockfiles during installation. Any Tauri resolution below 2.11.1 or a need
  for network, remote origin, generic shell/filesystem authority, or a different
  Python boundary invokes the architecture-deviation procedure.

## Preflight verdict

`READY_TO_IMPLEMENT`

E02 implementation may begin only on `codex/e02-secure-desktop-shell` after
the missing build prerequisite is satisfied. E02 remains `READY / NOT_STARTED`.
