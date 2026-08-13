"""Domain entity types for the F0 schema boundary.

Implements the canonical minimum from DATA_MODEL.md:
Vault, Subject, Actor, SourceArtifact, BlobObject, SourceLocator,
Report, Observation, Assertion, Claim/ClaimVersion, EvidenceLink,
UncertaintyProfile, ContradictionSet, Unknown, DerivationRun,
DataPolicy, PolicyLineageEdge, AuditEvent, DeletionRequest/Plan/Receipt,
SchemaMigration, BackupManifest, ExportManifest, KnowledgeSource/Snapshot,
OntologyRegistryEntry, AssessmentRegistryEntry (metadata skeletons only).
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
from enum import Enum
from typing import Any

from psyche_os.domain.ids import (
    ActorId,
    BlobId,
    DerivationId,
    PolicyId,
    RecordId,
    SubjectId,
    VaultId,
    VersionId,
)
from psyche_os.domain.versions import VersionRow

# ---------------------------------------------------------------------------
# Vault, Subject, Actor
# ---------------------------------------------------------------------------


class DataMode(Enum):
    SYNTHETIC_ONLY = "synthetic_only"


@dataclass(frozen=True, slots=True)
class Vault:
    """Immutable vault profile — data_mode is set at creation and never changes."""

    vault_id: VaultId
    owner_subject_id: SubjectId
    data_mode: DataMode = DataMode.SYNTHETIC_ONLY
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


@dataclass(frozen=True, slots=True)
class Subject:
    """The person whose evidence is stored."""

    subject_id: SubjectId
    vault_id: VaultId


@dataclass(frozen=True, slots=True)
class Actor:
    """An actor who can perform actions (user, importer, system rule, etc.)."""

    actor_id: ActorId
    actor_kind: str  # user, system, import, derivation
    subject_id: SubjectId | None  # None for system actors


# ---------------------------------------------------------------------------
# Source and evidence aggregates
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ArtifactKind:
    code: (
        str  # user_note, document, image, audio, message_export, form, device_file, external_record
    )


@dataclass(frozen=True, slots=True)
class OriginKind:
    code: str  # user_created, imported, device_generated, clinician_provided


@dataclass(frozen=True, slots=True)
class SourceArtifact(VersionRow):
    """Immutable byte source with metadata."""

    artifact_kind: str = ""
    origin_kind: str = ""
    captured_at: datetime.datetime | None = None
    source_actor_id: ActorId | None = None
    language_tags: list[str] = field(default_factory=list)
    blob_id: BlobId | None = None
    original_filename_encrypted: str = ""
    declared_mime_type: str = ""
    observed_mime_type: str = ""
    byte_size: int = 0
    parser_state: str = "raw"  # raw, parsed, quarantined
    quarantine_state: str = "none"  # none, quarantined, released
    policy_id: PolicyId | None = None
    rights_note: str = ""
    replaces_artifact_id: RecordId | None = None
    is_corrected_copy_of_id: RecordId | None = None


@dataclass(frozen=True, slots=True)
class BlobObject:
    """Encrypted blob envelope metadata. No plaintext in database pages."""

    blob_id: BlobId
    cipher_suite: str = ""
    cipher_version: int = 1
    key_version: int = 1
    nonce_hex: str = ""
    authenticated_metadata_version: int = 1
    ciphertext_length: int = 0
    storage_locator: str = ""  # relative path within vault
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    integrity_state: str = "unknown"  # unknown, verified, failed
    plaintext_digest_keyed: str = ""  # keyed/encrypted, never plaintext


@dataclass(frozen=True, slots=True)
class SourceLocator(VersionRow):
    """Non-mutating range inside an artifact."""

    artifact_id: RecordId = field(default_factory=lambda: RecordId(""))
    locator_type: str = (
        ""  # page_paragraph, timestamp_range, message_id, cell_range, byte_extractor
    )
    locator_value: str = ""  # the actual reference
    extractor_name: str = ""
    extractor_version: str = ""


# ---------------------------------------------------------------------------
# Report, Observation, Measurement
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Report(VersionRow):
    """A statement attributed to an actor at a reported time."""

    report_kind: str = (
        ""  # autobiographical_memory, current_state, event_account, belief, goal, etc.
    )
    verbatim_blob_id: BlobId | None = None
    reporter_actor_id: ActorId | None = None
    subject_id: SubjectId | None = None
    perspective: str = "first_person"  # first_person, third_party, document_author, unknown
    language_tag: str = ""
    elicitation_method: str = ""
    source_locator_id: RecordId | None = None


@dataclass(frozen=True, slots=True)
class MemoryProfile(VersionRow):
    """Separate dimensions for autobiographical memory reports."""

    report_id: RecordId = field(default_factory=lambda: RecordId(""))
    subjective_belief: str = "unknown"  # low, moderate, high, unknown
    vividness: str = "unknown"
    temporal_precision: str = "unknown"
    source_attribution_clarity: str = "unknown"
    sensory_detail: str = "unknown"
    emotional_intensity_at_report: str = "unknown"
    independent_corroboration_state: str = "none"  # none, partial, independent
    conflict_state: str = "none"  # none, conflicting_reports, unresolved
    elicitation_suggestion_risk: str = "unknown"  # low, moderate, high, unknown


@dataclass(frozen=True, slots=True)
class Observation(VersionRow):
    """Bounded observation with observer, subject, construct, value, method, context."""

    observer_actor_id: ActorId | None = None
    subject_id: SubjectId | None = None
    construct_phenomenon: str = ""
    value_or_coded_state: str = ""
    method: str = ""
    context: str = ""
    observation_time: datetime.datetime | None = None
    quality_flags: list[str] = field(default_factory=list)
    source_locator_id: RecordId | None = None
    observation_kind: str = "self_observation"  # self_observation, external_observation, device_observation, clinician_observation


@dataclass(frozen=True, slots=True)
class Measurement(VersionRow):
    """Value produced under a named MeasurementProtocolVersion."""

    quantity_category: str = ""
    unit_code: str = ""  # UCUM-compatible
    value_numeric: str = ""  # Exact decimal as string to avoid float surprises
    resolution: str = ""
    device_instrument: str = ""
    calibration_algorithm_version: str = ""
    raw_reference: str = ""
    observed_window: str = ""
    missingness_flags: list[str] = field(default_factory=list)
    quality_flags: list[str] = field(default_factory=list)
    protocol_version_id: RecordId = field(default_factory=lambda: RecordId(""))


# ---------------------------------------------------------------------------
# Temporal
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TemporalAssertion(VersionRow):
    """Time as an assertion with provenance."""

    temporal_role: str = (
        ""  # occurred, observed, reported, recorded, asserted, effective, scheduled
    )
    value_kind: str = (
        ""  # instant, closed_interval, open_interval, calendar_period, recurring, unknown
    )
    lower_value: datetime.datetime | None = None
    upper_value: datetime.datetime | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = False
    precision: str = (
        "unknown"  # second, minute, hour, day, month, season, year, life_period, unknown
    )
    original_literal: str = ""  # Encrypted text where sensitive
    timezone_known: bool = False
    timezone_name: str = ""
    calendar: str = "gregorian"
    source_actor_id: ActorId | None = None
    assertion_actor_id: ActorId | None = None
    certainty_class: str = "unknown"  # certain, probable, possible, unknown, disputed
    certainty_rationale: str = ""
    target_record_id: RecordId = field(default_factory=lambda: RecordId(""))


# ---------------------------------------------------------------------------
# Assertion, Claim, Evidence, Uncertainty, Contradiction, Unknown
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Assertion(VersionRow):
    """Normalized, source-near statement with provenance."""

    subject: str = ""
    predicate: str = ""
    object_value: str = ""
    qualifiers: list[str] = field(default_factory=list)
    negation: bool = False
    modality: str = ""  # actual, possible, reported, hypothetical
    scope: str = ""
    source_locator_id: RecordId | None = None
    source_unavailable_reason: str = ""  # typed reason if no locator


class ClaimType(Enum):
    DESCRIPTIVE = "descriptive"
    PATTERN = "pattern"
    INTERPRETIVE = "interpretive"
    NARRATIVE = "narrative"
    STATISTICAL_ASSOCIATION = "statistical_association"
    CAUSAL_HYPOTHESIS = "causal_hypothesis"
    PREDICTION = "prediction"
    CLINICAL_MAPPING = "clinical_mapping"
    TRAIT_ESTIMATE = "trait_estimate"
    FUNCTIONING_ASSESSMENT = "functioning_assessment"
    STRENGTH_OR_RESOURCE = "strength_or_resource"
    RECOMMENDATION_CANDIDATE = "recommendation_candidate"


class ClaimStatus(Enum):
    PROPOSED = "proposed"
    USER_ACCEPTED = "user_accepted"
    ACTIVE = "active"
    CONTESTED = "contested"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"
    WITHDRAWN = "withdrawn"
    INVALIDATED = "invalidated"


class ClaimOrigin(Enum):
    USER = "user"
    DETERMINISTIC_RULE = "deterministic_rule"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    CLINICIAN_IMPORT = "clinician_import"
    LLM_PROPOSAL = "llm_proposal"
    MIXED = "mixed"


@dataclass(frozen=True, slots=True)
class Claim(VersionRow):
    """Interpretive, statistical, clinical, or verifiable claim."""

    claim_type: ClaimType = ClaimType.DESCRIPTIVE
    proposition: str = ""
    bounded_wording: str = ""
    population_scope: str = ""
    window_context: str = ""
    status: ClaimStatus = ClaimStatus.PROPOSED
    origin: ClaimOrigin = ClaimOrigin.USER
    uncertainty_profile_id: RecordId | None = None
    falsification_criteria: str = ""
    review_trigger: str = ""
    alternatives: str = ""
    counterfactual_cautions: str = ""


@dataclass(frozen=True, slots=True)
class EvidenceLink(VersionRow):
    """Typed link from evidence to a target claim."""

    source_record_id: RecordId = field(default_factory=lambda: RecordId(""))
    target_claim_id: RecordId = field(default_factory=lambda: RecordId(""))
    relation: str = ""  # supports, contradicts, qualifies, contextualizes, duplicates, is_alternative_to, fails_to_support, cannot_discriminate
    directness: str = "direct"  # direct, indirect, derived
    source_independence_group: str = ""
    scope_match: str = "unknown"  # exact, partial, different, unknown
    temporal_match: str = "unknown"
    strength_class: str = "unknown"
    rationale: str = ""
    author_actor_id: ActorId | None = None
    derivation_id: DerivationId | None = None


@dataclass(frozen=True, slots=True)
class UncertaintyProfile(VersionRow):
    """Multidimensional uncertainty — no generic confidence flag."""

    source_reliability: str = "unknown"
    measurement_error: str = "unknown"
    construct_validity: str = "unknown"
    temporal_uncertainty: str = "unknown"
    interpretation_ambiguity: str = "unknown"
    model_parameter_uncertainty: str = "unknown"
    confounding_causal_identification: str = "unknown"
    external_validity_population_transfer: str = "unknown"
    missingness_selection: str = "unknown"
    rights_version_uncertainty: str = "unknown"
    rationale: str = ""
    numeric_interval_estimand: str = ""
    numeric_interval_method: str = ""


class ContradictionResolution(Enum):
    UNRESOLVED = "unresolved"
    DIFFERENT_CONTEXTS = "different_contexts"
    DIFFERENT_TIMES = "different_times"
    SOURCE_ERROR = "source_error"
    SUPERSEDED = "superseded"
    BOTH_PARTLY_HOLD = "both_partly_hold"
    CANNOT_RESOLVE = "cannot_resolve"


@dataclass(frozen=True, slots=True)
class ContradictionSet(VersionRow):
    """Groups mutually inconsistent assertions/claims."""

    conflict_type: str = ""  # direct_contradiction, incompatible_values, mutually_exclusive
    scope: str = ""
    time_context: str = ""
    resolution_status: ContradictionResolution = ContradictionResolution.UNRESOLVED
    resolution_rationale: str = ""
    member_record_ids: list[RecordId] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Unknown(VersionRow):
    """A relevant unknown — question, scope, why it matters."""

    question: str = ""
    scope: str = ""
    why_matters: str = ""
    knowledge_state: str = ""
    attempts: str = ""
    what_could_reduce: str = ""
    burden_or_safety_concern: str = ""
    status: str = "open"
    unknown_reason: str = ""  # not_observed, not_asked, declined, forgotten, not_applicable, measurement_failed, source_unavailable, ambiguous, rights_blocked


@dataclass(frozen=True, slots=True)
class PersonalModelSnapshot(VersionRow):
    """Immutable, deterministic selection of pinned canonical versions."""

    evidence_transaction_cutoff: datetime.datetime | None = None
    domain_time_lower: datetime.datetime | None = None
    domain_time_upper: datetime.datetime | None = None
    domain_time_precision: str = "unknown"
    knowledge_snapshot_id: str = ""
    previous_snapshot_record_id: RecordId | None = None
    previous_snapshot_version_id: VersionId | None = None
    change_summary: str = ""
    user_review_status: str = "not_reviewed"
    generation_derivation_id: DerivationId | None = None


# ---------------------------------------------------------------------------
# Derivation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DerivationRun:
    """Immutable execution record linking inputs to outputs."""

    derivation_id: DerivationId
    method_kind: str = ""  # deterministic_rule, statistical_analysis, llm_proposal, manual
    code_rule_model_tool: str = ""
    code_rule_model_version: str = ""
    parameters_config_digest: str = ""
    environment_profile: str = ""
    started_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    ended_at: datetime.datetime | None = None
    actor_id: ActorId | None = None
    purpose: str = ""
    validation_outcomes: str = ""
    review_state: str = "pending"  # pending, validated, rejected
    failure_reason: str = ""


@dataclass(frozen=True, slots=True)
class DerivationInput:
    """Links an input record to a derivation run."""

    derivation_id: DerivationId
    input_record_id: RecordId
    input_version_id: VersionId | None = None
    role: str = ""  # primary, context, reference, calibration


@dataclass(frozen=True, slots=True)
class DerivationOutput:
    """Links a produced record to a derivation run."""

    derivation_id: DerivationId
    output_record_id: RecordId
    output_version_id: VersionId | None = None
    role: str = ""  # primary_result, intermediate, diagnostic, alternative


# ---------------------------------------------------------------------------
# Data Policy
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class DataPolicy(VersionRow):
    """Versioned orthogonal privacy policy axes — PS-01."""

    sensitivity: str = "sensitive"  # ordinary, sensitive, deeply_sensitive
    processing_location: str = "local_only"  # local_only, approved_cloud
    cloud_policy: str = "never_cloud"  # never_cloud, ask_each_time, named_purpose_and_provider
    purpose: str = ""
    purpose_expiry: datetime.datetime | None = None
    third_party_scope: str = "none"  # none, incidental, material
    retention_policy_id: str = ""
    retention_review_date: datetime.datetime | None = None
    export_rule: str = "block"  # allow, redact, block, ask
    export_audience: str = ""
    lineage_rule: str = "most_restrictive_parent"  # most_restrictive_parent
    legal_consent_basis_note: str = ""
    precedence: int = 0
    expiry: datetime.datetime | None = None


@dataclass(frozen=True, slots=True)
class PolicyLineageEdge:
    """Edge in the policy lineage DAG."""

    parent_policy_id: PolicyId
    child_policy_id: PolicyId
    derivation_id: DerivationId | None = None
    edge_kind: str = "derivation"  # derivation, containment, summarization, embedding, prediction


# ---------------------------------------------------------------------------
# Audit
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """Content-free allowlisted operational audit event — PS-15, PS-16."""

    event_id: str
    event_code: str
    occurred_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    actor_category: str = ""  # user, system, adapter
    actor_id: ActorId | None = None
    action_code: str = ""
    result_code: str = ""  # success, failure, conflict, blocked
    target_type: str = ""
    target_id: str = ""  # opaque ID
    policy_version: str = ""
    rule_version: str = ""
    schema_version: str = ""
    correlation_id: str = ""
    duration_ms_bucket: str = ""  # coarse bucket: <100ms, <1s, <10s, <60s, >60s
    size_bytes_bucket: str = ""


# ---------------------------------------------------------------------------
# Deletion
# ---------------------------------------------------------------------------


class DeletionScope(Enum):
    RECORD = "record"
    SOURCE_AND_DERIVATIVES = "source_and_derivatives"
    TIME_RANGE = "time_range"
    ALL_SUBJECT_DATA = "all_subject_data"
    VAULT = "vault"


@dataclass(frozen=True, slots=True)
class DeletionRequest:
    """Request for hard deletion with scope and roots."""

    request_id: DeletionRequestId
    root_record_ids: list[RecordId]
    scope: DeletionScope
    backup_policy: str = "expire_at_declared_horizon"
    external_copy_warning_shown: bool = False
    requested_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    requested_by_actor_id: ActorId | None = None


@dataclass(frozen=True, slots=True)
class DeletionPlan:
    """Content-free dry-run plan with counts by type."""

    plan_id: DeletionPlanId
    request_id: DeletionRequestId
    affected_counts_by_type: dict[str, int] = field(default_factory=dict)
    external_limitations: list[str] = field(default_factory=list)
    backup_expiry_horizon: str = ""
    generated_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


@dataclass(frozen=True, slots=True)
class DeletionReceipt:
    """Content-free record of completed deletion."""

    receipt_id: str
    request_id: DeletionRequestId
    plan_id: DeletionPlanId
    root_opaque_refs: list[str] = field(default_factory=list)
    counts_by_type: dict[str, int] = field(default_factory=dict)
    completion_status: str = "complete"  # complete, partial, failed
    projection_rebuild_state: str = "not_applicable"
    backup_expiry_horizon: str = ""
    known_exclusions: list[str] = field(default_factory=list)
    completed_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )


# ---------------------------------------------------------------------------
# Migration, Backup, Export
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SchemaMigration:
    """Versioned, checksummed, directional migration."""

    migration_id: MigrationId
    from_schema_version: int
    to_schema_version: int
    checksum: str = ""
    preconditions: list[str] = field(default_factory=list)
    forward_transform: str = ""
    validation_rules: list[str] = field(default_factory=list)
    rollback_strategy: str = ""
    data_loss_risk: str = "none"
    projection_rebuild_required: bool = False
    privacy_deletion_effects: str = ""
    minimum_reader_version: str = ""
    applied_at: datetime.datetime | None = None


@dataclass(frozen=True, slots=True)
class BackupManifest:
    """Authenticated backup package metadata."""

    backup_id: BackupId
    vault_id: VaultId
    schema_version: int
    app_version: str = ""
    key_wrap_version: int = 1
    package_format: str = "psyche_backup_v1"
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    transaction_cutoff: datetime.datetime | None = None
    encrypted_entries: list[str] = field(default_factory=list)
    authenticated_inventory_digest: str = ""
    retention_policy: str = ""
    expiry_date: datetime.datetime | None = None
    recovery_method: str = "argon2id_recovery_wrap"
    restore_test_history: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class ExportManifest:
    """Versioned logical export metadata."""

    export_id: ExportId
    vault_id: VaultId
    schema_version: int
    app_version: str = ""
    export_format: str = "psyche_export_v1"
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    transaction_cutoff: datetime.datetime | None = None
    audience: str = "personal_archive"
    knowledge_snapshot_id: KnowledgeSnapshotId | None = None
    record_count: int = 0
    blob_count: int = 0
    schemas_included: list[str] = field(default_factory=list)
    checksum_algorithm: str = "sha256"
    entry_checksums: dict[str, str] = field(default_factory=dict)
    synthetic_fixture: bool = True


# ---------------------------------------------------------------------------
# Knowledge metadata skeletons
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class KnowledgeSource:
    """Versioned scientific source metadata — no personal evidence."""

    source_id: KnowledgeSourceId
    citation: str = ""
    version_date: str = ""
    evidence_type: str = ""  # S1–S8
    population: str = ""
    limitations: str = ""
    currentness_review_date: str = ""
    rights: str = ""
    retraction_state: str = "not_retracted"
    local_storage_permitted: bool = True


@dataclass(frozen=True, slots=True)
class KnowledgeSnapshot:
    """Immutable manifest of source/ontology/instrument/algorithm versions."""

    snapshot_id: KnowledgeSnapshotId
    created_at: datetime.datetime = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC)
    )
    source_ids: list[KnowledgeSourceId] = field(default_factory=list)
    ontology_registry_version: str = ""
    ontology_registry_digest: str = ""
    description: str = ""


@dataclass(frozen=True, slots=True)
class OntologyRegistryEntry:
    """Metadata skeleton for a domain concept — no scientific content expansion."""

    domain_id: str
    layer: str
    labels: dict[str, str] = field(default_factory=dict)
    definition: str = ""
    non_goals: list[str] = field(default_factory=list)
    allowed_evidence_kinds: list[str] = field(default_factory=list)
    allowed_claim_types: list[str] = field(default_factory=list)
    sensitivity_default: str = "sensitive"
    review_status: str = "accepted_with_limits"
    review_due: str = ""


@dataclass(frozen=True, slots=True)
class AssessmentRegistryEntry:
    """Metadata skeleton — default blocked; no item/scoring/content fields."""

    registry_id: str
    title: str = ""
    abbreviation: str = ""
    construct: str = ""
    intended_use: str = ""
    version: str = ""
    authors_publisher: str = ""
    item_content_rights: str = "unknown"
    scoring_rights: str = "unknown"
    permitted_storage: str = "none"
    permitted_display: str = "none"
    permitted_export: str = "none"
    official_source: str = ""
    languages: list[str] = field(default_factory=list)
    translation_status: str = "unknown"
    target_population: str = ""
    administration_modes: list[str] = field(default_factory=list)
    recall_period: str = ""
    status: str = "blocked"  # Default blocked — requires rights/version/validation gates
    review_date: str = ""
