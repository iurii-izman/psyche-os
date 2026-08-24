# P1 package-boundary technical evidence

**Scope:** P1-01 Synthetic frozen-resource repair and P1-02 package-boundary
receipts. This is technical evidence only; it is not human acceptance or an
independent security, privacy, or legal approval. `REAL_DATA_GATE` remains
`CLOSED` and all exercised content is repository-owned synthetic data.

## Candidate identity

| Field | Value |
| --- | --- |
| Algorithm | `PSYCHE-OS-DIRTY-CANDIDATE-v1` |
| Manifest | `docs/development/personal-mode-v1/P1_TASK_OWNED_MANIFEST.txt` |
| Candidate identity algorithm | `PSYCHE-OS-DIRTY-CANDIDATE-v1` |
| Binding mode | `PMV1-DIRTY-CANDIDATE-DETACHED-RECEIPT-V1` |
| Detached receipt | `dist/evidence/personal-mode-v1/P1_CANDIDATE_RECEIPT.json` |
| Candidate binding rule | A reviewer MUST recompute the candidate digest from the explicit manifest and compare it with `receipt.candidate_sha256`; independently hash the manifest and this evidence file and compare them with their receipt fields. |

The evidence file and manifest are candidate inputs. The detached receipt is
generated only after those bytes are frozen and is excluded from the manifest;
it is generated acceptance evidence, not source or authority. This removes the
self-reference without normalization, a per-file hashing exception, or a
cryptographic fixed point. This file intentionally contains no final candidate
SHA-256 literal.

## P1-01: Synthetic frozen resource

Classification: **A — legitimate packaged resource.** `status.get` constructs
`DesktopApplicationService`, which constructs `E03ArchiveService`; that service
validates the package-owned Orchid Station authority fixture during startup.
The frozen Synthetic sidecar therefore legitimately requires
`psyche_os/fixtures/e03_orchid_station_v1.json` at its runtime resource path.

Repair: `scripts/dev/build_desktop_sidecar.py` adds only that fixture to the
Synthetic PyInstaller `--add-data` list at `psyche_os/fixtures`. The Personal
build has no corresponding data inclusion. The helper also verifies the actual
Synthetic archive contains the resource and validates the current status
contract (`real_data_gate=CLOSED`, `inbound_listener=NONE`) instead of the
retired `network` field.

| Command | Exit | Decisive result |
| --- | --- | --- |
| `npm --prefix desktop run tauri:build:personal` | 0 | Builds both profile-specific sidecars; Synthetic helper reports `PASS: ... synthetic probe passed`; emits `PSYCHE OS Personal_0.2.0_x64-setup.exe`. |
| `uv run python -m PyInstaller.utils.cliutils.archive_viewer -r -b desktop/src-tauri/binaries/psyche-os-sidecar-x86_64-pc-windows-msvc.exe` | 0 | Contains `psyche_os\\fixtures\\e03_orchid_station_v1.json`. |
| Frozen executable `status.get` from a temporary non-repository working directory | 0 | `status=ok`, `real_data_gate=CLOSED`, `inbound_listener=NONE`; no source-tree working-directory fallback. |
| `npm --prefix desktop run build:synthetic` | 0 | Synthetic Vite build completed. |

## Personal isolation and product boundary

| Command | Exit | Decisive result |
| --- | --- | --- |
| `uv run python scripts/dev/verify_personal_package_inventory.py --installer desktop/src-tauri/target/release/bundle/nsis/PSYCHE\ OS\ Personal_0.2.0_x64-setup.exe` | 0 | Actual NSIS installer has the desktop host and `psyche-os-personal-sidecar.exe`, not Synthetic sidecar; Personal renderer, command table, config, and frozen modulegraph pass isolation checks. |
| `npm --prefix desktop run build:personal` | 0 | Personal-only renderer build completed from `vite.personal.config.ts`. |
| `cargo test --manifest-path desktop/src-tauri/Cargo.toml --features personal-product personal_` | 0 | 4/4: Personal command/capability table; absent `OPENAI_API_KEY`; closed sidecar reports `CLOSED → NOT_ADMITTED`, rejects AI, and creates no Personal root; admitted synthetic fixture captures, retrieves, searches, locks, and rejects AI. |
| `uv run pytest -q tests/unit/test_dirty_candidate_identity.py tests/integration/test_personal_runtime_slice_c.py` | 0 | 5/5: explicit identity helper and Personal dispatcher/lifecycle `NEVER_CLOUD` E2E coverage pass. |

## RDG dimensions

| Dimension | Final technical receipt |
| --- | --- |
| RDG-07 | Personal Rust test proves `env_clear` child environment excludes `OPENAI_API_KEY`; actual frozen Personal modulegraph inspection excludes forbidden provider/archive surfaces. |
| RDG-08 | `build:personal` emits the Personal renderer; actual inventory rejects AI/provider, archive, and action renderer surfaces and checks Personal command/capability ownership. |
| RDG-09 | Actual NSIS installer inventory is exact: host plus Personal sidecar; Synthetic sidecar is absent. |
| RDG-12 | Rust framed-protocol E2E proves the closed `NOT_ADMITTED` path and admitted synthetic Personal capture/search/lock path, with provider command absent in both. |

## Supporting verification

| Command | Exit | Result |
| --- | --- | --- |
| `npm --prefix desktop run typecheck` | 0 | Passed. |
| `npm --prefix desktop run lint` | 0 | Passed. |
| `npm --prefix desktop run test:unit` | 0 | 7 files, 60 tests passed. |
| `cargo check --manifest-path desktop/src-tauri/Cargo.toml --features personal-product` | 0 | Passed. |
| `cargo clippy --manifest-path desktop/src-tauri/Cargo.toml --all-targets --features personal-product -- -D warnings` | 0 | Passed. |
| `uv run ruff format --check scripts/dev/build_desktop_sidecar.py && uv run ruff check scripts/dev/build_desktop_sidecar.py` | 0 | Passed. |
| `uv run mypy src` | 1 | 53 pre-existing source-wide errors, none in the touched build helper; recorded as existing repository type debt. |
| `gitleaks detect --no-git --source {build-helper,evidence,manifest} --redact --verbose` | 0 | No leaks in all three P1-changed files. |
| `git diff --check` | 0 | Passed (Git only reports existing LF→CRLF working-copy warnings). |

The emitted-package receipts above bind the concrete build/profile artifacts.
`scripts/dev/dirty_candidate_identity.py` writes or verifies the detached
receipt, including independent exact-byte hashes for this evidence file and the
manifest. The E11 evaluation remains DRAFT and `REAL_DATA_GATE` remains
`CLOSED`.
