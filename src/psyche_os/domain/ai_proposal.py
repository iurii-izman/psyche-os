"""Pure E07 values for one bounded, stateless reflection proposal."""

from __future__ import annotations

from dataclasses import dataclass, replace
import datetime as dt
from enum import StrEnum
import hashlib
import json
import re
from typing import Any

from psyche_os.domain.experiments import ClaimLevel


def identity_digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


class EvidenceRole(StrEnum):
    SUPPORTING = "supporting"
    COUNTEREVIDENCE = "counterevidence"
    UNKNOWN = "unknown"


class ProposalStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    EDITED = "EDITED"
    REJECTED = "REJECTED"
    DISCARDED = "DISCARDED"


class EvaluationAction(StrEnum):
    ACCEPT = "accept"
    EDIT = "edit"
    REJECT = "reject"
    DISCARD = "discard"


@dataclass(frozen=True, slots=True)
class ProviderIdentity:
    provider: str
    model_snapshot: str
    config_snapshot: str

    @property
    def digest(self) -> str:
        return identity_digest(
            {
                "provider": self.provider,
                "model_snapshot": self.model_snapshot,
                "config_snapshot": self.config_snapshot,
            }
        )


@dataclass(frozen=True, slots=True)
class ManifestRecord:
    record_id: str
    version_id: str
    category: str
    role: EvidenceRole
    policy_id: str


@dataclass(frozen=True, slots=True)
class ContextManifest:
    schema_version: str
    manifest_id: str
    purpose: str
    records: tuple[ManifestRecord, ...]
    cutoff: dt.datetime
    policy_decision_id: str
    provider_identity: ProviderIdentity
    context_builder_version: str
    claim_ceiling: ClaimLevel
    action_ceiling: str

    @classmethod
    def create(
        cls,
        *,
        purpose: str,
        records: tuple[ManifestRecord, ...],
        cutoff: dt.datetime,
        policy_decision_id: str,
        provider_identity: ProviderIdentity,
        context_builder_version: str,
        claim_ceiling: ClaimLevel,
        action_ceiling: str,
    ) -> ContextManifest:
        material = {
            "schema_version": "e07-context-manifest-v1",
            "purpose": purpose,
            "records": [
                {
                    "record_id": item.record_id,
                    "version_id": item.version_id,
                    "category": item.category,
                    "role": item.role.value,
                    "policy_id": item.policy_id,
                }
                for item in records
            ],
            "cutoff": cutoff.isoformat(),
            "policy_decision_id": policy_decision_id,
            "provider_identity": provider_identity.digest,
            "context_builder_version": context_builder_version,
            "claim_ceiling": int(claim_ceiling),
            "action_ceiling": action_ceiling,
        }
        return cls(manifest_id=identity_digest(material), **material_for_manifest(material, records, cutoff, provider_identity, claim_ceiling))


def material_for_manifest(
    material: dict[str, Any],
    records: tuple[ManifestRecord, ...],
    cutoff: dt.datetime,
    provider_identity: ProviderIdentity,
    claim_ceiling: ClaimLevel,
) -> dict[str, Any]:
    return {
        "schema_version": str(material["schema_version"]),
        "purpose": str(material["purpose"]),
        "records": records,
        "cutoff": cutoff,
        "policy_decision_id": str(material["policy_decision_id"]),
        "provider_identity": provider_identity,
        "context_builder_version": str(material["context_builder_version"]),
        "claim_ceiling": claim_ceiling,
        "action_ceiling": str(material["action_ceiling"]),
    }


@dataclass(frozen=True, slots=True)
class DisclosurePreview:
    preview_id: str
    manifest_id: str
    purpose: str
    provider_identity: ProviderIdentity
    selected: tuple[tuple[str, str, str], ...]
    transformations: tuple[str, ...]
    retention: str
    policy_decision_id: str

    @classmethod
    def create(cls, manifest: ContextManifest, transformations: tuple[str, ...]) -> DisclosurePreview:
        selected = tuple(
            (record.record_id, record.version_id, record.category) for record in manifest.records
        )
        material = {
            "manifest_id": manifest.manifest_id,
            "purpose": manifest.purpose,
            "provider_identity": manifest.provider_identity.digest,
            "selected": selected,
            "transformations": transformations,
            "retention": "ephemeral",
            "policy_decision_id": manifest.policy_decision_id,
        }
        return cls(
            preview_id=identity_digest(material),
            manifest_id=manifest.manifest_id,
            purpose=manifest.purpose,
            provider_identity=manifest.provider_identity,
            selected=selected,
            transformations=transformations,
            retention="ephemeral",
            policy_decision_id=manifest.policy_decision_id,
        )


@dataclass(frozen=True, slots=True)
class DisclosureAuthorization:
    authorization_id: str
    preview_id: str
    authorized_at: dt.datetime
    expires_at: dt.datetime


@dataclass(frozen=True, slots=True)
class ProviderContextRecord:
    record_id: str
    version_id: str
    category: str
    role: EvidenceRole
    content: str


@dataclass(frozen=True, slots=True)
class ProviderRequest:
    request_id: str
    manifest_id: str
    purpose: str
    provider_identity: ProviderIdentity
    records: tuple[ProviderContextRecord, ...]
    output_schema: str
    claim_ceiling: ClaimLevel
    action_ceiling: str
    retention: str = "ephemeral"
    tools: tuple[()] = ()


@dataclass(frozen=True, slots=True)
class ReflectionStatement:
    statement_id: str
    text: str
    supporting_evidence_ids: tuple[str, ...]
    uncertainty: str
    claim_level: ClaimLevel


@dataclass(frozen=True, slots=True)
class ProposalUnknown:
    unknown_id: str
    uncertainty: str


@dataclass(frozen=True, slots=True)
class ProposalQuestion:
    question_id: str
    unknown_id: str
    text: str


@dataclass(frozen=True, slots=True)
class ReflectionProposal:
    schema_version: str
    proposal_id: str
    status: ProposalStatus
    reflections: tuple[ReflectionStatement, ...]
    counterevidence_ids: tuple[str, ...]
    unknowns: tuple[ProposalUnknown, ...]
    questions: tuple[ProposalQuestion, ...]
    authority: str = "proposal_only"
    is_evidence: bool = False
    is_canonical: bool = False


@dataclass(frozen=True, slots=True)
class EvaluatedProposal:
    proposal: ReflectionProposal
    evaluation_status: ProposalStatus
    edited_text: str | None = None
    authority: str = "proposal_only"
    is_evidence: bool = False
    is_source_report: bool = False
    is_accepted_claim: bool = False
    is_canonical: bool = False


class ProposalValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


_PROHIBITED = {
    "diagnosis": ("diagnos",),
    "treatment": ("treatment", "treat this"),
    "therapy": ("therapy", "therapist"),
    "clinical_triage": ("triage", "clinical risk"),
    "medical_direction": (
        "medication",
        "medicine",
        "prescribe",
        "dose",
        "doctor says",
        " mg of ",
    ),
    "causal_claim": (" caused ", "because of", "root cause", "leads to"),
    "recommendation": (
        "you should",
        "you must",
        "i recommend",
        "try doing",
        "start journaling",
    ),
    "rescue_promise": ("i will monitor", "i'll monitor", "keep you safe", "call help for you"),
    "relationship_claim": ("your friend", "your confidant", "i care about you", "understand you better"),
}


def _exact_keys(value: Any, expected: set[str], code: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise ProposalValidationError(code)
    return value


def _bounded_text(value: Any, maximum: int, code: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise ProposalValidationError(code)
    return value.strip()


def _unique(values: tuple[str, ...], code: str) -> None:
    if len(values) != len(set(values)):
        raise ProposalValidationError(code)


def _validate_language(texts: tuple[str, ...]) -> None:
    joined = " ".join(texts).casefold()
    padded = f" {joined} "
    for code, terms in _PROHIBITED.items():
        if any(term in padded for term in terms):
            raise ProposalValidationError(code)


def validate_provider_output(raw: Any, manifest: ContextManifest) -> ReflectionProposal:
    top = _exact_keys(
        raw,
        {"schema_version", "proposal_id", "status", "reflections", "counterevidence", "unknowns", "questions"},
        "malformed_schema",
    )
    if top["schema_version"] != "e07-reflection-proposal-v1" or top["status"] != "PROPOSED":
        raise ProposalValidationError("malformed_schema")
    proposal_id = _bounded_text(top["proposal_id"], 128, "oversize_or_missing_field")
    if not isinstance(top["reflections"], list) or not 1 <= len(top["reflections"]) <= 4:
        raise ProposalValidationError("malformed_schema")
    roles = {item.record_id: item.role for item in manifest.records}
    selected_ids = set(roles)
    supporting = {key for key, role in roles.items() if role is EvidenceRole.SUPPORTING}
    required_counter = {key for key, role in roles.items() if role is EvidenceRole.COUNTEREVIDENCE}
    required_unknowns = {key for key, role in roles.items() if role is EvidenceRole.UNKNOWN}
    reflections: list[ReflectionStatement] = []
    all_text: list[str] = []
    for item in top["reflections"]:
        row = _exact_keys(item, {"statement_id", "text", "supporting_evidence_ids", "uncertainty", "claim_level"}, "unexpected_field")
        statement_id = _bounded_text(row["statement_id"], 128, "oversize_or_missing_field")
        text = _bounded_text(row["text"], 500, "oversize_or_missing_field")
        uncertainty = _bounded_text(row["uncertainty"], 240, "missing_uncertainty")
        ids_raw = row["supporting_evidence_ids"]
        if not isinstance(ids_raw, list) or not ids_raw or not all(isinstance(x, str) for x in ids_raw):
            raise ProposalValidationError("missing_supporting_evidence")
        ids = tuple(ids_raw)
        _unique(ids, "duplicate_id")
        if not set(ids) <= selected_ids:
            raise ProposalValidationError("invented_or_unselected_evidence")
        if not set(ids) <= supporting:
            raise ProposalValidationError("wrong_evidence_role")
        try:
            claim_level = ClaimLevel(row["claim_level"])
        except (TypeError, ValueError):
            raise ProposalValidationError("claim_ceiling_violation") from None
        if claim_level > manifest.claim_ceiling:
            raise ProposalValidationError("claim_ceiling_violation")
        reflections.append(ReflectionStatement(statement_id, text, ids, uncertainty, claim_level))
        all_text.extend((text, uncertainty))
    _unique(tuple(item.statement_id for item in reflections), "duplicate_id")
    counter_raw = top["counterevidence"]
    if not isinstance(counter_raw, list) or not all(isinstance(x, str) for x in counter_raw):
        raise ProposalValidationError("malformed_schema")
    counters = tuple(counter_raw)
    _unique(counters, "duplicate_id")
    if set(counters) != required_counter:
        raise ProposalValidationError("missing_or_invalid_counterevidence")
    unknown_items: list[ProposalUnknown] = []
    if not isinstance(top["unknowns"], list):
        raise ProposalValidationError("malformed_schema")
    for item in top["unknowns"]:
        row = _exact_keys(item, {"unknown_id", "uncertainty"}, "unexpected_field")
        unknown_id = _bounded_text(row["unknown_id"], 128, "oversize_or_missing_field")
        uncertainty = _bounded_text(row["uncertainty"], 240, "missing_uncertainty")
        unknown_items.append(ProposalUnknown(unknown_id, uncertainty))
        all_text.append(uncertainty)
    unknown_ids = tuple(item.unknown_id for item in unknown_items)
    _unique(unknown_ids, "duplicate_id")
    if set(unknown_ids) != required_unknowns:
        raise ProposalValidationError("missing_or_invalid_unknown")
    questions: list[ProposalQuestion] = []
    if not isinstance(top["questions"], list) or len(top["questions"]) > 3:
        raise ProposalValidationError("malformed_schema")
    for item in top["questions"]:
        row = _exact_keys(item, {"question_id", "unknown_id", "text"}, "unexpected_field")
        question_id = _bounded_text(row["question_id"], 128, "oversize_or_missing_field")
        unknown_id = _bounded_text(row["unknown_id"], 128, "oversize_or_missing_field")
        text = _bounded_text(row["text"], 240, "oversize_or_missing_field")
        if unknown_id not in required_unknowns:
            raise ProposalValidationError("question_not_linked_to_selected_unknown")
        if not text.endswith("?") or re.search(r"\b(should|must|recommend|diagnos|treat|therapy)\b", text, re.I):
            raise ProposalValidationError("directive_or_unsafe_question")
        questions.append(ProposalQuestion(question_id, unknown_id, text))
        all_text.append(text)
    _unique(tuple(item.question_id for item in questions), "duplicate_id")
    if manifest.action_ceiling != "disabled":
        raise ProposalValidationError("action_ceiling_violation")
    _validate_language(tuple(all_text))
    return ReflectionProposal(
        "e07-reflection-proposal-v1",
        proposal_id,
        ProposalStatus.PROPOSED,
        tuple(reflections),
        counters,
        tuple(unknown_items),
        tuple(questions),
    )


def evaluate_proposal(
    proposal: ReflectionProposal, action: EvaluationAction, *, edited_text: str | None = None
) -> EvaluatedProposal:
    states = {
        EvaluationAction.ACCEPT: ProposalStatus.ACCEPTED,
        EvaluationAction.EDIT: ProposalStatus.EDITED,
        EvaluationAction.REJECT: ProposalStatus.REJECTED,
        EvaluationAction.DISCARD: ProposalStatus.DISCARDED,
    }
    if action is EvaluationAction.EDIT:
        edited_text = _bounded_text(edited_text, 500, "oversize_or_missing_field")
        _validate_language((edited_text,))
    elif edited_text is not None:
        raise ProposalValidationError("unexpected_edit")
    return EvaluatedProposal(replace(proposal), states[action], edited_text)
