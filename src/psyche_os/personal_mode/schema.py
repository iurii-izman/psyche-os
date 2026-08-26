"""Fresh, minimal V10 SQLCipher schema for the Personal profile only.

Personal Mode starts at V10 and has no archive, actions/outcomes, import,
assessment, longitudinal, or provider tables. Existing legacy migration is
handled separately by the approved generalized V10 migrator.
"""

from __future__ import annotations

from typing import Any

_DDL = (
    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, label TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT (datetime('now')), checksum TEXT NOT NULL)",
    "CREATE TABLE reflection_sessions (session_id TEXT PRIMARY KEY, title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160), state TEXT NOT NULL CHECK(state IN ('ACTIVE','CLOSED')), retention TEXT NOT NULL CHECK(retention='ENCRYPTED_LOCAL'), data_mode TEXT NOT NULL CHECK(data_mode='real_personal'), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, closed_at TEXT, turn_count INTEGER NOT NULL DEFAULT 0 CHECK(turn_count >= 0))",
    "CREATE TABLE reflection_turns (turn_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, sequence INTEGER NOT NULL CHECK(sequence > 0), actor TEXT NOT NULL CHECK(actor='USER'), created_at TEXT NOT NULL, content TEXT NOT NULL CHECK(length(content) BETWEEN 1 AND 12000), UNIQUE(session_id, sequence), FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_explorations (session_id TEXT PRIMARY KEY, latest_snapshot_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_exploration_snapshots (snapshot_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0), method_version TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, UNIQUE(session_id, version))",
    "CREATE TABLE reflection_context_items (context_item_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, dimension TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('KNOWN','UNKNOWN','CONTRADICTION')), text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 12000), state TEXT NOT NULL CHECK(state IN ('OPEN','RESOLVED','SKIPPED','UNRESOLVED')), created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_context_sources (context_item_id TEXT NOT NULL, turn_id TEXT NOT NULL, PRIMARY KEY(context_item_id, turn_id), FOREIGN KEY(context_item_id) REFERENCES reflection_context_items(context_item_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_hypotheses (hypothesis_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, template_id TEXT NOT NULL, proposal_text TEXT NOT NULL CHECK(length(proposal_text) BETWEEN 1 AND 480), uncertainty_text TEXT NOT NULL CHECK(length(uncertainty_text) BETWEEN 1 AND 480), discriminator_text TEXT NOT NULL CHECK(length(discriminator_text) BETWEEN 1 AND 480), created_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_hypothesis_context_refs (hypothesis_id TEXT NOT NULL, context_item_id TEXT NOT NULL, relation TEXT NOT NULL CHECK(relation IN ('SUPPORT','COUNTEREVIDENCE','UNKNOWN')), PRIMARY KEY(hypothesis_id, context_item_id, relation), FOREIGN KEY(hypothesis_id) REFERENCES reflection_hypotheses(hypothesis_id) ON DELETE CASCADE, FOREIGN KEY(context_item_id) REFERENCES reflection_context_items(context_item_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_questions (question_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, snapshot_id TEXT NOT NULL, dimension TEXT NOT NULL, text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 480), status TEXT NOT NULL CHECK(status IN ('PROPOSED','ANSWERED','SKIPPED')), created_at TEXT NOT NULL, answered_turn_id TEXT, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(answered_turn_id) REFERENCES reflection_turns(turn_id) ON DELETE SET NULL)",
    "CREATE TABLE reflection_snapshot_context_items (snapshot_id TEXT NOT NULL, context_item_id TEXT NOT NULL, dimension TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('KNOWN','UNKNOWN','CONTRADICTION')), text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 12000), state TEXT NOT NULL CHECK(state IN ('OPEN','RESOLVED','SKIPPED','UNRESOLVED')), PRIMARY KEY(snapshot_id, context_item_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(context_item_id) REFERENCES reflection_context_items(context_item_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_snapshot_hypotheses (snapshot_id TEXT NOT NULL, hypothesis_id TEXT NOT NULL, PRIMARY KEY(snapshot_id, hypothesis_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(hypothesis_id) REFERENCES reflection_hypotheses(hypothesis_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_snapshot_questions (snapshot_id TEXT NOT NULL, question_id TEXT NOT NULL, dimension TEXT NOT NULL, text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 480), status TEXT NOT NULL CHECK(status IN ('PROPOSED','ANSWERED','SKIPPED')), PRIMARY KEY(snapshot_id, question_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id) ON DELETE CASCADE, FOREIGN KEY(question_id) REFERENCES reflection_questions(question_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_formulations (formulation_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, version INTEGER NOT NULL CHECK(version > 0), parent_formulation_id TEXT, snapshot_id TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('PROPOSED','CURRENT','REJECTED','SUPERSEDED')), summary TEXT NOT NULL CHECK(length(summary) BETWEEN 1 AND 12000), correction_text TEXT, method_version TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, FOREIGN KEY(parent_formulation_id) REFERENCES reflection_formulations(formulation_id), FOREIGN KEY(snapshot_id) REFERENCES reflection_exploration_snapshots(snapshot_id), UNIQUE(session_id, version))",
    "CREATE INDEX idx_reflection_sessions_updated ON reflection_sessions(updated_at DESC)",
    "CREATE INDEX idx_reflection_turns_session_sequence ON reflection_turns(session_id, sequence)",
    "CREATE INDEX idx_reflection_context_session ON reflection_context_items(session_id, dimension, kind)",
    "CREATE INDEX idx_reflection_questions_active ON reflection_questions(session_id, status, created_at)",
    "CREATE INDEX idx_reflection_formulations_session ON reflection_formulations(session_id, version DESC)",
    "CREATE UNIQUE INDEX idx_reflection_formulations_current ON reflection_formulations(session_id) WHERE status='CURRENT'",
)

_V11_DDL = (
    "CREATE TABLE reflection_ai_provenance (formulation_id TEXT PRIMARY KEY, origin TEXT NOT NULL CHECK(origin='AI'), provider TEXT NOT NULL, requested_model TEXT NOT NULL, actual_model TEXT NOT NULL, config_digest TEXT NOT NULL, method_version TEXT NOT NULL, context_manifest_id TEXT NOT NULL, disclosure_receipt_id TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(formulation_id) REFERENCES reflection_formulations(formulation_id) ON DELETE CASCADE)",
    "CREATE TABLE reflection_ai_provenance_sources (formulation_id TEXT NOT NULL, turn_id TEXT NOT NULL, PRIMARY KEY(formulation_id,turn_id), FOREIGN KEY(formulation_id) REFERENCES reflection_ai_provenance(formulation_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
)

# Kept public so the Personal integrity oracle has one authoritative inventory
# rather than duplicating the current schema shape.
PERSONAL_V10_INVENTORY = (
    "schema_migrations", "reflection_sessions", "reflection_turns",
    "reflection_explorations", "reflection_exploration_snapshots",
    "reflection_context_items", "reflection_context_sources", "reflection_hypotheses",
    "reflection_hypothesis_context_refs", "reflection_questions",
    "reflection_snapshot_context_items", "reflection_snapshot_hypotheses",
    "reflection_snapshot_questions", "reflection_formulations",
)
PERSONAL_V11_INVENTORY = (*PERSONAL_V10_INVENTORY, "reflection_ai_provenance", "reflection_ai_provenance_sources")


def initialize_personal_v10(connection: Any) -> None:
    """Create or validate the exact Personal-only V10 schema, fail closed."""
    existing = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    if existing:
        versions = connection.execute("SELECT version FROM schema_migrations").fetchall()
        if versions != [(10,)]:
            raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
        return
    with connection:
        for statement in _DDL:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO schema_migrations(version,label,checksum) VALUES(10,?,?)",
            ("pmv1_personal_reflection_v10", "personal-v10"),
        )


def migrate_personal_v11(connection: Any) -> None:
    """Atomic additive provenance migration; V10 rows and bytes remain intact."""
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    if versions == [10, 11]:
        return
    if versions != [10]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V11_DDL:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(11,?,?)", ("pmv1_ai_working_formulation_provenance_v11", "personal-v11-ai-provenance"))


def initialize_personal_v11(connection: Any) -> None:
    """Current Personal schema: initialize V10, then apply only V10→V11."""
    existing = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    if not existing:
        initialize_personal_v10(connection)
    migrate_personal_v11(connection)
