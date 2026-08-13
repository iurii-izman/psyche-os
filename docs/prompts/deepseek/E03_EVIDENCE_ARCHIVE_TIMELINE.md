# PSYCHE OS — EPIC E03: Evidence Archive, Timeline, and Epistemic Explorer

**Project root:** `C:\Dev\psyche-os`
**Accepted E02 implementation commit:** `e8535ffeb74ba7858cbc3eb1aa67fed9634dded1`
**Accepted E02 merge:** `1a4975aa2290a3f63e19e65bf2ec1ebb6c353ccd`
**Canonical branch:** `main`
**Implementation branch:** `codex/e03-evidence-archive`
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
- `docs/development/reports/E03_PREFLIGHT.md`
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

## Frozen preflight decision and implementation contract

The schema verdict is `V2_REQUIRED`. E03 is therefore escalated from the map's
default `RISK-M / EPIC` profile to `RISK-H / FULL` with independent Codex
review. The accepted V1 store cannot represent the authoritative temporal,
evidence-link, multidimensional uncertainty, contradiction, unknown and
personal-model-snapshot semantics without lossy JSON catch-alls or enum
weakening. This is an implementation gap, not authority to redesign the model.

`PersonalModelSnapshot` is a canonical, immutable derived record: a dated
selection of claim versions, contradiction versions, unknown versions and
domain summaries at pinned evidence and knowledge cut-offs. It is not
`KnowledgeSnapshot`, is not a projection, is never updated in place, and must
name its deterministic `DerivationRun`. Timeline and diff screens are
rebuildable views over this canonical record.

Implement exactly one forward, transactional, checksummed V1→V2 migration.
Keep every V1 row and raw legacy claim value unchanged. Rebuild only the five
existing semantic tables listed below to add explicit V2 columns and
conditional semantic-version checks; retain every legacy column for V1 reads.
Add only the listed V2 tables. Do not add E04+ assessment, measurement, AI,
import, search/vector, analytics or cloud schema.

### Existing V1 table delta

| Table | Exact V2 purpose |
| --- | --- |
| `source_artifacts` | Add `semantic_version`, canonical artifact/origin/capture/actor/language/MIME/size/parser/quarantine/policy/rights/correction-relation fields plus the missing version-envelope fields; V1 fields remain readable. |
| `reports` | Add `semantic_version`, report kind, verbatim content/blob locator, reporter, subject, perspective, language, elicitation and source-locator fields plus the version-envelope fields; V1 summary/JSON fields remain legacy-only. |
| `observations` | Add `semantic_version`, observation kind, construct, coded value, context, quality flags and source-locator fields plus the version-envelope fields; V1 raw/JSON fields remain legacy-only. |
| `assertions` | Add `semantic_version`, object value, qualifiers, negation, modality, scope, source locator/source-unavailable reason plus the version-envelope fields; do not use V1 `confidence` for V2 writes. |
| `claims` | Add `semantic_version`, authoritative proposition/wording/scope/window, uncertainty, falsification, review, alternatives, cautions, knowledge-snapshot and version-envelope fields. Conditional checks accept the frozen V1 enums only when `semantic_version=1` and authoritative enums only when `semantic_version=2`. |

### Added V2 tables

| Table | Canonical content |
| --- | --- |
| `source_locators` | Versioned, stable locator identity; artifact record/version FK; locator type/value and extractor/version. |
| `temporal_assertions` | Versioned target/role, value kind, bounds/inclusivity, precision, original literal, timezone known/name, calendar, source/assertion actor, certainty and supersession relation. |
| `evidence_links` | Versioned source-to-claim relation, directness, independence group, scope/time match, strength/rationale, author and derivation. |
| `uncertainty_profiles` | Versioned profile identity and qualified target. |
| `uncertainty_dimensions` | One checked dimension/class/rationale per profile version, with optional named estimand/method/interval; never a generic confidence score. |
| `contradiction_sets` | Versioned conflict type/scope/time and checked resolution/rationale. |
| `contradiction_members` | Set-version to assertion/claim-version membership with member role. |
| `unknowns` | Versioned question/scope/materiality/state/attempts/reducing evidence/burden/status and checked missingness reason. |
| `personal_model_snapshots` | Immutable snapshot/version, evidence transaction cut-off, domain-time scope, knowledge snapshot, previous snapshot, change summary, review state and required derivation. |
| `personal_model_snapshot_claims` | Snapshot-to-claim-version inclusion and reason. |
| `personal_model_snapshot_contradictions` | Snapshot-to-contradiction-version inclusion and unresolved state. |
| `personal_model_snapshot_unknowns` | Snapshot-to-unknown-version inclusion. |
| `personal_model_snapshot_domain_summaries` | Bounded domain ID, derived summary and source member set for a snapshot. |
| `personal_model_snapshot_algorithms` | Exact algorithm ID/version/config digest used by a snapshot. |
| `record_relations` | Typed correction, replacement, provenance and dependency edges for cross-aggregate closure where a direct FK cannot express the relation. |

The exact columns added to the rebuilt tables are:

- all five: `semantic_version`, `schema_version`, `change_reason_code`,
  `created_by_actor_id`; retain and use V1 `record_id`, `version_id`,
  `tx_from`, `tx_to`, `is_active`, `previous_version_id` and every other V1
  column unchanged as the canonical storage envelope; add `derivation_id` only
  to `source_artifacts` and `reports`, because the other three already have it;
- `source_artifacts`: `artifact_kind`, `origin_kind`, `captured_at`,
  `source_actor_id`, `language_tags`, `original_filename_encrypted`,
  `declared_mime_type`, `observed_mime_type`, `byte_size`, `parser_state`,
  `quarantine_state`, `policy_id`, `rights_note`, `replaces_artifact_id`,
  `corrected_copy_of_artifact_id`;
- `reports`: `report_kind`, `verbatim_content`, `verbatim_blob_id`,
  `reporter_actor_id`, `subject_record_id`, `perspective`, `language_tag`,
  `elicitation_method`, `source_locator_record_id`,
  `source_locator_version_id`;
- `observations`: `observation_kind`, `observer_actor_id`,
  `subject_record_id`, `construct_phenomenon`, `value_or_coded_state`,
  `context`, `quality_flags`, `source_locator_record_id`,
  `source_locator_version_id`;
- `assertions`: `object_value`, `qualifiers`, `negation`, `modality`, `scope`,
  `source_locator_record_id`, `source_locator_version_id`,
  `source_unavailable_reason`;
- `claims`: `proposition`, `bounded_wording`, `population_scope`,
  `window_context`, `uncertainty_profile_record_id`,
  `uncertainty_profile_version_id`, `falsification_criteria`,
  `review_trigger`, `alternatives`, `counterfactual_cautions`,
  `knowledge_snapshot_id`.

Typed list columns above (`language_tags`, `quality_flags`, `qualifiers`) use a
versioned JSON-array schema and reject objects/scalars/unknown members; they are
not catch-all objects. For V2 rows, `is_active` must equal (`tx_to IS NULL`).
V1 rows receive only deterministic envelope defaults and retain every
content/enum value unchanged.

The exact added-table column and constraint contract is:

| Table | Columns beyond the common envelope / owned identity | Required relations, checks and deletion behavior |
| --- | --- | --- |
| `source_locators` | `artifact_record_id`, `artifact_version_id`, `locator_type`, `locator_value`, `extractor_name`, `extractor_version` | Composite FK to `source_artifacts`; checked locator type; delete with artifact; index artifact record/version. |
| `temporal_assertions` | `target_record_id`, `target_version_id`, `temporal_role`, `value_kind`, `lower_value`, `upper_value`, `lower_inclusive`, `upper_inclusive`, `precision`, `original_literal`, `timezone_known`, `timezone_name`, `calendar`, `source_actor_id`, `assertion_actor_id`, `certainty_class`, `certainty_rationale`, `superseded_temporal_version_id` | Checked roles/kinds/precision/certainty and bound/inclusivity/timezone rules; target and supersession edges in `record_relations`; delete with exclusive target, invalidate when shared; target/role index. |
| `evidence_links` | `source_record_id`, `source_version_id`, `target_claim_record_id`, `target_claim_version_id`, `relation`, `directness`, `source_independence_group`, `scope_match`, `temporal_match`, `strength_class`, `rationale`, `author_actor_id`, `link_derivation_id` | Composite FK to target claim; checked relation/directness/match/strength; source edge in `record_relations`; delete on source/target deletion; target and source indexes. |
| `uncertainty_profiles` | `target_record_id`, `target_version_id`, `target_kind` | Checked E03 target kind and target relation; delete with qualified target; target index. |
| `uncertainty_dimensions` | `profile_record_id`, `profile_version_id`, `dimension`, `class`, `rationale`, `interval_lower`, `interval_upper`, `estimand`, `method` | PK `(profile_record_id, profile_version_id, dimension)` and composite FK to profile; checked ten dimensions/classes; interval requires estimand/method and valid bounds; cascade with profile. |
| `contradiction_sets` | `conflict_type`, `scope`, `time_context`, `resolution_status`, `resolution_rationale` | Checked conflict/resolution enums; active uniqueness; remove when empty; active-resolution index only. |
| `contradiction_members` | `set_record_id`, `set_version_id`, `member_kind`, `member_record_id`, `member_version_id`, `member_role` | PK across set version/member; composite FK to set; checked assertion/claim kind; member edge in `record_relations`; cascade from set, recompute/remove on member deletion; member index. |
| `unknowns` | `question`, `scope`, `why_matters`, `knowledge_state`, `attempts`, `what_could_reduce`, `burden_or_safety_concern`, `status`, `unknown_reason` | Checked status and authoritative missingness reason; active uniqueness; closure follows snapshot/relation edges. |
| `personal_model_snapshots` | `evidence_transaction_cutoff`, `domain_time_lower`, `domain_time_upper`, `domain_time_precision`, `knowledge_snapshot_id`, `previous_snapshot_record_id`, `previous_snapshot_version_id`, `change_summary`, `user_review_status`, `generation_derivation_id` | Insert-only immutable row; required derivation and valid cut-offs; previous-snapshot composite FK; delete if any included deleted input is reconstructive; previous/derivation indexes. |
| `personal_model_snapshot_claims` | `snapshot_record_id`, `snapshot_version_id`, `claim_record_id`, `claim_version_id`, `inclusion_reason`, `change_class` | Composite FKs to snapshot and claim; checked change class; cascade from snapshot; delete snapshot on claim erasure; claim index. |
| `personal_model_snapshot_contradictions` | `snapshot_record_id`, `snapshot_version_id`, `contradiction_record_id`, `contradiction_version_id`, `unresolved_at_cutoff` | Composite FKs to snapshot/set; cascade from snapshot; delete snapshot on member erasure; contradiction index. |
| `personal_model_snapshot_unknowns` | `snapshot_record_id`, `snapshot_version_id`, `unknown_record_id`, `unknown_version_id` | Composite FKs to snapshot/unknown; cascade from snapshot; delete snapshot on unknown erasure; unknown index. |
| `personal_model_snapshot_domain_summaries` | `summary_id`, `snapshot_record_id`, `snapshot_version_id`, `domain_id`, `summary_text` | Unique snapshot/domain; FK to snapshot; source dependencies in `record_relations`; cascade from snapshot and delete with reconstructive source; domain index. |
| `personal_model_snapshot_algorithms` | `snapshot_record_id`, `snapshot_version_id`, `algorithm_id`, `algorithm_version`, `config_digest` | Unique snapshot/algorithm; FK to snapshot; non-empty version/digest; cascade from snapshot. |
| `record_relations` | `relation_id`, `parent_record_id`, `parent_version_id`, `child_record_id`, `child_version_id`, `relation_kind`, `derivation_id`, `created_at` | Immutable unique typed edge; checked relation kinds (`anchors`, `targets`, `supports`, `contradicts`, `qualifies`, `derived_from`, `replaces`, `corrects`, `snapshot_includes`, `summary_uses`); endpoint existence validated transactionally; delete with either endpoint; parent/child indexes. |

The common version envelope for `source_locators`, `temporal_assertions`,
`evidence_links`, `uncertainty_profiles`, `contradiction_sets`, `unknowns` and
`personal_model_snapshots` is `record_id`, globally unique `version_id`,
`schema_version`, `tx_from`, nullable `tx_to`, `is_active`,
`change_reason_code`, nullable `previous_version_id`, `created_by_actor_id`,
nullable `derivation_id`; each has a partial unique index on active `record_id`,
an `is_active = (tx_to IS NULL)` check and transaction non-overlap validation.
Owned membership/dimension/algorithm rows inherit transaction meaning from the
immutable parent version. Add no indexes beyond those named above and the PK,
unique, FK and active-version indexes needed for correctness.

The exact V1 inventory remains the accepted 20-table set. The exact V2
inventory is that unchanged set plus the fifteen added tables above. Backup,
verify, restore, logical export, deletion verification and semantic-state
capture must select the exact inventory by schema version; missing, extra or
duplicate entries fail. V1 packages remain verifiable/restorable by the V1
reader. V2 packages and exports declare schema/format versions and exact
per-table schemas/checksums. Never mutate V1 inventory expectations.

The migration requires a verified V1 backup and open export, exact V1 schema
and V1 checksum, integrity/FK success and no pending deletion or migration. It
runs under one `BEGIN IMMEDIATE`, validates row counts/digests, version
intervals, enum preservation, provenance/deletion closure and exact V2
inventory before commit, and fails closed on checksum mismatch, missing/extra
tables, out-of-domain malformed legacy values, dangling links, invalid
intervals, constraint failure or injected interruption. Accepted but ambiguous
legacy values are tagged and preserved, not rejected. Rerun after success is a
verified no-op. No reverse migration is claimed: rollback means retaining/
restoring the verified pre-migration V1 vault/backup. V1 history is never
rewritten.

Legacy claim compatibility is explicit. `descriptive`, `proposed`,
`superseded` map identically. V1 `causal` and `predictive` may be displayed as
suggested `causal_hypothesis` and `prediction` only after typed review; they are
not auto-converted. Every other V1 type/status is ambiguous; every V1 origin is
ambiguous. Readers expose these as namespaced legacy values, and backup,
restore and export round-trip the raw strings. Only authoritative domain enum
values are writable for `semantic_version=2`.

Deletion closure traverses direct FKs, derivation I/O, policy lineage,
`record_relations`, evidence, uncertainty, contradiction and every snapshot
membership/summary/algorithm dependency. Exclusive descendants are removed;
mixed non-reconstructive derived records are invalidated; any snapshot or
summary that materially reconstructs a deleted input is removed. Receipts
remain content-free and post-delete V2 canonical, raw, rebuilt-view and export
absence is mandatory.

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
- E04 rights-gated assessments, instruments and scoring; LLM/provider code,
  generated interpretation or model proposals.
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

1. Begin from current `main` on `codex/e03-evidence-archive`. Inspect the
   clean worktree and applicable nested `AGENTS.md` before editing.
2. Define command-specific request/response types and application use cases;
   do not expose table names, generic CRUD, SQL, Python dispatch or arbitrary
   record bodies to the renderer.
3. Implement the smallest production adapters needed for canonical E03
   records. Validate table/entity allowlists, enum domains, identifiers,
   temporal bounds, provenance edges and unknown fields before mutation.
4. Keep the private synthetic fixture authority non-self-issuable. Extend it
   only with the repository-owned `e03_orchid_station_v1` pack and the eight
   fixed typed scenario operations/choices frozen in `E03_PREFLIGHT.md`; do not
   create a public token, arbitrary fixture path or user-content bypass.
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

The required V2 migration must also prove synthetic V1→V2 migration, checksum
and explicit preconditions, verified no-op rerun/fail-closed behavior, retained
V1 restore rollback, V1 backup readability, V2 backup/restore/export round trip,
exact version-selected inventories, raw legacy enum preservation, injected
mid-migration rollback, missing/extra-table rejection, dangling-link rejection,
invalid-interval rejection and projection/view rebuild. No migration, E01/E02,
desktop or deletion proof may be skipped.

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
`codex/e03-evidence-archive`, and one draft PR against `main` after meaningful
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
