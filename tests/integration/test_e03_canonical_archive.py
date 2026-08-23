"""Production-path canonical correction/deletion/desktop proofs for E03."""

import sqlite3

import pytest

from psyche_os.application.desktop_service import DesktopApplicationService
from psyche_os.application.e03_archive import E03ArchiveError, E03ArchiveService


def archive_with_all_records() -> E03ArchiveService:
    archive = E03ArchiveService(sqlite3.connect(":memory:"))
    for index, (operation, choice) in enumerate((
        ("CAPTURE_LAMP_REPORT", "reported_exact"),
        ("CAPTURE_LAMP_OBSERVATION", "observed_interval"),
        ("CAPTURE_COUNTERREPORT", "reported_exact"),
        ("ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed"),
        ("CREATE_BASELINE_SNAPSHOT", "baseline"),
        ("CREATE_REVISED_SNAPSHOT", "revised"),
    )):
        archive.operate(operation, choice, f"integration_{index:02d}")
    return archive


def test_e03_t5_canonical_correction_is_atomic_and_rejects_stale_base() -> None:
    """E03-T5: stale correction must not close or overwrite canonical history."""
    archive = archive_with_all_records()
    result = archive.correct_lamp_report_time("report-lamp-v1")
    assert result["history_preserved"] and result["change_reason"] == "correction"
    versions = archive.connection.execute("SELECT version_id,is_active,tx_to,previous_version_id FROM reports WHERE record_id='report-lamp' ORDER BY version_id").fetchall()
    assert versions[0][1] == 0 and versions[0][2] is not None
    assert versions[1][1] == 1 and versions[1][3] == "report-lamp-v1"
    with pytest.raises(E03ArchiveError, match="STALE_VERSION"):
        archive.correct_lamp_report_time("report-lamp-v1")
    assert archive.connection.execute("SELECT COUNT(*) FROM reports WHERE record_id='report-lamp' AND is_active=1").fetchone()[0] == 1


def test_e03_t6_dry_run_cancel_and_fault_preserve_all_canonical_state() -> None:
    """E03-T6: preview, wrong confirmation and injected failure must not mutate."""
    archive = archive_with_all_records()
    before = archive.connection.iterdump()
    before_sql = "\n".join(before)
    preview = archive.operate("DELETE_LAMP_SOURCE", "dry_run", "delete_preview")
    assert preview["mutated"] is False
    with pytest.raises(E03ArchiveError, match="CONFIRMATION_REQUIRED"):
        archive.execute_deletion(preview["plan_id"], "cancel")
    with pytest.raises(E03ArchiveError, match="DELETION_FAILED_PRESERVED"):
        archive.execute_deletion(preview["plan_id"], "DELETE ORCHID LAMP SOURCE", inject_failure=True)
    assert "\n".join(archive.connection.iterdump()) == before_sql


def test_e03_t6_dependency_deletion_removes_reconstructive_state_and_receipt_content() -> None:
    """E03-T6: closure is data-derived and preserves unrelated canonical rows."""
    archive = archive_with_all_records()
    archive.connection.execute(
        "INSERT INTO source_artifacts("
        "record_id,artifact_id,version_id,source_kind,source_label,uri_or_path,mime_type,"
        "source_metadata,tx_from,is_active,created_at,semantic_version,schema_version,"
        "change_reason_code,created_by_actor_id,artifact_kind,origin_kind,captured_at,"
        "language_tags,byte_size,parser_state,quarantine_state) "
        "VALUES(?,?,?,?,?,?,?,?,?,1,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            "source-unrelated", "source-unrelated", "source-unrelated-v1", "fixture_report",
            "Unrelated fictional source", "", "text/plain", "{}", "2042-09-02T10:00:00+00:00",
            "2042-09-02T10:00:00+00:00", 2, 2, "initial", "actor-owner", "user_note",
            "user_created", "2042-09-02T10:00:00+00:00", "[\"en\"]", 10, "raw", "none",
        ),
    )
    archive.connection.commit()
    preview = archive.operate("DELETE_LAMP_SOURCE", "dry_run", "delete_preview")
    assert preview["counts"]["source_artifacts"] == 1
    assert preview["counts"]["reports"] == 1
    assert preview["counts"]["assertions"] == 1
    receipt = archive.execute_deletion(preview["plan_id"], "DELETE ORCHID LAMP SOURCE")
    assert receipt["canonical_absence"] is True
    assert receipt["content_in_receipt"] is False and receipt["stable_content_hash"] is False
    assert receipt["projection_rebuild"] == "rebuilt"
    assert archive.connection.execute(
        "SELECT COUNT(*) FROM source_artifacts WHERE record_id='source-unrelated'"
    ).fetchone() == (1,)
    assert archive.connection.execute(
        "SELECT COUNT(*) FROM reports WHERE record_id='report-counter'"
    ).fetchone() == (1,)
    assert archive.connection.execute(
        "SELECT COUNT(*) FROM assertions WHERE record_id='assertion-counter'"
    ).fetchone() == (1,)
    assert archive.connection.execute(
        "SELECT COUNT(*) FROM source_artifacts WHERE record_id='source-lamp'"
    ).fetchone() == (0,)
    assert archive.connection.execute(
        "SELECT COUNT(*) FROM personal_model_snapshots"
    ).fetchone() == (0,)
    stored = archive.connection.execute("SELECT verification_hash FROM deletion_receipts").fetchone()
    assert stored == (None,)


def test_e03_t5_t7_real_desktop_command_path_is_named_bounded_and_offline() -> None:
    """E03-T5/T7: desktop session must reach canonical correction via named IPC state."""
    desktop = DesktopApplicationService()
    try:
        token = desktop.dispatch("session.unlock", {"secret": "fixture"}, None)["session_token"]
        for index, (operation, choice) in enumerate((
            ("CAPTURE_LAMP_REPORT", "reported_exact"),
            ("CAPTURE_COUNTERREPORT", "occurred_unknown"),
            ("ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed"),
        )):
            desktop.dispatch("archive.operate", {"operation": operation, "choice": choice, "idempotency_key": f"desktop_{index:02d}"}, token)
        corrected = desktop.dispatch("archive.operate", {"operation":"CORRECT_LAMP_REPORT_TIME","choice":"corrected_reported_exact","idempotency_key":"desktop_correct"}, token)
        status = desktop.dispatch("status.get", {}, None)
        assert corrected["history_preserved"] is True
        assert status["inbound_listener"] == "NONE"
        assert status["outbound_provider"] == "NOT_CONFIGURED"
        assert status["real_data_gate"] == "CLOSED"
        with pytest.raises(Exception, match="INVALID_PAYLOAD"):
            desktop.dispatch("archive.explorer", {"sql":"SELECT *"}, token)
    finally:
        desktop.close()
