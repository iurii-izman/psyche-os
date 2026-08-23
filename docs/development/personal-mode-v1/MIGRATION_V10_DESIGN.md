# V10 SQLite-safe reflection rebuild

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW**. Design ID: `PMV1-V10-SQLITE-GENERALIZED-REBUILD`.

## Falsified prior sequence

Disposable synthetic probe, run with the repository runtime (`sqlite3` **3.49.1**), created one `reflection_sessions` row, two turns, exploration state, one action plan and one outcome, with `PRAGMA foreign_keys=ON`. Before: `sessions=1, turns=2, explorations=1, plans=1, outcomes=1`; child FKs targeted `reflection_sessions`. After the old parent rename, each child FK targeted `reflection_sessions_v9_old`. After old-table drop: `sessions=1, turns=0, explorations=0, plans=0, outcomes=0`; `foreign_key_check=[]`. The former V10 sequence is therefore **REJECTED**: clean FK check did not detect the cascaded data loss.

## Selected exact procedure

Before any transaction: exclusively quiesce the application/writer; verify recognized V9 inventory/checksum, `integrity_check=ok`, `foreign_key_check=[]`, no pending deletion, capacity, and verified backup/export. Do `PRAGMA foreign_keys=OFF` **outside a transaction** and verify it returns 0. The Migrator must own a V10-special prelude and epilogue; generic per-migration transaction ownership cannot toggle that pragma after its `BEGIN IMMEDIATE`.

1. `BEGIN IMMEDIATE`.
2. Create `reflection_sessions_v10_new` with the V6 columns and `CHECK(data_mode IN ('synthetic_only','real_personal'))`.
3. Copy all explicit V6 columns. Require source/new counts equal, exact content equality, and every copied value `synthetic_only`.
4. Drop `reflection_sessions` while FK enforcement is off.
5. Rename `reflection_sessions_v10_new` to `reflection_sessions`; recreate `idx_reflection_sessions_updated` and every table-local trigger/index recorded in the V10 inventory.
6. Verify the full inventory, copied rows, required indexes, and `PRAGMA foreign_key_list` targets while still in the transaction. Insert the V10 migration record. Commit.
7. Re-enable `PRAGMA foreign_keys=ON` outside a transaction; require `foreign_key_check=[]`, integrity check, and a reopening test before activation. Any failure means the candidate is not used and a verified pre-migration backup is restored to an isolated target.

No `writable_schema`, `legacy_alter_table`, SQL-text edits, or parent rename is allowed. A process crash before commit rolls back. Post-commit FK failure is an activation failure, not a repair-on-live-data opportunity. A recorded V10 skips the second apply.

## Selected-procedure proof

The same disposable fixture used steps 1–7. After rebuild: `sessions=1, turns=2, explorations=1, plans=1, outcomes=1`; all inspected child FK targets were `reflection_sessions`; `foreign_key_check=[]`. Deleting the rebuilt parent then cascaded to `0` for every descendant. This proves descendant survival and post-migration cascade semantics on the actual runtime, not documentation alone. Future candidate tests additionally cover full V7/V8/V9 graph, content/index inventory, fault points, no-op second apply, and 0→10.
