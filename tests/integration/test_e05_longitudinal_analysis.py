"""Canonical application/storage integration proofs for E05."""

from pathlib import Path
import sqlite3

import pytest

from psyche_os.application.e05_longitudinal import E05LongitudinalError, E05LongitudinalService
from psyche_os.domain.longitudinal import MissingnessState, ProcessingKind, SleepSourceType


def loaded_service() -> E05LongitudinalService:
    service = E05LongitudinalService()
    result = service.operate("LOAD_FICTIONAL_LANTERN", "fictional_lantern_v1", "load_fixture")
    assert result == {
        "protocols": 1,
        "events": 10,
        "sleep_records": 5,
        "contexts": 2,
        "data_mode": "synthetic_only",
    }
    return service


def test_fixed_fixture_writes_typed_canonical_records_and_analyzes_exact_window() -> None:
    service = loaded_service()
    summary = service.operate("ANALYZE_FICTIONAL_LANTERN", "full_window", "analysis_fixture")
    assert summary.denominator == 10 and summary.observed_count == 5
    assert dict(summary.missingness_counts)[MissingnessState.DECLINED] == 1
    assert dict(summary.source_composition) == dict.fromkeys(SleepSourceType, 1)
    assert summary.c3_enabled is False
    consumer = service.connection.execute(
        "SELECT processing_kind,device_model,firmware_version,algorithm_epoch FROM sleep_records WHERE source_type='consumer_wearable'"
    ).fetchone()
    assert consumer == ("black_box_estimate", "W-2", "fw-7", "proprietary-2044-04")
    assert ProcessingKind(consumer[0]) is ProcessingKind.BLACK_BOX_ESTIMATE


def test_arbitrary_payload_cannot_modify_protocol_or_analysis_policy_and_gate_stays_closed() -> (
    None
):
    service = loaded_service()
    before = service.connection.execute("SELECT * FROM sampling_protocols").fetchall()
    with pytest.raises(E05LongitudinalError, match="INVALID_NAMED_OPERATION"):
        service.operate("WRITE_PROTOCOL", '{"schedule":"arbitrary"}', "attack")
    with pytest.raises(E05LongitudinalError, match="INVALID_NAMED_OPERATION"):
        service.operate("ANALYZE_SQL", "SELECT * FROM sleep_records", "attack2")
    assert service.connection.execute("SELECT * FROM sampling_protocols").fetchall() == before
    gate = Path("docs/architecture/REAL_DATA_GATE.yaml").read_text(encoding="utf-8")
    assert 'status: "CLOSED"' in gate


def test_database_constraints_reject_incomplete_device_metadata_and_out_of_window_event() -> None:
    service = loaded_service()
    with pytest.raises(sqlite3.IntegrityError):
        service.connection.execute(
            "INSERT INTO sleep_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "bad",
                3,
                "fictional-lantern-activation",
                "1.0.0",
                "consumer_wearable",
                "2044-04-01T00:00:00+00:00",
                "2044-04-01T08:00:00+00:00",
                400,
                "black_box_estimate",
                None,
                None,
                None,
                None,
            ),
        )
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        service.connection.execute(
            "UPDATE sampling_protocols SET duration_days=7 WHERE protocol_id='fictional-lantern-activation'"
        )
    with pytest.raises(sqlite3.IntegrityError):
        service.connection.execute(
            "INSERT INTO longitudinal_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "bad-event",
                3,
                "fictional-lantern-activation",
                "1.0.0",
                "2044-04-01T09:00:00+00:00",
                "2044-04-01T10:00:00+00:00",
                "2044-04-01T10:00:00+00:00",
                "prompt_exposed",
                "none",
                "recorded",
                "observed",
                2,
            ),
        )


def test_deleting_protocol_cascades_all_e05_dependencies() -> None:
    service = loaded_service()
    result = service.operate("DELETE_FICTIONAL_LANTERN", "confirmed_fixture_only", "delete_fixture")
    assert result == {
        "protocols_deleted": 1,
        "dependency_rows_remaining": 0,
        "canonical_absence": True,
    }
