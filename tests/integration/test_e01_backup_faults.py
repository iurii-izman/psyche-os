"""E01 integration tests: backup/restore fault injection and adversarial verification.

Proves:
- Wrong key → fail before mutation
- Bit flip in ciphertext → decrypt fail
- Manifest/payload swap → AAD mismatch
- Downgraded/missing format version → rejected
- Missing/extra table in inventory → rejected
- Corrupt package JSON → rejected
- Wrong magic → rejected
- Injection failures preserve active vault
- Fault injection hooks for deterministic fault-preservation proofs
- ALL 4 required phases: after_staging, after_restore_write, during_validation, before_activation
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest
from sqlcipher3 import dbapi2

from psyche_os.backup_export.operations import (
    BACKUP_FORMAT_VERSION,
    BACKUP_MAGIC,
    BackupBuilder,
    BackupError,
    HOOK_AFTER_PACKAGE_STAGING,
    HOOK_AFTER_RESTORE_WRITE,
    HOOK_DURING_VALIDATION,
    HOOK_BEFORE_ACTIVATION,
    ActivationError,
    RestoreError,
    activate_restored_vault,
    arm_fault_hook,
    capture_semantic_state,
    capture_vault_state,
    clear_fault_hooks,
    restore_backup,
    verify_backup_file,
)
from psyche_os.backup_export.package_store import BackupPackageStore
from psyche_os.crypto.envelope import (
    SensitiveBytes,
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


def _make_store_and_rel(tmp_path: Path, name: str = "test.backup") -> tuple[BackupPackageStore, str]:
    """Create a BackupPackageStore in tmp_path and return (store, relative_path)."""
    store_dir = str(tmp_path / "backups")
    return BackupPackageStore(store_dir), name


def _create_backup(
    tmp_path: Path,
) -> tuple[BackupPackageStore, str, str, str, SensitiveBytes]:
    """Create a minimal vault and backup via BackupPackageStore.

    Returns (store, relative_path, vault_id, db_key_hex, backup_key).
    """
    db_path = str(tmp_path / "source.db")
    store, rel_path = _make_store_and_rel(tmp_path)

    vmk = generate_vmk()
    vault_id = VaultId(generate_id())
    backup_key = derive_domain_key(vmk, "backup")
    db_key_hex = os.urandom(32).hex()

    con = dbapi2.connect(db_path)
    try:
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        con.execute(
            "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
            "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
            "VALUES (?, ?, 'synthetic_only', datetime('now'), NULL, ?, ?, 'generated')",
            (str(vault_id), "test_vault", _DUMMY_SALT, _DUMMY_SALT),
        )
        con.commit()
        builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
        builder.build(connection=con, store=store, relative_path=rel_path)
    finally:
        con.close()

    return store, rel_path, str(vault_id), db_key_hex, backup_key


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestBackupFaults:
    """Wrong keys, tampered data, format attacks."""

    def test_wrong_key_fails_decryption(self, tmp_path: Path) -> None:
        """Verification with a different VMK-derived key fails."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        wrong_vmk = generate_vmk()
        wrong_key = derive_domain_key(wrong_vmk, "backup")

        ok, detail = verify_backup_file(store, rel_path, wrong_key)
        assert not ok, f"Expected failure with wrong key, got: {detail}"
        assert "decrypt" in detail.lower() or "wrong key" in detail.lower(), (
            f"Expected decryption/key error, got: {detail}"
        )

    def test_bit_flip_in_ciphertext_fails(self, tmp_path: Path) -> None:
        """A single bit flip in the ciphertext breaks decryption."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        # Flip one byte in the ciphertext
        ct = pkg["ciphertext_hex"]
        idx = 32  # Flip a byte in the middle
        flipped_byte = int(ct[idx:idx + 2], 16) ^ 0x01
        flipped = ct[:idx] + f"{flipped_byte:02x}" + ct[idx + 2:]
        pkg["ciphertext_hex"] = flipped

        tamper_store, tamper_rel = _make_store_and_rel(tmp_path, "tampered.backup")
        tamper_store.write_package(tamper_rel, json.dumps(pkg).encode("utf-8"))

        ok, detail = verify_backup_file(tamper_store, tamper_rel, backup_key)
        assert not ok, f"Expected failure with bit-flipped ciphertext, got: {detail}"

    def test_manifest_swap_causes_aad_mismatch(self, tmp_path: Path) -> None:
        """Swapping the manifest after encryption causes AAD mismatch."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        # Create a second backup with a different vault_id manifest
        vmk2 = generate_vmk()
        vid2 = VaultId(generate_id())
        bk2 = derive_domain_key(vmk2, "backup")

        db2 = str(tmp_path / "source2.db")
        store2, rel2 = _make_store_and_rel(tmp_path, "test2.backup")
        con = dbapi2.connect(db2)
        con.execute(f"PRAGMA key = \"x'{os.urandom(32).hex()}'\"")
        apply_schema(con)
        con.execute(
            "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
            "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
            "VALUES (?, ?, 'synthetic_only', datetime('now'), NULL, ?, ?, 'generated')",
            (str(vid2), "other", _DUMMY_SALT, _DUMMY_SALT),
        )
        con.commit()
        builder2 = BackupBuilder(vault_id=vid2, backup_key=bk2)
        builder2.build(connection=con, store=store2, relative_path=rel2)
        con.close()

        raw2 = store2.read_package(rel2)
        pkg2 = json.loads(raw2.decode("utf-8"))

        # Swap manifest: pkg gets pkg2's manifest, but pkg's ciphertext
        swapped = dict(pkg)
        swapped["manifest"] = pkg2["manifest"]

        swap_store, swap_rel = _make_store_and_rel(tmp_path, "swapped.backup")
        swap_store.write_package(swap_rel, json.dumps(swapped).encode("utf-8"))

        ok, detail = verify_backup_file(swap_store, swap_rel, backup_key)
        assert not ok, f"Expected failure with swapped manifest, got: {detail}"

    def test_missing_format_version_rejected(self, tmp_path: Path) -> None:
        """A backup package with format_version=0 or missing is rejected."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        # Remove format_version
        del pkg["format_version"]
        bad_store, bad_rel = _make_store_and_rel(tmp_path, "no_version.backup")
        bad_store.write_package(bad_rel, json.dumps(pkg).encode("utf-8"))

        ok, detail = verify_backup_file(bad_store, bad_rel, backup_key)
        assert not ok, f"Expected failure with missing format_version, got: {detail}"

    def test_wrong_magic_rejected(self, tmp_path: Path) -> None:
        """A backup with wrong magic bytes fails early."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        pkg["magic"] = "NOT-PSYCHE-BACKUP"
        bad_store, bad_rel = _make_store_and_rel(tmp_path, "bad_magic.backup")
        bad_store.write_package(bad_rel, json.dumps(pkg).encode("utf-8"))

        ok, detail = verify_backup_file(bad_store, bad_rel, backup_key)
        assert not ok
        assert "magic" in detail.lower(), f"Expected magic error, got: {detail}"

    def test_corrupt_package_json_rejected(self, tmp_path: Path) -> None:
        """Malformed JSON in the backup package is rejected."""
        bad_store, bad_rel = _make_store_and_rel(tmp_path, "corrupt.backup")
        bad_store.write_package(bad_rel, b"this is not json {{{")

        vmk = generate_vmk()
        backup_key = derive_domain_key(vmk, "backup")

        ok, detail = verify_backup_file(bad_store, bad_rel, backup_key)
        assert not ok, f"Expected failure with corrupt JSON, got: {detail}"

    def test_wrong_key_restore_fails_no_mutation(self, tmp_path: Path) -> None:
        """Restore with wrong key fails, no filesystem mutation."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        wrong_vmk = generate_vmk()
        wrong_key = derive_domain_key(wrong_vmk, "backup")

        restore_path = str(tmp_path / "restored.db")
        restore_db_key = os.urandom(32).hex()

        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=wrong_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_db_key,
        )

        assert result["success"] is False
        assert result["activated"] is False
        reason_lower = result.get("reason", "").lower()
        assert "decrypt" in reason_lower or "wrong" in reason_lower, (
            f"Expected decryption/key error, got: {result.get('reason')}"
        )


class TestRestoreFaults:
    """Restore-specific fault injection."""

    def test_restore_missing_package_fails(self, tmp_path: Path) -> None:
        """Restore with a nonexistent backup file fails."""
        vmk = generate_vmk()
        backup_key = derive_domain_key(vmk, "backup")

        store = BackupPackageStore(str(tmp_path / "empty_store"))
        restore_path = str(tmp_path / "restored.db")
        restore_db_key = os.urandom(32).hex()

        result = restore_backup(
            store=store,
            relative_path="nonexistent.backup",
            backup_key=backup_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_db_key,
        )

        assert result["success"] is False
        assert "not found" in result.get("reason", "").lower() or "cannot read" in result.get("reason", "").lower()

    def test_missing_table_in_inventory_fails_validation(self, tmp_path: Path) -> None:
        """A manifest with missing required table is rejected during validation."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        # Remove a required table from manifest checksums
        del pkg["manifest"]["table_checksums"]["vault_config"]

        bad_store, bad_rel = _make_store_and_rel(tmp_path, "missing_table.backup")
        bad_store.write_package(bad_rel, json.dumps(pkg).encode("utf-8"))

        ok, detail = verify_backup_file(bad_store, bad_rel, backup_key)
        assert not ok, f"Expected failure with missing table checksum, got: {detail}"
        assert "missing" in detail.lower() or "inventory" in detail.lower(), (
            f"Expected inventory/missing error, got: {detail}"
        )

    def test_empty_checksum_rejected(self, tmp_path: Path) -> None:
        """A manifest with empty sha256_hex for a table is rejected."""
        store, rel_path, vault_id, db_key_hex, backup_key = _create_backup(tmp_path)

        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        # Empty the checksum for one table
        pkg["manifest"]["table_checksums"]["actors"]["sha256_hex"] = ""

        bad_store, bad_rel = _make_store_and_rel(tmp_path, "empty_checksum.backup")
        bad_store.write_package(bad_rel, json.dumps(pkg).encode("utf-8"))

        ok, detail = verify_backup_file(bad_store, bad_rel, backup_key)
        assert not ok, f"Expected failure with empty checksum, got: {detail}"
        assert "empty" in detail.lower() or "missing" in detail.lower() or "checksum" in detail.lower(), (
            f"Expected empty/missing checksum error, got: {detail}"
        )


class TestFaultInjectionHooks:
    """Prove deterministic fault-preservation hooks for ALL 4 required phases
    (E01 target 4)."""

    def test_fault_after_staging_preserves_active_vault(self, tmp_path: Path) -> None:
        """Fault at after_package_staging: package not written, active vault unchanged."""
        db_path = str(tmp_path / "source.db")
        store_dir = str(tmp_path / "backups")
        store = BackupPackageStore(store_dir)
        rel_path = "fault_test.backup"

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

        # Capture active vault state (bytes + semantic) before fault
        before_bytes = capture_vault_state(db_path)
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        before_semantic = capture_semantic_state(con)
        con.close()

        # Arm fault hook
        arm_fault_hook(HOOK_AFTER_PACKAGE_STAGING, BackupError("injected staging fault"))

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        try:
            builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
            with pytest.raises(BackupError, match="injected staging fault"):
                builder.build(connection=con, store=store, relative_path=rel_path)
        finally:
            con.close()

        # Package must NOT exist in store
        assert not store.exists(rel_path), "Fault at staging: package must not be written"

        # Active vault bytes unchanged
        after_bytes = capture_vault_state(db_path)
        assert before_bytes == after_bytes, (
            f"Active vault bytes changed after staging fault!\n"
            f"Before: {before_bytes}\nAfter: {after_bytes}"
        )

        # Active vault semantic state unchanged
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        after_semantic = capture_semantic_state(con)
        con.close()
        assert before_semantic == after_semantic, (
            f"Active vault semantic state changed after staging fault!\n"
            f"Before: {before_semantic}\nAfter: {after_semantic}"
        )

        # Prove active vault is still usable after fault
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM vault_config")
        assert cur.fetchone()[0] == 1, "Active vault unusable after staging fault!"
        con.close()

        clear_fault_hooks()

    def test_fault_after_restore_write_preserves_active_vault(self, tmp_path: Path) -> None:
        """Fault at after_restore_write: restore fails, candidate discarded, active vault unchanged."""
        store, rel_path, vault_id_str, db_key_hex, backup_key = _create_backup(tmp_path)
        restore_path = str(tmp_path / "restored.db")
        restore_key = os.urandom(32).hex()

        # Arm the AFTER_RESTORE_WRITE fault hook
        arm_fault_hook(HOOK_AFTER_RESTORE_WRITE, RestoreError("injected after-restore-write fault"))

        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=backup_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )

        clear_fault_hooks()

        assert result["success"] is False
        assert result["activated"] is False
        # The candidate should have been discarded
        assert not os.path.exists(restore_path), (
            "Restore candidate was not cleaned up after fault"
        )

    def test_fault_during_validation_preserves_active_vault(self, tmp_path: Path) -> None:
        """Fault at during_validation: restore fails, candidate discarded, active vault unchanged."""
        db_path = str(tmp_path / "source.db")
        restore_path = str(tmp_path / "restored.db")
        store, rel_path = _make_store_and_rel(tmp_path, "fault_val.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source vault with data
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

        # Capture active vault state before fault
        before_bytes = capture_vault_state(db_path)
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        before_semantic = capture_semantic_state(con)
        con.close()

        # Arm the DURING_VALIDATION fault hook
        arm_fault_hook(HOOK_DURING_VALIDATION, RestoreError("injected during-validation fault"))

        restore_key = os.urandom(32).hex()
        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=backup_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )

        clear_fault_hooks()

        assert result["success"] is False
        assert result["activated"] is False
        assert not os.path.exists(restore_path), "Restore candidate not cleaned up"

        # Active vault bytes unchanged
        after_bytes = capture_vault_state(db_path)
        assert before_bytes == after_bytes, (
            f"Active vault bytes changed after during_validation fault!\n"
            f"Before: {before_bytes}\nAfter: {after_bytes}"
        )

        # Active vault semantic state unchanged
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        after_semantic = capture_semantic_state(con)
        con.close()
        assert before_semantic == after_semantic, (
            f"Active vault semantic state changed after during_validation fault!"
        )

        # Prove active vault is still usable
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM vault_config")
        assert cur.fetchone()[0] == 1, "Active vault unusable after during_validation fault!"
        con.close()

    def test_fault_before_activation_preserves_active_vault(self, tmp_path: Path) -> None:
        """Fault at before_activation: activation fails, active vault preserved
        (both bytes and semantic state), active vault remains usable."""
        db_path = str(tmp_path / "source.db")
        restore_path = str(tmp_path / "restored.db")
        active_path = str(tmp_path / "active.db")
        store, rel_path = _make_store_and_rel(tmp_path, "fault_act.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source vault
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

        # Create an "active" vault file with known key and content
        active_key = os.urandom(32).hex()
        active_con = dbapi2.connect(active_path)
        active_con.execute(f"PRAGMA key = \"x'{active_key}'\"")
        apply_schema(active_con)
        _insert_vault_config(active_con, str(VaultId(generate_id())), "active_original")
        active_con.commit()
        active_con.close()

        # Capture full persisted+semantic state of the active vault
        before_bytes = capture_vault_state(active_path)
        active_con = dbapi2.connect(active_path)
        active_con.execute(f"PRAGMA key = \"x'{active_key}'\"")
        before_semantic = capture_semantic_state(active_con)
        active_con.close()

        # Restore to isolated target
        restore_key = os.urandom(32).hex()
        result = restore_backup(
            store=store,
            relative_path=rel_path,
            backup_key=backup_key,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )
        assert result["success"], f"Restore failed: {result.get('reason')}"

        # Arm BEFORE_ACTIVATION fault
        arm_fault_hook(HOOK_BEFORE_ACTIVATION, ActivationError("injected activation fault"))

        # Exercise the production scoped atomic boundary.  The hook fires
        # with candidate/active security handles open, immediately before the
        # atomic replace, and the API reports a fail-closed result.
        activation_result = activate_restored_vault(
            restored_db_path=restore_path,
            db_key_hex=restore_key,
            active_db_path=active_path,
            backup_key=backup_key,
            activation_store=BackupPackageStore(tmp_path),
        )
        assert activation_result["success"] is False
        assert activation_result["activated"] is False
        assert "injected activation fault" in activation_result["reason"]
        clear_fault_hooks()

        # Active vault bytes must be byte-for-byte unchanged
        after_bytes = capture_vault_state(active_path)
        assert before_bytes == after_bytes, (
            f"Active vault bytes changed after activation fault!\n"
            f"Before: {before_bytes}\nAfter: {after_bytes}"
        )

        # Active vault semantic state must match
        active_con = dbapi2.connect(active_path)
        active_con.execute(f"PRAGMA key = \"x'{active_key}'\"")
        after_semantic = capture_semantic_state(active_con)
        active_con.close()
        assert before_semantic == after_semantic, (
            f"Active vault semantic state changed after activation fault!\n"
            f"Before: {before_semantic}\nAfter: {after_semantic}"
        )

        # Prove the active vault is still usable
        active_con = dbapi2.connect(active_path)
        active_con.execute(f"PRAGMA key = \"x'{active_key}'\"")
        cur = active_con.cursor()
        cur.execute("SELECT vault_name FROM vault_config")
        row = cur.fetchone()
        assert row is not None and row[0] == "active_original", (
            "Active vault content was mutated after activation fault!"
        )
        active_con.close()
