"""Additive E08 V4-to-V5 untrusted-import storage delta."""

from __future__ import annotations

import hashlib
import sqlite3

from psyche_os.storage.e06_schema import V4_INVENTORY

V5_ADDED_TABLES: tuple[str, ...] = (
    "e08_quarantine_objects",
    "e08_import_sources",
    "e08_import_nodes",
)
V5_INVENTORY: tuple[str, ...] = V4_INVENTORY + V5_ADDED_TABLES

V5_MIGRATION_SQL = """
CREATE TABLE e08_quarantine_objects (
 quarantine_id TEXT PRIMARY KEY,
 bounded_bytes BLOB NOT NULL,
 protected_digest_ref TEXT NOT NULL,
 fingerprint_key_version TEXT NOT NULL,
 processing_state TEXT NOT NULL CHECK(processing_state IN ('committed','deleting')),
 byte_count INTEGER NOT NULL CHECK(byte_count=length(bounded_bytes)),
 created_at TEXT NOT NULL
);
CREATE TABLE e08_import_sources (
 source_version_id TEXT PRIMARY KEY,
 source_record_id TEXT NOT NULL,
 quarantine_id TEXT NOT NULL UNIQUE,
 parser_identity TEXT NOT NULL,
 profile_identity TEXT NOT NULL,
 policy_record_id TEXT NOT NULL,
 policy_version_id TEXT NOT NULL,
 policy_decision_id TEXT NOT NULL,
 preview_id TEXT NOT NULL,
 consent_id TEXT NOT NULL UNIQUE,
 correction_of TEXT,
 state TEXT NOT NULL CHECK(state IN ('active','superseded')),
 created_at TEXT NOT NULL,
 FOREIGN KEY(quarantine_id) REFERENCES e08_quarantine_objects(quarantine_id) ON DELETE CASCADE,
 FOREIGN KEY(source_record_id,source_version_id) REFERENCES source_artifacts(record_id,version_id) ON DELETE CASCADE
);
CREATE TABLE e08_import_nodes (
 record_id TEXT PRIMARY KEY,
 version_id TEXT NOT NULL UNIQUE,
 kind TEXT NOT NULL CHECK(kind IN ('source_segment','exclusion','redaction','attributed_verbatim_report','review_needed_assertion_proposal','derived_relation')),
 source_version_id TEXT NOT NULL,
 parent_ids TEXT NOT NULL CHECK(json_valid(parent_ids) AND json_type(parent_ids)='array'),
 policy_decision_id TEXT NOT NULL,
 locator TEXT CHECK(locator IS NULL OR json_valid(locator)),
 method_version TEXT,
 status TEXT NOT NULL CHECK(status IN ('active','review_needed','invalidated','superseded')),
 content TEXT,
 created_at TEXT NOT NULL
);
CREATE INDEX idx_e08_nodes_source ON e08_import_nodes(source_version_id);
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
        raise ValueError("Incomplete E08 migration SQL")
    return tuple(statements)


V5_MIGRATION_STATEMENTS = _split(V5_MIGRATION_SQL)
V5_MIGRATION_CHECKSUM = hashlib.sha256(
    (";\n".join(V5_MIGRATION_STATEMENTS) + ";").encode()
).hexdigest()
