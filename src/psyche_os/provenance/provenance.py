"""Provenance layer — derivation, evidence linking, source tracking.

Implements typed provenance/derivation/evidence per DATA_MODEL.md §6–7.
Every derived output has a DerivationRun linking inputs to outputs.

F09 (FIX): Enforces canonical edge kinds, contradiction/correction/supersession
rules, and deterministic configuration digests. Rejects dangling/non-canonical
provenance references.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
from enum import Enum
import hashlib
from typing import Any

from psyche_os.domain.ids import (
    ActorId,
    DerivationId,
    RecordId,
    VersionId,
    generate_id,
)

# ---------------------------------------------------------------------------
# Canonical edge kinds — F09 provenance semantics
# ---------------------------------------------------------------------------


class EdgeKind(str, Enum):
    """Canonical provenance edge relations.

    Only these exact values may appear in provenance edges.
    Unknown/arbitrary strings are rejected.
    """

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    CONTEXTUALIZES = "contextualizes"
    DUPLICATES = "duplicates"
    IS_ALTERNATIVE_TO = "is_alternative_to"
    FAILS_TO_SUPPORT = "fails_to_support"
    CANNOT_DISCRIMINATE = "cannot_discriminate"
    CORRECTS = "corrects"
    SUPERSEDES = "supersedes"
    DERIVES_FROM = "derives_from"
    CORROBORATES = "corroborates"


CANONICAL_EDGE_KINDS = frozenset(e.value for e in EdgeKind)

# Edge kinds that indicate the target is invalidated or weakened
INVALIDATING_EDGES = frozenset(
    {
        "contradicts",
        "corrects",
        "supersedes",
        "fails_to_support",
    }
)

# Edge kinds that indicate the target is strengthened or confirmed
SUPPORTING_EDGES = frozenset(
    {
        "supports",
        "corroborates",
        "derives_from",
    }
)

# Reversible edge kinds — edges that have a natural inverse
REVERSIBLE_EDGES = {
    "supports": "supported_by",
    "contradicts": "contradicted_by",
    "corrects": "corrected_by",
    "supersedes": "superseded_by",
    "derives_from": "derives_to",
    "corroborates": "corroborated_by",
    "duplicates": "duplicated_by",
    "is_alternative_to": "has_alternative",
}


# Edge directness levels
class Directness(str, Enum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    TRANSITIVE = "transitive"


# Edge strength classes
class StrengthClass(str, Enum):
    STRONG = "strong"
    MODERATE = "moderate"
    WEAK = "weak"
    UNKNOWN = "unknown"


def validate_edge_kind(kind: str) -> bool:
    """Return True if the edge kind is canonical."""
    return kind in CANONICAL_EDGE_KINDS


def compute_config_digest(config: dict[str, Any]) -> str:
    """Compute a deterministic digest of a configuration dict.

    F09 (FIX): Handles nested dicts by canonicalizing to sorted JSON.
    Uses key-stable encoding (sorted keys) so the same logical config
    produces the same digest regardless of insertion order.
    """
    import json

    canonical = json.dumps(config, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Contradiction/supersession/correction rules — F09
# ---------------------------------------------------------------------------


class ContradictionSet:
    """Tracks conflicting claims and their resolution state.

    F09: When a contradiction edge is created, both claims are added to
    a contradiction set. Resolution requires one claim to be retracted or
    superseded, or a new claim that qualifies/synthesizes both.
    """

    def __init__(
        self,
        set_id: str = "",
        member_ids: list[RecordId] | None = None,
        resolution: str = "",
        resolved_by: RecordId | None = None,
    ) -> None:
        self.set_id = set_id or generate_id()
        self.member_ids: list[RecordId] = list(member_ids or [])
        self.resolution = resolution
        self.resolved_by = resolved_by

    def add_member(self, record_id: RecordId) -> None:
        """Add a member to the contradiction set if not already present."""
        sid = str(record_id)
        if sid not in [str(m) for m in self.member_ids]:
            self.member_ids.append(record_id)

    def resolve(self, resolution: str, resolved_by: RecordId) -> None:
        """Mark the contradiction as resolved."""
        if resolution not in ("retracted", "superseded", "synthesized", "qualified"):
            raise ValueError(f"Invalid contradiction resolution: {resolution}")
        self.resolution = resolution
        self.resolved_by = resolved_by

    @property
    def is_resolved(self) -> bool:
        return bool(self.resolution) and self.resolved_by is not None


def deduce_supersession_reason(
    old_claim_status: str,
    new_claim_status: str,
    edge_kind: str,
) -> str | None:
    """Deduce why a claim was superseded based on edge and status transitions.

    Returns None if no valid supersession chain can be established.
    """
    if edge_kind not in {"supersedes", "corrects"}:
        return None

    valid_new_statuses = {
        "superseded",
        "retracted",
        "disconfirmed",
        "resolved",
    }
    if old_claim_status not in valid_new_statuses:
        return (
            f"Supersession edge requires old claim status in "
            f"{valid_new_statuses}, got '{old_claim_status}'"
        )

    valid_old_statuses = {"proposed", "supported", "contradicted", "pending_review"}
    if new_claim_status not in valid_old_statuses:
        return (
            f"Superseding claim must have status in {valid_old_statuses}, got '{new_claim_status}'"
        )

    return None  # Valid supersession chain


def verify_provenance_closure(
    nodes: dict[str, ProvenanceNode],
    edges: list[dict[str, Any]],
) -> list[str]:
    """Verify provenance closure: every referenced record exists and no edges dangle.

    Returns a list of error messages (empty = valid).
    """
    errors: list[str] = []
    node_ids = set(nodes.keys())

    for edge in edges:
        src = edge.get("source_record_id", "")
        tgt = edge.get("target_record_id", "")

        if src not in node_ids:
            errors.append(f"Edge source '{src}' not found in provenance nodes")
        if tgt not in node_ids:
            errors.append(f"Edge target '{tgt}' not found in provenance nodes")

        kind = edge.get("relation", "")
        if kind not in CANONICAL_EDGE_KINDS:
            errors.append(
                f"Non-canonical edge kind '{kind}' — must be one of {sorted(CANONICAL_EDGE_KINDS)}"
            )

    return errors


@dataclass(frozen=True, slots=True)
class ProvenanceNode:
    """A node in the provenance graph."""

    record_id: RecordId
    version_id: VersionId
    record_kind: str  # type of entity
    parent_record_ids: list[RecordId] = field(default_factory=list)
    parent_version_ids: list[VersionId] = field(default_factory=list)
    derivation_id: DerivationId | None = None


@dataclass(frozen=True, slots=True)
class DerivationRecord:
    """Immutable derivation run record."""

    derivation_id: DerivationId = field(default_factory=lambda: DerivationId(generate_id()))
    method_kind: str = ""
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
    input_record_ids: list[RecordId] = field(default_factory=list)
    output_record_ids: list[RecordId] = field(default_factory=list)
    validation_outcomes: str = ""
    review_state: str = "pending"
    failure_reason: str = ""

    def add_output(self, record_id: RecordId) -> DerivationRecord:
        """Return a new DerivationRecord with an added output."""
        new_outputs = list(self.output_record_ids)
        if str(record_id) not in [str(o) for o in new_outputs]:
            new_outputs.append(record_id)
        return type(self)(
            derivation_id=self.derivation_id,
            method_kind=self.method_kind,
            code_rule_model_tool=self.code_rule_model_tool,
            code_rule_model_version=self.code_rule_model_version,
            parameters_config_digest=self.parameters_config_digest,
            environment_profile=self.environment_profile,
            started_at=self.started_at,
            ended_at=self.ended_at,
            actor_id=self.actor_id,
            purpose=self.purpose,
            input_record_ids=list(self.input_record_ids),
            output_record_ids=new_outputs,
            validation_outcomes=self.validation_outcomes,
            review_state=self.review_state,
            failure_reason=self.failure_reason,
        )

    def finalize(self) -> DerivationRecord:
        """Mark derivation as complete."""
        return type(self)(
            derivation_id=self.derivation_id,
            method_kind=self.method_kind,
            code_rule_model_tool=self.code_rule_model_tool,
            code_rule_model_version=self.code_rule_model_version,
            parameters_config_digest=self.parameters_config_digest,
            environment_profile=self.environment_profile,
            started_at=self.started_at,
            ended_at=datetime.datetime.now(datetime.UTC),
            actor_id=self.actor_id,
            purpose=self.purpose,
            input_record_ids=list(self.input_record_ids),
            output_record_ids=list(self.output_record_ids),
            validation_outcomes=self.validation_outcomes,
            review_state=self.review_state,
            failure_reason=self.failure_reason,
        )


@dataclass(frozen=True, slots=True)
class EvidenceGraph:
    """Typed evidence graph linking assertions/claims.

    Edges: supports, contradicts, qualifies, contextualizes,
    duplicates, is_alternative_to, fails_to_support, cannot_discriminate.
    """

    nodes: dict[str, ProvenanceNode] = field(default_factory=dict)
    edges: list[dict[str, Any]] = field(default_factory=list)

    def add_node(self, node: ProvenanceNode) -> EvidenceGraph:
        new_nodes = dict(self.nodes)
        new_nodes[str(node.record_id)] = node
        return EvidenceGraph(nodes=new_nodes, edges=list(self.edges))

    def add_edge(
        self,
        source_id: RecordId,
        target_id: RecordId,
        relation: str,
        directness: str = "direct",
        strength_class: str = "unknown",
        rationale: str = "",
    ) -> EvidenceGraph:
        # F09: Validate edge kind and both endpoints at mutation
        if relation not in CANONICAL_EDGE_KINDS:
            raise ValueError(
                f"Non-canonical edge kind '{relation}' — "
                f"must be one of {sorted(CANONICAL_EDGE_KINDS)}"
            )
        if not source_id:
            raise ValueError("Edge source must be a non-empty RecordId")
        if not target_id:
            raise ValueError("Edge target must be a non-empty RecordId")
        if str(source_id) == str(target_id):
            raise ValueError(f"Self-referencing provenance edge rejected: {source_id}")

        # F09: Reject provenance edges unless both endpoint IDs exist in the graph
        nodes_by_id = {str(n.record_id) for n in self.nodes.values()}
        src_s = str(source_id)
        tgt_s = str(target_id)
        if src_s not in nodes_by_id:
            raise ValueError(
                f"Provenance edge source '{src_s}' does not exist in the graph — "
                f"both endpoints must be present at mutation time"
            )
        if tgt_s not in nodes_by_id:
            raise ValueError(
                f"Provenance edge target '{tgt_s}' does not exist in the graph — "
                f"both endpoints must be present at mutation time"
            )

        new_edges = list(self.edges)
        new_edges.append(
            {
                "source_record_id": str(source_id),
                "target_record_id": str(target_id),
                "relation": relation,
                "directness": directness,
                "strength_class": strength_class,
                "rationale": rationale,
            }
        )
        return EvidenceGraph(nodes=dict(self.nodes), edges=new_edges)

    def get_supporting(self, record_id: RecordId) -> list[str]:
        """Get IDs of records that support the target."""
        sid = str(record_id)
        return [
            e["source_record_id"]
            for e in self.edges
            if e["target_record_id"] == sid and e["relation"] == "supports"
        ]

    def get_contradicting(self, record_id: RecordId) -> list[str]:
        """Get IDs of records that contradict the target."""
        sid = str(record_id)
        return [
            e["source_record_id"]
            for e in self.edges
            if e["target_record_id"] == sid and e["relation"] == "contradicts"
        ]

    def find_dependencies(self, record_id: RecordId) -> set[str]:
        """Find all records that depend on (derive from) the given record."""
        sid = str(record_id)
        result: set[str] = set()
        # Find direct children through derivation
        for node in self.nodes.values():
            if sid in [str(p) for p in node.parent_record_ids]:
                result.add(str(node.record_id))
        # Transitive closure
        added = True
        while added:
            added = False
            new_found: set[str] = set()
            for node in self.nodes.values():
                if any(p in result for p in [str(p) for p in node.parent_record_ids]):
                    nid = str(node.record_id)
                    if nid not in result:
                        new_found.add(nid)
                        added = True
            result |= new_found
        return result
