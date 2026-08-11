"""Integration tests for SQLCipher gate and storage."""

import os
import tempfile

import pytest

from psyche_os.crypto.envelope import (
    BlobAEAD,
    derive_domain_key,
    generate_vmk,
)
from psyche_os.domain.ids import BlobId, RecordId, VaultId, generate_id
from psyche_os.storage.schema import ALL_DDL, apply_schema
from psyche_os.storage.sqlcipher_gate import (
    ALL_PROBES,
    GateReport,
    GateState,
    gate_accepted,
    run_gate,
)
from psyche_os.storage.uow import (
    UnitOfWork,
    UnitOfWorkManager,
)

pytestmark = [pytest.mark.integration, pytest.mark.sqlcipher]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def temp_db_path() -> str:
    fd, path = tempfile.mkstemp(suffix=".db", prefix="psyche_test_")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Gate tests
# ---------------------------------------------------------------------------


class TestSQLCipherGate:
    def test_all_8_probes_registered(self) -> None:
        assert len(ALL_PROBES) == 8

    def test_run_gate_returns_report(self) -> None:
        report = run_gate()
        assert isinstance(report, GateReport)
        assert len(report.results) == 8

    def test_gate_accepted(self) -> None:
        result = run_gate()
        assert result.gate_state == GateState.ACCEPTED
        assert result.all_passed is True
        assert result.failed_count == 0

    def test_gate_accepted_function(self) -> None:
        assert gate_accepted() is True

    def test_each_probe_has_evidence(self) -> None:
        report = run_gate()
        for r in report.results:
            assert r.probe_number >= 1
            assert r.probe_name
            assert r.passed is True


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSchema:
    def test_all_ddl_applies(self, temp_db_path: str) -> None:
        from sqlcipher3 import dbapi2

        con = dbapi2.connect(temp_db_path)
        con.execute("PRAGMA key = 'schema_test_key';")
        apply_schema(con)
        con.close()

        # Reopen
        con2 = dbapi2.connect(temp_db_path)
        con2.execute("PRAGMA key = 'schema_test_key';")
        cur = con2.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name;")
        tables = [row[0] for row in cur.fetchall()]
        con2.close()

        assert "schema_migrations" in tables
        assert "vault_config" in tables
        assert "actors" in tables
        assert "observations" in tables
        assert "claims" in tables
        assert "data_policies" in tables
        assert "audit_events" in tables
        assert "blobs" in tables
        assert "deletion_plans" in tables
        assert "backup_manifests" in tables

    def test_all_ddl_count(self) -> None:
        # 20 tables total
        assert len(ALL_DDL) == 20


# ---------------------------------------------------------------------------
# Unit of work tests
# ---------------------------------------------------------------------------


class TestUnitOfWork:
    def test_create_uow(self) -> None:
        uow = UnitOfWork(actor_id="test-actor", purpose="testing")
        assert uow.actor_id == "test-actor"
        assert uow.total_operations == 0

    def test_add_operation(self) -> None:
        uow = UnitOfWork()
        # F05: data must not contain system-managed columns
        op = uow.add_operation(
            table="actors",
            record_id=RecordId(generate_id()),
            data={
                "actor_id": generate_id(),
                "actor_kind": "human",
                "actor_label": "test",
            },
        )
        assert uow.total_operations == 1
        assert op.table == "actors"

    def test_add_operation_rejects_system_columns(self) -> None:
        """F05: add_operation must reject system-managed columns in data dict."""
        from psyche_os.storage.uow import UnitOfWorkError

        uow = UnitOfWork()
        with pytest.raises(UnitOfWorkError):
            uow.add_operation(
                table="actors",
                record_id=RecordId(generate_id()),
                data={"record_id": generate_id(), "tx_from": "2026-01-01T00:00:00+00:00"},
            )

    def test_add_operation_rejects_unknown_table(self) -> None:
        """F05: add_operation must reject tables not in the allowlist."""
        from psyche_os.storage.uow import UnitOfWorkError

        uow = UnitOfWork()
        with pytest.raises(UnitOfWorkError):
            uow.add_operation(
                table="nonexistent_table",
                record_id=RecordId(generate_id()),
                data={"x": "y"},
            )

    def test_add_blob(self) -> None:
        uow = UnitOfWork()
        bop = uow.add_blob(
            blob_id=BlobId(generate_id()),
            record_id=RecordId(generate_id()),
            plaintext=b"test content",
            vault_id=VaultId(generate_id()),
        )
        assert uow.total_operations == 1

    def test_complete(self) -> None:
        uow = UnitOfWork()
        uow.complete()
        assert uow.completed_at is not None

    def test_commit_and_rollback(self, temp_db_path: str) -> None:
        """Test that UnitOfWorkManager commits data atomically.

        F07: The test must supply a valid FixtureAuthority via _authority
        since direct writes without authority are now rejected at the UoW
        boundary.
        """
        from sqlcipher3 import dbapi2

        from psyche_os.application.ports import FixtureAuthority

        con = dbapi2.connect(temp_db_path)
        con.execute("PRAGMA key = 'uow_test_key';")
        apply_schema(con)

        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        authority = FixtureAuthority._mint("test", "a" * 64)
        manager = UnitOfWorkManager(con, blob_aead=aead, _authority=authority)

        vault_id = VaultId(generate_id())
        actor_id = RecordId(generate_id())

        with manager.begin(actor_id="test-actor", purpose="test") as uow:
            uow.add_operation(
                table="actors",
                record_id=actor_id,
                data={
                    "actor_id": generate_id(),
                    "actor_kind": "system",
                    "actor_label": "test actor",
                },
            )

        # Verify data was committed
        cur = con.cursor()
        cur.execute(
            "SELECT record_id, actor_label FROM actors WHERE record_id = ?", (str(actor_id),)
        )
        row = cur.fetchone()
        con.close()

        assert row is not None
        assert row[1] == "test actor"
