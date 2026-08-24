#!/usr/bin/env python3
"""Standalone smoke test for the hook dispatcher.

Runs dispatcher.py as a subprocess with sample PreToolUse/Stop JSON and asserts
exit codes: 0 = allow, 2 = block. Not a pytest test — runs with system Python.

Run: python .ai-dev/hooks/test_dispatcher.py
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_DISPATCHER = os.path.join(_HERE, "dispatcher.py")
_REPO = os.path.dirname(os.path.dirname(_HERE))


def run_dispatcher(payload: dict) -> int:
    p = subprocess.run(
        [sys.executable, _DISPATCHER],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )
    return p.returncode, p.stdout, p.stderr


def pre_tool(tool: str, **tool_input) -> dict:
    return {
        "session_id": "test-session",
        "hook_event_name": "PreToolUse",
        "tool_name": tool,
        "tool_input": tool_input,
        "cwd": os.path.dirname(os.path.dirname(_HERE)),
    }


def main() -> int:
    cases = []
    # (name, payload, expected_exit)
    cases.append(("protected path edit blocked", pre_tool("Edit", file_path=".ai-dev/policy/risk.yaml"), 2))
    cases.append(("protected state file blocked", pre_tool("Edit", file_path=".ai-dev/state.yaml"), 2))
    cases.append(("protected AGENTS.md edit blocked", pre_tool("Write", file_path="AGENTS.md"), 2))
    cases.append(("normal source edit allowed", pre_tool("Edit", file_path="src/psyche_os/__main__.py"), 0))
    cases.append(("absolute protected path edit blocked", pre_tool("Edit", file_path=os.path.join(_REPO, ".ai-dev", "state.yaml")), 2))
    case_variant_exit = 2 if os.path.normcase("A") != "A" else 0
    cases.append(("Windows protected-path case variant follows filesystem semantics", pre_tool("Edit", file_path=".AI-DEV/STATE.YAML"), case_variant_exit))
    cases.append(("protected path traversal blocked", pre_tool("Edit", file_path="tmp/../.ai-dev/state.yaml"), 2))
    cases.append(("protected path mixed separators blocked", pre_tool("Edit", file_path=r"tmp\..\.ai-dev\state.yaml"), 2))
    cases.append(("protected directory descendant blocked", pre_tool("Edit", file_path=".ai-dev/policy/risk.yaml"), 2))
    cases.append(("protected file near-prefix allowed", pre_tool("Edit", file_path=".ai-dev/state.yaml.backup"), 0))
    cases.append(("protected directory near-prefix allowed", pre_tool("Edit", file_path=".ai-dev/policy-notes/example.yaml"), 0))
    cases.append(("absolute normal source edit allowed", pre_tool("Edit", file_path=os.path.join(_REPO, "src", "psyche_os", "__main__.py")), 0))
    cases.append(("git force push blocked", pre_tool("Bash", command="git push --force origin main"), 2))
    cases.append(("git reset --hard blocked", pre_tool("Bash", command="git reset --hard HEAD~1"), 2))
    cases.append(("rm -rf / blocked", pre_tool("Bash", command="rm -rf /"), 2))
    cases.append(("rm -rf node_modules allowed (no false positive)", pre_tool("Bash", command="rm -rf node_modules && rm -rf build"), 0))
    cases.append(("normal test command allowed", pre_tool("Bash", command="uv run pytest -q"), 0))
    cases.append(("Stop never blocks", {"session_id": "t", "hook_event_name": "Stop", "stop_hook_active": False, "last_assistant_message": "done"}, 0))

    failed = 0
    for name, payload, expected in cases:
        rc, _out, err = run_dispatcher(payload)
        status = "PASS" if rc == expected else "FAIL"
        if rc != expected:
            failed += 1
        print(f"{status}  {name}  (exit={rc}, expected={expected})")
        if rc == 2 and err:
            print(f"        stderr: {err.strip()[:100]}")

    # Kill-switch test
    marker = os.path.join(_HERE, "DISABLED")
    open(marker, "w").close()
    try:
        rc, _, _ = run_dispatcher(pre_tool("Edit", file_path=".ai-dev/policy/risk.yaml"))
        ok = "PASS" if rc == 0 else "FAIL"
        if rc != 0:
            failed += 1
        print(f"{ok}  kill-switch DISABLED marker forces fail-open (exit={rc})")
    finally:
        os.remove(marker)

    print(f"\n{'ALL PASS' if failed == 0 else f'{failed} FAILED'}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
