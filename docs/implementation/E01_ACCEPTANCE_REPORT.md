# E01 final acceptance report

**Review date:** 2026-08-13  
**Verdict:** `ACCEPTED`  
**Accepted baseline:** `0090ba0`  
**Profile:** synthetic database-only  
**REAL_DATA_GATE:** `CLOSED`

## Frozen E01 evidence

| Target | Result | Production-path evidence |
| --- | --- | --- |
| Exact fail-closed authenticated snapshot | **PASS** | `BEGIN IMMEDIATE` is mandatory; the exact unique 20-table inventory includes frozen V1 `schema_migrations`; unreadable inventory, sequence, deletion, or table state aborts; manifest, checksums, and authenticated payload inventories must agree exactly. |
| Truly isolated validated SQLCipher restore | **PASS** | Restore exclusively reserves a new candidate distinct from the active vault, restores transactionally, and verifies migration evidence, exact schema, foreign keys, canonical rows/counts, deletion state, and SQLCipher integrity before returning it. |
| Separate atomic activation | **PASS** | Validation-only mode returns `activated: false`; activation requires a scoped store, rejects candidate/active identity, retains the prior active inode, and performs one handle-relative atomic replacement without first moving the active vault away. |
| Four-phase fault preservation | **PASS** | Faults after package staging, after isolated writes, during production validation, and immediately before the atomic boundary preserve active main/WAL/SHM bytes and canonical per-table semantic digests while the active vault remains usable. |
| Independent Argon2id recovery | **PASS** | Vault initialization emits separate Argon2id recovery material. Production recovery unwraps a recovered VMK, derives backup/database keys, restores without the OS wrapper or retained original raw VMK, and rejects raw `--vmk-hex` on the recovery command. |
| Backup-specific Windows boundary | **PASS** | Windows production tests exercise fail-closed handle identity, held source/destination-parent handles, handle-relative publication/activation, reparse ambiguity, and a deterministic mid-operation target swap that cannot redirect writes outside the authority. General filesystem/blob mutation remains deferred. |
| Truthful read-only evidence validation | **PASS** | The validator performs no evidence writes and rejects missing/empty/wrong digests, missing or expired timestamps, `PENDING`/`BLOCKED`, missing artifacts, contradictory baseline/state, and mismatched on-disk evidence. All 15 claimed candidate digests matched. |

## Canonical post-fix FULL gate

```text
uv sync --frozen
PASS (13 packages audited)

uv run pytest -q
294 passed, 1 skipped in 33.67s

uv run python scripts/validate_f0_scope.py
PASS (6/6)

uv run python scripts/validate_f0_artifacts.py
PASS (4/4)

uv run python scripts/validate_e01_assurance.py
PASS (16/16; 0 FAIL; 0 BLOCKED)

python scripts/dev/validate_orchestration.py
PASS (111/111)
```

The sole skip is the unchanged accepted-baseline
`TestF09aPathEscape::test_symlink_traversal_rejected` Windows-admin symlink
case for the deferred general `FilesystemAdapter`. It is not E01
backup-specific Windows, recovery, activation, or atomicity evidence. No
mandatory E01 proof was skipped.

## Preserved boundaries and residual risks

- A package's authenticated sequence is checked against its own vault manifest
  history. No external trusted monotonic anti-rollback floor exists or is
  claimed.
- Python secret zeroization is best-effort.
- Administrator/SYSTEM, hostile kernel/filesystem drivers, and arbitrary code
  execution in the trusted process remain outside the Windows boundary.
- Blob/attachment writes, general filesystem mutation, broad imports, UI,
  network/cloud, LLM/provider features, and release signing/attestation remain
  deferred.
- Independent human cryptographic/privacy/recovery review remains required for
  any later real-data decision.

## Decision

All seven frozen targets and the current canonical FULL gate pass. E01 is
`ACCEPTED`; review stops at this boundary. New hardening opportunities do not
reopen it without concrete evidence that an accepted invariant is violated.
Exactly E02 may now be prepared just in time. `REAL_DATA_GATE` remains
`CLOSED`.
