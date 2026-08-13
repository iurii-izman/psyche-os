# PSYCHE OS — E01 FINAL TARGETED FROZEN-TARGET FIX

Work only in `C:\Dev\psyche-os`, against accepted baseline `0090ba0` and the
current E01 candidate. Keep `REAL_DATA_GATE` closed. Do not reopen E00,
research, blob/general-filesystem hardening, or E02.

Repair only the remaining frozen E01 failures confirmed in
`docs/development/reports/E01.md`.

## 1. Exact fail-closed snapshot and restore inventory

- Fail on every sequence/deletion-state read error; never authenticate a
  fallback `0` or empty digest.
- Require exact, unique and identical sets for manifest `table_inventory`,
  `table_checksums`, and decrypted payload tables. Reject every missing, extra
  or duplicate entry; never use `all_rows.get(table, [])` for required data.
- Preserve and authenticate the frozen V1 migration evidence, including
  `schema_migrations`; do not manufacture a checksum. Require the exact frozen
  schema version and call the accepted migration verifier before activation.
- Maintain and check a trusted per-vault sequence floor so stale/rollback
  packages fail before activation.

## 2. Truly isolated SQLCipher restore

- Create the restore target with exclusive, handle-bound semantics; remove the
  `exists` then later `dbapi2.connect(path)` race.
- After writes, and before returning an activation candidate, validate
  SQLCipher integrity, exact schema/migration checksums, foreign keys, exact
  inventory/counts, canonical equality, policy/provenance/deletion invariants,
  and semantic equality. A hook named `during_validation` must surround actual
  validation.

## 3. One atomic handle-bound activation

- Route verified candidate activation through the scoped backup-specific
  Windows authority. Hold verified directory/file identity through the atomic
  point; no verify-handle, close, then pathname `rename`/`replace` sequence.
- Never move the active vault away before the atomic transition. Preserve the
  prior complete persisted state, including applicable `-wal`/`-shm`, across
  failures and crashes. Do not swallow rollback/restoration failures.
- Validation-only mode must not return `activated: true`. The enabled CLI
  activation path must require and exercise a real active target.

## 4. Required persisted and semantic fault proofs

- Add deterministic tests for all four required phases: after staging, after
  at least one restore write, during real validation, and during/immediately at
  the activation atomic point.
- At every failure compare active main/WAL/SHM bytes plus canonical semantic
  content, not row counts. Prove the previous active vault remains usable and
  unchanged.

## 5. Integrated independent Argon2id recovery

- Integrate recovery-header creation into the enabled vault lifecycle and add
  the production recovery command/path. Recovery must work in a clean process
  with encrypted package plus separate recovery header/secret only, with the OS
  wrapper unavailable and no retained original VMK or raw `--vmk-hex` argv.
- Wrong recovery material must fail before restore/activation with content-free
  errors.

## 6. Actual Windows production-boundary proof

- Empty, failed or ambiguous final-handle identity must raise.
- Publication, replacement and activation must keep verified handles through
  mutation; post-mutation verification is not prevention.
- Add real deterministic non-admin reparse/junction, mid-operation swap,
  ambiguous-handle and production activation-path tests on this Windows
  profile. Sequential write/read tests are not TOCTOU simulations. No required
  Windows test may skip.

## Evidence and lifecycle

Preserve the now-strict expiry/baseline/aggregate checks in
`scripts/validate_e01_assurance.py`. Regenerate current-worktree evidence and
digests only after all production code/tests are final. The validator must
reject empty/wrong digest, missing/future/expired timestamp, PENDING, BLOCKED,
missing artifact, wrong baseline and aggregate contradictions while remaining
read-only.

The baseline-only skipped test
`TestF09aPathEscape::test_symlink_traversal_rejected` concerns the deferred
general `FilesystemAdapter`; record it separately and do not use it as E01
Windows evidence.

Run affected tests while repairing, then the canonical E01 FULL gate exactly
once. Record exact counts and every skip. Leave E01 `IMPLEMENTED`, Codex review
required, E02 unprepared, and do not commit or set `ACCEPTED`.

