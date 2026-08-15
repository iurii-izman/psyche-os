# AI Dev OS V2.0 — Control Canary Draft

**Status:** CANARY (`2.0.0-canary.1`) — IMPLEMENTED / PENDING_REVIEW. Not production-ready.
**Base:** `ceb3031dd5d7d75564691f59ddf6e23dd71a812f`
**V1:** unchanged, still `VERIFIED / PRODUCTION_READY`.

This draft records the five V2.0 control mechanisms promoted from E10 evidence into
a bounded canary. It does not describe a V2 rollout.

## 1. The five promoted canary components

| # | Component | Where | E10 evidence that justified it |
|---|---|---|---|
| A | Model / provider attestation | `scripts/ai_dev_v2.py attest`, `.ai-dev/routing/provider-mapping.yaml` | configured/requested/harness-reported/effective model identity was ambiguous (E10 review recorded `claude-opus-5[1m]` while DeepSeek V4 Pro was not observably confirmed). |
| B | Versioned diagnostic ratchet | `scripts/ai_dev_v2.py ratchet`, `.ai-dev/evidence/diagnostics/` | diagnostic counts changed across tool versions; a count-only baseline could not distinguish "same count, different findings". |
| C | Cross-platform hook conformance | `tests/control_plane/test_hook_conformance.py` | a real Windows absolute-path hook bypass existed in V1 before closeout. |
| D | Authority / contract guard | `scripts/ai_dev_v2.py contract` | accepted implementation precedent can conflict with higher normative authority. |
| E | Task / review packet compiler | `scripts/ai_dev_v2.py packet` | Task/Review packets were repeatedly assembled manually. |

## 2. Component semantics (bounded)

### A. Model / provider attestation

Separates `configured_provider`, `configured_model`, `requested_model`,
`harness_reported_model`, `provider_mapping`, `effective_backend_model`,
`effective_backend_observable`, `attestation_status`, `evidence_source`.

Statuses: `CONFIRMED`, `MAPPED_BY_PROVIDER_CONTRACT`, `HARNESS_ONLY`, `UNKNOWN`, `CONFLICT`.

Rules: configuration is not runtime proof; a harness-reported Claude-style name is
harness evidence only; a documented deterministic provider alias mapping yields
`MAPPED_BY_PROVIDER_CONTRACT` (never `CONFIRMED`) **only when the active endpoint/upstream
is itself proven**; a direct-backend contradiction yields `CONFLICT`; unobservable backend
yields `UNKNOWN`/weaker mapped status. Secrets are never persisted. No live network probe
is required.

### B. Versioned diagnostic ratchet (Ruff + mypy only)

Each baseline binds `tool`, `tool_version`, `config_fingerprint`, `baseline_commit`,
`finding_identity_digest`, `finding_count`, `finding_identities`, `captured_at`.
Comparison is identity-aware. Version/config drift yields `BASELINE_INCOMPATIBLE`, never a
false regression. Baselines are integrity-checked (required fields + digest/count/identity
consistency); a tampered or malformed baseline fails closed. Rebaseline is a separate
explicit command (requires a stated reason) and appends to an append-only history ledger;
it never runs automatically after a failure.

### C. Cross-platform hook conformance

Deterministic tests over the existing single dispatcher/security guard. Covers relative,
dot-relative, absolute Windows, mixed separators, case variants, worktree-absolute, and
`..` traversal forms; proves equivalent protected-path semantics. Failure-driven fixes only.

### D. Authority / contract guard

HIGH/CRITICAL contracts carry `authority` (`highest` / `supporting` /
`implementation_precedent`) and `authority_conflicts` (`status` / `items`).
`implementation_precedent` never outranks normative authority. A single guard decision
drives both contract check and packet rendering: unresolved/invalid conflict status,
precedence violations, malformed resolution, or missing V2 structure block acceptance-ready
output. V1 flat-list contracts remain readable (legacy interpretation).

### E. Task / review packet compiler

Deterministic renderer (no LLM, no network, no timestamps/random IDs). Same input →
byte-identical output. Recursively sanitizes input (drop raw-prompt/tool-IO/transcript/CoT;
redact secret keys and bounded secret patterns) and omits generic `AGENTS.md` / `.ai-dev`
policy. HIGH/CRITICAL unresolved conflicts render a BLOCKED packet.

## 3. Invariants

- V1 remains the production path; V2 is additive and inactive by default.
- No new production dependency, no new daemon/server/gateway/framework.
- Application source diff is zero.
- No secret, token, raw prompt, or chain-of-thought is persisted or rendered.
- A requested model is never promoted to an effective backend model.
- A discovered authority conflict cannot disappear from the deterministic transaction.
- Diagnostic baselines are never rewritten silently after a failure.

## 4. Rollback

V1 is not deleted or replaced. The V2 additions are additive: disabling/ignoring them
(`scripts/ai_dev_v2.py`, `.ai-dev/evidence/`, V2 contract/state fields) restores the V1
dispatcher/routing/verification path. Rollback requires no history rewrite, destructive
cleanup, schema migration, external service, or dependency removal.

## 5. Deferred LAB components (NOT promoted)

Pathfinder, SymLens, Reasonix, Codebase-Memory, projectmem, selective/impacted testing,
vector memory, Context Mode, RTK, multi-agent orchestration, and any new harness/gateway.
No equivalent real-work evidence yet justifies them.

## 6. Field-test requirement

V2.0 must not be considered production-ready until it is field-tested on the bounded
`PREPARE E11` workflow (no E11 implementation, `REAL_DATA_GATE` stays CLOSED) and a fresh
strong review returns `ACCEPT_CANARY`.
