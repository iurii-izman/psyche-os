# PSYCHE OS — prepare the next DeepSeek epic prompt

**Project root:** `C:\Dev\psyche-os`

Prepare exactly one next implementation prompt after the current epic is `ACCEPTED`. This is a short just-in-time coordination task, not global planning.

## Read first

1. `AGENTS.md`, `CONSTITUTION.md`, and `docs/development/STATE.yaml`.
2. `docs/development/EPIC_MAP.md` and only the next epic's section.
3. The accepted report for the current epic and its recorded commit/diff.
4. Only architecture/decision files directly changed by or depended on by that report.
5. `docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md`.
6. For E07–E11 only, read `docs/future/CONVERSATIONAL_PSYCHOLOGICAL_SUPPORT_NORTH_STAR.md` solely to preserve the listed forward-compatible extension points.

Do not reread historical v1, the giant research prompt, every prior report, the full dossier/source registry, or unrelated architecture. Do not start new research, a project-wide red team, or a master-spec rewrite.

The North Star is not implementation authority. It must not add deliverables, capabilities, data, trust boundaries, gates, or tests to the current epic; the Constitution, normative safety architecture, accepted contracts, epic map, and bounded epic prompt remain controlling.

## Procedure

1. Verify the current epic is `ACCEPTED`, its commit exists, the worktree is understood, and the planned next epic's dependencies remain valid.
2. Confirm the next epic is neither already delivered nor made obsolete by the accepted implementation. Narrow/defer it rather than inventing work.
3. Reclassify risk only if concrete changed boundaries justify it. If material architecture drift exists, require a deviation decision before preparing blocked scope.
4. Extract exact accepted toolchain/gate commands from the current repository. Do not invent commands or arbitrary coverage targets.
   Do not silently strengthen static-analysis scope beyond the accepted
   repository baseline. Until repository-wide Ruff/mypy debt is explicitly
   cleared, require strict cleanliness for touched/current-epic code plus a
   no-new-diagnostics ratchet against the exact preparation baseline. Compare
   stable diagnostic identities, not counts alone. Accepted untouched lint/type
   debt does not block an unrelated epic unless that epic materially depends on
   or changes the affected code. This does not weaken functional, safety,
   privacy, migration or FULL pytest gates.
5. Instantiate the template with one bounded objective, exact read list, relevant exclusions/invariants, named failure-driven tests, objective acceptance criteria, report path, and required review.
   For E07–E11, include only the smallest compatibility note applicable to that epic; defer every future conversational capability outside its mapped scope.
6. Save exactly one prompt as `docs/prompts/deepseek/{NEXT_ID}_{SHORT_NAME}.md`.
7. Run `python scripts/dev/validate_orchestration.py` and any prompt-specific lightweight checks.
8. At this epic boundary update `STATE.yaml`: current epic becomes the next epic with `READY`, exact prompt/risk/review fields; preserve accepted history/commit; set the following mapped epic to `PLANNED`; update `next_action`.

## Stop conditions

Stop without marking `READY` if dependencies/evidence are missing, the scope needs a material architecture or gate decision, or the prompt would request real personal/sensitive data while the gate is closed. State the smallest decision or artifact needed.

## Output

Report the created prompt path, context files, risk/final gate, whether Codex review is required, state changes, validation, and the exact command/path the user should give DeepSeek. Do not implement the epic and do not commit/push unless separately authorized.
