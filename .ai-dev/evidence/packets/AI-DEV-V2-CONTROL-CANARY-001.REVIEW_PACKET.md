# Review Packet — AI-DEV-V2-CONTROL-CANARY-001


- task_id: AI-DEV-V2-CONTROL-CANARY-001
- base_sha: ceb3031dd5d7d75564691f59ddf6e23dd71a812f
- candidate_sha: b81c53b4275a1fc6b3dc9bbd4a62f43b1fc8857c
- risk: high
- acceptance_blocked: false

## Changed files
- changed_files: .ai-dev/contracts/AI-DEV-V2-CONTROL-CANARY-001.yaml
  .ai-dev/evidence/attestation/AI-DEV-V2-CONTROL-CANARY-001.attest.yaml
  .ai-dev/evidence/decisions/V2-CANARY-CONTROL-PLANE-CHANGE.md
  .ai-dev/evidence/diagnostics/historical-debt.yaml
  .ai-dev/evidence/diagnostics/history.jsonl
  .ai-dev/evidence/diagnostics/mypy.baseline.yaml
  .ai-dev/evidence/diagnostics/ruff.baseline.yaml
  .ai-dev/evidence/packets/AI-DEV-V2-CONTROL-CANARY-001.TASK_PACKET.md
  .ai-dev/hooks/modules/security_guard.py
  .ai-dev/routing/provider-mapping.yaml
  .ai-dev/state.yaml
  .ai-dev/telemetry/schema.json
  docs/AI_DEV_OS_V2_CANARY_REPORT.md
  docs/AI_DEV_OS_V2_DRAFT.md
  scripts/ai_dev_doctor.py
  scripts/ai_dev_v2.py
  tests/control_plane/test_attestation.py
  tests/control_plane/test_authority_guard.py
  tests/control_plane/test_hook_conformance.py
  tests/control_plane/test_packet_compiler.py
  tests/control_plane/test_ratchet.py
  tests/control_plane/test_telemetry_redaction.py

## Frozen acceptance / invariants
- acceptance: V1 rollback path remains functional.
  Model/provider attestation records configured/requested/harness/effective concepts without unsupported inference.
  Diagnostic baseline ratchet detects incompatible tool/config baselines and no-new findings deterministically.
  Hook conformance covers Windows absolute/mixed/case/worktree protected-path cases.
  HIGH/CRITICAL unresolved authority conflicts cannot produce acceptance-ready state/packet.
  Task and Review packet rendering is deterministic.
  Doctor/control-canary verification passes.
  Existing V1 dispatcher/telemetry/security behavior does not regress.
  Application-source diff is zero.
  No LAB capability is promoted.
  V2 remains CANARY, not production-ready, until PREPARE E11 field observation.

## Authority
- highest: CONSTITUTION.md
  docs/AI_DEV_OS_V1.md
  AGENTS.md

- supporting: .ai-dev/README.md
  .ai-dev/policy/approvals.yaml
  .ai-dev/policy/protected-paths.yaml
  .ai-dev/routing/routing.yaml
  .ai-dev/verification/commands.yaml
  .ai-dev/verification/gates.yaml
  .ai-dev/state.yaml

- implementation_precedent: E10 implementation/review/acceptance evidence
  existing V1 dispatcher, telemetry, doctor and Task Contract

## Authority conflicts
- status: none
- items: (none)

## Verification evidence
- app_source_diff: 0 changes under src/ and desktop/
- dispatcher_smoke: ALL PASS (uv run python .ai-dev/hooks/test_dispatcher.py)
- doctor: RESULT: PASS
- focused_v2_tests: 69 passed (uv run pytest tests/control_plane/ -q)
- full_pytest: 713 passed, 2 skipped (pre-existing symlink skips)
- mypy_ratchet: PASS - no new diagnostics
- orchestration: 113 passed, 1 failed (branch-name gate, pre-existing)
- packet_determinism: byte-identical on repeat render
- ruff_ratchet: PASS - no new diagnostics
- telemetry_self_test: SELF-TEST OK

## Model / provider attestation
- configured_provider: deepseek
- configured_model: deepseek-v4-pro
- requested_model: deepseek-v4-pro
- harness_reported_model: claude-opus-5[1m]
- provider_mapping: claude-opus* -> deepseek-v4-pro (DeepSeek Anthropic-compatible contract)
- effective_backend_model: deepseek-v4-pro
- effective_backend_observable: False
- attestation_status: MAPPED_BY_PROVIDER_CONTRACT
- evidence_source: ['env:DEEPSEEK_API_KEY present', 'env:ANTHROPIC_BASE_URL present (host=127.0.0.1)', 'config:cc-switch present']

## Known residuals
- residuals: Effective backend identity is not directly observable; attestation is MAPPED_BY_PROVIDER_CONTRACT, never CONFIRMED.
  Live network/provider probing is intentionally not implemented (not required to pass).
  Ratchet covers Ruff and mypy only; no generic scanner platform.
  Symlink/reparse conformance limited to what Windows permits without admin.
  Pre-existing endpoint_identifier_without_secret field name triggers telemetry redaction (bounded non-secret value).

## Blockers
- blockers: (none)

## Review questions / verdict requested
- review_questions: Can the requested model ever be promoted to the effective backend model?
  Can a Windows case-variant or traversal path bypass the protected-path guard?
  Can a same-count diagnostic change evade the identity-aware ratchet?
  Can an unresolved HIGH/CRITICAL authority conflict produce an acceptance-ready packet?
  Can packet output vary across renders of identical input, or leak secret/raw-prompt content?
  Can V2 become required and break the V1 rollback path?

- verdict requested: ACCEPT_CANARY | FIX_REQUIRED | REDESIGN_REQUIRED
