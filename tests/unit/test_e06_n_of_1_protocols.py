"""Failure-driven E06 domain and policy proofs."""

from dataclasses import FrozenInstanceError, replace
import datetime as dt

import pytest

from psyche_os.application.e06_experiments import (
    FULL_EVIDENCE,
    fictional_intervention,
    fictional_protocol,
    fictional_records,
)
from psyche_os.domain.experiments import (
    ActionRiskTier,
    ClaimEvidence,
    ClaimLevel,
    DesignTier,
    ExperimentValidationError,
    MissingOutcome,
    PeriodRecord,
    ProtocolDecisionCode,
    RiskDecisionCode,
    analyze_known_answer,
    assignment_digest,
    resolve_claim,
    resolve_intervention,
    resolve_protocol,
    seeded_assignments,
    validate_claim_wording,
)


def evidence(level: ClaimLevel = ClaimLevel.C5_RANDOMIZED_SINGLE_CASE) -> ClaimEvidence:
    return ClaimEvidence(*((level,) * 7))


@pytest.mark.unit
@pytest.mark.parametrize(
    "field",
    (
        "question", "estimand", "outcome", "measurement_version", "phase_design",
        "missingness_plan", "stopping_rule", "adverse_rule", "analysis_config",
    ),
)
def test_incomplete_preregistration_is_rejected_before_write(field: str) -> None:
    with pytest.raises(ExperimentValidationError, match="incomplete"):
        replace(fictional_protocol(), **{field: ""})


@pytest.mark.unit
def test_preregistration_is_immutable_versioned_and_digest_bound() -> None:
    protocol = fictional_protocol()
    changed = replace(protocol, version="1.0.1", digest="")
    assert changed.digest != protocol.digest
    with pytest.raises(ExperimentValidationError, match="digest changed"):
        replace(protocol, question="changed question")
    with pytest.raises(FrozenInstanceError):
        protocol.question = "rewrite"  # type: ignore[misc]


@pytest.mark.unit
def test_protocol_approval_preregistration_and_intervention_allowlist_are_independent() -> None:
    protocol = fictional_protocol()
    assert resolve_protocol(
        protocol,
        active_digest=protocol.digest,
        eligibility_available=True,
        contraindication_present=False,
    ).code is ProtocolDecisionCode.APPROVED_FIXED_PROTOCOL
    assert resolve_protocol(
        protocol,
        active_digest="0" * 64,
        eligibility_available=True,
        contraindication_present=False,
    ).code is ProtocolDecisionCode.STALE_PREREGISTRATION
    assert resolve_protocol(
        protocol,
        active_digest=protocol.digest,
        eligibility_available=False,
        contraindication_present=False,
    ).code is ProtocolDecisionCode.ELIGIBILITY_UNAVAILABLE
    assert resolve_protocol(
        protocol,
        active_digest=protocol.digest,
        eligibility_available=True,
        contraindication_present=True,
    ).code is ProtocolDecisionCode.CONTRAINDICATION_PRESENT
    # Protocol approval does not make a separately denied intervention executable.
    assert not resolve_intervention(
        replace(fictional_intervention(), risk_tier=ActionRiskTier.R2_MODERATE_OR_SYMPTOM_TARGETING)
    ).allowed


@pytest.mark.unit
def test_seeded_assignment_is_exactly_reproducible_and_drift_fails() -> None:
    protocol = fictional_protocol()
    first = seeded_assignments(protocol)
    assert first == seeded_assignments(protocol)
    assert assignment_digest(first) == "5acbb52efebe1dea7ecb9ce9c7acce3112d2df055f4c14f242fe3e202b529546"
    with pytest.raises(ExperimentValidationError, match="drift"):
        seeded_assignments(replace(protocol, assignment_version="changed", digest=""))
    with pytest.raises(ExperimentValidationError, match="assignment drift"):
        analyze_known_answer(protocol, fictional_intervention(), fictional_records(protocol), "0" * 64, FULL_EVIDENCE)


@pytest.mark.unit
def test_risk_cannot_be_lowered_and_r2_r3_are_never_executable() -> None:
    fixed = fictional_intervention()
    r2 = replace(fixed, risk_tier=ActionRiskTier.R2_MODERATE_OR_SYMPTOM_TARGETING)
    r3 = replace(fixed, risk_tier=ActionRiskTier.R3_PROHIBITED_AUTONOMOUS)
    assert resolve_intervention(r2).code is RiskDecisionCode.QUALIFIED_REVIEW_REQUIRED
    assert resolve_intervention(r3).code is RiskDecisionCode.PROHIBITED_AUTONOMOUS
    assert not resolve_intervention(r2).allowed and not resolve_intervention(r3).allowed
    # User/model/imported labels have no authority; altered identity or component fails exact allowlisting.
    assert not resolve_intervention(replace(fixed, intervention_id="medication-alias")).allowed
    assert not resolve_intervention(replace(fixed, components=("substitute action",))).allowed
    assert not resolve_intervention(replace(fixed, label="renamed bypass")).allowed


@pytest.mark.unit
def test_claim_ceiling_uses_minimum_and_is_monotone_under_failures() -> None:
    strong = resolve_claim(
        DesignTier.D3_RANDOMIZED_CROSSOVER,
        ActionRiskTier.R1_LOW_REVERSIBLE,
        evidence(),
        ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL,
    )
    weak = resolve_claim(
        DesignTier.D3_RANDOMIZED_CROSSOVER,
        ActionRiskTier.R1_LOW_REVERSIBLE,
        replace(evidence(), coverage=ClaimLevel.C1_COOCCURRENCE),
        ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL,
    )
    prohibited = resolve_claim(
        DesignTier.D4_REPLICATED_SERIES,
        ActionRiskTier.R3_PROHIBITED_AUTONOMOUS,
        evidence(ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL),
        ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL,
    )
    assert strong.ceiling is ClaimLevel.C5_RANDOMIZED_SINGLE_CASE
    assert weak.ceiling is ClaimLevel.C1_COOCCURRENCE
    assert prohibited.ceiling is ClaimLevel.C0_OBSERVATION
    assert weak.ceiling <= strong.ceiling


@pytest.mark.unit
@pytest.mark.parametrize(
    ("field", "ceiling"),
    (
        ("measurement", ClaimLevel.C1_COOCCURRENCE),
        ("coverage", ClaimLevel.C1_COOCCURRENCE),
        ("missingness", ClaimLevel.C0_OBSERVATION),
        ("serial_dependence", ClaimLevel.C2_TEMPORAL_PRECEDENCE),
        ("carryover", ClaimLevel.C2_TEMPORAL_PRECEDENCE),
        ("replication", ClaimLevel.C2_TEMPORAL_PRECEDENCE),
        ("sensitivity", ClaimLevel.C1_COOCCURRENCE),
    ),
)
def test_each_missing_evidence_axis_lowers_claim(field: str, ceiling: ClaimLevel) -> None:
    decision = resolve_claim(
        DesignTier.D4_REPLICATED_SERIES,
        ActionRiskTier.R1_LOW_REVERSIBLE,
        replace(evidence(ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL), **{field: ceiling}),
        ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL,
    )
    assert decision.ceiling is ceiling


@pytest.mark.unit
def test_design_label_alone_and_d0_d1_effect_wording_never_authorize_causality() -> None:
    for design in (DesignTier.D0_TRACKING, DesignTier.D1_EXPLORATORY_AB):
        decision = resolve_claim(design, ActionRiskTier.R1_LOW_REVERSIBLE, evidence(), ClaimLevel.C5_RANDOMIZED_SINGLE_CASE)
        assert decision.ceiling <= ClaimLevel.C2_TEMPORAL_PRECEDENCE
        with pytest.raises(ExperimentValidationError, match="effect wording"):
            validate_claim_wording("the effect caused a change", design)
    with pytest.raises(ExperimentValidationError, match="clinical"):
        validate_claim_wording("this treatment predicts diagnosis", DesignTier.D3_RANDOMIZED_CROSSOVER)


@pytest.mark.unit
def test_missing_outcomes_are_not_imputed_or_recast_as_adherence() -> None:
    record = PeriodRecord(1, "A_left_marker", None, None, None, MissingOutcome.DECLINED)
    assert record.outcome is None and record.actual_exposure is None
    with pytest.raises(ExperimentValidationError, match="cannot be imputed"):
        replace(record, outcome=4, outcome_time=dt.datetime(2044, 6, 1, tzinfo=dt.UTC))
    result = analyze_known_answer(
        fictional_protocol(), fictional_intervention(), fictional_records(fictional_protocol()),
        assignment_digest(seeded_assignments(fictional_protocol())), FULL_EVIDENCE,
    )
    output = repr(result).casefold()
    assert result.coverage.as_tuple().exponent == -3
    assert all(term not in output for term in ("noncompliant", "shame", "streak", "engagement score", "p-value"))
    assert result.scope and result.window and result.cutoff and result.sensitivity_results and result.limitations
