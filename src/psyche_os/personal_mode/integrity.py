"""The one fail-closed integrity oracle for a Personal vault.

This is deliberately a small, Personal-only boundary.  It validates a keyed
SQLCipher connection that has already been opened by trusted code; it never
repairs, migrates, or accepts a caller-provided path.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from psyche_os.personal_mode.key_envelope import PersonalKeyEnvelope
from psyche_os.personal_mode.schema import (
    PERSONAL_V10_INVENTORY,
    PERSONAL_V11_INVENTORY,
    PERSONAL_V12_INVENTORY,
    PERSONAL_V13_INVENTORY,
    initialize_personal_v10,
    initialize_personal_v11,
    initialize_personal_v12,
    initialize_personal_v13,
)


class PersonalIntegrityError(Exception):
    """Content-free indication that a Personal vault is not safe to use."""


_PROFILE_ID = "local_personal_evidence_reflection_windows_v1"
_PROFILE_VERSION = "v1"


def _schema_fingerprint(version: int) -> dict[str, tuple[tuple[Any, ...], ...]]:
    reference = sqlite3.connect(":memory:")
    try:
        (initialize_personal_v10 if version == 10 else initialize_personal_v11 if version == 11 else initialize_personal_v12 if version == 12 else initialize_personal_v13)(reference)
        inventory = PERSONAL_V10_INVENTORY if version == 10 else PERSONAL_V11_INVENTORY if version == 11 else PERSONAL_V12_INVENTORY if version == 12 else PERSONAL_V13_INVENTORY
        return {
            table: tuple(reference.execute(f"PRAGMA table_info({table})").fetchall())
            for table in inventory
        }
    finally:
        reference.close()


_EXPECTED = {10: _schema_fingerprint(10), 11: _schema_fingerprint(11), 12: _schema_fingerprint(12), 13: _schema_fingerprint(13)}


def verify_personal_vault(connection: Any, envelope: PersonalKeyEnvelope) -> int:
    """Prove the opened vault is the exact supported Personal generation.

    SQLCipher reports a keyed ``cipher_integrity_check`` before the ordinary
    SQLite integrity and FK checks.  Any unavailable pragma, malformed result,
    schema drift, or envelope identity mismatch is a closed failure.
    """
    try:
        if (
            envelope.value["vault_id"] != "personal_vault"
            or envelope.value["profile_id"] != _PROFILE_ID
            or envelope.value["profile_version"] != _PROFILE_VERSION
        ):
            raise PersonalIntegrityError()
        # SQLCipher builds which implement this pragma return ``ok``; the
        # bundled SQLCipher compatibility build reports no rows for an
        # unsupported pragma.  In either case, any reported non-ok result is
        # closed.  SQLite's mandatory integrity check remains the fallback.
        cipher_result = connection.execute("PRAGMA cipher_integrity_check").fetchall()
        if cipher_result not in ([], [("ok",)]):
            raise PersonalIntegrityError()
        if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
            raise PersonalIntegrityError()
        if connection.execute("PRAGMA foreign_key_check").fetchall() != []:
            raise PersonalIntegrityError()
        versions = tuple(row[0] for row in connection.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall())
        if versions not in {(10,), (10, 11), (10, 11, 12), (10, 11, 12, 13)}:
            raise PersonalIntegrityError()
        version = versions[-1]
        inventory = PERSONAL_V10_INVENTORY if version == 10 else PERSONAL_V11_INVENTORY if version == 11 else PERSONAL_V12_INVENTORY if version == 12 else PERSONAL_V13_INVENTORY
        actual = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        if actual != set(inventory):
            raise PersonalIntegrityError()
        for table, expected in _EXPECTED[version].items():
            if tuple(connection.execute(f"PRAGMA table_info({table})").fetchall()) != expected:
                raise PersonalIntegrityError()
        modes = connection.execute("SELECT DISTINCT data_mode FROM reflection_sessions").fetchall()
        if modes not in ([], [("real_personal",)]):
            raise PersonalIntegrityError()
        return version
    except PersonalIntegrityError:
        raise
    except Exception as exc:
        raise PersonalIntegrityError() from exc
