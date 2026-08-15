# Decision — V2.0 Control Canary T0 changes (authorized)

- **Date:** 2026-08-15
- **Task:** AI-DEV-V2-CONTROL-CANARY-001 (HIGH, control plane)
- **Approval:** pre-authorized by the Task Contract `control_plane_pre_authorization`
  (`.ai-dev/contracts/AI-DEV-V2-CONTROL-CANARY-001.yaml`), which lists `.ai-dev/hooks/**`,
  `.ai-dev/telemetry/schema.json`, and `.ai-dev/state.yaml` in its exact scope. Per
  `.ai-dev/policy/approvals.yaml`, Task Contract pre-authorization counts as approval.

## Changes

1. `.ai-dev/hooks/modules/security_guard.py` — two minimal, failure-driven fixes:
   - case-insensitive protected-path comparison (Windows NTFS is case-insensitive;
     `.AI-DEV/STATE.YAML` is the same file as `.ai-dev/state.yaml`);
   - `..`/`.` normalization via `os.path.normpath` so traversal cannot reach a
     protected file without matching.
2. `.ai-dev/telemetry/schema.json` — add model/provider attestation fields
   (backward-compatible; `additionalProperties` remains true).
3. `.ai-dev/state.yaml` — add a `v2_control_canary` section; V1 fields are unchanged.

## Affected invariants

- Protected-path guard (defense-in-depth) — strengthened, not weakened.
- No change to kill-switch, PreToolUse block, or Stop fail-open semantics.

## Rollback

- Revert the three files to `ceb3031dd5d7d75564691f59ddf6e23dd71a812f`.
- V2 remains inactive unless explicitly invoked; no history rewrite or destructive
  cleanup is required.
