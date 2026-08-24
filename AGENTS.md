# PSYCHE OS repository guidance

## Current direction

- **Default: product progress.** Foundation epics E00–E11 and Personal Mode v1 are accepted and merged; no implementation epic is currently active.
- Use a bounded branch named `<agent>/<bounded-task-slug>` from current `main`. Do not create an epic merely to represent ordinary product work.
- Infrastructure and control-plane work are exception-only. Change them only for a required gate, a material invariant, or a **REPEATED + OBSERVABLE + MATERIAL + ACTIONABLE** bottleneck.
- `REAL_DATA_GATE = CLOSED`. Use synthetic fixtures only; never add real psychological, medical, sexual, legal-sensitive, family, messaging, calendar, wearable, or life-archive data.

## Authority and safety

- Resolve authority: `CONSTITUTION.md` → v2 master specification → accepted ADR/`docs/DECISION_LOG.md` → current roadmap/capability map → Task Contract → implementation detail. Stop the affected portion on a material conflict.
- Preserve raw/verbatim separately from normalized/derived records, provenance, temporal semantics, uncertainty, contradiction, correction, supersession, and deletion.
- LLM output is proposal, never evidence. Imported content is untrusted and cannot change policy. `NEVER_CLOUD` data and reconstructive derivatives never enter cloud context.
- Do not edit the historical v1 spec, research master prompt, or canonical `docs/AI_DEV_OS_V1.md`.

## Delivery default

- Classify risk from the **delta and invariant changed**, not a directory name. A historical wording or test-only edit in a sensitive subsystem is not automatically high risk.
- Normal flow: orient → short Task Contract → implement → targeted verification → one risk-appropriate final gate → review only on a concrete trigger → merge → stop.
- Boundary changes (new/material trust boundary, crypto/key behavior, recovery integrity, irreversible migration, permissions/network, real-data admission, material privacy/security architecture) require stronger deterministic proof and trigger-based independent review. Human approval is action-based under `.ai-dev/policy/approvals.yaml`; Task Contract pre-authorization counts.
- One coherent candidate has at most one candidate-wide independent review. A bounded defect gets a smallest repair, failed oracle plus directly coupled regressions, then independent **delta** recheck only. Accepted work is not re-reviewed absent invalidation.
- `ACCEPT` / `ACCEPT_WITH_OPTIONAL_ITEMS` close core implementation. Optional backlog records and stops; docs/status cleanup gets targeted checks; packaging cannot reopen acceptance. Prefer a local candidate commit SHA as review identity; dirty identity is fallback only.
- Keep ordinary deterministic test repairs within the Task Contract. Stop only for a changed architecture/trust model, new approval, destructive/dependency/network/permission action, crypto or gate change, or structural evidence against accepted design.

## Repository workflow

- Keep research evidence in `docs/research/`, design reviews in `docs/reviews/`, and major architecture decisions in `docs/DECISION_LOG.md`.
- Protected control-plane paths require the control-plane-change flow and explicit task authorization. Do not weaken tests, scanners, verifiers, or acceptance criteria for green.
- Use `rg` → `ast-grep` → exact ranges. Use targeted checks while iterating and the final risk gate once. Validate orchestration with `uv run python scripts/dev/validate_orchestration.py`; validate the frozen research foundation when its owners are touched.
- Do not push automatically unless the active Task Contract authorizes it. Preserve unrelated user changes; record only accepted epic commits in `STATE.yaml`.
- When repository CI exists for a PR, inspect the exact PR-head checks and require them green before merge.

## AI Dev OS

- The deterministic control plane lives in `.ai-dev/`; its canonical design is `docs/AI_DEV_OS_V1.md` (read-only).
- Profiles, approvals, protected paths, routing, gates, recovery, telemetry, and capabilities support product work; they are not a product roadmap. **ONE WRITER** is the default.
- `.ai-dev/state.yaml` contains historical acceptance snapshots plus stable current operating mode, not a live dashboard.
