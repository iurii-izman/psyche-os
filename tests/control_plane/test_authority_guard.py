"""Authority / contract guard tests (component D)."""
from __future__ import annotations

import ai_dev_v2 as v2


def contract(risk: str = "high", conflict_status: str = "none", items: list | None = None,
             authority: dict | list | None = None) -> dict:
    if authority is None:
        authority = {
            "highest": ["CONSTITUTION.md"],
            "supporting": [".ai-dev/README.md"],
            "implementation_precedent": ["E10 acceptance evidence"],
        }
    return {
        "task_id": "T-1",
        "risk": risk,
        "authority": authority,
        "authority_conflicts": {"status": conflict_status, "items": items or []},
    }


class TestAcceptanceBlocking:
    def test_high_unresolved_blocks(self) -> None:
        blocked, reason = v2.acceptance_blocked(contract(risk="high", conflict_status="unresolved"))
        assert blocked
        assert "unresolved" in reason

    def test_critical_unresolved_blocks(self) -> None:
        blocked, _ = v2.acceptance_blocked(
            contract(risk="critical", conflict_status="unresolved")
        )
        assert blocked

    def test_high_resolved_does_not_block(self) -> None:
        blocked, _ = v2.acceptance_blocked(contract(risk="high", conflict_status="resolved"))
        assert not blocked

    def test_low_unresolved_does_not_block(self) -> None:
        # the hard rule applies only to HIGH/CRITICAL.
        blocked, _ = v2.acceptance_blocked(contract(risk="low", conflict_status="unresolved"))
        assert not blocked


class TestResolutionRetention:
    def test_resolved_conflict_retains_disposition(self) -> None:
        item = {
            "refs": ["CONSTITUTION.md", "E10 acceptance evidence"],
            "outranks": "CONSTITUTION.md",
            "disposition": "CONSTITUTION.md wins",
            "evidence": ".ai-dev/evidence/decisions/example.md",
            "blocks_acceptance": False,
        }
        c = contract(risk="high", conflict_status="resolved", items=[item])
        guard = v2.check_authority_guard(c)
        assert guard["conflict_status"] == "resolved"
        assert not guard["acceptance_blocked"]


class TestPrecedenceRule:
    def test_implementation_precedent_cannot_outrank_highest(self) -> None:
        item = {
            "refs": ["CONSTITUTION.md", "E10 acceptance evidence"],
            "outranks": "E10 acceptance evidence",
            "disposition": "pending",
        }
        c = contract(
            risk="high",
            conflict_status="unresolved",
            items=[item],
            authority={
                "highest": ["CONSTITUTION.md"],
                "supporting": [],
                "implementation_precedent": ["E10 acceptance evidence"],
            },
        )
        guard = v2.check_authority_guard(c)
        assert any("implementation_precedent" in v for v in guard["violations"])

    def test_same_ref_in_highest_and_precedent_is_violation(self) -> None:
        c = contract(
            authority={
                "highest": ["CONSTITUTION.md", "AGENTS.md"],
                "supporting": [],
                "implementation_precedent": ["AGENTS.md"],
            }
        )
        guard = v2.check_authority_guard(c)
        assert guard["violations"]


class TestBackwardsCompatibility:
    def test_legacy_v1_flat_authority_is_readable(self) -> None:
        c = contract(authority=["CONSTITUTION.md", "docs/AI_DEV_OS_V1.md"])
        auth = v2.normalize_authority(c)
        assert auth["highest"] == ["CONSTITUTION.md", "docs/AI_DEV_OS_V1.md"]
        assert auth["implementation_precedent"] == []
        # legacy contract has no authority_conflicts -> not blocked.
        assert v2.authority_conflict_status(c) == "none"
        assert not v2.acceptance_blocked(c)[0]

    def test_missing_authority_is_readable(self) -> None:
        auth = v2.normalize_authority({"task_id": "T-1"})
        assert auth == {"highest": [], "supporting": [], "implementation_precedent": []}

    def test_unknown_conflict_status_treated_as_unresolved(self) -> None:
        c = contract(risk="high", conflict_status="weird")
        assert v2.authority_conflict_status(c) == "unresolved"
        assert v2.acceptance_blocked(c)[0]


class TestGuardBlockingRules:
    def test_high_resolved_precedent_outranks_highest_is_blocked(self) -> None:
        item = {
            "refs": ["CONSTITUTION.md", "E10 acceptance evidence"],
            "outranks": "E10 acceptance evidence",
            "disposition": "precedent wins (invalid)",
            "blocks_acceptance": False,
        }
        c = contract(
            risk="high",
            conflict_status="resolved",
            items=[item],
            authority={
                "highest": ["CONSTITUTION.md"],
                "supporting": [],
                "implementation_precedent": ["E10 acceptance evidence"],
            },
        )
        guard = v2.guard_decision(c)
        assert guard["violations"]
        assert guard["acceptance_blocked"] is True

    def test_high_v2_missing_authority_conflicts_is_blocked(self) -> None:
        c = {
            "task_id": "T-1",
            "risk": "high",
            "authority": {
                "highest": ["CONSTITUTION.md"],
                "supporting": [],
                "implementation_precedent": [],
            },
        }
        assert v2.guard_decision(c)["acceptance_blocked"] is True

    def test_malformed_resolution_missing_disposition_is_blocked(self) -> None:
        item = {"refs": ["CONSTITUTION.md", "E10 acceptance evidence"], "outranks": "CONSTITUTION.md"}
        c = contract(risk="high", conflict_status="resolved", items=[item])
        assert v2.guard_decision(c)["acceptance_blocked"] is True

    def test_resolved_item_still_blocks_acceptance_is_blocked(self) -> None:
        item = {
            "refs": ["CONSTITUTION.md", "E10 acceptance evidence"],
            "outranks": "CONSTITUTION.md",
            "disposition": "resolved",
            "blocks_acceptance": True,
        }
        c = contract(risk="high", conflict_status="resolved", items=[item])
        assert v2.guard_decision(c)["acceptance_blocked"] is True
