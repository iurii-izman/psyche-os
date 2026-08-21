"""Focused regressions for the stable real-data gate architecture split."""

from __future__ import annotations

import yaml

from scripts.dev.validate_orchestration import (
    GATE_PATH,
    PROFILE_PATH,
    STATE_PATH,
    Validation,
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
