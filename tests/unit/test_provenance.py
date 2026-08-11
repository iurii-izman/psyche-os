"""Unit tests for provenance layer."""

from psyche_os.domain.ids import (
    RecordId,
    VersionId,
    generate_id,
)
from psyche_os.provenance.provenance import (
    DerivationRecord,
    EvidenceGraph,
    ProvenanceNode,
    compute_config_digest,
)


class TestProvenanceNode:
    def test_construction(self) -> None:
        node = ProvenanceNode(
            record_id=RecordId(generate_id()),
            version_id=VersionId(generate_id()),
            record_kind="observation",
        )
        assert node.record_kind == "observation"
        assert node.parent_record_ids == []

    def test_with_parents(self) -> None:
        parent_id = RecordId(generate_id())
        node = ProvenanceNode(
            record_id=RecordId(generate_id()),
            version_id=VersionId(generate_id()),
            record_kind="assertion",
            parent_record_ids=[parent_id],
        )
        assert len(node.parent_record_ids) == 1


class TestDerivationRecord:
    def test_construction(self) -> None:
        dr = DerivationRecord(
            method_kind="test",
            code_rule_model_tool="hypothesis",
        )
        assert dr.method_kind == "test"
        assert dr.review_state == "pending"
        assert dr.ended_at is None

    def test_add_output(self) -> None:
        dr = DerivationRecord()
        rid = RecordId(generate_id())
        dr2 = dr.add_output(rid)
        assert len(dr2.output_record_ids) == 1
        assert dr2.output_record_ids[0] == rid
        # Original unchanged
        assert len(dr.output_record_ids) == 0

    def test_add_output_no_duplicates(self) -> None:
        rid = RecordId(generate_id())
        dr = DerivationRecord()
        dr2 = dr.add_output(rid)
        dr3 = dr2.add_output(rid)
        assert len(dr3.output_record_ids) == 1

    def test_finalize(self) -> None:
        dr = DerivationRecord()
        finalized = dr.finalize()
        assert finalized.ended_at is not None
        assert dr.ended_at is None  # Original unchanged


class TestEvidenceGraph:
    def test_add_node(self) -> None:
        g = EvidenceGraph()
        node = ProvenanceNode(
            record_id=RecordId(generate_id()),
            version_id=VersionId(generate_id()),
            record_kind="claim",
        )
        g2 = g.add_node(node)
        assert len(g2.nodes) == 1
        assert len(g.nodes) == 0  # Immutable

    def test_add_edge(self) -> None:
        source = RecordId(generate_id())
        target = RecordId(generate_id())
        g = EvidenceGraph()
        # F09: Both endpoints must exist in graph before adding edge
        g = g.add_node(
            ProvenanceNode(
                record_id=source,
                version_id=VersionId(generate_id()),
                record_kind="claim",
            )
        )
        g = g.add_node(
            ProvenanceNode(
                record_id=target,
                version_id=VersionId(generate_id()),
                record_kind="claim",
            )
        )
        g2 = g.add_edge(source, target, "supports")
        assert len(g2.edges) == 1
        assert g2.edges[0]["relation"] == "supports"

    def test_get_supporting(self) -> None:
        source = RecordId(generate_id())
        target = RecordId(generate_id())
        g = EvidenceGraph()
        g = g.add_node(
            ProvenanceNode(
                record_id=source,
                version_id=VersionId(generate_id()),
                record_kind="claim",
            )
        )
        g = g.add_node(
            ProvenanceNode(
                record_id=target,
                version_id=VersionId(generate_id()),
                record_kind="claim",
            )
        )
        g2 = g.add_edge(source, target, "supports")
        supporting = g2.get_supporting(target)
        assert str(source) in supporting

    def test_get_contradicting(self) -> None:
        source = RecordId(generate_id())
        target = RecordId(generate_id())
        g = EvidenceGraph()
        g = g.add_node(
            ProvenanceNode(
                record_id=source,
                version_id=VersionId(generate_id()),
                record_kind="claim",
            )
        )
        g = g.add_node(
            ProvenanceNode(
                record_id=target,
                version_id=VersionId(generate_id()),
                record_kind="claim",
            )
        )
        g2 = g.add_edge(source, target, "contradicts")
        contradicting = g2.get_contradicting(target)
        assert str(source) in contradicting

    def test_find_dependencies_transitive(self) -> None:
        rid1 = RecordId(generate_id())
        rid2 = RecordId(generate_id())
        rid3 = RecordId(generate_id())

        node1 = ProvenanceNode(
            record_id=rid1,
            version_id=VersionId(generate_id()),
            record_kind="observation",
        )
        node2 = ProvenanceNode(
            record_id=rid2,
            version_id=VersionId(generate_id()),
            record_kind="assertion",
            parent_record_ids=[rid1],
        )
        node3 = ProvenanceNode(
            record_id=rid3,
            version_id=VersionId(generate_id()),
            record_kind="claim",
            parent_record_ids=[rid2],
        )

        g = EvidenceGraph()
        g = g.add_node(node1)
        g = g.add_node(node2)
        g = g.add_node(node3)

        deps = g.find_dependencies(rid1)
        assert str(rid2) in deps
        assert str(rid3) in deps


class TestComputeConfigDigest:
    def test_deterministic(self) -> None:
        config = {"a": 1, "b": 2}
        d1 = compute_config_digest(config)
        d2 = compute_config_digest(config)
        assert d1 == d2

    def test_order_independent(self) -> None:
        config1 = {"a": 1, "b": 2}
        config2 = {"b": 2, "a": 1}
        assert compute_config_digest(config1) == compute_config_digest(config2)

    def test_different_configs(self) -> None:
        d1 = compute_config_digest({"a": 1})
        d2 = compute_config_digest({"a": 2})
        assert d1 != d2

    def test_hex_format(self) -> None:
        digest = compute_config_digest({"key": "value"})
        assert len(digest) == 64
        assert all(c in "0123456789abcdef" for c in digest)
