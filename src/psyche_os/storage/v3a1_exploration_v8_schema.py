"""Forward-only V3-A1 semantic compatibility migration."""
from __future__ import annotations

import hashlib
import sqlite3

from psyche_os.storage.v3a1_exploration_schema import V7_INVENTORY

V8_ADDED_TABLES = (
    "reflection_hypothesis_context_refs",
    "reflection_snapshot_context_items",
    "reflection_snapshot_hypotheses",
    "reflection_snapshot_questions",
)
V8_INVENTORY = V7_INVENTORY + V8_ADDED_TABLES
V8_MIGRATION_SQL = """
CREATE TABLE reflection_hypothesis_context_refs (hypothesis_id TEXT NOT NULL, context_item_id TEXT NOT NULL, relation TEXT NOT NULL CHECK(relation IN ('SUPPORT','COUNTEREVIDENCE','UNKNOWN')), PRIMARY KEY(hypothesis_id, context_item_id, relation), FOREIGN KEY(hypothesis_id) REFERENCES reflection_hypotheses(hypothesis_id) ON DELETE CASCADE, FOREIGN KEY(context_item_id) REFERENCES reflection_context_items(context_item_id) ON DELETE CASCADE);
CREATE TABLE reflection_snapshot_context_items (snapshot_id TEXT NOT NULL, context_item_id TEXT NOT NULL, dimension TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('KNOWN','UNKNOWN','CONTRADICTION')), text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 12000), state TEXT NOT NULL CHECK(state IN ('OPEN','RESOLVED','SKIPPED','UNRESOLVED')), PRIMARY KEY(snapshot_id, context_item_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(context_item_id) REFERENCES reflection_context_items(context_item_id) ON DELETE CASCADE);
CREATE TABLE reflection_snapshot_hypotheses (snapshot_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL, PRIMARY KEY(snapshot_id, hypothesis_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(hypothesis_id) REFERENCES reflection_hypotheses(hypothesis_id) ON DELETE CASCADE);
CREATE TABLE reflection_snapshot_questions (snapshot_id TEXT NOT NULL, question_id TEXT NOT NULL, dimension TEXT NOT NULL, text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 480), status TEXT NOT NULL CHECK(status IN ('PROPOSED','ANSWERED','SKIPPED')), PRIMARY KEY(snapshot_id, question_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(question_id) REFERENCES reflection_questions(question_id) ON DELETE CASCADE);
CREATE TABLE reflection_formulations_v8 (formulation_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0), parent_formulation_id TEXT, snapshot_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('PROPOSED','CURRENT','REJECTED','SUPERSEDED')), summary TEXT NOT NULL CHECK(length(summary) BETWEEN 1 AND 12000), correction_text TEXT, method_version TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, FOREIGN KEY(parent_formulation_id) REFERENCES reflection_formulations_v8(formulation_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id), UNIQUE(session_id, version));
INSERT INTO reflection_formulations_v8 SELECT formulation_id,session_id,version,parent_formulation_id,snapshot_id,CASE status WHEN 'ACCEPTED' THEN 'CURRENT' ELSE status END,summary,correction_text,method_version,created_at,updated_at FROM reflection_formulations;
DROP TABLE reflection_formulations;
ALTER TABLE reflection_formulations_v8 RENAME TO reflection_formulations;
CREATE INDEX idx_reflection_formulations_session ON reflection_formulations(session_id, version DESC);
CREATE UNIQUE INDEX idx_reflection_formulations_current ON reflection_formulations(session_id) WHERE status='CURRENT';
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
        raise ValueError("Incomplete V3-A1 V8 migration SQL")
    return tuple(statements)


V8_MIGRATION_STATEMENTS = _split(V8_MIGRATION_SQL)
V8_MIGRATION_CHECKSUM = hashlib.sha256((";\n".join(V8_MIGRATION_STATEMENTS) + ";").encode()).hexdigest()
