"""Additive V9 storage for the non-canonical reflection action workspace."""

from __future__ import annotations

import hashlib
import sqlite3

V9_ADDED_TABLES = ("reflection_action_plans", "reflection_action_outcomes")

V9_MIGRATION_SQL = """
CREATE TABLE reflection_action_plans (
    plan_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK(version > 0),
    supersedes_plan_id TEXT,
    status TEXT NOT NULL CHECK(status IN ('CURRENT','SUPERSEDED','CLOSED')),
    basis_snapshot_id TEXT,
    basis_formulation_id TEXT,
    anchor_type TEXT CHECK(anchor_type IN ('UNKNOWN','CONTRADICTION','FORMULATION')),
    anchor_id TEXT,
    user_goal TEXT NOT NULL CHECK(length(user_goal) BETWEEN 1 AND 12000),
    template_id TEXT NOT NULL,
    template_version TEXT NOT NULL,
    action_text TEXT NOT NULL CHECK(length(action_text) BETWEEN 1 AND 12000),
    method_version TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE,
    FOREIGN KEY(supersedes_plan_id) REFERENCES reflection_action_plans(plan_id),
    FOREIGN KEY(basis_snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id),
    FOREIGN KEY(basis_formulation_id) REFERENCES reflection_formulations(formulation_id),
    CHECK((anchor_type IS NULL AND anchor_id IS NULL) OR (anchor_type IS NOT NULL AND anchor_id IS NOT NULL)),
    UNIQUE(session_id, version)
);
CREATE UNIQUE INDEX idx_reflection_action_plans_current ON reflection_action_plans(session_id) WHERE status='CURRENT';
CREATE INDEX idx_reflection_action_plans_history ON reflection_action_plans(session_id, version DESC);
CREATE TABLE reflection_action_outcomes (
    outcome_id TEXT PRIMARY KEY,
    plan_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK(status IN ('DONE','NOT_DONE','CANCELLED','UNKNOWN')),
    note_text TEXT CHECK(note_text IS NULL OR length(note_text) BETWEEN 1 AND 12000),
    created_at TEXT NOT NULL,
    FOREIGN KEY(plan_id) REFERENCES reflection_action_plans(plan_id) ON DELETE CASCADE
);
"""


def _statements(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete V9 migration SQL")
    return tuple(statements)


V9_MIGRATION_STATEMENTS = _statements(V9_MIGRATION_SQL)
V9_MIGRATION_CHECKSUM = hashlib.sha256(
    ";\n".join(V9_MIGRATION_STATEMENTS).encode("utf-8") + b";"
).hexdigest()
