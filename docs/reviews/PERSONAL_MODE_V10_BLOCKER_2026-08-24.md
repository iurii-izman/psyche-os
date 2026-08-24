# Personal Mode V10 implementation blocker

**Status:** `REDESIGN_REQUIRED` for the V10 migration workstream.  This is not
an acceptance decision and does not alter `REAL_DATA_GATE`, which remains
`CLOSED`.

## Exact evidence

On 2026-08-24, a fresh in-memory SQLite database was created using the
repository's V1-to-V9 migration chain with `PRAGMA foreign_keys=ON`.
`Migrator(connection).apply(9)` returned `success=True`.

The required V10 preflight from
`docs/development/personal-mode-v1/MIGRATION_V10_DESIGN.md` then cannot run:

```text
PRAGMA foreign_key_check
sqlite3.OperationalError: foreign key mismatch - "policy_lineage" referencing "data_policies"
```

The persistent schema declares:

```sql
CREATE TABLE data_policies (..., PRIMARY KEY (record_id, version_id));
CREATE TABLE policy_lineage (
  ...,
  FOREIGN KEY (parent_policy_id) REFERENCES data_policies(policy_id),
  FOREIGN KEY (child_policy_id) REFERENCES data_policies(policy_id)
);
```

`data_policies.policy_id` is not a primary key or unique key, so SQLite
rejects the FK relationship even before the accepted V10
`reflection_sessions` rebuild is attempted.

## Why this blocks the selected design

The accepted V10 procedure requires preflight `foreign_key_check=[]` and a
post-commit `foreign_key_check=[]`.  Changing the check to a narrower scope
would weaken that accepted invariant.  Repairing the unrelated
`data_policies`/`policy_lineage` relationship would require an additional
schema migration and an accepted design decision not contained in
`PMV1-V10-SQLITE-GENERALIZED-REBUILD`.

No V10 code or migration was retained after this discovery.  No real or
personal data was used.

## Required decision

Provide an accepted architecture amendment that either:

1. defines a validated repair migration for the existing malformed global FK
   relationship, including its compatibility and fault requirements; or
2. explicitly and safely redefines the V10 preflight/postflight FK invariant
   with independent review.

Until then, the V10 migration workstream must remain stopped.
