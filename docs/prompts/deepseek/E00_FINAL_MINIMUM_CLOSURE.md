# PSYCHE OS — E00 final minimum closure

Work in `C:\Dev\psyche-os`. Make one bounded implementation pass against
`docs/development/E00_REBASELINE_DECISION.md`. Use synthetic fixtures only and
keep `REAL_DATA_GATE = CLOSED`.

Do not repair F02 backup/restore, F05 blob lifecycle, F09 Windows filesystem
hardening, or release-grade SBOM depth here. Do not revisit F01/F03/F04/F06,
redesign architecture, run a broad audit, clean unrelated Ruff/mypy findings,
start E01, commit, or push.

## 1. Minimal transactional migrations

**Current defect:** migration SQL is embedded and executed with naïve semicolon
splitting; atomic schema/bookkeeping rollback is unproved.

**Implement:** one explicit ordered/checksummed migration artifact and an
explicit transaction that applies statements without string splitting, validates
the result, and records the migration in the same commit. Keep the current
corrected stable/version identity and subtype-preserving behavior.

**Proof:** normal apply and rerun succeed; altered checksum/order fails closed;
an injected failure after a schema statement leaves both schema and migration
bookkeeping unchanged.

## 2. Synthetic-only storage write boundary

**Current defect:** direct UoW writes succeed without fixture authority, while
callable authority factories exist and no production bundled-fixture loader owns
the authorized path.

**Implement:** reject ordinary content mutation in the actual UoW before SQL or
filesystem side effects. Add one package-owned loader that reads only bundled
resources, validates manifest/schema/`synthetic_fixture=true`/digest, and invokes
the authorized mutation internally. Do not expose authority/factory objects to
ordinary callers and do not claim protection from arbitrary code execution in an
already-compromised trusted Python process.

**Proof:** direct UoW mutation and altered/unknown fixture fail with zero row/file
change; the bundled fixture succeeds through the package loader; CLI output is
truthful and the gate remains closed.

## 3. Truthful E00 validation and deferred-surface lock

**Current defect:** validators can claim schema/evidence success without applying
the shipped schema to the actual emitted artifact. Deferred unsafe features are
still exposed and can be mistaken for accepted E00 capability.

**Implement:** validate actual production-emitted in-scope artifacts with the
shipped JSON Schema; malformed output and placeholder/ambiguous evidence fail;
validation remains read-only. Backup/restore, blob writes, and affected Windows
filesystem mutations must be absent or return typed
`FEATURE_DEFERRED_PRE_REAL_DATA` before mutation. Validators must report these
features `DEFERRED/NOT_READY`, never `PASS`. Keep open logical export distinct
from deferred backup. Do not expand SBOM checks in this pass.

**Proof:** valid emitted in-scope artifact passes; a schema-invalid artifact and
fake evidence fail; read-only inputs remain unchanged; each deferred operation
fails with no DB/file mutation and cannot be reported ready.

Add only the demonstrated cases above to
`tests/integration/test_e00_rebaseline_gate.py`; retain the focused existing
version/storage regressions. Iterate with targeted tests, then run this gate once:

```powershell
uv run pytest -q tests/unit/test_versions.py tests/integration/test_storage_integration.py tests/integration/test_e00_rebaseline_gate.py
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
python scripts/dev/validate_orchestration.py
```

If all four commands pass, update the E00 implementation report and set the
state to `IMPLEMENTED / REVIEW_REQUIRED`; Codex alone may accept E00. If any
named invariant fails, keep `FIX_REQUIRED` and report the exact blocker. Do not
run a global test/audit gate or prepare E01.
