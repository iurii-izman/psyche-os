# E00 architectural rebaseline decision

**Date:** 2026-08-11
**Status:** `APPROVED`
**Decision:** `ADR-021`
**REAL_DATA_GATE:** `CLOSED`

## Why E00 was rebaselined

Repeated repair rounds treated every security control needed before real
psychological data as if it also had to block the next synthetic-only epic.
That made E00 unbounded. The master specification itself distinguishes
irreversible/high-cost semantics in §24.1 from important but migratable controls
required for the real-data gate in §24.2. This decision changes epic allocation;
it does not lower severity, authorize real data, or claim deferred code is safe.

The latest independent evidence is
`docs/implementation/E00_ACCEPTANCE_REPORT.md`. Implementer labels such as
`REPAIRED` are not acceptance evidence.

## Severity and blocking stage

Severity describes impact if the affected capability/profile is used.
`blocking_stage` describes the latest milestone at which the defect must be
closed. They are independent:

- `E00`: must be correct before later code can build on the synthetic core;
- `PRE_REAL_DATA`: synthetic development may continue, but the affected feature
  stays unavailable and the real-data gate cannot open;
- `RELEASE_HARDENING`: required for the release/profile evidence package, not
  for the synthetic canonical foundation.

## Final classification

| Subfinding | Severity | Blocking stage | Current decision | Assigned epic |
|---|---|---|---|---|
| F02 authenticated backup completeness | High | `PRE_REAL_DATA` | `DISABLE_AND_DEFER`; do not claim backup readiness | E01 |
| F02 atomic isolated restore | High | `PRE_REAL_DATA` | `DISABLE_AND_DEFER`; restore cannot activate or mutate a vault | E01 |
| F05 stable identity/version identity, history, one active version, subtype-preserving transition | High | `E00` | Corrected by the last repair; retain focused regression proof | E00 |
| F05 minimal schema migrations | High | `E00` | `FIX_NOW`: explicit order, checksum, transaction, rollback and consistent bookkeeping | E00 |
| F05 blob lifecycle and vault-bound verification | High | `PRE_REAL_DATA` | `DISABLE_AND_DEFER`; no accepted blob write surface | E01 |
| F07 synthetic authorization at the storage/UoW boundary | High | `E00` | `FIX_NOW`: ordinary mutation rejected before side effects; one package-owned verified fixture path | E00 |
| F08 truthful E00 validator and evidence semantics | High | `E00` | `FIX_NOW`: validate actual in-scope output and reject fake/label-only evidence | E00 |
| F08 exact SBOM reconciliation and release supply-chain depth | High for an enabled real-data/release profile | `PRE_REAL_DATA` | Keep RDG-09 unsatisfied; complete release-grade evidence in E11 | E11 |
| F09 Windows reparse/TOCTOU mutation boundary | High | `PRE_REAL_DATA` | `DISABLE_AND_DEFER`; preserve `runtime_not_verified` and expose no affected mutation path | E01 |
| Unrelated Ruff/mypy/style/package polish | As individually assessed | `RELEASE_HARDENING` | Does not block E00 unless a diagnostic violates an invariant listed below | owning later epic/E11 |

F02, deferred F05 blob work, and F09 remain open High findings. Their affected
features are not part of the accepted E00 profile, so they do not become an
“unresolved High in the reviewed E00 profile.” They remain explicit blockers for
the profiles that would enable them and for `REAL_DATA_GATE`.

## Frozen E00 acceptance boundary

E00 is acceptable only when all of these are true:

1. Canonical IDs, row/version identity, immutable history, exactly one active
   version, subtype-preserving correction, provenance, temporal, policy,
   deletion and encryption invariants previously closed in F01/F03/F04/F06 and
   the corrected F05 versioning path remain intact.
2. The small migration mechanism is explicit, ordered and checksummed; schema
   change plus bookkeeping are transactional; an injected failure rolls both
   back; rerun is deterministic/idempotent.
3. With the real-data gate closed, direct application/storage/UoW content writes
   are rejected before SQL or filesystem mutation. The sole successful content
   write is a package-owned loader for a bundled, digest-verified,
   schema-validated synthetic fixture.
4. E00 validators inspect actual production-emitted artifacts in the accepted
   scope, apply the shipped JSON Schema whenever they claim schema validity,
   reject malformed artifacts and structurally invalid evidence, and are
   read-only.
5. Backup/restore, blob writes, and affected Windows filesystem mutations return
   an explicit `FEATURE_DEFERRED_PRE_REAL_DATA` (or are absent from the command
   surface) without mutation. E00 validation reports them `DEFERRED/NOT_READY`;
   it must never report them `PASS`.
6. `REAL_DATA_GATE` remains `CLOSED`, no arbitrary or real input is accepted,
   and no documentation or CLI output claims production/real-data readiness.

The rebaselined E00 gate is exactly:

```powershell
uv run pytest -q tests/unit/test_versions.py tests/integration/test_storage_integration.py tests/integration/test_e00_rebaseline_gate.py
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
python scripts/dev/validate_orchestration.py
```

The two F0 validators must implement the rebaselined profile above: deferred
features are checked for unavailability and reported as deferred, not tested for
readiness or silently omitted. The final four-command gate runs once after
targeted iteration passes.

## PRE_REAL_DATA blockers

- E01 must complete and independently attack authenticated encrypted backup,
  exact inventory, clean isolated atomic restore and recovery/fault behavior
  before RDG-03 can pass.
- E01 must either complete the blob lifecycle and vault-bound integrity protocol
  or keep blobs disabled for the candidate profile before RDG-01 can pass.
- E01 must close the Windows handle/reparse/TOCTOU mutation boundary on the exact
  supported Windows profile before affected filesystem capabilities can be
  enabled or RDG-06/RDG-10 can pass.
- E11 must assemble truthful dependency/SBOM/license/build provenance evidence
  before RDG-09 can pass.

E11 remains the only epic that may prepare an explicit signed open/keep-closed
decision. None of the assignments above opens the gate automatically.

## Disabled and deferred capabilities

- encrypted backup creation/verification and restore activation;
- blob/object attachment writes and lifecycle verification;
- the affected general Windows filesystem mutation adapter;
- production/real-data readiness claims for those capabilities;
- release-grade SBOM attestation beyond truthful E00 dependency evidence.

Open logical export already closed under F01 remains in the synthetic E00
surface; it must not be conflated with disabled backup/restore.

## Compatibility and migration impact

No accepted E00 data or schema exists, and only disposable bundled synthetic
fixtures are authorized. Feature subtraction therefore requires no user-data
migration. The public/application result for a deferred operation must be a
stable typed error so E01 can replace it without callers depending on unsafe
behavior. Canonical version and migration semantics cannot be weakened by this
deferral.

## Stop rule

After the final minimum closure is accepted, E00 may reopen only when concrete
evidence demonstrates a violation of one of the six frozen E00 invariants above.
New hardening ideas, deferred-feature defects, release hygiene, or findings in a
future trust boundary keep their severity but go to `PRE_REAL_DATA`, the owning
later epic, or release hardening. “More improvements are possible” is not an E00
reopening condition.
