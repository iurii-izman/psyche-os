"""Synthetic failure proofs for the exact-candidate E11 evaluator."""

from __future__ import annotations

import copy
from datetime import UTC, datetime
import hashlib
from pathlib import Path
from typing import Any

import yaml

from psyche_os.release_evidence.e11_gate import (
    _verify_profile_binding,
    evaluate_evaluation,
    seal_evaluation,
)

ROOT = Path(__file__).resolve().parents[2]
NOW = datetime(2026, 8, 21, tzinfo=UTC)
EVALUATION_PATH = (
    ROOT / "artifacts" / "e11" / "gate-evaluations" / "e11-implementation-candidate-draft.yaml"
)
RAW_EVIDENCE_PATH = "artifacts/e11/release-manifests/e11-implementation-candidate.yaml"
RDG_PROOF_PATH = "tests/fixtures/e11/deterministic-rdg-proof.yaml"
EXCLUSION_PROOF_PATH = "tests/fixtures/e11/boundary-exclusion-proof.yaml"
WRONG_EXCLUSION_PROOF_PATH = "tests/fixtures/e11/wrong-boundary-exclusion-proof.yaml"


def _sha256(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def _draft() -> dict[str, Any]:
    value = yaml.safe_load(EVALUATION_PATH.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return copy.deepcopy(value)


def _proved_sealed() -> dict[str, Any]:
    evaluation = _draft()
    candidate = evaluation["candidate"]
    candidate["reproducibility"] = {
        "status": "REPRODUCED",
        "evidence_ids": ["synthetic-release-evidence"],
    }
    evaluation["evidence"] = [
        {
            "id": "synthetic-release-evidence",
            "rdg_ids": [f"RDG-{number:02d}" for number in range(1, 13)],
            "proof_class": "deterministic_validator_result_v1",
            "proof_result": "PASS",
            "candidate_source_commit": candidate["source_commit"],
            "candidate_build_id": candidate["build_id"],
            "candidate_platform": copy.deepcopy(candidate["platform"]),
            "raw_evidence_path": RDG_PROOF_PATH,
            "raw_evidence_sha256": _sha256(RDG_PROOF_PATH),
            "expires_at": "2030-01-01T00:00:00Z",
        },
        {
            "id": "synthetic-exclusion-evidence",
            "rdg_ids": [],
            "proof_class": "boundary_exclusion_proof_v1",
            "proof_result": "PASS",
            "candidate_source_commit": candidate["source_commit"],
            "candidate_build_id": candidate["build_id"],
            "candidate_platform": copy.deepcopy(candidate["platform"]),
            "raw_evidence_path": EXCLUSION_PROOF_PATH,
            "raw_evidence_sha256": _sha256(EXCLUSION_PROOF_PATH),
            "expires_at": "2030-01-01T00:00:00Z",
        },
        {
            "id": "wrong-boundary-exclusion-evidence",
            "rdg_ids": [],
            "proof_class": "boundary_exclusion_proof_v1",
            "proof_result": "PASS",
            "candidate_source_commit": candidate["source_commit"],
            "candidate_build_id": candidate["build_id"],
            "candidate_platform": copy.deepcopy(candidate["platform"]),
            "raw_evidence_path": WRONG_EXCLUSION_PROOF_PATH,
            "raw_evidence_sha256": _sha256(WRONG_EXCLUSION_PROOF_PATH),
            "expires_at": "2030-01-01T00:00:00Z",
        },
    ]
    profile = yaml.safe_load(
        (ROOT / "docs/architecture/REAL_DATA_GATE_PROFILE.yaml").read_text(encoding="utf-8")
    )
    assert isinstance(profile, dict)
    reviews: list[dict[str, Any]] = []
    for boundary_id, boundary in profile["boundary_inventory"].items():
        if boundary["state"] != "ENABLED":
            continue
        review_ids: list[str] = []
        for number, review_class in enumerate(boundary["required_review_classes"], start=1):
            review_id = f"{boundary_id}-review-{number}"
            review_ids.append(review_id)
            reviews.append(
                {
                    "id": review_id,
                    "boundary_id": boundary_id,
                    "review_class": review_class,
                    "candidate_source_commit": candidate["source_commit"],
                    "candidate_build_id": candidate["build_id"],
                    "candidate_platform": copy.deepcopy(candidate["platform"]),
                    "state": "COMPLETE",
                    "expires_at": "2030-01-01T00:00:00Z",
                    "findings": [],
                }
            )
        for assessment in evaluation["boundary_assessments"]:
            if assessment["boundary_id"] == boundary_id:
                assessment["review_ids"] = review_ids
    for assessment in evaluation["boundary_assessments"]:
        if assessment["state"] == "EXCLUDED":
            assessment["exclusion_evidence_ids"] = ["synthetic-exclusion-evidence"]
    evaluation["reviews"] = reviews
    for control in evaluation["rdg_controls"]:
        control["status"] = "PROVED_FOR_CANDIDATE"
        control["evidence_ids"] = ["synthetic-release-evidence"]
    evaluation["residual_risks"][0].update(
        {"severity": "HIGH", "status": "RESOLVED", "expires_at": "2030-01-01T00:00:00Z"}
    )
    return seal_evaluation(evaluation, "2026-08-20T00:00:00Z")


def _outcome(evaluation: dict[str, Any], attestation: dict[str, Any] | None = None):
    return evaluate_evaluation(ROOT, evaluation, attestation=attestation, now=NOW)


def _open_attestation(evaluation: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "evaluation_id": evaluation["evaluation_id"],
        "sealed_evaluation_sha256": evaluation["seal"]["payload_sha256"],
        "method": "local_human_attestation_v1",
        "attestor_kind": "HUMAN_REPOSITORY_OWNER",
        "decision": "OPEN",
        "attested_at": "2026-08-20T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
    }


def _reseal(evaluation: dict[str, Any]) -> dict[str, Any]:
    draft = copy.deepcopy(evaluation)
    draft["lifecycle"] = "DRAFT"
    draft["seal"] = None
    return seal_evaluation(draft, "2026-08-20T00:00:00Z")


def test_draft_candidate_is_valid_but_cannot_support_open() -> None:
    outcome = _outcome(_draft())

    assert outcome.state == "CLOSED"
    assert "draft_cannot_support_open" in outcome.reasons
    assert "non_reproducible_build" in outcome.reasons


def test_profile_digest_mismatch_closes_candidate() -> None:
    evaluation = _proved_sealed()
    evaluation["profile_binding"]["profile_definition_sha256"] = "0" * 64

    assert "profile_digest_mismatch" in _outcome(evaluation).reasons


def test_profile_history_requires_existing_matching_ancestor_commit() -> None:
    evaluation = _proved_sealed()
    evaluation["profile_binding"]["profile_source_commit"] = "f" * 40
    assert "profile_source_commit_missing" in _outcome(evaluation).reasons

    evaluation = _proved_sealed()
    evaluation["profile_binding"]["profile_definition_sha256"] = "0" * 64
    assert "profile_historical_digest_mismatch" in _outcome(evaluation).reasons

    evaluation = _proved_sealed()
    evaluation["profile_binding"]["profile_source_commit"] = (
        "21d0154376dc7926ce8ee80711605101e2b5820c"
    )
    assert "profile_source_not_in_candidate_lineage" in _outcome(evaluation).reasons


def test_older_ancestor_profile_binding_is_valid() -> None:
    evaluation = _draft()
    evaluation["candidate"]["source_commit"] = "21d0154376dc7926ce8ee80711605101e2b5820c"
    reasons: list[str] = []

    _verify_profile_binding(ROOT, evaluation, reasons)

    assert reasons == []


def test_wrong_source_build_or_platform_identity_closes_candidate() -> None:
    for field, value, expected in (
        ("candidate_source_commit", "f" * 40, "evidence_candidate_mismatch"),
        ("candidate_build_id", "wrong-build", "evidence_build_mismatch"),
        ("candidate_platform", {"operating_system": "Linux"}, "evidence_platform_mismatch"),
    ):
        evaluation = _proved_sealed()
        evaluation["evidence"][0][field] = value
        assert any(reason.startswith(expected) for reason in _outcome(evaluation).reasons)


def test_wrong_candidate_platform_is_not_supported() -> None:
    evaluation = _proved_sealed()
    evaluation["candidate"]["platform"]["operating_system"] = "Linux"

    assert "unsupported_platform" in _outcome(evaluation).reasons


def test_lock_sbom_and_artifact_identity_mismatch_close_candidate() -> None:
    for section in ("lock", "sbom"):
        evaluation = _proved_sealed()
        evaluation["identities"][section]["sha256"] = "0" * 64
        assert f"identity_digest_mismatch:{section}" in _outcome(evaluation).reasons

    evaluation = _proved_sealed()
    evaluation["identities"]["artifacts"][0]["sha256"] = "0" * 64
    assert (
        "identity_digest_mismatch:artifact:draft-release-manifest" in _outcome(evaluation).reasons
    )


def test_evidence_from_a_previous_candidate_closes_candidate() -> None:
    evaluation = _proved_sealed()
    evaluation["evidence"][0]["candidate_source_commit"] = "a" * 40

    assert "evidence_candidate_mismatch:synthetic-release-evidence" in _outcome(evaluation).reasons


def test_expired_evidence_or_review_closes_candidate() -> None:
    evaluation = _proved_sealed()
    evaluation["evidence"][0]["expires_at"] = "2020-01-01T00:00:00Z"
    assert "expired_evidence:synthetic-release-evidence" in _outcome(evaluation).reasons

    evaluation = _proved_sealed()
    evaluation["reviews"][0]["expires_at"] = "2020-01-01T00:00:00Z"
    assert any(reason.startswith("expired_review:") for reason in _outcome(evaluation).reasons)


def test_unresolved_critical_or_high_finding_closes_candidate() -> None:
    evaluation = _proved_sealed()
    evaluation["reviews"][0]["findings"] = [{"severity": "CRITICAL", "state": "OPEN"}]

    assert any(
        reason.startswith("unresolved_critical_or_high:") for reason in _outcome(evaluation).reasons
    )


def test_unresolved_or_expired_critical_high_residual_risk_closes_candidate() -> None:
    for severity in ("HIGH", "CRITICAL"):
        evaluation = _proved_sealed()
        evaluation["residual_risks"][0].update({"severity": severity, "status": "OPEN"})
        assert (
            "unresolved_critical_or_high_residual_risk:all-rdg-controls-unproved-for-draft"
            in _outcome(evaluation).reasons
        )

    evaluation = _proved_sealed()
    evaluation["residual_risks"][0]["expires_at"] = "2020-01-01T00:00:00Z"
    assert (
        "expired_residual_risk:all-rdg-controls-unproved-for-draft" in _outcome(evaluation).reasons
    )


def test_invalid_not_applicable_exclusion_closes_candidate() -> None:
    evaluation = _proved_sealed()
    control = next(item for item in evaluation["rdg_controls"] if item["id"] == "RDG-08")
    control["status"] = "NOT_APPLICABLE_EXCLUDED"
    control["excluded_boundary_ids"] = ["importer_parser_or_untrusted_rendering"]

    assert "invalid_exclusion:RDG-08" in _outcome(evaluation).reasons


def test_fully_excluded_control_can_be_not_applicable_only_with_valid_proofs() -> None:
    evaluation = _proved_sealed()
    control = next(item for item in evaluation["rdg_controls"] if item["id"] == "RDG-11")
    control.update(
        {
            "status": "NOT_APPLICABLE_EXCLUDED",
            "excluded_boundary_ids": sorted(control["boundary_predicates"]),
        }
    )
    evaluation = _reseal(evaluation)

    assert _outcome(evaluation, _open_attestation(evaluation)).state == "OPEN"


def test_exclusion_requires_exact_boundary_proof() -> None:
    evaluation = _proved_sealed()
    assessment = next(
        item
        for item in evaluation["boundary_assessments"]
        if item["boundary_id"] == "importer_parser_or_untrusted_rendering"
    )
    assessment["exclusion_evidence_ids"] = []
    assert (
        "missing_boundary_exclusion_evidence:importer_parser_or_untrusted_rendering"
        in _outcome(evaluation).reasons
    )

    evaluation = _proved_sealed()
    assessment = next(
        item
        for item in evaluation["boundary_assessments"]
        if item["boundary_id"] == "importer_parser_or_untrusted_rendering"
    )
    assessment["exclusion_evidence_ids"] = ["synthetic-release-evidence"]
    assert (
        "invalid_boundary_exclusion_evidence:importer_parser_or_untrusted_rendering"
        in _outcome(evaluation).reasons
    )

    evaluation = _proved_sealed()
    assessment = next(
        item
        for item in evaluation["boundary_assessments"]
        if item["boundary_id"] == "importer_parser_or_untrusted_rendering"
    )
    assessment["exclusion_evidence_ids"] = ["wrong-boundary-exclusion-evidence"]
    assert (
        "invalid_boundary_exclusion_evidence:importer_parser_or_untrusted_rendering"
        in _outcome(evaluation).reasons
    )


def test_arbitrary_hashed_release_manifest_cannot_be_laundered_into_rdg_proof() -> None:
    evaluation = _proved_sealed()
    evidence = evaluation["evidence"][0]
    evidence.update(
        {
            "raw_evidence_path": RAW_EVIDENCE_PATH,
            "raw_evidence_sha256": _sha256(RAW_EVIDENCE_PATH),
        }
    )
    evaluation = _reseal(evaluation)

    outcome = _outcome(evaluation, _open_attestation(evaluation))

    assert outcome.state == "CLOSED"
    assert any(
        reason.startswith("evidence_proof_invalid:synthetic-release-evidence")
        for reason in outcome.reasons
    )


def test_provider_importer_and_professional_profile_mismatches_close_candidate() -> None:
    for boundary_id in (
        "provider_model_or_network",
        "importer_parser_or_untrusted_rendering",
        "professional_report_or_external_handoff",
    ):
        evaluation = _proved_sealed()
        assessment = next(
            item
            for item in evaluation["boundary_assessments"]
            if item["boundary_id"] == boundary_id
        )
        assessment["state"] = "APPLICABLE"
        assert f"boundary_profile_mismatch:{boundary_id}" in _outcome(evaluation).reasons


def test_non_reproducible_build_closes_candidate() -> None:
    evaluation = _proved_sealed()
    evaluation["candidate"]["reproducibility"]["status"] = "NOT_REPRODUCED"

    assert "non_reproducible_build" in _outcome(evaluation).reasons


def test_modified_sealed_evaluation_is_rejected() -> None:
    evaluation = _proved_sealed()
    evaluation["residual_risks"][0]["status"] = "OPEN"

    assert "sealed_payload_modified" in _outcome(evaluation).reasons


def test_invalidation_requires_a_distinct_successor_record() -> None:
    evaluation = _proved_sealed()
    evaluation["successor"] = {"supersedes": None, "invalidation_reasons": ["dependency_change"]}

    assert "successor_missing_predecessor" in _outcome(evaluation).reasons


def test_wrong_human_attestation_digest_closes_candidate() -> None:
    evaluation = _proved_sealed()
    attestation = {
        "schema_version": "1.0",
        "evaluation_id": evaluation["evaluation_id"],
        "sealed_evaluation_sha256": "0" * 64,
        "method": "local_human_attestation_v1",
        "attestor_kind": "HUMAN_REPOSITORY_OWNER",
        "decision": "OPEN",
        "attested_at": "2026-08-20T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
    }

    assert "attestation_digest_mismatch" in _outcome(evaluation, attestation).reasons


def test_coding_model_cannot_act_as_human_gate_decider() -> None:
    evaluation = _proved_sealed()
    attestation = {
        "schema_version": "1.0",
        "evaluation_id": evaluation["evaluation_id"],
        "sealed_evaluation_sha256": evaluation["seal"]["payload_sha256"],
        "method": "local_human_attestation_v1",
        "attestor_kind": "CODING_MODEL",
        "decision": "OPEN",
        "attested_at": "2026-08-20T00:00:00Z",
        "expires_at": "2030-01-01T00:00:00Z",
    }

    assert "model_or_unqualified_gate_decider" in _outcome(evaluation, attestation).reasons


def test_missing_human_attestation_closes_an_otherwise_proved_candidate() -> None:
    outcome = _outcome(_proved_sealed())

    assert outcome.state == "CLOSED"
    assert outcome.reasons == ("missing_human_attestation",)


def test_positive_synthetic_oracle_opens_only_with_verified_trust_inputs() -> None:
    evaluation = _proved_sealed()
    outcome = _outcome(evaluation, _open_attestation(evaluation))

    assert outcome.state == "OPEN"
    assert outcome.automatic is False
    assert outcome.reasons == ()

    mutations = (
        ("evidence", lambda value: value["evidence"][0].update({"proof_result": "FAIL"})),
        (
            "exclusion",
            lambda value: next(
                item for item in value["boundary_assessments"] if item["state"] == "EXCLUDED"
            ).update({"exclusion_evidence_ids": []}),
        ),
        (
            "residual-risk",
            lambda value: value["residual_risks"][0].update({"status": "OPEN"}),
        ),
        (
            "profile-history",
            lambda value: value["profile_binding"].update({"profile_definition_sha256": "0" * 64}),
        ),
        ("seal", lambda value: value["seal"].update({"payload_sha256": "0" * 64})),
    )
    for _name, mutate in mutations:
        mutated = copy.deepcopy(evaluation)
        mutate(mutated)
        assert _outcome(mutated, _open_attestation(mutated)).state == "CLOSED"

    bad_attestation = _open_attestation(evaluation)
    bad_attestation["sealed_evaluation_sha256"] = "0" * 64
    assert _outcome(evaluation, bad_attestation).state == "CLOSED"


def test_automatic_open_and_real_data_attempts_are_closed() -> None:
    automatic = _draft()
    automatic["gate_decision"]["requested_state"] = "OPEN"
    automatic_outcome = _outcome(automatic)
    assert automatic_outcome.state == "CLOSED"
    assert "automatic_open_forbidden" in automatic_outcome.reasons

    real_data = _proved_sealed()
    real_data["candidate"]["requested_data_class"] = "REAL_PERSONAL"
    real_data_outcome = _outcome(real_data)
    assert real_data_outcome.state == "CLOSED"
    assert "real_data_attempt_while_gate_closed" in real_data_outcome.reasons
