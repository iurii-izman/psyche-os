"""Closed E06 N-of-1 protocol, action-policy, and claim contracts."""

from __future__ import annotations

from dataclasses import dataclass, fields
import datetime as dt
from decimal import Decimal
from enum import IntEnum, StrEnum
import hashlib
import json


class ExperimentValidationError(ValueError):
    """E06 state is incomplete, stale, contradictory, or outside authority."""


class DesignTier(StrEnum):
    D0_TRACKING = "D0_tracking"
    D1_EXPLORATORY_AB = "D1_exploratory_AB"
    D2_REPEATED_PHASE = "D2_repeated_phase"
    D3_RANDOMIZED_CROSSOVER = "D3_randomized_crossover"
    D4_REPLICATED_SERIES = "D4_replicated_series"


class ActionRiskTier(StrEnum):
    R0_OBSERVATIONAL = "R0_observational"
    R1_LOW_REVERSIBLE = "R1_low_reversible"
    R2_MODERATE_OR_SYMPTOM_TARGETING = "R2_moderate_or_symptom_targeting"
    R3_PROHIBITED_AUTONOMOUS = "R3_prohibited_autonomous"


class ClaimLevel(IntEnum):
    C0_OBSERVATION = 0
    C1_COOCCURRENCE = 1
    C2_TEMPORAL_PRECEDENCE = 2
    C3_REPLICATED_WITHIN_PERSON_ASSOCIATION = 3
    C4_QUASI_EXPERIMENTAL = 4
    C5_RANDOMIZED_SINGLE_CASE = 5
    C6_REPLICATED_N_OF_1_OR_TRIAL = 6


class RiskDecisionCode(StrEnum):
    ALLOWED_OBSERVATIONAL = "allowed_observational"
    ALLOWED_FIXED_LOW_REVERSIBLE = "allowed_fixed_low_reversible"
    QUALIFIED_REVIEW_REQUIRED = "qualified_review_required"
    PROHIBITED_AUTONOMOUS = "prohibited_autonomous"
    IDENTITY_NOT_ALLOWLISTED = "identity_not_allowlisted"


class ProtocolDecisionCode(StrEnum):
    APPROVED_FIXED_PROTOCOL = "approved_fixed_protocol"
    IDENTITY_NOT_APPROVED = "identity_not_approved"
    STALE_PREREGISTRATION = "stale_preregistration"
    ELIGIBILITY_UNAVAILABLE = "eligibility_unavailable"
    CONTRAINDICATION_PRESENT = "contraindication_present"


class RunStatus(StrEnum):
    PREREGISTERED = "preregistered"
    ACTIVE = "active"
    STOPPED = "stopped"


class StopReason(StrEnum):
    NONE = "none"
    USER_STOP = "user_stop"
    ADVERSE_SIGNAL = "adverse_signal"
    CONTRAINDICATION = "contraindication"
    ELIGIBILITY_UNAVAILABLE = "eligibility_unavailable"
    STALE_PROTOCOL = "stale_protocol"
    ASSIGNMENT_DRIFT = "assignment_drift"


class MissingOutcome(StrEnum):
    OBSERVED = "observed"
    DECLINED = "declined"
    TECHNICAL_FAILURE = "technical_failure"
    NOT_AVAILABLE = "not_available"


@dataclass(frozen=True, slots=True)
class InterventionDefinition:
    intervention_id: str
    version: str
    label: str
    components: tuple[str, ...]
    delivery: str
    reversible: bool
    evidence_certainty: str
    harms_boundary: str
    contraindication_boundary: str
    accessibility_equity: str
    rights_state: str
    guideline_context: str
    risk_tier: ActionRiskTier
    review_state: str
    review_trigger: str

    def __post_init__(self) -> None:
        if any(
            not str(getattr(self, f.name)).strip()
            for f in fields(self)
            if f.name not in {"components", "reversible", "risk_tier"}
        ):
            raise ExperimentValidationError("intervention metadata must be complete")
        if not self.components or any(not item.strip() for item in self.components):
            raise ExperimentValidationError("intervention components must be explicit")


FIXED_R0_ID = "fictional-prism-observation"
FIXED_R1_ID = "fictional-prism-card-position"


@dataclass(frozen=True, slots=True)
class RiskDecision:
    allowed: bool
    tier: ActionRiskTier
    code: RiskDecisionCode


def resolve_intervention(definition: InterventionDefinition) -> RiskDecision:
    """Fail closed by exact immutable identity; labels and aliases have no authority."""
    if definition.risk_tier is ActionRiskTier.R3_PROHIBITED_AUTONOMOUS:
        return RiskDecision(False, definition.risk_tier, RiskDecisionCode.PROHIBITED_AUTONOMOUS)
    if definition.risk_tier is ActionRiskTier.R2_MODERATE_OR_SYMPTOM_TARGETING:
        return RiskDecision(False, definition.risk_tier, RiskDecisionCode.QUALIFIED_REVIEW_REQUIRED)
    if definition.risk_tier is ActionRiskTier.R0_OBSERVATIONAL:
        allowed = (
            definition.intervention_id == FIXED_R0_ID
            and definition.version == "1.0.0"
            and definition.label == "Fictional prism observation"
            and definition.components == ("observe the fictional prism marker without changing it",)
            and definition.delivery == "fixture_observation_only"
            and definition.reversible
            and definition.evidence_certainty == "mechanics_fixture_only"
            and definition.harms_boundary == "stop_on_any_unwanted_or_adverse_signal"
            and definition.contraindication_boundary == "any_contraindication_blocks"
            and definition.accessibility_equity == "neutral_nonclinical_fixture"
            and definition.rights_state == "repository_owned_fictional"
            and definition.guideline_context == "none_fixture_only"
            and definition.review_state == "fixture_observational_allowlisted"
            and definition.review_trigger == "identity_component_or_risk_change"
        )
        return RiskDecision(
            allowed,
            definition.risk_tier,
            RiskDecisionCode.ALLOWED_OBSERVATIONAL
            if allowed
            else RiskDecisionCode.IDENTITY_NOT_ALLOWLISTED,
        )
    allowed = (
        definition.intervention_id == FIXED_R1_ID
        and definition.version == "1.0.0"
        and definition.label == "Fictional prism card position"
        and definition.components == ("place one fictional prism card at the left or right marker",)
        and definition.delivery == "self_directed_fixture_instruction"
        and definition.reversible
        and definition.evidence_certainty == "mechanics_fixture_only"
        and definition.harms_boundary == "stop_on_any_unwanted_or_adverse_signal"
        and definition.contraindication_boundary == "any_contraindication_blocks"
        and definition.accessibility_equity == "neutral_nonclinical_fixture"
        and definition.rights_state == "repository_owned_fictional"
        and definition.guideline_context == "none_fixture_only"
        and definition.review_state == "fixture_allowlisted"
        and definition.review_trigger == "identity_component_or_risk_change"
    )
    return RiskDecision(
        allowed,
        definition.risk_tier,
        RiskDecisionCode.ALLOWED_FIXED_LOW_REVERSIBLE
        if allowed
        else RiskDecisionCode.IDENTITY_NOT_ALLOWLISTED,
    )


@dataclass(frozen=True, slots=True)
class ExperimentProtocol:
    protocol_id: str
    version: str
    design_tier: DesignTier
    intervention_id: str
    intervention_version: str
    question: str
    estimand: str
    eligibility: str
    condition_a: str
    condition_b: str
    outcome: str
    measurement_version: str
    baseline_plan: str
    phase_design: str
    assignment_algorithm: str
    assignment_version: str
    seed: int
    blinding_state: str
    duration_periods: int
    washout_carryover: str
    concurrent_change_plan: str
    missingness_plan: str
    autocorrelation_plan: str
    multiplicity_family: str
    minimum_information: str
    stopping_rule: str
    adverse_rule: str
    analysis_version: str
    analysis_config: str
    preregistered_at: dt.datetime
    digest: str = ""

    def __post_init__(self) -> None:
        textual = tuple(
            getattr(self, f.name)
            for f in fields(self)
            if f.name
            not in {"design_tier", "seed", "duration_periods", "preregistered_at", "digest"}
        )
        if any(not isinstance(value, str) or not value.strip() for value in textual):
            raise ExperimentValidationError("preregistration is incomplete")
        if self.preregistered_at.tzinfo is None or self.preregistered_at.utcoffset() is None:
            raise ExperimentValidationError("preregistration time must be aware")
        if self.duration_periods != 8 or self.seed != 6062044:
            raise ExperimentValidationError("only the pinned fictional schedule is authorized")
        computed = self.compute_digest()
        if self.digest and self.digest != computed:
            raise ExperimentValidationError("preregistration digest changed")
        object.__setattr__(self, "digest", computed)

    def canonical(self) -> dict[str, str | int]:
        return {
            f.name: (
                value.value
                if isinstance(value, StrEnum)
                else value.isoformat()
                if isinstance(value, dt.datetime)
                else value
            )
            for f in fields(self)
            if f.name != "digest"
            for value in (getattr(self, f.name),)
        }

    def compute_digest(self) -> str:
        encoded = json.dumps(self.canonical(), sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class Assignment:
    period: int
    condition: str


def seeded_assignments(protocol: ExperimentProtocol) -> tuple[Assignment, ...]:
    if (
        protocol.assignment_algorithm != "psyche_sha256_balanced_rank"
        or protocol.assignment_version != "sha256-rank-v1"
    ):
        raise ExperimentValidationError("assignment algorithm/config drift")
    # Fully specified PSYCHE OS algorithm: rank period numbers by the unsigned
    # SHA-256 digest of this exact ASCII payload, assign the first half A and
    # the second half B, then return records in period order. No runtime RNG
    # implementation participates in historical reproduction.
    ranked = sorted(
        range(1, protocol.duration_periods + 1),
        key=lambda period: hashlib.sha256(
            f"psyche-os-e06-assignment-v1:{protocol.seed}:{period}".encode("ascii")
        ).digest(),
    )
    a_periods = frozenset(ranked[: protocol.duration_periods // 2])
    return tuple(
        Assignment(
            period,
            protocol.condition_a if period in a_periods else protocol.condition_b,
        )
        for period in range(1, protocol.duration_periods + 1)
    )


def assignment_digest(assignments: tuple[Assignment, ...]) -> str:
    payload = "|".join(f"{item.period}:{item.condition}" for item in assignments)
    return hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class ProtocolDecision:
    allowed: bool
    code: ProtocolDecisionCode


def resolve_protocol(
    protocol: ExperimentProtocol,
    *,
    active_digest: str,
    eligibility_available: bool,
    contraindication_present: bool,
) -> ProtocolDecision:
    """Approve protocol identity independently of intervention allowlisting."""
    if protocol.protocol_id != "fictional-prism-crossover" or protocol.version != "1.0.0":
        return ProtocolDecision(False, ProtocolDecisionCode.IDENTITY_NOT_APPROVED)
    if active_digest != protocol.digest:
        return ProtocolDecision(False, ProtocolDecisionCode.STALE_PREREGISTRATION)
    if not eligibility_available:
        return ProtocolDecision(False, ProtocolDecisionCode.ELIGIBILITY_UNAVAILABLE)
    if contraindication_present:
        return ProtocolDecision(False, ProtocolDecisionCode.CONTRAINDICATION_PRESENT)
    return ProtocolDecision(True, ProtocolDecisionCode.APPROVED_FIXED_PROTOCOL)


@dataclass(frozen=True, slots=True)
class ClaimEvidence:
    measurement: ClaimLevel
    coverage: ClaimLevel
    missingness: ClaimLevel
    serial_dependence: ClaimLevel
    carryover: ClaimLevel
    replication: ClaimLevel
    sensitivity: ClaimLevel


@dataclass(frozen=True, slots=True)
class ClaimDecision:
    supported_ceiling: ClaimLevel
    requested_level: ClaimLevel
    allowed: bool
    denial_reasons: tuple[str, ...]
    emitted_level: ClaimLevel | None
    wording: str | None


DESIGN_CEILING = {
    DesignTier.D0_TRACKING: ClaimLevel.C2_TEMPORAL_PRECEDENCE,
    DesignTier.D1_EXPLORATORY_AB: ClaimLevel.C2_TEMPORAL_PRECEDENCE,
    DesignTier.D2_REPEATED_PHASE: ClaimLevel.C4_QUASI_EXPERIMENTAL,
    DesignTier.D3_RANDOMIZED_CROSSOVER: ClaimLevel.C5_RANDOMIZED_SINGLE_CASE,
    DesignTier.D4_REPLICATED_SERIES: ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL,
}

CLAIM_WORDING = {
    ClaimLevel.C0_OBSERVATION: "observed in the named fictional protocol",
    ClaimLevel.C1_COOCCURRENCE: "co-occurred in the named fictional window",
    ClaimLevel.C2_TEMPORAL_PRECEDENCE: "preceded the outcome and may be a bounded signal",
    ClaimLevel.C3_REPLICATED_WITHIN_PERSON_ASSOCIATION: "stable within-protocol association under the named checks",
    ClaimLevel.C4_QUASI_EXPERIMENTAL: "compatible with an effect under the explicit assumptions",
    ClaimLevel.C5_RANDOMIZED_SINGLE_CASE: "individual effect estimate in this fictional randomized design",
    ClaimLevel.C6_REPLICATED_N_OF_1_OR_TRIAL: "effect supported only in the named replicated design scope",
}


RISK_CEILING = {
    ActionRiskTier.R0_OBSERVATIONAL: ClaimLevel.C2_TEMPORAL_PRECEDENCE,
    ActionRiskTier.R1_LOW_REVERSIBLE: ClaimLevel.C5_RANDOMIZED_SINGLE_CASE,
    ActionRiskTier.R2_MODERATE_OR_SYMPTOM_TARGETING: ClaimLevel.C0_OBSERVATION,
    ActionRiskTier.R3_PROHIBITED_AUTONOMOUS: ClaimLevel.C0_OBSERVATION,
}


def resolve_claim(
    design: DesignTier, risk: ActionRiskTier, evidence: ClaimEvidence, requested: ClaimLevel
) -> ClaimDecision:
    named = {
        "design": DESIGN_CEILING[design],
        "intervention_risk": RISK_CEILING[risk],
        **{f.name: getattr(evidence, f.name) for f in fields(evidence)},
    }
    supported_ceiling = min(named.values())
    limiting_reasons = tuple(
        f"{name}_ceiling={value.name}"
        for name, value in named.items()
        if value == supported_ceiling
    )
    if requested > supported_ceiling:
        return ClaimDecision(
            supported_ceiling,
            requested,
            False,
            (*limiting_reasons, f"requested_{requested.name}_denied"),
            None,
            None,
        )
    return ClaimDecision(
        supported_ceiling,
        requested,
        True,
        (),
        requested,
        CLAIM_WORDING[requested],
    )


PROHIBITED_OUTPUT = (
    "diagnos",
    "treatment",
    "should take",
    "should stop",
    "universal cause",
    "predicts",
    "noncompliant",
    "poor adherence",
    "shame",
    "streak",
    "urgency",
    "engagement score",
)


def validate_claim_wording(text: str, design: DesignTier) -> None:
    lowered = text.casefold()
    if any(term in lowered for term in PROHIBITED_OUTPUT):
        raise ExperimentValidationError("clinical, action, or manipulative wording denied")
    if design in {DesignTier.D0_TRACKING, DesignTier.D1_EXPLORATORY_AB} and any(
        term in lowered for term in ("effect", "caused", "causal")
    ):
        raise ExperimentValidationError("D0/D1 effect wording denied")


@dataclass(frozen=True, slots=True)
class PeriodRecord:
    period: int
    scheduled_condition: str
    actual_exposure: str | None
    outcome_time: dt.datetime | None
    outcome: int | None
    missingness: MissingOutcome
    deviation: str | None = None
    concurrent_change: str | None = None

    def __post_init__(self) -> None:
        if self.missingness is MissingOutcome.OBSERVED:
            if self.outcome is None or self.outcome_time is None or not 0 <= self.outcome <= 10:
                raise ExperimentValidationError("observed outcome is incomplete")
        elif self.outcome is not None or self.outcome_time is not None:
            raise ExperimentValidationError("missing outcomes cannot be imputed")


@dataclass(frozen=True, slots=True)
class EvidenceEvaluation:
    evidence: ClaimEvidence
    coverage: Decimal
    sensitivity_results: tuple[str, ...]


def _contrast(records: tuple[PeriodRecord, ...], protocol: ExperimentProtocol) -> Decimal | None:
    observed = tuple(record for record in records if record.missingness is MissingOutcome.OBSERVED)
    a_values = tuple(
        record.outcome
        for record in observed
        if record.scheduled_condition == protocol.condition_a and record.outcome is not None
    )
    b_values = tuple(
        record.outcome
        for record in observed
        if record.scheduled_condition == protocol.condition_b and record.outcome is not None
    )
    if not a_values or not b_values:
        return None
    return Decimal(sum(b_values)) / Decimal(len(b_values)) - Decimal(sum(a_values)) / Decimal(
        len(a_values)
    )


def evaluate_evidence(
    protocol: ExperimentProtocol,
    records: tuple[PeriodRecord, ...],
    *,
    assignment_integrity: bool,
) -> EvidenceEvaluation:
    """Derive the seven frozen fixture axes from protocol and execution state."""
    observed = tuple(record for record in records if record.missingness is MissingOutcome.OBSERVED)
    coverage = Decimal(len(observed)) / Decimal(protocol.duration_periods)
    missing = tuple(
        record for record in records if record.missingness is not MissingOutcome.OBSERVED
    )
    counts = {
        condition: sum(record.scheduled_condition == condition for record in observed)
        for condition in (protocol.condition_a, protocol.condition_b)
    }
    base_contrast = _contrast(records, protocol)
    leave_one_out = tuple(
        contrast
        for index in range(len(records))
        if (contrast := _contrast(records[:index] + records[index + 1 :], protocol)) is not None
    )
    sensitivity_ok = (
        base_contrast is not None
        and base_contrast != 0
        and len(leave_one_out) == len(records)
        and all((contrast > 0) == (base_contrast > 0) for contrast in leave_one_out)
    )
    sensitivity_results = (
        "leave-one-period-out preserves contrast direction"
        if sensitivity_ok
        else "leave-one-period-out sensitivity failed",
        "no missing outcome imputation",
    )
    high = ClaimLevel.C5_RANDOMIZED_SINGLE_CASE
    low = ClaimLevel.C2_TEMPORAL_PRECEDENCE
    evidence = ClaimEvidence(
        measurement=(
            high
            if protocol.measurement_version == "fictional-scale-v1"
            else ClaimLevel.C1_COOCCURRENCE
        ),
        coverage=(high if coverage >= Decimal("0.875") else low),
        missingness=(
            high
            if len(missing) <= 1
            and all(record.missingness is MissingOutcome.TECHNICAL_FAILURE for record in missing)
            else low
        ),
        serial_dependence=(
            high
            if protocol.autocorrelation_plan
            == "report lag-one contrast and leave-one-period-out sensitivity"
            else low
        ),
        carryover=(
            high
            if protocol.washout_carryover
            == "each period is independent by construction; lag-one sensitivity is required"
            else low
        ),
        replication=(
            high
            if assignment_integrity
            and counts[protocol.condition_a] >= 3
            and counts[protocol.condition_b] >= 3
            else ClaimLevel.C1_COOCCURRENCE
        ),
        sensitivity=(high if sensitivity_ok else low),
    )
    return EvidenceEvaluation(evidence, coverage, sensitivity_results)


@dataclass(frozen=True, slots=True)
class AnalysisResult:
    scope: str
    window: str
    cutoff: dt.datetime
    protocol_version: str
    preregistration_digest: str
    intervention_version: str
    measurement_version: str
    assignment_version: str
    assignment_digest: str
    analysis_version: str
    included_periods: tuple[int, ...]
    excluded_periods: tuple[int, ...]
    coverage: Decimal
    missingness: tuple[tuple[MissingOutcome, int], ...]
    mean_a: Decimal
    mean_b: Decimal
    contrast_b_minus_a: Decimal
    serial_method: str
    carryover_assumption: str
    multiplicity_family: str
    sensitivity_results: tuple[str, ...]
    claim: ClaimDecision
    limitations: tuple[str, ...]


def analyze_known_answer(
    protocol: ExperimentProtocol,
    intervention: InterventionDefinition,
    records: tuple[PeriodRecord, ...],
    expected_assignment_digest: str,
    requested_level: ClaimLevel = ClaimLevel.C5_RANDOMIZED_SINGLE_CASE,
) -> AnalysisResult:
    assignments = seeded_assignments(protocol)
    actual_digest = assignment_digest(assignments)
    if actual_digest != expected_assignment_digest:
        raise ExperimentValidationError("assignment drift blocks analysis")
    if len(records) != 8 or any(
        r.period != a.period or r.scheduled_condition != a.condition
        for r, a in zip(records, assignments, strict=True)
    ):
        raise ExperimentValidationError("scheduled assignment mismatch")
    evaluation = evaluate_evidence(protocol, records, assignment_integrity=True)
    observed = tuple(r for r in records if r.missingness is MissingOutcome.OBSERVED)
    a_values = tuple(
        r.outcome
        for r in observed
        if r.scheduled_condition == protocol.condition_a and r.outcome is not None
    )
    b_values = tuple(
        r.outcome
        for r in observed
        if r.scheduled_condition == protocol.condition_b and r.outcome is not None
    )
    if not a_values or not b_values:
        raise ExperimentValidationError("minimum information unavailable")
    mean_a = Decimal(sum(a_values)) / Decimal(len(a_values))
    mean_b = Decimal(sum(b_values)) / Decimal(len(b_values))
    claim = resolve_claim(
        protocol.design_tier, intervention.risk_tier, evaluation.evidence, requested_level
    )
    return AnalysisResult(
        "single repository-owned fictional prism run",
        "2044-06-01/2044-06-09",
        dt.datetime(2044, 6, 9, tzinfo=dt.UTC),
        protocol.version,
        protocol.digest,
        intervention.version,
        protocol.measurement_version,
        protocol.assignment_version,
        actual_digest,
        protocol.analysis_version,
        tuple(r.period for r in observed),
        tuple(r.period for r in records if r not in observed),
        evaluation.coverage,
        tuple((state, sum(r.missingness is state for r in records)) for state in MissingOutcome),
        mean_a,
        mean_b,
        mean_b - mean_a,
        protocol.autocorrelation_plan,
        protocol.washout_carryover,
        protocol.multiplicity_family,
        evaluation.sensitivity_results,
        claim,
        (
            "Synthetic mechanics fixture only.",
            "No inference extends beyond this named fictional run.",
            "Statistical magnitude does not authorize an action.",
        ),
    )
