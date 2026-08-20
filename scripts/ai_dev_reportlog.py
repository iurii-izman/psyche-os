#!/usr/bin/env python3
"""AI Dev OS v2 — deterministic pytest-reportlog parser (Acceleration Wave 1).

Replaces the giant pytest console stream sent to the LLM with a small, bounded,
deterministic failure packet. Full raw evidence stays on disk.

The parser understands the JSONL artifact written by the `pytest-reportlog`
plugin (`--report-log <path>`). Event types (`$report_type`):

  SessionStart     pytest_version
  CollectReport    nodeid + outcome (+ longrepr on collection error)
  TestReport       nodeid + when (setup/call/teardown) + outcome
                   (+ longrepr on failure/error/skip)
  SessionFinish    exitstatus

FAIL-CLOSED: the parser never invents a green. If the log has no SessionFinish
(truncated/crashed pytest) or the file is unreadable/malformed, the run is
reported as incomplete (exit_code None / truncated True) and the caller must
treat it as UNKNOWN, never PASS.

CLI:  uv run python scripts/ai_dev_reportlog.py <reportlog.jsonl> [--json]
Run with the same `uv` environment that produced the artifact.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re
import sys
import time
from typing import Any

SCHEMA_VERSION = 1
MAX_FAILURES = 10  # bound the AI-facing packet; full log stays on disk.
TRACEBACK_LINE_LIMIT = 6  # lines per failure excerpt.
DETAIL_FAILURES = 5  # full excerpt detail for the first N; compact beyond that.
MESSAGE_CHARS = 240

VERSION = "0.1.0"

# Deterministic secret redaction for every AI-facing rendering. This is a
# bounded local redactor (never claims perfect secret detection): it covers the
# classes already tested in the repo (OpenAI-style sk-/pk-/rk- keys, bearer
# tokens, common API-key assignments, GitHub/AWS tokens, PEM private keys).
REDACTED = "[REDACTED]"
_SECRET_PATTERNS = (
    re.compile(r"(?i)\b(sk|pk|rk)-[a-z0-9_-]{12,}\b"),
    re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{12,}\b"),
    re.compile(r"(?i)\b(ghp|gho|ghu)_[a-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?i)\b(x-api-key|api[_-]?key|authorization|access[_-]?token|auth[_-]?token"
        r"|client[_-]?secret|password|secret|token)\b\s*[:=]\s*[\"']?[A-Za-z0-9._~+/=-]{8,}"
    ),
    re.compile(r"(?i)-----BEGIN [A-Z ]*PRIVATE KEY-----"),
)


def redact_secret(text: str) -> str:
    """Redact secret-looking substrings from an AI-facing string."""
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub(REDACTED, text)
    return text


class ReportLogError(Exception):
    """Unreadable/malformed report log — must never become a green."""


def _crash_message(longrepr: Any) -> str:
    """Extract the short error message from a pytest longrepr."""
    if isinstance(longrepr, str):
        return longrepr
    if isinstance(longrepr, dict):
        crash = longrepr.get("reprcrash") or {}
        msg = crash.get("message") or ""
        if isinstance(msg, str):
            return msg
        return ""
    return ""


def _traceback_lines(longrepr: Any) -> list[str]:
    """Extract the rendered traceback lines from a pytest longrepr."""
    if isinstance(longrepr, str):
        return [ln for ln in longrepr.splitlines() if ln.strip()][: TRACEBACK_LINE_LIMIT]
    if isinstance(longrepr, dict):
        tb = longrepr.get("reprtraceback") or {}
        lines: list[str] = []
        for entry in tb.get("reprentries") or []:
            data = entry.get("data") if isinstance(entry, dict) else None
            for ln in data.get("lines") or [] if isinstance(data, dict) else []:
                if isinstance(ln, str):
                    lines.append(ln)
        if lines:
            return lines[: TRACEBACK_LINE_LIMIT]
        # No traceback entries: fall back to the crash message.
        msg = _crash_message(longrepr)
        return msg.splitlines()[: TRACEBACK_LINE_LIMIT] if msg else []
    return []


def _error_type(message: str) -> str:
    """First dotted identifier before a ':' in the message, e.g. AssertionError."""
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_.]*)", message)
    return m.group(1) if m else ""


def _bounded(text: str, limit: int = MESSAGE_CHARS) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit]}\n... [excerpt truncated {len(text) - limit} chars]"


def parse_reportlog(path: Path | str, *, command: str | None = None) -> dict[str, Any]:
    """Parse a pytest-reportlog JSONL artifact into a bounded deterministic packet."""
    p = Path(path)
    if not p.is_file():
        raise ReportLogError(f"report log artifact not found: {p}")

    collected: set[str] = set()
    passed = failed = errors = skipped = 0
    failures: list[dict[str, Any]] = []
    malformed_lines = 0
    exit_code: int | None = None
    pytest_version: str | None = None
    saw_session_finish = False
    total_bytes = 0

    with p.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if not line.strip():
                continue
            total_bytes += len(line.encode("utf-8", errors="replace"))
            try:
                ev = json_loads(line)
            except ValueError:
                malformed_lines += 1
                continue
            # A parsed JSONL event MUST be a mapping before any event handling.
            # Valid JSON with the wrong shape (null/[]/"str"/123) is a malformed
            # event, not an uncaught exception and never a green.
            if not isinstance(ev, dict):
                malformed_lines += 1
                continue
            rtype = ev.get("$report_type")
            if rtype == "SessionStart":
                pytest_version = ev.get("pytest_version")
            elif rtype == "CollectReport":
                nodeid = ev.get("nodeid")
                if ev.get("outcome") == "failed":
                    errors += 1
                    failures.append(_failure(nodeid or "", "collection", ev.get("longrepr"), len(failures)))
            elif rtype == "TestReport":
                nodeid = ev.get("nodeid") or ""
                when = ev.get("when")
                outcome = ev.get("outcome")
                if nodeid:
                    collected.add(nodeid)
                if when == "call":
                    # The call phase determines the test outcome.
                    if outcome == "failed":
                        failed += 1
                        failures.append(_failure(nodeid, when, ev.get("longrepr"), len(failures)))
                    elif outcome in ("passed", "xpassed"):
                        passed += 1
                    elif outcome in ("skipped", "xfailed"):
                        skipped += 1
                elif when in ("setup", "teardown") and outcome == "failed":
                    # Fixture setup/teardown failures are pytest ERRORS.
                    errors += 1
                    failures.append(_failure(nodeid, when, ev.get("longrepr"), len(failures)))
            elif rtype == "SessionFinish":
                saw_session_finish = True
                es = ev.get("exitstatus")
                exit_code = int(es) if isinstance(es, int) else es

    # A run that never reached SessionFinish is incomplete. It must be treated
    # as UNKNOWN by the caller, never PASS. rc is then the subprocess rc.
    truncated = not saw_session_finish or malformed_lines > 0
    # MACHINE ACCOUNTING (complete, NEVER truncated): every failing detector
    # identity and the full failure-record count. Presentation (failures) is
    # bounded; machine truth is not. Callers that need detector ground truth
    # MUST read failure_nodeids, never the bounded failures list.
    failure_nodeids = [f["nodeid"] for f in failures]
    failures_capped = failures[:MAX_FAILURES]

    return {
        "schema_version": SCHEMA_VERSION,
        "command": redact_secret(command) if command else None,
        "exit_code": exit_code,
        "truncated": truncated,
        "malformed_lines": malformed_lines,
        "pytest_version": pytest_version,
        "duration": None,  # caller fills wall-clock duration; reportlog has no session clock
        "collection": {
            "collected": len(collected),
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "errors": errors,
        },
        "failure_nodeids": failure_nodeids,
        "failure_records_count": len(failures),
        "failures": failures_capped,
        "failures_truncated": failed + errors > len(failures_capped),
        "warnings_count": 0,  # pytest-reportlog does not emit warning events
        "raw_evidence": str(p.resolve()),
        "artifact_bytes": total_bytes,
    }


def json_loads(line: str) -> dict[str, Any]:
    import json

    return json.loads(line)


def _failure(nodeid: str, phase: str, longrepr: Any, index: int) -> dict[str, Any]:
    compact = index >= DETAIL_FAILURES
    raw_message = _crash_message(longrepr)
    error_type = redact_secret(_error_type(raw_message))
    message = redact_secret(raw_message)
    if compact:
        # First line only; the AI-facing packet stays small for many-failure runs.
        message = message.splitlines()[0] if message else ""
        tb: list[str] = []
    else:
        tb = [redact_secret(ln) for ln in _traceback_lines(longrepr)]
    message = _bounded(message)
    return {
        "nodeid": nodeid,
        "phase": phase,
        "error_type": error_type,
        "message": message,
        "traceback_excerpt": "\n".join(tb) if tb else "",
    }


def render_summary(result: dict[str, Any]) -> str:
    """Render the bounded AI-facing packet (deterministic, no LLM in the loop)."""
    coll = result["collection"]
    lines: list[str] = []
    if result.get("command"):
        lines.append(f"command: {result['command']}")
    lines.append(f"exit_code: {result['exit_code']}  duration: {result['duration']}")
    lines.append(
        f"collected: {coll['collected']}  passed: {coll['passed']}  failed: {coll['failed']}  "
        f"skipped: {coll['skipped']}  errors: {coll['errors']}"
    )
    if result.get("failures"):
        lines.append(f"failures ({len(result['failures'])}):")
        for f in result["failures"]:
            lines.append(f"- {f['nodeid']}  [{f['phase']}]")
            if f["error_type"]:
                lines.append(f"  type: {f['error_type']}")
            if f["message"]:
                lines.append(f"  message: {f['message']}")
            if f["traceback_excerpt"]:
                excerpt = f["traceback_excerpt"].replace("\n", "\n  ")
                lines.append(f"  traceback:\n  {excerpt}")
        if result.get("failures_truncated"):
            lines.append(f"... {coll['failed'] + coll['errors'] - len(result['failures'])} more failure(s) in the raw artifact")
    if result.get("truncated"):
        lines.append(f"TRUNCATED: {result['malformed_lines']} malformed line(s); no clean SessionFinish — treat as UNKNOWN")
    lines.append(f"warnings_count: {result['warnings_count']}")
    lines.append(f"raw_evidence: {result['raw_evidence']}")
    return "\n".join(lines)


def cmd_parse(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ai_dev_reportlog", description="deterministic pytest-reportlog parser")
    ap.add_argument("artifact", help="path to the --report-log JSONL artifact")
    ap.add_argument("--json", action="store_true", help="emit the packet as JSON")
    ap.add_argument("--command", help="the pytest command that produced the artifact (for the packet)")
    ap.add_argument("--version", action="version", version=f"ai_dev_reportlog {VERSION} (schema {SCHEMA_VERSION})")
    args = ap.parse_args(argv)
    try:
        result = parse_reportlog(args.artifact, command=args.command)
    except ReportLogError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if args.json:
        import json

        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        print(render_summary(result))
    return 0


def main(argv: list[str] | None = None) -> int:
    return cmd_parse(argv)


if __name__ == "__main__":
    try:
        t0 = time.perf_counter()
        rc = main()
    except KeyboardInterrupt:
        sys.exit(130)
    if rc:
        sys.exit(rc)
