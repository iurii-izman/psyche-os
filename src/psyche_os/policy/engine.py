"""Policy engine — orthogonal data policy and NEVER_CLOUD lineage.

Implements PS-01–PS-03:
- Orthogonal axes: sensitivity, processing location, cloud policy, purpose,
  third-party scope, retention, export/redaction, lineage
- Deterministic fail-closed composition
- NEVER_CLOUD transitive inheritance through reconstructive descendants
- Missing/unknown/contradictory policy fails closed
- Declassification does not exist in F0

FIX (F06): resolve_derived_policy now always combines the node's OWN policy
with all ancestors. A child can NEVER weaken NEVER_CLOUD. Third-party scope
ordering is most-restrictive-first (NONE < INCIDENTAL < MATERIAL). All axes
(sensitivity, processing_location, cloud_policy, purpose, third_party_scope,
retention, export_rule, audience, lineage_rule) are preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
from enum import Enum

from psyche_os.domain.ids import PolicyId

# ---------------------------------------------------------------------------
# Policy axes
# ---------------------------------------------------------------------------


class Sensitivity(str, Enum):
    ORDINARY = "ordinary"
    SENSITIVE = "sensitive"
    DEEPLY_SENSITIVE = "deeply_sensitive"

    @classmethod
    def most_restrictive(cls, a: Sensitivity, b: Sensitivity) -> Sensitivity:
        order = {cls.ORDINARY: 0, cls.SENSITIVE: 1, cls.DEEPLY_SENSITIVE: 2}
        return a if order[a] >= order[b] else b


class ProcessingLocation(str, Enum):
    LOCAL_ONLY = "local_only"
    APPROVED_CLOUD = "approved_cloud"

    @classmethod
    def most_restrictive(cls, a: ProcessingLocation, b: ProcessingLocation) -> ProcessingLocation:
        # local_only is more restrictive than approved_cloud
        if a == cls.LOCAL_ONLY or b == cls.LOCAL_ONLY:
            return cls.LOCAL_ONLY
        return cls.APPROVED_CLOUD


class CloudPolicy(str, Enum):
    NEVER_CLOUD = "never_cloud"
    ASK_EACH_TIME = "ask_each_time"
    NAMED_PURPOSE_AND_PROVIDER = "named_purpose_and_provider"

    @classmethod
    def most_restrictive(cls, a: CloudPolicy, b: CloudPolicy) -> CloudPolicy:
        order = {
            cls.NEVER_CLOUD: 0,
            cls.ASK_EACH_TIME: 1,
            cls.NAMED_PURPOSE_AND_PROVIDER: 2,
        }
        return a if order[a] <= order[b] else b


class ThirdPartyScope(str, Enum):
    NONE = "none"
    INCIDENTAL = "incidental"
    MATERIAL = "material"

    @classmethod
    def most_restrictive(cls, a: ThirdPartyScope, b: ThirdPartyScope) -> ThirdPartyScope:
        # F06: MATERIAL involvement persists — once a third party has material
        # access, combining with NONE does NOT erase that involvement.
        # The normative rule: MATERIAL + NONE → MATERIAL.
        # INCIDENTAL + NONE → INCIDENTAL (incidental access also persists).
        # Order: NONE < INCIDENTAL < MATERIAL for persistence;
        # the "most restrictive" from a data-protection standpoint is the
        # highest level of actual third-party involvement that occurred.
        order = {cls.NONE: 0, cls.INCIDENTAL: 1, cls.MATERIAL: 2}
        return a if order[a] >= order[b] else b


class ExportRule(str, Enum):
    BLOCK = "block"
    ASK = "ask"
    REDACT = "redact"
    ALLOW = "allow"

    @classmethod
    def most_restrictive(cls, a: ExportRule, b: ExportRule) -> ExportRule:
        order = {cls.BLOCK: 0, cls.ASK: 1, cls.REDACT: 2, cls.ALLOW: 3}
        return a if order[a] <= order[b] else b


# ---------------------------------------------------------------------------
# Policy value
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyAxes:
    """The orthogonal axes of a data policy — PS-01.

    All axes are preserved through composition. No axis is dropped.
    """

    sensitivity: Sensitivity = Sensitivity.SENSITIVE
    processing_location: ProcessingLocation = ProcessingLocation.LOCAL_ONLY
    cloud_policy: CloudPolicy = CloudPolicy.NEVER_CLOUD
    purpose: str = ""
    purpose_expiry: datetime.datetime | None = None
    third_party_scope: ThirdPartyScope = ThirdPartyScope.NONE
    retention_policy_id: str = ""
    retention_review_date: datetime.datetime | None = None
    export_rule: ExportRule = ExportRule.BLOCK
    export_audience: str = ""
    lineage_rule: str = "most_restrictive_parent"


# ---------------------------------------------------------------------------
# Policy composition engine
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyResolution:
    """Result of resolving a derived item's effective policy from self + parents."""

    effective: PolicyAxes
    own_policy_id: PolicyId
    parent_ids: list[PolicyId]
    resolution_method: str  # "leaf_policy" | "most_restrictive_meet"
    warnings: list[str] = field(default_factory=list)

    @property
    def is_never_cloud(self) -> bool:
        return self.effective.cloud_policy == CloudPolicy.NEVER_CLOUD

    @property
    def allows_local_only(self) -> bool:
        return self.effective.processing_location == ProcessingLocation.LOCAL_ONLY


class PolicyCompositionError(Exception):
    """Fail-closed error during policy composition."""

    def __init__(self, detail: str, parent_ids: list[PolicyId] | None = None) -> None:
        super().__init__(detail)
        self.detail = detail
        self.parent_ids = parent_ids or []


def resolve_effective_policy(
    parent_policies: list[PolicyAxes],
    parent_ids: list[PolicyId],
) -> PolicyResolution:
    """Compute the most restrictive effective policy from a set of parent policies.

    This is used when resolving from ancestors only (without a node's own policy).
    Fail-closed: empty list raises error.
    Declassification does not exist in F0.
    NEVER_CLOUD cannot be relaxed by any parent combination.
    """
    warnings: list[str] = []

    if not parent_policies:
        raise PolicyCompositionError(
            "Cannot resolve policy: no parent policies provided",
            parent_ids=parent_ids,
        )

    # Start with values from the first parent, then meet with each subsequent
    first = parent_policies[0]

    # Use typed enums — this ensures third-party ordering is correct
    effective_sensitivity = Sensitivity(
        first.sensitivity if isinstance(first.sensitivity, Sensitivity) else first.sensitivity
    )
    effective_location = ProcessingLocation(
        first.processing_location
        if isinstance(first.processing_location, ProcessingLocation)
        else first.processing_location
    )
    effective_cloud = CloudPolicy(
        first.cloud_policy if isinstance(first.cloud_policy, CloudPolicy) else first.cloud_policy
    )
    effective_third_party = ThirdPartyScope(
        first.third_party_scope
        if isinstance(first.third_party_scope, ThirdPartyScope)
        else first.third_party_scope
    )
    effective_export = ExportRule(
        first.export_rule if isinstance(first.export_rule, ExportRule) else first.export_rule
    )

    purposes: list[str] = [first.purpose] if first.purpose else []
    purpose_expiry: datetime.datetime | None = first.purpose_expiry
    retention_policy_ids: list[str] = (
        [first.retention_policy_id] if first.retention_policy_id else []
    )
    retention_review_date: datetime.datetime | None = first.retention_review_date
    export_audiences: list[str] = [first.export_audience] if first.export_audience else []

    for i, p in enumerate(parent_policies[1:], start=1):
        p_sensitivity = (
            Sensitivity(p.sensitivity) if isinstance(p.sensitivity, str) else p.sensitivity
        )
        p_location = (
            ProcessingLocation(p.processing_location)
            if isinstance(p.processing_location, str)
            else p.processing_location
        )
        p_cloud = CloudPolicy(p.cloud_policy) if isinstance(p.cloud_policy, str) else p.cloud_policy
        p_third_party = (
            ThirdPartyScope(p.third_party_scope)
            if isinstance(p.third_party_scope, str)
            else p.third_party_scope
        )
        p_export = ExportRule(p.export_rule) if isinstance(p.export_rule, str) else p.export_rule

        effective_sensitivity = Sensitivity.most_restrictive(effective_sensitivity, p_sensitivity)
        effective_location = ProcessingLocation.most_restrictive(effective_location, p_location)
        effective_cloud = CloudPolicy.most_restrictive(effective_cloud, p_cloud)
        effective_third_party = ThirdPartyScope.most_restrictive(
            effective_third_party, p_third_party
        )
        effective_export = ExportRule.most_restrictive(effective_export, p_export)

        # NEVER_CLOUD guard: any NEVER_CLOUD parent forces NEVER_CLOUD on child
        if p_cloud == CloudPolicy.NEVER_CLOUD:
            effective_cloud = CloudPolicy.NEVER_CLOUD

        if p.purpose:
            purposes.append(p.purpose)
        if p.purpose_expiry is not None:
            if purpose_expiry is None or p.purpose_expiry < purpose_expiry:
                purpose_expiry = p.purpose_expiry
        if p.retention_policy_id:
            retention_policy_ids.append(p.retention_policy_id)
        if p.retention_review_date is not None:
            if retention_review_date is None or p.retention_review_date < retention_review_date:
                retention_review_date = p.retention_review_date
        if p.export_audience:
            export_audiences.append(p.export_audience)

    return PolicyResolution(
        own_policy_id=parent_ids[0] if parent_ids else PolicyId(""),
        effective=PolicyAxes(
            sensitivity=effective_sensitivity,
            processing_location=effective_location,
            cloud_policy=effective_cloud,
            purpose="; ".join(purposes) if purposes else "",
            purpose_expiry=purpose_expiry,
            third_party_scope=effective_third_party,
            retention_policy_id="; ".join(retention_policy_ids) if retention_policy_ids else "",
            retention_review_date=retention_review_date,
            export_rule=effective_export,
            export_audience="; ".join(export_audiences) if export_audiences else "",
            lineage_rule="most_restrictive_parent",
        ),
        parent_ids=list(parent_ids),
        resolution_method="most_restrictive_meet",
        warnings=warnings,
    )


def resolve_with_own_policy(
    own_policy: PolicyAxes,
    own_policy_id: PolicyId,
    parent_policies: list[PolicyAxes],
    parent_ids: list[PolicyId],
) -> PolicyResolution:
    """Resolve effective policy by combining own policy with ALL ancestors.

    This is the correct approach per PS-02: a node's effective policy
    is the most-restrictive meet of its own policy AND all ancestor policies.

    FIX (F06): Always includes the node's own policy. No child can
    weaken NEVER_CLOUD inherited from any ancestor.
    """
    all_policies = [own_policy] + list(parent_policies)
    all_ids = [own_policy_id] + list(parent_ids)
    return resolve_effective_policy(all_policies, all_ids)


# ---------------------------------------------------------------------------
# NEVER_CLOUD lineage engine
# ---------------------------------------------------------------------------


class LineageNode:
    """A node in the policy lineage DAG."""

    def __init__(
        self,
        policy_id: PolicyId,
        policy: PolicyAxes,
        record_id: str = "",
    ) -> None:
        self.policy_id = policy_id
        self.policy = policy
        self.record_id = record_id
        self.parents: list[LineageNode] = []
        self.children: list[LineageNode] = []

    def add_parent(self, parent: LineageNode) -> None:
        if parent not in self.parents:
            self.parents.append(parent)
            parent.children.append(self)


@dataclass
class LineageDAG:
    """Directed acyclic graph of policy lineage edges."""

    nodes: dict[str, LineageNode] = field(default_factory=dict)

    def add_node(self, node: LineageNode) -> None:
        self.nodes[str(node.policy_id)] = node

    def add_edge(self, parent_id: PolicyId, child_id: PolicyId) -> None:
        parent = self.nodes.get(str(parent_id))
        child = self.nodes.get(str(child_id))
        if parent is None:
            raise PolicyCompositionError(
                f"Unknown parent policy: {parent_id}",
                parent_ids=[parent_id],
            )
        if child is None:
            raise PolicyCompositionError(
                f"Unknown child policy: {child_id}",
                parent_ids=[child_id],
            )
        child.add_parent(parent)

    def resolve_derived_policy(self, record_policy_id: PolicyId) -> PolicyResolution:
        """Resolve effective policy by combining own policy with all ancestors.

        FIX (F06): Always includes the node's OWN policy in the meet.
        Previously this could drop the node's own policy, allowing a child
        to appear less restrictive than its ancestors.
        """
        node = self.nodes.get(str(record_policy_id))
        if node is None:
            raise PolicyCompositionError(
                f"Unknown policy: {record_policy_id}",
                parent_ids=[record_policy_id],
            )

        # Collect all ancestor policies via DFS
        ancestors: list[tuple[PolicyId, PolicyAxes]] = []
        visited: set[str] = set()
        self._collect_ancestors(node, ancestors, visited)

        if not ancestors:
            # Leaf node with no parents — own policy stands
            return PolicyResolution(
                effective=node.policy,
                own_policy_id=node.policy_id,
                parent_ids=[],
                resolution_method="leaf_policy",
            )

        parent_policies = [p for _, p in ancestors]
        parent_ids = [pid for pid, _ in ancestors]

        # Combine own policy with all ancestors
        return resolve_with_own_policy(
            own_policy=node.policy,
            own_policy_id=node.policy_id,
            parent_policies=parent_policies,
            parent_ids=parent_ids,
        )

    def _collect_ancestors(
        self,
        node: LineageNode,
        result: list[tuple[PolicyId, PolicyAxes]],
        visited: set[str],
    ) -> None:
        """DFS to collect all ancestor policies. Cycle detection fails closed."""
        node_key = str(node.policy_id)
        if node_key in visited:
            raise PolicyCompositionError(
                f"Cycle detected in policy lineage at {node_key}",
                parent_ids=[PolicyId(node_key)],
            )
        visited.add(node_key)
        for parent in node.parents:
            result.append((parent.policy_id, parent.policy))
            self._collect_ancestors(parent, result, set(visited))

    def never_cloud_closure(self, root_policy_id: PolicyId) -> set[str]:
        """Return set of all policy IDs that inherit NEVER_CLOUD from root.

        Traverses descendants via BFS. A child inherits NEVER_CLOUD if its
        resolution (own + all ancestors) yields NEVER_CLOUD.
        """
        never_cloud_ids: set[str] = set()
        root = self.nodes.get(str(root_policy_id))
        if root is None:
            return never_cloud_ids

        if root.policy.cloud_policy == CloudPolicy.NEVER_CLOUD:
            never_cloud_ids.add(str(root_policy_id))
            queue = list(root.children)
            while queue:
                child = queue.pop(0)
                child_id = str(child.policy_id)
                if child_id not in never_cloud_ids:
                    resolved = self.resolve_derived_policy(child.policy_id)
                    if resolved.is_never_cloud:
                        never_cloud_ids.add(child_id)
                        queue.extend(child.children)

        return never_cloud_ids


def is_reconstructive_derivative(derivation_kind: str) -> bool:
    """Determine if a derivation kind materially reconstructs the source.

    Summary, excerpt, embedding, prediction, and aggregate are reconstructive.
    Unknown derivation kinds fail closed (treated as reconstructive).
    """
    reconstructive_kinds = {
        "summary",
        "excerpt",
        "embedding",
        "prediction",
        "aggregate",
        "containment",
        "quote",
        "derivation",
        "translation",
        "extract",
        "retelling",
        "paraphrase",
    }
    if derivation_kind in reconstructive_kinds:
        return True
    # Unknown types → fail closed as reconstructive
    if derivation_kind:
        return True
    # Empty/unknown → fail closed
    return True
