# E02 final bounded acceptance report

**Review date:** 2026-08-13
**Verdict:** `ACCEPTED`
**Base:** `f36abb023abc7f388576aa97ebd64c95c6c16023`
**Accepted E02 implementation commit:** `e8535ffeb74ba7858cbc3eb1aa67fed9634dded1`
**Profile:** Windows 11, Tauri 2 / Edge WebView2, synthetic-only
**REAL_DATA_GATE:** `CLOSED`

## Bounded review decision

| Target | Result | Production-path evidence |
| --- | --- | --- |
| T1 Secure local shell | **PASS** | Packaged local Tauri origin only; remote navigation and popups denied; devtools disabled; restrictive CSP; no listener; fixed sidecar over inherited pipes. The resolved Tauri manifest showed that `core:default` would grant path, event, window, webview, app, image, resource, menu and tray defaults, so it was removed. Generated `capabilities.json` now contains only the twelve named E02 commands. The packaged workflows complete with external hostname resolution forced unavailable, no desktop/sidecar INET connection and no application listener. Observed WebView2 background HTTPS is recorded separately and is not renderer authority under the frozen threat model. |
| T2 Typed IPC | **PASS** | Renderer calls named Tauri commands; Rust strict structs reject unknown fields and bind fixed Python commands; framed JSON is versioned and bounded to 65,536 bytes; Python rejects unknown fields/commands and stale or missing sessions before operations; Rust verifies correlation/version and maps errors to content-free codes. No renderer-controlled dispatch, arguments, sidecar path, SQL, filesystem or process authority exists. |
| T3 Renderer confidentiality/content | **PASS** | Dynamic content uses `textContent`/text nodes; no raw HTML sink exists. The real renderer path and packaged UIA flow render malicious markup inertly. UIA, response, stderr, state, URLs and errors expose no vault path, key, VMK, recovery/package secret or raw exception body. |
| T4 Privacy/correction/deletion | **PASS** | **Classification A — authorized ephemeral synthetic UX.** The frozen prompt requires a synthetic flow and explicitly leaves evidence archive/capture to E03. Correction history and deletion plan/receipt state are therefore session-scoped UX/application-service proof, not canonical storage. UI, response and report wording now say synthetic-session semantics and explicitly state that no canonical record changed. Dry-run, exact confirmation, limitations, content-free receipt and cancellation preservation pass. |
| T5 Backup/recovery | **PASS** | UI commands reach accepted `verify_backup_file`, `restore_backup` and `activate_restored_vault`. Validation creates an isolated candidate and reports `activated=false`; activation is separately confirmed; failure preserves active state; renderer receives no paths or keys. |
| T6 Export | **PASS** | Preview precedes execution; purpose/audience/scope are allowlisted; encryption and redaction are mandatory and truthful; missing/invalid policy fails closed; execution reaches accepted `ExportBuilder`/`verify_export`; export is explicitly not backup and no renderer output path exists. |
| T7 Accessibility/offline | **PASS** | Packaged native UIA drives keyboard-operable controls with labels, associated errors, focus transitions/return and non-color status; CSS honors reduced motion. All bounded workflows pass with remote hostname resolution unavailable, no application listener and no desktop/sidecar INET use. |

## Acceptance fixes

- Removed unnecessary `core:default` from the renderer capability and added a regression test against any `core:*` grant.
- Forced external hostname resolution to fail in the production WebView profile and strengthened packaged network evidence without treating WebView2 background behavior as application authority.
- Made correction/deletion UI, service response and implementation report explicitly synthetic-session-only.
- Reconciled the implemented-but-unaccepted candidate state before the final gates.

## Fresh desktop/toolchain gate

```text
uv sync --frozen: PASS (25 packages audited)
targeted pytest: PASS (9 passed)
npm ci: PASS (189 packages audited; 0 vulnerabilities)
npm typecheck: PASS
npm lint: PASS
npm test:unit: PASS (6 passed)
cargo fmt --check: PASS
cargo clippy --all-targets --locked -- -D warnings: PASS
cargo test --locked: PASS (6 passed)
npm test:desktop: PASS (native UIA; no skips)
npm build: PASS
npm tauri:build -- --debug: PASS (debug executable and NSIS bundle)
```

## Fresh authoritative FULL gate

```text
uv sync --frozen: PASS (25 packages audited)
uv run pytest -q: PASS (303 passed, 1 skipped)
validate_f0_scope.py: PASS (6/6)
validate_f0_artifacts.py: PASS (4/4)
validate_e01_assurance.py: PASS (16/16)
validate_orchestration.py: PASS (112/112)
```

The sole skip is the unchanged accepted-baseline Windows administrator-only
symlink fixture in `TestF09aPathEscape::test_symlink_traversal_rejected`. It is
unrelated to E01 backup/recovery and every E02 mandatory proof; no E01/E02
mandatory proof skipped.

## Decision

T1–T7 pass, the T4 storage semantics are reconciled without implementing E03,
the renderer capability is least-authority, required packaged proofs and both
gates pass, E01 remains green, deferred surfaces remain deferred, and
`REAL_DATA_GATE` remains `CLOSED`. E02 is `ACCEPTED`.
