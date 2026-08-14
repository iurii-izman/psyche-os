"""V5 additive migration and logical-portability evidence for E08."""

from __future__ import annotations

import sqlite3

from psyche_os.adapters.e08_filesystem import FilesystemQuarantine
from psyche_os.application.e08_imports import E08CanonicalStore, E08ImportService
from psyche_os.backup_export.versioned import (
    create_versioned_package,
    restore_versioned_package,
    verify_versioned_package,
)
from psyche_os.storage.e03_schema import V1_INVENTORY, V2_INVENTORY, inventory_for_schema
from psyche_os.storage.e05_schema import V3_INVENTORY
from psyche_os.storage.e06_schema import V4_INVENTORY
from psyche_os.storage.e08_schema import V5_INVENTORY, V5_MIGRATION_CHECKSUM
from psyche_os.storage.migrations import MIGRATIONS, Migrator


def test_v5_is_exactly_additive_and_preserves_frozen_history() -> None:
    assert V5_INVENTORY[: len(V4_INVENTORY)] == V4_INVENTORY
    assert V5_INVENTORY[len(V4_INVENTORY) :] == (
        "e08_quarantine_objects",
        "e08_import_sources",
        "e08_import_nodes",
    )
    assert inventory_for_schema(1) == V1_INVENTORY
    assert inventory_for_schema(2) == V2_INVENTORY
    assert inventory_for_schema(3) == V3_INVENTORY
    assert inventory_for_schema(4) == V4_INVENTORY
    assert inventory_for_schema(5) == V5_INVENTORY
    assert MIGRATIONS[5].checksum == V5_MIGRATION_CHECKSUM
    assert len(V5_MIGRATION_CHECKSUM) == 64


def test_fresh_v5_noop_rerun_and_v4_upgrade_requires_recovery_evidence() -> None:
    fresh = sqlite3.connect(":memory:")
    report = Migrator(fresh).apply(5)
    assert report.success and report.applied == [1, 2, 3, 4, 5]
    assert Migrator(fresh).apply(5).success
    assert {row[0] for row in fresh.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )} == set(V5_INVENTORY)

    old = sqlite3.connect(":memory:")
    assert Migrator(old).apply(4).success
    blocked = Migrator(old).apply(5)
    assert not blocked.success and "Verified V4 backup and export" in blocked.errors[0]
    upgraded = Migrator(old).apply(5, backup_verified=True, export_verified=True)
    assert upgraded.success and upgraded.applied == [5]


def test_v4_and_v5_logical_packages_remain_portable() -> None:
    for version in (4, 5):
        source = sqlite3.connect(":memory:")
        assert Migrator(source).apply(version).success
        package = create_versioned_package(source)
        assert package["schema_version"] == version
        assert verify_versioned_package(package)
        restored = sqlite3.connect(":memory:")
        restore_versioned_package(package, restored)
        assert create_versioned_package(restored)["package_checksum"] == package["package_checksum"]


def test_v5_portability_restores_governed_quarantine_bytes(tmp_path) -> None:  # type: ignore[no-untyped-def]
    store = E08CanonicalStore.for_test()
    instance = E08ImportService(
        FilesystemQuarantine(digest_key=b"migration-vault-fingerprint-key-01"[:32]),
        store=store,
    )
    path = tmp_path / "portable.txt"
    path.write_text("portable synthetic source", encoding="utf-8")
    candidate = instance.parse(instance.intake(str(path)).quarantine_id)
    preview = instance.preview(candidate)
    result = instance.commit(
        candidate, preview, instance.issue_consent(candidate, preview, approved=True)
    )
    package = create_versioned_package(store.connection)
    restored = sqlite3.connect(":memory:")
    restore_versioned_package(package, restored)
    reopened = E08CanonicalStore(restored)
    assert reopened.sources[result.source_version_id].original_bytes == path.read_bytes()
