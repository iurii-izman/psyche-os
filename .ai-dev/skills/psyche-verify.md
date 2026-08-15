# psyche-verify

WHEN TO USE: deciding and running the right verification for a change.

INPUTS: risk level, affected files, Task Contract.

STEPS:
1. Select gates from `.ai-dev/verification/gates.yaml` by changed area (python / ts / rust).
2. Inner loop: run targeted checks (ruff, mypy, targeted pytest) per edit batch.
3. Final gate (once, risk-appropriate): full pytest + orchestration + research
   validators (`.ai-dev/verification/commands.yaml`).
4. Record exit code + result in telemetry/snapshot.

OUTPUT: PASS/FAIL per gate with evidence.

STOP CONDITIONS: do not weaken the gate to pass (anti-reward-hacking). A repeated
deterministic failure → escalate, do not retry-until-green.

ALLOWED TOOLS: run verification commands.

FORBIDDEN SIDE EFFECTS: no editing of verification commands, no `noqa`/`type: ignore`
solely to silence errors.
