# V10 data-mode migration design

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW; implementation human-gated.** Design ID: `PMV1-V10-REFLECTION-DATA-MODE-REBUILD`.

## Selection

Select **Option A: transactional rebuild of `reflection_sessions` in the common V10 database**. Add `10: personal_mode_data_mode_v10` to `SCHEMA_VERSIONS`, set `LATEST_SCHEMA_VERSION = 10`, add `src/psyche_os/storage/personal_mode_v10_schema.py`, import its `V10_MIGRATION_{STATEMENTS,CHECKSUM}` in `migrations.py`, and register `Migration(version=10, label="personal_mode_data_mode_v10", ...)`. Callers that intentionally request V9 remain V9; Personal admission explicitly requests V10 only after gate admission and migration preflight.

Option B duplicates workspace semantics and deletion/search/backup contracts. Option C creates two incompatible stores and leaves canonical inventory/recovery ambiguous. Both are rejected. Existing Synthetic V9 workspaces **migrate to V10 only through the explicit verified migration flow**; every copied row remains `synthetic_only` forever.

## SQL transaction

The exact migration statement list is checksum-bound and executes inside the existing `BEGIN IMMEDIATE` transaction, with `PRAGMA foreign_keys=ON` verified before start (never turned off):

1. `CREATE TABLE reflection_sessions_v10_new` with the V6 columns and exact `data_mode TEXT NOT NULL CHECK(data_mode IN ('synthetic_only','real_personal'))`.
2. `INSERT INTO reflection_sessions_v10_new (all columns) SELECT (all columns) FROM reflection_sessions WHERE data_mode='synthetic_only';` Then require source/new row counts equal and reject any non-synthetic source value.
3. Run `PRAGMA foreign_key_check`; recreate `idx_reflection_sessions_updated` on the new table.
4. Rename old `reflection_sessions` to `reflection_sessions_v9_old`; rename new table to `reflection_sessions`; recreate/verify the index; run `foreign_key_check` and content/count checks; drop only `reflection_sessions_v9_old` immediately before the transaction’s migration record and commit.

SQLite’s supported table-rebuild technique may require dependent foreign keys to reference the renamed table during the operation. The implementer must prove this exact sequence against V9 fixtures with `foreign_keys=ON`; if SQLite cannot preserve those references without disabling it, this design is blocked and must return for architecture review rather than use `PRAGMA foreign_keys=OFF`.

## Preconditions and failure semantics

Mandatory: exact recognized V9 checksum/inventory; `integrity_check=ok`; empty pending deletion state; `foreign_key_check` clean; exclusive writer lock; verified encrypted backup and verified open export; sufficient free staging capacity (at least DB size plus WAL and rebuild headroom); no Personal gate opening. The migration captures those checks before `BEGIN IMMEDIATE`.

Create/copy/index/rename/drop/record failures, process crash, I/O error, or disk full roll back the single transaction to the valid V9 database. A crash after commit leaves a valid V10 database and migration record. No intermediate state activates. The record makes reruns idempotent: current V10 is skipped, and partial work has rolled back. Downgrade is deliberately unsupported; restore the verified pre-migration backup into an isolated target.

## Required future tests

Synthetic V9 fixture: exact inventory/checksum, surviving sessions/turns/exploration/actions, no value reinterpretation; double apply; each precondition denial; injected failure at each step; `integrity_check`/`foreign_key_check`; V10 backup/restore/export round trip; and direct attempted `real_personal` insert denied while gate/profile admission is closed.
