"""Personal-only encrypted package logical format, free of archive modules."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from psyche_os.personal_mode.schema import initialize_personal_v10

PERSONAL_V10_FORMAT_VERSION = 3
PERSONAL_V10_INVENTORY = (
    "schema_migrations",
    "reflection_sessions",
    "reflection_turns",
    "reflection_explorations",
    "reflection_exploration_snapshots",
    "reflection_context_items",
    "reflection_context_sources",
    "reflection_hypotheses",
    "reflection_hypothesis_context_refs",
    "reflection_questions",
    "reflection_snapshot_context_items",
    "reflection_snapshot_hypotheses",
    "reflection_snapshot_questions",
    "reflection_formulations",
)
_RESTORE_ORDER = (
    *(table for table in PERSONAL_V10_INVENTORY if table != "schema_migrations"),
    "schema_migrations",
)


class PersonalPackageError(Exception):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _expected_schemas() -> dict[str, list[str]]:
    reference = sqlite3.connect(":memory:")
    try:
        initialize_personal_v10(reference)
        return {
            table: [row[1] for row in reference.execute(f"PRAGMA table_info({table})")]
            for table in PERSONAL_V10_INVENTORY
        }
    finally:
        reference.close()


def _package_body(connection: Any) -> dict[str, Any]:
    actual = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if actual != set(PERSONAL_V10_INVENTORY):
        raise PersonalPackageError()
    tables: dict[str, list[dict[str, Any]]] = {}
    schemas: dict[str, list[str]] = {}
    checksums: dict[str, str] = {}
    for table in PERSONAL_V10_INVENTORY:
        cursor = connection.execute(f"SELECT * FROM {table}")
        columns = [item[0] for item in cursor.description]
        rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        tables[table] = rows
        schemas[table] = columns
        checksums[table] = _digest(rows)
    return {
        "format": "psyche-os-personal-logical-package",
        "format_version": PERSONAL_V10_FORMAT_VERSION,
        "schema_version": 10,
        "inventory": list(PERSONAL_V10_INVENTORY),
        "schemas": schemas,
        "checksums": checksums,
        "tables": tables,
    }


def create_personal_package(connection: Any) -> dict[str, Any]:
    package = _package_body(connection)
    package["package_checksum"] = _digest(package)
    return package


def verify_personal_package(package: Any) -> bool:
    if not verify_personal_package_structure(package):
        return False
    body = dict(package)
    checksum = body.pop("package_checksum")
    return _digest(body) == checksum


def _valid_package(package: Any) -> bool:
    return verify_personal_package(package)


def verify_personal_package_structure(package: Any) -> bool:
    """Check every unencrypted field apart from the final package digest."""
    try:
        if not isinstance(package, dict) or set(package) != {
            "format",
            "format_version",
            "schema_version",
            "inventory",
            "schemas",
            "checksums",
            "tables",
            "package_checksum",
        }:
            return False
        if (
            package["format"] != "psyche-os-personal-logical-package"
            or package["format_version"] != 3
            or package["schema_version"] != 10
            or tuple(package["inventory"]) != PERSONAL_V10_INVENTORY
            or _expected_schemas() != package["schemas"]
        ):
            return False
        for table in PERSONAL_V10_INVENTORY:
            rows = package["tables"][table]
            if (
                any(set(row) != set(package["schemas"][table]) for row in rows)
                or _digest(rows) != package["checksums"][table]
            ):
                return False
        return True
    except (KeyError, TypeError, ValueError, sqlite3.Error):
        return False


def restore_personal_package(package: dict[str, Any], connection: Any) -> None:
    if not _valid_package(package):
        raise PersonalPackageError()
    existing = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    if existing:
        raise PersonalPackageError()
    initialize_personal_v10(connection)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("DELETE FROM schema_migrations")
        for table in _RESTORE_ORDER:
            for row in package["tables"][table]:
                columns = list(row)
                connection.execute(
                    f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                    [row[column] for column in columns],
                )
        if create_personal_package(connection)["package_checksum"] != package["package_checksum"]:
            raise PersonalPackageError()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
