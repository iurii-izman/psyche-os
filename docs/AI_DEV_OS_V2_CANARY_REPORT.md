# AI Dev OS V2.0 Control Canary — Implementation Report

**Status:** `IMPLEMENTED / PENDING_REVIEW` (CANARY, not production-ready)
**Base:** `ceb3031dd5d7d75564691f59ddf6e23dd71a812f`
**Branch:** `ai-dev/v2-control-canary`
**Implementation SHA:** `b81c53b4275a1fc6b3dc9bbd4a62f43b1fc8857c`
**V1:** unchanged — `VERIFIED / PRODUCTION_READY`

This report distinguishes **CLAIM** (what the implementation states), **EVIDENCE**
(exact observable output), **INFERENCE** (weaker derivation), and **UNKNOWN**.

---

## 1. What was implemented (five components)

| # | Component | Artifact |
|---|---|---|
| A | Model / provider attestation | `scripts/ai_dev_v2.py attest`, `.ai-dev/routing/provider-mapping.yaml`, `.ai-dev/telemetry/schema.json` |
| B | Versioned diagnostic ratchet (Ruff + mypy) | `scripts/ai_dev_v2.py ratchet`, `.ai-dev/evidence/diagnostics/` |
| C | Cross-platform hook conformance | `tests/control_plane/test_hook_conformance.py` |
| D | Authority / contract guard | `scripts/ai_dev_v2.py contract` |
| E | Task / review packet compiler | `scripts/ai_dev_v2.py packet` |

One unified repository-native CLI (`scripts/ai_dev_v2.py`, stdlib + PyYAML only). No
new dependency, no daemon, no server, no gateway, no framework. Application source
(`src/`, `desktop/`) is unchanged.

---

## 2. Model / provider attestation — this run

**CLAIM** — the canary records observable identity without unsupported inference.

**EVIDENCE**
- `env:DEEPSEEK_API_KEY present`
- `env:ANTHROPIC_BASE_URL present (host=127.0.0.1)` — a localhost Anthropic-compatible endpoint
- `config:cc-switch present`
- harness-reported model: `claude-opus-5[1m]`
- routing strong role: `deepseek-v4-pro` (`.ai-dev/routing/routing.yaml`)

**INFERENCE** — `claude-opus-5[1m]` maps to `deepseek-v4-pro` via the documented
DeepSeek Anthropic/Claude Code compatibility contract → status
`MAPPED_BY_PROVIDER_CONTRACT` (never `CONFIRMED`).

**UNKNOWN** — whether the backend actually executed as `deepseek-v4-pro`; the backend is
not directly observable, so `effective_backend_observable: false`.

Machine-readable record: `.ai-dev/evidence/attestation/AI-DEV-V2-CONTROL-CANARY-001.attest.yaml`
(status `MAPPED_BY_PROVIDER_CONTRACT`). The requested model was never promoted to
effective state; the harness-reported Claude-style name was preserved separately.

---

## 3. Diagnostic baseline ratchet

- **Historical V1 debt** (count-only, preserved as historical evidence): Ruff 215, mypy 40
  (`docs`/`.ai-dev/state.yaml`, `.ai-dev/evidence/diagnostics/historical-debt.yaml`).
- **New V2 identity-aware baseline** (bootstrapped at the base SHA):
  - Ruff `0.15.10` — 215 findings, config fingerprint `e6e151a3…`, digest `41b5bcb7…`
  - mypy `2.3.0` — 40 findings, config fingerprint `cf866f84…`, digest `6495c4a1…`
- Comparison is identity-aware; version/config drift → `BASELINE_INCOMPATIBLE`; rebaseline
  is a separate explicit command with an append-only history ledger.

---

## 4. Defects found and fixed (failure-driven, in-scope)

1. **Windows case-insensitive protected-path bypass** — `.AI-DEV/STATE.YAML` (same file on
   NTFS) was not blocked. Fixed by case-insensitive comparison in `security_guard._is_protected`.
2. **`..` traversal gap** — a path through a non-protected parent could reach a protected
   file without matching. Fixed by `os.path.normpath` in `security_guard._norm`.
3. **Packet secret/raw-prompt leakage** — the renderer emitted arbitrary `verification_evidence`
   keys. Fixed by dropping/redacting sensitive keys in the packet renderer.

Each fix: conformance/regression test added first, smallest change made, focused rerun,
and the existing dispatcher smoke test re-confirmed (`ALL PASS`, 12/12).

---

## 5. Verification (exact commands and results)

| Check | Command | Result |
|---|---|---|
| Focused V2 suite | `uv run pytest tests/control_plane/ -q` | `69 passed` |
| Dispatcher smoke | `uv run python .ai-dev/hooks/test_dispatcher.py` | `ALL PASS` |
| Hook conformance | (part of focused suite) | `passed` |
| Telemetry self-test | `uv run python .ai-dev/telemetry/writer.py --self-test` | `SELF-TEST OK` |
| Doctor | `uv run python scripts/ai_dev_doctor.py` | `RESULT: PASS` |
| Orchestration | `uv run python scripts/dev/validate_orchestration.py` | `113 passed, 1 failed` (branch-name gate, pre-existing) |
| Ruff ratchet | `uv run python scripts/ai_dev_v2.py ratchet compare` | `ruff: PASS — no new diagnostics` |
| mypy ratchet | (same) | `mypy: PASS — no new diagnostics` |
| Full pytest | `uv run pytest -q` | `713 passed, 2 skipped` (pre-existing symlink skips) |
| App-source diff | `git diff --stat ceb3031 -- src desktop` | empty (0 changes) |
| Packet determinism | render twice, byte-diff | identical |

**INFERENCE** — the `1 failed` orchestration check is the branch-name gate: the candidate
branch is not `main` and E10 is `ACCEPTED` (no candidate-branch exception). This is the
documented pre-existing `113/1 on feature branch` behavior, not a V2 regression.

**UNKNOWN** — none of the verification commands require a network call; no paid probe was run.

---

## 6. V1 rollback

**CLAIM** — V1 remains immediately usable.

**EVIDENCE** — V2 is additive and inactive by default; the dispatcher, telemetry writer,
doctor, and protected-paths policy are unchanged except for two security-guard fixes (which
the dispatcher smoke test confirms). Rollback requires no history rewrite, destructive
cleanup, migration, external service, or dependency removal. Reverting the three pre-authorized
T0 files (`security_guard.py`, `schema.json`, `state.yaml`) to the base SHA restores V1 exactly.

---

## 7. Residuals (exact remaining canary limitations)

1. Effective backend identity is not directly observable in this environment; attestation is
   `MAPPED_BY_PROVIDER_CONTRACT`, never `CONFIRMED`.
2. Live network/provider probing is intentionally not implemented (not required to pass).
3. The ratchet covers Ruff and mypy only; no generic scanner platform.
4. Symlink/reparse conformance is limited to what Windows permits without admin (the two
   pre-existing symlink skips remain).
5. `endpoint_identifier_without_secret` is a pre-existing schema field whose name substring
   triggers the telemetry redactor; its value is a bounded non-secret hostname, so this loses
   no secret and is left as pre-existing behavior.

---

## 8. State

- **V1:** `VERIFIED / PRODUCTION_READY`
- **V2.0:** `IMPLEMENTED / PENDING_REVIEW / CANARY` (`2.0.0-canary.1`, `production_ready: false`)
- **E10:** `ACCEPTED`
- **E11:** `PLANNED`
- **REAL_DATA_GATE:** `CLOSED`

Next: **FRESH STRONG V2 CANARY REVIEW REQUIRED** (do not run here).
