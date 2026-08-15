#!/usr/bin/env python3
"""Single deterministic hook dispatcher (AI Dev OS v1).

Reads the hook JSON from stdin, dispatches on `hook_event_name`:
  - PreToolUse  -> security guard (fail-closed: exit 2 to block)
  - Stop        -> verification-gate warning (fail-open: exit 0, stdout systemMessage)
  - SessionStart-> telemetry only (exit 0)
Everything else -> exit 0 (no-op).

Kill switch: if the file `.ai-dev/hooks/DISABLED` exists, the dispatcher exits 0
immediately (fail-open) — this is the documented rollback for hook integration.

Stdlib only; runs under system Python from the hook process.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))  # .ai-dev/.. == repo root
sys.path.insert(0, _HERE)

from modules import security_guard, telemetry  # noqa: E402

DISABLED_MARKER = os.path.join(_HERE, "DISABLED")


def main() -> int:
    if os.path.exists(DISABLED_MARKER):
        return 0  # kill switch: fail-open

    raw = sys.stdin.read()
    if not raw.strip():
        return 0

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        # Cannot evaluate input; a blocking exit here could brick the session.
        # Log a warning and allow — the guard is defense-in-depth, not the sole
        # security boundary (the permission system is).
        sys.stderr.write("AI_DEV_OS dispatcher: unparseable hook input; allowing.\n")
        return 0

    event = data.get("hook_event_name", "")

    if event == "PreToolUse":
        block, reason = security_guard.check_tool_use(data, _REPO)
        telemetry.emit_tool(data, decision="deny" if block else "allow", reason=reason)
        if block:
            sys.stderr.write(f"AI_DEV_OS guard BLOCKED: {reason}\n")
            return 2
        return 0

    if event == "Stop":
        warn = security_guard.check_stop(data)
        telemetry.emit_stop(data, reason=warn)
        if warn:
            # fail-open warning: turn still ends, message surfaced to the user.
            sys.stdout.write(json.dumps({"systemMessage": warn}))
        return 0

    if event == "SessionStart":
        telemetry.emit_session_start(data)
        return 0

    # PreCompact / PostToolUse / other events: no-op.
    return 0


if __name__ == "__main__":
    sys.exit(main())
