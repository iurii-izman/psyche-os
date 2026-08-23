"""Fail-closed proofs for the V1 logical export builder and verifier."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
from typing import Any

import pytest

from psyche_os.backup_export.operations import (
    ExportBuilder,
    ExportError,
    verify_export,
)
from psyche_os.crypto.envelope import SensitiveBytes
from psyche_os.domain.ids import VaultId, generate_id


def _builder() -> tuple[ExportBuilder, SensitiveBytes]:
    key = SensitiveBytes(os.urandom(32))
    return ExportBuilder(VaultId(generate_id()), key), key


def _actors_connection(*, include_is_active: bool = True) -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    if include_is_active:
        connection.execute(
            "CREATE TABLE actors (record_id TEXT, actor_id TEXT, is_active INTEGER)"
        )
        connection.execute(
            "INSERT INTO actors VALUES ('synthetic-record', 'synthetic-actor', 1)"
        )
    else:
        connection.execute("CREATE TABLE actors (record_id TEXT, actor_id TEXT)")
        connection.execute(
            "INSERT INTO actors VALUES ('synthetic-record', 'synthetic-actor')"
        )
    connection.commit()
    return connection


def test_table_without_is_active_is_exported_instead_of_silently_skipped(
    tmp_path: Path,
) -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute(
        "CREATE TABLE audit_events ("
        "event_id TEXT, event_kind TEXT, occurred_at TEXT)"
    )
    connection.execute(
        "INSERT INTO audit_events VALUES "
        "('synthetic-event', 'synthetic-check', '2042-01-01T00:00:00Z')"
    )
    connection.commit()
    builder, key = _builder()

    manifest = builder.export(
        connection, str(tmp_path / "export"), tables=["audit_events"]
    )

    assert manifest.record_count == 1
    assert set(manifest.table_checksums) == {"audit_events"}
    assert verify_export(str(tmp_path / "export"), key) == (
        True,
        "Export verified",
    )


def test_unsupported_table_and_schema_fail_before_artifact_creation(
    tmp_path: Path,
) -> None:
    builder, _key = _builder()
    unsupported_table_output = tmp_path / "unsupported-table"
    with pytest.raises(ExportError, match="^Unsupported export source table$"):
        builder.export(
            sqlite3.connect(":memory:"),
            str(unsupported_table_output),
            tables=["reflection_sessions"],
        )
    assert not unsupported_table_output.exists()

    connection = _actors_connection()
    connection.execute(
        "CREATE TABLE schema_migrations "
        "(version INTEGER, label TEXT, checksum TEXT)"
    )
    connection.execute(
        "INSERT INTO schema_migrations VALUES (9, 'unsupported', 'synthetic')"
    )
    connection.commit()
    unsupported_schema_output = tmp_path / "unsupported-schema"
    with pytest.raises(ExportError, match="^Export source schema is unsupported$"):
        builder.export(
            connection,
            str(unsupported_schema_output),
            tables=["actors"],
        )
    assert not unsupported_schema_output.exists()


def test_missing_required_columns_and_empty_selection_fail_closed(
    tmp_path: Path,
) -> None:
    builder, _key = _builder()
    output = tmp_path / "missing-column"
    with pytest.raises(
        ExportError,
        match="^Export source table is missing required columns$",
    ):
        builder.export(
            _actors_connection(include_is_active=False),
            str(output),
            tables=["actors"],
        )
    assert not output.exists()

    with pytest.raises(ExportError, match="^Export selection is empty$"):
        builder.export(
            sqlite3.connect(":memory:"),
            str(tmp_path / "empty-selection"),
            tables=[],
        )


class _CursorFault:
    def __init__(
        self,
        inner: sqlite3.Cursor,
        *,
        fail_count: bool = False,
        drop_actor_rows: bool = False,
    ) -> None:
        self._inner = inner
        self._fail_count = fail_count
        self._drop_actor_rows = drop_actor_rows
        self._drop_next_fetchall = False

    @property
    def description(self) -> Any:
        return self._inner.description

    def execute(self, sql: str, *args: Any) -> "_CursorFault":
        normalized = " ".join(sql.split())
        if self._fail_count and normalized.startswith("SELECT COUNT(*) FROM actors"):
            raise sqlite3.OperationalError("synthetic-sensitive-driver-detail")
        self._inner.execute(sql, *args)
        self._drop_next_fetchall = self._drop_actor_rows and normalized.startswith(
            "SELECT * FROM actors"
        )
        return self

    def fetchone(self) -> Any:
        return self._inner.fetchone()

    def fetchall(self) -> list[Any]:
        rows = self._inner.fetchall()
        if self._drop_next_fetchall:
            self._drop_next_fetchall = False
            return []
        return rows


class _ConnectionFault:
    def __init__(
        self,
        inner: sqlite3.Connection,
        *,
        fail_count: bool = False,
        drop_actor_rows: bool = False,
    ) -> None:
        self._inner = inner
        self._fail_count = fail_count
        self._drop_actor_rows = drop_actor_rows

    def cursor(self) -> _CursorFault:
        return _CursorFault(
            self._inner.cursor(),
            fail_count=self._fail_count,
            drop_actor_rows=self._drop_actor_rows,
        )


def test_query_error_is_stable_and_non_sensitive(tmp_path: Path) -> None:
    builder, _key = _builder()
    output = tmp_path / "query-error"
    connection = _ConnectionFault(_actors_connection(), fail_count=True)

    with pytest.raises(ExportError) as captured:
        builder.export(connection, str(output), tables=["actors"])

    assert str(captured.value) == "Export source query failed"
    assert "driver-detail" not in str(captured.value)
    assert not output.exists()


def test_source_count_mismatch_cannot_be_published(tmp_path: Path) -> None:
    builder, _key = _builder()
    output = tmp_path / "count-mismatch"
    connection = _ConnectionFault(_actors_connection(), drop_actor_rows=True)

    with pytest.raises(ExportError, match="^Export source count mismatch$"):
        builder.export(connection, str(output), tables=["actors"])

    assert not output.exists()


def test_verifier_rejects_manifest_record_count_mismatch(tmp_path: Path) -> None:
    builder, key = _builder()
    output = tmp_path / "plaintext"
    builder.export(
        _actors_connection(),
        str(output),
        encrypted=False,
        tables=["actors"],
    )

    manifest_path = output / "export_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["record_count"] = 2
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    assert verify_export(str(output), key) == (
        False,
        "Export record count mismatch",
    )
