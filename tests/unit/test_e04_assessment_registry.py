"""E04 failure-driven tests for the typed assessment governance model."""

from dataclasses import FrozenInstanceError, replace

import pytest

from psyche_os.domain.assessments import (
    AssessmentGateEvaluator,
    AssessmentIdentity,
    AssessmentLifecycle,
    AssessmentRegistryEntry,
    GateId,
    GateOutcome,
    GateReasonCode,
    GateRecord,
    GateStatus,
    ReviewState,
    RightsDecision,
    RightsMatrix,
    TranslationStatus,
)
from psyche_os.knowledge import AssessmentRegistry

FAIL_REASONS = {
    GateId.P0_IDENTITY_AND_USE: GateReasonCode.IDENTITY_INCOMPLETE,
    GateId.P1_RIGHTS: GateReasonCode.RIGHTS_MISSING_OR_DENIED,
    GateId.P2_VERSION_INTEGRITY: GateReasonCode.VERSION_INTEGRITY_UNRESOLVED,
    GateId.P3_LANGUAGE_TRANSLATION: GateReasonCode.TRANSLATION_UNVALIDATED,
    GateId.P4_MEASUREMENT_EVIDENCE: GateReasonCode.MEASUREMENT_EVIDENCE_ABSENT,
    GateId.P5_SCORING_IMPLEMENTATION: GateReasonCode.SCORING_IMPLEMENTATION_ABSENT,
    GateId.P6_INTERPRETATION: GateReasonCode.INTERPRETATION_EVIDENCE_ABSENT,
    GateId.P7_MONITORING_AND_BURDEN: GateReasonCode.MONITORING_REVIEW_ABSENT,
}


def _all_rights(decision: RightsDecision = RightsDecision.ALLOW) -> RightsMatrix:
    return RightsMatrix(**{name: decision for name, _ in RightsMatrix().decisions()})


def _entry_failing_at(gate_to_fail: GateId) -> AssessmentRegistryEntry:
    records: list[GateRecord] = []
    failed = False
    for gate_id in GateId:
        if failed:
            records.append(
                GateRecord(
                    gate_id,
                    GateStatus.NOT_EVALUATED,
                    GateReasonCode.UPSTREAM_GATE_BLOCKED,
                    (),
                    ReviewState.NOT_APPLICABLE,
                )
            )
        elif gate_id is gate_to_fail:
            records.append(
                GateRecord(
                    gate_id,
                    GateStatus.FAIL,
                    FAIL_REASONS[gate_id],
                    (),
                    ReviewState.PENDING,
                )
            )
            failed = True
        else:
            records.append(
                GateRecord(
                    gate_id,
                    GateStatus.PASS,
                    GateReasonCode.IDENTITY_COMPLETE,
                    (f"fictional_evidence_{gate_id.value}",),
                    ReviewState.APPROVED,
                )
            )

    identity = AssessmentIdentity(
        registry_id="fictional_gate_test",
        definition_version="1.0.0-metadata",
        title="Fictional Gate Test Metadata",
        owner="synthetic fixture package",
        construct="fictional registry behavior",
        intended_use="software verification only",
        target_population="fictional synthetic context",
        language="zxx",
        locale="und",
        administration_mode="not_available",
        recall_period="not_applicable",
        official_source_reference="package:psyche_os.synthetic.unit",
    )
    if gate_to_fail is GateId.P0_IDENTITY_AND_USE:
        identity = replace(identity, definition_version="")

    return AssessmentRegistryEntry(
        identity=identity,
        rights=(RightsMatrix() if gate_to_fail is GateId.P1_RIGHTS else _all_rights()),
        translation_status=(
            TranslationStatus.UNVALIDATED_TRANSLATION
            if gate_to_fail is GateId.P3_LANGUAGE_TRANSLATION
            else TranslationStatus.AUTHORIZED_VALIDATED
        ),
        lifecycle=AssessmentLifecycle.VALIDATION_PENDING,
        review_owner="fictional_reviewer_role",
        review_state=ReviewState.PENDING,
        reviewed_on=None,
        review_due=None,
        supersedes_definition_version=None,
        gates=tuple(records),
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    ("gate_id", "outcome"),
    [
        (GateId.P0_IDENTITY_AND_USE, GateOutcome.METADATA_ONLY),
        (GateId.P1_RIGHTS, GateOutcome.RIGHTS_BLOCKED),
        (GateId.P2_VERSION_INTEGRITY, GateOutcome.VERSION_UNRESOLVED),
        (GateId.P3_LANGUAGE_TRANSLATION, GateOutcome.UNVALIDATED_TRANSLATION),
        (GateId.P4_MEASUREMENT_EVIDENCE, GateOutcome.RESEARCH_ONLY),
        (GateId.P5_SCORING_IMPLEMENTATION, GateOutcome.SCORING_DISABLED),
        (GateId.P6_INTERPRETATION, GateOutcome.INTERPRETATION_DISABLED),
        (GateId.P7_MONITORING_AND_BURDEN, GateOutcome.REPEATED_USE_DISABLED),
    ],
)
def test_each_gate_failure_has_exact_fail_closed_outcome(
    gate_id: GateId, outcome: GateOutcome
) -> None:
    status = AssessmentGateEvaluator().evaluate(_entry_failing_at(gate_id))

    assert status.outcome is outcome
    assert status.scientific_claims_enabled is False
    failed_index = tuple(GateId).index(gate_id)
    assert status.evaluated_gates[failed_index].status is GateStatus.FAIL
    assert all(
        record.status is GateStatus.NOT_EVALUATED
        for record in status.evaluated_gates[failed_index + 1 :]
    )


@pytest.mark.unit
def test_unknown_or_denied_rights_block_every_capability_independently() -> None:
    entry = _entry_failing_at(GateId.P1_RIGHTS)
    entry = replace(
        entry,
        rights=replace(
            entry.rights, view_items=RightsDecision.ALLOW, export_content=RightsDecision.DENY
        ),
    )

    status = AssessmentGateEvaluator().evaluate(entry)

    assert status.outcome is GateOutcome.RIGHTS_BLOCKED
    assert len(status.rights.decisions()) == 12
    assert status.capability("view_items").allowed is False
    assert status.capability("store_items").allowed is False
    assert status.capability("score_locally").allowed is False
    assert status.capability("store_score").allowed is False
    assert status.capability("display_interpretation").allowed is False
    assert status.capability("export_content").allowed is False


@pytest.mark.unit
def test_missing_scientific_validation_never_creates_interpretive_claims() -> None:
    status = AssessmentGateEvaluator().evaluate(_entry_failing_at(GateId.P4_MEASUREMENT_EVIDENCE))

    assert status.outcome is GateOutcome.RESEARCH_ONLY
    assert status.scientific_claims_enabled is False


@pytest.mark.unit
def test_fixture_is_metadata_only_and_blocked_at_rights_gate() -> None:
    registry = AssessmentRegistry()
    entry = registry.list_all()[0]
    status = registry.list_statuses()[0]

    assert entry.identity.registry_id == "fictional_orchid_metadata"
    assert status.evaluated_gates[0].status is GateStatus.PASS
    assert status.evaluated_gates[1].status is GateStatus.FAIL
    assert status.outcome is GateOutcome.RIGHTS_BLOCKED
    assert all(decision is RightsDecision.UNKNOWN for _, decision in entry.rights.decisions())
    assert all(not capability.allowed for capability in status.capabilities)
    forbidden_names = {"items", "responses", "scoring_key", "norms", "cutoffs"}
    assert forbidden_names.isdisjoint(entry.__dataclass_fields__)


@pytest.mark.unit
def test_malformed_duplicate_and_forged_input_fails_before_registry_mutation() -> None:
    registry = AssessmentRegistry(include_fixture=False)
    blocked = _entry_failing_at(GateId.P1_RIGHTS)

    with pytest.raises(TypeError, match="typed metadata contract"):
        registry.register({"lifecycle": "approved_for_named_use"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        AssessmentRegistryEntry(items=("forbidden",))  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="approved lifecycle"):
        registry.register(replace(blocked, lifecycle=AssessmentLifecycle.APPROVED_FOR_NAMED_USE))
    with pytest.raises(ValueError, match="P0-P7 exactly once"):
        replace(blocked, gates=(*blocked.gates[:-1], blocked.gates[-2]))

    assert registry.count() == 0


@pytest.mark.unit
def test_registry_entries_and_rights_are_immutable() -> None:
    entry = _entry_failing_at(GateId.P1_RIGHTS)

    with pytest.raises(FrozenInstanceError):
        entry.lifecycle = AssessmentLifecycle.APPROVED_FOR_NAMED_USE  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        entry.rights.view_items = RightsDecision.ALLOW  # type: ignore[misc]
