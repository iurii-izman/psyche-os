"""Deterministic E11 real-data-gate evaluation.

The stable policy and profile are intentionally not mutable evaluation owners.
This module evaluates one exact candidate record and returns a recommendation;
it never writes ``STATE.yaml`` and cannot manufacture human authority.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import subprocess
from typing import Any

from jsonschema import Draft202012Validator
import yaml

RDG_IDS = tuple(f"RDG-{index:02d}" for index in range(1, 13))
RDG_STATUSES = {
    "PROVED_FOR_CANDIDATE",
    "NOT_PROVED",
    "NOT_APPLICABLE_EXCLUDED",
    "STALE_OR_EXPIRED",
    "UNKNOWN_OR_INCOMPLETE",
}
_ADMISSIBLE_PROOF_CLASSES_BY_RDG = {
    rdg_id: frozenset({"deterministic_validator_result_v1"}) for rdg_id in RDG_IDS
}
_BOUNDARY_EXCLUSION_PROOF_CLASS = "boundary_exclusion_proof_v1"
_PASSING_PROOF_RESULT = "PASS"
_CLOSED_RESIDUAL_RISK_STATUSES = {"RESOLVED"}
_REQUIRED_REVIEW_STATE = "COMPLETE"
_SHA256_LENGTH = 64


@dataclass(frozen=True)
class EvaluationOutcome:
    """A content-free gate result for one candidate evaluation."""

    state: str
    reasons: tuple[str, ...]
    evaluation_id: str | None
    lifecycle: str | None
    automatic: bool = False

    @property
    def closed(self) -> bool:
        return self.state == "CLOSED"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def _payload_for_seal(evaluation: Mapping[str, Any]) -> dict[str, Any]:
    """Return the immutable evaluation payload, excluding its seal wrapper."""
    return {key: value for key, value in evaluation.items() if key != "seal"}


def sealed_payload_sha256(evaluation: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(_payload_for_seal(evaluation))).hexdigest()


def seal_evaluation(evaluation: Mapping[str, Any], sealed_at: str) -> dict[str, Any]:
    """Produce a sealed copy; callers persist it as a new immutable record."""
    if evaluation.get("lifecycle") != "DRAFT":
        raise ValueError("only DRAFT evaluations can be sealed")
    sealed = dict(evaluation)
    sealed["lifecycle"] = "SEALED"
    sealed["seal"] = {
        "payload_sha256": sealed_payload_sha256(sealed),
        "sealed_at": sealed_at,
    }
    return sealed


def load_evaluation(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return data


def _load_schema(root: Path, name: str) -> dict[str, Any]:
    path = root / "schemas" / "e11" / name
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"schema {path} is not a mapping")
    Draft202012Validator.check_schema(data)
    return data


def _schema_errors(root: Path, value: Any, schema_name: str) -> list[str]:
    try:
        validator = Draft202012Validator(_load_schema(root, schema_name))
    except Exception as exc:
        return [f"schema_unavailable:{type(exc).__name__}"]
    return [
        f"schema:{'.'.join(str(part) for part in error.absolute_path) or '<root>'}:{error.message}"
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    ]


def _parse_timestamp(value: Any, field: str, reasons: list[str]) -> datetime | None:
    if not isinstance(value, str):
        reasons.append(f"invalid_timestamp:{field}")
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        reasons.append(f"invalid_timestamp:{field}")
        return None
    if parsed.tzinfo is None:
        reasons.append(f"invalid_timestamp:{field}")
        return None
    parsed = parsed.astimezone(UTC)
    return parsed


def _repo_path(root: Path, value: Any, field: str, reasons: list[str]) -> Path | None:
    if not isinstance(value, str) or not value:
        reasons.append(f"missing_path:{field}")
        return None
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        reasons.append(f"path_escapes_repository:{field}")
        return None
    if not candidate.is_file():
        reasons.append(f"missing_path:{field}")
        return None
    return candidate


def _matches_sha256(path: Path, expected: Any) -> bool:
    return (
        isinstance(expected, str)
        and len(expected) == _SHA256_LENGTH
        and (hashlib.sha256(path.read_bytes()).hexdigest() == expected)
    )


def _verify_identity_files(root: Path, evaluation: Mapping[str, Any], reasons: list[str]) -> None:
    identities = evaluation.get("identities", {})
    if not isinstance(identities, dict):
        reasons.append("invalid_identities")
        return
    for kind in ("lock", "sbom"):
        identity = identities.get(kind)
        if not isinstance(identity, dict):
            reasons.append(f"missing_identity:{kind}")
            continue
        path = _repo_path(root, identity.get("path"), f"identities.{kind}", reasons)
        if path is not None and not _matches_sha256(path, identity.get("sha256")):
            reasons.append(f"identity_digest_mismatch:{kind}")
    artifacts = identities.get("artifacts", [])
    if not isinstance(artifacts, list) or not artifacts:
        reasons.append("missing_identity:artifacts")
        return
    for artifact in artifacts:
        if not isinstance(artifact, dict):
            reasons.append("invalid_artifact_identity")
            continue
        name = str(artifact.get("id", "unknown"))
        path = _repo_path(root, artifact.get("path"), f"identities.artifacts.{name}", reasons)
        if path is not None and not _matches_sha256(path, artifact.get("sha256")):
            reasons.append(f"identity_digest_mismatch:artifact:{name}")


def _verify_candidate_source(root: Path, evaluation: Mapping[str, Any], reasons: list[str]) -> None:
    candidate = evaluation.get("candidate")
    source_commit = candidate.get("source_commit") if isinstance(candidate, Mapping) else None
    if not isinstance(source_commit, str):
        reasons.append("candidate_source_missing")
        return
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        reasons.append("candidate_source_missing")


def _profile(root: Path, reasons: list[str]) -> dict[str, Any] | None:
    path = root / "docs" / "architecture" / "REAL_DATA_GATE_PROFILE.yaml"
    try:
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        reasons.append(f"profile_unavailable:{type(exc).__name__}")
        return None
    if not isinstance(profile, dict):
        reasons.append("profile_unavailable:not_mapping")
        return None
    return profile


def _verify_profile_binding(
    root: Path, evaluation: Mapping[str, Any], reasons: list[str]
) -> dict[str, Any] | None:
    profile = _profile(root, reasons)
    binding = evaluation.get("profile_binding", {})
    if profile is None or not isinstance(binding, dict):
        reasons.append("profile_binding_invalid")
        return profile
    path = _repo_path(root, binding.get("profile_path"), "profile_binding.profile_path", reasons)
    if path is None:
        return profile
    if binding.get("profile_path") != "docs/architecture/REAL_DATA_GATE_PROFILE.yaml":
        reasons.append("profile_path_mismatch")
    if binding.get("profile_id") != profile.get("profile_id"):
        reasons.append("profile_id_mismatch")
    if binding.get("profile_version") != profile.get("profile_version"):
        reasons.append("profile_version_mismatch")
    current_profile_bytes = path.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(current_profile_bytes).hexdigest() != binding.get(
        "profile_definition_sha256"
    ):
        reasons.append("profile_digest_mismatch")
    source_commit = binding.get("profile_source_commit")
    candidate = evaluation.get("candidate", {})
    candidate_source = candidate.get("source_commit") if isinstance(candidate, dict) else None
    if not isinstance(source_commit, str):
        reasons.append("profile_source_commit_missing")
    else:
        commit = subprocess.run(
            ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
            cwd=root,
            check=False,
            capture_output=True,
        )
        if commit.returncode != 0:
            reasons.append("profile_source_commit_missing")
        else:
            historical = subprocess.run(
                ["git", "show", f"{source_commit}:{binding.get('profile_path', '')}"],
                cwd=root,
                check=False,
                capture_output=True,
            )
            if historical.returncode != 0:
                reasons.append("profile_historical_bytes_unavailable")
            elif hashlib.sha256(historical.stdout).hexdigest() != binding.get(
                "profile_definition_sha256"
            ):
                reasons.append("profile_historical_digest_mismatch")
            if isinstance(candidate_source, str):
                lineage = subprocess.run(
                    ["git", "merge-base", "--is-ancestor", source_commit, candidate_source],
                    cwd=root,
                    check=False,
                    capture_output=True,
                )
                if lineage.returncode != 0:
                    reasons.append("profile_source_not_in_candidate_lineage")
    platform = candidate.get("platform") if isinstance(candidate, dict) else None
    supported = profile.get("supported_platform_envelope", {}).get("operating_systems", [])
    if not isinstance(platform, dict) or platform.get("operating_system") not in supported:
        reasons.append("unsupported_platform")
    return profile


def _load_evidence_proof(
    root: Path, path: Path, reasons: list[str], evidence_id: str
) -> Mapping[str, Any] | None:
    try:
        proof = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        reasons.append(f"evidence_proof_unreadable:{evidence_id}:{type(exc).__name__}")
        return None
    if not isinstance(proof, Mapping):
        reasons.append(f"evidence_proof_invalid:{evidence_id}")
        return None
    schema_errors = _schema_errors(root, proof, "evidence_proof.schema.json")
    if schema_errors:
        reasons.extend(f"evidence_proof_invalid:{evidence_id}:{error}" for error in schema_errors)
        return None
    return proof


def _evidence_index(
    root: Path, evaluation: Mapping[str, Any], now: datetime, reasons: list[str]
) -> dict[str, Mapping[str, Any]]:
    candidate = evaluation.get("candidate", {})
    candidate_source = candidate.get("source_commit") if isinstance(candidate, dict) else None
    evidence_by_id: dict[str, Mapping[str, Any]] = {}
    raw = evaluation.get("evidence", [])
    if not isinstance(raw, list):
        reasons.append("invalid_evidence")
        return evidence_by_id
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            reasons.append("invalid_evidence")
            continue
        evidence_id = item["id"]
        if evidence_id in evidence_by_id:
            reasons.append(f"duplicate_evidence:{evidence_id}")
            continue
        indexed_item = dict(item)
        evidence_by_id[evidence_id] = indexed_item
        if item.get("candidate_source_commit") != candidate_source:
            reasons.append(f"evidence_candidate_mismatch:{evidence_id}")
        if item.get("candidate_build_id") != candidate.get("build_id"):
            reasons.append(f"evidence_build_mismatch:{evidence_id}")
        if item.get("candidate_platform") != candidate.get("platform"):
            reasons.append(f"evidence_platform_mismatch:{evidence_id}")
        expires = _parse_timestamp(item.get("expires_at"), f"evidence:{evidence_id}", reasons)
        if expires is not None and expires <= now:
            reasons.append(f"expired_evidence:{evidence_id}")
        path = _repo_path(root, item.get("raw_evidence_path"), f"evidence:{evidence_id}", reasons)
        if path is not None and not _matches_sha256(path, item.get("raw_evidence_sha256")):
            reasons.append(f"evidence_digest_mismatch:{evidence_id}")
        if path is None:
            continue
        proof = _load_evidence_proof(root, path, reasons, evidence_id)
        if proof is None:
            continue
        indexed_item["_verified_proof"] = proof
        for field in (
            "proof_class",
            "proof_result",
            "candidate_source_commit",
            "candidate_build_id",
            "candidate_platform",
        ):
            if proof.get(field) != item.get(field):
                reasons.append(f"evidence_proof_mismatch:{evidence_id}:{field}")
        declared_rdg_ids = item.get("rdg_ids", [])
        if (
            item.get("proof_class") == "deterministic_validator_result_v1"
            and proof.get("rdg_ids", []) != declared_rdg_ids
        ):
            reasons.append(f"evidence_proof_mismatch:{evidence_id}:rdg_ids")
        if item.get("proof_result") != _PASSING_PROOF_RESULT:
            reasons.append(f"evidence_proof_not_passing:{evidence_id}")
    return evidence_by_id


def _review_index(
    evaluation: Mapping[str, Any], now: datetime, reasons: list[str]
) -> dict[str, Mapping[str, Any]]:
    candidate = evaluation.get("candidate", {})
    candidate_source = candidate.get("source_commit") if isinstance(candidate, dict) else None
    reviews_by_id: dict[str, Mapping[str, Any]] = {}
    raw = evaluation.get("reviews", [])
    if not isinstance(raw, list):
        reasons.append("invalid_reviews")
        return reviews_by_id
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            reasons.append("invalid_review")
            continue
        review_id = item["id"]
        if review_id in reviews_by_id:
            reasons.append(f"duplicate_review:{review_id}")
            continue
        reviews_by_id[review_id] = item
        if item.get("candidate_source_commit") != candidate_source:
            reasons.append(f"review_candidate_mismatch:{review_id}")
        if item.get("candidate_build_id") != candidate.get("build_id"):
            reasons.append(f"review_build_mismatch:{review_id}")
        if item.get("candidate_platform") != candidate.get("platform"):
            reasons.append(f"review_platform_mismatch:{review_id}")
        expires = _parse_timestamp(item.get("expires_at"), f"review:{review_id}", reasons)
        if expires is not None and expires <= now:
            reasons.append(f"expired_review:{review_id}")
        if item.get("state") != _REQUIRED_REVIEW_STATE:
            reasons.append(f"review_incomplete:{review_id}")
        findings = item.get("findings", [])
        if not isinstance(findings, list):
            reasons.append(f"invalid_review_findings:{review_id}")
        elif any(
            isinstance(finding, dict)
            and finding.get("state") != "RESOLVED"
            and finding.get("severity") in {"CRITICAL", "HIGH"}
            for finding in findings
        ):
            reasons.append(f"unresolved_critical_or_high:{review_id}")
    return reviews_by_id


def _boundary_assessments(
    profile: Mapping[str, Any] | None,
    evaluation: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, Any]],
    reasons: list[str],
) -> dict[str, Mapping[str, Any]]:
    raw = evaluation.get("boundary_assessments", [])
    assessments: dict[str, Mapping[str, Any]] = {}
    if not isinstance(raw, list):
        reasons.append("invalid_boundary_assessments")
        return assessments
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("boundary_id"), str):
            reasons.append("invalid_boundary_assessment")
            continue
        boundary_id = item["boundary_id"]
        if boundary_id in assessments:
            reasons.append(f"duplicate_boundary_assessment:{boundary_id}")
        assessments[boundary_id] = item
    inventory = profile.get("boundary_inventory", {}) if isinstance(profile, dict) else {}
    if not isinstance(inventory, dict):
        return assessments
    for boundary_id, boundary in inventory.items():
        assessment = assessments.get(boundary_id)
        if assessment is None:
            reasons.append(f"missing_boundary_assessment:{boundary_id}")
            continue
        expected = "APPLICABLE" if boundary.get("state") == "ENABLED" else "EXCLUDED"
        if assessment.get("state") != expected:
            reasons.append(f"boundary_profile_mismatch:{boundary_id}")
        if expected == "EXCLUDED" and assessment.get("unreachable") is not True:
            reasons.append(f"unproven_boundary_exclusion:{boundary_id}")
        if expected == "EXCLUDED":
            evidence_ids = assessment.get("exclusion_evidence_ids", [])
            if not isinstance(evidence_ids, list) or not evidence_ids:
                reasons.append(f"missing_boundary_exclusion_evidence:{boundary_id}")
                continue
            for evidence_id in evidence_ids:
                proof = evidence.get(evidence_id)
                raw_proof = proof.get("_verified_proof", {}) if isinstance(proof, Mapping) else {}
                if (
                    proof is None
                    or proof.get("proof_class") != _BOUNDARY_EXCLUSION_PROOF_CLASS
                    or proof.get("proof_result") != _PASSING_PROOF_RESULT
                    or not isinstance(raw_proof, Mapping)
                    or boundary_id not in raw_proof.get("boundary_ids", [])
                ):
                    reasons.append(f"invalid_boundary_exclusion_evidence:{boundary_id}")
    return assessments


def _control_results(
    profile: Mapping[str, Any] | None,
    evaluation: Mapping[str, Any],
    evidence: Mapping[str, Mapping[str, Any]],
    reasons: list[str],
) -> dict[str, Mapping[str, Any]]:
    raw = evaluation.get("rdg_controls", [])
    controls: dict[str, Mapping[str, Any]] = {}
    if not isinstance(raw, list):
        reasons.append("invalid_rdg_controls")
        return controls
    for item in raw:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str):
            reasons.append("invalid_rdg_control")
            continue
        control_id = item["id"]
        if control_id in controls:
            reasons.append(f"duplicate_rdg_control:{control_id}")
        controls[control_id] = item
    if set(controls) != set(RDG_IDS):
        reasons.append("rdg_control_set_mismatch")
    inventory = profile.get("boundary_inventory", {}) if isinstance(profile, dict) else {}
    for control_id, control in controls.items():
        status = control.get("status")
        if status not in RDG_STATUSES:
            reasons.append(f"invalid_rdg_status:{control_id}")
            continue
        expected_boundaries = sorted(
            boundary_id
            for boundary_id, boundary in inventory.items()
            if isinstance(boundary, dict) and control_id in boundary.get("applicable_rdg", [])
        )
        predicates = control.get("boundary_predicates", [])
        if sorted(predicates) != expected_boundaries:
            reasons.append(f"boundary_predicate_mismatch:{control_id}")
        if status == "PROVED_FOR_CANDIDATE":
            evidence_ids = control.get("evidence_ids", [])
            if not isinstance(evidence_ids, list) or not evidence_ids:
                reasons.append(f"missing_control_evidence:{control_id}")
            for evidence_id in evidence_ids if isinstance(evidence_ids, list) else []:
                item = evidence.get(evidence_id)
                admissible = _ADMISSIBLE_PROOF_CLASSES_BY_RDG.get(control_id, frozenset())
                if (
                    item is None
                    or control_id not in item.get("rdg_ids", [])
                    or item.get("proof_class") not in admissible
                    or item.get("proof_result") != _PASSING_PROOF_RESULT
                ):
                    reasons.append(f"control_evidence_mismatch:{control_id}")
        if status == "NOT_APPLICABLE_EXCLUDED":
            excluded = control.get("excluded_boundary_ids", [])
            if sorted(excluded) != expected_boundaries or not expected_boundaries:
                reasons.append(f"invalid_exclusion:{control_id}")
                continue
            for boundary_id in expected_boundaries:
                boundary = inventory.get(boundary_id, {})
                assessment = next(
                    (
                        item
                        for item in evaluation.get("boundary_assessments", [])
                        if isinstance(item, Mapping) and item.get("boundary_id") == boundary_id
                    ),
                    None,
                )
                if (
                    not isinstance(boundary, Mapping)
                    or boundary.get("state") != "EXCLUDED"
                    or not isinstance(assessment, Mapping)
                    or assessment.get("state") != "EXCLUDED"
                    or assessment.get("unreachable") is not True
                ):
                    reasons.append(f"invalid_exclusion:{control_id}")
    return controls


def _required_reviews(
    profile: Mapping[str, Any] | None,
    assessments: Mapping[str, Mapping[str, Any]],
    reviews: Mapping[str, Mapping[str, Any]],
    reasons: list[str],
) -> None:
    inventory = profile.get("boundary_inventory", {}) if isinstance(profile, dict) else {}
    for boundary_id, boundary in inventory.items():
        assessment = assessments.get(boundary_id)
        if not isinstance(assessment, dict) or assessment.get("state") != "APPLICABLE":
            continue
        review_ids = assessment.get("review_ids", [])
        for review_class in boundary.get("required_review_classes", []):
            if not any(
                review_id in reviews
                and reviews[review_id].get("review_class") == review_class
                and reviews[review_id].get("boundary_id") == boundary_id
                for review_id in review_ids
            ):
                reasons.append(f"missing_required_review:{boundary_id}:{review_class}")


def _verify_seal(evaluation: Mapping[str, Any], now: datetime, reasons: list[str]) -> None:
    lifecycle = evaluation.get("lifecycle")
    seal = evaluation.get("seal")
    if lifecycle == "DRAFT":
        if seal is not None:
            reasons.append("draft_has_seal")
        return
    if lifecycle != "SEALED" or not isinstance(seal, dict):
        reasons.append("missing_seal")
        return
    if seal.get("payload_sha256") != sealed_payload_sha256(evaluation):
        reasons.append("sealed_payload_modified")
    _parse_timestamp(seal.get("sealed_at"), "seal", reasons)


def _verify_successor(evaluation: Mapping[str, Any], reasons: list[str]) -> None:
    """Require a named predecessor whenever an invalidation is carried forward."""
    successor = evaluation.get("successor")
    if not isinstance(successor, Mapping):
        reasons.append("invalid_successor")
        return
    predecessor = successor.get("supersedes")
    invalidations = successor.get("invalidation_reasons")
    if not isinstance(invalidations, list):
        reasons.append("invalid_successor")
        return
    if predecessor is None and invalidations:
        reasons.append("successor_missing_predecessor")
    if predecessor is not None and (
        not isinstance(predecessor, str)
        or not predecessor
        or predecessor == evaluation.get("evaluation_id")
        or not invalidations
    ):
        reasons.append("invalid_successor")


def _verify_attestation(
    root: Path,
    evaluation: Mapping[str, Any],
    attestation: Mapping[str, Any] | None,
    now: datetime,
    reasons: list[str],
) -> bool:
    if attestation is None:
        reasons.append("missing_human_attestation")
        return False
    reasons.extend(_schema_errors(root, attestation, "human_attestation.schema.json"))
    if attestation.get("evaluation_id") != evaluation.get("evaluation_id"):
        reasons.append("attestation_evaluation_mismatch")
    seal_value = evaluation.get("seal")
    seal: Mapping[str, Any] = seal_value if isinstance(seal_value, Mapping) else {}
    if attestation.get("sealed_evaluation_sha256") != seal.get("payload_sha256"):
        reasons.append("attestation_digest_mismatch")
    if attestation.get("method") != "local_human_attestation_v1":
        reasons.append("attestation_method_mismatch")
    if attestation.get("attestor_kind") != "HUMAN_REPOSITORY_OWNER":
        reasons.append("model_or_unqualified_gate_decider")
    expires = _parse_timestamp(attestation.get("expires_at"), "attestation", reasons)
    if expires is not None and expires <= now:
        reasons.append("expired_human_attestation")
    return not reasons


def evaluate_evaluation(
    root: Path,
    evaluation: Mapping[str, Any],
    *,
    attestation: Mapping[str, Any] | None = None,
    now: datetime | None = None,
) -> EvaluationOutcome:
    """Evaluate a record without side effects; every uncertainty remains closed."""
    current_time = now or datetime.now(UTC)
    reasons = _schema_errors(root, evaluation, "gate_evaluation.schema.json")
    evaluation_id = (
        evaluation.get("evaluation_id")
        if isinstance(evaluation.get("evaluation_id"), str)
        else None
    )
    lifecycle = (
        evaluation.get("lifecycle") if isinstance(evaluation.get("lifecycle"), str) else None
    )
    if reasons:
        return EvaluationOutcome("CLOSED", tuple(sorted(set(reasons))), evaluation_id, lifecycle)

    _verify_candidate_source(root, evaluation, reasons)
    _verify_identity_files(root, evaluation, reasons)
    profile = _verify_profile_binding(root, evaluation, reasons)
    evidence = _evidence_index(root, evaluation, current_time, reasons)
    reviews = _review_index(evaluation, current_time, reasons)
    assessments = _boundary_assessments(profile, evaluation, evidence, reasons)
    controls = _control_results(profile, evaluation, evidence, reasons)
    _required_reviews(profile, assessments, reviews, reasons)
    _verify_seal(evaluation, current_time, reasons)
    _verify_successor(evaluation, reasons)

    candidate = evaluation.get("candidate", {})
    if not isinstance(candidate, dict) or candidate.get("requested_data_class") != "SYNTHETIC_ONLY":
        reasons.append("real_data_attempt_while_gate_closed")
    reproduction = candidate.get("reproducibility", {}) if isinstance(candidate, dict) else {}
    if not isinstance(reproduction, dict) or reproduction.get("status") != "REPRODUCED":
        reasons.append("non_reproducible_build")
    elif not reproduction.get("evidence_ids") or any(
        evidence_id not in evidence for evidence_id in reproduction["evidence_ids"]
    ):
        reasons.append("reproduction_evidence_mismatch")
    for risk in evaluation.get("residual_risks", []):
        if not isinstance(risk, dict):
            reasons.append("invalid_residual_risk")
            continue
        expires = _parse_timestamp(
            risk.get("expires_at"), f"residual_risk:{risk.get('id', 'unknown')}", reasons
        )
        if expires is not None and expires <= current_time:
            reasons.append(f"expired_residual_risk:{risk.get('id', 'unknown')}")
        if (
            risk.get("severity") in {"CRITICAL", "HIGH"}
            and risk.get("status") not in _CLOSED_RESIDUAL_RISK_STATUSES
        ):
            reasons.append(f"unresolved_critical_or_high_residual_risk:{risk.get('id', 'unknown')}")
    if lifecycle == "DRAFT":
        reasons.append("draft_cannot_support_open")
    if any(
        control.get("status") not in {"PROVED_FOR_CANDIDATE", "NOT_APPLICABLE_EXCLUDED"}
        for control in controls.values()
    ):
        reasons.append("rdg_controls_not_proved")
    if evaluation.get("gate_decision", {}).get("requested_state") == "OPEN":
        reasons.append("automatic_open_forbidden")

    attestation_valid = False
    if lifecycle == "SEALED" and not reasons:
        attestation_valid = _verify_attestation(
            root, evaluation, attestation, current_time, reasons
        )
    elif attestation is None:
        reasons.append("missing_human_attestation")

    if (
        reasons
        or not attestation_valid
        or attestation is None
        or attestation.get("decision") != "OPEN"
    ):
        return EvaluationOutcome("CLOSED", tuple(sorted(set(reasons))), evaluation_id, lifecycle)
    return EvaluationOutcome("OPEN", (), evaluation_id, lifecycle, automatic=False)
