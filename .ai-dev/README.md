# AI Dev OS v1 — Control Plane

Vendor-neutral, deterministic, version-controlled control plane around replaceable AI
coding harnesses and model providers. This directory is **operational control (T0)**:
changes to `policy/`, `verification/`, and `hooks/` require the control-plane-change
flow and explicit approval (see `policy/approvals.yaml`).

## Layout

| Path | Purpose |
|---|---|
| `policy/` | Risk engine, protected paths, approval matrix, capability & dependency policy (T0) |
| `profiles/` | Operating profiles: `balanced`, `quality`, `economy`, `lab` |
| `contracts/` | Reusable Task Contract template |
| `skills/` | Project-local `psyche-*` skills (lazy-loaded, compact) |
| `verification/` | Canonical project commands and V0–V4 gate mapping |
| `hooks/` | Single deterministic hook dispatcher + modules |
| `telemetry/` | Append-only JSONL schema, redaction, retention, writer |
| `capabilities/` | Capability registry (DISABLED/LAB/CONDITIONAL/CORE/QUARANTINED) |
| `evidence/` | Evidence ledger for capability/decision provenance |
| `recovery/` | Task Snapshot and Recovery Packet templates |
| `routing/` | Model routing profiles and circuit-breaker thresholds |
| `lab/` | Lab experiments (NOT production) |
| `state.yaml` | Machine-readable implementation state (no secrets) |

## Authority

Source of truth order (from `AGENTS.md`): `CONSTITUTION.md` → v2 master spec →
accepted ADR / `docs/DECISION_LOG.md` → `docs/ROADMAP.md` + `docs/development/EPIC_MAP.md`
→ Task Contract → code + tests → operational memory → transcript.

Canonical AI Dev OS spec: `docs/AI_DEV_OS_V1.md` (READ-ONLY).
Research/decision catalog: `docs/AI_DEV_OS_RESEARCH_CATALOG_V1.docx` (READ-ONLY).

## Product-first delivery

The control plane exists to help accept safe, meaningful Psyche OS product slices.
Optimize for accepted user-facing progress with the minimum sufficient process and
risk-proportionate evidence; it is not itself the product. Improve a harness,
evaluator, benchmark, agent, context system, or verification tool only when it blocks
a repository-required gate, protects a material product/security invariant, or solves
a repeated material bottleneck whose expected payoff justifies the cost. Otherwise,
record bounded debt and return to product work.

Every non-trivial Task Contract separates repository-required gates,
contract-required proof, and supplemental evidence. Repository gates cannot be
silently waived. Supplemental evidence may inform confidence or diagnosis, but its
failure is not automatically a product failure. When an oracle is unreliable, classify
the failure and use the recovery/verification policy to decide whether a trusted
alternate proof is sufficient or only the affected claim must remain blocked.

## Doctor

Validate the whole control plane + environment with:

```bash
uv run python scripts/ai_dev_doctor.py
```
