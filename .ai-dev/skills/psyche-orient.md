# psyche-orient

WHEN TO USE: at the start of any non-trivial task, before editing code.

INPUTS: task goal, risk level (from `.ai-dev/policy/risk.yaml`).

STEPS:
1. Resolve authority: `CONSTITUTION.md` → `docs/PSYCHE_OS_MASTER_SPEC_v2.1_PRODUCT_REORIENTATION.md`
   → `docs/DECISION_LOG.md` → `docs/ROADMAP.md` + `docs/development/EPIC_MAP.md`.
2. Read the relevant spec/ADR sections only (exact ranges, not whole files).
3. Locate code with `rg` (exact lexical) then `ast-grep` (structural), per
   `.ai-dev/context-broker.md`.
4. Identify expected vs protected scope and write a short Task Contract
   (`.ai-dev/contracts/task-contract.template.yaml`).

OUTPUT: a filled Task Contract (scope, risk, acceptance, verification) and the exact
source ranges that matter.

STOP CONDITIONS: material conflict with higher authority → stop and run
`psyche-control-plane-change` (or architecture-deviation) rather than proceed.

ALLOWED TOOLS: Read, Glob, Grep, rg, ast-grep, git (read-only).

FORBIDDEN SIDE EFFECTS: no edits, no dependency changes, no tool installation.
