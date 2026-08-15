# Task Packet — AI-DEV-V2-CONTROL-CANARY-001


- task_id: AI-DEV-V2-CONTROL-CANARY-001
- base_sha: ceb3031dd5d7d75564691f59ddf6e23dd71a812f
- risk: high
- profile: quality
- acceptance_blocked: false

## Goal
- goal: Implement the bounded AI Dev OS V2.0 Control Intelligence Canary.
  Preserve V1 as an immediately usable rollback path.
  Prepare deterministic field observation on PREPARE E11 without implementing E11.

## Non-goals
- non_goals: Full AI Dev OS V2 rollout.
  E11 product implementation.
  REAL_DATA_GATE changes.
  Pathfinder, SymLens, Reasonix, projectmem, Codebase-Memory, selective testing, vector memory, new harness or multi-agent production adoption.
  Product/application refactoring.
  Dependency upgrades unrelated to this canary.

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

## Expected scope
- expected_scope: .ai-dev/contracts/**
  .ai-dev/evidence/**
  .ai-dev/hooks/**
  .ai-dev/telemetry/schema.json
  .ai-dev/telemetry/**
  .ai-dev/verification/**
  .ai-dev/routing/**
  .ai-dev/state.yaml
  scripts/ai_dev_*.py
  docs/AI_DEV_OS_V2_DRAFT.md
  docs/AI_DEV_OS_V2_CANARY_REPORT.md
  focused control-plane tests

## Protected scope
- protected_scope: CONSTITUTION.md
  docs/AI_DEV_OS_V1.md
  docs/AI_DEV_OS_RESEARCH_CATALOG_V1.docx
  src/psyche_os/**
  desktop/**
  docs/development/STATE.yaml

## Acceptance
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

## Verification
- verification: focused V2 control-plane tests during implementation
  existing dispatcher tests
  telemetry self-test
  uv run python scripts/ai_dev_doctor.py
  uv run python scripts/dev/validate_orchestration.py
  one final uv run pytest -q
  current Ruff/mypy diagnostic ratchet with version/config compatibility evidence
  application-source diff check

## Permissions
- network: False
- dependencies: False
- migrations: False
- destructive: False
- control_plane_change: True

## Routing / model request
- initial: strong
- max_grounded_retry: 1
- escalation: stop_and_report

## Attestation summary
- configured_provider: deepseek
- configured_model: deepseek-v4-pro
- requested_model: deepseek-v4-pro
- harness_reported_model: claude-opus-5[1m]
- provider_mapping: None
- effective_backend_model: UNKNOWN
- effective_backend_observable: False
- attestation_status: HARNESS_ONLY
- evidence_source: ['env:DEEPSEEK_API_KEY present', 'env:ANTHROPIC_BASE_URL present (host=127.0.0.1)', 'config:cc-switch present', 'cc-switch: no current claude-harness provider (upstream unproven)']
