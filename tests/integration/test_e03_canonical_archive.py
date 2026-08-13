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
    """E03-T6: confirmed closure must remove canonical V2 descendants and hashes."""
    archive = archive_with_all_records()
    preview = archive.operate("DELETE_LAMP_SOURCE", "dry_run", "delete_preview")
    receipt = archive.execute_deletion(preview["plan_id"], "DELETE ORCHID LAMP SOURCE")
    assert receipt["canonical_absence"] is True
    assert receipt["content_in_receipt"] is False and receipt["stable_content_hash"] is False
    assert receipt["projection_rebuild"] == "rebuilt"
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
        assert status["network"] == "OFFLINE_NO_LISTENER" and status["real_data_gate"] == "CLOSED"
        with pytest.raises(Exception, match="INVALID_PAYLOAD"):
            desktop.dispatch("archive.explorer", {"sql":"SELECT *"}, token)
    finally:
        desktop.close()
