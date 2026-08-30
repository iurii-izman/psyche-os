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
    "CREATE TABLE interview_attempt_model_items (attempt_id TEXT NOT NULL, alias TEXT NOT NULL, item_id TEXT NOT NULL, revision_id TEXT NOT NULL, sent_state TEXT NOT NULL CHECK(sent_state IN ('ACTIVE','CONTESTED','RESOLVED','INVALIDATED')), ordinal INTEGER NOT NULL, char_count INTEGER NOT NULL, PRIMARY KEY(attempt_id, alias), UNIQUE(attempt_id, item_id), FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE, FOREIGN KEY(item_id) REFERENCES personal_model_items(item_id) ON DELETE CASCADE, FOREIGN KEY(revision_id) REFERENCES personal_model_revisions(revision_id) ON DELETE CASCADE)",
    # Losing the last supporting SOURCE invalidates the current meaning; losing
    # counterevidence never strengthens anything automatically.  Owner
    # challenges are an overlay: the challenge relation itself carries the
    # owner-contested state, so no trigger mutates the base lifecycle state.
    "CREATE TRIGGER personal_model_support_lost AFTER DELETE ON personal_model_revision_sources BEGIN UPDATE personal_model_revisions SET status='INVALIDATED' WHERE revision_id=OLD.revision_id AND status='CURRENT' AND NOT EXISTS (SELECT 1 FROM personal_model_revision_sources WHERE revision_id=OLD.revision_id AND role='SUPPORT'); UPDATE personal_model_items SET state='INVALIDATED' WHERE state IN ('ACTIVE','CONTESTED') AND NOT EXISTS (SELECT 1 FROM personal_model_revisions WHERE item_id=personal_model_items.item_id AND status='CURRENT'); END",
)

# V14 is the deliberately narrow Inquiry -> Change model.  Check-in text stays
# in reflection_turns; these rows only bind durable derived plans and outcomes
# to exact source/derivation identities.
_V14_DDL = (
    "CREATE TABLE change_plans (plan_id TEXT PRIMARY KEY, derivation_id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('OBSERVE','EXPERIMENT')), state TEXT NOT NULL CHECK(state IN ('PROPOSED','ACTIVE','COMPLETED','STOPPED','DISMISSED','INVALIDATED')), title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160), reason TEXT NOT NULL CHECK(length(reason) BETWEEN 1 AND 480), instructions TEXT NOT NULL CHECK(length(instructions) BETWEEN 1 AND 1200), observation_prompt TEXT NOT NULL CHECK(length(observation_prompt) BETWEEN 1 AND 480), expected_signal TEXT NOT NULL CHECK(length(expected_signal) BETWEEN 1 AND 480), counter_signal TEXT NOT NULL CHECK(length(counter_signal) BETWEEN 1 AND 480), duration_days INTEGER CHECK(duration_days BETWEEN 1 AND 31), stop_conditions TEXT NOT NULL CHECK(length(stop_conditions) BETWEEN 1 AND 480), risk_level TEXT NOT NULL CHECK(risk_level='LOW'), reversible INTEGER NOT NULL CHECK(reversible=1), self_directed INTEGER NOT NULL CHECK(self_directed=1), created_at TEXT NOT NULL, activated_at TEXT, ended_at TEXT, completion_review_id TEXT UNIQUE, FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE, FOREIGN KEY(completion_review_id) REFERENCES change_reviews(review_id) ON DELETE NO ACTION)",
    "CREATE TABLE change_plan_targets (plan_id TEXT NOT NULL, item_id TEXT NOT NULL, revision_id TEXT NOT NULL, PRIMARY KEY(plan_id,item_id), FOREIGN KEY(plan_id) REFERENCES change_plans(plan_id) ON DELETE CASCADE, FOREIGN KEY(item_id) REFERENCES personal_model_items(item_id) ON DELETE CASCADE, FOREIGN KEY(revision_id) REFERENCES personal_model_revisions(revision_id) ON DELETE CASCADE)",
    "CREATE TABLE change_observations (observation_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, turn_id TEXT NOT NULL UNIQUE, signal TEXT CHECK(signal IN ('BETTER','SAME','WORSE','UNCLEAR','NOT_APPLICABLE')), created_at TEXT NOT NULL, FOREIGN KEY(plan_id) REFERENCES change_plans(plan_id) ON DELETE CASCADE, FOREIGN KEY(turn_id) REFERENCES reflection_turns(turn_id) ON DELETE CASCADE)",
    "CREATE TABLE change_reviews (review_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, derivation_id TEXT NOT NULL, practical_effect TEXT NOT NULL CHECK(practical_effect IN ('HELPED','NO_CLEAR_EFFECT','WORSE','MIXED','NOT_TESTED')), epistemic_outcome TEXT NOT NULL CHECK(epistemic_outcome IN ('SUPPORTED','WEAKENED','INCONCLUSIVE','CONTEXT_DEPENDENT')), summary TEXT NOT NULL CHECK(length(summary) BETWEEN 1 AND 480), understanding TEXT NOT NULL CHECK(length(understanding) BETWEEN 1 AND 480), recommended_next TEXT NOT NULL CHECK(recommended_next IN ('COMPLETE','CONTINUE_OBSERVING','RETURN_TO_INQUIRY')), created_at TEXT NOT NULL, FOREIGN KEY(plan_id) REFERENCES change_plans(plan_id) ON DELETE CASCADE, FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE)",
    "CREATE TRIGGER change_review_deleted_reopens_plan AFTER DELETE ON change_reviews WHEN (SELECT completion_review_id FROM change_plans WHERE plan_id=OLD.plan_id)=OLD.review_id BEGIN UPDATE change_plans SET state='ACTIVE',ended_at=NULL,completion_review_id=NULL WHERE plan_id=OLD.plan_id; END",
    "CREATE TABLE change_review_sessions (interview_session_id TEXT PRIMARY KEY, plan_id TEXT NOT NULL, FOREIGN KEY(interview_session_id) REFERENCES interview_sessions(interview_session_id) ON DELETE CASCADE, FOREIGN KEY(plan_id) REFERENCES change_plans(plan_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_attempt_change_items (attempt_id TEXT NOT NULL, alias TEXT NOT NULL, plan_id TEXT NOT NULL, sent_state TEXT NOT NULL CHECK(sent_state IN ('PROPOSED','ACTIVE','COMPLETED','STOPPED','DISMISSED','INVALIDATED')), ordinal INTEGER NOT NULL, char_count INTEGER NOT NULL, PRIMARY KEY(attempt_id,alias), UNIQUE(attempt_id,plan_id), FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE, FOREIGN KEY(plan_id) REFERENCES change_plans(plan_id) ON DELETE CASCADE)",
    "CREATE UNIQUE INDEX idx_change_one_active_experiment ON change_plans(kind) WHERE state='ACTIVE' AND kind='EXPERIMENT'",
)

# V15 adds local-only, immutable external evidence.  Imported payloads are
# deliberately separate from reflection turns and from every AI lineage table.
_V15_DDL = (
    "CREATE TABLE external_sources (source_id TEXT PRIMARY KEY, source_kind TEXT NOT NULL, label TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('ACTIVE','ERROR','DISABLED')), processing_policy TEXT NOT NULL CHECK(processing_policy='LOCAL_ONLY'), inbox_path TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, last_imported_at TEXT)",
    "CREATE TABLE external_import_batches (batch_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, artifact_name TEXT NOT NULL, artifact_sha256 TEXT NOT NULL, imported_at TEXT NOT NULL, record_count INTEGER NOT NULL CHECK(record_count >= 0), snapshot_status TEXT NOT NULL DEFAULT 'COMPLETE' CHECK(snapshot_status IN ('COMPLETE','PARTIAL')), issue_count INTEGER NOT NULL DEFAULT 0 CHECK(issue_count >= 0), FOREIGN KEY(source_id) REFERENCES external_sources(source_id) ON DELETE CASCADE, UNIQUE(source_id, artifact_sha256))",
    "CREATE TABLE external_records (external_record_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, native_id TEXT NOT NULL, record_type TEXT NOT NULL, origin_json TEXT NOT NULL CHECK(json_valid(origin_json)), start_at TEXT, end_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES external_sources(source_id) ON DELETE CASCADE, UNIQUE(source_id, native_id, record_type))",
    "CREATE TABLE external_record_versions (version_id TEXT PRIMARY KEY, external_record_id TEXT NOT NULL, batch_id TEXT NOT NULL, ordinal INTEGER NOT NULL CHECK(ordinal > 0), payload_sha256 TEXT NOT NULL, raw_payload TEXT NOT NULL CHECK(json_valid(raw_payload)), source_modified_at TEXT, source_version TEXT, is_current INTEGER NOT NULL CHECK(is_current IN (0,1)), supersedes_version_id TEXT, imported_at TEXT NOT NULL, FOREIGN KEY(external_record_id) REFERENCES external_records(external_record_id) ON DELETE CASCADE, FOREIGN KEY(batch_id) REFERENCES external_import_batches(batch_id) ON DELETE CASCADE, FOREIGN KEY(supersedes_version_id) REFERENCES external_record_versions(version_id), UNIQUE(external_record_id, ordinal), UNIQUE(external_record_id, payload_sha256))",
    "CREATE UNIQUE INDEX idx_external_record_current_version ON external_record_versions(external_record_id) WHERE is_current=1",
    "CREATE TABLE sleep_episodes (episode_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, ended_at TEXT NOT NULL, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)",
    "CREATE TABLE sleep_observations (observation_id TEXT PRIMARY KEY, episode_id TEXT NOT NULL, external_record_id TEXT NOT NULL UNIQUE, current_version_id TEXT NOT NULL, source_kind TEXT NOT NULL, classification TEXT NOT NULL CHECK(classification='VENDOR_DERIVED'), created_at TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(episode_id) REFERENCES sleep_episodes(episode_id) ON DELETE CASCADE, FOREIGN KEY(external_record_id) REFERENCES external_records(external_record_id) ON DELETE CASCADE, FOREIGN KEY(current_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
    "CREATE TABLE sleep_stages (stage_id TEXT PRIMARY KEY, observation_id TEXT NOT NULL, source_version_id TEXT NOT NULL, category TEXT NOT NULL CHECK(category IN ('AWAKE','AWAKE_IN_BED','LIGHT','DEEP','REM','SLEEPING','OUT_OF_BED','UNKNOWN')), started_at TEXT NOT NULL, ended_at TEXT NOT NULL, FOREIGN KEY(observation_id) REFERENCES sleep_observations(observation_id) ON DELETE CASCADE, FOREIGN KEY(source_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
    "CREATE TABLE physiological_samples (sample_id TEXT PRIMARY KEY, external_record_id TEXT NOT NULL, source_version_id TEXT NOT NULL, metric TEXT NOT NULL CHECK(metric IN ('HEART_RATE','RESTING_HEART_RATE','SPO2','RESPIRATORY_RATE')), classification TEXT NOT NULL CHECK(classification='MEASUREMENT'), observed_at TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL, FOREIGN KEY(external_record_id) REFERENCES external_records(external_record_id) ON DELETE CASCADE, FOREIGN KEY(source_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
    "CREATE INDEX idx_physiological_samples_interval ON physiological_samples(observed_at, metric)",
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
PERSONAL_V14_INVENTORY = (*PERSONAL_V13_INVENTORY, "change_plans", "change_plan_targets", "change_observations", "change_reviews", "change_review_sessions", "interview_attempt_change_items")
PERSONAL_V15_INVENTORY = (*PERSONAL_V14_INVENTORY, "external_sources", "external_import_batches", "external_records", "external_record_versions", "sleep_episodes", "sleep_observations", "sleep_stages", "physiological_samples")

# V16 is deliberately parallel to the USER-source interview lineage.  An E
# alias names a small, immutable transmission view, never a reflection turn or
# an external raw record.  Cascades from source versions remove the exact
# sent-state and its derivations rather than attempting to reconstruct it.
_V16_DDL = (
    "ALTER TABLE interview_attempts ADD COLUMN external_item_count INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE interview_attempts ADD COLUMN external_char_count INTEGER NOT NULL DEFAULT 0",
    "CREATE TABLE interview_external_policies (source_id TEXT PRIMARY KEY, policy_id TEXT NOT NULL UNIQUE, enabled INTEGER NOT NULL DEFAULT 0 CHECK(enabled IN (0,1)), evidence_view TEXT NOT NULL CHECK(evidence_view='SLEEP_AI_FACTS_V1'), purpose TEXT NOT NULL CHECK(purpose='personal_ai_interview'), provider_profile TEXT NOT NULL, updated_at TEXT NOT NULL, FOREIGN KEY(source_id) REFERENCES external_sources(source_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_attempt_external_items (attempt_id TEXT NOT NULL, alias TEXT NOT NULL, source_version_id TEXT NOT NULL, policy_id TEXT NOT NULL, evidence_view TEXT NOT NULL CHECK(evidence_view='SLEEP_AI_FACTS_V1'), normalized_content TEXT NOT NULL CHECK(json_valid(normalized_content)), ordinal INTEGER NOT NULL, char_count INTEGER NOT NULL, PRIMARY KEY(attempt_id,alias), UNIQUE(attempt_id,source_version_id), FOREIGN KEY(attempt_id) REFERENCES interview_attempts(attempt_id) ON DELETE CASCADE, FOREIGN KEY(source_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
    "CREATE TABLE interview_derivation_external_sources (derivation_id TEXT NOT NULL, source_version_id TEXT NOT NULL, alias TEXT NOT NULL, PRIMARY KEY(derivation_id,source_version_id), FOREIGN KEY(derivation_id) REFERENCES interview_derivations(derivation_id) ON DELETE CASCADE, FOREIGN KEY(source_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
    "CREATE TRIGGER interview_derivation_external_source_deleted AFTER DELETE ON interview_derivation_external_sources BEGIN DELETE FROM interview_derivations WHERE derivation_id=OLD.derivation_id; END",
    "CREATE TABLE interview_question_external_basis (question_id TEXT NOT NULL, alias TEXT NOT NULL, source_version_id TEXT NOT NULL, PRIMARY KEY(question_id,alias), FOREIGN KEY(question_id) REFERENCES interview_questions(question_id) ON DELETE CASCADE, FOREIGN KEY(source_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
    "CREATE TABLE personal_model_revision_external_sources (revision_id TEXT NOT NULL, source_version_id TEXT NOT NULL, alias TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('SUPPORT','COUNTEREVIDENCE')), PRIMARY KEY(revision_id,source_version_id,role), FOREIGN KEY(revision_id) REFERENCES personal_model_revisions(revision_id) ON DELETE CASCADE, FOREIGN KEY(source_version_id) REFERENCES external_record_versions(version_id) ON DELETE CASCADE)",
)
PERSONAL_V16_INVENTORY = (*PERSONAL_V15_INVENTORY, "interview_external_policies", "interview_attempt_external_items", "interview_derivation_external_sources", "interview_question_external_basis", "personal_model_revision_external_sources")


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
    if versions in ([10, 11], [10, 11, 12], [10, 11, 12, 13], [10, 11, 12, 13, 14], [10, 11, 12, 13, 14, 15]):
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
    if versions in ([10, 11, 12], [10, 11, 12, 13], [10, 11, 12, 13, 14], [10, 11, 12, 13, 14, 15]):
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
    if versions in ([10, 11, 12, 13], [10, 11, 12, 13, 14], [10, 11, 12, 13, 14, 15]):
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

def migrate_personal_v14(connection: Any) -> None:
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    if versions in ([10, 11, 12, 13, 14], [10, 11, 12, 13, 14, 15]):
        return
    if versions != [10, 11, 12, 13]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V14_DDL:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(14,?,?)", ("pmv1_inquiry_change_v14", "personal-v14-inquiry-change"))

def initialize_personal_v14(connection: Any) -> None:
    initialize_personal_v13(connection)
    migrate_personal_v14(connection)

def migrate_personal_v15(connection: Any) -> None:
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    if versions == [10, 11, 12, 13, 14, 15]:
        return
    if versions != [10, 11, 12, 13, 14]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V15_DDL:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(15,?,?)", ("pmv1_connected_evidence_sleep_v15", "personal-v15-connected-evidence"))

def initialize_personal_v15(connection: Any) -> None:
    initialize_personal_v14(connection)
    migrate_personal_v15(connection)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(external_import_batches)")}
    with connection:
        if "snapshot_status" not in columns:
            connection.execute("ALTER TABLE external_import_batches ADD COLUMN snapshot_status TEXT NOT NULL DEFAULT 'COMPLETE' CHECK(snapshot_status IN ('COMPLETE','PARTIAL'))")
        if "issue_count" not in columns:
            connection.execute("ALTER TABLE external_import_batches ADD COLUMN issue_count INTEGER NOT NULL DEFAULT 0 CHECK(issue_count >= 0)")

def migrate_personal_v16(connection: Any) -> None:
    versions = [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")]
    if versions == [10, 11, 12, 13, 14, 15, 16]:
        return
    if versions != [10, 11, 12, 13, 14, 15]:
        raise ValueError("PERSONAL_SCHEMA_UNAVAILABLE")
    with connection:
        for statement in _V16_DDL:
            connection.execute(statement)
        connection.execute("INSERT INTO schema_migrations(version,label,checksum) VALUES(16,?,?)", ("pmv1_external_evidence_ai_inquiry_sleep_v16", "personal-v16-external-ai-sleep"))

def initialize_personal_v16(connection: Any) -> None:
    initialize_personal_v15(connection)
    migrate_personal_v16(connection)
