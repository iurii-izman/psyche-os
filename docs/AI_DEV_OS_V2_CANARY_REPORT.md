# AI Dev OS V2.0 Control Canary — Implementation Report

**Status:** `IMPLEMENTED / PENDING_REVIEW` (CANARY, not production-ready)
**Base:** `ceb3031dd5d7d75564691f59ddf6e23dd71a812f`
**Branch:** `ai-dev/v2-control-canary`
**Candidate SHA (freeze for review):** `d0d1ed573b7ba8db135b82d51593359ee0937a09`
**Trusted baseline ref (immutable):** `1868237c15ef02fdba20c6ed0d47bb6486d23b8f` — baseline
findings were captured against the base SHA `ceb3031…`; comparison reads the baseline from
this immutable commit via `git show`, never the working-tree file.
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
- `env:DEEPSEEK_API_KEY present` (a key exists; presence is declaration, not routing proof)
- `env:ANTHROPIC_BASE_URL present (host=127.0.0.1)` — a localhost Anthropic-compatible proxy
- `config:cc-switch present`
- cc-switch: no current `claude`-harness provider (upstream unproven) — the only current
  DeepSeek provider is scoped to `claude-desktop`, not the Claude Code CLI
- harness-reported model: `claude-opus-5[1m]`

**INFERENCE** — none. The mapping contract is **not** applied because its applicability to
the active endpoint/upstream is not proven: the endpoint is localhost and cc-switch's
active CLI-harness provider is not observably DeepSeek.

**UNKNOWN** — the effective backend model. Status is `HARNESS_ONLY`, effective backend
`UNKNOWN`, `effective_backend_observable: false`.

Machine-readable record: `.ai-dev/evidence/attestation/AI-DEV-V2-CONTROL-CANARY-001.attest.yaml`
(status `HARNESS_ONLY`). The requested model was never promoted to effective state; the
harness-reported Claude-style name was preserved separately.

---

## 3. Diagnostic baseline ratchet

- **Historical V1 debt** (count-only, preserved as historical evidence): Ruff 215, mypy 40
  (`docs`/`.ai-dev/state.yaml`, `.ai-dev/evidence/diagnostics/historical-debt.yaml`).
- **New V2 identity-aware baseline** (bootstrapped at the base SHA):
  - Ruff `0.15.10` — 215 findings, config fingerprint `e6e151a3…`, digest `41b5bcb7…`
  - mypy `2.3.0` — 40 findings, config fingerprint `cf866f84…`, digest `6495c4a1…`
- Comparison is identity-aware; version/config drift → `BASELINE_INCOMPATIBLE`.
- **Baseline authority is an immutable Git commit/ref** (F4b): `ratchet compare --baseline-ref
  <ref-or-sha>` loads the baseline via `git show <sha>:.ai-dev/verification/baselines/<tool>.baseline.yaml`,
  never the working-tree file. Promotion is a separate human-gated repository transaction, not
  an agent command.

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

## 4b. Targeted fix pass (post-implementation)

Four verified boundary defects and two provenance inconsistencies were fixed:

- **F1** — attestation no longer applies the provider mapping without proven mapping
  context (endpoint host identifies the provider, or an explicitly-parsed active upstream
  provider config names it). A key merely being present does not establish applicability.
  Direct backend provider without an observed model is not `CONFIRMED`; model-level
  contradiction yields `CONFLICT`; mapping is scoped to the named provider (no fall-through).
- **F2** — a single `guard_decision()` now drives `contract check` AND both packet
  renderers; HIGH/CRITICAL acceptance-ready rendering is blocked on unresolved/invalid
  conflict status, authority precedence violations, malformed resolution, or missing V2
  authority/conflict structure. Legacy V1 flat contracts remain readable.
- **F3** — packet rendering recursively sanitizes contract/state/attestation (drop
  raw-prompt/tool-IO/transcript/CoT; redact secret keys and bounded secret patterns;
  nested mappings/lists/conflict items included).
- **F4** — the ratchet is fail-closed: baselines are verified for required fields and
  digest/count/identity consistency; rebaseline requires an explicit `--reason` and records
  the previous baseline in history.
- **P1** — implementation vs review-artifact HEAD ambiguity is closed (candidate SHA is the
  content HEAD; the packaging commit is stated separately).
- **P2** — the temporary kill-switch use is recorded truthfully in
  `.ai-dev/evidence/decisions/V2-CANARY-CONTROL-PLANE-CHANGE.md`.

---

## 4c. Pre-review hardening (F4 canonical baseline + F1b endpoint proof)

- **F4 (re-scoped)** — canonical diagnostic baselines now live under protected verification
  scope (`.ai-dev/verification/baselines/`). `ratchet rebaseline` was replaced by a two-phase
  transaction: `ratchet propose` (writes an evidence proposal only) and `ratchet promote`
  (requires an explicit approval/evidence reference and writes the protected canonical
  baseline). `compare` is read-only and fail-closed against git ancestry (baseline commit
  must exist and be an ancestor of the comparison HEAD) plus structural integrity (tool
  identity, count/digest consistency).
- **F1b** — the provider mapping now requires provider-owned endpoint evidence. Trusted hosts
  are declared in `.ai-dev/routing/provider-mapping.yaml` (`api.deepseek.com` only);
  `notdeepseek.com` / `deepseek.example.com` / arbitrary substring matches are rejected.
  cc-switch upstream is trusted only by its endpoint host, never its display name.

> **Superseded by F4b (next section):** the F4 `ratchet promote --evidence <string>` path was a
> reward-hacking boundary — a non-empty evidence string was not a real approval boundary. F4b
> removes autonomous promotion and makes comparison read the immutable baseline via Git SHA.

---

## 4d. F4b — immutable baseline authority (final boundary fix)

The F4 `propose`/`promote` split still left an autonomous canonical-write path: `ratchet
promote --evidence <any-non-empty-string>` wrote the protected canonical baseline, so an
arbitrary evidence string authorized a self-promotion. That recreated a reward-hacking path
(diagnostic FAIL → propose → self-promote → canonical baseline absorbs the defect → PASS).
F4b removes it.

- **Immutable baseline source** — `ratchet compare --baseline-ref <ref-or-sha>` resolves the ref
  to a full commit SHA and loads the canonical baseline via
  `git show <sha>:.ai-dev/verification/baselines/<tool>.baseline.yaml`. The working-tree file
  never controls comparison. The exact resolved SHA and baseline path are observable in output.
- **Git commit/ref = baseline authority** — a missing or unresolvable ref, an absent baseline
  file at the ref, tool mismatch, or digest/count/ancestry corruption all fail closed; there is
  no silent fall-back to the working-tree baseline.
- **No autonomous promotion** — the coding-agent CLI has no canonical-write path.
  `ratchet promote` returns `HUMAN_GATE_REQUIRED` and performs no write; `--evidence` is removed
  as an authorization argument.
- **Promotion = separate human-gated transaction** — proposal → human/architect review →
  separate approved PR → deterministic verification → merge to canonical main → the merged
  commit becomes the new trusted baseline SHA. A future dedicated promotion utility may be
  designed later only if real work requires it (no signing/tokens/ACLs/generic approval now).

Regression proof (central anti-reward-hacking invariant): a trusted baseline SHA contains
finding A; the working tree mutates the baseline file to A+B; current diagnostics produce A+B;
comparison against the trusted SHA still detects B as NEW. Likewise `propose` after a failure
does not change the trusted-ref comparison result.

---

## 5. Verification (exact commands and results)

| Check | Command | Result |
|---|---|---|
| Focused V2 suite | `uv run pytest tests/control_plane/ -q` | `114 passed` |
| Dispatcher smoke | `uv run python .ai-dev/hooks/test_dispatcher.py` | `ALL PASS` |
| Hook conformance | (part of focused suite) | `passed` |
| Telemetry self-test | `uv run python .ai-dev/telemetry/writer.py --self-test` | `SELF-TEST OK` |
| Doctor | `uv run python scripts/ai_dev_doctor.py` | `RESULT: PASS` |
| Orchestration | `uv run python scripts/dev/validate_orchestration.py` | `113 passed, 1 failed` (branch-name gate, pre-existing) |
| Ruff ratchet (immutable ref) | `uv run python scripts/ai_dev_v2.py ratchet compare --baseline-ref 1868237c…` | `ruff: PASS — no new diagnostics` |
| mypy ratchet (immutable ref) | (same) | `mypy: PASS — no new diagnostics` |
| Adversarial baseline mutation | `pytest -k working_tree_absorbs_new_diagnostic_still_fails` | `PASS` |
| Proposal-does-not-green | `pytest -k propose_after_failure_compare_still_fails` | `PASS` |
| Full pytest | `uv run pytest -q` | `758 passed, 2 skipped` (pre-existing symlink skips) |
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

1. Effective backend identity is not directly observable in this environment; for this run the
   attestation is `HARNESS_ONLY` / `UNKNOWN` (localhost endpoint, no proven DeepSeek upstream).
   The mapping contract would only apply with proven endpoint/upstream context.
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

> Review freeze: `base = ceb3031…`, `candidate = d0d1ed5…` (the content HEAD). The review
> packet is committed in a separate packaging commit on the branch, which is excluded from
> review scope; it does not change the frozen candidate SHA.
