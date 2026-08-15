# psyche-recover

WHEN TO USE: a task has failed or is escalating (Flash → Pro, reviewer handoff,
session end, risky operation).

INPUTS: Task Contract, current diff, the exact verifier failure.

STEPS:
1. Write a Task Snapshot (`.ai-dev/recovery/task-snapshot.template.yaml`).
2. Build a Recovery Packet (`.ai-dev/recovery/recovery-packet.template.md`):
   contract + snapshot + diff + exact failure + relevant source + attempt summary.
3. Respect circuit breakers (`.ai-dev/routing/routing.yaml`): one grounded retry,
   then escalate; provider failure → snapshot then explicit fallback/pause.

OUTPUT: a Recovery Packet (bounded, no raw transcript) and a next action.

STOP CONDITIONS: same deterministic failure twice → stop or escalate. Do not
retry-until-green. Do not pass giant logs or the full transcript to the strong model.

ALLOWED TOOLS: Read, git diff, run the failing command to capture evidence.

FORBIDDEN SIDE EFFECTS: no history rewrite, no discarding failure evidence.
