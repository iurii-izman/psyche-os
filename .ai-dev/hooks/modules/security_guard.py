"""Security guard — protected paths and destructive commands (fail-closed).

Violations return (True, reason) and the dispatcher exits 2 (blocking).
No violation returns (False, ""). Non-blocking cases never raise.
"""
from __future__ import annotations

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
            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            protected = data.get("protected", [])
            if protected:
                return [str(p) for p in protected]
    except Exception:
        pass
    return list(DEFAULT_PROTECTED)


def _norm(p: str) -> str:
    p = os.path.normpath(p).replace("\\", "/")
    while p.startswith("./"):
        p = p[2:]
    return p


def _path_key(p: str) -> str:
    """Return the filesystem-appropriate comparison form for a normalized path."""
    return os.path.normcase(_norm(p)).replace("\\", "/")


def _relativize(target: str, repo: str) -> str:
    """Reduce an absolute path under `repo` to a repo-relative path.

    Claude Code passes absolute tool paths (e.g. C:\\...\\.ai-dev\\state.yaml)
    while the protected list uses repo-relative entries. Without this, absolute
    targets never match and the guard silently allows protected-path edits.
    """
    t = _norm(target)
    r = _norm(os.path.abspath(repo)).rstrip("/")
    if _path_key(t) == _path_key(r):
        return ""
    prefix = _path_key(r) + "/"
    if _path_key(t).startswith(prefix):
        return t[len(r) + 1:]
    return t


def _is_protected(target: str, repo: str, protected: list) -> bool:
    t = _path_key(_relativize(target, repo))
    for p in protected:
        pn = _path_key(p)
        if t == pn or (pn and t.startswith(pn.rstrip("/") + "/")):
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
