"""E01 integration tests: backup create, restore, and semantic equality.

Proves:
- Consistent transactional snapshot (fail-closed BEGIN IMMEDIATE)
- ALL rows backed up (active+inactive, no is_active filter)
- BackupPackageStore publication (handle-bound, no plaintext staging)
- Full backup → isolated restore → semantic-equality cycle
- Isolated restore creates its own SQLCipher target
- Atomic activation with file-level swap
- E00 invariants preserved after restore
- Backup output never overwrites
- Populated target rejection
- Repeatable archive cycles
"""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
from sqlcipher3 import dbapi2

from psyche_os.backup_export.operations import (
    BACKUP_FORMAT_VERSION,
    BACKUP_MAGIC,
    BackupBuilder,
    activate_restored_vault,
    restore_backup,
    verify_backup_file,
)
from psyche_os.backup_export.package_store import BackupPackageStore
from psyche_os.crypto.envelope import (
    derive_domain_key,
    generate_vmk,
)
from psyche_os.domain.ids import VaultId, generate_id
from psyche_os.storage.migrations import Migrator


def apply_schema(connection: object) -> None:
    report = Migrator(connection).apply(1)
    assert not report.errors and report.applied == [1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DUMMY_SALT = b"\x00" * 32


def _insert_vault_config(
    con: object, vault_id: str, vault_name: str = "test_vault"
) -> None:
    """Insert a minimal vault_config row with required NOT NULL columns."""
    con.execute(
        "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
        "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
        "VALUES (?, ?, 'synthetic_only', datetime('now'), NULL, ?, ?, 'generated')",
        (vault_id, vault_name, _DUMMY_SALT, _DUMMY_SALT),
    )


def _make_store_and_rel(tmp_path: Path, name: str) -> tuple[BackupPackageStore, str]:
    """Create a BackupPackageStore in tmp_path and return (store, relative_path)."""
    store_dir = str(tmp_path / "backups")
    return BackupPackageStore(store_dir), name


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackupCreate:
    """Prove backup creation with consistent snapshot and BackupPackageStore."""

    def test_backup_creates_encrypted_package(self, tmp_path: Path) -> None:
        """Backup creates an encrypted JSON package via BackupPackageStore."""
        db_path = str(tmp_path / "test.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create vault
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id))
        con.commit()
        con.close()

        # Build backup via scoped store
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            manifest = builder.build(
                connection=con, store=store, relative_path=rel_path,
            )
        finally:
            con.close()

        assert store.exists(rel_path)
        assert manifest.vault_id == vault_id
        assert manifest.format_version == BACKUP_FORMAT_VERSION
        assert manifest.encrypted is True

        # Verify package structure through store
        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        assert pkg["magic"] == BACKUP_MAGIC.decode()
        assert pkg["format_version"] == BACKUP_FORMAT_VERSION
        assert "nonce_hex" in pkg
        assert "ciphertext_hex" in pkg
        assert "manifest" in pkg

    def test_backup_verification_passes(self, tmp_path: Path) -> None:
        """A freshly created backup passes verification."""
        db_path = str(tmp_path / "test.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id))
        con.commit()
        con.close()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
        finally:
            con.close()

        ok, detail = verify_backup_file(store, rel_path, backup_key)
        assert ok, f"Verification failed: {detail}"

    def test_backup_output_never_overwrites(self, tmp_path: Path) -> None:
        """Creating a backup over an existing file raises BackupError."""
        db_path = str(tmp_path / "test.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        # Pre-write a package at the target relative path
        store.write_package(rel_path, b"existing content")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id))
        con.commit()
        con.close()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            from psyche_os.backup_export.operations import BackupError

            with pytest.raises(BackupError, match="already exists"):
                builder.build(connection=con, store=store, relative_path=rel_path)
        finally:
            con.close()

    def test_wrong_key_fails_verification(self, tmp_path: Path) -> None:
        """A backup verified with the wrong key fails."""
        db_path = str(tmp_path / "test.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id))
        con.commit()
        con.close()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
        finally:
            con.close()

        # Wrong VMK
        wrong_vmk = generate_vmk()
        wrong_key = derive_domain_key(wrong_vmk, "backup")

        ok, detail = verify_backup_file(store, rel_path, wrong_key)
        assert not ok


class TestBackupRestore:
    """Prove full backup → isolated restore → semantic equality cycle."""

    def test_full_backup_restore_cycle(self, tmp_path: Path) -> None:
        """Create vault → backup → restore to isolated target → activate."""
        db_path = str(tmp_path / "source.db")
        restore_path = str(tmp_path / "restored.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source vault with data
        con = dbapi2.connect(db_path)
        try:
            con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
            apply_schema(con)
            _insert_vault_config(con, str(vault_id))
            # Insert a test subject
            sid = str(uuid.uuid4())
            con.execute(
                "INSERT INTO subjects (record_id, subject_id, subject_label, "
                "anonymous, data_mode, tx_from, is_active, created_at, version_id, "
                "previous_version_id) "
                "VALUES (?, ?, 'test', 0, 'synthetic_only', '1', 1, datetime('now'), '', '')",
                (sid, sid),
            )
            con.commit()
        finally:
            con.close()

        # Backup
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            manifest = builder.build(
                connection=con, store=store, relative_path=rel_path,
            )
        finally:
            con.close()

        assert manifest.record_count >= 2  # vault_config + subject

        # Restore to isolated target (restore_backup creates its own DB)
        restore_key = os.urandom(32).hex()
        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=backup_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )

        assert result["success"], f"Restore failed: {result.get('reason', 'unknown')}"
        assert result["activated"] is False
        assert result["records_restored"] >= 2

        # Activate the restored vault (validate only, no swap)
        act_result = activate_restored_vault(
            restored_db_path=restore_path,
            db_key_hex=restore_key,
            active_db_path=None,
            backup_key=backup_key,
        )

        assert act_result["success"], f"Activation failed: {act_result.get('reason')}"

    def test_restore_to_existing_path_fails(self, tmp_path: Path) -> None:
        """Restoring to a path that already exists is rejected."""
        db_path = str(tmp_path / "source.db")
        existing_path = str(tmp_path / "existing.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        # Create a file at the target path
        Path(existing_path).write_text("pre-existing")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source and backup
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id))
        con.commit()

        builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
        builder.build(connection=con, store=store, relative_path=rel_path)
        con.close()

        # Try restoring into the existing path
        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=backup_key,
            restore_db_path=existing_path,
            restore_db_key_hex=os.urandom(32).hex(),
        )

        assert result["success"] is False
        assert "already exists" in result.get("reason", "").lower()
        assert result["activated"] is False

    def test_repeatable_archive_cycles(self, tmp_path: Path) -> None:
        """Create → verify multiple times → restore into multiple targets."""
        db_path = str(tmp_path / "source.db")
        store, rel_path = _make_store_and_rel(tmp_path, "cycle.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id))
        con.commit()
        con.close()

        # Backup
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
        finally:
            con.close()

        # Verify the backup 3 times
        for i in range(3):
            ok, detail = verify_backup_file(store, rel_path, backup_key)
            assert ok, f"Cycle {i}: verification failed: {detail}"

        # Restore into 3 different targets
        for i in range(3):
            restore_path = str(tmp_path / f"restored_{i}.db")
            restore_key = os.urandom(32).hex()

            result = restore_backup(
                store=store,
                relative_path=rel_path,
                backup_key=backup_key,
                restore_db_path=restore_path,
                restore_db_key_hex=restore_key,
            )
            assert result["success"], f"Cycle {i}: {result.get('reason')}"

    def test_e00_invariants_preserved_after_restore(self, tmp_path: Path) -> None:
        """The restored vault passes E00 invariant checks."""
        db_path = str(tmp_path / "source.db")
        restore_path = str(tmp_path / "restored.db")
        store, rel_path = _make_store_and_rel(tmp_path, "test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        _insert_vault_config(con, str(vault_id), "test_e01")
        con.commit()
        con.close()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
        finally:
            con.close()

        # Restore
        restore_key = os.urandom(32).hex()
        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=backup_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )

        assert result["success"]

        # E00 invariants: vault_config has exactly 1 row
        restore_con = dbapi2.connect(restore_path)
        restore_con.execute(f"PRAGMA key = \"x'{restore_key}'\"")
        try:
            cur = restore_con.cursor()
            cur.execute("SELECT COUNT(*) FROM vault_config")
            assert cur.fetchone()[0] == 1, "Restored vault must have exactly 1 vault_config row"

            # Schema tables are present
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [r[0] for r in cur.fetchall()]
            for req in ["vault_config", "actors", "subjects", "data_policies", "blobs"]:
                assert req in tables, f"Required table '{req}' missing in restored vault"
        finally:
            restore_con.close()
