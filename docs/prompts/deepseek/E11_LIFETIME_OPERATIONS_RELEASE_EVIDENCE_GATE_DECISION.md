# PSYCHE OS — E11: Lifetime Operations, Release Evidence, and Gate Decision

**Project root:** `C:\Dev\psyche-os`
**Implementation branch:** `codex/e11-lifetime-operations-release-evidence`
**Prepared from:** E10 accepted `6c2ccf75637ef85db42bc62caf206c1c0e736d21`
**Risk:** `RISK-H`
**Expected final gate:** `FULL / RELEASE`

## Role and outcome

You are the primary implementation engineer for this epic. Deliver one concise
outcome: deterministic machinery and an evidence-package format that can
evaluate one exact candidate for the accepted local/offline profile, while
keeping the real-data gate closed unless a separate authorized human decision
later opens it.

This is not an authorization to admit real data. An implementation agent or
model cannot act as `REPOSITORY_OWNER` or create the required human decision.

## Read first

Always read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`

Then read only these relevant sources:

- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` §§20, 22--25.
- `docs/ROADMAP.md` Phase 8 and `docs/development/EPIC_MAP.md` E11.
- `docs/DECISION_LOG.md` ADR-020, ADR-021, and ADR-023.
- `docs/architecture/REAL_DATA_GATE.yaml` and
  `docs/architecture/REAL_DATA_GATE_PROFILE.yaml`.
- `docs/architecture/PRIVACY_SECURITY_MODEL.md` PS-22--PS-26 and
  `docs/architecture/THREAT_MODEL.md` release/dependency, recovery, and
  incident boundaries.
- `docs/development/reports/E10.md` and
  `docs/implementation/E10_ACCEPTANCE_REPORT.md`.
- `scripts/validate_f0_artifacts.py` and the existing artifact/SBOM owners it
  names; reuse their accepted evidence patterns only where the exact candidate
  binding still holds.
- `docs/future/CONVERSATIONAL_PSYCHOLOGICAL_SUPPORT_NORTH_STAR.md` §10 and the
  E11 row only. It supplies one compatibility constraint: preserve independent
  capability/profile decisions and provider/model/policy regression triggers;
  it adds no feature or opening authority.

Do not load historical v1, the original research master prompt, the full
research dossier/source registry, or unrelated architecture. Do not reread or
modify the proposal package.

## Frozen architecture

- The accepted profile is
  `local_personal_evidence_reflection_windows_v1` version `1.0`, defined in
  `docs/architecture/REAL_DATA_GATE_PROFILE.yaml`. Its enabled/excluded scope
  is a release definition, not proof that the current implementation enforces
  it.
- `docs/architecture/REAL_DATA_GATE.yaml` is stable policy only. It remains
  fail-closed with default `CLOSED`, retains RDG-01--RDG-12, and owns no live
  candidate decision or per-candidate evidence.
- An exact candidate record lives at
  `artifacts/e11/gate-evaluations/<evaluation-id>.yaml`. It binds profile path,
  ID, version, SHA-256 of the exact profile-file bytes, profile source commit,
  candidate source/build/platform, lock/SBOM/artifact identities, raw evidence,
  reviews, expiry/currentness, and candidate-specific RDG status.
- Lifecycle is `DRAFT` → deterministic final validation → immutable `SEALED`.
  A DRAFT cannot support `OPEN`; any changed build, evidence, review, status,
  applicability, expiry, regression, or decision uses a new evaluation ID or
  successor record.
- The only RDG statuses are `PROVED_FOR_CANDIDATE`, `NOT_PROVED`,
  `NOT_APPLICABLE_EXCLUDED`, `STALE_OR_EXPIRED`, and
  `UNKNOWN_OR_INCOMPLETE`. `NOT_APPLICABLE_EXCLUDED` requires proof that the
  whole control predicate is excluded and unreachable.
- Required independent/qualified reviews remain in scope for every applicable
  boundary. The gate decider is a human `REPOSITORY_OWNER`, using
  `local_human_attestation_v1`, bound to the exact sealed-evaluation digest.
  Implement record support only; do not create, impersonate, or automatically
  accept an attestation. No PKI, service, daemon, or production dependency is
  introduced.

## In scope

- Release manifest/provenance and reproducibility evidence for one exact
  candidate; exact dependency, lock, SBOM, license, artifact, and source/
  security-currentness reconciliation.
- Preservation, migration, recovery, restore, incident-disable, rollback, and
  residual-risk/expiry evidence that names the exact candidate and profile.
- A machine-readable exact-candidate RDG evaluation schema, deterministic
  evaluator/validator, `DRAFT`/`SEALED` lifecycle, successor/invalidation
  mechanics, and human-attestation record schema/validation support.
- Focused synthetic tests and reports that preserve raw evidence references,
  provenance, uncertainty, contradictions, expiry, and fail-closed outcomes.

## Out of scope

- Automatic gate opening, an authorized `OPEN` decision, impersonating
  `REPOSITORY_OWNER`, or treating a coding-model output as a human decision.
- Real personal or sensitive data while `REAL_DATA_GATE` is closed.
- New product capability, importer, provider/network boundary, professional
  workflow, schema migration unrelated to E11 evidence mechanics, or
  speculative future/conversational scaffolding.
- Mutating stable policy/profile files to record a candidate result, inventing
  evidence from accepted E00--E10 reports, and any new production dependency.

## Invariants to protect

- C-02, C-10--C-14, C-18--C-20: evidence remains distinct from model output;
  `NEVER_CLOUD`, encryption/recovery/deletion, open exit, rights/provenance,
  synthetic-first, and closed-gate rules remain fail closed.
- The stable policy/profile/evaluation lifecycle from ADR-023 remains separate;
  a profile never self-hashes and accepted epics never auto-prove an RDG.
- Historical raw/verbatim material remains separate from normalized/derived
  records; all new fixtures are clearly fictional and repository-owned.

## Implementation requirements

1. Inspect the current worktree, dependencies, accepted interfaces, and any
   applicable nested `AGENTS.md` before editing. Reuse accepted F0/E01/E07/E08/
   E10 primitives only where their exact candidate binding can be proved.
2. Keep the exact evaluation immutable after sealing. Its seal digest covers
   the evaluation payload; a later attestation names the evaluation ID and
   sealed digest without modifying the payload.
3. Make every identity mismatch, missing/expired evidence or review, unresolved
   Critical/High finding, unsupported platform, failed reproduction, unknown
   boundary, invalid exclusion, missing human attestation, and attestation
   digest mismatch return `CLOSED`.
4. Preserve the gate as closed throughout implementation. A future human may
   separately attest over a valid SEALED evaluation; the evaluator must never
   generate that authority or change `STATE.yaml.real_data_gate.state` to OPEN.

## Failure-driven tests

Each test must use only synthetic fixtures and name its failure. Cover at least:

1. profile digest mismatch;
2. wrong source, build, or platform identity;
3. lock, SBOM, or artifact mismatch;
4. evidence from a previous candidate;
5. expired evidence or review;
6. unresolved Critical/High finding;
7. invalid `NOT_APPLICABLE_EXCLUDED` classification;
8. provider/importer/professional boundary mismatch;
9. non-reproducible build;
10. a modified SEALED evaluation;
11. human attestation referencing the wrong sealed digest;
12. model attempt to act as human gate decider;
13. missing human attestation;
14. accidental automatic OPEN; and
15. attempted real-data use while the gate is closed.

Do not add an arbitrary coverage target or duplicate equivalent tests.

## Validation

During implementation, run the smallest relevant unit/property/integration
checks. Before reporting completion, run the final FULL / RELEASE gate once:

```powershell
uv run pytest -q
uv run python scripts/dev/validate_orchestration.py
uv run python scripts/validate_research_foundation.py
```

Also run the exact deterministic E11 release/evaluation validators introduced
by this epic, a clean independent rerun of affected evidence paths, and
`git diff --check`. Do not weaken an existing validator to pass a gate.

## Acceptance criteria

- [ ] Exact candidate, profile, build/platform, lock/SBOM/artifact, evidence,
  review, expiry/currentness, and residual-risk bindings are machine-readable
  and fail closed.
- [ ] DRAFT never supports OPEN; SEALED content is immutable; successors are
  required for changed/expired/regressed facts.
- [ ] The candidate evaluator never opens the gate automatically and never
  treats a model as the required human `REPOSITORY_OWNER` attestation.
- [ ] Every listed failure-driven path has focused synthetic coverage.
- [ ] `REAL_DATA_GATE` remains `CLOSED`; no actual evaluation is misrepresented
  as an authorized OPEN decision.
- [ ] Targeted and final validation results are recorded exactly.

## Work and stop rules

- Keep scope controlled; do not commit or push unless separately authorized.
- Stop only the blocked portion for a material source-of-truth conflict,
  security/privacy impossibility, unavailable required dependency/license,
  gate bypass, a need for stronger-than-ADR-023 cryptographic attestation, or
  appearance of real data/secrets. Create an architecture-deviation record for
  a material architecture conflict; do not silently alter higher authority.
- Do not mark this epic `ACCEPTED`, append it to `accepted_epics`, or create a
  successor. It is terminal; `next_epic: null` remains valid.

## Final report and state boundary

Create `docs/development/reports/E11.md` from
`docs/development/EPIC_REPORT_TEMPLATE.md`. Report only implemented behavior,
key files, exact validation results, evidence gaps, residual risks, and
deviations—never chain-of-thought or sensitive content.

If all implementation criteria and local validation pass, set only
`current_epic.status` in `docs/development/STATE.yaml` to `IMPLEMENTED`. For a
material blocker set it to `BLOCKED`. Do not set `ACCEPTED`, append
`accepted_epics`, change `next_epic`, or open the real-data gate.
