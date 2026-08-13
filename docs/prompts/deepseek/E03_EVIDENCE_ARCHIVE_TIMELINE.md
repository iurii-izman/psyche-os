# PSYCHE OS — EPIC E03: Evidence Archive, Timeline, and Epistemic Explorer

**Project root:** `C:\Dev\psyche-os`
**Accepted E02 implementation commit:** `e8535ffeb74ba7858cbc3eb1aa67fed9634dded1`
**Accepted E02 merge:** `1a4975aa2290a3f63e19e65bf2ec1ebb6c353ccd`
**Canonical branch:** `main`
**Implementation branch:** `deepseek/e03-evidence-archive`
**Risk:** `RISK-H`
**Expected final gate:** `FULL`
**Data:** repository-owned fictional synthetic fixtures only
**REAL_DATA_GATE:** `CLOSED`

## Role and outcome

Deliver one bounded outcome: a canonical synthetic evidence archive and desktop
explorer that lets a user capture from a closed fictional scenario vocabulary,
navigate explicitly selected fuzzy clocks, and distinguish source-near records,
claims, uncertainty, contradictions, unknowns and snapshot changes. Correction
and dependency-aware deletion must now use canonical synthetic storage rather
than E02's explicitly session-only demonstration state.

Do not expand this epic into arbitrary free-text or file ingestion, AI/model
interpretation, measurements, cloud/network, real data, or later epic work.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/implementation/E02_ACCEPTANCE_REPORT.md`
- `docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md`

Then read only these directly relevant sources and sections:

- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §§6, 8–9, 19 and 21
- `docs/architecture/DATA_MODEL.md` — §§2–7 and 12–16
- `docs/architecture/SYSTEM_ARCHITECTURE.md` — §§5, 7, 8.1, 8.4–8.5,
  11–13 and 15
- `docs/DECISION_LOG.md` — ADR-002, ADR-004, ADR-005, ADR-009 and ADR-018
- `docs/development/EPIC_MAP.md` — E03 only
- `src/psyche_os/application/ports.py` — `RecordPort`, `DeletionPort` and
  synthetic fixture authority only
- `src/psyche_os/domain/entities.py` — source/evidence, temporal, claim,
  uncertainty, contradiction, unknown, snapshot and deletion entities only
- `src/psyche_os/storage/schema.py`
- `src/psyche_os/storage/migrations.py`
- `src/psyche_os/storage/uow.py`
- `src/psyche_os/fixtures/__init__.py` and the bundled fixture manifest shape
- `src/psyche_os/backup_export/operations.py` — schema inventory, deletion and
  canonical validation paths only
- `src/psyche_os/application/desktop_service.py`
- `src/psyche_os/interfaces/desktop_sidecar.py`
- `desktop/src-tauri/src/lib.rs`
- `desktop/src-tauri/capabilities/main-local.json`
- `desktop/src/api.ts`, `desktop/src/main.ts`, and `desktop/src/styles.css`

Inspect additional files only when directly imported by a touched path. Do not
load historical v1 documentation, the research corpus, broad threat/safety
documents, prior repair prompts or E04+ scope.

## Preparation finding and frozen interpretation

E03 is escalated from the map's default `RISK-M / EPIC` profile to
`RISK-H / FULL` with independent Codex review because the accepted V1 store has
an exact 20-table profile and legacy claim values, while the authoritative
entities required by E03 include richer temporal, evidence-link, uncertainty,
contradiction, unknown and model-snapshot semantics. This is an implementation
gap, not authority to rewrite the data model.

- Preserve V1 DDL and accepted E00/E01 readers and evidence unchanged.
- If canonical E03 persistence needs new tables or corrected enums, add one
  forward, checksummed V2 migration with a synthetic V1 fixture, validation,
  rollback/restore strategy, projection rebuild and deletion impact.
- Extend version-aware backup/export/restore inventory only as required for the
  new V2 profile while keeping the accepted V1 profile readable and testable.
- Do not silently encode authoritative entities into unrelated JSON columns to
  avoid a migration.
- If satisfying the authoritative model would require rewriting V1 history,
  weakening E01 exact restore/inventory guarantees, or inventing a conflicting
  canonical model, stop that portion and create an architecture deviation.

## In scope

- A typed application-service layer over production `RecordPort` and
  `DeletionPort` adapters for the E03 canonical entities.
- A private package-owned E03 fictional scenario pack and closed typed capture
  choices. The renderer may choose bounded fictional IDs/enum values but must
  not persist arbitrary user text, host files, paths or imported content while
  `REAL_DATA_GATE` is closed.
- Canonical source-near capture/inbox using `SourceArtifact` without enabling
  blob/file mutation, plus `Report`, `Observation`, `Assertion` and explicit
  provenance/source locators supported by the accepted schema boundary.
- Explicit `TemporalAssertion` clocks and fuzzy/unknown interval view models;
  timeline sorting must select a temporal role and show precision/uncertainty.
- Evidence, claim, contradiction and unknown explorers that preserve source /
  normalized / derived separation and never label a proposal as fact.
- Deterministic `PersonalModelSnapshot` fixture views and immutable snapshot
  diff; do not generate snapshots with AI.
- Canonical correction/history and dependency-aware deletion dry-run,
  confirmation, limitation-aware content-free receipt and post-delete absence.
- Narrow named Tauri/Python commands and text-safe accessible renderer views
  for these workflows, reusing the accepted E02 boundary.
- Synthetic task tests for first use and return after months with no streak,
  shame, urgency, completion score, variable reward or engagement pressure.

## Out of scope

- Arbitrary free-text capture, filesystem browsing, blobs/attachments, OCR,
  import parsers or real account/device data.
- E04 chat/composition, LLM/provider code, generated interpretation or model
  proposals.
- Diagnosis, causal inference, recommendations, measurements/instruments,
  experiments, analytics, graph/vector/search engines or clinician mode.
- Network/cloud, telemetry, sync/sharing, updater/signing or release work.
- Redesign of E00/E01 crypto, recovery, backup format or atomic activation.
- Real personal or sensitive data while `REAL_DATA_GATE = CLOSED`.

## Invariants to protect

- C-01–C-04, C-08–C-09, C-14, C-17 and C-20.
- Verbatim/source-near, normalized and derived records remain distinct; LLM or
  deterministic output never becomes evidence merely by being stored.
- Occurred, observed, reported, recorded and asserted time remain distinct;
  fuzzy or unknown time is never fabricated into an instant.
- Correction creates a version and preserves deliberate history; active views
  show material conflicts and unknowns.
- Deletion is a dependency operation over canonical rows and rebuildable
  projections. Receipts contain no deleted content or reconstructive hash and
  state backup/external-copy limitations.
- The renderer remains an untrusted presentation adapter with only named E03
  commands and bounded view models. It receives no path, key, SQL, generic
  dispatch, raw exception or storage/process handle.
- No listener, remote origin, general filesystem capability or cloud/provider
  dependency is introduced.
- V1 and accepted E01 backup/recovery evidence must remain green.

## Implementation requirements

1. Begin from current `main` on `deepseek/e03-evidence-archive`. Inspect the
   clean worktree and applicable nested `AGENTS.md` before editing.
2. Define command-specific request/response types and application use cases;
   do not expose table names, generic CRUD, SQL, Python dispatch or arbitrary
   record bodies to the renderer.
3. Implement the smallest production adapters needed for canonical E03
   records. Validate table/entity allowlists, enum domains, identifiers,
   temporal bounds, provenance edges and unknown fields before mutation.
4. Keep the private synthetic fixture authority non-self-issuable. Extend it
   only with a repository-owned E03 pack and fixed typed scenario operations;
   do not create a public token, arbitrary fixture path or user-content bypass.
5. Preserve optimistic/current-version semantics: correction must reject a
   stale base version and atomically close the prior transaction interval
   before inserting the successor.
6. Build timeline/explorer view models in Python from canonical records. The
   Rust shell validates authority and framing but does not implement domain,
   storage, temporal, correction or deletion rules.
7. Extend the existing Tauri capability only with individually named E03
   commands. Keep `core:*` absent and preserve CSP, origin, navigation, popup,
   devtools, offline and content-free error controls.
8. Render every dynamic string through `textContent`/text nodes. Preserve
   keyboard traversal, focus return, labels, associated errors, non-color
   status and reduced-motion behavior.
9. Preserve unrelated changes and reuse accepted utilities before adding a
   dependency. Record any dependency/license change in `docs/development/reports/E03.md`.

## Failure-driven validation

Every new check must name the realistic failure it closes and cite one target
from E03-T1 through E03-T7. Do not add an arbitrary coverage threshold.

- **E03-T1 — canonical synthetic capture:** prove only the private packaged E03
  scenario authority can create canonical source-near records; arbitrary text,
  paths, tables, unknown fields and forged authority fail before write; source,
  report, assertion and derived claim remain distinguishable.
- **E03-T2 — temporal semantics:** property-test exact, interval, fuzzy/calendar
  and unknown values; invalid bounds fail; timeline clock selection is explicit
  and summer/year precision is not converted to a fabricated day.
- **E03-T3 — epistemic explorer:** prove evidence relations, uncertainty axes,
  contradiction membership/status and unknown reasons survive round trip and
  views expose alternatives/conflicts without a generic truth/confidence score.
- **E03-T4 — snapshot diff:** prove immutable deterministic fixture snapshots
  show added/changed/removed claims and unresolved conflicts without completion
  percentage, generated interpretation or source/derived conflation.
- **E03-T5 — correction:** prove canonical history, stale-version rejection,
  atomic active-version uniqueness, explicit reason and deliberate history
  visibility through the real desktop command path.
- **E03-T6 — deletion:** prove dry-run closure across canonical dependencies,
  exact confirmation, cancellation/fault preservation, content-free receipt,
  projection rebuild and post-delete canonical/export absence while limitations
  remain visible.
- **E03-T7 — bounded desktop UX:** prove real renderer text safety, keyboard and
  focus behavior, labels/errors/non-color/reduced motion, months-away return
  without engagement pressure, offline operation and no new listener/authority.

If a V2 migration is added, also prove synthetic V1→V2 migration, checksum and
preconditions, idempotence/fail-closed behavior, rollback/restore plan,
V1 backup readability, V2 backup/restore/export round trip and exact inventory.
No migration, E01/E02, desktop or deletion proof may be skipped.

## Validation

Run the smallest affected unit/property/integration/renderer checks while
iterating. The final targeted desktop/toolchain gate is:

```powershell
uv sync --frozen
uv run pytest -q tests/unit/test_e03_archive_service.py tests/integration/test_e03_canonical_archive.py tests/integration/test_e03_migration.py
npm --prefix desktop ci
npm --prefix desktop run typecheck
npm --prefix desktop run lint
npm --prefix desktop run test:unit
cargo fmt --check --manifest-path desktop/src-tauri/Cargo.toml
cargo clippy --manifest-path desktop/src-tauri/Cargo.toml --all-targets --locked -- -D warnings
cargo test --manifest-path desktop/src-tauri/Cargo.toml --locked
npm --prefix desktop run test:desktop
npm --prefix desktop run build
npm --prefix desktop run tauri:build -- --debug
```

After E03-T1 through E03-T7 are ready, run this authoritative `FULL` gate once:

```powershell
uv sync --frozen
uv run pytest -q
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python scripts/validate_e01_assurance.py
python scripts/dev/validate_orchestration.py
```

The unchanged accepted Windows administrator-only general symlink skip may
remain if still identical and unrelated. No mandatory E01/E02/E03 proof may
skip. If implementation changes after the FULL gate, it is no longer final.

## Acceptance criteria

### E03-T1 — Canonical synthetic capture

- [ ] A closed fictional scenario flow creates canonical source-near records
  through typed application/storage ports without admitting arbitrary content.

### E03-T2 — Fuzzy and multi-clock time

- [ ] Timeline views select the clock explicitly and preserve bounds,
  precision, uncertainty and unknown time without invented precision.

### E03-T3 — Evidence, claims, contradictions and unknowns

- [ ] Representative synthetic records preserve provenance and distinct
  epistemic types; proposals are never displayed as evidence or fact.

### E03-T4 — Snapshot change

- [ ] Deterministic fixture snapshot diff shows changes and unresolved conflict
  without identity/completion claims or AI generation.

### E03-T5 — Canonical correction

- [ ] Correction executes against canonical synthetic storage, rejects stale
  state and preserves deliberate version history.

### E03-T6 — Dependency-aware deletion

- [ ] Dry-run, confirmation, failure preservation, deletion closure,
  content-free receipt, rebuild and absence verification pass.

### E03-T7 — Accessible offline UX

- [ ] The packaged bounded UI passes text-safety, keyboard/focus, accessible
  naming/error, non-color, reduced-motion, months-away-return and offline proof.

- [ ] Targeted/toolchain and final FULL results are recorded exactly.
- [ ] E00–E02 accepted invariants remain green and deferred surfaces remain deferred.
- [ ] `REAL_DATA_GATE` remains `CLOSED`.

## Git and review workflow

This prompt authorizes coherent E03 candidate commits, pushing only
`deepseek/e03-evidence-archive`, and one draft PR against `main` after meaningful
validated implementation exists. Candidate publication is not acceptance.

Do not merge, push implementation to `main`, force-push, rewrite accepted
history, mark E03 `ACCEPTED`, append it to `accepted_epics`, prepare E04 or open
the real-data gate. Independent bounded Codex review of the migration,
canonical epistemic semantics, deletion and expanded IPC/UI path is required.

## Final report and stop rules

Create `docs/development/reports/E03.md` from the epic report template. If every
criterion and local gate passes, set only `current_epic.status: IMPLEMENTED` and
`implementation_status: IMPLEMENTED`; otherwise set the blocked state
truthfully. Do not self-award acceptance.

Stop when E03-T1 through E03-T7 pass. Do not implement E04, AI/chat, imports,
measurements, analytics, cloud/network, arbitrary capture or real data. End
with changed areas, exact migrations, validation/skips, limitations and the
focused Codex review required.
