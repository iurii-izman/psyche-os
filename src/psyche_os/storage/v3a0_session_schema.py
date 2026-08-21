"""Additive V3-A0 interaction-workspace schema delta."""

from __future__ import annotations

import hashlib
import sqlite3

from psyche_os.storage.e08_schema import V5_INVENTORY

V6_ADDED_TABLES = ("reflection_sessions", "reflection_turns")
V6_INVENTORY = V5_INVENTORY + V6_ADDED_TABLES

V6_MIGRATION_SQL = """
CREATE TABLE reflection_sessions (
 session_id TEXT PRIMARY KEY,
 title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
 state TEXT NOT NULL CHECK(state IN ('ACTIVE','CLOSED')),
 retention TEXT NOT NULL CHECK(retention = 'ENCRYPTED_LOCAL'),
 data_mode TEXT NOT NULL CHECK(data_mode = 'synthetic_only'),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 closed_at TEXT,
 turn_count INTEGER NOT NULL DEFAULT 0 CHECK(turn_count >= 0)
);
CREATE TABLE reflection_turns (
 turn_id TEXT PRIMARY KEY,
 session_id TEXT NOT NULL,
 sequence INTEGER NOT NULL CHECK(sequence > 0),
 actor TEXT NOT NULL CHECK(actor = 'USER'),
 created_at TEXT NOT NULL,
 content TEXT NOT NULL CHECK(length(content) BETWEEN 1 AND 12000),
 UNIQUE(session_id, sequence),
 FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE
);
CREATE INDEX idx_reflection_sessions_updated ON reflection_sessions(updated_at DESC);
CREATE INDEX idx_reflection_turns_session_sequence ON reflection_turns(session_id, sequence);
"""


def _split(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete V3-A0 migration SQL")
    return tuple(statements)


V6_MIGRATION_STATEMENTS = _split(V6_MIGRATION_SQL)
V6_MIGRATION_CHECKSUM = hashlib.sha256(
    (";\n".join(V6_MIGRATION_STATEMENTS) + ";").encode()
).hexdigest()
