# PSYCHE OS — E01 BOUNDED REPAIR

**Project root:** `C:\Dev\psyche-os`  
**Accepted baseline:** `0090ba0`  
**Epic:** E01 only  
**REAL_DATA_GATE:** `CLOSED`

## Outcome

Repair only the material gaps confirmed by the Codex E01 bounded acceptance
review. Do not reopen E00, research, blob/general-filesystem capability, or
prepare E02. Preserve every accepted E00 invariant and all unrelated changes.

## Read first

- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/prompts/deepseek/E01_SYNTHETIC_ASSURANCE_RECOVERY.md`
- `docs/development/reports/E01.md`, especially the Codex bounded-review section
- `artifacts/e01/evidence_index.json`
- the current E01 diff from `0090ba0`

## Confirmed blockers to repair

### 1. Backup is not yet a fail-closed complete snapshot

In `backup_export/operations.py`, transaction acquisition currently catches
`BEGIN IMMEDIATE` failure and continues, active-row filtering omits preserved
inactive history, and output uses a pathname `exists` check followed by
`open(..., "w")`. Replace this with one supported consistent SQLCipher snapshot
that fails closed if it cannot be obtained. Back up the complete authoritative
V1 database inventory required for exact recovery, including preserved
correction/supersession/deletion and migration evidence; explicitly justify any
bookkeeping exclusion. Missing, extra, duplicate or unreadable inventory must
fail. Write only the already encrypted/authenticated package through the scoped
package store with exclusive no-overwrite semantics; no plaintext staging file.

### 2. Restore and activation are not isolated/atomic

`restore_backup()` must not restore into a caller-supplied populated or active
connection. It must create a new explicit isolated SQLCipher target, restore in
one rollback-safe transaction, and validate cipher integrity, schema/migration
checksums, foreign keys, exact inventory/counts/checksums, canonical/version/
policy/provenance/deletion invariants and semantic equality before it can become
an activation candidate. Activation must be a separate operation that atomically
replaces the active vault while retaining the previous vault on every failure.
Maintain a trusted per-vault sequence floor so stale/rollback packages fail
before activation.

Add deterministic fault hooks/tests after staging, after at least one restore
write, during migration/validation, and immediately before activation. For each
hook, byte-compare the active vault before/after and prove it is unchanged.
Also prove wrong key/recovery material, bit flip, downgrade, manifest/payload
swap, missing/extra table, populated target and target-inspection error fail
before activation.

### 3. Independent recovery is not integrated

The recovery drill currently retains the raw VMK and derives the same backup
key again; that is not the promised independent recovery path. Integrate the
accepted Argon2id recovery wrap/unwrap path so recovery succeeds in a clean
process using only the encrypted package plus independent recovery material,
with the OS convenience wrapper unavailable. Do not store raw VMK, backup key,
secret or recovery material in the package, evidence, logs or reports.

### 4. Enabled Windows boundary is not proven and contains fail-open paths

The production backup path must actually use `BackupPackageStore`. On Windows,
an empty/failed/ambiguous final-path result must raise, never return success.
Hold and verify the relevant directory/file handles across creation,
no-overwrite publication, replacement and activation; do not verify a pathname,
close the handle and then mutate by pathname. Add deterministic non-admin
swap/reparse/open-ambiguity tests against the production path plus an exact
runtime test that asserts and records the enabled Windows profile. A skip or
source inspection is `BLOCKED`, not PASS. Keep general filesystem mutation and
all blob writes deferred.

### 5. Evidence validator currently accepts placeholder evidence

`artifacts/e01/evidence_index.json` currently has empty timestamps/expiry,
empty artifact digests and `PENDING` evidence, yet
`validate_e01_assurance.py` reports PASS. Make the read-only validator reject
missing, empty, placeholder, expired, `PENDING`, unverifiable or mismatched
evidence. Generate reproducible records from actual commands/artifacts with
relative paths, SHA-256 digests, platform/profile, exact test node IDs and
PASS/FAIL/BLOCKED states. Do not self-award independent review. Preserve human
review placeholders as pending without allowing them to count as acceptance.

## Baseline F07 classification

The three F07 failures were independently reproduced on `0090ba0`. They used
short fake digests (`abc123`/`xyz789`) rejected by the accepted 64-hex SHA-256
authority invariant. The test fixtures have been corrected to valid synthetic
64-hex values. Do not weaken `FixtureAuthority`, change its validation rule, or
count these baseline fixture failures as an E01 regression.

## Required validation

Iterate only on affected tests. Before reporting completion, run the canonical
E01 gate exactly once:

```powershell
uv sync --frozen
uv run pytest -q
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python scripts/validate_e01_assurance.py
python scripts/dev/validate_orchestration.py
```

No skipped Windows, recovery or atomicity proof may count as PASS. Record exact
commands, counts, skips and failures in `docs/development/reports/E01.md`. Keep
`REAL_DATA_GATE` closed and every RDG requirement unsatisfied. Leave
`current_epic.status: IMPLEMENTED` with Codex review required; do not set
`ACCEPTED`, append E01 to accepted history, commit, or prepare E02.

