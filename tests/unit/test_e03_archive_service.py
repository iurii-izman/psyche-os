"""Failure-driven E03 archive tests (E03-T1 through E03-T4)."""

import sqlite3

import pytest

from psyche_os.application.e03_archive import E03ArchiveError, E03ArchiveService


def service() -> E03ArchiveService:
    return E03ArchiveService(sqlite3.connect(":memory:"))


def seed_epistemic(value: E03ArchiveService) -> None:
    value.operate("CAPTURE_LAMP_REPORT", "occurred_summer_2042", "capture_001")
    value.operate("CAPTURE_LAMP_OBSERVATION", "observed_interval", "capture_002")
    value.operate("CAPTURE_COUNTERREPORT", "occurred_unknown", "capture_003")
    value.operate("ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed", "capture_004")


def test_e03_t1_closed_fixture_rejects_arbitrary_payload_before_write() -> None:
    """E03-T1: arbitrary text/path/table choices must fail before canonical mutation."""
    archive = service()
    before = archive.connection.total_changes
    with pytest.raises(E03ArchiveError, match="INVALID_OPERATION_CHOICE"):
        archive.operate("CAPTURE_LAMP_REPORT", "C:/private.txt", "capture_001")
    with pytest.raises(E03ArchiveError, match="INVALID_OPERATION_CHOICE"):
        archive.operate("DROP TABLE claims", "reported_exact", "capture_002")
    assert archive.connection.total_changes == before


def test_e03_t1_exact_operation_is_idempotent_and_types_do_not_collapse() -> None:
    """E03-T1: retry must not duplicate rows or collapse source/report/assertion."""
    archive = service()
    first = archive.operate("CAPTURE_LAMP_REPORT", "reported_exact", "capture_001")
    replay = archive.operate("CAPTURE_LAMP_REPORT", "reported_exact", "capture_001")
    assert first["created_types"][:4] == ["source_artifact", "source_locator", "report", "assertion"]
    assert replay["idempotent_replay"] is True
    assert archive.connection.execute("SELECT COUNT(*) FROM source_artifacts WHERE semantic_version=2").fetchone()[0] == 1


def test_e03_t2_fuzzy_unknown_and_explicit_clocks_preserve_precision() -> None:
    """E03-T2: summer/unknown time must not become fabricated instants."""
    archive = service()
    seed_epistemic(archive)
    occurred = archive.timeline("occurred")
    summer = next(item for item in occurred if item["original_literal"] == "summer 2042")
    unknown = next(item for item in occurred if item["value_kind"] == "unknown")
    assert summer["precision"] == "season" and summer["lower_value"] == "2042-06-01"
    assert unknown["lower_value"] is None and unknown["upper_value"] is None
    with pytest.raises(E03ArchiveError, match="INVALID_TEMPORAL_ROLE"):
        archive.timeline("event_at")


def test_e03_t3_epistemic_axes_and_conflict_survive_round_trip_without_truth_score() -> None:
    """E03-T3: conflict/unknown/uncertainty must remain typed, not one confidence."""
    archive = service()
    seed_epistemic(archive)
    view = archive.explorer()
    assert len(view["uncertainty"]) == 4
    assert view["contradictions"][0]["resolution_status"] == "unresolved"
    assert view["unknowns"][0]["unknown_reason"] == "ambiguous"
    assert view["claims"][0]["claim_status"] == "proposed"
    assert "not facts" in view["notice"]
    assert "confidence" not in str(view).lower()


def test_e03_t4_snapshot_is_immutable_and_diff_keeps_unresolved_state() -> None:
    """E03-T4: deterministic successor must not mutate baseline or imply completion."""
    archive = service()
    seed_epistemic(archive)
    archive.operate("CREATE_BASELINE_SNAPSHOT", "baseline", "snapshot_001")
    archive.operate("CREATE_REVISED_SNAPSHOT", "revised", "snapshot_002")
    diff = archive.snapshot_diff()
    assert diff["previous_snapshot"] == "snapshot-baseline-v1"
    assert diff["changed"] == ["claim-lamp"]
    assert diff["unresolved_contradictions"] == 1 and diff["open_unknowns"] == 1
    assert diff["completion_percentage"] is None
    with pytest.raises(sqlite3.IntegrityError, match="immutable"):
        archive.connection.execute("UPDATE personal_model_snapshots SET change_summary='rewrite'")
