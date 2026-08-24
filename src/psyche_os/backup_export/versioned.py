"""Explicit schema-versioned legacy and Personal-V10 portability helpers.

The accepted encrypted E01 V1 package reader remains unchanged.  E03 uses this
small dispatch layer for exact-inventory semantic portability proofs and for
open, per-table checksummed logical export. Legacy format-2 packages retain
their historical inventory; Personal V10 uses the distinct format-3 spec.
This module does not claim E01's authenticated encrypted recovery,
clean-device recovery, or atomic activation guarantees for legacy packages.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from typing import Any

from psyche_os.storage.e03_schema import inventory_for_schema as _legacy_inventory_for_schema
from psyche_os.storage.schema import apply_schema
from psyche_os.storage.personal_mode_v10_schema import V10_INVENTORY


class VersionedPackageError(Exception):
    pass


@dataclass(frozen=True)
class ArchiveSpec:
    """Immutable, explicit archive contract for one supported schema."""

    format_version: int
    schema_version: int
    inventory: tuple[str, ...]
    restore_order: tuple[str, ...]


def _legacy_spec(schema_version: int) -> ArchiveSpec:
    inventory = _legacy_inventory_for_schema(schema_version)
    return ArchiveSpec(2, schema_version, inventory, inventory)


# This is deliberately separate from legacy V1/V2 package semantics.  It is
# the exact V10 relational graph, not a runtime discovery of whatever tables
# happen to be present.
PERSONAL_V10_SPEC = ArchiveSpec(
    format_version=3,
    schema_version=10,
    inventory=V10_INVENTORY,
    restore_order=tuple(
        table for table in V10_INVENTORY
        if table not in {"policy_identities", "data_policies", "policy_lineage", "schema_migrations"}
    ) + ("policy_identities", "data_policies", "policy_lineage", "schema_migrations"),
)


def archive_spec_for_schema(schema_version: int) -> ArchiveSpec:
    if schema_version == 10:
        return PERSONAL_V10_SPEC
    if schema_version in (1, 2, 3, 4, 5):
        return _legacy_spec(schema_version)
    raise ValueError("Unsupported schema version")


def _schema_version(connection: Any) -> int:
    row = connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()
    if not row or row[0] not in (1, 2, 3, 4, 5, 10):
        raise VersionedPackageError("Schema migration evidence is missing")
    return int(row[0])


def _safe(value: Any) -> Any:
    return value.hex() if isinstance(value, bytes) else value


def _expected_schemas(schema_version: int) -> dict[str, list[str]]:
    reference = sqlite3.connect(":memory:")
    try:
        apply_schema(reference, schema_version)
        return {
            table: [row[1] for row in reference.execute(f"PRAGMA table_info({table})")]
            for table in archive_spec_for_schema(schema_version).inventory
        }
    finally:
        reference.close()


def create_versioned_package(connection: Any) -> dict[str, Any]:
    schema_version = _schema_version(connection)
    spec = archive_spec_for_schema(schema_version)
    inventory = spec.inventory
    actual = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    if actual != set(inventory):
        raise VersionedPackageError("Exact schema inventory mismatch")
    tables: dict[str, list[dict[str, Any]]] = {}
    schemas: dict[str, list[str]] = {}
    checksums: dict[str, str] = {}
    for table in inventory:
        cursor = connection.execute(f"SELECT * FROM {table}")
        columns = [item[0] for item in cursor.description]
        rows = [{column: _safe(value) for column, value in zip(columns, row, strict=True)} for row in cursor.fetchall()]
        tables[table] = rows
        schemas[table] = columns
        checksums[table] = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    package = {"format":"psyche-os-logical-portability-package","format_version":spec.format_version,"schema_version":schema_version,"inventory":list(inventory),"schemas":schemas,"checksums":checksums,"tables":tables}
    package["package_checksum"] = hashlib.sha256(json.dumps(package, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return package


def verify_versioned_package(package: dict[str, Any]) -> bool:
    try:
        if set(package) != {"format","format_version","schema_version","inventory","schemas","checksums","tables","package_checksum"}:
            return False
        if package["format"] != "psyche-os-logical-portability-package":
            return False
        spec = archive_spec_for_schema(int(package["schema_version"]))
        if package["format_version"] != spec.format_version:
            return False
        expected = spec.inventory
        expected_schemas = _expected_schemas(int(package["schema_version"]))
        inventory = package["inventory"]
        if not isinstance(inventory, list) or len(inventory) != len(set(inventory)) or tuple(inventory) != expected:
            return False
        if set(package["tables"]) != set(expected) or set(package["schemas"]) != set(expected) or set(package["checksums"]) != set(expected):
            return False
        for table in expected:
            if package["schemas"][table] != expected_schemas[table]:
                return False
            rows = package["tables"][table]
            if any(set(row) != set(package["schemas"][table]) for row in rows):
                return False
            digest = hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if digest != package["checksums"][table]:
                return False
        body = dict(package)
        checksum = body.pop("package_checksum")
        return bool(
            hashlib.sha256(
                json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
            == checksum
        )
    except (KeyError, TypeError, ValueError):
        return False


def restore_versioned_package(package: dict[str, Any], connection: Any) -> None:
    """Restore logical semantic state into an isolated empty target.

    This is a portability operation, not authenticated E01 recovery or atomic
    activation of a live vault.
    """
    if not verify_versioned_package(package):
        raise VersionedPackageError("Package verification failed")
    existing = connection.execute(
        "SELECT name FROM sqlite_master WHERE type IN ('table','view') AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    if existing:
        raise VersionedPackageError("Logical restore target must be isolated and empty")
    schema_version = int(package["schema_version"])
    apply_schema(connection, schema_version)
    try:
        connection.execute("BEGIN IMMEDIATE")
        for table in archive_spec_for_schema(schema_version).restore_order:
            rows = package["tables"][table]
            for row in rows:
                columns = list(row)
                values = [bytes.fromhex(value) if column in {"db_key_salt","blob_envelope_key_salt","vmk_os_wrapped","nonce","ciphertext","aad","wrapped_data_key","data_key_nonce","bounded_bytes"} and isinstance(value,str) else value for column,value in row.items()]
                connection.execute(f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})", values)
        if create_versioned_package(connection)["package_checksum"] != package["package_checksum"]:
            raise VersionedPackageError("Restored semantic state mismatch")
        connection.commit()
    except Exception:
        connection.rollback()
        raise


def create_versioned_export(connection: Any) -> dict[str, Any]:
    package = create_versioned_package(connection)
    return {**package, "format":"psyche-os-open-json-export", "human_readable":True}
