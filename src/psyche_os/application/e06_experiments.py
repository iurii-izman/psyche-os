"""Named-operation E06 service over one package-owned fictional protocol."""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any, ClassVar

from psyche_os.domain.experiments import (
    FIXED_R1_ID,
    ActionRiskTier,
    AnalysisResult,
    DesignTier,
    ExperimentProtocol,
    ExperimentValidationError,
    InterventionDefinition,
    MissingOutcome,
    PeriodRecord,
    StopReason,
    analyze_known_answer,
    assignment_digest,
    resolve_intervention,
    resolve_protocol,
    seeded_assignments,
)
from psyche_os.storage.migrations import Migrator


class E06ExperimentError(ValueError):
    """The request is outside the fixed E06 synthetic authority."""


RUN_ID = "fictional-prism-run-001"


def fictional_intervention() -> InterventionDefinition:
    return InterventionDefinition(
        FIXED_R1_ID,
        "1.0.0",
        "Fictional prism card position",
        ("place one fictional prism card at the left or right marker",),
        "self_directed_fixture_instruction",
        True,
        "mechanics_fixture_only",
        "stop_on_any_unwanted_or_adverse_signal",
        "any_contraindication_blocks",
        "neutral_nonclinical_fixture",
        "repository_owned_fictional",
        "none_fixture_only",
        ActionRiskTier.R1_LOW_REVERSIBLE,
        "fixture_allowlisted",
        "identity_component_or_risk_change",
    )


def fictional_protocol() -> ExperimentProtocol:
    return ExperimentProtocol(
        "fictional-prism-crossover",
        "1.0.0",
        DesignTier.D3_RANDOMIZED_CROSSOVER,
        FIXED_R1_ID,
        "1.0.0",
        "In this fictional fixture, do marker positions differ in the fictional response?",
        "mean fictional response under B minus mean under A for this named run",
        "repository-owned fictional fixture is available and no stop boundary is present",
        "A_left_marker",
        "B_right_marker",
        "fictional_prism_response",
        "fictional-scale-v1",
        "no historical baseline; eight randomized fixture periods define the test window",
        "eight-period balanced randomized crossover",
        "psyche_sha256_balanced_rank",
        "sha256-rank-v1",
        6062044,
        "fixture labels are not blinded",
        8,
        "each period is independent by construction; lag-one sensitivity is required",
        "any concurrent fixture change is recorded separately and excludes that period",
        "no imputation; every missing reason stays explicit",
        "report lag-one contrast and leave-one-period-out sensitivity",
        "one preregistered contrast only",
        "at least two observed outcomes per condition",
        "stop immediately on request, stale state, drift, ineligibility, or contraindication",
        "any adverse signal stops; no triage or substitute action",
        "e06-known-answer-v1",
        "integer outcome; raw-scale mean contrast; no p-value or action rule",
        dt.datetime(2044, 5, 1, tzinfo=dt.UTC),
    )


def fictional_records(protocol: ExperimentProtocol) -> tuple[PeriodRecord, ...]:
    assignments = seeded_assignments(protocol)
    values = {"A_left_marker": (2, 3, 2, 3), "B_right_marker": (6, 7, 6, 7)}
    seen = {"A_left_marker": 0, "B_right_marker": 0}
    records: list[PeriodRecord] = []
    for assignment in assignments:
        index = seen[assignment.condition]
        seen[assignment.condition] += 1
        if assignment.period == 5:
            records.append(
                PeriodRecord(
                    assignment.period,
                    assignment.condition,
                    assignment.condition,
                    None,
                    None,
                    MissingOutcome.TECHNICAL_FAILURE,
                    "fixture_read_unavailable",
                )
            )
        else:
            records.append(
                PeriodRecord(
                    assignment.period,
                    assignment.condition,
                    assignment.condition,
                    dt.datetime(2044, 6, assignment.period, 12, tzinfo=dt.UTC),
                    values[assignment.condition][index],
                    MissingOutcome.OBSERVED,
                )
            )
    return tuple(records)


class E06ExperimentService:
    """No raw payload entry point: only exact fixture operations and choices."""

    _ALLOWED: ClassVar[set[tuple[str, str]]] = {
        ("LOAD_FICTIONAL_PRISM", "fictional_prism_v1"),
        *(("ADVANCE_FICTIONAL_PRISM", f"period_{period}") for period in range(1, 9)),
        ("ANALYZE_FICTIONAL_PRISM", "preregistered_known_answer"),
        ("STOP_FICTIONAL_PRISM", "user_stop"),
        ("SIGNAL_ADVERSE_FICTIONAL_PRISM", "adverse_signal"),
        ("SIGNAL_CONTRAINDICATION_FICTIONAL_PRISM", "contraindication"),
        ("DELETE_FICTIONAL_PRISM", "confirmed_fixture_only"),
    }

    def __init__(self, connection: sqlite3.Connection | None = None) -> None:
        self.connection = connection or sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")
        report = Migrator(self.connection).apply(4)
        if not report.success:
            raise E06ExperimentError("MIGRATION_FAILED")
        self._results: dict[str, Any] = {}

    def operate(self, operation: str, choice: str, idempotency_key: str) -> Any:
        if (operation, choice) not in self._ALLOWED:
            raise E06ExperimentError("INVALID_NAMED_OPERATION")
        if not idempotency_key or len(idempotency_key) > 80:
            raise E06ExperimentError("INVALID_IDEMPOTENCY_KEY")
        if idempotency_key in self._results:
            return self._results[idempotency_key]
        if operation == "LOAD_FICTIONAL_PRISM":
            result: Any = self._load()
        elif operation == "ADVANCE_FICTIONAL_PRISM":
            result = self._advance(choice)
        elif operation == "ANALYZE_FICTIONAL_PRISM":
            result = self._analyze()
        elif operation == "DELETE_FICTIONAL_PRISM":
            result = self._delete()
        else:
            reason = {
                "STOP_FICTIONAL_PRISM": StopReason.USER_STOP,
                "SIGNAL_ADVERSE_FICTIONAL_PRISM": StopReason.ADVERSE_SIGNAL,
                "SIGNAL_CONTRAINDICATION_FICTIONAL_PRISM": StopReason.CONTRAINDICATION,
            }[operation]
            result = self._stop(reason)
        self._results[idempotency_key] = result
        return result

    def _load(self) -> dict[str, int | str]:
        intervention = fictional_intervention()
        decision = resolve_intervention(intervention)
        if not decision.allowed:
            raise E06ExperimentError(decision.code.value)
        protocol = fictional_protocol()
        protocol_decision = resolve_protocol(
            protocol,
            active_digest=protocol.digest,
            eligibility_available=True,
            contraindication_present=False,
        )
        if not protocol_decision.allowed:
            raise E06ExperimentError(protocol_decision.code.value)
        assignments = seeded_assignments(protocol)
        digest = assignment_digest(assignments)
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO intervention_definitions VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    intervention.intervention_id,
                    intervention.version,
                    4,
                    intervention.label,
                    intervention.components[0],
                    intervention.delivery,
                    int(intervention.reversible),
                    intervention.evidence_certainty,
                    intervention.harms_boundary,
                    intervention.contraindication_boundary,
                    intervention.accessibility_equity,
                    intervention.rights_state,
                    intervention.guideline_context,
                    intervention.risk_tier.value,
                    intervention.review_state,
                    intervention.review_trigger,
                ),
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO experiment_protocols VALUES("
                + ",".join("?" for _ in range(32))
                + ")",
                (
                    protocol.protocol_id,
                    protocol.version,
                    4,
                    protocol.design_tier.value,
                    protocol.intervention_id,
                    protocol.intervention_version,
                    protocol.question,
                    protocol.estimand,
                    protocol.eligibility,
                    protocol.condition_a,
                    protocol.condition_b,
                    protocol.outcome,
                    protocol.measurement_version,
                    protocol.baseline_plan,
                    protocol.phase_design,
                    protocol.assignment_algorithm,
                    protocol.assignment_version,
                    protocol.seed,
                    protocol.blinding_state,
                    protocol.duration_periods,
                    protocol.washout_carryover,
                    protocol.concurrent_change_plan,
                    protocol.missingness_plan,
                    protocol.autocorrelation_plan,
                    protocol.multiplicity_family,
                    protocol.minimum_information,
                    protocol.stopping_rule,
                    protocol.adverse_rule,
                    protocol.analysis_version,
                    protocol.analysis_config,
                    protocol.preregistered_at.isoformat(),
                    protocol.digest,
                ),
            )
            self.connection.execute(
                "INSERT OR IGNORE INTO experiment_runs VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    RUN_ID,
                    4,
                    protocol.protocol_id,
                    protocol.version,
                    protocol.digest,
                    digest,
                    "active",
                    "none",
                    "2044-06-01T00:00:00+00:00",
                ),
            )
        return {
            "interventions": 1,
            "protocols": 1,
            "runs": 1,
            "scheduled_periods": 8,
            "executed_periods": 0,
            "data_mode": "synthetic_only",
        }

    def _canonical_protocol(self) -> ExperimentProtocol:
        row = self.connection.execute(
            "SELECT * FROM experiment_protocols WHERE protocol_id='fictional-prism-crossover' AND protocol_version='1.0.0'"
        ).fetchone()
        if row is None or row[2] != 4:
            raise E06ExperimentError("CANONICAL_PROTOCOL_UNAVAILABLE")
        try:
            return ExperimentProtocol(
                row[0],
                row[1],
                DesignTier(row[3]),
                row[4],
                row[5],
                row[6],
                row[7],
                row[8],
                row[9],
                row[10],
                row[11],
                row[12],
                row[13],
                row[14],
                row[15],
                row[16],
                row[17],
                row[18],
                row[19],
                row[20],
                row[21],
                row[22],
                row[23],
                row[24],
                row[25],
                row[26],
                row[27],
                row[28],
                row[29],
                dt.datetime.fromisoformat(row[30]),
                row[31],
            )
        except (TypeError, ValueError) as exc:
            raise E06ExperimentError("CANONICAL_PROTOCOL_INVALID") from exc

    def _canonical_intervention(self) -> InterventionDefinition:
        row = self.connection.execute(
            "SELECT * FROM intervention_definitions WHERE intervention_id=? AND intervention_version='1.0.0'",
            (FIXED_R1_ID,),
        ).fetchone()
        if row is None or row[2] != 4:
            raise E06ExperimentError("CANONICAL_INTERVENTION_UNAVAILABLE")
        try:
            definition = InterventionDefinition(
                row[0],
                row[1],
                row[3],
                (row[4],),
                row[5],
                bool(row[6]),
                row[7],
                row[8],
                row[9],
                row[10],
                row[11],
                row[12],
                ActionRiskTier(row[13]),
                row[14],
                row[15],
            )
        except (TypeError, ValueError) as exc:
            raise E06ExperimentError("CANONICAL_INTERVENTION_INVALID") from exc
        if not resolve_intervention(definition).allowed:
            raise E06ExperimentError("CANONICAL_INTERVENTION_DENIED")
        return definition

    def _canonical_records(self) -> tuple[PeriodRecord, ...]:
        rows = self.connection.execute(
            "SELECT period,scheduled_condition,actual_exposure,outcome_time,outcome_value,missingness,deviation_code,concurrent_change_code "
            "FROM experiment_period_records WHERE run_id=? ORDER BY period",
            (RUN_ID,),
        ).fetchall()
        try:
            return tuple(
                PeriodRecord(
                    row[0],
                    row[1],
                    row[2],
                    dt.datetime.fromisoformat(row[3]) if row[3] else None,
                    row[4],
                    MissingOutcome(row[5]),
                    row[6],
                    row[7],
                )
                for row in rows
            )
        except (TypeError, ValueError) as exc:
            raise E06ExperimentError("CANONICAL_EXECUTION_INVALID") from exc

    def _advance(self, choice: str) -> dict[str, int | str]:
        requested_period = int(choice.removeprefix("period_"))
        row = self.connection.execute(
            "SELECT preregistration_digest,assignment_digest,status FROM experiment_runs WHERE run_id=?",
            (RUN_ID,),
        ).fetchone()
        if row is None:
            raise E06ExperimentError("FIXTURE_NOT_LOADED")
        preregistration, expected_assignment, status = row
        if status != "active":
            raise E06ExperimentError("EXECUTION_FROZEN")
        protocol = self._canonical_protocol()
        if preregistration != protocol.digest:
            self._stop(StopReason.STALE_PROTOCOL)
            raise E06ExperimentError("STALE_PROTOCOL")
        if assignment_digest(seeded_assignments(protocol)) != expected_assignment:
            self._stop(StopReason.ASSIGNMENT_DRIFT)
            raise E06ExperimentError("ASSIGNMENT_DRIFT")
        executed = self.connection.execute(
            "SELECT COUNT(*) FROM experiment_period_records WHERE run_id=?", (RUN_ID,)
        ).fetchone()[0]
        if requested_period != executed + 1:
            raise E06ExperimentError("PERIOD_TRANSITION_OUT_OF_ORDER")
        record = fictional_records(protocol)[requested_period - 1]
        with self.connection:
            self.connection.execute(
                "INSERT INTO experiment_period_records VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    RUN_ID,
                    record.period,
                    4,
                    record.scheduled_condition,
                    record.actual_exposure,
                    record.outcome_time.isoformat() if record.outcome_time else None,
                    record.outcome,
                    record.missingness.value,
                    record.deviation,
                    record.concurrent_change,
                ),
            )
        return {
            "executed_period": requested_period,
            "remaining_periods": 8 - requested_period,
            "status": "active",
        }

    def _analyze(self) -> AnalysisResult:
        protocol = self._canonical_protocol()
        intervention = self._canonical_intervention()
        row = self.connection.execute(
            "SELECT preregistration_digest,assignment_digest,status,stop_reason FROM experiment_runs WHERE run_id=?",
            (RUN_ID,),
        ).fetchone()
        if row is None:
            raise E06ExperimentError("FIXTURE_NOT_LOADED")
        preregistration, expected_assignment, status, stop_reason = row
        if status != "active":
            raise E06ExperimentError(f"CLAIMS_FROZEN:{stop_reason}")
        if preregistration != protocol.digest:
            self._stop(StopReason.STALE_PROTOCOL)
            raise E06ExperimentError("STALE_PROTOCOL")
        try:
            return analyze_known_answer(
                protocol,
                intervention,
                self._canonical_records(),
                expected_assignment,
            )
        except ExperimentValidationError as exc:
            if "assignment drift" in str(exc):
                self._stop(StopReason.ASSIGNMENT_DRIFT)
            raise E06ExperimentError(str(exc)) from exc

    def _stop(self, reason: StopReason) -> dict[str, str | bool]:
        if reason is StopReason.NONE:
            raise E06ExperimentError("INVALID_STOP_REASON")
        with self.connection:
            updated = self.connection.execute(
                "UPDATE experiment_runs SET status='stopped',stop_reason=? WHERE run_id=? AND status='active'",
                (reason.value, RUN_ID),
            ).rowcount
        if updated != 1:
            raise E06ExperimentError("RUN_NOT_ACTIVE")
        return {
            "status": "stopped",
            "reason": reason.value,
            "assignment_blocked": True,
            "claims_blocked": True,
        }

    def _delete(self) -> dict[str, int | bool]:
        with self.connection:
            deleted = self.connection.execute(
                "DELETE FROM intervention_definitions WHERE intervention_id=? AND intervention_version='1.0.0'",
                (FIXED_R1_ID,),
            ).rowcount
        remaining = sum(
            self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "intervention_definitions",
                "experiment_protocols",
                "experiment_runs",
                "experiment_period_records",
            )
        )
        return {
            "interventions_deleted": deleted,
            "dependency_rows_remaining": remaining,
            "canonical_absence": remaining == 0,
        }
