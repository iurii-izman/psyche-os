"""V10 policy-identity repair and SQLite-safe reflection rebuild.

This module deliberately owns executable V10 rather than exposing its registry
as a general caller write surface.  The migration is performed only by
``Migrator`` after its exact V9 preflight has succeeded.
"""

from __future__ import annotations

import hashlib
from typing import Any

from psyche_os.storage.v3a1_exploration_v8_schema import V8_INVENTORY
from psyche_os.storage.v3a3_action_schema import V9_ADDED_TABLES

V9_INVENTORY = V8_INVENTORY + V9_ADDED_TABLES
V10_ADDED_TABLES = ("policy_identities",)
V10_INVENTORY = V9_INVENTORY + V10_ADDED_TABLES
V10_LABEL = "pmv1_policy_identity_repair_v10"
# The marker binds the approved amendment identity into the normal migration
# checksum chain; the executable rebuild remains intentionally code-owned.
V10_MIGRATION_STATEMENTS = ("SELECT 'PMV1-V10-POLICY-IDENTITY-REPAIR-A1'",)
V10_MIGRATION_CHECKSUM = hashlib.sha256(
    (";\n".join(V10_MIGRATION_STATEMENTS) + ";").encode("utf-8")
).hexdigest()

POLICY_IDENTITIES_DDL = """
CREATE TABLE policy_identities (
    policy_id TEXT PRIMARY KEY,
    record_id TEXT NOT NULL UNIQUE,
    UNIQUE(record_id, policy_id)
)
"""

DATA_POLICIES_V10_DDL = """
CREATE TABLE data_policies_v10_new (
    record_id TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    version_id TEXT NOT NULL DEFAULT '',
    previous_version_id TEXT NOT NULL DEFAULT '',
    target_record_id TEXT NOT NULL,
    sensitivity TEXT NOT NULL DEFAULT 'sensitive'
        CHECK (sensitivity IN ('ordinary','sensitive','deeply_sensitive')),
    processing_location TEXT NOT NULL DEFAULT 'local_only'
        CHECK (processing_location IN ('local_only','approved_cloud')),
    cloud_policy TEXT NOT NULL DEFAULT 'never_cloud'
        CHECK (cloud_policy IN ('never_cloud','ask_each_time','named_purpose_and_provider')),
    purpose TEXT NOT NULL DEFAULT '',
    purpose_expiry TEXT,
    third_party_scope TEXT NOT NULL DEFAULT 'none'
        CHECK (third_party_scope IN ('none','incidental','material')),
    retention_policy_id TEXT NOT NULL DEFAULT '',
    retention_review TEXT,
    export_rule TEXT NOT NULL DEFAULT 'block'
        CHECK (export_rule IN ('block','ask','redact','allow')),
    export_audience TEXT NOT NULL DEFAULT '',
    lineage_rule TEXT NOT NULL DEFAULT 'most_restrictive_parent',
    tx_from TEXT NOT NULL,
    tx_to TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    closure_marker TEXT NOT NULL DEFAULT ''
        CHECK (closure_marker IN ('', 'pending_invalidation', 'invalidated')),
    PRIMARY KEY (record_id, version_id),
    FOREIGN KEY (record_id, policy_id)
        REFERENCES policy_identities(record_id, policy_id)
)
"""

POLICY_LINEAGE_V10_DDL = """
CREATE TABLE policy_lineage_v10_new (
    parent_policy_id TEXT NOT NULL,
    child_policy_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (parent_policy_id, child_policy_id),
    FOREIGN KEY (parent_policy_id) REFERENCES policy_identities(policy_id),
    FOREIGN KEY (child_policy_id) REFERENCES policy_identities(policy_id)
)
"""

REFLECTION_SESSIONS_V10_DDL = """
CREATE TABLE reflection_sessions_v10_new (
 session_id TEXT PRIMARY KEY,
 title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
 state TEXT NOT NULL CHECK(state IN ('ACTIVE','CLOSED')),
 retention TEXT NOT NULL CHECK(retention = 'ENCRYPTED_LOCAL'),
 data_mode TEXT NOT NULL CHECK(data_mode IN ('synthetic_only','real_personal')),
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL,
 closed_at TEXT,
 turn_count INTEGER NOT NULL DEFAULT 0 CHECK(turn_count >= 0)
)
"""

_POLICY_COLUMNS = (
    "record_id, policy_id, version_id, previous_version_id, target_record_id, "
    "sensitivity, processing_location, cloud_policy, purpose, purpose_expiry, "
    "third_party_scope, retention_policy_id, retention_review, export_rule, "
    "export_audience, lineage_rule, tx_from, tx_to, is_active, created_at, closure_marker"
)
_SESSION_COLUMNS = "session_id, title, state, retention, data_mode, created_at, updated_at, closed_at, turn_count"


def preflight_exact_v9(connection: Any) -> None:
    """Accept only the known V9 shape plus its two malformed lineage FKs."""
    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if tables != set(V9_INVENTORY):
        raise ValueError("V10 exact V9 inventory mismatch")
    relevant = connection.execute(
        "SELECT type, name, tbl_name FROM sqlite_master "
        "WHERE tbl_name IN ('data_policies','policy_lineage','reflection_sessions') "
        "AND type IN ('index','trigger') AND name NOT LIKE 'sqlite_autoindex%' ORDER BY type,name"
    ).fetchall()
    if relevant != [("index", "idx_data_policies_active_record", "data_policies"),
                    ("index", "idx_reflection_sessions_updated", "reflection_sessions")]:
        raise ValueError("V10 exact V9 rebuild-object mismatch")
    policy_fks = connection.execute("PRAGMA foreign_key_list(policy_lineage)").fetchall()
    if len(policy_fks) != 2 or {row[2] for row in policy_fks} != {"data_policies"} or {row[3] for row in policy_fks} != {"parent_policy_id", "child_policy_id"} or {row[4] for row in policy_fks} != {"policy_id"}:
        raise ValueError("V10 exact V9 policy lineage FK mismatch")
    if connection.execute("PRAGMA integrity_check").fetchone() != ("ok",):
        raise ValueError("V10 integrity check failed")
    active = connection.execute(
        "SELECT record_id FROM data_policies WHERE is_active=1 GROUP BY record_id HAVING COUNT(*) != 1"
    ).fetchone()
    if active:
        raise ValueError("V10 active policy version invariant failed")
    ambiguous = connection.execute(
        "SELECT 1 FROM (SELECT policy_id FROM data_policies GROUP BY policy_id HAVING COUNT(DISTINCT record_id) != 1) "
        "UNION ALL SELECT 1 FROM (SELECT record_id FROM data_policies GROUP BY record_id HAVING COUNT(DISTINCT policy_id) != 1) LIMIT 1"
    ).fetchone()
    if ambiguous:
        raise ValueError("POLICY_IDENTITY_AMBIGUOUS")
    orphan = connection.execute(
        "SELECT 1 FROM policy_lineage l WHERE NOT EXISTS (SELECT 1 FROM data_policies p WHERE p.policy_id=l.parent_policy_id) "
        "OR NOT EXISTS (SELECT 1 FROM data_policies p WHERE p.policy_id=l.child_policy_id) LIMIT 1"
    ).fetchone()
    if orphan:
        raise ValueError("POLICY_LINEAGE_ORPHAN")


def apply_v10_rebuild(connection: Any) -> None:
    """Run inside Migrator's transaction while foreign keys are disabled."""
    connection.execute(POLICY_IDENTITIES_DDL)
    connection.execute(
        "INSERT INTO policy_identities(policy_id,record_id) "
        "SELECT policy_id, record_id FROM data_policies GROUP BY policy_id, record_id"
    )
    connection.execute(DATA_POLICIES_V10_DDL)
    connection.execute(f"INSERT INTO data_policies_v10_new ({_POLICY_COLUMNS}) SELECT {_POLICY_COLUMNS} FROM data_policies")
    connection.execute(POLICY_LINEAGE_V10_DDL)
    connection.execute("INSERT INTO policy_lineage_v10_new(parent_policy_id,child_policy_id,created_at) SELECT parent_policy_id,child_policy_id,created_at FROM policy_lineage")
    connection.execute(REFLECTION_SESSIONS_V10_DDL)
    connection.execute(f"INSERT INTO reflection_sessions_v10_new ({_SESSION_COLUMNS}) SELECT {_SESSION_COLUMNS} FROM reflection_sessions")
    connection.execute("DROP TABLE policy_lineage")
    connection.execute("DROP TABLE data_policies")
    connection.execute("DROP TABLE reflection_sessions")
    connection.execute("ALTER TABLE data_policies_v10_new RENAME TO data_policies")
    connection.execute("ALTER TABLE policy_lineage_v10_new RENAME TO policy_lineage")
    connection.execute("ALTER TABLE reflection_sessions_v10_new RENAME TO reflection_sessions")
    connection.execute("CREATE UNIQUE INDEX idx_data_policies_active_record ON data_policies(record_id) WHERE is_active = 1")
    connection.execute("CREATE INDEX idx_reflection_sessions_updated ON reflection_sessions(updated_at DESC)")
