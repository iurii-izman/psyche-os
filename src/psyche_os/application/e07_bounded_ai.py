"""E07 application boundary: policy first, exact opt-in, one provider call."""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from enum import StrEnum
from typing import Any, Protocol

from psyche_os.domain.ai_proposal import (
    ContextManifest,
    DisclosureAuthorization,
    DisclosurePreview,
    EvidenceRole,
    ManifestRecord,
    ProviderContextRecord,
    ProviderIdentity,
    ProviderRequest,
    ReflectionProposal,
    identity_digest,
    validate_provider_output,
)
from psyche_os.domain.experiments import ClaimLevel
from psyche_os.domain.ids import PolicyId
from psyche_os.policy.engine import (
    CloudPolicy,
    PolicyAxes,
    PolicyCompositionError,
    resolve_with_own_policy,
)

PURPOSE = "synthetic_evidence_grounded_reflection"
CONTEXT_BUILDER_VERSION = "e07-explicit-selection-v1"
OUTPUT_SCHEMA = "e07-reflection-proposal-v1"
TRANSFORMATIONS = ("role_tagging", "bounded_record_serialization")
ALLOWED_ROLES_BY_CATEGORY: dict[str, tuple[EvidenceRole, ...]] = {
    "assertion": (EvidenceRole.SUPPORTING, EvidenceRole.COUNTEREVIDENCE),
    "unknown": (EvidenceRole.UNKNOWN,),
}


class E07ErrorCode(StrEnum):
    INVALID_PURPOSE = "invalid_purpose"
    INVALID_SELECTION = "invalid_selection"
    RECORD_NOT_FOUND = "record_not_found"
    STALE_VERSION = "stale_version"
    POLICY_BLOCKED = "policy_blocked"
    POLICY_EXPIRED = "policy_expired"
    PROVIDER_NOT_APPROVED = "provider_not_approved"
    PROVIDER_RETIRED = "provider_retired"
    REGRESSION_NOT_EVALUATED = "regression_not_evaluated"
    AUTHORIZATION_MISMATCH = "authorization_mismatch"
    AUTHORIZATION_EXPIRED = "authorization_expired"
    AUTHORIZATION_CONSUMED = "authorization_consumed"
    INTERACTION_REUSED = "interaction_reused"
    POLICY_STALE = "policy_stale"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    OUTPUT_REJECTED = "output_rejected"


class E07BoundaryError(RuntimeError):
    def __init__(self, code: E07ErrorCode, detail: str = "") -> None:
        super().__init__(code.value)
        self.code = code
        self.detail = detail


class ProviderUnavailableError(RuntimeError):
    pass


class ProviderTimeoutError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CanonicalRecordMetadata:
    record_id: str
    version_id: str
    category: str
    own_policy_id: str
    own_policy: PolicyAxes
    own_policy_version_id: str
    parent_policies: tuple[tuple[str, str, PolicyAxes], ...] = ()


class CanonicalRecordReader(Protocol):
    def read_metadata(self, record_id: str) -> CanonicalRecordMetadata | None: ...

    def read_content(self, record_id: str, version_id: str) -> str: ...


class ReflectionProvider(Protocol):
    def invoke(self, request: ProviderRequest) -> Any: ...


@dataclass(frozen=True, slots=True)
class ProviderRegistryEntry:
    identity: ProviderIdentity
    policy_snapshot: str
    knowledge_snapshot: str
    safety_policy: str
    approved: bool
    evaluated_identity_digest: str
    status: str = "approved"
    claim_ceiling: ClaimLevel = ClaimLevel.C0_OBSERVATION
    action_ceiling: str = "disabled"

    @property
    def exact_evaluation_passed(self) -> bool:
        return self.evaluated_identity_digest == self.identity.digest


class ProviderRegistry:
    def __init__(self, entries: tuple[ProviderRegistryEntry, ...]) -> None:
        self._entries = {item.identity.digest: item for item in entries}

    def resolve(self, identity: ProviderIdentity) -> ProviderRegistryEntry:
        entry = self._entries.get(identity.digest)
        if entry is None or not entry.approved:
            raise E07BoundaryError(E07ErrorCode.PROVIDER_NOT_APPROVED)
        if entry.status != "approved":
            raise E07BoundaryError(E07ErrorCode.PROVIDER_RETIRED)
        if not entry.exact_evaluation_passed:
            raise E07BoundaryError(E07ErrorCode.REGRESSION_NOT_EVALUATED)
        return entry

    def remove(self, identity: ProviderIdentity) -> None:
        self._entries.pop(identity.digest, None)

    def revoke_policy(self, identity: ProviderIdentity) -> None:
        entry = self._entries.get(identity.digest)
        if entry is not None:
            self._entries[identity.digest] = ProviderRegistryEntry(
                identity=entry.identity,
                policy_snapshot=entry.policy_snapshot,
                knowledge_snapshot=entry.knowledge_snapshot,
                safety_policy=entry.safety_policy,
                approved=False,
                evaluated_identity_digest=entry.evaluated_identity_digest,
                status=entry.status,
                claim_ceiling=entry.claim_ceiling,
                action_ceiling=entry.action_ceiling,
            )


@dataclass(frozen=True, slots=True)
class PreparedDisclosure:
    interaction_id: str
    manifest: ContextManifest
    preview: DisclosurePreview


@dataclass(frozen=True, slots=True)
class AIInteractionEnvelope:
    interaction_id: str
    session_id: str | None
    turn_id: str | None
    purpose: str
    context_manifest_id: str
    provider_identity: ProviderIdentity
    model_snapshot: str
    config_snapshot: str
    policy_snapshot: str
    knowledge_snapshot: str
    safety_policy: str
    claim_ceiling: ClaimLevel
    action_ceiling: str
    disclosure_receipt_id: str
    proposal_id: str
    proposal_status: str
    retention: str = "ephemeral"


@dataclass(frozen=True, slots=True)
class DisclosureReceipt:
    receipt_id: str
    interaction_id: str
    purpose: str
    selected: tuple[tuple[str, str, str], ...]
    selected_count: int
    provider_identity_digest: str
    policy_snapshot: str
    occurred_at: dt.datetime
    outcome: str


@dataclass(frozen=True, slots=True)
class BoundedAIResult:
    envelope: AIInteractionEnvelope
    proposal: ReflectionProposal
    receipt: DisclosureReceipt


class BoundedAIProposalService:
    def __init__(
        self,
        reader: CanonicalRecordReader,
        registry: ProviderRegistry,
        provider: ReflectionProvider,
    ) -> None:
        self._reader = reader
        self._registry = registry
        self._provider = provider
        self._pending_prepared: dict[str, PreparedDisclosure] = {}
        self._issued_authorizations: dict[
            str, tuple[PreparedDisclosure, DisclosureAuthorization]
        ] = {}
        self._interaction_ids: set[str] = set()
        self._consumed_authorizations: set[str] = set()
        self.receipts: list[DisclosureReceipt] = []
        self.events: list[dict[str, str]] = []

    def prepare(
        self,
        *,
        interaction_id: str,
        purpose: str,
        selected: tuple[tuple[str, EvidenceRole], ...],
        provider_identity: ProviderIdentity,
        cutoff: dt.datetime,
    ) -> PreparedDisclosure:
        if purpose != PURPOSE:
            raise E07BoundaryError(E07ErrorCode.INVALID_PURPOSE)
        if interaction_id in self._interaction_ids:
            raise E07BoundaryError(E07ErrorCode.INTERACTION_REUSED)
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise E07BoundaryError(E07ErrorCode.INVALID_SELECTION)
        ids = tuple(record_id for record_id, _ in selected)
        if len(ids) != len(set(ids)) or not ids or len(ids) > 8:
            raise E07BoundaryError(E07ErrorCode.INVALID_SELECTION)
        roles = {role for _, role in selected}
        if roles != {EvidenceRole.SUPPORTING, EvidenceRole.COUNTEREVIDENCE, EvidenceRole.UNKNOWN}:
            raise E07BoundaryError(E07ErrorCode.INVALID_SELECTION)
        entry = self._registry.resolve(provider_identity)
        records: list[ManifestRecord] = []
        policy_material: list[dict[str, Any]] = []
        for record_id, role in selected:
            metadata = self._reader.read_metadata(record_id)
            if metadata is None:
                raise E07BoundaryError(E07ErrorCode.RECORD_NOT_FOUND)
            policy = self._resolve_policy(metadata, purpose=purpose, at=cutoff)
            records.append(
                ManifestRecord(
                    metadata.record_id,
                    metadata.version_id,
                    metadata.category,
                    role,
                    metadata.own_policy_id,
                )
            )
            policy_material.append(policy)
        policy_decision_id = identity_digest(
            {
                "policy_snapshot": entry.policy_snapshot,
                "records": policy_material,
                "purpose": purpose,
            }
        )
        manifest = ContextManifest.create(
            purpose=purpose,
            records=tuple(records),
            cutoff=cutoff,
            policy_decision_id=policy_decision_id,
            provider_identity=provider_identity,
            context_builder_version=CONTEXT_BUILDER_VERSION,
            claim_ceiling=entry.claim_ceiling,
            action_ceiling=entry.action_ceiling,
        )
        prepared = PreparedDisclosure(
            interaction_id,
            manifest,
            DisclosurePreview.create(manifest, TRANSFORMATIONS),
        )
        self._interaction_ids.add(interaction_id)
        self._pending_prepared[interaction_id] = prepared
        return prepared

    def list_eligible(self, *, cutoff: dt.datetime) -> list[dict[str, Any]]:
        """Read-only enumeration of currently policy-eligible canonical records.

        The backend owns eligibility; a renderer cannot decide cloud eligibility.
        No network and no disclosure occur here.
        """
        if cutoff.tzinfo is None or cutoff.utcoffset() is None:
            raise E07BoundaryError(E07ErrorCode.INVALID_SELECTION)
        eligible: list[dict[str, Any]] = []
        for record_id in self._reader.enumerate_ids():
            metadata = self._reader.read_metadata(record_id)
            if metadata is None:
                continue
            try:
                self._resolve_policy(metadata, purpose=PURPOSE, at=cutoff)
            except E07BoundaryError:
                continue
            try:
                display_text = self._reader.read_content(record_id, metadata.version_id)
            except KeyError:
                continue
            eligible.append(
                {
                    "record_id": metadata.record_id,
                    "version_id": metadata.version_id,
                    "category": metadata.category,
                    "allowed_roles": [
                        role.value
                        for role in ALLOWED_ROLES_BY_CATEGORY.get(metadata.category, ())
                    ],
                    "display_text": display_text[:160],
                }
            )
        return eligible

    def category_for(self, record_id: str) -> str | None:
        metadata = self._reader.read_metadata(record_id)
        return metadata.category if metadata is not None else None

    def authorize(
        self,
        prepared: PreparedDisclosure,
        *,
        authorized_at: dt.datetime,
        expires_at: dt.datetime,
        opt_in: bool,
    ) -> DisclosureAuthorization:
        if self._pending_prepared.get(prepared.interaction_id) is not prepared:
            raise E07BoundaryError(E07ErrorCode.AUTHORIZATION_MISMATCH)
        if (
            authorized_at.tzinfo is None
            or authorized_at.utcoffset() is None
            or expires_at.tzinfo is None
            or expires_at.utcoffset() is None
            or not opt_in
            or expires_at <= authorized_at
        ):
            raise E07BoundaryError(E07ErrorCode.AUTHORIZATION_EXPIRED)
        authorization_id = identity_digest(
            {
                "interaction_id": prepared.interaction_id,
                "preview_id": prepared.preview.preview_id,
                "authorized_at": authorized_at.isoformat(),
                "expires_at": expires_at.isoformat(),
            }
        )
        authorization = DisclosureAuthorization(
            authorization_id, prepared.preview.preview_id, authorized_at, expires_at
        )
        del self._pending_prepared[prepared.interaction_id]
        self._issued_authorizations[authorization_id] = (prepared, authorization)
        return authorization

    def execute(
        self,
        prepared: PreparedDisclosure,
        authorization: DisclosureAuthorization,
        *,
        now: dt.datetime,
        session_id: str | None = None,
        turn_id: str | None = None,
    ) -> BoundedAIResult:
        if authorization.authorization_id in self._consumed_authorizations:
            raise E07BoundaryError(E07ErrorCode.AUTHORIZATION_CONSUMED)
        issued = self._issued_authorizations.get(authorization.authorization_id)
        if (
            issued is None
            or issued[0] is not prepared
            or issued[1] is not authorization
            or authorization.preview_id != prepared.preview.preview_id
        ):
            raise E07BoundaryError(E07ErrorCode.AUTHORIZATION_MISMATCH)
        del self._issued_authorizations[authorization.authorization_id]
        self._consumed_authorizations.add(authorization.authorization_id)
        if now.tzinfo is None or now.utcoffset() is None:
            raise E07BoundaryError(E07ErrorCode.AUTHORIZATION_EXPIRED)
        if now < authorization.authorized_at or now > authorization.expires_at:
            raise E07BoundaryError(E07ErrorCode.AUTHORIZATION_EXPIRED)
        entry = self._registry.resolve(prepared.manifest.provider_identity)
        policy_material: list[dict[str, Any]] = []
        for pinned in prepared.manifest.records:
            current = self._reader.read_metadata(pinned.record_id)
            if (
                current is None
                or current.version_id != pinned.version_id
                or current.category != pinned.category
            ):
                raise E07BoundaryError(E07ErrorCode.STALE_VERSION)
            try:
                policy_material.append(
                    self._resolve_policy(current, purpose=prepared.manifest.purpose, at=now)
                )
            except E07BoundaryError as exc:
                if exc.code in {E07ErrorCode.POLICY_BLOCKED, E07ErrorCode.POLICY_EXPIRED}:
                    raise E07BoundaryError(E07ErrorCode.POLICY_STALE) from None
                raise
        current_policy_decision_id = identity_digest(
            {
                "policy_snapshot": entry.policy_snapshot,
                "records": policy_material,
                "purpose": prepared.manifest.purpose,
            }
        )
        if current_policy_decision_id != prepared.manifest.policy_decision_id:
            raise E07BoundaryError(E07ErrorCode.POLICY_STALE)
        context = tuple(
            ProviderContextRecord(
                item.record_id,
                item.version_id,
                item.category,
                item.role,
                self._reader.read_content(item.record_id, item.version_id),
            )
            for item in prepared.manifest.records
        )
        request = ProviderRequest(
            request_id=authorization.authorization_id,
            manifest_id=prepared.manifest.manifest_id,
            purpose=prepared.manifest.purpose,
            provider_identity=prepared.manifest.provider_identity,
            records=context,
            output_schema=OUTPUT_SCHEMA,
            claim_ceiling=prepared.manifest.claim_ceiling,
            action_ceiling=prepared.manifest.action_ceiling,
        )
        try:
            raw = self._provider.invoke(request)
        except ProviderTimeoutError:
            self._record_receipt(prepared, entry, now, "provider_timeout")
            raise E07BoundaryError(E07ErrorCode.PROVIDER_TIMEOUT) from None
        except ProviderUnavailableError:
            self._record_receipt(prepared, entry, now, "provider_unavailable")
            raise E07BoundaryError(E07ErrorCode.PROVIDER_UNAVAILABLE) from None
        try:
            proposal = validate_provider_output(raw, prepared.manifest)
        except ValueError as exc:
            self._record_receipt(prepared, entry, now, "output_rejected")
            raise E07BoundaryError(E07ErrorCode.OUTPUT_REJECTED, str(exc)) from None
        receipt = self._record_receipt(prepared, entry, now, "proposed")
        envelope = AIInteractionEnvelope(
            interaction_id=prepared.interaction_id,
            session_id=session_id,
            turn_id=turn_id,
            purpose=prepared.manifest.purpose,
            context_manifest_id=prepared.manifest.manifest_id,
            provider_identity=prepared.manifest.provider_identity,
            model_snapshot=prepared.manifest.provider_identity.model_snapshot,
            config_snapshot=prepared.manifest.provider_identity.config_snapshot,
            policy_snapshot=entry.policy_snapshot,
            knowledge_snapshot=entry.knowledge_snapshot,
            safety_policy=entry.safety_policy,
            claim_ceiling=prepared.manifest.claim_ceiling,
            action_ceiling=prepared.manifest.action_ceiling,
            disclosure_receipt_id=receipt.receipt_id,
            proposal_id=proposal.proposal_id,
            proposal_status=proposal.status.value,
        )
        return BoundedAIResult(envelope, proposal, receipt)

    @staticmethod
    def _resolve_policy(
        metadata: CanonicalRecordMetadata, *, purpose: str, at: dt.datetime
    ) -> dict[str, Any]:
        try:
            resolution = resolve_with_own_policy(
                metadata.own_policy,
                PolicyId(metadata.own_policy_id),
                [policy for _, _, policy in metadata.parent_policies],
                [PolicyId(policy_id) for policy_id, _, _ in metadata.parent_policies],
            )
        except (PolicyCompositionError, ValueError):
            raise E07BoundaryError(E07ErrorCode.POLICY_BLOCKED) from None
        effective = resolution.effective
        if (
            resolution.is_never_cloud
            or effective.processing_location.value != "approved_cloud"
            or effective.cloud_policy
            not in {CloudPolicy.ASK_EACH_TIME, CloudPolicy.NAMED_PURPOSE_AND_PROVIDER}
            or effective.purpose != purpose
        ):
            raise E07BoundaryError(E07ErrorCode.POLICY_BLOCKED)
        expiry = effective.purpose_expiry
        if (
            expiry is None
            or expiry.tzinfo is None
            or expiry.utcoffset() is None
            or expiry <= at
        ):
            raise E07BoundaryError(E07ErrorCode.POLICY_EXPIRED)
        return {
            "record_id": metadata.record_id,
            "version_id": metadata.version_id,
            "own_policy": metadata.own_policy_id,
            "own_policy_version": metadata.own_policy_version_id,
            "parents": [
                {"policy_id": policy_id, "version_id": version_id}
                for policy_id, version_id, _ in metadata.parent_policies
            ],
            "effective": {
                "processing_location": effective.processing_location.value,
                "cloud_policy": effective.cloud_policy.value,
                "purpose": effective.purpose,
                "purpose_expiry": expiry.isoformat(),
                "retention_policy_id": effective.retention_policy_id,
                "lineage_rule": effective.lineage_rule,
            },
        }

    def _record_receipt(
        self,
        prepared: PreparedDisclosure,
        entry: ProviderRegistryEntry,
        occurred_at: dt.datetime,
        outcome: str,
    ) -> DisclosureReceipt:
        receipt = DisclosureReceipt(
            receipt_id=identity_digest(
                {
                    "interaction_id": prepared.interaction_id,
                    "manifest_id": prepared.manifest.manifest_id,
                    "outcome": outcome,
                    "occurred_at": occurred_at.isoformat(),
                }
            ),
            interaction_id=prepared.interaction_id,
            purpose=prepared.manifest.purpose,
            selected=prepared.preview.selected,
            selected_count=len(prepared.preview.selected),
            provider_identity_digest=prepared.manifest.provider_identity.digest,
            policy_snapshot=entry.policy_snapshot,
            occurred_at=occurred_at,
            outcome=outcome,
        )
        self.receipts.append(receipt)
        self.events.append(
            {
                "event_code": "e07_provider_boundary",
                "correlation_id": prepared.interaction_id,
                "result": outcome,
                "component_version": CONTEXT_BUILDER_VERSION,
            }
        )
        return receipt
