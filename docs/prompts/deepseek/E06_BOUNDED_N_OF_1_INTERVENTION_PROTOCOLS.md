# PSYCHE OS — EPIC E06: Bounded N-of-1 and Intervention Protocols

**Project root:** `C:\Dev\psyche-os`
**Accepted E05 implementation commit:** `8097de1a1f2e3e7e8e6199f633a774180e298069`
**Accepted E05 merge:** `b61cdc48b18894b7cf5b2134ca5444ae16697502`
**Canonical branch:** `main`
**Implementation branch:** `codex/e06-bounded-n-of-1-protocols`
**Risk:** `RISK-H`
**Expected final gate:** `FULL`
**Data:** repository-owned fictional synthetic protocols and outcomes only
**REAL_DATA_GATE:** `CLOSED`
**Acceptance review:** independent focused Codex high-risk review required

## Role and outcome

Deliver one bounded outcome: implement a deterministic synthetic-only N-of-1
protocol and policy vertical slice that preregisters design and analysis state,
keeps action risk and causal-language ceilings enforceable, and proves that
prohibited interventions or unsupported claims fail closed.

This epic is the first action-influencing and causal-language boundary. Implement
the candidate and its evidence; do not self-accept, merge, advance E07 or open the
real-data gate.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/implementation/E05_ACCEPTANCE_REPORT.md`

Then read only these directly relevant sources and sections:

- `docs/development/EPIC_MAP.md` — E06 only
- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §14 only
- `docs/SCIENTIFIC_GOVERNANCE.md` — §§7.3–9 and §13 only
- `docs/architecture/DATA_MODEL.md` — §9.4 only
- `docs/architecture/MENTAL_HEALTH_AI_SAFETY.md` — §§3, 9 and 12 only
- `docs/DECISION_LOG.md` — ADR-014 only
- `src/psyche_os/domain/longitudinal.py`,
  `src/psyche_os/application/e05_longitudinal.py`, and
  `src/psyche_os/storage/e05_schema.py` — accepted E05 boundaries only
- `src/psyche_os/storage/migrations.py`,
  `src/psyche_os/backup_export/versioned.py`, and
  `tests/integration/test_e05_migration.py` — accepted V3 compatibility only

Inspect additional files only when directly imported by a touched path. Do not
load historical v1 documents, the original research prompt, the full dossier or
source registry, unrelated architecture, prior repair prompts or E07+ scope.

## Frozen entry decisions

### Risk and review

Keep `RISK-H / FULL`. A separate focused Codex review is mandatory after the
implementation report and candidate commits exist. That review must use
`docs/prompts/codex/HIGH_RISK_EPIC_REVIEW_TEMPLATE.md` and focus on
identification assumptions, claim ceilings, action gates and dangerous edge
cases. Implementation validation is not acceptance.

Qualified scientific/clinical review is not available in this epic. Therefore:

- executable protocols are limited to `R0_observational` and one fixed fictional
  `R1_low_reversible` allowlisted action;
- `R2_moderate_or_symptom_targeting` remains encoded but unavailable with an
  explicit `qualified_review_required` decision;
- `R3_prohibited_autonomous` remains encoded and unconditionally denied;
- no fixture, recommendation or positive test may make R2/R3 executable.

### Synthetic fixture

Use exactly one package-owned semantically neutral fictional scenario. Its A/B
labels and outcomes exist only to test protocol mechanics and known-answer
analysis. They must not name medication, substance, diet/fasting, sleep
restriction, trauma/exposure, self-harm, dangerous exertion, acute symptoms,
diagnosis, treatment or a real person's behavior.

No renderer, CLI, environment, filesystem, import or generic database command
may supply arbitrary protocol, intervention, outcome or analysis content while
the gate is closed.

### Persistence

Decide inline whether accepted V3 is sufficient or one additive V3-to-V4
migration is required. Do not create a separate preflight.

Use V3 only if canonical E06 records remain typed, versioned, portable and
deletion-aware without opaque JSON, semantic overloading or source/version loss.
If persistence is required, V4 must be one checksummed additive forward
migration. It may add E06-specific tables, indexes and dependency relations only.
It must preserve exact V1/V2/V3 inventories and checksums, readers, logical
portability and accepted E03/E05 behavior. No accepted table may be rebuilt or
semantically altered; if that becomes necessary, stop the affected portion and
create an architecture deviation. No reverse migration is claimed: rollback is
restoration/activation of retained verified V3 state.

## In scope

- Closed typed `DesignTier` values `D0_tracking`, `D1_exploratory_AB`,
  `D2_repeated_phase`, `D3_randomized_crossover`, `D4_replicated_series` with a
  deterministic maximum-claim resolver.
- Closed typed `ActionRiskTier` values `R0_observational`,
  `R1_low_reversible`, `R2_moderate_or_symptom_targeting`, and
  `R3_prohibited_autonomous`; user/model/imported text cannot lower a tier.
- Immutable/versioned `InterventionDefinition` metadata with fixed identity,
  components, delivery, reversibility, evidence/certainty, harms,
  contraindication/interaction boundary, accessibility/equity, rights,
  guideline context, risk decision, review state and review trigger.
- Immutable/versioned preregistered `ExperimentProtocol` covering question,
  estimand, eligibility, A/B labels, outcome and measurement version, baseline,
  phase design, assignment/randomization, blinding state, duration,
  washout/carryover assumptions, concurrent-change/confound plan, missingness,
  autocorrelation, multiplicity, minimum information, stopping, adverse-event
  rule, analysis version/config and preregistration digest/time.
- Deterministic seeded assignment for the fixed fictional scenario. Pin seed,
  algorithm and runtime-visible version; reruns must reproduce exact assignments.
- Typed execution/deviation/stop state. An adverse event, unavailable eligibility,
  contraindication, stale protocol version or stop rule blocks further assignment
  and analysis claims.
- A deterministic claim resolver for C0–C6 that never exceeds the minimum of
  design, measurement, coverage, missingness, replication, sensitivity and risk
  ceilings. Denial exposes typed reasons, not a weakened fallback claim.
- Known-answer descriptive/statistical analysis for the fictional fixture with
  pinned cut-off, inclusion/exclusion, transformation, coverage, missingness,
  serial-dependence method, phase/carryover assumptions, multiplicity family,
  sensitivity results, code/config version and limitations.
- Focused unit/property/integration tests, reproducible report output and, if
  persistence is added, migration/portability/deletion tests.

## Explicitly out of scope

- Real personal, psychological, medical, sleep, substance, medication, food,
  trauma, self-harm, wearable, location, message, calendar or life-archive data.
- Medication/dose/start/stop/withdrawal, supplements, substances, dangerous
  fasting or food restriction, sleep restriction/deprivation, trauma exposure,
  self-harm, dangerous exertion, acute-state management or instructions that
  enable them.
- Executable R2/R3 interventions, autonomous symptom targeting, clinician
  substitution, treatment selection, diagnosis, risk prediction or safety
  monitoring/rescue promises.
- Universal causal stories, etiologic explanations, population generalization,
  recommendations based on significance, adaptive experimentation or automatic
  intervention optimization.
- LLM analysis/policy authority, external/network services, passive/ambient
  sensing, E04 assessment administration/content/scoring or E07+ AI work.
- UI expansion unless the complete frozen contract cannot be proved through the
  canonical domain/storage/application services and tests.

## Invariants to protect

- C-02: analysis is a versioned derived proposal, never source evidence.
- C-05–C-07: no diagnosis; causal and individual/population claims stay within
  their exact design and transfer limits.
- C-08–C-09: missingness, alternatives, contradictions, falsification and review
  triggers remain explicit.
- C-17–C-18: no clinical authority, rescue promise or ungoverned scientific or
  intervention content.
- C-20: one repository-owned fictional pack only; `REAL_DATA_GATE` stays closed.
- E05's C0–C2 descriptive default, source/version separation, reactivity warning,
  V1/V2/V3 histories and synthetic-only authority remain unchanged.

## Implementation requirements

1. Verify clean synchronized `main`, accepted E05 reachability and the configured
   candidate branch before editing. Never implement directly on `main`.
2. Use frozen dataclasses/value objects and closed enums. Reject unknown, extra,
   incomplete, contradictory or stale state before mutation.
3. Treat protocol approval, preregistration and intervention allowlisting as
   independent typed decisions. No field implies another approval.
4. Canonicalize the preregistration deterministically before hashing. A changed
   field creates a new version and digest; it never rewrites an active run.
5. Make assignment reproducible and auditable without using security-sensitive
   randomness. Detect assignment drift and refuse analysis.
6. Preserve scheduled assignment, actual exposure, outcome time, deviations,
   concurrent changes, missingness and stop state separately. Do not impute by
   default or convert missing outcomes into adherence judgments.
7. The claim resolver must be monotone: removing evidence or adding a failure can
   only preserve or lower the ceiling, never raise it. User/model wording cannot
   select a higher level.
8. D0/D1 must never emit causal effect wording. Higher design labels alone are
   insufficient: absent identification, measurement, replication, coverage,
   serial, carryover or sensitivity evidence blocks the corresponding ceiling.
9. P-values, if calculated for a justified known-answer test, never determine
   effect importance, causality or an action. Prefer exact effect/uncertainty and
   sensitivity disclosure; do not add a broad statistics dependency merely for
   convenience.
10. Any stop/adverse/contraindication signal immediately freezes assignment and
    claim generation with a typed state. It must not attempt clinical triage,
    diagnose severity or suggest a substitute intervention.
11. Keep audits/logs content-free: no fixture outcome content, intervention
    components, raw exceptions, stable content hashes, paths or preregistration
    payloads.
12. Reuse the accepted named-operation application authority. Do not add generic
    CRUD, SQL, Python, filesystem or renderer-provided raw payload dispatch.

## Required failure proofs

Every added test must map to a realistic E06 failure. At minimum prove:

- incomplete question/estimand/outcome/measurement/phase/missingness/stop/adverse
  or analysis plan is rejected before write;
- preregistration changes require a new version/digest and stale runs fail;
- the same seed/config reproduces assignments and changed algorithm/config is
  detected;
- user, model and imported text cannot lower risk or raise design/claim tier;
- R2 remains unavailable without qualified review and every R3 action is denied;
- prohibited intervention categories cannot be registered, aliased, substituted
  or emitted as recommendations;
- contraindication/adverse/stop state prevents further assignment and claims;
- D0/D1 cannot emit effect language; higher tiers cannot emit above their design
  ceiling;
- missing coverage, high missingness, autocorrelation checks, replication,
  carryover checks or sensitivity evidence lowers/blocks the requested claim;
- ceiling resolution is monotone under evidence removal and failure addition;
- no significance-to-action, universal-cause, diagnostic, treatment, prediction
  or clinical wording is emitted;
- missing outcomes are not imputed and no compliance, shame, streak, urgency or
  engagement score appears;
- output pins person/scope/window/cut-off, exact protocol/intervention/measurement,
  assignment and analysis versions, coverage, assumptions, sensitivity and
  limitations;
- arbitrary renderer/CLI/import/filesystem/environment/database payloads cannot
  create or change canonical protocols, policy or outcomes;
- E05 remains C3-disabled by default and E04 remains rights-blocked;
- `REAL_DATA_GATE` remains `CLOSED`.

If V4 exists also prove exact checksum, atomic interruption rollback, verified
no-op rerun, exact V1/V2/V3/V4 inventories, frozen prior checksums/readers,
old-version logical portability, pending-deletion block and E06 dependency
deletion.

Create focused tests at:

- `tests/unit/test_e06_n_of_1_protocols.py`
- `tests/integration/test_e06_n_of_1_protocols.py`
- `tests/integration/test_e06_migration.py` only if V4 persistence is introduced

Use property/invariant or bounded simulation tests only where they close the
named randomization, monotonicity, calibration or sensitivity failures. Do not
set an arbitrary coverage percentage.

## Validation

Run the smallest affected tests while iterating. Once the exact E06 candidate is
complete, run this `FULL` gate once on final implementation state:

```powershell
uv sync --frozen
uv run pytest -q tests/unit/test_e06_n_of_1_protocols.py tests/integration/test_e06_n_of_1_protocols.py tests/unit/test_e05_longitudinal_analysis.py tests/integration/test_e05_longitudinal_analysis.py tests/integration/test_e05_migration.py tests/integration/test_e03_migration.py tests/integration/test_e03_canonical_archive.py
uv run pytest -q
uv run python scripts/validate_f0_scope.py
python scripts/dev/validate_orchestration.py
```

If `tests/integration/test_e06_migration.py` exists, include it in the first
pytest command. Also run scoped Ruff and strict mypy over every new E06 source
module. If desktop files change, run the accepted desktop/toolchain gate from the
E05 prompt exactly once on final state. Record exact results and skips. No E06,
migration, E05 or E03 mandatory proof may skip. The unchanged administrator-only
Windows `FilesystemAdapter` symlink fixture may remain skipped if identical and
unrelated.

## Acceptance criteria

- [ ] Design tiers, action-risk tiers, intervention decisions, preregistration,
  assignments, deviations, stop/adverse state and analysis versions are closed,
  typed, immutable/versioned and reproducible.
- [ ] Only the fixed fictional R0/R1 pack is executable; R2 requires unavailable
  qualified approval and R3 is unconditionally denied.
- [ ] Claim language is monotone and never exceeds the minimum supported
  design/measurement/coverage/serial/replication/sensitivity/risk ceiling.
- [ ] Known-answer analysis exposes exact scope/window/cut-off, coverage,
  missingness, assumptions, versions, sensitivity and limitations without
  significance-to-action or universal/clinical interpretation.
- [ ] Stop, adverse, contraindication, prohibited action, stale version,
  assignment drift and arbitrary-payload failures are executable and fail closed.
- [ ] No real/arbitrary data path, external service, passive sensing, E04 content,
  generic dispatch or E05 regression is introduced.
- [ ] Any V4 migration is additive, checksummed, atomic, portable,
  deletion-aware and preserves exact V1/V2/V3 histories.
- [ ] Targeted and final validation results are recorded exactly.
- [ ] `REAL_DATA_GATE` remains `CLOSED`.

## Work, publication and stop rules

- Work only on `codex/e06-bounded-n-of-1-protocols` from current `main`.
- Coherent candidate commits, pushing only that branch and opening one draft PR
  against `main` are authorized after meaningful validated implementation exists.
- Candidate publication is not acceptance. Do not merge, mark E06 accepted,
  append accepted history, prepare E07 or modify the real-data gate.
- Stop the affected portion and create an architecture deviation for a material
  source-of-truth conflict, destructive/non-additive migration, new external
  trust boundary, real data, executable R2/R3 requirement or inability to enforce
  the claim/action ceiling. Continue unaffected safe work only.

## Final report and state boundary

Create `docs/development/reports/E06.md` from
`docs/development/EPIC_REPORT_TEMPLATE.md`. Record implemented behavior, schema
decision, exact protocol/analysis semantics, validation/skips and limitations.

If every implementation criterion and local gate passes, set only:

```text
current_epic.status: IMPLEMENTED
current_epic.implementation_status: IMPLEMENTED
current_epic.review_verdict: PENDING_CODEX_REVIEW
```

Otherwise record the blocked state truthfully. Do not set `ACCEPTED`, append
accepted history, advance E07, merge or open the gate. End with changed areas,
exact validation, residual limitations and the exact focused review handoff.
