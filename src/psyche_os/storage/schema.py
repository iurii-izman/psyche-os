"""Database schema — versioned DDL for the F0 core store.

All tables use half-open transaction intervals [tx_from, tx_to) for versioning.
Schema version is tracked in schema_migrations.

F05 (FIX): Every entity table now carries a closure_marker column for
subtype-preserving deletion propagation. Foreign key enforcement is
enabled via PRAGMA foreign_keys = ON. Each table that references other
entities carries temporal_ref or provenance_ref where applicable.
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Schema version tracking
# ---------------------------------------------------------------------------

SCHEMA_VERSIONS: dict[int, str] = {
    1: "f0_core_initial",
    2: "e03_evidence_archive_v2",
    3: "e05_longitudinal_analysis_v3",
    4: "e06_bounded_n_of_1_v4",
    5: "e08_untrusted_import_v5",
    6: "v3a0_reflection_workspace_v6",
    7: "v3a1_guided_exploration_v7",
    8: "v3a1_guided_exploration_v8",
}

# Accepted V1 callers keep their frozen default. E03 requests version 2
# explicitly through Migrator/apply_schema and exposes it as the latest schema.
CURRENT_SCHEMA_VERSION = 1
LATEST_SCHEMA_VERSION = 8

# ---------------------------------------------------------------------------
# Deletion closure constants
# ---------------------------------------------------------------------------

# Closure markers for subtype-preserving deletion propagation
CLOSURE_MARKER_CLEAR = ""
CLOSURE_MARKER_PENDING_INVALIDATION = "pending_invalidation"
CLOSURE_MARKER_INVALIDATED = "invalidated"

VALID_CLOSURE_MARKERS = frozenset(
    {
        CLOSURE_MARKER_CLEAR,
        CLOSURE_MARKER_PENDING_INVALIDATION,
        CLOSURE_MARKER_INVALIDATED,
    }
)


# ---------------------------------------------------------------------------
# DDL: Schema migrations table
# ---------------------------------------------------------------------------

SCHEMA_MIGRATIONS_DDL = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    version         INTEGER PRIMARY KEY,
    label           TEXT NOT NULL,
    applied_at      TEXT NOT NULL DEFAULT (datetime('now')),
    checksum        TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# DDL: Vault configuration (singleton row)
# ---------------------------------------------------------------------------

VAULT_CONFIG_DDL = """
CREATE TABLE IF NOT EXISTS vault_config (
    vault_id                TEXT PRIMARY KEY,
    vault_name              TEXT NOT NULL DEFAULT '',
    data_mode               TEXT NOT NULL DEFAULT 'synthetic_only'
        CHECK (data_mode = 'synthetic_only'),
    created_at              TEXT NOT NULL,
    vmk_os_wrapped          BLOB,
    vmk_recovery_header     TEXT,   -- JSON-serialised RecoveryWrapHeader
    key_state               TEXT NOT NULL DEFAULT 'generated'
        CHECK (key_state IN ('generated','active','rotation_pending',
              'retired_for_write','retained_for_read','destroyed')),
    db_key_salt             BLOB NOT NULL,
    blob_envelope_key_salt  BLOB NOT NULL
);
"""


# ---------------------------------------------------------------------------
# DDL: Actors
# ---------------------------------------------------------------------------

ACTORS_DDL = """
CREATE TABLE IF NOT EXISTS actors (
    record_id       TEXT NOT NULL,
    actor_id        TEXT NOT NULL,
    actor_kind      TEXT NOT NULL DEFAULT 'human'
        CHECK (actor_kind IN ('human','system','delegate')),
    actor_label     TEXT NOT NULL DEFAULT '',
    tx_from         TEXT NOT NULL,
    tx_to           TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    -- F05: Separate stable record identity from row version_id
    version_id      TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    -- Subtype closure: a deleted actor must cascade-invalidate
    -- provenance references that transitively depend on it
    closure_marker  TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    PRIMARY KEY (record_id, version_id)
);
-- F05: Enforce at most one active version per record
CREATE UNIQUE INDEX IF NOT EXISTS idx_actors_active_record
    ON actors (record_id) WHERE is_active = 1;
-- F05: Enforce at most one active version per stable identity (actor_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_actors_active_identity
    ON actors (actor_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Subjects
# ---------------------------------------------------------------------------

SUBJECTS_DDL = """
CREATE TABLE IF NOT EXISTS subjects (
    record_id       TEXT NOT NULL,
    subject_id      TEXT NOT NULL,
    subject_label   TEXT NOT NULL DEFAULT '',
    anonymous       INTEGER NOT NULL DEFAULT 0,
    data_mode       TEXT NOT NULL DEFAULT 'synthetic_only',
    tx_from         TEXT NOT NULL,
    tx_to           TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    created_at      TEXT NOT NULL,
    version_id      TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    -- Subtype closure tracking for deletion propagation
    closure_marker  TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    PRIMARY KEY (record_id, version_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_active_record
    ON subjects (record_id) WHERE is_active = 1;
-- F05: Enforce at most one active version per stable identity (subject_id)
CREATE UNIQUE INDEX IF NOT EXISTS idx_subjects_active_identity
    ON subjects (subject_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Source artifacts
# ---------------------------------------------------------------------------

SOURCE_ARTIFACTS_DDL = """
CREATE TABLE IF NOT EXISTS source_artifacts (
    record_id           TEXT NOT NULL,
    artifact_id         TEXT NOT NULL,
    version_id          TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    source_kind         TEXT NOT NULL DEFAULT '',
    source_label        TEXT NOT NULL DEFAULT '',
    uri_or_path         TEXT NOT NULL DEFAULT '',
    mime_type           TEXT NOT NULL DEFAULT '',
    blob_id             TEXT,
    locator_id          TEXT,
    ingested_at         TEXT,
    provided_by_actor   TEXT,
    source_metadata     TEXT NOT NULL DEFAULT '{}',
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    closure_marker      TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    PRIMARY KEY (record_id, version_id),
    -- F05: FK to blobs and actors
    FOREIGN KEY (blob_id) REFERENCES blobs(blob_id),
    FOREIGN KEY (provided_by_actor) REFERENCES actors(actor_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_source_artifacts_active_record
    ON source_artifacts (record_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Blobs (encrypted envelopes)
# ---------------------------------------------------------------------------

BLOBS_DDL = """
CREATE TABLE IF NOT EXISTS blobs (
    blob_id             TEXT PRIMARY KEY,
    record_id           TEXT NOT NULL,
    vault_id            TEXT NOT NULL DEFAULT '',
    envelope_version    INTEGER NOT NULL DEFAULT 1,
    key_version         INTEGER NOT NULL DEFAULT 1,
    nonce               BLOB NOT NULL,
    ciphertext          BLOB NOT NULL,
    aad                 BLOB,
    wrapped_data_key    BLOB,
    data_key_nonce      BLOB,
    blob_sha256         TEXT,
    byte_length         INTEGER NOT NULL,
    state               TEXT NOT NULL DEFAULT 'created'
        CHECK (state IN ('created','stored','verified','corrupted','deleted')),
    created_at          TEXT NOT NULL,
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    -- F05: Vault identity keyed digest for cross-vault blob verification
    vault_keyed_digest  TEXT NOT NULL DEFAULT ''
        CHECK (vault_keyed_digest != '')
);
"""


# ---------------------------------------------------------------------------
# DDL: Reports
# ---------------------------------------------------------------------------

REPORTS_DDL = """
CREATE TABLE IF NOT EXISTS reports (
    record_id           TEXT NOT NULL,
    report_id           TEXT NOT NULL,
    version_id          TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    title               TEXT NOT NULL DEFAULT '',
    source_ids          TEXT NOT NULL DEFAULT '[]',
    observation_ids     TEXT NOT NULL DEFAULT '[]',
    assertion_ids       TEXT NOT NULL DEFAULT '[]',
    claim_ids           TEXT NOT NULL DEFAULT '[]',
    summary             TEXT NOT NULL DEFAULT '',
    structured_data     TEXT NOT NULL DEFAULT '{}',
    authored_at         TEXT,
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    closure_marker      TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    PRIMARY KEY (record_id, version_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_reports_active_record
    ON reports (record_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Observations
# ---------------------------------------------------------------------------

OBSERVATIONS_DDL = """
CREATE TABLE IF NOT EXISTS observations (
    record_id           TEXT NOT NULL,
    observation_id      TEXT NOT NULL,
    version_id          TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    subject_id          TEXT,
    source_artifact_id  TEXT,
    method              TEXT NOT NULL DEFAULT '',
    raw_value           TEXT,
    structured_data     TEXT NOT NULL DEFAULT '{}',
    observed_at         TEXT,
    observer_actor_id   TEXT,
    derivation_id       TEXT,
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    closure_marker      TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    -- Temporal reference: must reference a valid temporal assertion
    temporal_ref        TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (record_id, version_id),
    -- F05: FK to source artifacts and derivation runs
    FOREIGN KEY (source_artifact_id) REFERENCES source_artifacts(artifact_id),
    FOREIGN KEY (derivation_id) REFERENCES derivation_runs(derivation_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_observations_active_record
    ON observations (record_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Assertions
# ---------------------------------------------------------------------------

ASSERTIONS_DDL = """
CREATE TABLE IF NOT EXISTS assertions (
    record_id           TEXT NOT NULL,
    assertion_id        TEXT NOT NULL,
    version_id          TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    subject_id          TEXT,
    assertion_type      TEXT NOT NULL DEFAULT '',
    predicate           TEXT NOT NULL DEFAULT '',
    support_ids         TEXT NOT NULL DEFAULT '[]',
    contra_ids          TEXT NOT NULL DEFAULT '[]',
    confidence          REAL,
    derivation_id       TEXT,
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    closure_marker      TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    provenance_ref      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (record_id, version_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_assertions_active_record
    ON assertions (record_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Claims
# ---------------------------------------------------------------------------

CLAIMS_DDL = """
CREATE TABLE IF NOT EXISTS claims (
    record_id           TEXT NOT NULL,
    claim_id            TEXT NOT NULL,
    version_id          TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    subject_id          TEXT,
    claim_type          TEXT NOT NULL DEFAULT 'descriptive'
        CHECK (claim_type IN ('descriptive','causal','predictive',
               'evaluative','normative','definitional','diagnostic',
               'synthetic','comparative','existential','prudential','taxonomic')),
    claim_status        TEXT NOT NULL DEFAULT 'proposed'
        CHECK (claim_status IN ('proposed','supported','contradicted',
               'resolved','retracted','superseded','disconfirmed','pending_review')),
    claim_origin        TEXT NOT NULL DEFAULT 'observation'
        CHECK (claim_origin IN ('observation','inference','derivation',
               'abduction','analogy','testimony')),
    claim_body          TEXT NOT NULL DEFAULT '',
    evidence_ids        TEXT NOT NULL DEFAULT '[]',
    contradiction_set_id TEXT,
    resolution          TEXT,
    derivation_id       TEXT,
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    closure_marker      TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    provenance_ref      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (record_id, version_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_claims_active_record
    ON claims (record_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Data policies
# ---------------------------------------------------------------------------

DATA_POLICIES_DDL = """
CREATE TABLE IF NOT EXISTS data_policies (
    record_id           TEXT NOT NULL,
    policy_id           TEXT NOT NULL,
    version_id          TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    target_record_id    TEXT NOT NULL,
    sensitivity         TEXT NOT NULL DEFAULT 'sensitive'
        CHECK (sensitivity IN ('ordinary','sensitive','deeply_sensitive')),
    processing_location TEXT NOT NULL DEFAULT 'local_only'
        CHECK (processing_location IN ('local_only','approved_cloud')),
    cloud_policy        TEXT NOT NULL DEFAULT 'never_cloud'
        CHECK (cloud_policy IN ('never_cloud','ask_each_time','named_purpose_and_provider')),
    purpose             TEXT NOT NULL DEFAULT '',
    purpose_expiry      TEXT,
    third_party_scope   TEXT NOT NULL DEFAULT 'none'
        CHECK (third_party_scope IN ('none','incidental','material')),
    retention_policy_id TEXT NOT NULL DEFAULT '',
    retention_review    TEXT,
    export_rule         TEXT NOT NULL DEFAULT 'block'
        CHECK (export_rule IN ('block','ask','redact','allow')),
    export_audience     TEXT NOT NULL DEFAULT '',
    lineage_rule        TEXT NOT NULL DEFAULT 'most_restrictive_parent',
    tx_from             TEXT NOT NULL,
    tx_to               TEXT,
    is_active           INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL,
    closure_marker      TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    PRIMARY KEY (record_id, version_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_data_policies_active_record
    ON data_policies (record_id) WHERE is_active = 1;
"""


# ---------------------------------------------------------------------------
# DDL: Policy lineage edges
# ---------------------------------------------------------------------------

POLICY_LINEAGE_DDL = """
CREATE TABLE IF NOT EXISTS policy_lineage (
    parent_policy_id    TEXT NOT NULL,
    child_policy_id     TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    PRIMARY KEY (parent_policy_id, child_policy_id),
    -- F05: FK to data_policies
    FOREIGN KEY (parent_policy_id) REFERENCES data_policies(policy_id),
    FOREIGN KEY (child_policy_id) REFERENCES data_policies(policy_id)
);
"""


# ---------------------------------------------------------------------------
# DDL: Derivation runs
# ---------------------------------------------------------------------------

DERIVATION_RUNS_DDL = """
CREATE TABLE IF NOT EXISTS derivation_runs (
    derivation_id               TEXT PRIMARY KEY,
    method_kind                 TEXT NOT NULL DEFAULT '',
    code_rule_model_tool        TEXT NOT NULL DEFAULT '',
    code_rule_model_version     TEXT NOT NULL DEFAULT '',
    parameters_config_digest    TEXT NOT NULL DEFAULT '',
    environment_profile         TEXT NOT NULL DEFAULT '',
    started_at                  TEXT,
    ended_at                    TEXT,
    actor_id                    TEXT,
    purpose                     TEXT NOT NULL DEFAULT '',
    validation_outcomes         TEXT NOT NULL DEFAULT '',
    review_state                TEXT NOT NULL DEFAULT 'pending',
    failure_reason              TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# DDL: Derivation inputs/outputs
# ---------------------------------------------------------------------------

DERIVATION_IO_DDL = """
CREATE TABLE IF NOT EXISTS derivation_io (
    derivation_id   TEXT NOT NULL,
    record_id       TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('input','output')),
    PRIMARY KEY (derivation_id, record_id, role),
    -- F05: FK to derivation runs
    FOREIGN KEY (derivation_id) REFERENCES derivation_runs(derivation_id)
);
"""


# ---------------------------------------------------------------------------
# DDL: Audit events
# ---------------------------------------------------------------------------

AUDIT_EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS audit_events (
    event_id                TEXT PRIMARY KEY,
    event_kind              TEXT NOT NULL DEFAULT '',
    occurred_at             TEXT NOT NULL,
    actor_id                TEXT,
    target_record_ids       TEXT NOT NULL DEFAULT '[]',
    operation               TEXT NOT NULL DEFAULT '',
    outcome                 TEXT NOT NULL DEFAULT '',
    reason                  TEXT NOT NULL DEFAULT '',
    -- Content-free allowlist: these fields MUST be empty in F0
    content_preview         TEXT NOT NULL DEFAULT '' CHECK (content_preview = ''),
    search_terms            TEXT NOT NULL DEFAULT '' CHECK (search_terms = ''),
    response_summary        TEXT NOT NULL DEFAULT '' CHECK (response_summary = ''),
    affected_paths          TEXT NOT NULL DEFAULT '' CHECK (affected_paths = ''),
    subject_names           TEXT NOT NULL DEFAULT '' CHECK (subject_names = ''),
    secret_hashes           TEXT NOT NULL DEFAULT '' CHECK (secret_hashes = ''),
    version_id              TEXT,
    created_at              TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# DDL: Deletion requests
# ---------------------------------------------------------------------------

DELETION_REQUESTS_DDL = """
CREATE TABLE IF NOT EXISTS deletion_requests (
    request_id      TEXT PRIMARY KEY,
    actor_id        TEXT,
    reason          TEXT NOT NULL DEFAULT '',
    scope           TEXT NOT NULL DEFAULT 'single_record'
        CHECK (scope IN ('single_record','subject','tree','policy','category')),
    target_ids      TEXT NOT NULL DEFAULT '[]',
    approved_by     TEXT,
    approved_at     TEXT,
    status          TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','approved','rejected','in_progress','completed','failed')),
    created_at      TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# DDL: Deletion plans
# ---------------------------------------------------------------------------

DELETION_PLANS_DDL = """
CREATE TABLE IF NOT EXISTS deletion_plans (
    plan_id                     TEXT PRIMARY KEY,
    request_id                  TEXT NOT NULL,
    target_record_ids           TEXT NOT NULL DEFAULT '[]',
    exclusive_descendant_ids    TEXT NOT NULL DEFAULT '[]',
    mixed_descendant_ids        TEXT NOT NULL DEFAULT '[]',
    invalidate_ids              TEXT NOT NULL DEFAULT '[]',
    recompute_ids               TEXT NOT NULL DEFAULT '[]',
    dependency_graph_snapshot   TEXT NOT NULL DEFAULT '{}',
    executed_at                 TEXT,
    receipt_id                  TEXT,
    status                      TEXT NOT NULL DEFAULT 'pending'
        CHECK (status IN ('pending','executing','completed','failed','rolled_back')),
    created_at                  TEXT NOT NULL,
    -- F05: FK to deletion requests
    FOREIGN KEY (request_id) REFERENCES deletion_requests(request_id)
);
"""


# ---------------------------------------------------------------------------
# DDL: Deletion receipts
# ---------------------------------------------------------------------------

DELETION_RECEIPTS_DDL = """
CREATE TABLE IF NOT EXISTS deletion_receipts (
    receipt_id          TEXT PRIMARY KEY,
    plan_id             TEXT NOT NULL UNIQUE,
    request_id          TEXT NOT NULL,
    records_deleted     INTEGER NOT NULL DEFAULT 0,
    records_invalidated INTEGER NOT NULL DEFAULT 0,
    records_recomputed  INTEGER NOT NULL DEFAULT 0,
    verification_hash   TEXT,
    executed_by         TEXT,
    executed_at         TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    -- F05: FK to deletion plans and requests
    FOREIGN KEY (plan_id) REFERENCES deletion_plans(plan_id),
    FOREIGN KEY (request_id) REFERENCES deletion_requests(request_id)
);
"""


# ---------------------------------------------------------------------------
# DDL: Backup manifests
# ---------------------------------------------------------------------------

BACKUP_MANIFESTS_DDL = """
CREATE TABLE IF NOT EXISTS backup_manifests (
    manifest_id         TEXT PRIMARY KEY,
    vault_id            TEXT NOT NULL,
    created_at          TEXT NOT NULL,
    schema_version      INTEGER NOT NULL,
    record_count        INTEGER NOT NULL DEFAULT 0,
    blob_count          INTEGER NOT NULL DEFAULT 0,
    byte_total          INTEGER NOT NULL DEFAULT 0,
    sha256_hex          TEXT NOT NULL DEFAULT '',
    encrypted           INTEGER NOT NULL DEFAULT 1,
    recovery_header     TEXT,
    storage_path        TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# DDL: Export manifests
# ---------------------------------------------------------------------------

EXPORT_MANIFESTS_DDL = """
CREATE TABLE IF NOT EXISTS export_manifests (
    manifest_id     TEXT PRIMARY KEY,
    vault_id        TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    export_version  TEXT NOT NULL DEFAULT '1.0.0',
    record_count    INTEGER NOT NULL DEFAULT 0,
    blob_count      INTEGER NOT NULL DEFAULT 0,
    encrypted       INTEGER NOT NULL DEFAULT 1,
    schema_versions TEXT NOT NULL DEFAULT '{}',
    storage_path    TEXT NOT NULL DEFAULT ''
);
"""


# ---------------------------------------------------------------------------
# All DDL in dependency order
# ---------------------------------------------------------------------------

ALL_DDL = [
    ("schema_migrations", SCHEMA_MIGRATIONS_DDL),
    ("vault_config", VAULT_CONFIG_DDL),
    ("actors", ACTORS_DDL),
    ("subjects", SUBJECTS_DDL),
    ("source_artifacts", SOURCE_ARTIFACTS_DDL),
    ("blobs", BLOBS_DDL),
    ("reports", REPORTS_DDL),
    ("observations", OBSERVATIONS_DDL),
    ("assertions", ASSERTIONS_DDL),
    ("claims", CLAIMS_DDL),
    ("data_policies", DATA_POLICIES_DDL),
    ("policy_lineage", POLICY_LINEAGE_DDL),
    ("derivation_runs", DERIVATION_RUNS_DDL),
    ("derivation_io", DERIVATION_IO_DDL),
    ("audit_events", AUDIT_EVENTS_DDL),
    ("deletion_requests", DELETION_REQUESTS_DDL),
    ("deletion_plans", DELETION_PLANS_DDL),
    ("deletion_receipts", DELETION_RECEIPTS_DDL),
    ("backup_manifests", BACKUP_MANIFESTS_DDL),
    ("export_manifests", EXPORT_MANIFESTS_DDL),
]


def apply_schema(connection: Any, schema_version: int = 1) -> None:
    """Apply all DDL up to the given schema version.

    F05 (FIX): Enables PRAGMA foreign_keys = ON so that FK constraints
    are enforced. SQLite requires this to be set per-connection.
    Uses executescript for multi-statement DDL entries so that
    CREATE INDEX IF NOT EXISTS can follow CREATE TABLE.
    """
    cur = connection.cursor()
    cur.execute("PRAGMA foreign_keys = ON;")
    if schema_version not in (1, 2, 3, 4, 5, 6, 7, 8):
        raise ValueError("Unsupported schema version")
    full_ddl = SCHEMA_MIGRATIONS_DDL
    for _name, ddl in ALL_DDL:
        full_ddl += "\n" + ddl
    connection.executescript(full_ddl)
    if schema_version >= 2:
        from psyche_os.storage.e03_schema import V2_MIGRATION_STATEMENTS

        for statement in V2_MIGRATION_STATEMENTS:
            connection.execute(statement)
    if schema_version >= 3:
        from psyche_os.storage.e05_schema import V3_MIGRATION_STATEMENTS

        for statement in V3_MIGRATION_STATEMENTS:
            connection.execute(statement)
    if schema_version >= 4:
        from psyche_os.storage.e06_schema import V4_MIGRATION_STATEMENTS

        for statement in V4_MIGRATION_STATEMENTS:
            connection.execute(statement)
    if schema_version >= 5:
        from psyche_os.storage.e08_schema import V5_MIGRATION_STATEMENTS

        for statement in V5_MIGRATION_STATEMENTS:
            connection.execute(statement)
    if schema_version >= 6:
        from psyche_os.storage.v3a0_session_schema import V6_MIGRATION_STATEMENTS

        for statement in V6_MIGRATION_STATEMENTS:
            connection.execute(statement)
    if schema_version >= 7:
        from psyche_os.storage.v3a1_exploration_schema import V7_MIGRATION_STATEMENTS
        for statement in V7_MIGRATION_STATEMENTS:
            connection.execute(statement)
    if schema_version >= 8:
        from psyche_os.storage.v3a1_exploration_v8_schema import V8_MIGRATION_STATEMENTS

        for statement in V8_MIGRATION_STATEMENTS:
            connection.execute(statement)
    connection.commit()
