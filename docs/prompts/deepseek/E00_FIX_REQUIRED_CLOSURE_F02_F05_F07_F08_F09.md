# PSYCHE OS — E00 exact remaining closure fixes

Work in `C:\Dev\psyche-os`. Fix only the concrete remaining mechanisms below in
F02, F05, F07, F08, and F09. Preserve the already-correct portions of those
findings. Do not revisit F01/F03/F04/F06, research, or architecture. Use only
synthetic fixtures; keep `REAL_DATA_GATE = CLOSED`; do not start E01.

## F02

- After AEAD decryption require `set(all_rows) == F0_BACKUP_INVENTORY`—do not use
  `.get(table, [])` to turn an omitted payload table into an empty table. Recompute
  every table checksum/count and total from the exact decrypted set and compare
  all authenticated manifest fields.
- During restore, every expected target table/schema inspection must succeed;
  missing tables or inspection errors fail before mutation.
- Restore into an explicit isolated staging database/transaction. Validate the
  full schema, foreign keys, checksums, counts, blobs, and invariants before one
  activation. An injected failure must leave the original target byte/state
  unchanged, including under autocommit-prone connection settings.
- Add only these missing tests: authenticated payload with an omitted table;
  absent target table whose backup rows are empty; injected failure after at
  least one insert; complete encrypted round trip with semantic equality. Retain
  the passing downgrade, wrong-key, manifest-tamper, checksum, and nonempty-target
  tests.

## F05

- Replace embedded `_migration_v1()` SQL and naïve semicolon splitting with one
  small explicit ordered/checksummed migration artifact and explicit transaction
  execution. Injected DDL or bookkeeping failure must roll back schema and the
  migration row; prove order, checksum, idempotence, and rollback behaviorally.
- Make the real blob UoW execute and verify `CREATED → STORED → VERIFIED` before
  related semantic commit can succeed. A returned successful UoW must never leave
  the new blob at `created` or `stored`.
- Persist and reload vault ID plus every envelope/AAD field and verify the
  non-empty vault-keyed digest. `verify_blob()` must use that persisted context,
  reject missing digest/cross-vault use, and successfully verify a just-written
  same-vault blob.
- Retain the corrected version schemas, active indexes, column allowlists, and
  `dataclasses.replace()` behavior. Add only migration fault and real blob-path
  tests. Resolve the remaining backup/export `B905` strict-zip diagnostic and
  make blob transition tables immutable or otherwise non-mutable by callers.

## F07

- Implement a real package-owned bundled fixture loader. It verifies an
  allowlisted package-resource manifest, schema/version, synthetic marker,
  fixture identity, and digest; it consumes authority internally and does not
  return authority/capability to ordinary callers.
- Remove ordinary supported access to mint/factory methods from
  `application.ports`; an underscored public classmethod is not the loader.
  Uninitialized/forged/copied/deserialized objects remain invalid.
- Add an authority requirement to the actual UoW/storage record and blob mutation
  boundary and validate it before any SQL/filesystem call. Direct UoW without
  loader authority must fail with database bytes/row counts unchanged.
- Prove altered/external fixture rejection, bundled fixture success through the
  production loader/storage path, and truthful CLI state including verified
  `vault init`. Make fixture allowlists/authority state immutable to ordinary
  callers.

This control need not claim protection after arbitrary execution or memory/code
replacement inside the already-compromised trusted process.

## F08

- Use a real local JSON Schema implementation to validate representative
  production backup and export instances against the shipped schemas. Reconcile
  the current schema/emitter mismatch (`magic`, `records`, format version, and
  checksum value shape) instead of comparing key sets. Add malformed-instance
  negatives.
- Run the F05 migration artifact behaviorally on temporary databases and the F07
  fixture through its real loader/authority/storage path; reject forged/external
  fixtures.
- Retain actual CycloneDX/`uv.lock` reconciliation, but detect duplicates and
  prove stale/missing/mismatched direct dependency failures using temporary
  inputs—not repository mutation or hard-coded package cases.
- Validate F04 structurally by expected probe IDs/verdicts and probe-specific
  evidence semantics, not only non-empty string length.
- Keep validators read-only and prove relevant repository content/metadata is
  unchanged. Exclude `.venv`, `.mypy_cache`, generated caches, and auxiliary
  worktrees from `validate_research_foundation.py`; do not weaken checks on
  repository-owned artifacts.
- Make the canonical mypy invocation deterministic (for example, package-base
  configuration and a scoped/justified sqlcipher stub policy) so it does not fail
  on duplicate script discovery or untyped third-party imports while still
  checking security-critical code.

## F09

- Hold and validate the base/relevant parent through actual Windows handles.
  Reparse attribute/tag or handle-open errors must fail closed.
- Perform atomic replace and delete through the verified handle/parent boundary;
  do not close the verified handle and then call `os.replace`, `Path.unlink`, or
  `Path.rmdir` on a re-opened pathname. Keep all public read/write/text/delete
  APIs routed through this single boundary.
- Add a deterministic production-code harness that swaps/reparse-redirects the
  parent/target between validation and mutation and proves rejection plus
  unchanged outside files. Retain positive contained read/write/text/delete.
  Source-string assertions are not proof. If the supported Windows runtime test
  cannot execute, keep the profile blocked rather than claiming F09 PASS.

Do not build a generic filesystem framework or claim protection against
Administrator/SYSTEM, hostile kernel/drivers, or arbitrary trusted-process code
execution.

## Validation and handoff

Run focused owning tests while working. When all five findings pass, run the
canonical E00 gate once exactly as frozen in
`docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`, including formatter, Ruff,
mypy, full pytest/coverage diagnostics, F0 validators, doctor/gate JSON,
portability smoke, orchestration, research-foundation validation, and
`git diff --check`. Do not chase a coverage percentage.

Leave `E00 = IMPLEMENTED / REVIEW_REQUIRED`, `E01 = PLANNED`, accepted commit
null, and `REAL_DATA_GATE = CLOSED`. Do not accept, commit, push, or prepare E01;
request one bounded Codex closure review.
