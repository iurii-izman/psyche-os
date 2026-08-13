# E03 final bounded acceptance report

**Review date:** 2026-08-13
**Verdict:** `ACCEPTED`
**Base:** `91ef4826705e286d6e12cd826c24f9e4958e5057`
**Accepted E03 implementation commit:** `6721e0b00a82f808405c17ab67358ad2f51199bc`
**Profile:** Windows 11, Tauri 2 / Edge WebView2, synthetic-only
**REAL_DATA_GATE:** `CLOSED`

## Bounded review decision

| Target | Result | Production-path evidence |
| --- | --- | --- |
| T1 Canonical synthetic capture | **PASS** | The digest-bound `e03_orchid_station_v1` package and eight typed operations are the only mutation authority. Arbitrary text, paths, tables, IDs and unknown fields fail before write. Source, report, assertion and derived claim remain separate canonical types. |
| T2 Fuzzy and multi-clock time | **PASS** | Exact, interval, season/calendar and unknown values retain explicit clock, bounds, inclusivity, precision, timezone state and uncertainty. Invalid bounds fail and no fuzzy date is converted to an invented instant. |
| T3 Epistemic explorer | **PASS** | Evidence axes, multidimensional uncertainty, contradiction membership/status and unknown reasons round-trip without a truth or generic confidence score. Claims remain proposals rather than evidence or fact. |
| T4 Snapshot diff | **PASS** | Baseline and successor personal-model snapshots are immutable, deterministic canonical derived records with pinned versions and derivation metadata. Diff preserves unresolved contradiction/unknown state without completion or AI claims. |
| T5 Canonical correction | **PASS** | Expected-version correction atomically closes the prior report version, inserts one successor, preserves history and rejects a stale base through the real desktop command path. |
| T6 Dependency-aware deletion | **PASS** | Dry-run counts and execution selectors are derived from the actual V2 locator, target, evidence, uncertainty, contradiction, typed-relation and snapshot-membership edges. Execution recomputes the plan to reject stale closure, removes reconstructive descendants, preserves an unrelated canonical source and counterreport/assertion, rolls back cancellation/faults, emits a content/hash-free receipt, and verifies canonical/export/view absence. |
| T7 Accessible offline UX | **PASS** | The previously demonstrated packaged E03 surface remains keyboard/focus operable, text-safe, labelled, non-color-only, reduced-motion aware, pressure-free after absence, offline and bounded by the accepted named IPC authority. No T7 code changed during acceptance repair. |

## Migration decision

- Exactly one visible forward `1 -> 2` migration exists; no reverse migration is claimed.
- Its frozen checksum is `8847dbb72271fa75e9f456502737ebcafe0027f6ac10bfd7ae3757f413e48bcf`.
- Exactly five V1 semantic tables are rebuilt, fifteen V2 tables are added, and inventories remain exactly 20/35.
- Raw legacy enums, including `causal`, `predictive` and every V1 origin, survive without causal or predictive reinterpretation.
- An established V1 vault always requires both verified backup and verified open export, even when its semantic tables are empty. There is no frozen pristine-V1 exception. Fresh vault creation through the direct `0 -> 2` bootstrap chain is not migration of an established V1 vault.
- Injected interruption rolls back schema and migration bookkeeping; a successful rerun is a verified no-op.

## V2 portability / E01 recovery decision

The frozen E03 preflight is interpreted as option A: E03 adds a checksummed,
schema-versioned logical portability package and open export for exact V1/V2
semantic inventories. It does not extend the accepted E01 authenticated,
encrypted recovery package beyond its frozen V1 profile. The logical package is
now labelled `psyche-os-logical-portability-package`, validates exact canonical
per-table schemas, and restores only into an explicitly empty isolated target.
It makes no encryption, authentication, clean-device recovery or atomic live
activation claim. Accepted E01 verification and recovery code remains unchanged
and its 16/16 assurance gate passes.

## Acceptance fixes

- Removed the implicit empty-V1 migration prerequisite exception and added proof that missing either required artifact fails closed.
- Replaced misleading logical-backup terminology and tightened exact-schema and empty-target portability validation.
- Replaced fixture-wide deletion counts and whole-table deletes with the smallest deterministic closure over the frozen V2 dependency model.
- Added regression evidence that unrelated canonical records survive while reconstructive snapshots and descendants are removed.

## Fresh targeted gate

```text
uv sync --frozen: PASS (25 packages audited)
targeted E03 pytest: PASS (23 passed, 0 skipped)
```

Desktop/toolchain checks were not repeated because no desktop/T7 code changed;
the candidate's existing mandatory desktop/toolchain proof remains recorded in
`docs/development/reports/E03.md` with zero E03 skips.

## Fresh authoritative FULL gate

```text
uv sync --frozen: PASS (25 packages audited)
uv run pytest -q: PASS (326 passed, 1 skipped)
validate_f0_scope.py: PASS (6/6)
validate_f0_artifacts.py: PASS (4/4)
validate_e01_assurance.py: PASS (16/16)
validate_orchestration.py: PASS (112/112)
```

The sole skip is the unchanged accepted-baseline Windows administrator-only
symlink fixture in `TestF09aPathEscape::test_symlink_traversal_rejected`. It
covers the deferred general `FilesystemAdapter`; no mandatory E01, E02 or E03
proof skipped. SQLCipher HMAC diagnostics came from expected wrong-key negative
recovery tests and are not gate failures.

## Decision

T1–T7 pass, migration prerequisites and terminology are truthful, V2 logical
portability is distinct from E01 authenticated recovery, deletion is derived
from the frozen canonical dependency model, E00–E02 remain green, all final
gates pass, and `REAL_DATA_GATE` remains `CLOSED`. E03 is `ACCEPTED`.
