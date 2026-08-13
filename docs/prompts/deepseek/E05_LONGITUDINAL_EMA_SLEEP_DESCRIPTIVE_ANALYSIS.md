# PSYCHE OS — EPIC E05: Longitudinal, EMA, Sleep, and Descriptive Analysis

**Project root:** `C:\Dev\psyche-os`
**Accepted E04 implementation commit:** `9197441a43c79a8c1905bdd7547f00073c76ece4`
**Accepted E04 merge:** `10030be3b1b13e72f047fa07878d9c2a6ac089b6`
**Canonical branch:** `main`
**Implementation branch:** `codex/e05-longitudinal-ema-sleep-analysis`
**Risk:** `RISK-M`
**Expected final gate:** `EPIC`
**Data:** repository-owned fictional synthetic protocols and observations only
**REAL_DATA_GATE:** `CLOSED`

## Role and outcome

Deliver one bounded outcome: add a typed synthetic-only longitudinal vertical
slice that records user-approved sampling/burden semantics, keeps sleep and
context source types distinct, and produces deterministic descriptive summaries
with explicit window, coverage, missingness, reactivity and version boundaries.

E04 assessment content, responses and scoring remain blocked. E05 is not an
assessment administration path and must not use the blocked E04 registry to
collect real or fictional questionnaire answers.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/implementation/E04_ACCEPTANCE_REPORT.md`

Then read only these directly relevant sources and sections:

- `docs/development/EPIC_MAP.md` — E05 only
- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §§11–14.2 and §22.1 only
- `docs/architecture/DATA_MODEL.md` — §§4.7 and 9 only
- `docs/SCIENTIFIC_GOVERNANCE.md` — §§3, 7.3 and 8 only
- `docs/DECISION_LOG.md` — ADR-013 only
- `ontology/psyche_domains.yaml` — `sleep.sleep_circadian`,
  `longitudinal.ema_context`, `sensing.device_observation` and their direct relations only
- `src/psyche_os/domain/entities.py` — measurement/temporal/derivation types only
- `src/psyche_os/storage/schema.py`, `src/psyche_os/storage/e03_schema.py`,
  `src/psyche_os/storage/migrations.py`, and `src/psyche_os/backup_export/versioned.py`
  — accepted V2 migration/portability boundary only
- `src/psyche_os/application/e03_archive.py` — accepted typed fixture/service pattern only

Inspect additional files only when directly imported by a touched path. Do not
load historical v1 documents, the research dossier/source registry, broad
threat/safety documents, prior repair prompts, or E06+ scope.

## Frozen entry decision

Implement one small canonical V2-to-V3 migration only if needed for the exact
longitudinal records below. It must preserve the accepted V1/V2 inventories,
E03 migration checksum, logical portability, deletion semantics and explicit
version selection. Do not retrofit longitudinal payloads into opaque JSON or
rewrite accepted E03 rows.

The only writable data is a package-owned fictional scenario with fixed typed
operations. `REAL_DATA_GATE` is closed: no arbitrary diary, EMA, sleep, device,
substance, medication, illness, location or life-event text may enter through
CLI, renderer, IPC, filesystem, environment or database APIs.

Keep `RISK-M / EPIC`. If satisfying the scope requires ambient/passive sensing,
real participant input, a clinical or causal decision, an external service, or
a destructive/unrecoverable migration, stop that portion and report the exact
escalation trigger.

## In scope

- Immutable/versioned `SamplingProtocol` metadata: stable ID/version,
  construct, schedule type, randomized window if applicable, prompt/burden
  ceilings, duration, pause/stop rules, context fields, allowed missingness
  reasons, feedback policy, timezone/travel behavior, review trigger and
  explicit fictional user-approval state.
- Fixed fictional sampling events that preserve scheduled/window/actual time,
  protocol version, exposure, feedback exposure, context state and one exact
  missingness value: `observed`, `deliberate_skip`, `declined`,
  `technical_failure`, `unavailable_context`, or `not_applicable`.
- Source-distinct sleep records: `subjective_diary`, `actigraphy`,
  `consumer_wearable`, `clinical_test`, and `derived_or_inferred`. Device/model,
  firmware and algorithm epoch are mandatory for device-derived data; unknown
  proprietary logic is labelled `black_box_estimate`.
- Typed non-diagnostic `ConfoundContext` records for only the fixed fictional
  fixture categories needed by tests, preserving source, time, uncertainty and
  version without medication advice or medical inference.
- Deterministic descriptive output over an explicit window: eligible/observed
  counts, coverage denominator and ratio, every missingness count, protocol and
  algorithm versions, source-type composition, feedback exposure/reactivity
  caution, and bounded C0–C2 wording. A C3 association may be emitted only if a
  prespecified synthetic known-answer analysis proves the accepted serial,
  missingness and replication requirements; otherwise keep C3 disabled.
- One package-owned fictional scenario and narrow named application/desktop
  commands only if the existing desktop surface is extended. Preserve the E02/E03
  typed IPC authority; renderer choices must be fixed enums/presets rather than
  arbitrary content.
- Focused unit/integration tests and, only when UI is changed, renderer/native
  desktop tests for the exact E05 surface.

## Out of scope

- Actual assessment administration, protected item content, responses, E04
  rights changes, assessment scoring, norms, cutoffs or screening.
- Real diary/EMA/sleep/device/substance/medication/illness/location/life-event
  data, free-text capture, arbitrary import or user-configurable raw payloads.
- Passive or ambient surveillance, microphone, keystroke, message, contact,
  location, face/voice emotion or background sensor collection.
- Sleep-stage/disorder diagnosis, medication/supplement advice, aggressive sleep
  restriction, medical verdict, treatment selection or safety monitoring claim.
- Causal claims, intervention execution, N-of-1 experiments, predictions,
  trait inference, adaptive sampling/battery, engagement streaks or adherence shaming.
- Cloud/network/provider work, generic CRUD/SQL/filesystem/Python dispatch,
  unrelated refactoring, speculative abstractions or E06+ scaffolding.

## Invariants to protect

- C-05–C-08: description is not diagnosis or causation; source limits,
  uncertainty, gaps and alternatives stay explicit.
- C-11–C-12: no new disclosure/network path; fixed synthetic data remains local
  and minimally exposed.
- C-17–C-18: no monitoring/rescue promise, clinical authority, hidden sensing or
  version-free measurement interpretation.
- C-20: only package-owned fictional fixtures; `REAL_DATA_GATE` remains closed.
- E03's accepted V1/V2 histories, checksums, portability, dependency deletion
  and desktop authority remain unchanged. E04 stays metadata-only/rights-blocked.

## Implementation requirements

1. Inspect the worktree, branch, accepted interfaces and nested `AGENTS.md`
   before editing. Develop only on the configured E05 candidate branch.
2. Model protocol, event, sleep source, confound and summary states with closed
   enums/value types. Reject unknown/extra/malformed fields before mutation.
3. Keep version changes explicit. Do not compare or aggregate across protocol,
   measurement, device, firmware or algorithm epochs unless the output reports
   the boundary and an explicit comparability decision permits it.
4. Coverage denominators must derive from the named schedule/window and preserve
   deliberate skip, decline, technical failure, unavailable context and not
   applicable separately. No LOCF, silent imputation or complete-case default.
5. Event-contingent observations cannot estimate event frequency without an
   explicit missed-opportunity model; this epic supplies none, so block that claim.
6. Feedback/protocol exposure must produce a visible reactivity caution. Missing
   records must never produce `noncompliant`, shame, overdue, streak or urgency language.
7. Sleep source types never collapse. Consumer/device estimates cannot become
   clinical truth; inferred/black-box values cannot masquerade as direct observation.
8. Descriptive outputs are derived proposals with exact inputs, method/version,
   window, coverage and limitations. No LLM participates in analysis or policy.
9. If V3 persistence is added, make one checksummed forward migration with exact
   inventory, interruption rollback, verified V2 prerequisite, versioned logical
   portability, dependency deletion and synthetic old-version proof. No reverse
   migration claim; rollback is retained verified V2 restore/activation.
10. Keep logs/audit content-free. Never log fixture content, free text, device
    identifiers, substance/medication details, locations, paths, raw exceptions
    or stable content hashes.

## Failure-driven validation

Every new check must name one realistic failure. At minimum prove equivalents of:

- protocol without burden ceiling, pause/stop, timezone/travel, missingness or
  review semantics fails before mutation;
- schedule/window mismatch and out-of-window events fail;
- decline, deliberate skip, technical failure, unavailable context and not
  applicable remain distinct and denominator handling is deterministic;
- long gaps produce no interpolation, shame or adherence judgment;
- feedback exposure adds a reactivity caution;
- event-contingent data cannot claim event frequency;
- diary, actigraphy, consumer, clinical and inferred sleep sources remain distinct;
- device estimates without device/model/firmware/algorithm epoch fail, and
  black-box estimates are labelled;
- version/algorithm drift blocks silent series comparison;
- absent coverage or scientific conditions blocks C3, causal, clinical,
  diagnostic, treatment and prediction wording;
- user/model/imported text cannot alter protocols, gates, analysis policy or
  named command authority;
- if V3 exists: exact migration inventory/checksum, interruption rollback,
  V1/V2 compatibility, portability and dependency deletion remain green.

Create focused tests at:

- `tests/unit/test_e05_longitudinal_analysis.py`
- `tests/integration/test_e05_longitudinal_analysis.py`
- `tests/integration/test_e05_migration.py` only if V3 persistence is introduced

## Validation

Run the smallest affected tests while iterating. When the exact E05 criteria are
ready, run this final `EPIC` gate once:

```powershell
uv sync --frozen
uv run pytest -q tests/unit/test_e05_longitudinal_analysis.py tests/integration/test_e05_longitudinal_analysis.py tests/integration/test_e03_migration.py tests/integration/test_e03_canonical_archive.py
uv run pytest -q
uv run python scripts/validate_f0_scope.py
python scripts/dev/validate_orchestration.py
```

If `tests/integration/test_e05_migration.py` exists, add it to the first pytest
command. If desktop code changes, also run the accepted repository commands:

```powershell
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

Record exact pass/fail/skip counts. No mandatory E05, migration, E03 or typed
authority proof may skip. The unchanged administrator-only general
`FilesystemAdapter` symlink skip may remain if identical and unrelated.

## Acceptance criteria

- [ ] Protocol, burden, pause/stop, missingness, feedback/reactivity, timezone
  and review semantics are explicit, typed and versioned.
- [ ] Fictional longitudinal events preserve actual windows and all named
  missingness states without imputation or adherence judgment.
- [ ] Sleep diary, device, clinical and inferred records remain source-specific;
  device/algorithm epochs and black-box limits are visible.
- [ ] Descriptive output reports window, denominator, coverage, missingness,
  reactivity, source and version boundaries with no unsupported C3+, causal,
  clinical, diagnostic or treatment language.
- [ ] No arbitrary/real data path, passive surveillance, assessment use,
  network/provider capability or generic dispatch is added.
- [ ] Any V3 migration is checksummed, atomic, portable, deletion-aware and
  preserves accepted V1/V2 histories and E03 behavior.
- [ ] Targeted and final validation results are recorded exactly.
- [ ] `REAL_DATA_GATE` remains `CLOSED`.

## Git, report and stop rules

This prompt authorizes coherent E05 candidate commits, pushing only the E05
candidate branch, and one draft PR against `main` after meaningful validated
implementation exists. Candidate publication is not acceptance.

Create `docs/development/reports/E05.md` from
`docs/development/EPIC_REPORT_TEMPLATE.md`. If every implementation criterion
and local gate passes, set only `current_epic.status: IMPLEMENTED` and
`implementation_status: IMPLEMENTED`; otherwise record the blocked state
truthfully. Do not set `ACCEPTED`, append accepted history, advance E06, merge,
open the real-data gate or implement later epics.

Stop the affected portion for real data, surveillance, clinical/causal scope,
unbounded capture, destructive migration, source-of-truth conflict or a new
external trust boundary. Do not weaken a gate to continue. End with changed
areas, exact validation/skips, limitations and the recommended next state.
