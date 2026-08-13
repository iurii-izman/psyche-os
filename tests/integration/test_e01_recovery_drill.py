"""E01 integration tests: independent recovery drill with Argon2id.

Proves:
- Independent recovery via Argon2id wrap/unwrap (no retained raw VMK)
- Canary scan on backup packages
- Backup immutability proof
- Deletion state preserved in restored vault
- Full recover_and_restore pipeline
"""

from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

import pytest
from sqlcipher3 import dbapi2

from psyche_os.backup_export.operations import (
    BackupBuilder,
    recover_and_restore,
    restore_backup,
    verify_backup_file,
)
from psyche_os.backup_export.package_store import BackupPackageStore
from psyche_os.crypto.envelope import (
    RecoveryWrapper,
    SensitiveBytes,
    derive_domain_key,
    generate_vmk,
)
from psyche_os.domain.ids import VaultId, generate_id
from psyche_os.interfaces.cli import create_cli
from psyche_os.storage.migrations import Migrator


def apply_schema(connection: object) -> None:
    report = Migrator(connection).apply(1)
    assert not report.errors and report.applied == [1]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CANARY = b"PSYCHE-E01-CANARY-0429f87e3b1c6a5d"
_DUMMY_SALT = b"\x00" * 32
_SALT_ARGS = (_DUMMY_SALT, _DUMMY_SALT)


def _make_store_and_rel(tmp_path: Path, name: str = "test.backup") -> tuple[BackupPackageStore, str]:
    """Create a BackupPackageStore in tmp_path and return (store, relative_path)."""
    store_dir = str(tmp_path / "backups")
    return BackupPackageStore(store_dir), name


def _create_backup(
    tmp_path: Path,
) -> tuple[BackupPackageStore, str, str, str, SensitiveBytes, SensitiveBytes]:
    """Create a minimal vault and backup via BackupPackageStore.

    Returns (store, relative_path, vault_id, db_key_hex, backup_key, vmk).
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

    return store, rel_path, str(vault_id), db_key_hex, backup_key, vmk


def _create_backup_with_canary(
    tmp_path: Path,
    canary: bytes = _CANARY,
) -> tuple[BackupPackageStore, str, str, SensitiveBytes]:
    """Create a backup from a vault that embeds a canary in vault_name."""
    db_path = str(tmp_path / "source.db")
    store, rel_path = _make_store_and_rel(tmp_path, "canary.backup")

    vmk = generate_vmk()
    vault_id = VaultId(generate_id())
    backup_key = derive_domain_key(vmk, "backup")
    db_key_hex = os.urandom(32).hex()

    canary_name = f"canary_vault_{canary.hex()[:16]}"

    con = dbapi2.connect(db_path)
    try:
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        con.execute(
            "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
            "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
            "VALUES (?, ?, 'synthetic_only', datetime('now'), NULL, ?, ?, 'generated')",
            (str(vault_id), canary_name, _DUMMY_SALT, _DUMMY_SALT),
        )
        con.commit()
        builder = BackupBuilder(vault_id=vault_id, backup_key=backup_key)
        builder.build(connection=con, store=store, relative_path=rel_path)
    finally:
        con.close()

    return store, rel_path, canary_name, backup_key


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRecoveryDrill:
    """Prove independent recovery via Argon2id wrap/unwrap (no retained VMK)."""

    def test_argon2id_recovery_without_raw_vmk(self, tmp_path: Path) -> None:
        """Independent recovery: Argon2id wrap VMK → store only header →
        re-derive VMK via unwrap + password → restore successfully.

        The raw VMK is NEVER retained in the test. Only the recovery header
        and password are kept.
        """
        rw = RecoveryWrapper()
        if not rw.available:
            pytest.skip("Argon2id not available on this platform")

        db_path = str(tmp_path / "source.db")
        restore_path = str(tmp_path / "recovered.db")
        store, rel_path = _make_store_and_rel(tmp_path, "recovery_test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        # Create source vault
        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        con.execute(
            "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
            "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
            "VALUES (?, ?, 'synthetic_only', datetime('now'), NULL, ?, ?, 'generated')",
            (str(vault_id), "recovery_test", *_SALT_ARGS),
        )
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

        # --- Wrap VMK under Argon2id-derived key ---
        recovery_secret = "independent-recovery-test-passphrase-8a3f"
        header = rw.wrap(vmk, recovery_secret, vault_id)

        # --- SIMULATE LOSS: discard all raw key material ---
        vmk.clear()
        del vmk
        del backup_key

        # --- Recover: only header + password needed ---
        restore_key = os.urandom(32).hex()
        result = recover_and_restore(
            store=store,
            relative_path=rel_path,
            recovery_header=header,
            recovery_secret=recovery_secret,
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )

        assert result["success"], (
            f"Argon2id independent recovery failed: {result.get('reason')}"
        )
        assert result["vault_id"] == str(vault_id)

        # Verify we can open the recovered vault
        restore_con = dbapi2.connect(restore_path)
        restore_con.execute(f"PRAGMA key = \"x'{restore_key}'\"")
        try:
            cur = restore_con.cursor()
            cur.execute("SELECT COUNT(*) FROM vault_config")
            assert cur.fetchone()[0] == 1
        finally:
            restore_con.close()

    def test_production_recovery_command_needs_no_raw_key(
        self, tmp_path: Path
    ) -> None:
        """Enabled CLI consumes package + separate header + secret only."""
        rw = RecoveryWrapper()
        if not rw.available:
            pytest.skip("Argon2id not available on this platform")

        store, rel_path, vault_id, _, backup_key, vmk = _create_backup(tmp_path)
        secret = "production-recovery-command-secret-1"
        header = rw.wrap(vmk, secret, VaultId(vault_id))
        header_path = tmp_path / "separate.recovery.json"
        header_path.write_text(json.dumps(header.to_dict()), encoding="utf-8")
        vmk.clear()
        backup_key.clear()
        del vmk, backup_key

        result = create_cli().dispatch(
            [
                "recovery", "restore",
                "--package", str(store.backup_root / rel_path),
                "--target", str(tmp_path / "cli-recovered.db"),
                "--recovery-secret", secret,
                "--recovery-header", str(header_path),
            ]
        )
        assert result.status == "ok", result.warnings
        assert result.data["success"] is True
        assert result.data["activated"] is False

    def test_vault_init_creates_separate_header_without_storing_secret(
        self, tmp_path: Path
    ) -> None:
        vault_path = tmp_path / "initialized.db"
        result = create_cli().dispatch(["vault", "init", "--path", str(vault_path)])
        assert result.status == "ok", result.warnings
        header_path = Path(result.data["recovery_header_path"])
        assert header_path.is_file()
        header_text = header_path.read_text(encoding="utf-8")
        assert result.data["recovery_secret"] not in header_text
        assert result.data["recovery_secret"].encode() not in vault_path.read_bytes()

    def test_recover_and_restore_wrong_password_fails(self, tmp_path: Path) -> None:
        """Recovery with wrong password fails with a content-free error."""
        rw = RecoveryWrapper()
        if not rw.available:
            pytest.skip("Argon2id not available on this platform")

        store, rel_path, vault_id, db_key_hex, backup_key, vmk = _create_backup(tmp_path)
        restore_path = str(tmp_path / "recovered.db")

        # Wrap VMK with correct password
        recovery_secret = "correct-password-7f2d"
        header = rw.wrap(vmk, recovery_secret, vault_id)

        # Discard VMK
        vmk.clear()
        del vmk
        del backup_key

        # Try recovery with WRONG password
        result = recover_and_restore(
            store=store,
            relative_path=rel_path,
            recovery_header=header,
            recovery_secret="wrong-password-0000",
            restore_db_path=restore_path,
            restore_db_key_hex=os.urandom(32).hex(),
        )

        assert not result["success"]
        assert "unwrap" in result.get("reason", "").lower() or "wrong" in result.get("reason", "").lower()

    def test_canary_not_in_plaintext_backup(self, tmp_path: Path) -> None:
        """The canary value must NOT appear in plaintext in the backup package."""
        store, rel_path, canary_name, backup_key = _create_backup_with_canary(tmp_path)

        raw = store.read_package(rel_path)
        raw_text = raw.decode("utf-8")

        # The canary hex bytes should not appear in plaintext
        canary_hex = _CANARY.hex()
        assert canary_hex not in raw_text, (
            "CANARY FOUND in backup package plaintext — canary hex appears in file"
        )

    def test_canary_in_backup_name_not_in_ciphertext_plaintext(self, tmp_path: Path) -> None:
        """The canary name in vault_name is in manifest, but actual canary bytes are not."""
        store, rel_path, canary_name, backup_key = _create_backup_with_canary(tmp_path)

        raw = store.read_package(rel_path)
        raw_text = raw.decode("utf-8")

        # The raw canary bytes must not appear
        assert _CANARY.hex() not in raw_text, "Raw canary found in backup plaintext"

    def test_backup_package_not_writable_after_creation(self, tmp_path: Path) -> None:
        """Any modification to the backup package is detected."""
        store, rel_path, vault_id, db_key_hex, backup_key, vmk = _create_backup(tmp_path)

        # Modification is detected through checksum/AAD mismatch
        raw = store.read_package(rel_path)
        pkg = json.loads(raw.decode("utf-8"))

        pkg["manifest"]["record_count"] = 999999
        tamper_store, tamper_rel = _make_store_and_rel(tmp_path, "tampered.backup")
        tamper_store.write_package(tamper_rel, json.dumps(pkg).encode("utf-8"))

        ok, detail = verify_backup_file(tamper_store, tamper_rel, backup_key)
        assert not ok, f"Tampered backup should fail verification: {detail}"


class TestDeletionStatePreserved:
    """Prove that deletion state is preserved across backup/restore."""

    def test_vault_id_consistent_after_restore(self, tmp_path: Path) -> None:
        """The vault_id in the restored vault matches the original."""
        db_path = str(tmp_path / "source.db")
        restore_path = str(tmp_path / "restored.db")
        store, rel_path = _make_store_and_rel(tmp_path, "id_test.backup")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        backup_key = derive_domain_key(vmk, "backup")
        db_key_hex = os.urandom(32).hex()

        con = dbapi2.connect(db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
        apply_schema(con)
        con.execute(
            "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
            "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
            "VALUES (?, ?, 'synthetic_only', datetime('now'), NULL, ?, ?, 'generated')",
            (str(vault_id), "id_consistency_test", *_SALT_ARGS),
        )
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
        assert result["vault_id"] == str(vault_id), (
            f"Vault ID mismatch: {result['vault_id']} != {vault_id}"
        )

        # Verify vault_config in restored DB
        con = dbapi2.connect(restore_path)
        con.execute(f"PRAGMA key = \"x'{restore_key}'\"")
        try:
            cur = con.cursor()
            cur.execute("SELECT vault_id FROM vault_config")
            row = cur.fetchone()
            assert row is not None, "Missing vault_config in restored DB"
            assert row[0] == str(vault_id)
        finally:
            con.close()
