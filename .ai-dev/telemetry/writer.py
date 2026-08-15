#!/usr/bin/env python3
"""Append-only JSONL telemetry writer with redaction (stdlib only).

Usage:
  python writer.py --dir <telemetry-dir> --event '<json>'
  python writer.py --dir <telemetry-dir> --stdin
  python writer.py --dir <telemetry-dir> --self-test

Never persists secrets, tokens, credentials, raw prompts/tool outputs, or private
chain-of-thought. Unobservable fields are written as null/unknown, never inferred.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
import uuid

REDACT = "[REDACTED]"

DEFAULT_REDACT_VALUE_KEYS = [
    "api_key", "apikey", "token", "secret", "password", "passwd",
    "authorization", "auth", "cookie", "credential", "private_key",
    "client_secret", "access_key", "session_key",
]

DEFAULT_DROP_FIELDS = [
    "raw_prompt", "prompt", "messages", "tool_output", "tool_input",
    "transcript", "chain_of_thought", "reasoning", "cot",
    "source_code_dump", "full_diff",
]

DEFAULT_REDACT_PATTERNS = [
    r"(?i)(sk|pk|rk)-[a-z0-9]{16,}",
    r"(?i)ghp_[a-z0-9]{36,}",
    r"(?i)github_pat_[a-z0-9_]{22,}",
    r"AKIA[0-9A-Z]{16}",
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----",
]


def load_config(telemetry_dir: str) -> dict:
    cfg = {
        "redact_value_keys": list(DEFAULT_REDACT_VALUE_KEYS),
        "drop_fields": list(DEFAULT_DROP_FIELDS),
        "redact_patterns": list(DEFAULT_REDACT_PATTERNS),
    }
    path = os.path.join(telemetry_dir, "redaction.yaml")
    if os.path.isfile(path):
        try:
            import yaml  # type: ignore  # optional

            with open(path, encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            cfg["redact_value_keys"].extend(data.get("redact_value_keys", []))
            cfg["drop_fields"].extend(data.get("drop_fields", []))
            cfg["redact_patterns"].extend(data.get("redact_patterns", []))
        except Exception:
            pass  # fall back to built-in defaults
    return cfg


def _key_sensitive(key: str, cfg: dict) -> bool:
    kl = key.lower().replace("-", "_")
    return any(k in kl for k in cfg["redact_value_keys"])


def _key_dropped(key: str, cfg: dict) -> bool:
    kl = key.lower().replace("-", "_")
    return any(k == kl for k in cfg["drop_fields"])


def redact(obj, cfg: dict):
    patterns = [re.compile(p) for p in cfg["redact_patterns"]]
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if _key_dropped(str(k), cfg):
                continue
            if _key_sensitive(str(k), cfg):
                out[k] = REDACT
            else:
                out[k] = redact(v, cfg)
        return out
    if isinstance(obj, list):
        return [redact(x, cfg) for x in obj]
    if isinstance(obj, str):
        for p in patterns:
            obj = p.sub(REDACT, obj)
        return obj
    return obj


def _now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def _default_event(event: dict) -> dict:
    event.setdefault("schema_version", 1)
    event.setdefault("run_id", uuid.uuid4().hex)
    event.setdefault("timestamp", _now_iso())
    return event


def write_event(event: dict, data_dir: str) -> str:
    os.makedirs(data_dir, exist_ok=True)
    path = os.path.join(data_dir, "events.jsonl")
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return path


def run(telemetry_dir: str, event: dict) -> dict:
    cfg = load_config(telemetry_dir)
    event = _default_event(event)
    redacted = redact(event, cfg)
    data_dir = os.path.join(telemetry_dir, "data")
    path = write_event(redacted, data_dir)
    return {"path": path, "event": redacted}


def self_test(telemetry_dir: str) -> int:
    event = {
        "event_type": "session_meta",
        "task_id": "SYNTHETIC-SELF-TEST",
        "risk": "low",
        "profile": "balanced",
        "harness": "test",
        "api_key": "SYNTHETIC-CANARY-NOT-A-SECRET",
        "secret": "should-not-persist",
        "raw_prompt": "should-be-dropped",
        "output": 42,
        "cache_read": None,
        "note": "ordinary field survives",
    }
    result = run(telemetry_dir, event)
    ev = result["event"]
    assert ev["api_key"] == REDACT, "secret not redacted"
    assert ev["secret"] == REDACT, "secret not redacted"
    assert "raw_prompt" not in ev, "raw_prompt not dropped"
    assert ev["output"] == 42, "ordinary value corrupted"
    assert ev["cache_read"] is None, "null value corrupted"
    assert ev["note"] == "ordinary field survives", "ordinary string corrupted"
    print("SELF-TEST OK ->", result["path"])
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="AI Dev OS telemetry writer")
    ap.add_argument("--dir", default=None, help="telemetry dir (default: repo .ai-dev/telemetry)")
    ap.add_argument("--event", default=None, help="JSON event string")
    ap.add_argument("--stdin", action="store_true", help="read JSON event from stdin")
    ap.add_argument("--self-test", action="store_true", help="write a synthetic redacted event")
    args = ap.parse_args(argv)

    telemetry_dir = args.dir or os.environ.get("AI_DEV_TELEMETRY_DIR")
    if not telemetry_dir:
        telemetry_dir = os.path.join(".ai-dev", "telemetry")

    if args.self_test:
        return self_test(telemetry_dir)

    if args.stdin:
        event = json.load(sys.stdin)
    elif args.event:
        event = json.loads(args.event)
    else:
        ap.error("provide --event, --stdin, or --self-test")

    result = run(telemetry_dir, event)
    print(json.dumps(result["event"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
