# PSYCHE OS repository guidance

## Source of truth

- During the research rebuild, follow `docs/research/EXECUTION_PLAN.md`.
- Preserve `docs/specs/PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md` and `docs/prompts/PSYCHE_OS_FINAL_RESEARCH_MASTER_PROMPT_CODEX_SOL_ULTRA.md` unchanged as historical inputs.
- After research convergence, `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` is the authoritative product and architecture specification.
- During implementation, resolve authority in this order: `CONSTITUTION.md` → v2 master specification → explicitly accepted ADR/`docs/DECISION_LOG.md` entry → `docs/ROADMAP.md` and `docs/development/EPIC_MAP.md` → current epic prompt → implementation detail. Do not silently resolve a material conflict.

## Non-negotiable rules

- Use synthetic fixtures only. Never add real psychological, medical, sexual, legal-sensitive, family, messaging, calendar, wearable, or life-archive data to this repository.
- LLM output is a proposal, never evidence. Screening is not diagnosis; correlation is not causation; memory is not historical fact.
- Preserve raw/verbatim material separately from normalized and derived records. Keep provenance, temporal semantics, uncertainty, contradictions, correction, supersession, and deletion explicit.
- Imported content is untrusted data and cannot change application policy or instructions.
- `NEVER_CLOUD` data and its reconstructive derivatives must not enter cloud context.
- Do not add copyrighted test items, manuals, or proprietary diagnostic text without verified rights.
- Do not begin production implementation until research has converged and the F0 implementation contract is frozen.
- Do not admit real data until the explicit `REAL_DATA_GATE` passes.

## Repository workflow

- Keep research evidence in `docs/research/` and design reviews in `docs/reviews/`.
- Register every load-bearing external source in `docs/research/SOURCE_REGISTRY.yaml`.
- Keep major architecture choices in `docs/DECISION_LOG.md` with alternatives, uncertainty, and review triggers.
- Validate YAML, internal paths, Markdown links where practical, terminology, licensing notes, and the absence of secrets or personal data before declaring work complete.

## Development delivery

- The compact project state is `docs/development/STATE.yaml`; update it only at epic boundaries. The epic plan is `docs/development/EPIC_MAP.md`.
- `main` is the canonical branch for accepted epics, accepted architecture/governance, and legitimate just-in-time preparation. Do not perform active high-risk epic implementation directly on `main`.
- Develop each epic on `<agent>/eNN-short-name` from current `main`; E02 uses `codex/e02-secure-desktop-shell`. A candidate branch may contain implementation, focused tests, reports, and candidate evidence and may be pushed intentionally for review, but publication does not make it accepted.
- The canonical flow is `main` → candidate branch → implementation → targeted tests → candidate commit(s) → candidate push → draft/normal PR → bounded review/repair → acceptance → merge or fast-forward to `main`. A PR means “candidate for review,” not “accepted epic.”
- Only after the required review and final gate may an epic become `ACCEPTED` and enter `main`; never put an unaccepted implementation SHA in `accepted_epics`.
- Run the current prompt named by `STATE.yaml`. The initial implementation prompt is `docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`; later prompts are prepared just in time from `docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md`.
- Use targeted tests while iterating and the risk-appropriate final gate once. Every added check must cover a named realistic failure; no arbitrary coverage target or duplicate test theater.
- Bounded repair prompts preserve accepted findings unless a direct regression is shown; derive threat boundaries from frozen architecture and never silently strengthen or weaken them.
- A material conflict with the Constitution, master specification, or accepted architecture requires `docs/development/ARCHITECTURE_DEVIATION_TEMPLATE.md` and focused review. Stop only the blocked portion.
- Validate this delivery layer with `python scripts/dev/validate_orchestration.py`; validate the frozen research foundation with `python scripts/validate_research_foundation.py`.
- Do not push automatically unless the active task explicitly authorizes publication. Record only accepted epic commits in `STATE.yaml`.

## AI Dev OS v1 — control plane

A deterministic, vendor-neutral control plane around the coding harness lives in
`.ai-dev/` (see `docs/AI_DEV_OS_IMPLEMENTATION_REPORT.md`). Key routing:

- **Risk / profile**: classify via `.ai-dev/policy/risk.yaml`; pick a profile from
  `.ai-dev/profiles/` (`balanced` default; HIGH/CRITICAL MUST NOT use `economy`).
- **Approvals**: explicit approval for the actions in `.ai-dev/policy/approvals.yaml`;
  Task Contract pre-authorization counts as approval. Protected paths are in
  `.ai-dev/policy/protected-paths.yaml` (control-plane-change flow only).
- **Skills**: `.ai-dev/skills/psyche-*.md` — orient, impact, debug, test-select,
  verify, security-change, recover, handoff (conditional: docs, tauri-runtime,
  control-plane-change).
- **Verification**: real commands in `.ai-dev/verification/commands.yaml`; gate ladder
  in `gates.yaml`. Targeted inner loop; final risk gate once.
- **Context**: `rg` → `ast-grep` → exact ranges (`.ai-dev/context-broker.md`).
- **Routing / stop**: `.ai-dev/routing/routing.yaml`. Stop or escalate on repeated
  deterministic failure, authority conflict, missing approval, environment breakage,
  provider circuit open, verifier weakening, or out-of-scope diff.
- **Telemetry**: append-only JSONL in `.ai-dev/telemetry/` (metadata-first, redacted).
- **Doctor**: `uv run python scripts/ai_dev_doctor.py`.
