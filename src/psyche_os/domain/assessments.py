"""Typed, content-free assessment registry governance for E04.

This module deliberately models metadata and gate decisions only.  It has no
item, response, scoring, norm, cutoff, administration, or interpretation
payload fields.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
import datetime
from enum import Enum


class AssessmentLifecycle(Enum):
    DRAFT = "draft"
    RIGHTS_PENDING = "rights_pending"
    VALIDATION_PENDING = "validation_pending"
    APPROVED_FOR_NAMED_USE = "approved_for_named_use"
    RESTRICTED = "restricted"
    DEPRECATED = "deprecated"
    REVOKED = "revoked"


class TranslationStatus(Enum):
    NOT_APPLICABLE = "not_applicable"
    AUTHORIZED_VALIDATED = "authorized_validated"
    UNVALIDATED_TRANSLATION = "unvalidated_translation"
    UNKNOWN = "unknown"


class ReviewState(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    NOT_APPLICABLE = "not_applicable"


class GateId(Enum):
    P0_IDENTITY_AND_USE = "P0_identity_and_use"
    P1_RIGHTS = "P1_rights"
    P2_VERSION_INTEGRITY = "P2_version_integrity"
    P3_LANGUAGE_TRANSLATION = "P3_language_translation"
    P4_MEASUREMENT_EVIDENCE = "P4_measurement_evidence"
    P5_SCORING_IMPLEMENTATION = "P5_scoring_implementation"
    P6_INTERPRETATION = "P6_interpretation"
    P7_MONITORING_AND_BURDEN = "P7_monitoring_and_burden"


GATE_ORDER = tuple(GateId)


class GateStatus(Enum):
    PASS = "pass"
    FAIL = "fail"
    NOT_EVALUATED = "not_evaluated"


class GateReasonCode(Enum):
    IDENTITY_COMPLETE = "identity_complete"
    IDENTITY_INCOMPLETE = "identity_incomplete"
    RIGHTS_GRANTED_FOR_NAMED_USE = "rights_granted_for_named_use"
    RIGHTS_MISSING_OR_DENIED = "rights_missing_or_denied"
    VERSION_INTEGRITY_UNRESOLVED = "version_integrity_unresolved"
    TRANSLATION_UNVALIDATED = "translation_unvalidated"
    MEASUREMENT_EVIDENCE_ABSENT = "measurement_evidence_absent"
    SCORING_IMPLEMENTATION_ABSENT = "scoring_implementation_absent"
    INTERPRETATION_EVIDENCE_ABSENT = "interpretation_evidence_absent"
    MONITORING_REVIEW_ABSENT = "monitoring_review_absent"
    EVIDENCE_REFERENCE_MISSING = "evidence_reference_missing"
    UPSTREAM_GATE_BLOCKED = "upstream_gate_blocked"


class GateOutcome(Enum):
    METADATA_ONLY = "metadata_only"
    RIGHTS_BLOCKED = "rights_blocked"
    VERSION_UNRESOLVED = "version_unresolved"
    UNVALIDATED_TRANSLATION = "unvalidated_translation"
    RESEARCH_ONLY = "research_only"
    SCORING_DISABLED = "scoring_disabled"
    INTERPRETATION_DISABLED = "interpretation_disabled"
    REPEATED_USE_DISABLED = "repeated_use_disabled"
    APPROVED_FOR_NAMED_USE = "approved_for_named_use"


class RightsDecision(Enum):
    ALLOW = "allow"
    DENY = "deny"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class RightsMatrix:
    view_items: RightsDecision = RightsDecision.UNKNOWN
    store_items: RightsDecision = RightsDecision.UNKNOWN
    collect_responses: RightsDecision = RightsDecision.UNKNOWN
    store_responses: RightsDecision = RightsDecision.UNKNOWN
    score_locally: RightsDecision = RightsDecision.UNKNOWN
    store_score: RightsDecision = RightsDecision.UNKNOWN
    display_interpretation: RightsDecision = RightsDecision.UNKNOWN
    use_norms_or_cutoffs: RightsDecision = RightsDecision.UNKNOWN
    translate_or_adapt: RightsDecision = RightsDecision.UNKNOWN
    export_content: RightsDecision = RightsDecision.UNKNOWN
    distribute_implementation: RightsDecision = RightsDecision.UNKNOWN
    use_in_research: RightsDecision = RightsDecision.UNKNOWN

    def decisions(self) -> tuple[tuple[str, RightsDecision], ...]:
        """Return all twelve independently governed decisions in stable order."""
        return tuple((item.name, getattr(self, item.name)) for item in fields(self))

    def all_allowed(self) -> bool:
        return all(decision is RightsDecision.ALLOW for _, decision in self.decisions())


@dataclass(frozen=True, slots=True)
class AssessmentIdentity:
    registry_id: str
    definition_version: str
    title: str
    owner: str
    construct: str
    intended_use: str
    target_population: str
    language: str
    locale: str
    administration_mode: str
    recall_period: str
    official_source_reference: str

    def is_complete(self) -> bool:
        return all(
            isinstance(getattr(self, item.name), str) and bool(getattr(self, item.name).strip())
            for item in fields(self)
        )


@dataclass(frozen=True, slots=True)
class GateRecord:
    gate_id: GateId
    status: GateStatus
    reason_code: GateReasonCode
    evidence_reference_ids: tuple[str, ...]
    review_state: ReviewState
    expires_on: str | None = None

    def __post_init__(self) -> None:
        if len(set(self.evidence_reference_ids)) != len(self.evidence_reference_ids):
            raise ValueError("duplicate evidence reference identifiers")
        if any(not value.strip() for value in self.evidence_reference_ids):
            raise ValueError("empty evidence reference identifier")
        if self.expires_on is not None:
            try:
                datetime.date.fromisoformat(self.expires_on)
            except ValueError as exc:
                raise ValueError("invalid gate expiry date") from exc


@dataclass(frozen=True, slots=True)
class AssessmentRegistryEntry:
    """Immutable, version-addressed assessment governance metadata."""

    identity: AssessmentIdentity
    rights: RightsMatrix
    translation_status: TranslationStatus
    lifecycle: AssessmentLifecycle
    review_owner: str
    review_state: ReviewState
    reviewed_on: str | None
    review_due: str | None
    supersedes_definition_version: str | None
    gates: tuple[GateRecord, ...]

    @property
    def registry_id(self) -> str:
        return self.identity.registry_id

    @property
    def definition_version(self) -> str:
        return self.identity.definition_version

    def __post_init__(self) -> None:
        for value, label in (
            (self.reviewed_on, "reviewed_on"),
            (self.review_due, "review_due"),
        ):
            if value is not None:
                try:
                    datetime.date.fromisoformat(value)
                except ValueError as exc:
                    raise ValueError(f"invalid {label} date") from exc
        gate_ids = tuple(record.gate_id for record in self.gates)
        if gate_ids != GATE_ORDER:
            raise ValueError("gate records must contain P0-P7 exactly once in order")
        if self.supersedes_definition_version == self.definition_version:
            raise ValueError("a definition version cannot supersede itself")


@dataclass(frozen=True, slots=True)
class CapabilityDecision:
    capability: str
    allowed: bool
    reason_code: str


@dataclass(frozen=True, slots=True)
class AssessmentStatus:
    registry_id: str
    definition_version: str
    outcome: GateOutcome
    evaluated_gates: tuple[GateRecord, ...]
    rights: RightsMatrix
    capabilities: tuple[CapabilityDecision, ...]
    scientific_claims_enabled: bool = False

    def capability(self, name: str) -> CapabilityDecision:
        for decision in self.capabilities:
            if decision.capability == name:
                return decision
        raise KeyError(name)


_FAIL_OUTCOMES = {
    GateId.P0_IDENTITY_AND_USE: GateOutcome.METADATA_ONLY,
    GateId.P1_RIGHTS: GateOutcome.RIGHTS_BLOCKED,
    GateId.P2_VERSION_INTEGRITY: GateOutcome.VERSION_UNRESOLVED,
    GateId.P3_LANGUAGE_TRANSLATION: GateOutcome.UNVALIDATED_TRANSLATION,
    GateId.P4_MEASUREMENT_EVIDENCE: GateOutcome.RESEARCH_ONLY,
    GateId.P5_SCORING_IMPLEMENTATION: GateOutcome.SCORING_DISABLED,
    GateId.P6_INTERPRETATION: GateOutcome.INTERPRETATION_DISABLED,
    GateId.P7_MONITORING_AND_BURDEN: GateOutcome.REPEATED_USE_DISABLED,
}


class AssessmentGateEvaluator:
    """Deterministically evaluate P0-P7; unknown and incomplete fail closed."""

    def evaluate(self, entry: AssessmentRegistryEntry) -> AssessmentStatus:
        source = {record.gate_id: record for record in entry.gates}
        evaluated: list[GateRecord] = []
        failed_gate: GateId | None = None

        for gate_id in GATE_ORDER:
            supplied = source[gate_id]
            if failed_gate is not None:
                evaluated.append(
                    GateRecord(
                        gate_id=gate_id,
                        status=GateStatus.NOT_EVALUATED,
                        reason_code=GateReasonCode.UPSTREAM_GATE_BLOCKED,
                        evidence_reference_ids=(),
                        review_state=ReviewState.NOT_APPLICABLE,
                    )
                )
                continue

            current = supplied
            if gate_id is GateId.P0_IDENTITY_AND_USE and not entry.identity.is_complete():
                current = GateRecord(
                    gate_id=gate_id,
                    status=GateStatus.FAIL,
                    reason_code=GateReasonCode.IDENTITY_INCOMPLETE,
                    evidence_reference_ids=(),
                    review_state=ReviewState.REJECTED,
                )
            elif gate_id is GateId.P1_RIGHTS and not entry.rights.all_allowed():
                current = GateRecord(
                    gate_id=gate_id,
                    status=GateStatus.FAIL,
                    reason_code=GateReasonCode.RIGHTS_MISSING_OR_DENIED,
                    evidence_reference_ids=supplied.evidence_reference_ids,
                    review_state=supplied.review_state,
                    expires_on=supplied.expires_on,
                )
            elif supplied.status is GateStatus.PASS and (
                not supplied.evidence_reference_ids
                or supplied.review_state is not ReviewState.APPROVED
            ):
                current = GateRecord(
                    gate_id=gate_id,
                    status=GateStatus.FAIL,
                    reason_code=GateReasonCode.EVIDENCE_REFERENCE_MISSING,
                    evidence_reference_ids=supplied.evidence_reference_ids,
                    review_state=supplied.review_state,
                    expires_on=supplied.expires_on,
                )

            evaluated.append(current)
            if current.status is not GateStatus.PASS:
                failed_gate = gate_id

        outcome = (
            _FAIL_OUTCOMES[failed_gate]
            if failed_gate is not None
            else GateOutcome.APPROVED_FOR_NAMED_USE
        )
        p1_passed = evaluated[1].status is GateStatus.PASS
        capabilities = tuple(
            CapabilityDecision(
                capability=name,
                allowed=p1_passed and decision is RightsDecision.ALLOW,
                reason_code=(
                    "rights_granted_for_named_use"
                    if p1_passed and decision is RightsDecision.ALLOW
                    else "rights_gate_blocked"
                ),
            )
            for name, decision in entry.rights.decisions()
        )
        return AssessmentStatus(
            registry_id=entry.registry_id,
            definition_version=entry.definition_version,
            outcome=outcome,
            evaluated_gates=tuple(evaluated),
            rights=entry.rights,
            capabilities=capabilities,
            scientific_claims_enabled=False,
        )
