"""Synthetic regression proof for PMV1-V10-POLICY-IDENTITY-REPAIR-A1."""

from __future__ import annotations

import sqlite3

import pytest

from psyche_os.storage.migrations import Migrator
from psyche_os.backup_export.versioned import (
    VersionedPackageError,
    create_versioned_package,
    restore_versioned_package,
    verify_versioned_package,
)


def _v9() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(9).success
    return connection


def _policy(connection: sqlite3.Connection, record_id: str, policy_id: str, version_id: str) -> None:
    connection.execute(
        "INSERT INTO data_policies(record_id,policy_id,version_id,target_record_id,tx_from,is_active,created_at) "
        "VALUES(?,?,?,?,?,?,?)",
        (record_id, policy_id, version_id, "target-" + record_id, "now", 1, "now"),
    )


def test_v10_repairs_exact_v9_and_preserves_versions_and_payload() -> None:
    connection = _v9()
    _policy(connection, "record-a", "policy-a", "a-v1")
    connection.execute("UPDATE data_policies SET is_active=0, tx_to='later' WHERE record_id='record-a'")
    _policy(connection, "record-a", "policy-a", "a-v2")
    _policy(connection, "record-b", "policy-b", "b-v1")
    connection.execute(
        "INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) VALUES('policy-a','policy-b','now')"
    )
    connection.commit()
    with pytest.raises(sqlite3.OperationalError, match="foreign key mismatch"):
        connection.execute("PRAGMA foreign_key_check").fetchall()

    report = Migrator(connection).apply(10)
    assert report.success and report.applied == [10]
    assert connection.execute("SELECT policy_id,record_id FROM policy_identities ORDER BY policy_id").fetchall() == [
        ("policy-a", "record-a"), ("policy-b", "record-b")
    ]
    assert connection.execute("SELECT record_id,policy_id,version_id,is_active FROM data_policies ORDER BY version_id").fetchall() == [
        ("record-a", "policy-a", "a-v1", 0), ("record-a", "policy-a", "a-v2", 1), ("record-b", "policy-b", "b-v1", 1)
    ]
    assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
    assert connection.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert Migrator(connection).apply(10).success


@pytest.mark.parametrize(
    ("rows", "expected"),
    [
        ([("record-a", "policy-a", "a-v1"), ("record-b", "policy-a", "a-v2")], "POLICY_IDENTITY_AMBIGUOUS"),
        ([("record-a", "policy-a", "a-v1"), ("record-a", "policy-b", "a-v2")], "POLICY_IDENTITY_AMBIGUOUS"),
    ],
)
def test_v10_rejects_ambiguous_legacy_identity_without_mutation(rows: list[tuple[str, str, str]], expected: str) -> None:
    connection = _v9()
    for row in rows:
        connection.execute("UPDATE data_policies SET is_active=0 WHERE record_id=?", (row[0],))
        _policy(connection, *row)
    connection.commit()
    report = Migrator(connection).apply(10)
    assert not report.success and report.errors == [expected]
    assert Migrator(connection).current_version() == 9
    assert connection.execute("SELECT name FROM sqlite_master WHERE name='policy_identities'").fetchone() is None


@pytest.mark.parametrize("column", ["parent_policy_id", "child_policy_id"])
def test_v10_rejects_orphan_lineage_endpoint(column: str) -> None:
    connection = _v9()
    _policy(connection, "record-a", "policy-a", "a-v1")
    values = {"parent_policy_id": "policy-a", "child_policy_id": "policy-a"}
    values[column] = "missing"
    connection.execute(
        "INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) VALUES(?,?,?)",
        (values["parent_policy_id"], values["child_policy_id"], "now"),
    )
    connection.commit()
    report = Migrator(connection).apply(10)
    assert not report.success and report.errors == ["POLICY_LINEAGE_ORPHAN"]
    assert Migrator(connection).current_version() == 9


def test_v10_rejects_rebuild_relevant_schema_drift() -> None:
    connection = _v9()
    connection.execute("CREATE INDEX unexpected_policy_index ON data_policies(policy_id)")
    connection.commit()
    report = Migrator(connection).apply(10)
    assert not report.success and report.errors == ["V10 exact V9 rebuild-object mismatch"]
    assert Migrator(connection).current_version() == 9


def test_v10_enforces_registry_pair_and_lineage_fks() -> None:
    connection = _v9()
    _policy(connection, "record-a", "policy-a", "a-v1")
    _policy(connection, "record-b", "policy-b", "b-v1")
    connection.commit()
    assert Migrator(connection).apply(10).success
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO data_policies(record_id,policy_id,version_id,target_record_id,tx_from,is_active,created_at) VALUES('record-b','policy-a','bad','target', 'now',0,'now')"
        )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO policy_lineage(parent_policy_id,child_policy_id,created_at) VALUES('missing','policy-a','now')")


def test_v10_versioned_archive_is_exact_and_restores_policy_identity_graph() -> None:
    connection = _v9()
    _policy(connection, "record-a", "policy-a", "a-v1")
    connection.execute("UPDATE data_policies SET is_active=0 WHERE record_id='record-a'")
    _policy(connection, "record-a", "policy-a", "a-v2")
    _policy(connection, "record-b", "policy-b", "b-v1")
    connection.execute("INSERT INTO policy_lineage VALUES('policy-a','policy-b','now')")
    connection.commit()
    assert Migrator(connection).apply(10).success
    package = create_versioned_package(connection)
    assert package["format_version"] == 3
    assert package["schema_version"] == 10
    assert package["inventory"].count("policy_identities") == 1
    assert verify_versioned_package(package)
    restored = sqlite3.connect(":memory:")
    restore_versioned_package(package, restored)
    assert restored.execute("PRAGMA foreign_key_check").fetchall() == []
    assert restored.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    assert restored.execute("SELECT policy_id,record_id FROM policy_identities ORDER BY policy_id").fetchall() == [
        ("policy-a", "record-a"), ("policy-b", "record-b")
    ]
    assert restored.execute("SELECT parent_policy_id,child_policy_id FROM policy_lineage").fetchall() == [("policy-a", "policy-b")]


def test_v10_versioned_archive_rejects_missing_or_extra_inventory() -> None:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(10).success
    package = create_versioned_package(connection)
    package["inventory"].remove("policy_identities")
    assert not verify_versioned_package(package)
    with pytest.raises(VersionedPackageError):
        restore_versioned_package(package, sqlite3.connect(":memory:"))
