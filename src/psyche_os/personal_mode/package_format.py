"""Personal-only encrypted package logical format, free of archive modules."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from typing import Any

from psyche_os.personal_mode.schema import (
    PERSONAL_V10_INVENTORY,
    PERSONAL_V11_INVENTORY,
    PERSONAL_V12_INVENTORY,
    PERSONAL_V13_INVENTORY,
    PERSONAL_V14_INVENTORY,
    PERSONAL_V15_INVENTORY,
    initialize_personal_v10,
    initialize_personal_v11,
    initialize_personal_v12,
    initialize_personal_v13,
    initialize_personal_v14,
    initialize_personal_v15,
)

PERSONAL_V10_FORMAT_VERSION = 3
PERSONAL_V11_FORMAT_VERSION = 4
PERSONAL_V12_FORMAT_VERSION = 5
PERSONAL_V13_FORMAT_VERSION = 6
PERSONAL_V14_FORMAT_VERSION = 7
PERSONAL_V15_FORMAT_VERSION = 8
class PersonalPackageError(Exception):
    pass


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _expected_schemas(version: int) -> dict[str, list[str]]:
    reference = sqlite3.connect(":memory:")
    try:
        (initialize_personal_v10 if version == 10 else initialize_personal_v11 if version == 11 else initialize_personal_v12 if version == 12 else initialize_personal_v13 if version == 13 else initialize_personal_v14 if version == 14 else initialize_personal_v15)(reference)
        return {
            table: [row[1] for row in reference.execute(f"PRAGMA table_info({table})")]
            for table in (PERSONAL_V10_INVENTORY if version == 10 else PERSONAL_V11_INVENTORY if version == 11 else PERSONAL_V12_INVENTORY if version == 12 else PERSONAL_V13_INVENTORY if version == 13 else PERSONAL_V14_INVENTORY if version == 14 else PERSONAL_V15_INVENTORY)
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
    versions = tuple(row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version"))
    inventory: tuple[str, ...]
    format_version: int
    if versions == (10,):
        version, inventory, format_version = 10, PERSONAL_V10_INVENTORY, PERSONAL_V10_FORMAT_VERSION
    elif versions == (10, 11):
        version, inventory, format_version = 11, PERSONAL_V11_INVENTORY, PERSONAL_V11_FORMAT_VERSION
    elif versions == (10, 11, 12):
        version, inventory, format_version = 12, PERSONAL_V12_INVENTORY, PERSONAL_V12_FORMAT_VERSION
    elif versions == (10, 11, 12, 13):
        version, inventory, format_version = 13, PERSONAL_V13_INVENTORY, PERSONAL_V13_FORMAT_VERSION
    elif versions == (10, 11, 12, 13, 14):
        version, inventory, format_version = 14, PERSONAL_V14_INVENTORY, PERSONAL_V14_FORMAT_VERSION
    elif versions == (10, 11, 12, 13, 14, 15):
        version, inventory, format_version = 15, PERSONAL_V15_INVENTORY, PERSONAL_V15_FORMAT_VERSION
    else:
        raise PersonalPackageError()
    if actual != set(inventory):
        raise PersonalPackageError()
    tables: dict[str, list[dict[str, Any]]] = {}
    schemas: dict[str, list[str]] = {}
    checksums: dict[str, str] = {}
    for table in inventory:
        cursor = connection.execute(f"SELECT * FROM {table}")
        columns = [item[0] for item in cursor.description]
        rows = [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
        tables[table] = rows
        schemas[table] = columns
        checksums[table] = _digest(rows)
    return {
        "format": "psyche-os-personal-logical-package",
        "format_version": format_version,
        "schema_version": version,
        "inventory": list(inventory),
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
        version = package.get("schema_version")
        inventory = PERSONAL_V10_INVENTORY if version == 10 else PERSONAL_V11_INVENTORY if version == 11 else PERSONAL_V12_INVENTORY if version == 12 else PERSONAL_V13_INVENTORY if version == 13 else PERSONAL_V14_INVENTORY if version == 14 else PERSONAL_V15_INVENTORY if version == 15 else ()
        expected_format = PERSONAL_V10_FORMAT_VERSION if version == 10 else PERSONAL_V11_FORMAT_VERSION if version == 11 else PERSONAL_V12_FORMAT_VERSION if version == 12 else PERSONAL_V13_FORMAT_VERSION if version == 13 else PERSONAL_V14_FORMAT_VERSION if version == 14 else PERSONAL_V15_FORMAT_VERSION if version == 15 else -1
        if (
            package["format"] != "psyche-os-personal-logical-package"
            or package["format_version"] != expected_format
            or tuple(package["inventory"]) != inventory
            or _expected_schemas(version) != package["schemas"]
        ):
            return False
        for table in inventory:
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
    version = package["schema_version"]
    (initialize_personal_v10 if version == 10 else initialize_personal_v11 if version == 11 else initialize_personal_v12 if version == 12 else initialize_personal_v13 if version == 13 else initialize_personal_v14 if version == 14 else initialize_personal_v15)(connection)
    try:
        connection.execute("BEGIN IMMEDIATE")
        connection.execute("PRAGMA defer_foreign_keys=ON")
        # V12+ initialization seeds a fail-closed policy row.  A package is the
        # authoritative logical snapshot, so remove that seed before restoring
        # its corresponding row rather than merging policy state.
        if version in (12, 13, 14, 15):
            connection.execute("DELETE FROM interview_policy")
        connection.execute("DELETE FROM schema_migrations")
        inventory = PERSONAL_V10_INVENTORY if version == 10 else PERSONAL_V11_INVENTORY if version == 11 else PERSONAL_V12_INVENTORY if version == 12 else PERSONAL_V13_INVENTORY if version == 13 else PERSONAL_V14_INVENTORY if version == 14 else PERSONAL_V15_INVENTORY
        for table in (*(table for table in inventory if table != "schema_migrations"), "schema_migrations"):
            for row in package["tables"][table]:
                columns = list(row)
                connection.execute(
                    f"INSERT INTO {table}({','.join(columns)}) VALUES({','.join('?' for _ in columns)})",
                    [row[column] for column in columns],
                )
        if version == 10:
            connection.commit()
            initialize_personal_v15(connection)
            return
        if create_personal_package(connection)["package_checksum"] != package["package_checksum"]:
            raise PersonalPackageError()
        connection.commit()
    except Exception:
        connection.rollback()
        raise
