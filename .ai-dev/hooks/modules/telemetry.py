"""Minimal hook telemetry — metadata-only, never tool_input or secrets.

Appends one line to the append-only JSONL. Stdlib only; low-overhead for the hot path.
"""
from __future__ import annotations

import datetime
import json
import os


def _data_dir() -> str:
    here = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(here, "telemetry", "data")


def _append(event: dict) -> None:
    try:
        d = _data_dir()
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "events.jsonl")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    except Exception:
        pass  # telemetry must never block a hook; fail-open


def _now() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def emit_tool(data: dict, decision: str, reason: str = "") -> None:
    _append({
        "schema_version": 1,
        "run_id": data.get("session_id"),
        "timestamp": _now(),
        "event_type": "tool_call",
        "tool_name": data.get("tool_name"),
        "decision": decision,
        "reason": reason or None,
    })


def emit_stop(data: dict, reason: str = "") -> None:
    _append({
        "schema_version": 1,
        "run_id": data.get("session_id"),
        "timestamp": _now(),
        "event_type": "task_stop",
        "reason": reason or None,
    })


def emit_session_start(data: dict) -> None:
    _append({
        "schema_version": 1,
        "run_id": data.get("session_id"),
        "timestamp": _now(),
        "event_type": "session_meta",
        "source": data.get("source"),
        "cwd": data.get("cwd"),
    })
