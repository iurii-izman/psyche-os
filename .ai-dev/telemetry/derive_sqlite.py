#!/usr/bin/env python3
"""Derive a SQLite store from the append-only JSONL telemetry (stdlib only).

The SQLite DB is a derived, always-rebuildable projection — the JSONL is the source
of truth. Regenerates a single `events` table mirroring the minimal schema.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys

COLS = [
    ("schema_version", "INTEGER"),
    ("run_id", "TEXT"),
    ("task_id", "TEXT"),
    ("timestamp", "TEXT"),
    ("event_type", "TEXT"),
    ("risk", "TEXT"),
    ("profile", "TEXT"),
    ("base_sha", "TEXT"),
    ("harness", "TEXT"),
    ("harness_version", "TEXT"),
    ("requested_model", "TEXT"),
    ("effective_model", "TEXT"),
    ("provider", "TEXT"),
    ("input_total", "INTEGER"),
    ("cache_read", "INTEGER"),
    ("cache_write", "INTEGER"),
    ("fresh_input", "INTEGER"),
    ("output", "INTEGER"),
    ("api_cost_actual", "REAL"),
    ("api_cost_estimated", "REAL"),
    ("tool_calls", "INTEGER"),
    ("files_read", "INTEGER"),
    ("rereads", "INTEGER"),
    ("files_changed", "INTEGER"),
    ("iterations", "INTEGER"),
    ("retries", "INTEGER"),
    ("failed_tools", "INTEGER"),
    ("failed_patches", "INTEGER"),
    ("compactions", "INTEGER"),
    ("verification_result", "TEXT"),
    ("accepted", "INTEGER"),
    ("wall_time", "REAL"),
    ("config_fingerprint", "TEXT"),
]

# SQL is assembled from the fixed COLS literal above — never from event data — and
# row values are always bound via `?` placeholders, so this is not injectable.
_COLS_SQL = ", ".join(name + " " + typ for name, typ in COLS)
_CREATE_SQL = "CREATE TABLE events (" + _COLS_SQL + ")"
_PLACEHOLDERS_SQL = ", ".join("?" for _ in COLS)
_INSERT_SQL = "INSERT INTO events VALUES (" + _PLACEHOLDERS_SQL + ")"
_COL_NAMES = [name for name, _ in COLS]


def derive(telemetry_dir: str) -> str:
    data_dir = os.path.join(telemetry_dir, "data")
    jl = os.path.join(data_dir, "events.jsonl")
    db_path = os.path.join(data_dir, "derived.sqlite")

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS events")
    cur.execute(_CREATE_SQL)  # nosemgrep: sqlalchemy-execute-raw-query — fixed schema, not user input

    n = 0
    if os.path.isfile(jl):
        with open(jl, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                row = [ev.get(name) for name in _COL_NAMES]
                cur.execute(_INSERT_SQL, row)  # nosemgrep: sqlalchemy-execute-raw-query — `?`-bound values
                n += 1
    conn.commit()
    conn.close()
    return f"{db_path} ({n} events)"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Derive SQLite telemetry store")
    ap.add_argument("--dir", default=None, help="telemetry dir")
    args = ap.parse_args(argv)
    telemetry_dir = args.dir or os.environ.get("AI_DEV_TELEMETRY_DIR") or os.path.join(".ai-dev", "telemetry")
    print(derive(telemetry_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
