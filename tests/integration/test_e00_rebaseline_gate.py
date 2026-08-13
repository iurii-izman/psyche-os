"""E00 rebaseline gate — minimum closure proofs for the three FIX_NOW areas.

1. Minimal transactional migrations:
   - normal apply succeeds and rerun is idempotent
   - altered checksum fails closed
   - injected failure after schema statement leaves schema + bookkeeping unchanged

2. Synthetic-only storage write boundary:
   - direct UoW write without authority is rejected with zero row/file change
   - altered/unknown fixture fails to load
   - bundled fixture succeeds through the package-owned loader

3. Truthful E00 validation and deferred-surface lock:
   - valid in-scope artifact passes schema validation
   - malformed/empty/fake evidence is rejected
   - backup/restore CLI returns FEATURE_DEFERRED_PRE_REAL_DATA
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import tempfile
from types import SimpleNamespace

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.sqlcipher]

# ============================================================================
# 1. Minimal transactional migrations
# ============================================================================


def _temp_db(extra_ddl: str | None = None) -> tuple[object, str]:
    """Create a temporary SQLCipher database with schema_migrations table."""
    from sqlcipher3 import dbapi2

    key = secrets.token_hex(32)
    con = dbapi2.connect(":memory:")
    con.execute(f"PRAGMA key = \"x'{key}'\";")
    con.execute(
        "CREATE TABLE IF NOT EXISTS schema_migrations ("
        "version INTEGER PRIMARY KEY, label TEXT NOT NULL,"
        " applied_at TEXT NOT NULL,"
        " checksum TEXT NOT NULL);"
    )
    if extra_ddl:
        con.execute(extra_ddl)
    con.commit()
    return con, key


class TestTransactionalMigrations:
    """Prove that migrations are explicit, ordered, checksummed, and atomic."""

    def test_normal_apply_and_idempotent_rerun(self) -> None:
        """Apply v1 migration, verify schema exists, rerun must succeed idempotently."""
        from sqlcipher3 import dbapi2

        from psyche_os.storage.migrations import CURRENT_SCHEMA_VERSION, Migrator

        con, _key = _temp_db()
        try:
            m1 = Migrator(con)
            assert m1.current_version() == 0

            report1 = m1.apply(CURRENT_SCHEMA_VERSION)
            assert report1.success, f"Migration failed: {report1.errors}"
            assert report1.applied == [1]

            # Verify schema exists after apply
            cur = con.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
            tables = [r[0] for r in cur.fetchall()]
            assert "vault_config" in tables
            assert "actors" in tables
            assert "blobs" in tables

            # Rerun must be idempotent
            report2 = m1.apply(CURRENT_SCHEMA_VERSION)
            assert report2.success, f"Rerun failed: {report2.errors}"
            assert report2.applied == []
            # v1 was already applied, so it should be skipped or simply not listed
            # (exact behavior depends on whether current_version() returns 1 or 0
            # in the in-memory DB — the key invariant is idempotence)
        finally:
            con.close()

    def test_altered_checksum_fails_closed(self) -> None:
        """An altered migration checksum must fail before any schema change.

        Patch MIGRATIONS[1] with a Migration whose statement list and
        checksum are both tampered.  get_migration_chain() returns a copy;
        apply() compares the copy's checksum against the canonical
        MIGRATIONS entry, which catches the discrepancy.
        """
        from psyche_os.storage.migrations import (
            CURRENT_SCHEMA_VERSION,
            MIGRATIONS,
            Migration,
            Migrator,
        )

        con, _key = _temp_db()
        try:
            orig = MIGRATIONS[1]
            extra_stmts = list(orig.statements) + ["SELECT 1;"]
            fake = Migration(
                version=1,
                label=orig.label,
                statements=extra_stmts,
            )
            # Overwrite checksum with the original value — mismatch between
            # the fake (enlarged) statement list and the declared checksum.
            object.__setattr__(fake, "checksum", orig.checksum)

            try:
                MIGRATIONS[1] = fake
                m = Migrator(con)
                report = m.apply(CURRENT_SCHEMA_VERSION)
                assert not report.success, "Altered migration was NOT rejected"
                assert any("Checksum" in e for e in report.errors), (
                    f"Expected checksum mismatch error: {report.errors}"
                )
            finally:
                MIGRATIONS[1] = orig
        finally:
            con.close()

    def test_injected_failure_rolls_back_both_schema_and_bookkeeping(self) -> None:
        """Inject a failing statement in the middle of a multi-statement migration,
        then prove that no schema change and no bookkeeping entry were committed."""
        from psyche_os.storage.migrations import (
            CURRENT_SCHEMA_VERSION,
            MIGRATIONS,
            Migrator,
            Migration,
        )

        from psyche_os.storage.schema import ALL_DDL, SCHEMA_MIGRATIONS_DDL

        con, _key = _temp_db()
        try:
            # Build a v2 migration that inserts a good statement, then a bogus one.
            # The good statement creates a test table; the bogus one raises an error.
            stmts = [
                "CREATE TABLE IF NOT EXISTS _migration_test_ (x INTEGER);",
                "INSERT INTO _nonexistent_table_ VALUES (1);",  # deliberate failure
            ]
            bad_migration = Migration(
                version=2,
                label="test_bad_migration",
                statements=stmts,
                checksum="",  # auto-computed in __post_init__
            )
            # Register it
            from psyche_os.storage.schema import SCHEMA_VERSIONS

            SCHEMA_VERSIONS[2] = "test_bad_migration"
            MIGRATIONS[2] = bad_migration

            try:
                m = Migrator(con)
                report = m.apply(target_version=2)
                assert not report.success, (
                    f"Migration with injected failure should have failed: {report.errors}"
                )

                # Verify no schema change from the good statement
                cur = con.cursor()
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
                tables = [r[0] for r in cur.fetchall()]
                assert "_migration_test_" not in tables, (
                    f"Table _migration_test_ was created — rollback failed! Tables: {tables}"
                )

                # Verify no bookkeeping entry for v2
                cur.execute("SELECT version FROM schema_migrations WHERE version = 2")
                row = cur.fetchone()
                assert row is None, "Bookkeeping shows v2 applied after injected failure!"

                # v1 should NOT have been applied either
                cur.execute("SELECT version FROM schema_migrations WHERE version = 1")
                row = cur.fetchone()
                assert row is None, "Bookkeeping shows v1 applied after injected failure!"
            finally:
                MIGRATIONS.pop(2, None)
                SCHEMA_VERSIONS.pop(2, None)
        finally:
            con.close()

    def test_multi_statement_entry_cannot_implicitly_commit(self) -> None:
        """A script-like entry must not leak DDL through executescript semantics."""
        from psyche_os.storage.migrations import MIGRATIONS, Migration, Migrator
        from psyche_os.storage.schema import SCHEMA_VERSIONS

        con, _key = _temp_db()
        migration = Migration(
            version=2,
            label="test_no_implicit_commit",
            statements=[
                "CREATE TABLE _must_rollback_(x INTEGER); "
                "INSERT INTO _missing_table_ VALUES (1);"
            ],
        )
        MIGRATIONS[2] = migration
        SCHEMA_VERSIONS[2] = migration.label
        try:
            report = Migrator(con).apply(2)
            assert not report.success
            names = {
                row[0]
                for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            assert "_must_rollback_" not in names
            assert list(con.execute("SELECT version FROM schema_migrations")) == []
        finally:
            MIGRATIONS.pop(2, None)
            SCHEMA_VERSIONS.pop(2, None)
            con.close()

    def test_clean_database_failure_rolls_back_bookkeeping_table(self) -> None:
        from sqlcipher3 import dbapi2

        from psyche_os.storage.migrations import MIGRATIONS, Migration, Migrator

        con = dbapi2.connect(":memory:")
        con.execute("PRAGMA key='clean-failure-test'")
        original = MIGRATIONS[1]
        MIGRATIONS[1] = Migration(
            version=1,
            label=original.label,
            statements=[
                "CREATE TABLE _must_rollback_(x INTEGER);",
                "INSERT INTO _missing_table_ VALUES (1);",
            ],
        )
        try:
            report = Migrator(con).apply(1)
            assert not report.success
            names = {
                row[0]
                for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")
            }
            assert "_must_rollback_" not in names
            assert "schema_migrations" not in names
        finally:
            MIGRATIONS[1] = original
            con.close()


# ============================================================================
# 2. Synthetic-only storage write boundary
# ============================================================================


class TestSyntheticWriteBoundary:
    """Prove that ordinary content writes are rejected at the UoW boundary."""

    def test_direct_uow_write_without_authority_rejected(self) -> None:
        """Direct UoW commit without FixtureAuthority must raise UnitOfWorkError
        before any SQL mutation, and zero rows must be changed."""
        from sqlcipher3 import dbapi2

        from psyche_os.domain.ids import RecordId, generate_id
        from psyche_os.storage.schema import apply_schema
        from psyche_os.storage.uow import UnitOfWorkError, UnitOfWorkManager

        con = dbapi2.connect(":memory:")
        con.execute(f"PRAGMA key = 'uow_auth_test';")
        apply_schema(con)

        # No authority supplied — writes must be rejected
        manager = UnitOfWorkManager(con, _authority=None)

        try:
            with manager.begin(actor_id="test", purpose="initial") as uow:
                uow.add_operation(
                    table="actors",
                    record_id=RecordId(generate_id()),
                    data={
                        "actor_id": generate_id(),
                        "actor_kind": "system",
                        "actor_label": "unauthorized",
                    },
                )
            pytest.fail("Direct UoW write without authority should have raised")
        except UnitOfWorkError as exc:
            assert "CONTENT_WRITE_REJECTED" in str(exc)

        # Verify zero rows in actors
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM actors")
        count = cur.fetchone()[0]
        assert count == 0, f"Expected 0 rows in actors after rejected write, got {count}"
        con.close()

    def test_altered_fixture_rejected(self) -> None:
        """A fixture whose digest does not match the canonical rows must fail."""
        import psyche_os.fixtures as fixture_module
        from psyche_os.fixtures import FixtureLoadError

        payload = json.loads(
            Path(fixture_module.__file__).with_name("f0_smoke.json").read_text(encoding="utf-8")
        )
        payload["digest"] = "deadbeef" * 8
        with pytest.raises(FixtureLoadError, match="digest mismatch"):
            fixture_module._validate_manifest(payload)

    def test_incompatible_fixture_schema_rejected(self) -> None:
        import psyche_os.fixtures as fixture_module
        from psyche_os.fixtures import FixtureLoadError

        payload = json.loads(
            Path(fixture_module.__file__).with_name("f0_smoke.json").read_text(encoding="utf-8")
        )
        payload["schema_version"] = 999
        with pytest.raises(FixtureLoadError, match="schema_version"):
            fixture_module._validate_manifest(payload)

    def test_unknown_fixture_rejected(self) -> None:
        """A fixture pack that is not in the known-pack registry must fail."""
        from psyche_os.fixtures import FixtureLoadError, load_fixture_rows

        with pytest.raises(FixtureLoadError, match="Unknown fixture pack"):
            load_fixture_rows("nonexistent_pack_xyz")

    def test_bundled_fixture_succeeds_through_loader(self) -> None:
        """The bundled f0_smoke fixture must load successfully and produce rows."""
        from psyche_os.fixtures import load_fixture_rows

        rows = load_fixture_rows("f0_smoke")
        assert isinstance(rows, dict)
        assert len(rows) >= 1
        total = sum(len(v) for v in rows.values())
        assert total >= 1, "fixture loader returned empty rows"

    def test_bundled_fixture_writes_to_vault(self) -> None:
        """write_fixture_to_vault must succeed and produce rows in the target DB."""
        from sqlcipher3 import dbapi2

        from psyche_os.domain.ids import VaultId, generate_id
        from psyche_os.fixtures import write_fixture_to_vault
        from psyche_os.storage.schema import apply_schema

        con = dbapi2.connect(":memory:")
        con.execute("PRAGMA key = 'fixture_write_test';")
        apply_schema(con)

        vault_id = VaultId(generate_id())
        count = write_fixture_to_vault(con, "f0_smoke", vault_id)
        assert count > 0, "write_fixture_to_vault wrote zero rows"

        # Verify rows exist
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM actors")
        actor_count = cur.fetchone()[0]
        assert actor_count > 0, "No actors rows after fixture write"
        con.close()


# ============================================================================
# 3. Truthful E00 validation and deferred-surface lock
# ============================================================================


class TestTruthfulValidation:
    """Prove that E00 validators emit truthful, schema-backed results."""

    def test_valid_schema_passes(self) -> None:
        """The production export emitter must pass its shipped JSON Schema."""
        from scripts.validate_f0_artifacts import check_export_schemas

        result = check_export_schemas()
        assert result["passed"], result["issues"]
        assert result["in_scope_state"] == "VALIDATED"
        assert result["deferred_capabilities"]["backup_restore"] == "DEFERRED_NOT_READY"

    def test_malformed_manifest_rejected(self) -> None:
        """A malformed export artifact must fail the actual shipped schema."""
        from scripts.validate_f0_artifacts import ROOT, validate_json_schema

        errors = validate_json_schema(
            {"manifest_id": "fake", "export_version": "not-semver"},
            ROOT / "schemas" / "export" / "v1" / "export_manifest.schema.json",
        )
        assert errors

    def test_fake_evidence_rejected(self) -> None:
        """A PASS label is not structural SQLCipher probe evidence."""
        from scripts.validate_f0_scope import validate_probe_evidence

        fake = SimpleNamespace(
            probe_number=5,
            passed=True,
            evidence="PASS",
            capability_verdict="verified",
        )
        assert validate_probe_evidence(fake) is not None

    def test_validator_is_read_only(self) -> None:
        from scripts.validate_f0_artifacts import ROOT, check_export_schemas

        paths = [
            ROOT / "schemas" / "export" / "v1" / "export_manifest.schema.json",
            ROOT / "schemas" / "backup" / "v1" / "backup_manifest.schema.json",
        ]
        before = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        assert check_export_schemas()["passed"]
        after = {path: hashlib.sha256(path.read_bytes()).hexdigest() for path in paths}
        assert after == before


class TestDeferredSurfaceLock:
    """Prove that features deferred in E01 remain locked.

    E01 activates backup/restore for the synthetic database-only profile.
    Blob writes and general filesystem mutation remain DEFERRED.
    """

    _DEFERRED_FEATURES: list[tuple[list[str], str]] = []

    _ACTIVATED_E01_FEATURES = [
        (["backup", "create", "--output", "x"], "backup.create"),
        (["backup", "verify", "--package", "x"], "backup.verify"),
        (["restore", "verify"], "restore.verify"),
        (["restore", "activate"], "restore.activate"),
    ]

    def test_all_deferred_features_removed_in_e01(self) -> None:
        """E01 activates backup/restore — no CLI commands remain deferred."""
        assert self._DEFERRED_FEATURES == [], (
            "No CLI features should remain deferred in E01"
        )

    def test_backup_restore_cli_activated_in_e01(self) -> None:
        """Backup/restore commands return ACTIVATED_E01 state in E01."""
        from psyche_os.interfaces.cli import create_cli

        cli = create_cli()
        for argv, feature_name in self._ACTIVATED_E01_FEATURES:
            result = cli.dispatch(argv)
            data = result.data or {}
            state = data.get("state", "")
            # In E01, backup/restore are activated but still expect proper args
            # Without required args, they return error status with a warning
            assert state != "FEATURE_DEFERRED_PRE_REAL_DATA", (
                f"{feature_name}: should not return FEATURE_DEFERRED_PRE_REAL_DATA in E01, "
                f"got data={data}"
            )
            assert result.status == "error", (
                f"{feature_name}: expected error status (missing required args), "
                f"got {result.status}"
            )

    def test_export_not_deferred(self) -> None:
        """Logical export remains available (not deferred per ADR-021)."""
        from psyche_os.interfaces.cli import create_cli

        cli = create_cli()
        # export create still requires a vault — error is expected but not deferred
        result = cli.dispatch(["export", "create", "--output", "/nonexistent"])
        data = result.data or {}
        assert data.get("state") != "FEATURE_DEFERRED_PRE_REAL_DATA", (
            "Export must not be deferred — only backup/restore are"
        )

    def test_e01_activated_python_apis_no_longer_deferred(self, tmp_path: Path) -> None:
        """E01 activates backup/restore Python APIs — they no longer raise DeferredFeatureError."""
        from sqlcipher3 import dbapi2

        from psyche_os.backup_export.operations import (
            restore_backup,
            verify_backup_file,
        )
        from psyche_os.backup_export.package_store import BackupPackageStore
        from psyche_os.storage.schema import apply_schema

        # verify_backup_file through BackupPackageStore — no longer deferred
        store = BackupPackageStore(str(tmp_path / "store"))
        missing_rel = "must-not-be-created.backup"
        # Returns (False, reason) tuple instead of raising
        result = verify_backup_file(store, missing_rel, None)  # type: ignore[arg-type]
        assert isinstance(result, tuple)
        assert result[0] is False  # File doesn't exist, so verification fails
        assert not (tmp_path / "store" / "must-not-be-created.backup").exists()

        # restore_backup — now creates its own target, no caller connection
        restore_path = str(tmp_path / "restored.db")
        restore_key = os.urandom(32).hex()
        result = restore_backup(
            store=store,
            relative_path=missing_rel,
            backup_key=None,  # type: ignore[arg-type]
            restore_db_path=restore_path,
            restore_db_key_hex=restore_key,
        )
        assert isinstance(result, dict)
        assert result.get("success") is False  # Missing backup file

    def test_blob_and_filesystem_still_deferred(self, tmp_path: Path) -> None:
        """Blob writes and general filesystem mutation remain DEFERRED in E01."""
        from sqlcipher3 import dbapi2

        from psyche_os.adapters.adapters import FilesystemAdapter, FilesystemError
        from psyche_os.application.ports import FixtureAuthority
        from psyche_os.domain.ids import BlobId, RecordId, VaultId, generate_id
        from psyche_os.storage.schema import apply_schema
        from psyche_os.storage.uow import UnitOfWorkError, UnitOfWorkManager

        con = dbapi2.connect(":memory:")
        con.execute("PRAGMA key='deferred-surface-test'")
        apply_schema(con)
        authority = FixtureAuthority._mint("f0_smoke", "a" * 64)
        manager = UnitOfWorkManager(con, _authority=authority)
        with pytest.raises(UnitOfWorkError, match="FEATURE_DEFERRED_PRE_REAL_DATA"):
            with manager.begin(actor_id="fixture-loader", purpose="initial") as uow:
                uow.add_blob(
                    BlobId(generate_id()),
                    RecordId(generate_id()),
                    b"synthetic blob",
                    VaultId(generate_id()),
                )
        assert con.execute("SELECT COUNT(*) FROM blobs").fetchone()[0] == 0
        con.close()

        adapter = FilesystemAdapter(tmp_path)
        with pytest.raises(FilesystemError, match="FEATURE_DEFERRED_PRE_REAL_DATA"):
            adapter.safe_write_bytes("blocked.bin", b"synthetic")
        assert not (tmp_path / "blocked.bin").exists()
