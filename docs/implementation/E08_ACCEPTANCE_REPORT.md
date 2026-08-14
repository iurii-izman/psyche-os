# E08 final high-risk bounded acceptance report

**Review date:** 2026-08-14
**Verdict:** `ACCEPTED`
**Base:** `b0bc7238964433470acc7f44756c05974d5cc917`
**Reviewed candidate:** `eef04e18bfdff6f0f0e5cae8adb076827ca6a7b8`
**Accepted E08 implementation commit:** `1e6dcd86dd226bc84ef728d643fd21db4ecc1fb9`
**Schema:** V5 `e08_untrusted_import_v5` (strictly additive)
**REAL_DATA_GATE:** `CLOSED`

## Review verdict

The mandatory independent review found eight concrete security and correctness
defects. The original process-local `E08CanonicalStore` was the actual authority,
not a test double, and therefore did not satisfy the frozen canonical storage,
restart, export, correction or deletion contract. The result was classified
`E08_CANONICAL_INTEGRATION_REQUIRED` and repaired in scope.

The accepted implementation now uses an explicit V5 connection-backed repository
and real accepted E03 records/relations. Quarantine bytes and E08 supplemental
provenance are held inside the accepted encrypted database boundary. Commit,
correction closure, governed-byte deletion, accepted-row deletion/invalidation,
verification and receipt persistence have truthful transaction boundaries.

## Finding closure

| Finding | Accepted closure |
| --- | --- |
| Shadow canonical authority | V5 repository plus accepted `source_artifacts`, `source_locators`, `reports` / `assertions` and `record_relations`; reopen and export proofs pass. |
| Parser-minted provenance | Independent application reconstruction rejects fabricated identities, counts, encoding/BOM, transformations, duplicate/overlapping/out-of-order segments and false topology. |
| BOM signature bypass | All frozen signatures are checked after recognizing the optional leading BOM; both forms reject. |
| Mutable policy label | Exact active own/parent policy versions and lineage edges are resolved, restricted to local/NEVER_CLOUD, identity-bound and re-resolved before commit. |
| Ephemeral duplicate key | A versioned vault-scoped fingerprint key is required; same-vault restart stability and cross-vault unlinkability pass. |
| False verbatim mapping | A redacted segment cannot use `ATTRIBUTED_VERBATIM_REPORT`; original bytes and transformation lineage remain distinct. |
| Filesystem/deletion atomicity | Handle/path/change-time checks reject the reproduced races; DB-backed canonical/raw deletion rolls back at A–F and verifies after reopen. |
| Diagnostic leakage | E08 repr/debug values are content-, path-, replacement- and protected/stable-digest-free. |

## Acceptance evidence

- Authoritative targeted plus bounded-review/migration suite: `151 passed`, no
  mandatory skip.
- FULL: `569 passed`, one unchanged unrelated administrator-only symlink skip.
- Frozen dependency sync, F0 scope validation and orchestration validation: PASS.
- Touched Ruff and strict mypy: PASS.
- Repository-wide static ratchet versus `b0bc7238964433470acc7f44756c05974d5cc917`:
  zero new Ruff identities and zero new mypy identities.
- V1–V4 inventories/checksums remain frozen; V5 fresh creation, V4 recovery gate,
  atomic migration, no-op rerun, logical portability and governed-byte restore pass.
- `REAL_DATA_GATE` is still `CLOSED`; E09 is still `PLANNED` and unprepared.

## Decision

No architecture deviation is required: the correction is an explicitly permitted
additive E08 schema and accepted-storage integration. E08 meets its frozen
acceptance criteria at implementation commit
`1e6dcd86dd226bc84ef728d643fd21db4ecc1fb9` and is accepted for merge preserving
candidate history.
