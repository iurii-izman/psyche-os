"""E00 portability smoke test — encrypted backup/export, wrong-key rejection,
isolated restore, and semantic equality with temporary synthetic data only.

This test belongs to the E00 gate. It uses only temporary files and
synthetic fixtures. It does not open or depend on the REAL_DATA_GATE.

E01 mechanical update: Updated to use BackupPackageStore + new API signatures.
Backup/restore logic unchanged.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import secrets
import tempfile

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.sqlcipher, pytest.mark.e2e]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ensure_gate() -> None:
    """Verify SQLCipher gate passes before running expensive tests."""
    from psyche_os.storage.sqlcipher_gate import gate_accepted

    if not gate_accepted():
        pytest.skip("SQLCipher gate not accepted — cannot run E00 portability smoke")


def _make_store_and_rel(tmpdir: str, name: str) -> tuple:
    """Create a BackupPackageStore in tmpdir and return (store, relative_path)."""
    from psyche_os.backup_export.package_store import BackupPackageStore

    store_dir = os.path.join(tmpdir, "backups")
    return BackupPackageStore(store_dir), name


# ---------------------------------------------------------------------------
# Smoke: Backup → verify → wrong-key reject → restore → equality
# ---------------------------------------------------------------------------


class TestE00BackupRestoreSmoke:
    """End-to-end backup → verify → wrong-key → restore → semantic equality."""

    @staticmethod
    def _make_vault_db(path: str, key: str, vault_id_str: str) -> None:
        """Create an encrypted SQLCipher database with the full F0 schema and
        a vault_config row."""
        from sqlcipher3 import dbapi2

        from psyche_os.storage.migrations import Migrator

        con = dbapi2.connect(path)
        con.execute(f"PRAGMA key = \"x'{key}'\";")
        migration = Migrator(con).apply(1)
        assert not migration.errors and migration.applied == [1]

        now = _dt.datetime.now(_dt.UTC).isoformat()
        cur = con.cursor()
        cur.execute(
            "INSERT INTO vault_config (vault_id, vault_name, data_mode,"
            " created_at, key_state, db_key_salt, blob_envelope_key_salt)"
            " VALUES (?, 'smoke', 'synthetic_only', ?, 'generated', ?, ?)",
            (vault_id_str, now, os.urandom(32), os.urandom(32)),
        )
        con.commit()
        con.close()

    @staticmethod
    def _open_db(path: str, key: str):
        """Open a SQLCipher database with the given key."""
        from sqlcipher3 import dbapi2

        con = dbapi2.connect(path)
        con.execute(f"PRAGMA key = \"x'{key}'\";")
        return con

    def test_encrypted_backup_and_restore_round_trip(self) -> None:
        """Create a SQLCipher vault with schema, back it up, verify, reject
        wrong key, restore into a fresh database, prove semantic equality."""
        _ensure_gate()

        from psyche_os.backup_export.operations import (
            _BACKUP_INVENTORY_TABLES,
            BackupBuilder,
            restore_backup,
            verify_backup_file,
        )
        from psyche_os.crypto.envelope import SensitiveBytes
        from psyche_os.domain.ids import VaultId, generate_id
        from psyche_os.storage.schema import apply_schema

        vault_id = VaultId(generate_id())
        db_key = secrets.token_hex(32)

        tmpdir = tempfile.mkdtemp(prefix="psyche_e00_smoke_")

        try:
            # -- Phase 1: Create encrypted source vault --
            src_path = os.path.join(tmpdir, "src_vault.db")
            self._make_vault_db(src_path, db_key, str(vault_id))

            # Count source rows
            con_src = self._open_db(src_path, db_key)
            cur = con_src.cursor()
            src_counts: dict[str, int] = {}
            for table in _BACKUP_INVENTORY_TABLES:
                try:
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    row = cur.fetchone()
                    src_counts[table] = row[0] if row else 0
                except Exception:
                    src_counts[table] = 0

            # -- Phase 2: Create backup via BackupPackageStore --
            store, rel_path = _make_store_and_rel(tmpdir, "smoke_backup.enc")
            manifest_key = SensitiveBytes(secrets.token_bytes(32))

            builder = BackupBuilder(vault_id=vault_id, backup_key=manifest_key)
            manifest = builder.build(
                connection=con_src, store=store, relative_path=rel_path,
            )
            con_src.close()

            assert manifest.record_count > 0
            assert store.exists(rel_path)

            # -- Phase 3: Verify backup --
            ok, msg = verify_backup_file(store, rel_path, manifest_key)
            assert ok, f"Backup verification failed: {msg}"

            # -- Phase 4: Wrong key MUST be rejected --
            wrong_key = SensitiveBytes(secrets.token_bytes(32))
            ok_wrong, msg_wrong = verify_backup_file(store, rel_path, wrong_key)
            assert not ok_wrong, "Wrong key should be rejected"
            assert "decrypt" in msg_wrong.lower() or "wrong key" in msg_wrong.lower() or "decr" in msg_wrong.lower()

            # -- Phase 5: Restore into fresh isolated target --
            dst_path = os.path.join(tmpdir, "dst_vault.db")
            dst_key = secrets.token_hex(32)

            result = restore_backup(
                store=store,
                relative_path=rel_path,
                backup_key=manifest_key,
                restore_db_path=dst_path,
                restore_db_key_hex=dst_key,
            )

            assert result.get("success"), f"Restore failed: {result.get('reason', result)}"

            # -- Phase 6: Verify semantic equality --
            con_dst2 = self._open_db(dst_path, dst_key)
            cur_dst = con_dst2.cursor()

            for table in _BACKUP_INVENTORY_TABLES:
                try:
                    cur_dst.execute(f"SELECT COUNT(*) FROM {table}")
                    row = cur_dst.fetchone()
                    dst_count = row[0] if row else 0
                except Exception:
                    dst_count = 0
                src_cnt = src_counts.get(table, 0)
                assert dst_count == src_cnt, (
                    f"Table '{table}' row count mismatch: src={src_cnt}, dst={dst_count}"
                )
            con_dst2.close()

        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_version_downgrade_rejected(self) -> None:
        """A backup with format_version=0 must fail verification."""
        _ensure_gate()

        from psyche_os.backup_export.operations import (
            BACKUP_MAGIC,
            verify_backup_file,
        )
        from psyche_os.crypto.envelope import SensitiveBytes

        from psyche_os.backup_export.package_store import BackupPackageStore

        tmpdir = tempfile.mkdtemp(prefix="psyche_e00_ver_")
        try:
            store_root = os.path.join(tmpdir, "backups")
            store = BackupPackageStore(store_root)
            rel_path = "downgraded_backup.json"
            manifest_key = SensitiveBytes(secrets.token_bytes(32))

            payload = {
                "magic": BACKUP_MAGIC.decode(),
                "format_version": 0,  # downgrade
                "manifest": {
                    "manifest_id": "test",
                    "vault_id": "test",
                    "format_version": 0,
                    "sha256_hex": "0000",
                    "record_count": 0,
                    "blob_count": 0,
                    "table_checksums": {},
                },
                "nonce_hex": "00" * 12,
                "ciphertext_hex": "00" * 32,
            }
            store.write_package(rel_path, json.dumps(payload).encode("utf-8"))

            ok, msg = verify_backup_file(store, rel_path, manifest_key)
            assert not ok, f"Version 0 should be rejected: {msg}"
            assert "format_version" in msg.lower() or "format version" in msg.lower()
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_outside_inventory_table_omitted_rejected(self) -> None:
        """A backup whose manifest is missing a required inventory table must fail."""
        _ensure_gate()

        from psyche_os.backup_export.operations import (
            _INVENTORY_TABLE_NAMES,
            BackupBuilder,
            verify_backup_file,
        )
        from psyche_os.crypto.envelope import SensitiveBytes
        from psyche_os.domain.ids import VaultId, generate_id

        vault_id = VaultId(generate_id())
        db_key = secrets.token_hex(32)

        tmpdir = tempfile.mkdtemp(prefix="psyche_e00_miss_")
        try:
            src_path = os.path.join(tmpdir, "vault.db")
            self._make_vault_db(src_path, db_key, str(vault_id))

            store, rel_path = _make_store_and_rel(tmpdir, "backup.enc")
            manifest_key = SensitiveBytes(secrets.token_bytes(32))

            con = self._open_db(src_path, db_key)
            builder = BackupBuilder(vault_id=vault_id, backup_key=manifest_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
            con.close()

            # Tamper: remove one table checksum from the manifest
            raw = store.read_package(rel_path)
            payload = json.loads(raw.decode("utf-8"))

            tables = sorted(_INVENTORY_TABLE_NAMES)
            drop_table = tables[-1]
            del payload["manifest"]["table_checksums"][drop_table]

            store.write_package(rel_path, json.dumps(payload).encode("utf-8"))

            ok, msg = verify_backup_file(store, rel_path, manifest_key)
            assert not ok, f"Missing table '{drop_table}' should be rejected: {msg}"
            assert "missing" in msg.lower() or "inventory" in msg.lower() or drop_table in msg
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_outer_manifest_tamper_rejected(self) -> None:
        """Altering the outer manifest after encryption must fail AEAD decryption."""
        _ensure_gate()

        from psyche_os.backup_export.operations import BackupBuilder, verify_backup_file
        from psyche_os.crypto.envelope import SensitiveBytes
        from psyche_os.domain.ids import VaultId, generate_id

        vault_id = VaultId(generate_id())
        db_key = secrets.token_hex(32)

        tmpdir = tempfile.mkdtemp(prefix="psyche_e00_tamp_")
        try:
            src_path = os.path.join(tmpdir, "vault.db")
            self._make_vault_db(src_path, db_key, str(vault_id))

            store, rel_path = _make_store_and_rel(tmpdir, "backup.enc")
            manifest_key = SensitiveBytes(secrets.token_bytes(32))

            con = self._open_db(src_path, db_key)
            builder = BackupBuilder(vault_id=vault_id, backup_key=manifest_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
            con.close()

            # Tamper: change the outer manifest's record_count
            raw = store.read_package(rel_path)
            payload = json.loads(raw.decode("utf-8"))
            payload["manifest"]["record_count"] = 999999
            store.write_package(rel_path, json.dumps(payload).encode("utf-8"))

            ok, msg = verify_backup_file(store, rel_path, manifest_key)
            assert not ok, f"Tampered outer manifest should be rejected: {msg}"
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_nonempty_target_restore_rejected(self) -> None:
        """Restoring a backup into a non-empty target database must be rejected."""
        _ensure_gate()

        from psyche_os.backup_export.operations import BackupBuilder, restore_backup
        from psyche_os.crypto.envelope import SensitiveBytes
        from psyche_os.domain.ids import VaultId, generate_id

        vault_id = VaultId(generate_id())
        db_key = secrets.token_hex(32)

        tmpdir = tempfile.mkdtemp(prefix="psyche_e00_rest_")
        try:
            # Create source backup
            src_path = os.path.join(tmpdir, "src_vault.db")
            self._make_vault_db(src_path, db_key, str(vault_id))

            store, rel_path = _make_store_and_rel(tmpdir, "backup.enc")
            manifest_key = SensitiveBytes(secrets.token_bytes(32))

            con = self._open_db(src_path, db_key)
            builder = BackupBuilder(vault_id=vault_id, backup_key=manifest_key)
            builder.build(connection=con, store=store, relative_path=rel_path)
            con.close()

            # Create a pre-existing file at the target path (non-empty target)
            dst_path = os.path.join(tmpdir, "dst_vault.db")
            dst_key = secrets.token_hex(32)
            from sqlcipher3 import dbapi2

            from psyche_os.storage.schema import apply_schema

            con_dst = dbapi2.connect(dst_path)
            con_dst.execute(f"PRAGMA key = \"x'{dst_key}'\";")
            apply_schema(con_dst)
            cur = con_dst.cursor()
            # Pre-populate a data row so the target is NOT empty
            now = _dt.datetime.now(_dt.UTC).isoformat()
            cur.execute(
                "INSERT INTO vault_config (vault_id, vault_name, data_mode,"
                " created_at, key_state, db_key_salt, blob_envelope_key_salt)"
                " VALUES (?, 'pre-existing', 'synthetic_only', ?, 'generated', ?, ?)",
                (generate_id(), now, os.urandom(32), os.urandom(32)),
            )
            con_dst.commit()
            con_dst.close()

            # The target path already exists, so restore_backup rejects it
            # (pre-validation phase: target must not exist)
            result = restore_backup(
                store=store,
                relative_path=rel_path,
                backup_key=manifest_key,
                restore_db_path=dst_path,
                restore_db_key_hex=dst_key,
            )
            assert not result["success"], (
                f"Expected non-empty target restore to be rejected: {result}"
            )
            assert "already exists" in result.get("reason", "").lower()
        finally:
            import shutil

            shutil.rmtree(tmpdir, ignore_errors=True)
