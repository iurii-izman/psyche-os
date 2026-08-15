# psyche-control-plane-change  (conditional)

WHEN TO USE: a change is required under `.ai-dev/policy/`, `AGENTS.md`, or the
verification/hooks definitions (T0 protected paths).

INPUTS: the proposed change + why it is required.

STEPS:
1. Confirm it is genuinely required and cannot be expressed in task scope.
2. Record a decision entry (`docs/DECISION_LOG.md` or `.ai-dev/evidence/decisions/`)
   with reason, affected invariants, and rollback.
3. Obtain explicit approval (approvals matrix). This skill does NOT grant approval.

OUTPUT: an approval-gated change to the control plane.

STOP CONDITIONS: no silent self-modification of verifier/policy/acceptance. Without
approval, the change is blocked, not performed.

ALLOWED TOOLS: Read, Write, Edit (only after approval).

FORBIDDEN SIDE EFFECTS: no weakening acceptance/verifier to pass a gate.
