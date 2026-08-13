"""Additive E06 V3-to-V4 schema delta."""

from __future__ import annotations

import hashlib
import sqlite3

from psyche_os.storage.e05_schema import V3_INVENTORY

V4_ADDED_TABLES: tuple[str, ...] = (
    "intervention_definitions",
    "experiment_protocols",
    "experiment_runs",
    "experiment_period_records",
)
V4_INVENTORY: tuple[str, ...] = V3_INVENTORY + V4_ADDED_TABLES

V4_MIGRATION_SQL = """
CREATE TABLE intervention_definitions (
 intervention_id TEXT NOT NULL CHECK(intervention_id='fictional-prism-card-position'),
 intervention_version TEXT NOT NULL CHECK(intervention_version='1.0.0'),
 schema_version INTEGER NOT NULL CHECK(schema_version=4),
 label TEXT NOT NULL CHECK(label='Fictional prism card position'),
 component TEXT NOT NULL CHECK(component='place one fictional prism card at the left or right marker'),
 delivery TEXT NOT NULL CHECK(delivery='self_directed_fixture_instruction'),
 reversible INTEGER NOT NULL CHECK(reversible=1),
 evidence_certainty TEXT NOT NULL CHECK(evidence_certainty='mechanics_fixture_only'),
 harms_boundary TEXT NOT NULL CHECK(harms_boundary='stop_on_any_unwanted_or_adverse_signal'),
 contraindication_boundary TEXT NOT NULL CHECK(contraindication_boundary='any_contraindication_blocks'),
 accessibility_equity TEXT NOT NULL CHECK(accessibility_equity='neutral_nonclinical_fixture'),
 rights_state TEXT NOT NULL CHECK(rights_state='repository_owned_fictional'),
 guideline_context TEXT NOT NULL CHECK(guideline_context='none_fixture_only'),
 risk_tier TEXT NOT NULL CHECK(risk_tier='R1_low_reversible'),
 review_state TEXT NOT NULL CHECK(review_state='fixture_allowlisted'),
 review_trigger TEXT NOT NULL CHECK(review_trigger='identity_component_or_risk_change'),
 PRIMARY KEY(intervention_id,intervention_version)
);
CREATE TRIGGER intervention_definitions_immutable BEFORE UPDATE ON intervention_definitions
BEGIN SELECT RAISE(ABORT,'intervention definitions are immutable; add a version'); END;
CREATE TABLE experiment_protocols (
 protocol_id TEXT NOT NULL CHECK(protocol_id='fictional-prism-crossover'),
 protocol_version TEXT NOT NULL CHECK(protocol_version='1.0.0'), schema_version INTEGER NOT NULL CHECK(schema_version=4),
 design_tier TEXT NOT NULL CHECK(design_tier='D3_randomized_crossover'),
 intervention_id TEXT NOT NULL, intervention_version TEXT NOT NULL,
 question TEXT NOT NULL, estimand TEXT NOT NULL, eligibility TEXT NOT NULL,
 condition_a TEXT NOT NULL CHECK(condition_a='A_left_marker'), condition_b TEXT NOT NULL CHECK(condition_b='B_right_marker'),
 outcome_name TEXT NOT NULL CHECK(outcome_name='fictional_prism_response'), measurement_version TEXT NOT NULL CHECK(measurement_version='fictional-scale-v1'),
 baseline_plan TEXT NOT NULL, phase_design TEXT NOT NULL,
 assignment_algorithm TEXT NOT NULL CHECK(assignment_algorithm='python_mt19937_balanced_shuffle'),
 assignment_version TEXT NOT NULL CHECK(assignment_version='python-random-v1'), seed INTEGER NOT NULL CHECK(seed=6062044),
 blinding_state TEXT NOT NULL, duration_periods INTEGER NOT NULL CHECK(duration_periods=8),
 washout_carryover TEXT NOT NULL, concurrent_change_plan TEXT NOT NULL, missingness_plan TEXT NOT NULL,
 autocorrelation_plan TEXT NOT NULL, multiplicity_family TEXT NOT NULL, minimum_information TEXT NOT NULL,
 stopping_rule TEXT NOT NULL, adverse_rule TEXT NOT NULL, analysis_version TEXT NOT NULL, analysis_config TEXT NOT NULL,
 preregistered_at TEXT NOT NULL, preregistration_digest TEXT NOT NULL CHECK(length(preregistration_digest)=64),
 PRIMARY KEY(protocol_id,protocol_version),
 FOREIGN KEY(intervention_id,intervention_version) REFERENCES intervention_definitions(intervention_id,intervention_version) ON DELETE CASCADE
);
CREATE TRIGGER experiment_protocols_immutable BEFORE UPDATE ON experiment_protocols
BEGIN SELECT RAISE(ABORT,'experiment protocols are immutable; add a version'); END;
CREATE TABLE experiment_runs (
 run_id TEXT PRIMARY KEY CHECK(run_id='fictional-prism-run-001'), schema_version INTEGER NOT NULL CHECK(schema_version=4),
 protocol_id TEXT NOT NULL, protocol_version TEXT NOT NULL, preregistration_digest TEXT NOT NULL,
 assignment_digest TEXT NOT NULL CHECK(length(assignment_digest)=64), status TEXT NOT NULL CHECK(status IN ('active','stopped')),
 stop_reason TEXT NOT NULL CHECK(stop_reason IN ('none','user_stop','adverse_signal','contraindication','eligibility_unavailable','stale_protocol','assignment_drift')),
 started_at TEXT NOT NULL,
 FOREIGN KEY(protocol_id,protocol_version) REFERENCES experiment_protocols(protocol_id,protocol_version) ON DELETE CASCADE,
 CHECK((status='active' AND stop_reason='none') OR (status='stopped' AND stop_reason!='none'))
);
CREATE TRIGGER experiment_runs_no_reactivation BEFORE UPDATE OF status ON experiment_runs
WHEN OLD.status='stopped' BEGIN SELECT RAISE(ABORT,'stopped experiment cannot reactivate'); END;
CREATE TABLE experiment_period_records (
 run_id TEXT NOT NULL, period INTEGER NOT NULL CHECK(period BETWEEN 1 AND 8), schema_version INTEGER NOT NULL CHECK(schema_version=4),
 scheduled_condition TEXT NOT NULL CHECK(scheduled_condition IN ('A_left_marker','B_right_marker')),
 actual_exposure TEXT CHECK(actual_exposure IN ('A_left_marker','B_right_marker')),
 outcome_time TEXT, outcome_value INTEGER CHECK(outcome_value BETWEEN 0 AND 10),
 missingness TEXT NOT NULL CHECK(missingness IN ('observed','declined','technical_failure','not_available')),
 deviation_code TEXT, concurrent_change_code TEXT,
 PRIMARY KEY(run_id,period), FOREIGN KEY(run_id) REFERENCES experiment_runs(run_id) ON DELETE CASCADE,
 CHECK((missingness='observed' AND outcome_time IS NOT NULL AND outcome_value IS NOT NULL) OR
       (missingness!='observed' AND outcome_time IS NULL AND outcome_value IS NULL))
);
CREATE TRIGGER experiment_period_records_immutable BEFORE UPDATE ON experiment_period_records
BEGIN SELECT RAISE(ABORT,'experiment period records are immutable'); END;
CREATE INDEX idx_experiment_period_records_run ON experiment_period_records(run_id,period);
"""


def _split(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete E06 migration SQL")
    return tuple(statements)


V4_MIGRATION_STATEMENTS = _split(V4_MIGRATION_SQL)
V4_MIGRATION_CHECKSUM = hashlib.sha256(
    (";\n".join(V4_MIGRATION_STATEMENTS) + ";").encode()
).hexdigest()
