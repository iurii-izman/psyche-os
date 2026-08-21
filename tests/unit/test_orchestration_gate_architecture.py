"""Focused regressions for the stable real-data gate architecture split."""

from __future__ import annotations

import yaml

from scripts.dev.validate_orchestration import (
    GATE_PATH,
    PROFILE_PATH,
    STATE_PATH,
    Validation,
    branch_matches_workflow,
    validate_epic_progression,
    validate_stable_gate_architecture,
)


def _yaml_mapping(path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_stable_gate_policy_and_profile_pass_without_candidate_evaluation() -> None:
    result = Validation()

    validate_stable_gate_architecture(
        result,
        _yaml_mapping(STATE_PATH),
        _yaml_mapping(GATE_PATH),
        _yaml_mapping(PROFILE_PATH),
    )

    assert result.failures == []


def test_stable_owners_reject_candidate_state_and_evaluation_fields() -> None:
    state = _yaml_mapping(STATE_PATH)
    gate = _yaml_mapping(GATE_PATH)
    profile = _yaml_mapping(PROFILE_PATH)
    gate["requirements"][0]["state"] = "PROVED_FOR_CANDIDATE"
    gate["status"] = "CLOSED"
    profile["boundary_inventory"]["desktop_renderer_and_typed_ipc"][
        "candidate_implementation_state"
    ] = "PROVED_FOR_CANDIDATE"

    result = Validation()
    validate_stable_gate_architecture(result, state, gate, profile)

    assert "stable policy has no stale dynamic fields" in result.failures
    assert "stable policy has no per-candidate RDG state or evidence" in result.failures
    assert (
        "stable profile has no exact evaluation, build, evidence, or decision fields"
        in result.failures
    )


def test_terminal_accepted_epic_has_no_successor_and_allows_main_or_codex_topic_branch() -> None:
    state = _yaml_mapping(STATE_PATH)
    epic_ids = [f"E{index:02d}" for index in range(12)]
    result = Validation()

    validate_epic_progression(result, state, epic_ids)

    assert result.failures == []
    assert branch_matches_workflow(state, epic_ids, "main", None)
    assert branch_matches_workflow(state, epic_ids, "codex/r0-runtime-russian-ux", None)


def test_pre_terminal_wrong_branch_and_detached_or_empty_branch_fail() -> None:
    state = _yaml_mapping(STATE_PATH)
    epic_ids = [f"E{index:02d}" for index in range(12)]
    state["current_epic"]["id"] = "E10"
    state["current_epic"]["status"] = "IMPLEMENTED"
    state["next_epic"] = {"id": "E11", "status": "PLANNED"}

    assert not branch_matches_workflow(state, epic_ids, "codex/r0-runtime-russian-ux", "codex/e10")

    terminal_state = _yaml_mapping(STATE_PATH)
    assert not branch_matches_workflow(terminal_state, epic_ids, "", None)
    assert not branch_matches_workflow(terminal_state, epic_ids, "codex/", None)
