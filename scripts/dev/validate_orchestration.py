"""Validate the current, lean PSYCHE OS delivery-control contracts."""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
import sys
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "docs/development/STATE.yaml"
GATE_PATH = ROOT / "docs/architecture/REAL_DATA_GATE.yaml"
PROFILE_PATH = ROOT / "docs/architecture/REAL_DATA_GATE_PROFILE.yaml"
RISK_PATH = ROOT / ".ai-dev/policy/risk.yaml"
APPROVALS_PATH = ROOT / ".ai-dev/policy/approvals.yaml"
ROUTING_PATH = ROOT / ".ai-dev/routing/routing.yaml"
GATES_PATH = ROOT / ".ai-dev/verification/gates.yaml"

REQUIRED_PATHS = (
    "AGENTS.md",
    "CONSTITUTION.md",
    "docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md",
    "docs/AI_DEV_OS_V1.md",
    "docs/ROADMAP.md",
    "docs/DECISION_LOG.md",
    "docs/architecture/REAL_DATA_GATE.yaml",
    "docs/architecture/REAL_DATA_GATE_PROFILE.yaml",
    "docs/development/DEVELOPMENT_STRATEGY.md",
    "docs/development/EPIC_MAP.md",
    "docs/development/STATE.yaml",
    ".ai-dev/policy/risk.yaml",
    ".ai-dev/policy/approvals.yaml",
    ".ai-dev/routing/routing.yaml",
    ".ai-dev/verification/gates.yaml",
)
RDG_IDS = [f"RDG-{index:02d}" for index in range(1, 13)]
RDG_STATUSES = {
    "PROVED_FOR_CANDIDATE",
    "NOT_PROVED",
    "NOT_APPLICABLE_EXCLUDED",
    "STALE_OR_EXPIRED",
    "UNKNOWN_OR_INCOMPLETE",
}
STALE_GATE_FIELDS = {
    "snapshot_date",
    "status",
    "research_converged",
    "production_implementation_exists",
    "pre_real_data_blockers",
    "current_decision",
}
STALE_GATE_AUTHORITY_FIELDS = {"frozen_f0_contract", "e00_rebaseline", "next_implementation_contract"}
EXACT_EVALUATION_PROFILE_FIELDS = {
    "profile_definition_sha256",
    "profile_source_commit",
    "source_commit",
    "build_artifact_hashes",
    "sbom_identity",
    "evidence_status",
    "review_attestations",
    "gate_decision",
    "current_decision",
    "evaluation_id",
    "sealed_evaluation_sha256",
    "candidate_enforcement_result",
    "candidate_implementation_state",
}


class Validation:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.passes: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        (self.passes if condition else self.failures).append(message)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a YAML mapping")
    return data


def mapping_contains_any_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in forbidden or mapping_contains_any_key(child, forbidden) for key, child in value.items())
    if isinstance(value, list):
        return any(mapping_contains_any_key(child, forbidden) for child in value)
    return False


def validate_stable_gate_architecture(
    result: Validation, state: dict[str, Any], gate: dict[str, Any], profile: dict[str, Any]
) -> None:
    """Validate the stable policy/profile split without evaluating a candidate."""
    result.check(state.get("real_data_gate", {}).get("state") == "CLOSED", "state gate is CLOSED")
    result.check(gate.get("fail_closed_default") == "CLOSED", "policy default is CLOSED")
    result.check(gate.get("research_convergence_required") is True, "policy requires research convergence")
    result.check(gate.get("opening_rule", {}).get("automatic_opening_forbidden") is True, "automatic gate opening is forbidden")
    result.check(gate.get("opening_rule", {}).get("coding_models_may_decide_gate") is False, "coding models cannot decide the gate")
    result.check(gate.get("opening_rule", {}).get("gate_decider_role") == "REPOSITORY_OWNER", "policy names REPOSITORY_OWNER")
    result.check(not (set(gate) & STALE_GATE_FIELDS), "stable policy has no stale dynamic fields")
    result.check(not (set(gate.get("authority", {})) & STALE_GATE_AUTHORITY_FIELDS), "stable policy has no historical implementation pointers")
    result.check(set(gate.get("rdg_status_vocabulary", [])) == RDG_STATUSES, "policy has canonical RDG statuses")
    requirements = gate.get("requirements", [])
    result.check(isinstance(requirements, list) and [item.get("id") for item in requirements if isinstance(item, dict)] == RDG_IDS, "stable policy retains RDG-01 through RDG-12")
    result.check(not any(isinstance(item, dict) and ({"state", "evidence", "decision", "review"} & set(item)) for item in requirements), "stable policy has no candidate RDG evidence")
    result.check(profile.get("status") == "ACCEPTED_STABLE_PROFILE_DEFINITION" and profile.get("authoritative") is True, "stable profile is authoritative")
    result.check(profile.get("definition_lifecycle", {}).get("self_digest_forbidden") is True, "stable profile forbids self-owned digest")
    result.check(not mapping_contains_any_key(profile, EXACT_EVALUATION_PROFILE_FIELDS), "stable profile has no exact evaluation fields")


def validate_product_state(result: Validation, state: dict[str, Any]) -> None:
    result.check(state.get("research", {}).get("converged") is True, "research is converged")
    result.check(state.get("foundation", {}).get("status") == "COMPLETE", "foundation is COMPLETE")
    result.check(state.get("operating_mode") == "PRODUCT_DEVELOPMENT", "operating mode is PRODUCT_DEVELOPMENT")
    result.check(state.get("infrastructure") == "CLOSED_EXCEPTION_ONLY", "infrastructure is exception-only")
    current = state.get("current_implementation", {})
    result.check(current.get("task") is None and current.get("next_epic") is None, "no implementation task or epic is active")
    result.check(current.get("next_action") == "DEFINE_NEXT_PRODUCT_INCREMENT", "next action defines a product increment")
    result.check(state.get("personal_mode", {}).get("v1_status") == "CLOSED_ACCEPTED_MERGED", "Personal Mode v1 is closed, accepted, and merged")
    accepted = state.get("accepted_epics", [])
    ids = [entry.get("id") for entry in accepted if isinstance(entry, dict)]
    result.check(ids == [f"E{index:02d}" for index in range(12)], "E00-E11 are accepted in historical order")
    result.check(all(entry.get("status") == "ACCEPTED" for entry in accepted if isinstance(entry, dict)), "accepted epic history is accepted")
    result.check("current_epic" not in state and "next_epic" not in state and "next_action" not in state, "state has no stale active-epic fields")
    for entry in accepted:
        if isinstance(entry, dict) and isinstance(entry.get("report"), str):
            result.check((ROOT / entry["report"]).is_file(), f"accepted report exists: {entry['id']}")
    for key in ("constitution", "master_spec", "decision_log", "roadmap", "epic_map"):
        value = state.get("architecture", {}).get(key)
        result.check(isinstance(value, str) and (ROOT / value).is_file(), f"state reference exists: {key}")


def validate_product_mode_policy(
    result: Validation, risk: dict[str, Any], approvals: dict[str, Any], routing: dict[str, Any], gates: dict[str, Any]
) -> None:
    classification = risk.get("classification", {})
    examples = classification.get("examples", {})
    result.check("delta" in str(classification.get("primary_rule", "")).lower(), "risk classification is delta based")
    result.check(examples.get("historical_crypto_wording") == "low", "historical crypto wording is LOW")
    result.check(examples.get("isolated_regression_test") == "low", "isolated test-only change is LOW")
    result.check(examples.get("bounded_control_plane_bugfix") == "low_or_medium", "bounded control-plane bugfix is LOW/MEDIUM")
    result.check(examples.get("accepted_architecture_storage_fix") == "high", "bounded sensitive implementation fix is HIGH")
    result.check(examples.get("crypto_key_lifecycle_or_trust_model_change") == "critical", "crypto/key/trust-model change is CRITICAL")
    result.check(risk.get("levels", {}).get("critical", {}).get("review") == "concrete_trigger_only", "critical review is trigger based")
    result.check(risk.get("levels", {}).get("critical", {}).get("human_approval") == "required_for_listed_actions", "critical labels do not create unconditional approval")
    result.check(isinstance(approvals.get("require_explicit_approval"), list), "approval matrix remains action owned")
    review = routing.get("review_policy", {})
    result.check(review.get("candidate_wide_review_budget") == 1, "one candidate-wide review maximum")
    result.check("sensitive_directory_or_domain_name" in review.get("not_triggers", []), "sensitive path is not a review trigger")
    result.check("task_contract_requires_review" in review.get("triggers", []), "task contract can require review")
    firewall = routing.get("acceptance_firewall", {})
    result.check(firewall.get("accepted_closes_core_implementation") is True, "acceptance firewall closes core implementation")
    result.check(firewall.get("packaging_or_commit_identity_change") == "not_a_product_regression", "packaging cannot reopen acceptance")
    identity = routing.get("candidate_identity", {})
    result.check(identity.get("default_review_target") == "local_candidate_commit_sha", "commit SHA is default review identity")
    selection = gates.get("selection", {})
    result.check(selection.get("docs_or_status_only") == "relevant_syntax_schema_link_or_orchestration_checks_only", "docs/status verification is focused")
    result.check(selection.get("independent_review") == "only_when_routing_review_trigger_is_true", "review gate is trigger based")


def branch_matches_workflow(branch: str) -> bool:
    return branch == "main" or re.fullmatch(r"[a-z0-9-]+/[a-z0-9][a-z0-9-]*", branch) is not None


def main() -> int:
    result = Validation()
    for relative in REQUIRED_PATHS:
        result.check((ROOT / relative).is_file(), f"required path exists: {relative}")
    try:
        state = load_yaml(STATE_PATH)
        gate = load_yaml(GATE_PATH)
        profile = load_yaml(PROFILE_PATH)
        risk = load_yaml(RISK_PATH)
        approvals = load_yaml(APPROVALS_PATH)
        routing = load_yaml(ROUTING_PATH)
        gates = load_yaml(GATES_PATH)
        result.check(True, "current YAML owners parse")
    except Exception as exc:
        result.failures.append(f"YAML parse failed: {exc}")
        state = gate = profile = risk = approvals = routing = gates = {}
    validate_stable_gate_architecture(result, state, gate, profile)
    validate_product_state(result, state)
    validate_product_mode_policy(result, risk, approvals, routing, gates)
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT, check=False, capture_output=True, text=True).stdout.strip()
    result.check(branch_matches_workflow(branch), "Git branch matches product workflow")
    for message in result.passes:
        print(f"PASS: {message}")
    for message in result.failures:
        print(f"FAIL: {message}")
    print(f"SUMMARY: {len(result.passes)} passed, {len(result.failures)} failed; gate_default={gate.get('fail_closed_default', 'UNKNOWN')}")
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
