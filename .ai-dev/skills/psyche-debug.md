# psyche-debug

WHEN TO USE: a deterministic verification failure needs diagnosis.

INPUTS: failing command, exact error output, relevant source range.

STEPS:
1. Reproduce the failure with the exact command from
   `.ai-dev/verification/commands.yaml`.
2. Classify: PRE-EXISTING vs introduced-by-this-change (compare against base_sha).
3. Narrow to the minimal failing case; read the exact source that produced the error.
4. Form ONE hypothesis with observable evidence before editing.

OUTPUT: a bounded hypothesis + the minimal source range to fix.

STOP CONDITIONS:
- Same deterministic failure after the allowed retry → escalate (do not loop).
- Timeout ≠ code defect: do not change production code without evidence the cause
  is in it (see `.ai-dev/routing/routing.yaml` circuit breakers).

ALLOWED TOOLS: Read, Grep, rg, ast-grep, run verification commands.

FORBIDDEN SIDE EFFECTS: no speculative edits; no deleting/skipping/weakening tests
to gain green (anti-reward-hacking).
