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

# V12 deliberately keeps interview-specific state separate from the canonical
# USER source turns.  Interview answers are rows in reflection_turns; every
# derived interview row points back to those turns and therefore disappears
# with the source/session through ordinary foreign-key deletion.
_V12_DDL = (
    "CREATE TABLE interview_policy (policy_id TEXT PRIMARY KEY CHECK(policy_id='personal_ai_interview_v1'), enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)), updated_at TEXT NOT NULL)",
    "CREATE TABLE interview_sessions (interview_session_id TEXT PRIMARY KEY, source_session_id TEXT NOT NULL UNIQUE, state TEXT NOT NULL CHECK(state IN ('ACTIVE','END_RECOMMENDED','PAUSED','COMPLETED')), owner_topic TEXT, summary TEXT, next_direction TEXT, summary_derivation_id TEXT, next_direction_derivation_id TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, ended_at TEXT, FOREIGN KEY(source_session_id) REFERENCES reflection_sessions(session_id) ON DELETE CASCADE, FOREIGN KEY(summary_derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE SET NULL, FOREIGN KEY(next_direction_derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE SET NULL)",
    "CREATE TABLE interview_submissions (interview_session_id TEXT NOT NULL, client_submission_id TEXT NOT NULL, turn_id TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, PRIMARY KEY(interview_session_id,client_submission_id), FOREIGN KEY(interview_session_id) REFERENCES interview_sessions(interview_session_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_source_policies (turn_id TEXT PRIMARY KEY, policy_id TEXT NOT NULL UNIQUE, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)), sensitivity TEXT NOT NULL CHECK(sensitivity IN ('ordinary','sensitive','deeply_sensitive')), processing_location TEXT NOT NULL CHECK(processing_location IN ('local_only','approved_cloud')), cloud_policy TEXT NOT NULL CHECK(cloud_policy IN ('never_cloud','ask_each_time','named_purpose_and_provider')), purpose TEXT NOT NULL, provider_profile TEXT NOT NULL, third_party_scope TEXT NOT NULL CHECK(third_party_scope IN ('none','incidental','material')), lineage_rule TEXT NOT NULL, assigned_by TEXT NOT NULL CHECK(assigned_by IN ('OWNER_HISTORY_ACTION','SESSION_CONSENT')), updated_at TEXT NOT NULL, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_attempts (attempt_id TEXT PRIMARY KEY, interview_session_id TEXT NOT NULL, answer_turn_id TEXT, purpose TEXT NOT NULL CHECK(purpose='personal_ai_interview'), provider_profile TEXT NOT NULL, model TEXT NOT NULL, config_id TEXT NOT NULL, schema_id TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('PREPARED','SENT','SUCCEEDED','FAILED','OUTCOME_UNKNOWN')), policy_enabled INTEGER NOT NULL CHECK(policy_enabled IN (0,1)), source_item_count INTEGER NOT NULL, source_char_count INTEGER NOT NULL, inquiry_item_count INTEGER NOT NULL, inquiry_char_count INTEGER NOT NULL, context_char_count INTEGER NOT NULL, created_at TEXT NOT NULL, sent_at TEXT, completed_at TEXT, error_code TEXT, FOREIGN KEY(interview_session_id) REFERENCES interview_sessions(interview_session_id) ON DELETE CASCADE, FOREIGN KEY(answer_turn_id) REFERENCES reflection_turns(turn_id) ON DELETE SET NULL)",
    "CREATE TABLE interview_attempt_manifest_items (attempt_id TEXT NOT NULL, alias TEXT NOT NULL, turn_id TEXT NOT NULL, policy_id TEXT NOT NULL, ordinal INTEGER NOT NULL, char_count INTEGER NOT NULL, PRIMARY KEY(attempt_id,alias), UNIQUE(attempt_id,turn_id), FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_derivations (derivation_id TEXT PRIMARY KEY, attempt_id TEXT NOT NULL UNIQUE, validation_state TEXT NOT NULL CHECK(validation_state='VALIDATED'), created_at TEXT NOT NULL, FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_derivation_sources (derivation_id TEXT NOT NULL, turn_id TEXT NOT NULL, alias TEXT NOT NULL, PRIMARY KEY(derivation_id,turn_id), FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TRIGGER interview_derivation_source_deleted AFTER DELETE ON interview_derivation_sources BEGIN DELETE FROM interview_derivations WHERE derivation_id=OLD.derivation_id; END",
    "CREATE TRIGGER interview_derivation_deleted BEFORE DELETE ON interview_derivations BEGIN UPDATE interview_sessions SET summary=CASE WHEN summary_derivation_id=OLD.derivation_id THEN NULL ELSE summary END, summary_derivation_id=CASE WHEN summary_derivation_id=OLD.derivation_id THEN NULL ELSE summary_derivation_id END, next_direction=CASE WHEN next_direction_derivation_id=OLD.derivation_id THEN NULL ELSE next_direction END, next_direction_derivation_id=CASE WHEN next_direction_derivation_id=OLD.derivation_id THEN NULL ELSE next_direction_derivation_id END WHERE summary_derivation_id=OLD.derivation_id OR next_direction_derivation_id=OLD.derivation_id; END",
    "CREATE TABLE interview_questions (question_id TEXT PRIMARY KEY, interview_session_id TEXT NOT NULL, derivation_id TEXT NOT NULL, question TEXT NOT NULL CHECK(length(question) BETWEEN 1 AND 480), rationale TEXT NOT NULL CHECK(length(rationale) BETWEEN 1 AND 480), decision TEXT NOT NULL CHECK(decision IN ('ASK','END_RECOMMENDED')), status TEXT NOT NULL CHECK(status IN ('CURRENT','ANSWERED','SKIPPED','DECLINED','SUPERSEDED')), basis_aliases TEXT NOT NULL CHECK(json_valid(basis_aliases) AND json_type(basis_aliases)='array'), created_at TEXT NOT NULL, FOREIGN KEY(interview_session_id) REFERENCES interview_sessions(interview_session_id) ON DELETE CASCADE, FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE)",
    "CREATE UNIQUE INDEX idx_interview_current_question ON interview_questions(interview_session_id) WHERE status='CURRENT'",
    "CREATE TABLE interview_question_basis (question_id TEXT NOT NULL, alias TEXT NOT NULL, turn_id TEXT NOT NULL, PRIMARY KEY(question_id,alias), FOREIGN KEY(question_id) REFERENCES interview_questions(question_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_inquiry_items (item_id TEXT PRIMARY KEY, interview_session_id TEXT NOT NULL, derivation_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('THEME','WHITE_SPOT','REVISIT','HYPOTHESIS','CONTRADICTION','UNKNOWN')), text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 480), priority INTEGER NOT NULL CHECK(priority BETWEEN 1 AND 5), state TEXT NOT NULL CHECK(state IN ('ACTIVE','DISMISSED','INVALIDATED')), source_turn_id TEXT, created_at TEXT NOT NULL, FOREIGN KEY(interview_session_id) REFERENCES interview_sessions(interview_session_id) ON DELETE CASCADE, FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE, FOREIGN KEY(source_turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_attempt_inquiry_items (attempt_id TEXT NOT NULL, item_id TEXT NOT NULL, ordinal INTEGER NOT NULL, char_count INTEGER NOT NULL, PRIMARY KEY(attempt_id,item_id), FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE, FOREIGN KEY(item_id) REFERENCES interview_inquiry_items(item_id) ON DELETE CASCADE)",
)

# V13 adds the cross-session Personal Model: stable model items with immutable
# revisions, exact SOURCE evidence links, and owner challenges.  It is strictly
# additive: no existing table or row changes meaning, no semantic backfill of
# older interview inquiry items happens, and every derived row remains
# cascade-bound to its derivation and USER source turns.
_V13_DDL = (
    "ALTER TABLE interview_attempts ADD COLUMN model_item_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE interview_attempts ADD COLUMN model_char_count INTEGER NOT NULL DEFAULT 0",
    "CREATE TABLE personal_model_items (item_id TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('HYPOTHESIS','PATTERN','CONTRADICTION','UNKNOWN')), state TEXT NOT NULL CHECK(state IN ('ACTIVE','CONTESTED','RESOLVED','INVALIDATED')), created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE personal_model_revisions (revision_id TEXT PRIMARY KEY, item_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal > 0), kind TEXT NOT NULL CHECK(kind IN ('HYPOTHESIS','PATTERN','CONTRADICTION','UNKNOWN')), text TEXT NOT NULL CHECK(length(text) BETWEEN 1 AND 480), temporal_scope TEXT NOT NULL CHECK(temporal_scope IN ('CURRENT_STATE','CONTEXTUAL_PATTERN','CROSS_PERIOD_PATTERN','HISTORICAL_CHANGED','UNCLEAR')), uncertainty TEXT, revision_reason TEXT, derivation_id TEXT, owner_turn_id TEXT, status TEXT NOT NULL CHECK(status IN ('CURRENT','SUPERSEDED','INVALIDATED')), created_at TEXT NOT NULL, FOREIGN KEY(item_id) REFERENCES personal_model_items(item_id) ON DELETE CASCADE, FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE, FOREIGN KEY(owner_turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE, UNIQUE(item_id, ordinal))",
    "CREATE UNIQUE INDEX idx_personal_model_current_revision ON personal_model_revisions(item_id) WHERE status='CURRENT'",
    "CREATE TABLE personal_model_revision_sources (revision_id TEXT NOT NULL, turn_id TEXT NOT NULL, alias TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('SUPPORT','COUNTEREVIDENCE')), PRIMARY KEY(revision_id, turn_id, role), FOREIGN KEY(revision_id) REFERENCES personal_model_revisions(revision_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE personal_model_challenges (challenge_id TEXT PRIMARY KEY, item_id TEXT NOT NULL, revision_id TEXT NOT NULL, turn_id TEXT NOT NULL UNIQUE, created_at TEXT NOT NULL, FOREIGN KEY(item_id) REFERENCES personal_model_items(item_id) ON DELETE CASCADE, FOREIGN KEY(revision_id) REFERENCES personal_model_revisions(revision_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_attempt_model_items (attempt_id TEXT NOT NULL, alias TEXT NOT NULL, item_id TEXT NOT NULL, revision_id TEXT NOT NULL, ordinal INTEGER NOT NULL, char_count INTEGER NOT NULL, PRIMARY KEY(attempt_id, alias), UNIQUE(attempt_id, item_id), FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE, FOREIGN KEY(item_id) REFERENCES personal_model_items(item_id) ON DELETE CASCADE, FOREIGN KEY(revision_id) REFERENCES personal_model_revisions(revision_id) ON DELETE CASCADE)",
    # Losing the last supporting SOURCE invalidates the current meaning; losing
    # counterevidence never strengthens anything automatically.
    "CREATE TRIGGER personal_model_support_lost AFTER DELETE ON personal_model_revision_sources BEGIN UPDATE personal_model_revisions SET status='INVALIDATED' WHERE revision_id=OLD.revision_id AND status='CURRENT' AND NOT EXISTS (SELECT 1 FROM personal_model_revision_sources WHERE revision_id=OLD.revision_id AND role='SUPPORT'); UPDATE personal_model_items SET state='INVALIDATED' WHERE state IN ('ACTIVE','CONTESTED') AND NOT EXISTS (SELECT 1 FROM personal_model_revisions WHERE item_id=personal_model_items.item_id AND status='CURRENT'); END",
    # Deleting the owner correction SOURCE removes the challenge relation; the
    # item returns to ACTIVE only when no other challenge remains.
    "CREATE TRIGGER personal_model_challenge_deleted AFTER DELETE ON personal_model_challenges BEGIN UPDATE personal_model_items SET state='ACTIVE' WHERE item_id=OLD.item_id AND state='CONTESTED' AND NOT EXISTS (SELECT 1 FROM personal_model_challenges WHERE item_id=OLD.item_id); END",
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
PERSONAL_V12_INVENTORY = (*PERSONAL_V11_INVENTORY, "interview_policy", "interview_sessions", "interview_submissions", "interview_source_policies", "interview_attempts", "interview_attempt_manifest_items", "interview_derivations", "interview_derivation_sources", "interview_questions", "interview_question_basis", "interview_inquiry_items", "interview_attempt_inquiry_items")
PERSONAL_V13_INVENTORY = (*PERSONAL_V12_INVENTORY, "personal_model_items", "personal_model_revisions", "personal_model_revision_sources", "personal_model_challenges", "interview_attempt_model_items")


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
    if versions in ([10, 11], [10, 11, 12], [10, 11, 12, 13]):
        return
    if versions != [10]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V11_DDL:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(11,?,?)", ("pmv1_ai_working_formulation_provenance_v11", "personal-v11-ai-provenance"))


def migrate_personal_v12(connection: Any) -> None:
    """Atomic additive AI Interview migration; historical source fails closed."""
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    if versions in ([10, 11, 12], [10, 11, 12, 13]):
        return
    if versions != [10, 11]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V12_DDL:
            connection.execute(statement)
        connection.execute(
            "INSERT INTO interview_policy(policy_id,enabled,updated_at) VALUES('personal_ai_interview_v1',0,datetime('now'))"
        )
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(12,?,?)", ("pmv1_personal_ai_interview_v12", "personal-v12-ai-interview"))


def migrate_personal_v13(connection: Any) -> None:
    """Atomic additive Personal Model migration; no semantic backfill."""
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    if versions == [10, 11, 12, 13]:
        return
    if versions != [10, 11, 12]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V13_DDL:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(13,?,?)", ("pmv1_personal_model_v13", "personal-v13-personal-model"))


def initialize_personal_v11(connection: Any) -> None:
    """Former current schema for exact legacy-package compatibility."""
    existing = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    if not existing:
        initialize_personal_v10(connection)
    migrate_personal_v11(connection)


def initialize_personal_v12(connection: Any) -> None:
    """Former current schema: initialize V10, then additive V11 and V12."""
    existing = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    if not existing:
        initialize_personal_v10(connection)
    migrate_personal_v11(connection)
    migrate_personal_v12(connection)


def initialize_personal_v13(connection: Any) -> None:
    """Current Personal schema: initialize V10, then additive V11..V13."""
    existing = connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchall()
    if not existing:
        initialize_personal_v10(connection)
    migrate_personal_v11(connection)
    migrate_personal_v12(connection)
    migrate_personal_v13(connection)
