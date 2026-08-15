"""Security guard — protected paths and destructive commands (fail-closed).

Violations return (True, reason) and the dispatcher exits 2 (blocking).
No violation returns (False, ""). Non-blocking cases never raise.
"""
from __future__ import annotations

import json
import os
import re

# Destructive / irreversible commands that require explicit approval. Kept narrow to
# avoid false positives on legitimate cleanup (`rm -rf node_modules` is allowed; only
# root-level / history-destroying operations are blocked).
DESTRUCTIVE_PATTERNS = [
    r"\bgit\s+push\s+(-[^ ]*f|--force)\b",
    r"\bgit\s+reset\s+--hard\b",
    r"\bgit\s+clean\s+-[a-z]*[fx]",
    r"\brm\s+(-[a-z]*r[a-z]*f[a-z]*|-rf)\s+(/(?:\s|$)|~/|\.\.?/(?:\s|$)|\*)",
    r"\brmdir\s+/s\b",
    r"\bdel\s+/[sfq][a-z]*\b",
    r"\bformat\s+[a-zA-Z]:",
    r"\bmkfs\b",
    r"\bdiskpart\b",
    r"\bRemove-Item\s+[^\n]*\s+-Recurse\b",
]

# Default protected prefixes if protected-paths.yaml is missing.
DEFAULT_PROTECTED = [
    ".ai-dev/policy",
    ".ai-dev/verification",
    ".ai-dev/hooks",
    ".ai-dev/telemetry/schema.json",
    "AGENTS.md",
    "CONSTITUTION.md",
]


def _load_protected(repo: str) -> list:
    try:
        import yaml  # type: ignore  # optional

        path = os.path.join(repo, ".ai-dev", "policy", "protected-paths.yaml")
        if os.path.isfile(path):
            data = yaml.safe_load(open(path, encoding="utf-8")) or {}
            protected = data.get("protected", [])
            if protected:
                return [str(p) for p in protected]
    except Exception:
        pass
    return list(DEFAULT_PROTECTED)


def _norm(p: str) -> str:
    return p.replace("\\", "/").lstrip("./")


def _is_protected(target: str, repo: str, protected: list) -> bool:
    t = _norm(target)
    for p in protected:
        pn = _norm(p)
        if t == pn or t.startswith(pn.rstrip("/") + "/"):
            return True
    return False


def check_tool_use(data: dict, repo: str) -> tuple:
    tool = data.get("tool_name", "")
    ti = data.get("tool_input", {}) or {}

    if tool in ("Edit", "Write", "NotebookEdit", "MultiEdit"):
        fp = ti.get("file_path") or ""
        if fp and _is_protected(fp, repo, _load_protected(repo)):
            return True, f"edit to protected path blocked: {fp}"
        return False, ""

    if tool == "Bash":
        cmd = ti.get("command") or ""
        for pat in DESTRUCTIVE_PATTERNS:
            if re.search(pat, cmd, re.IGNORECASE):
                return True, f"destructive command blocked: {cmd[:120]}"
        return False, ""

    return False, ""


def check_stop(data: dict) -> str:
    """Fail-open warning: never blocks. Returns a warning string or ''."""
    if data.get("stop_hook_active"):
        return ""  # avoid the repeated-block cap
    # A real verification-gate check would read a gate marker set by the test runner.
    # v1 keeps this a warning-only signal; it does not block stop.
    return ""
