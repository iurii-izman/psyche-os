"""Additive V3-A1 Guided Exploration interaction-workspace schema."""
from __future__ import annotations

import hashlib
import sqlite3

from psyche_os.storage.v3a0_session_schema import V6_INVENTORY

V7_ADDED_TABLES = (
    "reflection_explorations", "reflection_exploration_snapshots",
    "reflection_context_items", "reflection_context_sources",
    "reflection_hypotheses", "reflection_questions", "reflection_formulations",
)
V7_INVENTORY = V6_INVENTORY + V7_ADDED_TABLES
V7_MIGRATION_SQL = """
CREATE TABLE reflection_explorations (session_id TEXT PRIMARY KEY, latest_snapshot_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE);
CREATE TABLE reflection_exploration_snapshots (snapshot_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0), method_version TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, UNIQUE(session_id, version));
CREATE TABLE reflection_context_items (context_item_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, dimension TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('KNOWN','UNKNOWN','CONTRADICTION')), text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 12000), state TEXT NOT NULL CHECK(state IN ('OPEN','RESOLVED','SKIPPED','UNRESOLVED')), created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE);
CREATE TABLE reflection_context_sources (context_item_id TEXT NOT NULL, turn_id TEXT NOT NULL, PRIMARY KEY(context_item_id, turn_id), FOREIGN KEY(context_item_id) REFERENCES reflection_context_items(context_item_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE);
CREATE TABLE reflection_hypotheses (hypothesis_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, template_id TEXT NOT NULL, proposal_text TEXT NOT NULL CHECK(length(proposal_text) BETWEEN 1 AND 480), uncertainty_text TEXT NOT NULL CHECK(length(uncertainty_text) BETWEEN 1 AND 480), discriminator_text TEXT NOT NULL CHECK(length(discriminator_text) BETWEEN 1 AND 480), created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE);
CREATE TABLE reflection_questions (question_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, dimension TEXT NOT NULL, text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 480), status TEXT NOT NULL CHECK(status IN ('PROPOSED','ANSWERED','SKIPPED')), created_at TEXT NOT NULL, answered_turn_id TEXT, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(answered_turn_id) REFERENCES reflection_turns(turn_id) ON DELETE SET NULL);
CREATE TABLE reflection_formulations (formulation_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0), parent_formulation_id TEXT, snapshot_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('PROPOSED','ACCEPTED','REJECTED','SUPERSEDED')), summary TEXT NOT NULL CHECK(length(summary) BETWEEN 1 AND 12000), correction_text TEXT, method_version TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, FOREIGN KEY(parent_formulation_id) REFERENCES reflection_formulations(formulation_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id), UNIQUE(session_id, version));
CREATE INDEX idx_reflection_context_session ON reflection_context_items(session_id, dimension, kind);
CREATE INDEX idx_reflection_questions_active ON reflection_questions(session_id, status, created_at);
CREATE INDEX idx_reflection_formulations_session ON reflection_formulations(session_id, version DESC);
"""

def _split(script: str) -> tuple[str, ...]:
    buffer = ""
    statements: list[str] = []
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete V3-A1 migration SQL")
    return tuple(statements)

V7_MIGRATION_STATEMENTS = _split(V7_MIGRATION_SQL)
V7_MIGRATION_CHECKSUM = hashlib.sha256((";\n".join(V7_MIGRATION_STATEMENTS) + ";").encode()).hexdigest()
