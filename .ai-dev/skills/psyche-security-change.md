# psyche-security-change

WHEN TO USE: any change touching crypto, storage, policy, backup/export, permissions,
dependency trust boundary, or Tauri IPC (HIGH/CRITICAL in `.ai-dev/policy/risk.yaml`).

INPUTS: the change, its threat boundary, the Task Contract.

STEPS:
1. Confirm the change is in-scope and pre-authorized (approvals matrix).
2. State the security property being preserved/changed and what would violate it.
3. Run targeted security checks: `tests/security/`, plus conditional scanners
   (gitleaks, osv-scanner, semgrep) per `.ai-dev/capabilities/registry.yaml`.
4. For CRITICAL: require independent fresh review + human acceptance.

OUTPUT: a security-impact note + verification evidence.

STOP CONDITIONS: unexpected security-boundary change → stop and escalate. Never
disable a scanner to pass. Never expand permissions without explicit approval.

ALLOWED TOOLS: Read, rg, ast-grep, security scanners, run security tests.

FORBIDDEN SIDE EFFECTS: no weakening of invariants, no secret persistence.
