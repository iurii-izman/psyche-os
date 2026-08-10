# PSYCHE OS repository guidance

## Source of truth

- During the research rebuild, follow `docs/research/EXECUTION_PLAN.md`.
- Preserve `docs/specs/PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md` and `docs/prompts/PSYCHE_OS_FINAL_RESEARCH_MASTER_PROMPT_CODEX_SOL_ULTRA.md` unchanged as historical inputs.
- After research convergence, `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` is the authoritative product and architecture specification.

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

