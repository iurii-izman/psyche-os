# PSYCHE OS — E00 final bounded repair

Work autonomously in `C:\Dev\psyche-os`. Repair only the remaining F02, F05,
F07, F08, and F09 failures documented in
`docs/implementation/E00_ACCEPTANCE_REPORT.md`. Do not perform research, a broad
audit, or architecture redesign. Do not revisit F01/F03/F04/F06 unless these
changes cause a direct regression in an already accepted invariant.

Use synthetic fixtures only. Do not start E01, create an accepted commit, or
open the real-data gate. `REAL_DATA_GATE` remains `CLOSED`.

## Read first and authority

Read only:

1. `AGENTS.md` and `CONSTITUTION.md`;
2. `docs/development/STATE.yaml`;
3. `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` relevant F0/security sections;
4. `docs/architecture/THREAT_MODEL.md`;
5. `docs/architecture/PRIVACY_SECURITY_MODEL.md` relevant controls;
6. `docs/architecture/SYSTEM_ARCHITECTURE.md` relevant storage boundaries;
7. `docs/architecture/REAL_DATA_GATE.yaml`;
8. `docs/DECISION_LOG.md` relevant ADRs;
9. `docs/prompts/F0_IMPLEMENTATION_PROMPT.md` and
   `docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md` relevant contracts;
10. the acceptance report and current production/tests for these five findings.

Authority is Constitution → v2 master specification → accepted threat model/ADR
→ frozen F0/E00 contract → this prompt. Stop the affected portion and record a
deviation instead of silently resolving a material conflict.

## Threat-boundary calibration

F07 protects the supported storage mutation boundary from ordinary application
callers, imported/untrusted input, direct unauthorized UoW use, and forged,
copied, uninitialized, or serialized authority. It does not claim to defeat an
attacker who already has arbitrary execution, unrestricted monkey-patching or
memory access inside the trusted Python process, can replace trusted package
code, or has Administrator/SYSTEM control. Those remain serious endpoint and
supply-chain risks; do not describe them as solved.

F09 protects the supported Windows vault boundary from ordinary traversal,
junction/reparse redirection, and pathname swap/TOCTOU. It does not claim to
defeat Administrator/SYSTEM, a hostile kernel/filesystem driver, trusted-process
arbitrary execution, or trusted-code replacement. Implement only the minimum
documented Windows handle adapter needed for the frozen operations, not a generic
filesystem-security framework.

These calibrations do not weaken the mandatory controls below.

## F02 — authenticated complete backup and isolated restore

- Establish one authoritative, versioned F0 backup inventory from the frozen
  schema/migrations. Enumerate deliberate exclusions explicitly. Every listed
  table must exist and be readable; omission or inspection error fails backup.
- Authenticate the canonical manifest by placing it inside the AEAD payload or
  binding its canonical bytes in AAD. Require exact magic and format/schema
  versions at every level—no version `0`, downgrade, missing, or contradictory
  value.
- Require the exact inventory key set, one non-empty checksum per table, exact
  counts, and agreement among manifest, decrypted rows, schema, and blob totals.
  Reject extra/missing tables, removed checksums, mutable outer-manifest tamper,
  wrong key, and any ambiguous evidence.
- Restore into a new isolated staging database with the complete expected schema.
  Target inspection errors or existing data fail closed. Validate database/blob
  integrity, foreign keys, schema, migrations, counts, checksums, and invariants
  before one all-or-nothing activation; never expose partial restore state.
- Do not add new backup features beyond F0.

Required production-path tests: omitted inventory table; version downgrade;
empty/missing checksum; outer/inner manifest tamper; wrong key; nonempty target;
injected failure with original target byte/state equality; successful encrypted
full-schema backup → isolated restore → content/invariant equality.

## F05 — real version, migration, SQL, and blob invariants

- For every frozen `VERSIONED_TABLES` entry, separate stable/business identity
  from row/version identity. Allow multiple historical versions, keep consistent
  version/supersession/transaction columns, and enforce exactly one active row
  per stable identity. Preserve required foreign keys and historical references.
- Remove global business-ID constraints that block history. Use a parameterized
  real-schema test for the common version contract rather than duplicate tests.
- Preserve every immutable subtype value on close/version with
  `dataclasses.replace()` or a proven equivalent; test a non-default subtype
  value.
- Retain per-table table/column allowlists. No caller-controlled identifier may
  reach SQL interpolation.
- Use small explicit, ordered, checksummed migration artifacts and explicit
  transactions. Do not split SQL naïvely on semicolons. A DDL or bookkeeping
  fault must roll back both schema and migration record; prove idempotence.
- Require a non-empty vault-keyed digest before any blob write. Persist vault ID
  and all envelope/AAD context. Enforce observable `CREATED → STORED → VERIFIED`
  before semantic commit; failure rolls back or leaves a restartable non-active
  state. Verification must load persisted context and reject missing digest,
  tampering, wrong vault, and cross-vault reuse.

Required production-path tests: multiple historical versions; one-active
uniqueness; non-default subtype preservation; hostile column identifier;
migration ordering/idempotence and injected rollback; blob state sequence;
missing digest; cross-vault rejection; persisted AAD/context verification.

## F07 — bundled-fixture authorization and truthful CLI

- Expose no supported/public minting API. A normal constructor must not yield
  authority. An `object.__new__`/uninitialized object, forged state, copy,
  deepcopy, or serialized/deserialized object must not pass storage validation.
  Never return a raw authority secret/token to callers.
- Keep authority creation and consumption inside a package-owned loader that
  verifies an allowlisted bundled package-resource manifest, schema/version,
  `synthetic_fixture` marker, fixture identity, and digest. Bind authority to
  that exact verified identity and do not return it from the loader API.
- The storage/UoW boundary must validate authority before any SQL or filesystem
  mutation for synthetic record/blob writes. Direct UoW use without valid loader
  authority fails and leaves state byte-for-byte/semantically unchanged.
- External paths, files, flags, environment values, restored forged markers, or
  caller-created content cannot become bundled fixture authority.
- Every CLI `ok` result must be followed by verification of the reported state.
  `vault init` must actually create, initialize, close/reopen as appropriate, and
  verify the encrypted synthetic-only vault it reports.

Required tests: public/normal mint attempt; uninitialized/forged authority;
copy/deepcopy/serialization; direct UoW without authority and no mutation;
altered/external fixture rejection; bundled fixture success through production
loader; CLI false-success prevention including verified `vault init`.

## F08 — read-only behavioral evidence validation

- Validators must not create or modify repository artifacts. Test a before/after
  inventory of relevant paths using metadata and content digests; temporary test
  output belongs outside the repository and is removed.
- Generate representative backup/export packages with production code and use a
  real shipped JSON Schema validator against the emitted instances. Exercise
  nested types, required fields, versions, checksum structures, a positive
  artifact, and malformed/tampered negatives. A key-set comparison is not proof.
- Execute real migration artifacts on temporary databases to validate order,
  checksum, rollback, and idempotence behavior.
- Exercise the bundled fixture through the production F07 loader/authority path;
  reject external, altered, and forged fixtures.
- Read the actual `artifacts/f0/sbom.cdx.json` and `uv.lock`. For every direct
  dependency reconcile normalized name and exact resolved version, detecting
  missing, duplicate, stale, and mismatched components. Fix SBOM generation or
  make validation fail truthfully; do not hard-code today's mismatch list.
- Consume the already accepted F04 result structurally: expected probe IDs,
  explicit pass/verdict, and probe-specific evidence semantics. Non-empty text or
  a status label alone is insufficient. Do not reopen F04 without a regression.

Required tests: validator filesystem immutability; production JSON Schema
positive; malformed artifact negative; migration behavioral failure/rollback;
forged fixture rejection and bundled success; injected SBOM version drift.

## F09 — provenance preservation and Windows handle boundary

- Preserve the accepted endpoint existence, canonical relation,
  contradiction/supersession, and deterministic digest behavior.
- Route `read_bytes`, `write_bytes`, `read_text`, `write_text`, `delete`, and
  atomic write/replace through one hardened boundary; leave no legacy pathname
  bypass.
- On Windows, use the minimum documented Win32 handle primitives required to
  open the base/relevant parent/object without following unexpected reparse
  points, inspect reparse attributes, obtain final identity/path from the actual
  handles, and verify containment. Perform I/O through verified handles. Do not
  treat `realpath/check → later pathname open` or `fstat + pathname realpath` as
  handle-bound verification.
- Make write/replace/delete fail closed if the verified parent/object changes or
  cannot be proven. Keep non-Windows behavior small and do not build a generic
  framework.
- Add a deterministic Windows-capable reparse/swap harness plus positive
  contained read/write/delete tests. The only security-property test may not
  silently skip. If local privileges prevent a real junction/reparse exercise,
  separately report `implemented` and `runtime_verified`, run the strongest
  deterministic handle-API harness, and leave the Windows profile blocked rather
  than claiming PASS.

Required tests: traversal and junction/reparse redirect rejection; deterministic
swap between validation and operation; every legacy API uses the hardened path;
positive contained read/write/text/delete/atomic replace; actual handle identity
and parent containment; no silent skip of the Windows invariant.

## Work and test strategy

Fix the current production paths; do not satisfy this prompt with source-string
assertions or mocks that never cross the real boundary. Use one focused test for
each named failure and parameterize repeated schema cases. Do not chase coverage
percentage or unrelated Ruff/mypy cleanup. Correct security/correctness typing
and lint in changed/high-risk modules; document cosmetic or known-safe limits.

Run owning tests while iterating. Only after all five findings pass locally, run
the canonical E00 gate once from the repository root:

```powershell
uv sync --frozen --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run coverage run -m pytest -q
uv run coverage report
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python -m psyche_os doctor --json
uv run python -m psyche_os gate status --json
uv run pytest -q tests/integration/test_e00_portability_smoke.py
python scripts/dev/validate_orchestration.py
python scripts/validate_research_foundation.py
git diff --check
git status --short
```

Create `tests/integration/test_e00_portability_smoke.py` only if no equivalent
production-code smoke already exists. It must use temporary synthetic data and
prove encrypted backup/export, wrong-key rejection, isolated restore, and
semantic equality. Coverage is diagnostic, not a target.

## Handoff

Update `docs/development/reports/E00.md` with exact commands, results, platform,
skips, limitations, and remaining Critical/High findings. Leave:

- `E00 = IMPLEMENTED / REVIEW_REQUIRED`;
- `E01 = PLANNED`, prompt `null`;
- `accepted_epics = []` and `git.accepted_commit = null`;
- `REAL_DATA_GATE = CLOSED`.

Do not accept E00, commit an accepted epic, prepare E01/E02+, push, or claim the
Windows profile verified when its invariant was not executed. End by requesting
one independent bounded Codex closure review of these five findings.
