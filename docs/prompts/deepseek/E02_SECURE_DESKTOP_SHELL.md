# PSYCHE OS — EPIC E02: Secure Desktop Shell and Vault Operations UX

**Project root:** `C:\Dev\psyche-os`  
**Accepted E01 commit:** `eac9031`  
**Prepared E02 commit:** `a69a5b1`
**Canonical branch:** `main`
**Implementation branch:** `codex/e02-secure-desktop-shell`
**Risk:** `RISK-H`  
**Expected final gate:** `FULL`  
**Data:** repository-owned fictional synthetic fixtures only  
**REAL_DATA_GATE:** `CLOSED`

## Role and outcome

Deliver one bounded outcome: a local, accessible desktop vertical slice for
vault unlock/privacy status, correction/deletion, backup health, isolated
recovery and export through a narrow typed IPC boundary. Preserve the accepted
E01 core and keep the renderer incapable of reading vault paths, keys, recovery
secrets or direct storage handles.

Do not expand this epic into the evidence archive, capture system, chat, cloud,
imports, projections, analytics or release/distribution work.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/implementation/E01_ACCEPTANCE_REPORT.md`
- `docs/development/EPIC_MAP.md` — E02 only
- `docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md`

Then read only these directly relevant sources and sections:

- `docs/DECISION_LOG.md` — ADR-003, ADR-009, ADR-010, ADR-018 and
  ADR-022
- `docs/development/reports/E02_PREFLIGHT.md`
- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §§16, 19.3–19.4,
  20.3–20.5, 21 and 22.1/22.4
- `docs/architecture/SYSTEM_ARCHITECTURE.md` — §§4–6, 8.4–8.6, 9,
  11 and 12
- `docs/architecture/PRIVACY_SECURITY_MODEL.md` — PS-12, PS-14–PS-22,
  PS-25 and PS-26
- `docs/architecture/THREAT_MODEL.md` — trust-boundary table and TM-03,
  TM-04, TM-08, TM-13–TM-19 and TM-23
- `docs/architecture/REAL_DATA_GATE.yaml`
- `src/psyche_os/application/ports.py`
- `src/psyche_os/interfaces/cli.py`
- `src/psyche_os/backup_export/operations.py`
- `src/psyche_os/domain/entities.py` — correction/deletion entities only

Inspect additional files only when they are directly imported by a touched
path. Do not load historical v1, the research corpus, unrelated architecture,
future epic sections or prior repair prompts.

## Frozen architecture

ADR-022 has completed the mandatory desktop checkpoint. Do not reopen the
framework choice during implementation.

- Use Tauri `2.x` with Microsoft Edge WebView2 on Windows, a minimal local
  TypeScript/Vite renderer and Rust-owned allowlisted Tauri commands.
- Keep the accepted Python application/domain/policy/storage/crypto/backup/
  export core authoritative as one fixed sidecar. Rust communicates with it
  only through length-bounded, versioned JSON messages over inherited
  stdin/stdout pipes. Do not add HTTP, TCP, a local socket or a localhost
  server.
- The renderer receives only explicit commands and bounded view models. Do not
  grant it a shell/filesystem plugin, generic IPC transport, sidecar handle,
  process execution, SQL, arbitrary CLI/Python dispatch, vault paths, keys or
  recovery material.
- Use npm and committed `package-lock.json`, Cargo and committed `Cargo.lock`,
  and the existing uv/Python 3.12 toolchain. Resolve current compatible stable
  dependencies when installing, with `tauri >=2.11.1,<3`; the preflight
  reference versions are core 2.11.5, CLI 2.11.4, API 2.11.1, Vite 8.2.1 and
  TypeScript 7.0.2.
- Microsoft C++ Build Tools with “Desktop development with C++” is a required
  local prerequisite and was absent at preflight. Satisfy it before the first
  build; do not report a skipped mandatory build or Windows desktop test as
  PASS.

If a concrete feasibility contradiction requires a different framework,
network transport, remote origin, renderer authority, generic dispatcher or
non-Python ownership of accepted semantics, stop only the affected portion and
create `docs/development/deviations/E02_DESKTOP_BOUNDARY.md` from the
architecture-deviation template. Do not silently switch or weaken ADR-022.

## In scope

- A restrictive local desktop shell and a versioned, allowlisted, typed IPC
  request/response contract. The renderer receives bounded view models and
  opaque IDs, never storage paths, key material, SQL, arbitrary CLI arguments
  or generic filesystem/process capabilities.
- A minimal unlock/lock/session-status flow with honest residual-risk and
  privacy status. Secrets cross only the smallest trusted boundary and are not
  retained in renderer state, URLs, logs, crash metadata or clipboard helpers.
- A Privacy Center vertical slice for effective policy/status, correction,
  deletion dry-run/confirmation/receipt limits, and backup-expiry/external-copy
  limitations using typed application services.
- Backup/recovery UX over the accepted E01 production paths: backup health,
  verify, isolated recovery validation, explicit separate activation and clear
  failure state. Never collapse restore validation into activation.
- Export preview and execution over accepted export contracts, with purpose,
  audience, scope, encryption/redaction status and truthful limitations.
- Keyboard-first navigation, focus management, labels/names, error association,
  non-color status cues, reduced-motion behavior and a usable offline path for
  the bounded views above.
- Synthetic end-to-end and adversarial evidence for the selected Windows
  desktop profile and IPC/renderer boundary.

## Out of scope

- E03 evidence archive, timeline, capture, search, claims or model views.
- Chat persona, LLM/model/provider code, cloud, network listeners, telemetry,
  sync, sharing, auto-update, public distribution or release signing.
- Broad imports/parsers, blob/attachment enablement, general filesystem
  mutation, arbitrary file browsing or renderer plugins.
- New assessment, clinical, crisis, recommendation or analytics behavior.
- Redesigning E00/E01 crypto, backup format, restore validation, Windows
  activation, canonical schema or rollback architecture.
- Real personal or sensitive data while `REAL_DATA_GATE = CLOSED`.

## Git and review workflow

Begin from current `main` and perform E02 implementation only on
`codex/e02-secure-desktop-shell`. This prompt explicitly permits coherent E02
candidate commits, pushing only that candidate branch, and creating/updating
one draft PR against `main` after meaningful implementation commits exist.
Candidate publication and a PR mean “candidate for review,” not acceptance.

Do not merge the PR, push implementation to `main`, force-push, rewrite
accepted history, mark E02 `ACCEPTED`, append E02 or its candidate SHA to
`accepted_epics`, prepare E03, or create an empty/no-diff PR.

## Invariants to protect

- C-01, C-10–C-14, C-17 and C-19–C-20.
- The desktop boundary is an interface adapter: domain/application contracts
  remain authoritative and neither renderer nor shell writes the database
  directly.
- No listener is introduced. The core remains offline and provider-independent.
- Imported/rendered strings are untrusted data. Unknown command, origin,
  payload field, enum value, identifier or state transition fails closed.
- Deletion is previewed and limitation-aware; correction preserves history;
  export is not backup; restore is not activation; validation-only never
  reports activation success.
- Accepted E01 inventory, recovery, fault-preservation, Windows-boundary and
  evidence invariants cannot regress.
- `FEATURE_DEFERRED_PRE_REAL_DATA` remains enforced for blob writes and general
  filesystem mutation.

## Implementation requirements

1. Create a small application-service layer behind the IPC commands. Reuse
   accepted ports/operations; do not dispatch arbitrary CLI strings or expose a
   generic command bridge.
2. Define explicit request and response schemas with version, command-specific
   payload limits, unknown-field rejection, stable content-free error codes and
   opaque correlation IDs. State-changing commands require current session
   authority and command-specific confirmation where destructive.
3. Configure Tauri fail closed: restrictive CSP with no remote
   origins, origin validation, no navigation/popups/devtools in the production
   profile, no Node/general process bridge, no arbitrary eval, and no renderer
   file/vault/key access. Grant only named local-window capabilities and keep
   sidecar spawn/pipe ownership inside trusted Rust. Pin new direct/transitive
   dependencies and record license/provenance implications.
4. Use text-safe rendering APIs and contextual encoding for every dynamic
   value. Do not render vault-derived strings through raw HTML.
5. Keep operational output content-free. UI diagnostics may expose bounded
   categories and recovery guidance, never secrets, source content, sensitive
   paths or raw exception bodies.
6. Keep all fixtures clearly fictional, repository-owned and synthetic. Do not
   copy data from conversations, local user files or external accounts.

## Failure-driven validation

Every new check must name the realistic failure it closes and cite one target
from E02-T1 through E02-T7. Add no arbitrary coverage threshold, giant browser
matrix, framework-generic suite or duplicate security-theater assertion.

- **T1:** prove the packaged/local shell starts on the selected Windows
  profile, remote origins/navigation/popups fail closed, production restrictions
  are enabled, and no TCP/HTTP/local-socket listener opens during offline flows.
- **T2:** prove unknown commands, wrong origins, malformed/oversized payloads,
  unknown fields and stale/sessionless state-changing requests are rejected
  before an application operation; prove no command reaches arbitrary SQL,
  CLI/process arguments, filesystem mutation, Python dispatch or another
  non-allowlisted action.
- **T3:** scan renderer state, logs, URLs, DOM snapshots and errors for vault
  paths, SQLCipher keys, VMK, recovery secret, raw package key, exception body
  and synthetic plaintext canaries; prove malicious markup remains inert under
  the actual CSP and cannot navigate, execute or gain IPC authority.
- **T4:** prove correction retains history; deletion requires a dry-run and
  explicit confirmation, displays backup/external-copy limitations, emits no
  deleted content/hash, and preserves state on cancellation or injected failure.
- **T5:** prove recovery uses an isolated candidate, validation-only is not
  activation, activation is separately explicit, and injected failure preserves
  the active vault and accepted E01 semantics.
- **T6:** prove export preview/execution retains purpose, audience, scope,
  encryption/redaction state, distinguishes export from backup and fails closed
  when policy is missing.
- **T7:** prove keyboard traversal, focus return, accessible names, error
  association, non-color status, reduced motion and offline operation on the
  actual bounded Windows UI.

All mandatory Windows desktop/IPC/security tests must execute. A skipped T1–T7
renderer, IPC, deletion, recovery, activation, export or accessibility proof is
not a pass.

## Validation

During implementation run the smallest affected unit, contract, UI and
integration checks. The desktop layout and scripts must support these exact
commands:

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

Run the implementation `FULL` gate only after T1–T7 targeted evidence is
locally ready:

```powershell
uv sync --frozen
uv run pytest -q
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python scripts/validate_e01_assurance.py
python scripts/dev/validate_orchestration.py
```

No arbitrary coverage target applies. A known accepted baseline skip may remain
only if it is unchanged and unrelated to E02; no mandatory E02 or E01 proof may
be skipped. Do not rerun the FULL gate after every minor edit. If implementation
changes after a failed FULL gate, record that clearly; independent acceptance
must run a fresh authoritative post-fix gate.

## Frozen E02 acceptance targets

### E02-T1 — Secure local desktop shell

- [ ] The selected shell starts locally with no localhost/network listener and
  no remote origin; production renderer restrictions are enabled.

### E02-T2 — Typed IPC authority

- [ ] Commands are versioned, allowlisted and typed; unknown commands, fields
  and origins fail closed; state changes require valid session authority; no
  arbitrary SQL, process, filesystem or CLI bridge exists.

### E02-T3 — Renderer confidentiality and content safety

- [ ] Renderer-visible state, DOM, logs, URLs and errors expose no vault paths,
  database keys, VMK, recovery secret, package key or sensitive raw exception
  data; malicious synthetic markup renders inertly and gains no privilege.

### E02-T4 — Privacy / correction / deletion UX

- [ ] A synthetic flow proves privacy status; correction preserves history;
  deletion requires dry-run and explicit confirmation, yields a
  limitation-aware receipt, and preserves state on cancellation/failure.

### E02-T5 — Backup and independent recovery UX

- [ ] The UI preserves accepted E01 backup-health/verify, isolated candidate,
  validation-only-not-activation, separate explicit activation and
  failure-preserves-active-vault semantics without redesigning E01.

### E02-T6 — Export UX

- [ ] Preview/execution preserves purpose, audience, scope and
  encryption/redaction status, distinguishes export from backup, and fails
  closed on missing policy.

### E02-T7 — Accessibility and offline behavior

- [ ] The bounded UI proves keyboard-first traversal, focus return, accessible
  names, error association, non-color-only status, reduced motion, offline
  operation and no production listener/socket.

## Work and stop rules

Preserve unrelated changes. When E02-T1 through E02-T7 pass and accepted E00/E01
invariants remain green, **STOP**. Do not conduct a broad security audit, run
Security Workbench, redesign the renderer architecture, implement E03, add
cloud/network, enable imports/blobs, add AI, add updater/release/signing, chase
arbitrary coverage, or add speculative hardening unrelated to a demonstrated
T1–T7 failure. Record new hardening ideas as later work unless they demonstrate
failure of a frozen target.

A material desktop-boundary conflict requires the focused deviation and stops
only the affected portion. Dependency, CSP, origin, IPC or packaging uncertainty
is not permission to weaken a check or relabel it as PASS.

Create `docs/development/reports/E02.md` from the epic report template. If all
implementation criteria and local evidence pass, set only
`current_epic.status: IMPLEMENTED`; otherwise set `BLOCKED`. Do not accept E02,
append accepted history, prepare E03, merge the candidate PR or self-award the
required independent Codex review. Candidate commits and the draft PR remain
review evidence only.

End with changed areas, the desktop choice, exact targeted/final results,
skips, residual risks and the focused Codex review required for the new
webview/IPC trust boundary.
