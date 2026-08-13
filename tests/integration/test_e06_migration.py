"""Additive E06 V3-to-V4 migration, portability, and deletion proofs."""

import copy
import sqlite3

from psyche_os.backup_export.versioned import (
    create_versioned_package,
    restore_versioned_package,
    verify_versioned_package,
)
from psyche_os.storage.e03_schema import V1_INVENTORY, V2_INVENTORY, V2_MIGRATION_CHECKSUM
from psyche_os.storage.e05_schema import V3_INVENTORY, V3_MIGRATION_CHECKSUM
from psyche_os.storage.e06_schema import V4_INVENTORY, V4_MIGRATION_CHECKSUM
from psyche_os.storage.migrations import MIGRATIONS, Migration, Migrator


def v3() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(3).success
    return connection


def test_v4_checksum_and_exact_additive_inventory_preserve_prior_history() -> None:
    assert tuple(map(len, (V1_INVENTORY, V2_INVENTORY, V3_INVENTORY, V4_INVENTORY))) == (
        20,
        35,
        39,
        43,
    )
    assert V4_INVENTORY[:39] == V3_INVENTORY
    assert MIGRATIONS[2].checksum == V2_MIGRATION_CHECKSUM
    assert MIGRATIONS[3].checksum == V3_MIGRATION_CHECKSUM
    assert MIGRATIONS[4].checksum == V4_MIGRATION_CHECKSUM
    assert (
        V4_MIGRATION_CHECKSUM == "31ecd16646aff211cfd991f30d9cbdf2f3b6010dc759fd4d7644ff90d63e9413"
    )


def test_established_v3_requires_proofs_migrates_once_and_rerun_is_verified_noop() -> None:
    connection = v3()
    blocked = Migrator(connection).apply(4)
    assert not blocked.success and "backup and export" in blocked.errors[0]
    report = Migrator(connection).apply(4, backup_verified=True, export_verified=True)
    assert report.success and report.applied == [4]
    tables = {
        row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert tables == set(V4_INVENTORY)
    rerun = Migrator(connection).apply(4)
    assert rerun.success and rerun.applied == [] and Migrator(connection).verify().success
    assert (
        connection.execute("SELECT checksum FROM schema_migrations WHERE version=3").fetchone()[0]
        == V3_MIGRATION_CHECKSUM
    )


def test_pending_deletion_blocks_v4() -> None:
    connection = v3()
    connection.execute(
        "INSERT INTO deletion_requests(request_id,reason,scope,target_ids,status,created_at) VALUES(?,?,?,?,?,?)",
        ("del-e06", "fixture deletion", "single_record", '["fixture"]', "pending", "2044-01-01"),
    )
    connection.commit()
    report = Migrator(connection).apply(4, backup_verified=True, export_verified=True)
    assert not report.success and "Pending deletion" in report.errors[0]


def test_v4_interruption_rolls_back_to_exact_v3() -> None:
    connection = v3()
    original = MIGRATIONS[4]
    try:
        MIGRATIONS[4] = Migration(
            4,
            original.label,
            [original.statements[0], "CREATE TABLE interrupted_e06(x INTEGER);", "INVALID SQL;"],
        )
        report = Migrator(connection).apply(4, backup_verified=True, export_verified=True)
        assert not report.success
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 3
        assert {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        } == set(V3_INVENTORY)
    finally:
        MIGRATIONS[4] = original


def test_v1_v2_v3_v4_logical_portability_remains_versioned() -> None:
    package = {}
    for version, inventory in (
        (1, V1_INVENTORY),
        (2, V2_INVENTORY),
        (3, V3_INVENTORY),
        (4, V4_INVENTORY),
    ):
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
