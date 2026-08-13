# PSYCHE OS — EPIC E01: Synthetic Assurance and Independent Recovery Proof

**Project root:** `C:\Dev\psyche-os`  
**Accepted E00 commit:** `0090ba0`  
**Risk:** `RISK-H`  
**Expected final gate:** `FULL`  
**Data:** bundled fictional synthetic fixtures only  
**REAL_DATA_GATE:** `CLOSED`

## Role and outcome

Deliver one bounded outcome: activate and adversarially prove authenticated
backup plus clean isolated recovery for the exact accepted synthetic E00
database-only profile, including the minimum Windows package-path boundary that
this capability needs. Assemble reproducible evidence for independent review;
do not self-award independence or real-data readiness.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/development/E00_REBASELINE_DECISION.md`
- `docs/implementation/E00_ACCEPTANCE_REPORT.md`
- `docs/development/reports/E00.md`
- `docs/development/EPIC_MAP.md` — E01 only
- `docs/architecture/PRIVACY_SECURITY_MODEL.md` — PS-17 through PS-26
- `docs/architecture/THREAT_MODEL.md` — TM-01–TM-05, TM-13–TM-17,
  TM-19, TM-21, TM-24, AP-4/AP-5 and required pre-real-data tests
- `docs/architecture/REAL_DATA_GATE.yaml`
- `docs/development/THREAT_TEST_MATRIX.md`

Inspect accepted commit `0090ba0`, the current backup/export, crypto, storage,
deletion, adapters and CLI paths, and their directly relevant tests. Do not read
the research corpus, historical v1, prior E00 repair prompts, UI/AI/import
architecture, or unrelated source files.

## Profile and activation decision

The E01 candidate is local, single-user, no-listener, SQLCipher-backed and
synthetic-only.

- Activate F02 backup/restore because clean recovery is E01's objective.
- Activate filesystem mutation only through a narrow backup-package store for
  the exact supported Windows profile. Keep the general blob/import filesystem
  mutation surface unavailable.
- Keep blob/object attachment writes disabled. The candidate profile contains
  no enabled blob payload capability; do not implement F05 blob lifecycle in
  this pass. RDG-01 remains unsatisfied for any blob-enabled profile.
- Keep broad imports, UI, network/cloud/LLM, release signing and release-grade
  SBOM attestation out of scope.

Do not remove the generic `FEATURE_DEFERRED_PRE_REAL_DATA` locks merely to make
tests pass. Introduce the smallest capability-scoped path required by backup.

## In scope

### 1. Authenticated encrypted backup

- Use a supported consistent SQLCipher snapshot; never serialize by racing live
  table reads.
- Encrypt/authenticate before leaving controlled staging. Bind exact format,
  vault/schema/app/key-wrap versions, sequence/cut-off, complete table inventory,
  row counts/checksums and deletion state in authenticated data.
- Require the exact authenticated payload inventory; missing, extra, duplicate,
  unreadable or ambiguous entries fail closed. Never default a missing table to
  an empty one.
- Recovery material is separate and is never embedded in the package. Output
  never overwrites an existing path.

### 2. Atomic isolated restore

- Authenticate and decrypt into a new explicit isolated target; never mutate an
  active or caller-supplied populated vault in place.
- Before activation validate package/version/inventory, SQLCipher integrity,
  schema and migration checksums, foreign keys, canonical/version/policy/
  provenance/deletion invariants, counts and semantic equality.
- Activation is a separate atomic operation that retains the previous vault on
  failure. Any injected failure leaves active-target bytes/state unchanged.
- Reject wrong/corrupt recovery material, malformed/downgraded/stale/rollback
  packages, manifest/payload swaps, extra/missing entries, interrupted writes,
  full-disk-like failures and poisoned restore data with content-free errors.

### 3. Minimum Windows backup-package boundary

- Scope filesystem authority to the configured backup root and package
  operation; no arbitrary path or general mutation capability escapes.
- On Windows, hold/verify actual directory and file handles across creation,
  replacement and activation. Reparse/tag/open/final-path ambiguity fails
  closed. Do not check a pathname, close the handle and then mutate by pathname.
- Add deterministic non-admin swap/reparse simulations against the production
  path plus an exact Windows runtime profile test. If the runtime proof cannot
  run, keep the Windows capability disabled and report E01 `BLOCKED`; do not
  label source inspection as runtime evidence.

### 4. Recovery and durability evidence

- Prove recovery with the OS convenience wrapper unavailable and only the
  independent recovery material plus encrypted package present.
- Rerun accepted canonical invariants after restore and prove a synthetic
  create/correct/delete/export/backup/recover semantic comparison.
- Exercise backup rollback/poisoning, backup expiry/deletion limits, interrupted
  migration during isolated restore, and deterministic repeated archive cycles.
- Do not invent future schemas. If E01 adds no schema version, exercise the
  frozen V1 fixture/migration and state that future-version compatibility is not
  evidenced. If E01 necessarily changes schema, add exactly one explicit
  ordered migration with rollback and old-reader implications.
- Scan controlled E01 outputs for a unique synthetic plaintext canary across
  database/WAL/temp/package/log locations. Never scan external user paths.

### 5. Evidence package

Create a compact machine-readable E01 evidence index under `artifacts/e01/`
containing the accepted commit, platform/profile, command/test identifiers,
artifact digests, pass/fail/blocked state, expiry and reviewer-role placeholders.
Do not store keys, recovery material, absolute home paths, plaintext fixture
bodies or self-declared independent approval. Human cryptographic/privacy/
recovery review remains required.

## Invariants to protect

- C-10 through C-14 and C-19/C-20.
- E00 canonical/version/migration/synthetic-write/validation invariants cannot
  regress.
- Backup is not logical export; restore is not activation; checksum is not
  authentication; test success is not real-data authorization.
- Logs, errors, reports and evidence remain content-free.
- `REAL_DATA_GATE` and every RDG requirement remain `CLOSED/UNSATISFIED` unless
  a later authorized reviewer records genuine evidence. E01 never opens it.

## Failure-driven validation

Add only tests corresponding to named paths above. At minimum prove:

1. exact synthetic snapshot → encrypted package → independent clean restore →
   semantic/invariant equality;
2. wrong key/recovery secret, bit flip, manifest/payload swap, downgrade,
   missing/extra table and stale/rollback package all fail before activation;
3. injected failures after staging, after at least one restore write, during
   migration/validation and immediately before activation preserve active bytes;
4. non-empty/populated target and target-schema inspection error fail closed;
5. backup-specific Windows path swap/reparse/open ambiguity cannot escape or
   mutate, with actual runtime profile evidence;
6. backup/restore CLI/API is enabled only for the proven profile, while blob and
   general filesystem mutations still return `FEATURE_DEFERRED_PRE_REAL_DATA`;
7. delete/backup-expiry limitations and canary scan results are truthful;
8. evidence index cannot turn missing/placeholder/expired reviewer evidence into
   PASS.

During implementation run the smallest affected tests. Before reporting
completion, run this `FULL` gate once:

```powershell
uv sync --frozen
uv run pytest -q
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python scripts/validate_e01_assurance.py
python scripts/dev/validate_orchestration.py
```

`validate_e01_assurance.py` must be read-only and must validate actual generated
E01 evidence and production-path behavior; it must not manufacture evidence.
No arbitrary coverage percentage is an acceptance condition. A skipped Windows,
recovery or atomicity proof is not a pass for the enabled candidate profile.

## Acceptance criteria

- [ ] F02 authenticated completeness and atomic isolated restore pass for the
  exact synthetic database-only profile.
- [ ] The backup-specific Windows mutation boundary has runtime evidence and no
  unresolved Critical/High for that enabled capability.
- [ ] Clean recovery works without the OS wrapper; hostile/fault cases fail
  closed and active bytes remain unchanged.
- [ ] E00 invariants rerun after restore; deletion/rollback/canary limitations
  are explicit.
- [ ] Blob writes and general filesystem/import mutation remain disabled; their
  PRE_REAL_DATA findings are not marked resolved.
- [ ] Evidence is reproducible and ready for genuine independent review, which
  is not self-awarded.
- [ ] All final commands and material skips/failures are recorded exactly.
- [ ] `REAL_DATA_GATE` remains `CLOSED`.

## Work and stop rules

Preserve unrelated changes and reuse accepted code. Do not redesign E00, prepare
E02, implement UI/import/blob/provider features, perform research, or broaden
the threat model. For a material conflict create the deviation record and stop
only that portion. Do not commit or push.

Create `docs/development/reports/E01.md` from the epic report template. If the
implementation and required local evidence pass, set only
`current_epic.status: IMPLEMENTED`; otherwise set `BLOCKED`. Do not set
`ACCEPTED`, append accepted history, advance E02, change RDG states, or claim an
independent review. End with exact results, residual risks and the focused Codex
review required next.
