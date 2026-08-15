# psyche-handoff

WHEN TO USE: handing a task to a fresh session/reviewer or closing a session.

INPUTS: Task Contract, latest snapshot, verification state.

STEPS:
1. Ensure Task Snapshot + Recovery Packet are current.
2. Ensure telemetry is closed and redacted (no secrets/private reasoning).
3. Summarize: base_sha, changed files, verification result, next action.

OUTPUT: a handoff note + preserved artifacts (snapshot, recovery packet, telemetry).

STOP CONDITIONS: do not hand off a broken intermediate state as done. State clearly
what is unresolved.

ALLOWED TOOLS: Read, git status/diff, telemetry writer.

FORBIDDEN SIDE EFFECTS: no claiming verification passed when it did not.
