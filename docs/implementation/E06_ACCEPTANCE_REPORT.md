# E06 final high-risk bounded acceptance report

**Review date:** 2026-08-13
**Verdict:** `ACCEPTED`
**Base:** `5852b3a5d1cc8ceae05b56a0770bb14095add3fa`
**Accepted E06 implementation commit:** `e6225c537ff94390abd1953d70d3caaf5b452712`
**Profile:** fixed synthetic-only bounded N-of-1 protocol and action/claim policy
**REAL_DATA_GATE:** `CLOSED`

## Findings and repairs

| Review target | Finding | Accepted repair |
| --- | --- | --- |
| Claim request semantics | Supported ceiling was also emitted, upgrading weak requests and silently falling back after denied strong requests. | `ClaimDecision` now separates supported ceiling, requested level, allow/deny, denial reasons, and optional emitted level/wording. Weak requests remain weak; unsupported requests emit nothing. |
| Canonical provenance | Analysis read run metadata from SQLite but regenerated period records from the package fixture. | Analysis reconstructs protocol, intervention, and ordered period records from V4. Controlled persisted-record changes affect or block results; fixture regeneration cannot hide canonical state. |
| Evidence axes | Production supplied a constant all-C5 `FULL_EVIDENCE`. | A bounded evaluator derives measurement, coverage, missingness, assignment/replication, serial, carryover, and computed sensitivity ceilings from the canonical protocol/run. Every weakened axis lowers or blocks the ceiling. |
| Stop semantics | Load wrote all eight exposures/outcomes before stop could have future effect. | Load now creates only preregistration/run state. Eight exact named transitions append immutable historical periods; stop/adverse/contraindication prevents remaining transitions and freezes claims. |
| Assignment lifetime | Python `Random.shuffle` plus an informal version label was not a sufficient lifetime reproduction contract. | A fully specified PSYCHE-owned SHA-256 period-ranking algorithm uses the frozen seed and has an exact version/digest known answer. |

## Bounded acceptance decision

| Target | Result | Evidence |
| --- | --- | --- |
| Claim ceiling and emission | **PASS** | Emitted level is never above request or support; unsupported requests are typed denials without fallback wording. Evidence removal is monotone. |
| Canonical analysis provenance | **PASS** | Pinned V4 protocol/intervention/run/period rows are the analysis authority. Persisted mutation tests change or block the deterministic result. |
| Derived evidence | **PASS** | No asserted `FULL_EVIDENCE` remains. Seven axes are evaluated from the actual canonical run and sensitivity calculation. |
| Execution lifecycle | **PASS** | Stop, adverse, and contraindication after historical periods block later production transitions and all claims; completed rows remain immutable. |
| Intervention gates | **PASS** | R0 and R1 require exact frozen metadata; R2 returns `qualified_review_required`; R3 is unconditional denial; alias/version/component changes fail closed. |
| Assignment reproduction | **PASS** | Seed `6062044`, algorithm `psyche_sha256_balanced_rank`, version `sha256-rank-v1`, assignment digest `7f6b7f5332d4f651f39ce2ceb0896e74878af7a4a8c84469ff053f10c979e2d4`. |
| Additive V4 | **PASS** | Same four E06 tables and exact 43-table inventory; checksum `31ecd16646aff211cfd991f30d9cbdf2f3b6010dc759fd4d7644ff90d63e9413`; V1–V3 history, atomicity, backup/export prerequisite, interruption rollback, portability, no-op, and deletion proofs pass. |
| Regression | **PASS** | Mandatory E06/E05/E03 targeted set and FULL gate pass; no mandatory proof skipped. |

## Validation

```text
uv sync --frozen: PASS (25 packages audited)
mandatory E06 + E05 + E03 targeted set: PASS (71 passed, 0 skipped)
uv run pytest -q: PASS (396 passed, 1 skipped)
validate_f0_scope.py: PASS (6/6)
validate_orchestration.py before acceptance metadata: PASS (112/112)
scoped Ruff: PASS
strict mypy over touched E06 source: PASS
```

The sole skip is the unchanged administrator-only Windows symlink fixture. Expected SQLCipher diagnostics are from wrong-key negative tests. Desktop/native gates were correctly omitted because desktop code did not change.

## Residual limitations

- One fixed semantically neutral synthetic protocol only; no real/arbitrary capture or general experiment builder exists.
- R2 lacks qualified review and is unavailable; R3 is always denied.
- Evidence and sensitivity evaluation is deliberately specific to the frozen known-answer fixture, not a general statistical engine.
- V4 rollback is restoration/activation of retained verified V3 state; no reverse migration is claimed.

## Decision

All mandatory high-risk findings are repaired locally at implementation commit `e6225c537ff94390abd1953d70d3caaf5b452712`. E06 is accepted without expanding scope or schema inventory. E07 remains `PLANNED`, and `REAL_DATA_GATE` remains `CLOSED`.
