"""Focused regressions for gate stability and product-mode policy semantics."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import yaml

from scripts.dev.validate_orchestration import (
    APPROVALS_PATH,
    GATE_PATH,
    GATES_PATH,
    PROFILE_PATH,
    RISK_PATH,
    ROUTING_PATH,
    STATE_PATH,
    Validation,
    branch_matches_workflow,
    validate_product_mode_policy,
    validate_product_state,
    validate_stable_gate_architecture,
)


def _yaml_mapping(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], yaml.safe_load(path.read_text(encoding="utf-8")))


def test_stable_gate_policy_and_product_state_pass() -> None:
    result = Validation()
    state = _yaml_mapping(STATE_PATH)
    validate_stable_gate_architecture(result, state, _yaml_mapping(GATE_PATH), _yaml_mapping(PROFILE_PATH))
    validate_product_state(result, state)
    assert result.failures == []


def test_stable_owners_reject_candidate_state_and_evaluation_fields() -> None:
    state = _yaml_mapping(STATE_PATH)
    gate = _yaml_mapping(GATE_PATH)
    profile = _yaml_mapping(PROFILE_PATH)
    gate["requirements"][0]["state"] = "PROVED_FOR_CANDIDATE"
    gate["status"] = "CLOSED"
    profile["boundary_inventory"]["desktop_renderer_and_typed_ipc"]["candidate_implementation_state"] = "PROVED_FOR_CANDIDATE"
    result = Validation()
    validate_stable_gate_architecture(result, state, gate, profile)
    assert "stable policy has no stale dynamic fields" in result.failures
    assert "stable policy has no candidate RDG evidence" in result.failures
    assert "stable profile has no exact evaluation fields" in result.failures


def test_product_mode_policy_covers_required_delta_and_acceptance_cases() -> None:
    result = Validation()
    validate_product_mode_policy(
        result,
        _yaml_mapping(RISK_PATH),
        _yaml_mapping(APPROVALS_PATH),
        _yaml_mapping(ROUTING_PATH),
        _yaml_mapping(GATES_PATH),
    )
    assert result.failures == []


def test_product_mode_state_rejects_stale_active_epic() -> None:
    state = _yaml_mapping(STATE_PATH)
    state["current_epic"] = {"id": "E11", "status": "ACCEPTED"}
    result = Validation()
    validate_product_state(result, state)
    assert "state has no stale active-epic fields" in result.failures


def test_policy_rejects_unconditional_critical_approval_or_second_review() -> None:
    risk = _yaml_mapping(RISK_PATH)
    routing = _yaml_mapping(ROUTING_PATH)
    risk["levels"]["critical"]["human_approval"] = "required"
    risk["levels"]["critical"]["review"] = "independent_reviewer_required"
    routing["review_policy"]["candidate_wide_review_budget"] = 2
    result = Validation()
    validate_product_mode_policy(
        result, risk, _yaml_mapping(APPROVALS_PATH), routing, _yaml_mapping(GATES_PATH)
    )
    assert "critical labels do not create unconditional approval" in result.failures
    assert "critical review is trigger based" in result.failures
    assert "one candidate-wide review maximum" in result.failures


def test_product_workflow_allows_main_or_bounded_topic_branch_only() -> None:
    assert branch_matches_workflow("main")
    assert branch_matches_workflow("codex/product-mode-reorientation")
    assert not branch_matches_workflow("")
    assert not branch_matches_workflow("codex/")
