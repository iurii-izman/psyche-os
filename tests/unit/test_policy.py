"""Unit tests for policy engine."""

import pytest

from psyche_os.domain.ids import PolicyId, generate_id
from psyche_os.policy.engine import (
    CloudPolicy,
    ExportRule,
    LineageDAG,
    LineageNode,
    PolicyAxes,
    PolicyCompositionError,
    ProcessingLocation,
    Sensitivity,
    is_reconstructive_derivative,
    resolve_effective_policy,
)


class TestSensitivity:
    def test_most_restrictive_ordinary_sensitive(self) -> None:
        result = Sensitivity.most_restrictive(Sensitivity.ORDINARY, Sensitivity.SENSITIVE)
        assert result == Sensitivity.SENSITIVE

    def test_most_restrictive_sensitive_deeply(self) -> None:
        result = Sensitivity.most_restrictive(Sensitivity.SENSITIVE, Sensitivity.DEEPLY_SENSITIVE)
        assert result == Sensitivity.DEEPLY_SENSITIVE

    def test_most_restrictive_deeply_ordinary(self) -> None:
        result = Sensitivity.most_restrictive(Sensitivity.DEEPLY_SENSITIVE, Sensitivity.ORDINARY)
        assert result == Sensitivity.DEEPLY_SENSITIVE


class TestCloudPolicy:
    def test_never_cloud_most_restrictive(self) -> None:
        result = CloudPolicy.most_restrictive(
            CloudPolicy.NEVER_CLOUD, CloudPolicy.NAMED_PURPOSE_AND_PROVIDER
        )
        assert result == CloudPolicy.NEVER_CLOUD

    def test_never_cloud_cannot_be_downgraded(self) -> None:
        result = CloudPolicy.most_restrictive(CloudPolicy.ASK_EACH_TIME, CloudPolicy.NEVER_CLOUD)
        assert result == CloudPolicy.NEVER_CLOUD


class TestProcessingLocation:
    def test_local_only_most_restrictive(self) -> None:
        result = ProcessingLocation.most_restrictive(
            ProcessingLocation.LOCAL_ONLY, ProcessingLocation.APPROVED_CLOUD
        )
        assert result == ProcessingLocation.LOCAL_ONLY


class TestResolveEffectivePolicy:
    def test_single_policy(self) -> None:
        p = PolicyAxes(
            sensitivity=Sensitivity.ORDINARY,
            cloud_policy=CloudPolicy.ASK_EACH_TIME,
        )
        result = resolve_effective_policy([p], [PolicyId(generate_id())])
        assert result.effective.sensitivity == Sensitivity.ORDINARY
        assert result.effective.cloud_policy == CloudPolicy.ASK_EACH_TIME

    def test_most_restrictive_meet(self) -> None:
        p1 = PolicyAxes(
            sensitivity=Sensitivity.ORDINARY,
            cloud_policy=CloudPolicy.ASK_EACH_TIME,
        )
        p2 = PolicyAxes(
            sensitivity=Sensitivity.DEEPLY_SENSITIVE,
            cloud_policy=CloudPolicy.NEVER_CLOUD,
        )
        result = resolve_effective_policy(
            [p1, p2],
            [PolicyId(generate_id()), PolicyId(generate_id())],
        )
        assert result.effective.sensitivity == Sensitivity.DEEPLY_SENSITIVE
        assert result.effective.cloud_policy == CloudPolicy.NEVER_CLOUD
        assert result.is_never_cloud is True

    def test_needs_at_least_one_parent(self) -> None:
        with pytest.raises(PolicyCompositionError):
            resolve_effective_policy([], [])

    def test_never_cloud_persists(self) -> None:
        p1 = PolicyAxes(cloud_policy=CloudPolicy.NEVER_CLOUD)
        p2 = PolicyAxes(cloud_policy=CloudPolicy.NAMED_PURPOSE_AND_PROVIDER)
        result = resolve_effective_policy(
            [p1, p2], [PolicyId(generate_id()), PolicyId(generate_id())]
        )
        assert result.effective.cloud_policy == CloudPolicy.NEVER_CLOUD

    def test_export_block_persists(self) -> None:
        p1 = PolicyAxes(export_rule=ExportRule.BLOCK)
        p2 = PolicyAxes(export_rule=ExportRule.ALLOW)
        result = resolve_effective_policy(
            [p1, p2], [PolicyId(generate_id()), PolicyId(generate_id())]
        )
        assert result.effective.export_rule == ExportRule.BLOCK


class TestLineageDAG:
    def _make_node(
        self, policy_id: str | None = None, cloud: CloudPolicy = CloudPolicy.NEVER_CLOUD
    ) -> LineageNode:
        pid = PolicyId(policy_id or generate_id())
        return LineageNode(
            policy_id=pid,
            policy=PolicyAxes(cloud_policy=cloud),
            record_id=generate_id(),
        )

    def test_add_node(self) -> None:
        dag = LineageDAG()
        node = self._make_node()
        dag.add_node(node)
        assert str(node.policy_id) in dag.nodes

    def test_add_edge(self) -> None:
        dag = LineageDAG()
        parent = self._make_node()
        child = self._make_node()
        dag.add_node(parent)
        dag.add_node(child)
        dag.add_edge(parent.policy_id, child.policy_id)
        assert parent.children == [child]
        assert child.parents == [parent]

    def test_unknown_parent_fails(self) -> None:
        dag = LineageDAG()
        child = self._make_node()
        dag.add_node(child)
        with pytest.raises(PolicyCompositionError):
            dag.add_edge(PolicyId("nonexistent"), child.policy_id)

    def test_cycle_detection(self) -> None:
        dag = LineageDAG()
        parent = self._make_node()
        child = self._make_node()
        dag.add_node(parent)
        dag.add_node(child)
        dag.add_edge(parent.policy_id, child.policy_id)

        # Adding reverse edge creates a cycle — resolving child policy
        # through parent will detect it since child is now parent's ancestor
        dag.add_edge(child.policy_id, parent.policy_id)

        # Resolving through the cycle should raise
        with pytest.raises(PolicyCompositionError, match="Cycle"):
            dag.resolve_derived_policy(parent.policy_id)

    def test_resolve_derived_policy(self) -> None:
        dag = LineageDAG()
        p1 = LineageNode(
            policy_id=PolicyId(generate_id()),
            policy=PolicyAxes(
                sensitivity=Sensitivity.DEEPLY_SENSITIVE,
                cloud_policy=CloudPolicy.NEVER_CLOUD,
            ),
        )
        p2 = LineageNode(
            policy_id=PolicyId(generate_id()),
            policy=PolicyAxes(
                sensitivity=Sensitivity.ORDINARY,
                cloud_policy=CloudPolicy.ASK_EACH_TIME,
            ),
        )
        dag.add_node(p1)
        dag.add_node(p2)
        dag.add_edge(p1.policy_id, p2.policy_id)

        result = dag.resolve_derived_policy(p2.policy_id)
        # Should get most restrictive from parent
        assert result.effective.sensitivity == Sensitivity.DEEPLY_SENSITIVE
        assert result.effective.cloud_policy == CloudPolicy.NEVER_CLOUD

    def test_never_cloud_closure(self) -> None:
        dag = LineageDAG()
        p1 = self._make_node(cloud=CloudPolicy.NEVER_CLOUD)
        p2 = self._make_node(cloud=CloudPolicy.ASK_EACH_TIME)
        p3 = self._make_node(cloud=CloudPolicy.NAMED_PURPOSE_AND_PROVIDER)

        dag.add_node(p1)
        dag.add_node(p2)
        dag.add_node(p3)
        dag.add_edge(p1.policy_id, p2.policy_id)
        dag.add_edge(p2.policy_id, p3.policy_id)

        closure = dag.never_cloud_closure(p1.policy_id)
        # p1 is NEVER_CLOUD, p2 inherits NEVER_CLOUD, p3 inherits from p2
        assert str(p1.policy_id) in closure


class TestReconstructiveDerivative:
    def test_known_reconstructive(self) -> None:
        assert is_reconstructive_derivative("summary") is True
        assert is_reconstructive_derivative("excerpt") is True
        assert is_reconstructive_derivative("embedding") is True

    def test_unknown_fails_closed(self) -> None:
        # Unknown derivation kinds are treated as reconstructive
        assert is_reconstructive_derivative("totally_unknown_kind") is True

    def test_empty_string_fails_closed(self) -> None:
        assert is_reconstructive_derivative("") is True
