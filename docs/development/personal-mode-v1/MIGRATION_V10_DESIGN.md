# V10 SQLite-safe reflection rebuild

Status: **ACCEPTED**. Design ID: `PMV1-V10-SQLITE-GENERALIZED-REBUILD`. The
accepted bounded amendment is `PMV1-V10-POLICY-IDENTITY-REPAIR-A1`; its active
owner authorization is recorded in [IMPLEMENTATION_AUTHORIZATION.md](IMPLEMENTATION_AUTHORIZATION.md).

## Approved bounded amendment: policy identity repair

Owner decision `PMV1-V10-POLICY-IDENTITY-REPAIR-A1` (2026-08-24) is part of
V10, not a V11. `DataPolicy` remains a versioned semantic record with stable
`policy_id`, stable canonical `record_id`, and many immutable `version_id`
rows. V10 creates the non-versioned, system-owned registry
`policy_identities(policy_id PRIMARY KEY, record_id UNIQUE NOT NULL,
UNIQUE(record_id, policy_id))`. Rebuilt `data_policies` retains
`PRIMARY KEY(record_id, version_id)` and adds a composite foreign key from
`(record_id, policy_id)` to that exact registry pair; `policy_id` is not unique
on version rows. Rebuilt `policy_lineage` remains policy-identity lineage and
its endpoints reference `policy_identities(policy_id)`.

Before mutation, V10 recognizes only the exact known V9 schema and checks
schema-migration checksum/inventory, integrity, active-version invariants, and
the bounded policy proof. It rejects `POLICY_IDENTITY_AMBIGUOUS` when either a
legacy policy_id maps to more than one record_id or a record_id maps to more
than one policy_id, and rejects unresolved lineage endpoints. It does not
catch or suppress arbitrary foreign-key errors. This bounded preflight replaces
only the impossible V9 global `foreign_key_check`, whose two malformed lineage
FKs target non-unique `data_policies(policy_id)`. After V10 commits, foreign
keys are enabled and global `foreign_key_check=[]` plus `integrity_check=ok`
remain mandatory.

## Falsified prior sequence

Disposable synthetic probe, run with the repository runtime (`sqlite3` **3.49.1**), created one `reflection_sessions` row, two turns, exploration state, one action plan and one outcome, with `PRAGMA foreign_keys=ON`. Before: `sessions=1, turns=2, explorations=1, plans=1, outcomes=1`; child FKs targeted `reflection_sessions`. After the old parent rename, each child FK targeted `reflection_sessions_v9_old`. After old-table drop: `sessions=1, turns=0, explorations=0, plans=0, outcomes=0`; `foreign_key_check=[]`. The former V10 sequence is therefore **REJECTED**: clean FK check did not detect the cascaded data loss.

## Selected exact procedure

Before any transaction: exclusively quiesce the application/writer; verify the exact recognized V9 inventory/checksum, `integrity_check=ok`, active-version invariants, one-to-one legacy policy identity mappings, and resolved lineage endpoints, with no pending deletion, capacity, and verified backup/export. The exact malformed V9 lineage FK relationship is not passed to global `foreign_key_check`; any other structural drift fails closed. Do `PRAGMA foreign_keys=OFF` **outside a transaction** and verify it returns 0. The Migrator must own a V10-special prelude and epilogue; generic per-migration transaction ownership cannot toggle that pragma after its `BEGIN IMMEDIATE`.

1. `BEGIN IMMEDIATE`.
2. Create and backfill `policy_identities` from the proven legacy identity pairs, rebuild `data_policies` with its exact-pair foreign key, and rebuild `policy_lineage` with stable-identity endpoint foreign keys; preserve every version row and semantic payload unchanged.
3. Create `reflection_sessions_v10_new` with the V6 columns and `CHECK(data_mode IN ('synthetic_only','real_personal'))`.
4. Copy all explicit V6 columns. Require source/new counts equal, exact content equality, and every copied value `synthetic_only`.
5. Drop/rebuild only the approved V10 parent tables while FK enforcement is off; recreate required indexes and table-local triggers from the V10 inventory.
6. Verify the full inventory, copied rows, policy mapping, required indexes, and `PRAGMA foreign_key_list` targets while still in the transaction. Insert the V10 migration record. Commit.
7. Re-enable `PRAGMA foreign_keys=ON` outside a transaction; require global `foreign_key_check=[]`, integrity check, and a reopening test before activation. Any failure means the candidate is not used and a verified pre-migration backup is restored to an isolated target.

No `writable_schema`, `legacy_alter_table`, SQL-text edits, or parent rename is allowed. A process crash before commit rolls back. Post-commit FK failure is an activation failure, not a repair-on-live-data opportunity. A recorded V10 skips the second apply.

## Selected-procedure proof

The same disposable fixture used steps 1–7. After rebuild: `sessions=1, turns=2, explorations=1, plans=1, outcomes=1`; all inspected child FK targets were `reflection_sessions`; `foreign_key_check=[]`. Deleting the rebuilt parent then cascaded to `0` for every descendant. This proves descendant survival and post-migration cascade semantics on the actual runtime, not documentation alone. Future candidate tests additionally cover full V7/V8/V9 graph, content/index inventory, fault points, no-op second apply, and 0→10.
