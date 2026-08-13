"""Canonical E06 named-operation, persistence, stop, and regression proofs."""

from pathlib import Path

import pytest

from psyche_os.application.e05_longitudinal import E05LongitudinalService
from psyche_os.application.e06_experiments import E06ExperimentError, E06ExperimentService
from psyche_os.knowledge import AssessmentRegistry


def loaded() -> E06ExperimentService:
    service = E06ExperimentService()
    assert service.operate("LOAD_FICTIONAL_PRISM", "fictional_prism_v1", "load") == {
        "interventions": 1, "protocols": 1, "runs": 1, "periods": 8, "data_mode": "synthetic_only"
    }
    return service


@pytest.mark.integration
def test_fixed_protocol_persists_separate_versions_assignments_exposure_outcomes_and_deviations() -> None:
    service = loaded()
    result = service.operate("ANALYZE_FICTIONAL_PRISM", "preregistered_known_answer", "analyze")
    assert result.protocol_version == "1.0.0"
    assert result.intervention_version == "1.0.0"
    assert result.measurement_version == "fictional-scale-v1"
    assert result.assignment_version == "python-random-v1"
    assert result.analysis_version == "e06-known-answer-v1"
    assert result.excluded_periods == (5,) and result.contrast_b_minus_a > 0
    row = service.connection.execute(
        "SELECT scheduled_condition,actual_exposure,outcome_value,missingness,deviation_code FROM experiment_period_records WHERE period=5"
    ).fetchone()
    assert row[0] == row[1] and row[2:] == (None, "technical_failure", "fixture_read_unavailable")


@pytest.mark.integration
@pytest.mark.parametrize(
    ("operation", "choice", "reason"),
    (
        ("STOP_FICTIONAL_PRISM", "user_stop", "user_stop"),
        ("SIGNAL_ADVERSE_FICTIONAL_PRISM", "adverse_signal", "adverse_signal"),
        ("SIGNAL_CONTRAINDICATION_FICTIONAL_PRISM", "contraindication", "contraindication"),
    ),
)
def test_stop_adverse_and_contraindication_freeze_assignment_and_claims(operation: str, choice: str, reason: str) -> None:
    service = loaded()
    stopped = service.operate(operation, choice, f"stop-{reason}")
    assert stopped == {"status": "stopped", "reason": reason, "assignment_blocked": True, "claims_blocked": True}
    with pytest.raises(E06ExperimentError, match="CLAIMS_FROZEN"):
        service.operate("ANALYZE_FICTIONAL_PRISM", "preregistered_known_answer", "after-stop")


@pytest.mark.integration
def test_stale_digest_and_assignment_drift_fail_closed() -> None:
    service = loaded()
    service.connection.execute("UPDATE experiment_runs SET preregistration_digest=?", ("0" * 64,))
    with pytest.raises(E06ExperimentError, match="STALE_PROTOCOL"):
        service.operate("ANALYZE_FICTIONAL_PRISM", "preregistered_known_answer", "stale")
    drift = loaded()
    drift.connection.execute("UPDATE experiment_runs SET assignment_digest=?", ("0" * 64,))
    with pytest.raises(E06ExperimentError, match="assignment drift"):
        drift.operate("ANALYZE_FICTIONAL_PRISM", "preregistered_known_answer", "drift")
    assert drift.connection.execute("SELECT stop_reason FROM experiment_runs").fetchone()[0] == "assignment_drift"


@pytest.mark.integration
def test_arbitrary_payloads_have_no_protocol_policy_outcome_or_database_authority() -> None:
    service = loaded()
    before = service.connection.execute("SELECT * FROM experiment_protocols").fetchall()
    attacks = (
        ("REGISTER_INTERVENTION", "medication-alias"),
        ("IMPORT_PROTOCOL", '{"risk":"R0_observational"}'),
        ("ANALYZE_SQL", "SELECT * FROM experiment_runs"),
        ("LOAD_FROM_ENV", "E06_PROTOCOL"),
        ("LOAD_FROM_FILE", "arbitrary.json"),
        ("RENDER_AND_SAVE", "arbitrary outcome"),
    )
    for index, (operation, choice) in enumerate(attacks):
        with pytest.raises(E06ExperimentError, match="INVALID_NAMED_OPERATION"):
            service.operate(operation, choice, f"attack-{index}")
    assert service.connection.execute("SELECT * FROM experiment_protocols").fetchall() == before


@pytest.mark.integration
def test_deletion_cascades_e06_dependencies_and_prior_epic_gates_stay_closed() -> None:
    service = loaded()
    assert service.operate("DELETE_FICTIONAL_PRISM", "confirmed_fixture_only", "delete") == {
        "interventions_deleted": 1, "dependency_rows_remaining": 0, "canonical_absence": True
    }
    e05 = E05LongitudinalService()
    e05.operate("LOAD_FICTIONAL_LANTERN", "fictional_lantern_v1", "e05-load")
    assert e05.operate("ANALYZE_FICTIONAL_LANTERN", "full_window", "e05-analysis").c3_enabled is False
    assert not AssessmentRegistry().list_statuses()[0].scientific_claims_enabled
    assert 'status: "CLOSED"' in Path("docs/architecture/REAL_DATA_GATE.yaml").read_text(encoding="utf-8")
