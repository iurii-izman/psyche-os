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

## Doctor

Validate the whole control plane + environment with:

```bash
uv run python scripts/ai_dev_doctor.py
```
