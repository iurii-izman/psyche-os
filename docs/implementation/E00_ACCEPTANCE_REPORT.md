# E00 final acceptance report after rebaseline

**Review date:** 2026-08-11
**Verdict:** `ACCEPTED`
**Boundary:** ADR-021 / `docs/development/E00_REBASELINE_DECISION.md`
**REAL_DATA_GATE:** `CLOSED`

## Frozen E00 evidence

| Invariant | Result | Production-path evidence |
|---|---|---|
| F05 minimal migrations | **PASS** | V1 is a deterministic ordered sequence with a frozen SHA-256 checksum. The migrator validates registry order/label/checksum before DDL, opens one explicit transaction, executes one complete statement at a time without `executescript`, and records bookkeeping in that transaction. Clean apply, idempotent rerun, checksum drift, separate-statement failure, script-like multi-statement failure and clean-database bookkeeping rollback are covered. |
| F07 synthetic-only boundary | **PASS** | UoW rejects ordinary writes before obtaining a cursor. Authority validation requires the internal concrete authority shape plus a fixture identity and SHA-256 digest. The package-owned loader accepts only allowlisted bundled resources and validates manifest/schema version, synthetic marker, table inventory, row shape and digest before an internal authorized write. Direct writes and altered/unknown/incompatible fixtures fail without mutation; the bundled fixture persists expected synthetic rows. |
| F08 truthful validation | **PASS** | The artifact validator applies the shipped Draft 2020-12 schema to the actual `ExportManifest` emitter through `jsonschema`; malformed instances fail and validation is read-only. SQLCipher probe evidence is checked with probe-specific structures rather than non-empty labels. Backup compatibility and release-grade evidence are explicitly `DEFERRED_NOT_READY`, not certified. |
| Deferred surfaces locked | **PASS** | Backup builder/verifier/restore, blob writes and filesystem mutations fail with `FEATURE_DEFERRED_PRE_REAL_DATA` before mutation. CLI backup/restore reports the same typed deferred state. Logical export remains distinct and in scope. |

The final review found and fixed two local frozen-boundary defects before
acceptance: `executescript()` could implicitly commit partial migration DDL, and
the artifact validator compared keys without applying JSON Schema. One existing
integration fixture was updated to use a valid SHA-256 authority digest. No
deferred subsystem was completed or declared production-ready.

## Canonical rebaselined E00 gate

```text
uv run pytest -q tests/unit/test_versions.py tests/integration/test_storage_integration.py tests/integration/test_e00_rebaseline_gate.py
48 passed in 8.16s

uv run python scripts/validate_f0_scope.py
PASS (6/6 checks)

uv run python scripts/validate_f0_artifacts.py
PASS (4/4 checks)

python scripts/dev/validate_orchestration.py
118 passed, 0 failed
```

No coverage target, broad audit, research rerun, unrelated Ruff/mypy cleanup or
PRE_REAL_DATA implementation was part of this acceptance.

## Preserved PRE_REAL_DATA blockers

| Finding | Severity | State | Owner |
|---|---|---|---|
| F02 authenticated backup completeness and atomic isolated restore | High | `UNSATISFIED / DISABLED_DEFERRED` | E01 |
| F05 blob lifecycle and vault-bound verification | High | `UNSATISFIED / DISABLED_DEFERRED` | E01 |
| F09 Windows reparse/TOCTOU filesystem mutation | High | `UNSATISFIED_RUNTIME_NOT_VERIFIED / DISABLED_DEFERRED` | E01 |
| F08 release-grade dependency/SBOM/license/build provenance | High for enabled release profile | `UNSATISFIED / EVIDENCE_DEFERRED` | E11 |

These remain recorded in `docs/architecture/REAL_DATA_GATE.yaml`. Acceptance of
the synthetic E00 profile neither resolves them nor permits real personal data.

## Decision

E00 satisfies the finite boundary frozen by ADR-021 and is `ACCEPTED`. The E00
review stops here. It may reopen only on concrete evidence that an explicitly
accepted E00 invariant is violated. E01 may be prepared just in time for
synthetic-only work; `REAL_DATA_GATE` remains `CLOSED`.
