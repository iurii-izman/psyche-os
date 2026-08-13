"""Mandatory E03 V1->V2 migration and versioned portability proofs."""

import copy
import sqlite3

import pytest

from psyche_os.backup_export.versioned import create_versioned_export, create_versioned_package, restore_versioned_package, verify_versioned_package
from psyche_os.storage.e03_schema import V1_INVENTORY, V2_INVENTORY, V2_MIGRATION_CHECKSUM
from psyche_os.storage.migrations import MIGRATIONS, Migration, Migrator


def v1() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    report = Migrator(connection).apply(1)
    assert report.success
    return connection


def test_e03_migration_pristine_v1_to_exact_v2_and_verified_noop() -> None:
    """E03 migration: pristine V1 must become exact 35-table V2 once only."""
    connection = v1()
    assert {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} == set(V1_INVENTORY)
    report = Migrator(connection).apply(2)
    assert report.success and report.applied == [2]
    assert {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")} == set(V2_INVENTORY)
    rerun = Migrator(connection).apply(2)
    assert rerun.success and rerun.applied == []
    assert connection.execute("SELECT checksum FROM schema_migrations WHERE version=2").fetchone()[0] == V2_MIGRATION_CHECKSUM


def test_e03_migration_checksum_is_frozen() -> None:
    """E03 migration: bundled statements must match the reviewed checksum."""
    assert V2_MIGRATION_CHECKSUM == "8847dbb72271fa75e9f456502737ebcafe0027f6ac10bfd7ae3757f413e48bcf"


def test_e03_migration_preserves_ambiguous_legacy_enum_bytes() -> None:
    """E03 migration: causal/predictive and every V1 origin must not be reinterpreted."""
    connection = v1()
    connection.execute("INSERT INTO claims(record_id,claim_id,version_id,claim_type,claim_status,claim_origin,claim_body,tx_from,is_active,created_at) VALUES('legacy','legacy','legacy-v1','causal','supported','observation','legacy bytes','2040-01-01',1,'2040-01-01')")
    connection.commit()
    report = Migrator(connection).apply(2, backup_verified=True, export_verified=True)
    assert report.success
    row = connection.execute("SELECT claim_type,claim_status,claim_origin,claim_body,semantic_version FROM claims WHERE record_id='legacy'").fetchone()
    assert row == ("causal", "supported", "observation", "legacy bytes", 1)


def test_e03_migration_malformed_v1_and_missing_recovery_proofs_fail_closed() -> None:
    """E03 migration: out-of-domain V1 or missing backup/export proof must not write."""
    connection = v1()
    connection.execute("PRAGMA ignore_check_constraints=ON")
    connection.execute("INSERT INTO claims(record_id,claim_id,version_id,claim_type,claim_status,claim_origin,tx_from,is_active,created_at) VALUES('bad','bad','bad-v1','invented','proposed','observation','2040',1,'2040')")
    connection.commit()
    connection.execute("PRAGMA ignore_check_constraints=OFF")
    report = Migrator(connection).apply(2, backup_verified=True, export_verified=True)
    assert not report.success and "out-of-domain" in report.errors[0]
    assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 1

    valid = v1()
    valid.execute("INSERT INTO reports(record_id,report_id,version_id,tx_from,is_active,created_at) VALUES('r','r','rv1','2040',1,'2040')")
    valid.commit()
    blocked = Migrator(valid).apply(2)
    assert not blocked.success and "backup and export" in blocked.errors[0]


def test_e03_migration_interruption_rolls_back_schema_and_bookkeeping() -> None:
    """E03 migration: a mid-migration failure must restore exact V1 atomically."""
    connection = v1()
    original = MIGRATIONS[2]
    try:
        MIGRATIONS[2] = Migration(2, original.label, [*original.statements[:3], "CREATE TABLE interrupted(x INTEGER)", "INVALID SQL"])
        report = Migrator(connection).apply(2)
        assert not report.success
        assert connection.execute("SELECT MAX(version) FROM schema_migrations").fetchone()[0] == 1
        assert connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='interrupted'").fetchone()[0] == 0
        assert connection.execute("PRAGMA table_info(source_artifacts)").fetchall()[-1][1] == "closure_marker"
    finally:
        MIGRATIONS[2] = original


def test_e03_v1_and_v2_backup_restore_export_use_exact_versioned_inventory() -> None:
    """E03 migration: V1 reader and V2 package/export must round-trip exact inventories."""
    old = v1()
    old_package = create_versioned_package(old)
    assert old_package["inventory"] == list(V1_INVENTORY) and verify_versioned_package(old_package)
    old_restore = sqlite3.connect(":memory:")
    restore_versioned_package(old_package, old_restore)
    assert create_versioned_package(old_restore)["package_checksum"] == old_package["package_checksum"]

    current = sqlite3.connect(":memory:")
    assert Migrator(current).apply(2).success
    package = create_versioned_package(current)
    assert package["inventory"] == list(V2_INVENTORY) and verify_versioned_package(package)
    restored = sqlite3.connect(":memory:")
    restore_versioned_package(package, restored)
    assert create_versioned_package(restored)["package_checksum"] == package["package_checksum"]
    exported = create_versioned_export(current)
    assert exported["schema_version"] == 2 and set(exported["schemas"]) == set(V2_INVENTORY)


@pytest.mark.parametrize("mutation", ["missing", "extra", "duplicate", "checksum"])
def test_e03_v2_package_rejects_inventory_and_checksum_tampering(mutation: str) -> None:
    """E03 migration: missing/extra/duplicate/checksum package ambiguity must fail."""
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(2).success
    package = copy.deepcopy(create_versioned_package(connection))
    if mutation == "missing": package["inventory"].pop()
    elif mutation == "extra": package["inventory"].append("future_table")
    elif mutation == "duplicate": package["inventory"].append(package["inventory"][0])
    else: package["checksums"]["claims"] = "0" * 64
    assert verify_versioned_package(package) is False


def test_e03_migration_temporal_constraints_reject_invalid_bounds() -> None:
    """E03-T2 migration invariant: invalid instant/unknown bounds must fail."""
    connection = sqlite3.connect(":memory:")
    assert Migrator(connection).apply(2).success
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute("INSERT INTO temporal_assertions(record_id,version_id,schema_version,tx_from,is_active,change_reason_code,created_by_actor_id,target_record_id,target_version_id,temporal_role,value_kind,lower_value,upper_value,precision,original_literal,timezone_known,certainty_class,certainty_rationale) VALUES('t','tv',2,'2040',1,'initial','a','r','rv','occurred','unknown','2040',NULL,'unknown','unknown',0,'unknown','invalid')")
