"""Frozen E03 V2 schema delta.

V1 remains the accepted twenty-table profile.  This module contains the one
externally visible V1 -> V2 migration and the explicit fifteen-table V2
inventory extension; it deliberately contains no future-epic schema.
"""

from __future__ import annotations

import hashlib


V1_INVENTORY: tuple[str, ...] = (
    "vault_config", "actors", "subjects", "source_artifacts", "blobs",
    "reports", "observations", "assertions", "claims", "data_policies",
    "policy_lineage", "derivation_runs", "derivation_io", "audit_events",
    "deletion_requests", "deletion_plans", "deletion_receipts",
    "backup_manifests", "export_manifests", "schema_migrations",
)

V2_ADDED_TABLES: tuple[str, ...] = (
    "source_locators", "temporal_assertions", "evidence_links",
    "uncertainty_profiles", "uncertainty_dimensions", "contradiction_sets",
    "contradiction_members", "unknowns", "personal_model_snapshots",
    "personal_model_snapshot_claims",
    "personal_model_snapshot_contradictions",
    "personal_model_snapshot_unknowns",
    "personal_model_snapshot_domain_summaries",
    "personal_model_snapshot_algorithms", "record_relations",
)
V2_INVENTORY: tuple[str, ...] = V1_INVENTORY + V2_ADDED_TABLES


# SQLite cannot add CHECK constraints while adding columns.  The five frozen
# V1 tables retain their exact columns and raw values; V2-only validity is
# enforced by the insert/update triggers below.  This is one atomic migration,
# and does not reinterpret any legacy row.
_COLUMN_SQL = {
    "source_artifacts": (
        "semantic_version INTEGER NOT NULL DEFAULT 1", "schema_version INTEGER NOT NULL DEFAULT 1",
        "change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved'", "created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration'",
        "derivation_id TEXT", "artifact_kind TEXT", "origin_kind TEXT", "captured_at TEXT", "source_actor_id TEXT",
        "language_tags TEXT NOT NULL DEFAULT '[]'", "original_filename_encrypted TEXT", "declared_mime_type TEXT",
        "observed_mime_type TEXT", "byte_size INTEGER", "parser_state TEXT", "quarantine_state TEXT", "policy_id TEXT",
        "rights_note TEXT", "replaces_artifact_id TEXT", "corrected_copy_of_artifact_id TEXT",
    ),
    "reports": (
        "semantic_version INTEGER NOT NULL DEFAULT 1", "schema_version INTEGER NOT NULL DEFAULT 1",
        "change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved'", "created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration'",
        "derivation_id TEXT", "report_kind TEXT", "verbatim_content TEXT", "verbatim_blob_id TEXT", "reporter_actor_id TEXT",
        "subject_record_id TEXT", "perspective TEXT", "language_tag TEXT", "elicitation_method TEXT",
        "source_locator_record_id TEXT", "source_locator_version_id TEXT",
    ),
    "observations": (
        "semantic_version INTEGER NOT NULL DEFAULT 1", "schema_version INTEGER NOT NULL DEFAULT 1",
        "change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved'", "created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration'",
        "observation_kind TEXT", "subject_record_id TEXT", "construct_phenomenon TEXT", "value_or_coded_state TEXT",
        "context TEXT", "quality_flags TEXT NOT NULL DEFAULT '[]'", "source_locator_record_id TEXT", "source_locator_version_id TEXT",
    ),
    "assertions": (
        "semantic_version INTEGER NOT NULL DEFAULT 1", "schema_version INTEGER NOT NULL DEFAULT 1",
        "change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved'", "created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration'",
        "object_value TEXT", "qualifiers TEXT NOT NULL DEFAULT '[]'", "negation INTEGER", "modality TEXT", "scope TEXT",
        "source_locator_record_id TEXT", "source_locator_version_id TEXT", "source_unavailable_reason TEXT",
    ),
    "claims": (
        "semantic_version INTEGER NOT NULL DEFAULT 1", "schema_version INTEGER NOT NULL DEFAULT 1",
        "change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved'", "created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration'",
        "proposition TEXT", "bounded_wording TEXT", "population_scope TEXT", "window_context TEXT",
        "uncertainty_profile_record_id TEXT", "uncertainty_profile_version_id TEXT", "falsification_criteria TEXT",
        "review_trigger TEXT", "alternatives TEXT", "counterfactual_cautions TEXT", "knowledge_snapshot_id TEXT",
    ),
}


COMMON = """
record_id TEXT NOT NULL,
version_id TEXT NOT NULL UNIQUE,
schema_version INTEGER NOT NULL DEFAULT 2 CHECK(schema_version=2),
tx_from TEXT NOT NULL,
tx_to TEXT,
is_active INTEGER NOT NULL CHECK(is_active IN (0,1) AND is_active=(tx_to IS NULL)),
change_reason_code TEXT NOT NULL,
previous_version_id TEXT,
created_by_actor_id TEXT NOT NULL,
derivation_id TEXT
"""


CREATE_V2_TABLES = f"""
CREATE TABLE source_locators ({COMMON}, artifact_record_id TEXT NOT NULL, artifact_version_id TEXT NOT NULL,
 locator_type TEXT NOT NULL CHECK(locator_type IN ('document_section','timestamp_range','message_id','cell_range','extractor_locator')),
 locator_value TEXT NOT NULL, extractor_name TEXT NOT NULL, extractor_version TEXT NOT NULL,
 PRIMARY KEY(record_id,version_id), FOREIGN KEY(artifact_record_id,artifact_version_id) REFERENCES source_artifacts(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE temporal_assertions ({COMMON}, target_record_id TEXT NOT NULL, target_version_id TEXT NOT NULL,
 temporal_role TEXT NOT NULL CHECK(temporal_role IN ('occurred','observed','reported','recorded','asserted','effective','scheduled')),
 value_kind TEXT NOT NULL CHECK(value_kind IN ('instant','closed_interval','open_interval','calendar_period','recurring','unknown')),
 lower_value TEXT, upper_value TEXT, lower_inclusive INTEGER NOT NULL DEFAULT 0 CHECK(lower_inclusive IN (0,1)),
 upper_inclusive INTEGER NOT NULL DEFAULT 0 CHECK(upper_inclusive IN (0,1)),
 precision TEXT NOT NULL CHECK(precision IN ('second','minute','hour','day','month','season','year','life_period','unknown')),
 original_literal TEXT NOT NULL, timezone_known INTEGER NOT NULL CHECK(timezone_known IN (0,1)), timezone_name TEXT,
 calendar TEXT NOT NULL DEFAULT 'gregorian', source_actor_id TEXT, assertion_actor_id TEXT,
 certainty_class TEXT NOT NULL CHECK(certainty_class IN ('low','moderate','high','unknown','not_applicable')),
 certainty_rationale TEXT NOT NULL, superseded_temporal_version_id TEXT,
 CHECK((value_kind='unknown' AND lower_value IS NULL AND upper_value IS NULL) OR
       (value_kind='instant' AND lower_value IS NOT NULL AND upper_value=lower_value) OR
       (value_kind IN ('closed_interval','open_interval','calendar_period','recurring') AND (lower_value IS NOT NULL OR upper_value IS NOT NULL))),
 CHECK((timezone_known=0 AND timezone_name IS NULL) OR (timezone_known=1 AND timezone_name IS NOT NULL)), PRIMARY KEY(record_id,version_id));
CREATE TABLE evidence_links ({COMMON}, source_record_id TEXT NOT NULL, source_version_id TEXT NOT NULL,
 target_claim_record_id TEXT NOT NULL, target_claim_version_id TEXT NOT NULL,
 relation TEXT NOT NULL CHECK(relation IN ('supports','contradicts','qualifies','cannot_discriminate')),
 directness TEXT NOT NULL CHECK(directness IN ('direct','indirect','unknown')),
 source_independence_group TEXT NOT NULL, scope_match TEXT NOT NULL CHECK(scope_match IN ('match','partial','mismatch','unknown')),
 temporal_match TEXT NOT NULL CHECK(temporal_match IN ('match','partial','mismatch','unknown')),
 strength_class TEXT NOT NULL CHECK(strength_class IN ('low','moderate','high','unknown','not_applicable')),
 rationale TEXT NOT NULL, author_actor_id TEXT NOT NULL, link_derivation_id TEXT,
 PRIMARY KEY(record_id,version_id), FOREIGN KEY(target_claim_record_id,target_claim_version_id) REFERENCES claims(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE uncertainty_profiles ({COMMON}, target_record_id TEXT NOT NULL, target_version_id TEXT NOT NULL,
 target_kind TEXT NOT NULL CHECK(target_kind IN ('assertion','claim','unknown','contradiction')), PRIMARY KEY(record_id,version_id));
CREATE TABLE uncertainty_dimensions (profile_record_id TEXT NOT NULL, profile_version_id TEXT NOT NULL,
 dimension TEXT NOT NULL CHECK(dimension IN ('source_authenticity','measurement_error','construct_validity','temporal','interpretation','model_parameter','confounding','external_validity','missingness','rights')),
 class TEXT NOT NULL CHECK(class IN ('low','moderate','high','unknown','not_applicable')), rationale TEXT NOT NULL,
 interval_lower REAL, interval_upper REAL, estimand TEXT, method TEXT,
 PRIMARY KEY(profile_record_id,profile_version_id,dimension),
 FOREIGN KEY(profile_record_id,profile_version_id) REFERENCES uncertainty_profiles(record_id,version_id) ON DELETE CASCADE,
 CHECK((interval_lower IS NULL AND interval_upper IS NULL) OR (interval_lower IS NOT NULL AND interval_upper IS NOT NULL AND interval_lower<=interval_upper AND estimand IS NOT NULL AND method IS NOT NULL)));
CREATE TABLE contradiction_sets ({COMMON}, conflict_type TEXT NOT NULL, scope TEXT NOT NULL, time_context TEXT,
 resolution_status TEXT NOT NULL CHECK(resolution_status IN ('unresolved','different_contexts','different_times','source_error','superseded','both_partly_hold','cannot_resolve')),
 resolution_rationale TEXT NOT NULL, PRIMARY KEY(record_id,version_id));
CREATE TABLE contradiction_members (set_record_id TEXT NOT NULL,set_version_id TEXT NOT NULL,
 member_kind TEXT NOT NULL CHECK(member_kind IN ('assertion','claim')),member_record_id TEXT NOT NULL,member_version_id TEXT NOT NULL,
 member_role TEXT NOT NULL CHECK(member_role IN ('position','counterposition','qualifier')),
 PRIMARY KEY(set_record_id,set_version_id,member_record_id,member_version_id),
 FOREIGN KEY(set_record_id,set_version_id) REFERENCES contradiction_sets(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE unknowns ({COMMON}, question TEXT NOT NULL, scope TEXT NOT NULL, why_matters TEXT NOT NULL,
 knowledge_state TEXT NOT NULL, attempts TEXT NOT NULL, what_could_reduce TEXT NOT NULL, burden_or_safety_concern TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('open','deferred','resolved','withdrawn')),
 unknown_reason TEXT NOT NULL CHECK(unknown_reason IN ('not_observed','not_asked','declined','forgotten','not_applicable','measurement_failed','source_unavailable','ambiguous','rights_blocked')), PRIMARY KEY(record_id,version_id));
CREATE TABLE personal_model_snapshots ({COMMON}, evidence_transaction_cutoff TEXT NOT NULL, domain_time_lower TEXT,
 domain_time_upper TEXT, domain_time_precision TEXT NOT NULL, knowledge_snapshot_id TEXT NOT NULL,
 previous_snapshot_record_id TEXT, previous_snapshot_version_id TEXT, change_summary TEXT NOT NULL,
 user_review_status TEXT NOT NULL CHECK(user_review_status IN ('not_reviewed','reviewed','contested')),
 generation_derivation_id TEXT NOT NULL,
 PRIMARY KEY(record_id,version_id), FOREIGN KEY(previous_snapshot_record_id,previous_snapshot_version_id) REFERENCES personal_model_snapshots(record_id,version_id));
CREATE TABLE personal_model_snapshot_claims (snapshot_record_id TEXT NOT NULL,snapshot_version_id TEXT NOT NULL,
 claim_record_id TEXT NOT NULL,claim_version_id TEXT NOT NULL,inclusion_reason TEXT NOT NULL,
 change_class TEXT NOT NULL CHECK(change_class IN ('added','changed','unchanged','removed')),
 PRIMARY KEY(snapshot_record_id,snapshot_version_id,claim_record_id,claim_version_id),
 FOREIGN KEY(snapshot_record_id,snapshot_version_id) REFERENCES personal_model_snapshots(record_id,version_id) ON DELETE CASCADE,
 FOREIGN KEY(claim_record_id,claim_version_id) REFERENCES claims(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE personal_model_snapshot_contradictions (snapshot_record_id TEXT NOT NULL,snapshot_version_id TEXT NOT NULL,
 contradiction_record_id TEXT NOT NULL,contradiction_version_id TEXT NOT NULL,unresolved_at_cutoff INTEGER NOT NULL CHECK(unresolved_at_cutoff IN (0,1)),
 PRIMARY KEY(snapshot_record_id,snapshot_version_id,contradiction_record_id,contradiction_version_id),
 FOREIGN KEY(snapshot_record_id,snapshot_version_id) REFERENCES personal_model_snapshots(record_id,version_id) ON DELETE CASCADE,
 FOREIGN KEY(contradiction_record_id,contradiction_version_id) REFERENCES contradiction_sets(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE personal_model_snapshot_unknowns (snapshot_record_id TEXT NOT NULL,snapshot_version_id TEXT NOT NULL,
 unknown_record_id TEXT NOT NULL,unknown_version_id TEXT NOT NULL,
 PRIMARY KEY(snapshot_record_id,snapshot_version_id,unknown_record_id,unknown_version_id),
 FOREIGN KEY(snapshot_record_id,snapshot_version_id) REFERENCES personal_model_snapshots(record_id,version_id) ON DELETE CASCADE,
 FOREIGN KEY(unknown_record_id,unknown_version_id) REFERENCES unknowns(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE personal_model_snapshot_domain_summaries (summary_id TEXT PRIMARY KEY,snapshot_record_id TEXT NOT NULL,
 snapshot_version_id TEXT NOT NULL,domain_id TEXT NOT NULL,summary_text TEXT NOT NULL,
 UNIQUE(snapshot_record_id,snapshot_version_id,domain_id),
 FOREIGN KEY(snapshot_record_id,snapshot_version_id) REFERENCES personal_model_snapshots(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE personal_model_snapshot_algorithms (snapshot_record_id TEXT NOT NULL,snapshot_version_id TEXT NOT NULL,
 algorithm_id TEXT NOT NULL,algorithm_version TEXT NOT NULL CHECK(length(algorithm_version)>0),config_digest TEXT NOT NULL CHECK(length(config_digest)>0),
 PRIMARY KEY(snapshot_record_id,snapshot_version_id,algorithm_id),
 FOREIGN KEY(snapshot_record_id,snapshot_version_id) REFERENCES personal_model_snapshots(record_id,version_id) ON DELETE CASCADE);
CREATE TABLE record_relations (relation_id TEXT PRIMARY KEY,parent_record_id TEXT NOT NULL,parent_version_id TEXT NOT NULL,
 child_record_id TEXT NOT NULL,child_version_id TEXT NOT NULL,
 relation_kind TEXT NOT NULL CHECK(relation_kind IN ('anchors','targets','supports','contradicts','qualifies','derived_from','replaces','corrects','snapshot_includes','summary_uses')),
 derivation_id TEXT,created_at TEXT NOT NULL,UNIQUE(parent_record_id,parent_version_id,child_record_id,child_version_id,relation_kind));
"""

REBUILD_E03_CORE = """
PRAGMA defer_foreign_keys=ON;
ALTER TABLE source_artifacts RENAME TO source_artifacts_e03_v1;
CREATE TABLE source_artifacts (
 record_id TEXT NOT NULL,artifact_id TEXT NOT NULL,version_id TEXT NOT NULL DEFAULT '',previous_version_id TEXT NOT NULL DEFAULT '',
 source_kind TEXT NOT NULL DEFAULT '',source_label TEXT NOT NULL DEFAULT '',uri_or_path TEXT NOT NULL DEFAULT '',mime_type TEXT NOT NULL DEFAULT '',
 blob_id TEXT,locator_id TEXT,ingested_at TEXT,provided_by_actor TEXT,source_metadata TEXT NOT NULL DEFAULT '{}',tx_from TEXT NOT NULL,
 tx_to TEXT,is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,closure_marker TEXT NOT NULL DEFAULT '' CHECK(closure_marker IN ('','pending_invalidation','invalidated')),
 semantic_version INTEGER NOT NULL DEFAULT 1,schema_version INTEGER NOT NULL DEFAULT 1,change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved',
 created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration',derivation_id TEXT,artifact_kind TEXT,origin_kind TEXT,captured_at TEXT,
 source_actor_id TEXT,language_tags TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(language_tags) AND json_type(language_tags)='array'),
 original_filename_encrypted TEXT,declared_mime_type TEXT,observed_mime_type TEXT,byte_size INTEGER CHECK(byte_size IS NULL OR byte_size>=0),
 parser_state TEXT,quarantine_state TEXT,policy_id TEXT,rights_note TEXT,replaces_artifact_id TEXT,corrected_copy_of_artifact_id TEXT,
 PRIMARY KEY(record_id,version_id),FOREIGN KEY(blob_id) REFERENCES blobs(blob_id),
 CHECK(semantic_version=1 OR (semantic_version=2 AND schema_version=2 AND is_active=(tx_to IS NULL))));
INSERT INTO source_artifacts SELECT * FROM source_artifacts_e03_v1;

ALTER TABLE reports RENAME TO reports_e03_v1;
CREATE TABLE reports (
 record_id TEXT NOT NULL,report_id TEXT NOT NULL,version_id TEXT NOT NULL DEFAULT '',previous_version_id TEXT NOT NULL DEFAULT '',title TEXT NOT NULL DEFAULT '',
 source_ids TEXT NOT NULL DEFAULT '[]',observation_ids TEXT NOT NULL DEFAULT '[]',assertion_ids TEXT NOT NULL DEFAULT '[]',claim_ids TEXT NOT NULL DEFAULT '[]',
 summary TEXT NOT NULL DEFAULT '',structured_data TEXT NOT NULL DEFAULT '{}',authored_at TEXT,tx_from TEXT NOT NULL,tx_to TEXT,is_active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL,closure_marker TEXT NOT NULL DEFAULT '' CHECK(closure_marker IN ('','pending_invalidation','invalidated')),
 semantic_version INTEGER NOT NULL DEFAULT 1,schema_version INTEGER NOT NULL DEFAULT 1,change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved',
 created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration',derivation_id TEXT,report_kind TEXT,verbatim_content TEXT,verbatim_blob_id TEXT,
 reporter_actor_id TEXT,subject_record_id TEXT,perspective TEXT,language_tag TEXT,elicitation_method TEXT,source_locator_record_id TEXT,source_locator_version_id TEXT,
 PRIMARY KEY(record_id,version_id),CHECK(semantic_version=1 OR (semantic_version=2 AND schema_version=2 AND is_active=(tx_to IS NULL)
  AND report_kind IN ('autobiographical_memory','current_state','event_account','belief','goal','value','preference','symptom_report','collateral_report','other')
  AND perspective IN ('first_person','third_party','document_author','unknown'))));
INSERT INTO reports SELECT * FROM reports_e03_v1;
DROP TABLE reports_e03_v1;
CREATE UNIQUE INDEX idx_reports_active_record ON reports(record_id) WHERE is_active=1;

ALTER TABLE observations RENAME TO observations_e03_v1;
CREATE TABLE observations (
 record_id TEXT NOT NULL,observation_id TEXT NOT NULL,version_id TEXT NOT NULL DEFAULT '',previous_version_id TEXT NOT NULL DEFAULT '',subject_id TEXT,
 source_artifact_id TEXT,method TEXT NOT NULL DEFAULT '',raw_value TEXT,structured_data TEXT NOT NULL DEFAULT '{}',observed_at TEXT,observer_actor_id TEXT,
 derivation_id TEXT,tx_from TEXT NOT NULL,tx_to TEXT,is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,
 closure_marker TEXT NOT NULL DEFAULT '' CHECK(closure_marker IN ('','pending_invalidation','invalidated')),temporal_ref TEXT NOT NULL DEFAULT '',
 semantic_version INTEGER NOT NULL DEFAULT 1,schema_version INTEGER NOT NULL DEFAULT 1,change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved',
 created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration',observation_kind TEXT,subject_record_id TEXT,construct_phenomenon TEXT,value_or_coded_state TEXT,
 context TEXT,quality_flags TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(quality_flags) AND json_type(quality_flags)='array'),source_locator_record_id TEXT,source_locator_version_id TEXT,
 PRIMARY KEY(record_id,version_id),FOREIGN KEY(derivation_id) REFERENCES derivation_runs(derivation_id),
 CHECK(semantic_version=1 OR (semantic_version=2 AND schema_version=2 AND is_active=(tx_to IS NULL)
  AND observation_kind IN ('self_observation','external_observation','device_observation','clinician_observation'))));
INSERT INTO observations SELECT * FROM observations_e03_v1;
DROP TABLE observations_e03_v1;
CREATE UNIQUE INDEX idx_observations_active_record ON observations(record_id) WHERE is_active=1;
DROP TABLE source_artifacts_e03_v1;
CREATE UNIQUE INDEX idx_source_artifacts_active_record ON source_artifacts(record_id) WHERE is_active=1;

ALTER TABLE assertions RENAME TO assertions_e03_v1;
CREATE TABLE assertions (
 record_id TEXT NOT NULL,assertion_id TEXT NOT NULL,version_id TEXT NOT NULL DEFAULT '',previous_version_id TEXT NOT NULL DEFAULT '',subject_id TEXT,
 assertion_type TEXT NOT NULL DEFAULT '',predicate TEXT NOT NULL DEFAULT '',support_ids TEXT NOT NULL DEFAULT '[]',contra_ids TEXT NOT NULL DEFAULT '[]',confidence REAL,
 derivation_id TEXT,tx_from TEXT NOT NULL,tx_to TEXT,is_active INTEGER NOT NULL DEFAULT 1,created_at TEXT NOT NULL,
 closure_marker TEXT NOT NULL DEFAULT '' CHECK(closure_marker IN ('','pending_invalidation','invalidated')),provenance_ref TEXT NOT NULL DEFAULT '',
 semantic_version INTEGER NOT NULL DEFAULT 1,schema_version INTEGER NOT NULL DEFAULT 1,change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved',
 created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration',object_value TEXT,qualifiers TEXT NOT NULL DEFAULT '[]' CHECK(json_valid(qualifiers) AND json_type(qualifiers)='array'),
 negation INTEGER,modality TEXT,scope TEXT,source_locator_record_id TEXT,source_locator_version_id TEXT,source_unavailable_reason TEXT,
 PRIMARY KEY(record_id,version_id),CHECK(semantic_version=1 OR (semantic_version=2 AND schema_version=2 AND is_active=(tx_to IS NULL)
  AND confidence IS NULL AND negation IN (0,1) AND modality IN ('actual','possible','reported','hypothetical')
  AND ((source_locator_record_id IS NOT NULL AND source_locator_version_id IS NOT NULL) OR source_unavailable_reason IS NOT NULL))));
INSERT INTO assertions SELECT * FROM assertions_e03_v1;
DROP TABLE assertions_e03_v1;
CREATE UNIQUE INDEX idx_assertions_active_record ON assertions(record_id) WHERE is_active=1;
"""

REBUILD_CLAIMS = """
CREATE TABLE claims_e03_rebuilt (
 record_id TEXT NOT NULL, claim_id TEXT NOT NULL, version_id TEXT NOT NULL DEFAULT '', previous_version_id TEXT NOT NULL DEFAULT '',
 subject_id TEXT, claim_type TEXT NOT NULL DEFAULT 'descriptive', claim_status TEXT NOT NULL DEFAULT 'proposed',
 claim_origin TEXT NOT NULL DEFAULT 'observation', claim_body TEXT NOT NULL DEFAULT '', evidence_ids TEXT NOT NULL DEFAULT '[]',
 contradiction_set_id TEXT, resolution TEXT, derivation_id TEXT, tx_from TEXT NOT NULL, tx_to TEXT, is_active INTEGER NOT NULL DEFAULT 1,
 created_at TEXT NOT NULL, closure_marker TEXT NOT NULL DEFAULT '' CHECK(closure_marker IN ('','pending_invalidation','invalidated')),
 provenance_ref TEXT NOT NULL DEFAULT '', semantic_version INTEGER NOT NULL DEFAULT 1, schema_version INTEGER NOT NULL DEFAULT 1,
 change_reason_code TEXT NOT NULL DEFAULT 'legacy_preserved', created_by_actor_id TEXT NOT NULL DEFAULT 'legacy:migration',
 proposition TEXT, bounded_wording TEXT, population_scope TEXT, window_context TEXT, uncertainty_profile_record_id TEXT,
 uncertainty_profile_version_id TEXT, falsification_criteria TEXT, review_trigger TEXT, alternatives TEXT,
 counterfactual_cautions TEXT, knowledge_snapshot_id TEXT, PRIMARY KEY(record_id,version_id),
 CHECK((semantic_version=1 AND claim_type IN ('descriptive','causal','predictive','evaluative','normative','definitional','diagnostic','synthetic','comparative','existential','prudential','taxonomic')
  AND claim_status IN ('proposed','supported','contradicted','resolved','retracted','superseded','disconfirmed','pending_review')
  AND claim_origin IN ('observation','inference','derivation','abduction','analogy','testimony')) OR
 (semantic_version=2 AND claim_type IN ('descriptive','pattern','interpretive','narrative','statistical_association','causal_hypothesis','prediction','clinical_mapping','trait_estimate','functioning_assessment','strength_or_resource','recommendation_candidate')
  AND claim_status IN ('proposed','user_accepted','active','contested','rejected','superseded','withdrawn','invalidated')
  AND claim_origin IN ('user','deterministic_rule','statistical_analysis','clinician_import','llm_proposal','mixed') AND is_active=(tx_to IS NULL))));
INSERT INTO claims_e03_rebuilt SELECT * FROM claims;
DROP TABLE claims;
ALTER TABLE claims_e03_rebuilt RENAME TO claims;
CREATE UNIQUE INDEX idx_claims_active_record ON claims(record_id) WHERE is_active=1;
"""

INDEX_SQL = """
CREATE UNIQUE INDEX idx_source_locators_active ON source_locators(record_id) WHERE is_active=1;
CREATE INDEX idx_source_locators_artifact ON source_locators(artifact_record_id,artifact_version_id);
CREATE UNIQUE INDEX idx_temporal_assertions_active ON temporal_assertions(record_id) WHERE is_active=1;
CREATE INDEX idx_temporal_target_role ON temporal_assertions(target_record_id,target_version_id,temporal_role);
CREATE UNIQUE INDEX idx_evidence_links_active ON evidence_links(record_id) WHERE is_active=1;
CREATE INDEX idx_evidence_target ON evidence_links(target_claim_record_id,target_claim_version_id);
CREATE INDEX idx_evidence_source ON evidence_links(source_record_id,source_version_id);
CREATE UNIQUE INDEX idx_uncertainty_profiles_active ON uncertainty_profiles(record_id) WHERE is_active=1;
CREATE INDEX idx_uncertainty_target ON uncertainty_profiles(target_record_id,target_version_id);
CREATE UNIQUE INDEX idx_contradiction_sets_active ON contradiction_sets(record_id) WHERE is_active=1;
CREATE INDEX idx_contradiction_member ON contradiction_members(member_record_id,member_version_id);
CREATE UNIQUE INDEX idx_unknowns_active ON unknowns(record_id) WHERE is_active=1;
CREATE UNIQUE INDEX idx_personal_model_snapshots_active ON personal_model_snapshots(record_id) WHERE is_active=1;
CREATE INDEX idx_snapshot_claim ON personal_model_snapshot_claims(claim_record_id,claim_version_id);
CREATE INDEX idx_snapshot_contradiction ON personal_model_snapshot_contradictions(contradiction_record_id,contradiction_version_id);
CREATE INDEX idx_snapshot_unknown ON personal_model_snapshot_unknowns(unknown_record_id,unknown_version_id);
CREATE INDEX idx_snapshot_domain ON personal_model_snapshot_domain_summaries(domain_id);
CREATE INDEX idx_relation_parent ON record_relations(parent_record_id,parent_version_id);
CREATE INDEX idx_relation_child ON record_relations(child_record_id,child_version_id);
"""

TRIGGER_SQL = """
CREATE TRIGGER claims_v2_insert_guard BEFORE INSERT ON claims WHEN NEW.semantic_version=2 BEGIN
 SELECT CASE WHEN NEW.claim_type NOT IN ('descriptive','pattern','interpretive','narrative','statistical_association','causal_hypothesis','prediction','clinical_mapping','trait_estimate','functioning_assessment','strength_or_resource','recommendation_candidate') THEN RAISE(ABORT,'invalid V2 claim type') END;
 SELECT CASE WHEN NEW.claim_status NOT IN ('proposed','user_accepted','active','contested','rejected','superseded','withdrawn','invalidated') THEN RAISE(ABORT,'invalid V2 claim status') END;
 SELECT CASE WHEN NEW.claim_origin NOT IN ('user','deterministic_rule','statistical_analysis','clinician_import','llm_proposal','mixed') THEN RAISE(ABORT,'invalid V2 claim origin') END;
END;
CREATE TRIGGER claims_v2_update_guard BEFORE UPDATE ON claims WHEN NEW.semantic_version=2 BEGIN
 SELECT CASE WHEN NEW.claim_type NOT IN ('descriptive','pattern','interpretive','narrative','statistical_association','causal_hypothesis','prediction','clinical_mapping','trait_estimate','functioning_assessment','strength_or_resource','recommendation_candidate') THEN RAISE(ABORT,'invalid V2 claim type') END;
END;
CREATE TRIGGER snapshots_immutable_update BEFORE UPDATE ON personal_model_snapshots BEGIN SELECT RAISE(ABORT,'snapshot is immutable'); END;
"""


def _split(script: str) -> list[str]:
    import sqlite3
    statements: list[str] = []
    buffer = ""
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete E03 migration SQL")
    return statements


V2_MIGRATION_STATEMENTS: tuple[str, ...] = tuple(
    [f"ALTER TABLE {table} ADD COLUMN {definition};" for table, columns in _COLUMN_SQL.items() for definition in columns]
    + _split(REBUILD_E03_CORE)
    + _split(REBUILD_CLAIMS)
    + _split(CREATE_V2_TABLES)
    + _split(INDEX_SQL)
    + _split(TRIGGER_SQL)
)
V2_MIGRATION_CHECKSUM = hashlib.sha256(
    (";\n".join(V2_MIGRATION_STATEMENTS) + ";").encode("utf-8")
).hexdigest()


def inventory_for_schema(schema_version: int) -> tuple[str, ...]:
    if schema_version == 1:
        return V1_INVENTORY
    if schema_version == 2:
        return V2_INVENTORY
    if schema_version == 3:
        from psyche_os.storage.e05_schema import V3_INVENTORY

        return V3_INVENTORY
    raise ValueError("Unsupported schema version")
