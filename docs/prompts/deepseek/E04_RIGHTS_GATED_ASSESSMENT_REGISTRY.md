# PSYCHE OS — EPIC E04: Rights-Gated Assessment Registry

**Project root:** `C:\Dev\psyche-os`
**Accepted E03 implementation commit:** `6721e0b00a82f808405c17ab67358ad2f51199bc`
**Accepted E03 merge:** `6bb303ced1f7e6e650941a020d9b7240476184d0`
**Canonical branch:** `main`
**Implementation branch:** `codex/e04-rights-gated-assessment-registry`
**Risk:** `RISK-M`
**Expected final gate:** `EPIC`
**Data:** repository-owned fictional synthetic metadata only
**REAL_DATA_GATE:** `CLOSED`

## Role and outcome

Deliver one bounded outcome: replace the F0 assessment metadata skeleton with a
typed, versioned, deny-by-default registry that evaluates and exposes P0–P7 and
the exact rights matrix without admitting any assessment item, response,
administration, score, norm, cutoff or interpretation capability.

The E04 entry dependency for an active instrument is not satisfied. There is no
exact instrument/version/language/mode rights approval or qualified scientific
governance decision in the repository. Implement only the metadata-only,
rights-blocked branch authorized by the epic map. Do not select an instrument,
search for one, infer permission from public availability, or self-award a
rights/scientific/psychometric approval.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/implementation/E03_ACCEPTANCE_REPORT.md`

Then read only these directly relevant sources and sections:

- `docs/development/EPIC_MAP.md` — E04 only
- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §10 and §22.1 assessment testing only
- `docs/SCIENTIFIC_GOVERNANCE.md` — §§2, 6, 8–9 and 12–13
- `docs/architecture/DATA_MODEL.md` — §8
- `docs/DECISION_LOG.md` — ADR-012 only
- `ontology/psyche_domains.yaml` — `assessment.definition_rights`,
  `assessment.administration_score`, and their direct relation only
- `src/psyche_os/domain/entities.py` — knowledge snapshot and assessment registry metadata only
- `src/psyche_os/knowledge/registry.py`
- `src/psyche_os/knowledge/__init__.py`
- `src/psyche_os/application/ports.py` — `KnowledgePort` only
- `src/psyche_os/domain/invariants.py` — assessment/audit restrictions only
- `src/psyche_os/storage/schema.py`, `src/psyche_os/storage/e03_schema.py`, and
  `src/psyche_os/storage/migrations.py` — current accepted schema boundary only

Inspect additional files only when directly imported by a touched path. Do not
load historical v1 documents, the research dossier/source registry, broad
threat/safety documents, prior repair prompts, or E05+ scope.

## Frozen entry decision

The active-instrument path is `BLOCKED_BY_MISSING_RIGHTS_AND_GOVERNANCE`.
Therefore E04 must not implement an instrument, items, response collection,
administration, scoring, norms, thresholds, screening output or repeated-use
workflow. A fictional metadata fixture is permitted only to prove fail-closed
registry behavior; it is not a scientifically approved instrument.

Keep `RISK-M / EPIC`. Any attempt to add protected content, approve a real
instrument, enable administration/scoring, add clinical interpretation, or
change the personal-vault schema is an expansion requiring a new exact rights
and governance decision before that portion proceeds.

## In scope

- One authoritative immutable assessment-registry domain model. Reconcile the
  currently shadowing domain and knowledge-layer DTOs; preserve compatibility
  exports where practical, but do not keep two conflicting definitions.
- Exact instrument identity metadata: stable registry ID, definition version,
  title/owner, construct, named intended use, target population, language and
  locale, administration mode, recall period, official source reference,
  review owner/state/dates, and supersession relation.
- P0–P7 gate records with typed status (`pass`, `fail`, `not_evaluated`), stable
  content-free reason code, evidence-reference IDs, review state and expiry.
- The exact rights matrix fields:
  `view_items`, `store_items`, `collect_responses`, `store_responses`,
  `score_locally`, `store_score`, `display_interpretation`,
  `use_norms_or_cutoffs`, `translate_or_adapt`, `export_content`,
  `distribute_implementation`, and `use_in_research`. Each decision is typed
  `allow`, `deny` or `unknown`; `unknown` fails closed.
- Registry lifecycle states `draft`, `rights_pending`, `validation_pending`,
  `approved_for_named_use`, `restricted`, `deprecated`, and `revoked`, while
  preserving the distinct P0–P7 fail-closed outcomes from scientific governance.
- A deterministic evaluator that processes gates in order. A failed gate makes
  downstream gates `not_evaluated`; metadata cannot manufacture evidence,
  reviewer authority or an approved state.
- One package-owned fictional metadata-only fixture that passes P0 identity but
  is explicitly `rights_blocked` at P1. It contains no items, response options,
  scoring key, norm table, cutoff or proprietary/real instrument material.
- A narrow application-facing read/list/status path for the fixed fixture and
  registry metadata. No generic renderer dispatch, arbitrary metadata import or
  public self-issued approval token.

## Out of scope

- Any real or fictional assessment administration, responses, scoring engine,
  known-answer scoring vectors, norms, percentiles, thresholds, screening,
  diagnosis, treatment, recommendation or repeated-measurement workflow.
- Real instrument selection or research; proprietary/publicly posted test
  items, manuals, criteria, translations, scoring keys or norm tables.
- LLM scoring, translation, item generation, imputation or interpretation.
- A V3/personal-vault migration, new assessment/response/score tables, changes
  to the frozen E03 V2 inventory, desktop redesign, E05 sampling, analytics,
  cloud/network or importer work.
- Real personal or sensitive data while `REAL_DATA_GATE = CLOSED`.
- Unrelated refactoring, speculative abstractions, or future-epic scaffolding.

## Invariants to protect

- C-02: registry and deterministic gate output are metadata/derived decisions,
  never source evidence.
- C-05: no screening result or diagnostic authority exists in this blocked profile.
- C-08: missing rights/evidence remains explicit unknown/failure, never inferred permission.
- C-18: exact version, language, mode, rights and permitted use govern every state.
- C-20: fixtures are fictional metadata only and the real-data gate stays closed.
- E03's 35-table V2 inventory, migration checksum, logical portability,
  dependency deletion and accepted desktop authority remain unchanged.

## Implementation requirements

1. Inspect the clean worktree, current branch, accepted interfaces and any
   nested `AGENTS.md` before editing. Develop on the configured E04 candidate
   branch from current `main`; do not implement directly on `main`.
2. Model identity, lifecycle, gates, rights decisions and reason codes as closed
   enums/value types. Reject missing, extra, duplicate, malformed or internally
   contradictory fields before registry mutation.
3. Make registry entries immutable and version-addressed. A changed identity,
   rights decision or review creates a new version linked to its predecessor;
   it never silently rewrites the historical decision.
4. Enforce gate order. P0 failure yields `metadata_only`; P1 missing/deny yields
   `rights_blocked`; later failures use the frozen P2–P7 outcomes. No downstream
   `pass`, active use or `approved_for_named_use` is possible when an upstream
   gate failed or was not evaluated.
5. Treat evidence references as identifiers to separately governed evidence,
   not free-text claims. The fixture must not contain external copyrighted
   content or pretend that a citation is a license.
6. Remove or adapt the unsafe generic `register_assessment(..., schema)` port;
   callers must submit the typed closed metadata contract, not an arbitrary
   schema/object that could smuggle content or approval state.
7. Keep audit/errors content-free. Never log fixture descriptions, instrument
   content, evidence prose, assessment answers, paths, raw exceptions or stable
   content hashes.
8. Do not add a dependency. If a persistence or schema requirement appears
   necessary, stop that portion and document the exact need; do not create V3
   under this metadata-only prompt.

## Failure-driven validation

Every new check must name one realistic P0–P7 or boundary failure. Do not impose
an arbitrary coverage target.

- P0: incomplete/ambiguous identity, intended use, population, language, mode,
  recall period or version remains `metadata_only`.
- P1: every missing, `unknown` or `deny` required right yields
  `rights_blocked`; public availability/source citation cannot override it.
- P2: unresolved form/version/missing-rule integrity cannot be treated as ready.
- P3: unauthorized or unvalidated translation cannot enable standardized output.
- P4: missing purpose/population-specific measurement evidence stays
  `research_only` or `not_scored` as applicable.
- P5: absent deterministic algorithm, vectors or independent sign-off keeps
  scoring disabled; this epic supplies none and must never reach this gate as pass.
- P6: absent version/language/population interpretation evidence forbids norms,
  cutoffs and interpretation claims.
- P7: absent burden/retest/reactivity review keeps repeated use disabled.
- Boundary: unknown fields, arbitrary item/response/scoring content, duplicate
  versions, lifecycle jumps, forged approval/reviewer fields and mutable
  historical rewrites fail before registry mutation.
- Regression: accepted E03 migration inventory/checksum, archive tests and F0
  assessment-content prohibition remain green; no mandatory E04 proof skips.

Create focused tests at:

- `tests/unit/test_e04_assessment_registry.py`
- `tests/integration/test_e04_assessment_registry.py`

## Validation

Run the smallest affected tests while iterating. When the metadata-only E04
criteria are ready, run this final `EPIC` gate once:

```powershell
uv sync --frozen
uv run pytest -q tests/unit/test_e04_assessment_registry.py tests/integration/test_e04_assessment_registry.py tests/integration/test_e03_migration.py tests/integration/test_e03_canonical_archive.py
uv run pytest -q
uv run python scripts/validate_f0_scope.py
python scripts/dev/validate_orchestration.py
```

Record exact pass/fail/skip counts. No P0–P7, content-boundary, E03 migration or
E03 deletion regression proof may skip. The unchanged administrator-only
general `FilesystemAdapter` symlink skip may remain if still identical and
unrelated.

## Acceptance criteria

- [ ] P0–P7 and all twelve rights decisions are explicit, versioned and fail closed.
- [ ] One fictional metadata-only entry passes P0 and is blocked at P1; no entry can become approved or usable in this profile.
- [ ] No item, response, administration, scoring, norm, cutoff, screening or interpretation field/path is added.
- [ ] Registry history is immutable; malformed, duplicate and forged approval state fails before mutation.
- [ ] The read/status path exposes exact gate/reason/rights state without content or clinical claims.
- [ ] E03's V2 schema/migration/portability/deletion behavior is unchanged and green.
- [ ] Targeted and final validation results are recorded exactly.
- [ ] Qualified rights, scientific and psychometric review remains explicitly required before any active-instrument implementation; acceptance of this metadata-only blocked registry does not approve an instrument.
- [ ] `REAL_DATA_GATE` remains `CLOSED`.

## Git, report and stop rules

This prompt authorizes coherent E04 candidate commits, pushing only the E04
candidate branch, and one draft PR against `main` after meaningful validated
implementation exists. Candidate publication is not acceptance.

Create `docs/development/reports/E04.md` from
`docs/development/EPIC_REPORT_TEMPLATE.md`. If every implementation criterion
and local gate passes, record the implementation state truthfully. The active
acceptance workflow may set `ACCEPTED`, append accepted history and merge only
when the metadata-only profile and all objective EPIC gates pass without an
escalation trigger. Acceptance never approves an instrument or awards qualified
rights/scientific review. Do not open the real-data gate.

Stop the affected portion if protected content appears, exact rights/governance
approval would be required, the blocked profile cannot be represented without a
V3 migration, or a source-of-truth conflict is found. Do not weaken a gate to
continue. End with changed areas, exact validation/skips, limitations and the
specific qualified review still required.
