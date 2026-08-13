# PSYCHE OS — EPIC E02: Secure Desktop Shell and Vault Operations UX

**Project root:** `C:\Dev\psyche-os`  
**Accepted E01 commit:** `eac9031`  
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

- `docs/DECISION_LOG.md` — ADR-003, ADR-009, ADR-010 and ADR-018
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

## Mandatory architecture checkpoint

ADR-003 intentionally deferred the exact desktop-shell choice. Before adding a
UI runtime or dependency:

1. inspect the accepted no-listener Python core and available local toolchain;
2. choose one maintained local desktop shell with a webview-class renderer and
   typed command boundary, or record why a materially different shell is
   required;
3. append one focused accepted decision entry to `docs/DECISION_LOG.md` with
   alternatives, rationale, CSP/origin/IPC implications, packaging/license
   uncertainty and review triggers;
4. if the choice contradicts ADR-003 or introduces a localhost/network service,
   create `docs/development/deviations/E02_DESKTOP_BOUNDARY.md` from the
   architecture-deviation template and stop the affected implementation until
   focused review; do not silently proceed.

This checkpoint fills the deferred E02 choice; it does not authorize a network
listener, general filesystem access, renderer-side vault access or real data.

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
3. Configure the selected shell fail closed: restrictive CSP with no remote
   origins, origin validation, no navigation/popups/devtools in the production
   profile, no Node/general process bridge, no arbitrary eval, and no renderer
   file/vault/key access. Pin new direct/transitive dependencies and record
   license/provenance implications.
4. Use text-safe rendering APIs and contextual encoding for every dynamic
   value. Do not render vault-derived strings through raw HTML.
5. Keep operational output content-free. UI diagnostics may expose bounded
   categories and recovery guidance, never secrets, source content, sensitive
   paths or raw exception bodies.
6. Keep all fixtures clearly fictional, repository-owned and synthetic. Do not
   copy data from conversations, local user files or external accounts.

## Failure-driven validation

Add only checks that close named realistic failures. At minimum prove:

1. an unknown/unregistered IPC command, wrong origin, malformed/oversized
   payload, unknown field and stale/sessionless state-changing request are
   rejected before an application operation runs;
2. renderer-visible state, logs, URLs, DOM snapshots and error payloads contain
   no vault path, SQLCipher key, VMK, recovery secret, raw package key or
   synthetic plaintext canary;
3. malicious HTML/Markdown-like strings render as inert text under the actual
   CSP and cannot navigate, execute script or invoke privileged IPC;
4. no renderer command can execute SQL, arbitrary CLI/process arguments,
   general filesystem mutation or a non-allowlisted application action;
5. deletion requires dry-run plus explicit confirmation, displays
   backup/external-copy limits, and never places deleted content/hash in the
   receipt or logs; cancellation and injected failure preserve state;
6. recovery restores to an isolated candidate, reports validation-only as not
   activated, requires a separate explicit activation action, and an injected
   failure preserves the previous active vault;
7. export preview and execution preserve purpose/audience/scope/encryption
   semantics, distinguish export from backup and fail closed on missing policy;
8. loss of network has no effect on unlock, privacy status, deletion, backup,
   recovery or export, and no listener/socket is opened by the production app;
9. keyboard-only traversal, focus return after dialogs, accessible names/error
   association, non-color status and reduced-motion behavior pass on the actual
   bounded UI; and
10. all mandatory Windows desktop/IPC/security tests execute; a newly skipped
    renderer, IPC, deletion, recovery or activation proof is not a pass.

## Validation

During implementation run the smallest affected unit, contract, UI and
integration checks. Run the selected desktop toolchain's pinned build, type,
lint and test commands and record them exactly after the architecture
checkpoint establishes that toolchain. Before reporting completion, run this
accepted repository `FULL` gate once:

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
be skipped.

## Acceptance criteria

- [ ] One explicit desktop-shell decision is recorded and the local production
  shell runs without a listener or remote origin.
- [ ] Renderer and IPC cannot expose keys/paths or invoke untyped, arbitrary or
  non-allowlisted capabilities; actual CSP/origin/XSS/IPC failure tests pass.
- [ ] Synthetic users can unlock/lock, inspect privacy status, correct/delete,
  verify backup health, complete isolated recovery plus separate activation,
  and preview/export with truthful limitations.
- [ ] All state changes traverse typed application services and accepted
  storage/policy/backup paths; direct renderer database/filesystem access is
  absent.
- [ ] The bounded UI passes named keyboard/accessibility/error-recovery tasks
  without manipulative engagement or misleading safety/recovery promises.
- [ ] Accepted E00/E01 tests and validators pass; deferred surfaces remain
  disabled; exact final results and material skips are recorded.
- [ ] `REAL_DATA_GATE` remains `CLOSED`.

## Work and stop rules

Preserve unrelated changes. Do not implement E03, broaden architecture, perform
a general security scan, conduct research, open the real-data gate, commit or
push. A material desktop-boundary conflict requires the focused deviation and
stops only the affected portion. Dependency, CSP, origin, IPC or packaging
uncertainty is not permission to weaken a check or relabel it as PASS.

Create `docs/development/reports/E02.md` from the epic report template. If all
implementation criteria and local evidence pass, set only
`current_epic.status: IMPLEMENTED`; otherwise set `BLOCKED`. Do not accept E02,
append accepted history, prepare E03 or self-award the required independent
Codex review.

End with changed areas, the desktop choice, exact targeted/final results,
skips, residual risks and the focused Codex review required for the new
webview/IPC trust boundary.
