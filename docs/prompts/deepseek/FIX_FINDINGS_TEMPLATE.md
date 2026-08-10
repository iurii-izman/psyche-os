# PSYCHE OS — fix validated findings for epic {ID}

**Project root:** `C:\Dev\psyche-os`

Read `AGENTS.md`, `CONSTITUTION.md`, `docs/development/STATE.yaml`, the relevant epic report, and only the supplied findings below. Inspect the affected code and directly related tests; do not reload the original epic prompt or broad research context unless a finding cites it.

## Validated findings

{PASTE_SEVERITY_RANKED_ACTIONABLE_FINDINGS}

## Task

1. Reproduce or statically confirm each finding against the current diff.
2. Fix every validated in-scope issue with the smallest coherent change.
3. Add a regression test only when it protects the concrete failure from recurrence.
4. Run the affected targeted checks; then run the epic's final gate once if the fix changes a high-risk boundary or acceptance-relevant behavior.
5. Do not perform unrelated refactoring, cleanup, dependency upgrades, architecture changes, or scope expansion.
6. If a finding requires a material architecture deviation, use `docs/development/ARCHITECTURE_DEVIATION_TEMPLATE.md` and stop only that blocked portion.

Update the epic report with exact resolutions and validation. Keep `REAL_DATA_GATE = CLOSED`, use synthetic fixtures only, do not set the epic to `ACCEPTED`, and do not commit/push unless separately authorized.

Return a finding-by-finding disposition: `FIXED`, `NOT_REPRODUCIBLE` with evidence, or `BLOCKED` with the exact dependency.
