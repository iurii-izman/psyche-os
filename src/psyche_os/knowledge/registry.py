"""Knowledge registries, including the E04 metadata-only assessment path."""

from __future__ import annotations

from dataclasses import dataclass, field

from psyche_os.domain.assessments import (
    AssessmentGateEvaluator,
    AssessmentIdentity,
    AssessmentLifecycle,
    AssessmentRegistryEntry,
    AssessmentStatus,
    GateId,
    GateReasonCode,
    GateRecord,
    GateStatus,
    ReviewState,
    RightsMatrix,
    TranslationStatus,
)
from psyche_os.domain.ids import generate_id

# ---------------------------------------------------------------------------
# Ontology registry entry skeleton
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OntologyRegistryEntry:
    """A registered ontology with version and schema metadata."""

    entry_id: str = field(default_factory=lambda: generate_id())
    name: str = ""
    version: str = ""
    description: str = ""
    schema_uri: str = ""
    schema_hash: str = ""
    registered_at: str = ""
    registered_by: str = ""
    is_active: bool = True


# ---------------------------------------------------------------------------
# Knowledge snapshot skeleton
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    """A point-in-time snapshot of registered knowledge."""

    snapshot_id: str = field(default_factory=lambda: generate_id())
    created_at: str = ""
    vault_id: str = ""
    ontology_count: int = 0
    assessment_count: int = 0
    summary: str = ""
    blocked: bool = True


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class OntologyRegistry:
    """In-memory ontology registry for F0."""

    def __init__(self) -> None:
        self._entries: dict[str, OntologyRegistryEntry] = {}

    def register(self, entry: OntologyRegistryEntry) -> None:
        self._entries[str(entry.entry_id)] = entry

    def get(self, entry_id: str) -> OntologyRegistryEntry | None:
        return self._entries.get(entry_id)

    def list_active(self) -> list[OntologyRegistryEntry]:
        return [e for e in self._entries.values() if e.is_active]

    def count(self) -> int:
        return len(self._entries)


class AssessmentRegistry:
    """Versioned registry that cannot enable assessment use in the E04 profile."""

    def __init__(self, *, include_fixture: bool = True) -> None:
        self._entries: dict[tuple[str, str], AssessmentRegistryEntry] = {}
        self._evaluator = AssessmentGateEvaluator()
        if include_fixture:
            self.register(_fictional_metadata_fixture())

    def register(self, entry: AssessmentRegistryEntry) -> AssessmentStatus:
        """Validate and append one immutable typed version before mutation."""
        if not isinstance(entry, AssessmentRegistryEntry):
            raise TypeError("assessment registration requires the typed metadata contract")
        if not entry.identity.is_complete():
            raise ValueError("assessment identity is incomplete")
        if not entry.review_owner.strip():
            raise ValueError("assessment review owner is missing")
        if entry.lifecycle is AssessmentLifecycle.APPROVED_FOR_NAMED_USE:
            raise ValueError("approved lifecycle is unavailable in the metadata-only profile")

        status = self._evaluator.evaluate(entry)
        supplied_statuses = tuple(record.status for record in entry.gates)
        evaluated_statuses = tuple(record.status for record in status.evaluated_gates)
        if supplied_statuses != evaluated_statuses:
            raise ValueError("gate state contradicts deterministic fail-closed evaluation")
        if any(decision.allowed for decision in status.capabilities):
            raise ValueError("assessment capabilities are unavailable in the metadata-only profile")

        key = (entry.registry_id, entry.definition_version)
        if key in self._entries:
            raise ValueError("assessment definition version already exists")

        prior_versions = {
            version for registry_id, version in self._entries if registry_id == entry.registry_id
        }
        predecessor = entry.supersedes_definition_version
        if prior_versions and predecessor not in prior_versions:
            raise ValueError("new assessment version must name an existing predecessor")
        if not prior_versions and predecessor is not None:
            raise ValueError("initial assessment version cannot name a predecessor")
        if not prior_versions and entry.lifecycle not in {
            AssessmentLifecycle.DRAFT,
            AssessmentLifecycle.RIGHTS_PENDING,
        }:
            raise ValueError("initial assessment lifecycle must start at draft or rights_pending")
        if predecessor is not None:
            previous = self._entries[(entry.registry_id, predecessor)]
            allowed_transitions = {
                AssessmentLifecycle.DRAFT: {
                    AssessmentLifecycle.DRAFT,
                    AssessmentLifecycle.RIGHTS_PENDING,
                    AssessmentLifecycle.RESTRICTED,
                    AssessmentLifecycle.REVOKED,
                },
                AssessmentLifecycle.RIGHTS_PENDING: {
                    AssessmentLifecycle.RIGHTS_PENDING,
                    AssessmentLifecycle.VALIDATION_PENDING,
                    AssessmentLifecycle.RESTRICTED,
                    AssessmentLifecycle.DEPRECATED,
                    AssessmentLifecycle.REVOKED,
                },
                AssessmentLifecycle.VALIDATION_PENDING: {
                    AssessmentLifecycle.VALIDATION_PENDING,
                    AssessmentLifecycle.RESTRICTED,
                    AssessmentLifecycle.DEPRECATED,
                    AssessmentLifecycle.REVOKED,
                },
                AssessmentLifecycle.RESTRICTED: {
                    AssessmentLifecycle.RESTRICTED,
                    AssessmentLifecycle.RIGHTS_PENDING,
                    AssessmentLifecycle.DEPRECATED,
                    AssessmentLifecycle.REVOKED,
                },
                AssessmentLifecycle.DEPRECATED: {
                    AssessmentLifecycle.DEPRECATED,
                    AssessmentLifecycle.REVOKED,
                },
                AssessmentLifecycle.REVOKED: {AssessmentLifecycle.REVOKED},
                AssessmentLifecycle.APPROVED_FOR_NAMED_USE: set(),
            }
            if entry.lifecycle not in allowed_transitions[previous.lifecycle]:
                raise ValueError("assessment lifecycle transition is not allowed")
            if any(
                existing.supersedes_definition_version == predecessor
                for existing in self._entries.values()
            ):
                raise ValueError("assessment predecessor already has a successor")

        self._entries[key] = entry
        return status

    def get(self, registry_id: str, definition_version: str) -> AssessmentRegistryEntry | None:
        return self._entries.get((registry_id, definition_version))

    def status(self, registry_id: str, definition_version: str) -> AssessmentStatus | None:
        entry = self.get(registry_id, definition_version)
        return self._evaluator.evaluate(entry) if entry is not None else None

    def list_all(self) -> tuple[AssessmentRegistryEntry, ...]:
        return tuple(self._entries[key] for key in sorted(self._entries))

    def list_statuses(self) -> tuple[AssessmentStatus, ...]:
        return tuple(self._evaluator.evaluate(entry) for entry in self.list_all())

    def count(self) -> int:
        return len(self._entries)


def _fictional_metadata_fixture() -> AssessmentRegistryEntry:
    """Package-owned fictional metadata; it deliberately fails at P1."""
    gate_records = (
        GateRecord(
            gate_id=GateId.P0_IDENTITY_AND_USE,
            status=GateStatus.PASS,
            reason_code=GateReasonCode.IDENTITY_COMPLETE,
            evidence_reference_ids=("fixture_identity_metadata_v1",),
            review_state=ReviewState.APPROVED,
        ),
        GateRecord(
            gate_id=GateId.P1_RIGHTS,
            status=GateStatus.FAIL,
            reason_code=GateReasonCode.RIGHTS_MISSING_OR_DENIED,
            evidence_reference_ids=(),
            review_state=ReviewState.PENDING,
        ),
        *(
            GateRecord(
                gate_id=gate_id,
                status=GateStatus.NOT_EVALUATED,
                reason_code=GateReasonCode.UPSTREAM_GATE_BLOCKED,
                evidence_reference_ids=(),
                review_state=ReviewState.NOT_APPLICABLE,
            )
            for gate_id in tuple(GateId)[2:]
        ),
    )
    return AssessmentRegistryEntry(
        identity=AssessmentIdentity(
            registry_id="fictional_orchid_metadata",
            definition_version="1.0.0-metadata",
            title="Fictional Orchid Metadata Entry",
            owner="PSYCHE OS synthetic fixture package",
            construct="fictional metadata registry behavior",
            intended_use="fail-closed software verification only",
            target_population="fictional synthetic test context",
            language="zxx",
            locale="und",
            administration_mode="not_available",
            recall_period="not_applicable",
            official_source_reference="package:psyche_os.synthetic.e04",
        ),
        rights=RightsMatrix(),
        translation_status=TranslationStatus.UNKNOWN,
        lifecycle=AssessmentLifecycle.RIGHTS_PENDING,
        review_owner="data_steward_maintainer",
        review_state=ReviewState.PENDING,
        reviewed_on=None,
        review_due=None,
        supersedes_definition_version=None,
        gates=gate_records,
    )
