"""Additive E05 V2-to-V3 migration and portability proofs."""

import copy
import sqlite3

from psyche_os.backup_export.versioned import (
    create_versioned_package,
    restore_versioned_package,
    verify_versioned_package,
)
from psyche_os.storage.e03_schema import V1_INVENTORY, V2_INVENTORY, V2_MIGRATION_CHECKSUM
from psyche_os.storage.e05_schema import V3_INVENTORY, V3_MIGRATION_CHECKSUM
from psyche_os.storage.migrations import MIGRATIONS, Migration, Migrator


def v2() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(2).success
    return connection


def test_e05_migration_checksum_and_exact_additive_inventory_are_frozen() -> None:
    assert len(V1_INVENTORY) == 20 and len(V2_INVENTORY) == 35 and len(V3_INVENTORY) == 39
    assert V3_INVENTORY[:35] == V2_INVENTORY
    assert MIGRATIONS[2].checksum == V2_MIGRATION_CHECKSUM
    assert (
        V3_MIGRATION_CHECKSUM == "fe0bc5ea00687169b36a1cbdcbde866ef6ad47cb01a01095b52a1f26b730c8d3"
    )


def test_established_v2_requires_proofs_then_migrates_once_and_rerun_is_noop() -> None:
    connection = v2()
    blocked = Migrator(connection).apply(3)
    assert not blocked.success and "backup and export" in blocked.errors[0]
    report = Migrator(connection).apply(3, backup_verified=True, export_verified=True)
    assert report.success and report.applied == [3]
    assert {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    } == set(V3_INVENTORY)
    rerun = Migrator(connection).apply(3)
    assert rerun.success and rerun.applied == []
    assert (
        connection.execute("SELECT checksum FROM schema_migrations WHERE version=2").fetchone()[0]
        == V2_MIGRATION_CHECKSUM
    )


def test_v3_interruption_rolls_back_to_exact_v2() -> None:
    connection = v2()
    original = MIGRATIONS[3]
    try:
        MIGRATIONS[3] = Migration(
            3,
            original.label,
            [original.statements[0], "CREATE TABLE interrupted_e05(x INTEGER);", "INVALID SQL;"],
        )
        report = Migrator(connection).apply(3, backup_verified=True, export_verified=True)
        assert not report.success
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 2
        assert {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        } == set(V2_INVENTORY)
    finally:
        MIGRATIONS[3] = original


def test_v1_v2_v3_logical_portability_remains_versioned() -> None:
    for version, inventory in ((1, V1_INVENTORY), (2, V2_INVENTORY), (3, V3_INVENTORY)):
        source = sqlite3.connect(":memory:")
        assert Migrator(source).apply(version).success
        package = create_versioned_package(source)
        assert package["inventory"] == list(inventory) and verify_versioned_package(package)
        restored = sqlite3.connect(":memory:")
        restore_versioned_package(package, restored)
        assert create_versioned_package(restored)["package_checksum"] == package["package_checksum"]
    tampered = copy.deepcopy(package)
    tampered["inventory"].append("opaque_future_table")
    assert verify_versioned_package(tampered) is False
