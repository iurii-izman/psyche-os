"""Validate the lean PSYCHE OS development-orchestration layer.

This deliberately checks documentation/state contracts only. It does not claim
that F0 exists, that security controls work, or that real data is permitted.
PyYAML is already used by the repository research validators.
"""

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
EPIC_MAP_PATH = ROOT / "docs/development/EPIC_MAP.md"

REQUIRED_PATHS = (
    "AGENTS.md",
    "CONSTITUTION.md",
    "docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md",
    "docs/ROADMAP.md",
    "docs/DECISION_LOG.md",
    "docs/SCIENTIFIC_GOVERNANCE.md",
    "docs/architecture/DATA_MODEL.md",
    "docs/architecture/SYSTEM_ARCHITECTURE.md",
    "docs/architecture/PRIVACY_SECURITY_MODEL.md",
    "docs/architecture/MENTAL_HEALTH_AI_SAFETY.md",
    "docs/architecture/THREAT_MODEL.md",
    "docs/architecture/REAL_DATA_GATE.yaml",
    "docs/architecture/REAL_DATA_GATE_PROFILE.yaml",
    "docs/development/DEVELOPMENT_STRATEGY.md",
    "docs/development/EPIC_MAP.md",
    "docs/development/STATE.yaml",
    "docs/development/EPIC_REPORT_TEMPLATE.md",
    "docs/development/ARCHITECTURE_DEVIATION_TEMPLATE.md",
    "docs/development/ORCHESTRATION_REPORT.md",
    "docs/prompts/F0_IMPLEMENTATION_PROMPT.md",
    "docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md",
    "docs/prompts/deepseek/FIX_FINDINGS_TEMPLATE.md",
    "docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md",
    "docs/prompts/codex/PREPARE_NEXT_EPIC.md",
    "docs/prompts/codex/HIGH_RISK_EPIC_REVIEW_TEMPLATE.md",
)
MARKDOWN_PATHS = tuple(path for path in REQUIRED_PATHS if path.endswith(".md"))
EPIC_RE = re.compile(r"^## (E\d{2}) — (.+)$", re.MULTILINE)
ALLOWED_STATUS = {
    "PLANNED",
    "READY",
    "IN_PROGRESS",
    "BLOCKED",
    "IMPLEMENTED",
    "ACCEPTED",
}
FORBIDDEN_AUTHORIZATION = (
    re.compile(r"REAL_DATA_GATE\s*=\s*OPEN", re.IGNORECASE),
    re.compile(r"real data (?:is|are) (?:now )?allowed", re.IGNORECASE),
    re.compile(r"(?:ingest|load|copy|test with) real personal data", re.IGNORECASE),
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
STALE_GATE_AUTHORITY_FIELDS = {
    "frozen_f0_contract",
    "e00_rebaseline",
    "next_implementation_contract",
}
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
        if condition:
            self.passes.append(message)
        else:
            self.failures.append(message)


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(ROOT)} must contain a YAML mapping")
    return data


def nested_path_values(state: dict[str, Any]) -> list[str]:
    next_epic = state.get("next_epic")
    next_epic = next_epic if isinstance(next_epic, dict) else {}
    candidates = [
        state.get("real_data_gate", {}).get("authority"),
        state.get("current_epic", {}).get("prompt"),
        next_epic.get("preparation_prompt"),
        state.get("architecture", {}).get("constitution"),
        state.get("architecture", {}).get("master_spec"),
        state.get("architecture", {}).get("decision_log"),
        state.get("architecture", {}).get("roadmap"),
        state.get("architecture", {}).get("epic_map"),
        state.get("next_action", {}).get("prompt"),
    ]
    return [value for value in candidates if isinstance(value, str)]


def mapping_contains_any_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(
            key in forbidden or mapping_contains_any_key(child, forbidden)
            for key, child in value.items()
        )
    if isinstance(value, list):
        return any(mapping_contains_any_key(child, forbidden) for child in value)
    return False


def validate_stable_gate_architecture(
    result: Validation, state: dict[str, Any], gate: dict[str, Any], profile: dict[str, Any]
) -> None:
    """Validate the stable policy/profile split without evaluating a candidate."""
    result.check(state.get("real_data_gate", {}).get("state") == "CLOSED", "state gate is CLOSED")
    result.check(gate.get("fail_closed_default") == "CLOSED", "policy default is CLOSED")
    result.check(
        gate.get("research_convergence_required") is True,
        "policy requires research convergence without asserting its live state",
    )
    result.check(
        gate.get("opening_rule", {}).get("automatic_opening_forbidden") is True,
        "automatic gate opening is forbidden",
    )
    result.check(
        gate.get("opening_rule", {}).get("coding_models_may_decide_gate") is False,
        "coding models cannot act as gate deciders",
    )
    result.check(
        gate.get("opening_rule", {}).get("gate_decider_role") == "REPOSITORY_OWNER",
        "policy names REPOSITORY_OWNER as gate decider",
    )
    result.check(
        gate.get("opening_rule", {}).get("attestation_method") == "local_human_attestation_v1",
        "policy names the accepted local human attestation method",
    )
    result.check(not (set(gate) & STALE_GATE_FIELDS), "stable policy has no stale dynamic fields")
    result.check(
        not (set(gate.get("authority", {})) & STALE_GATE_AUTHORITY_FIELDS),
        "stable policy has no historical implementation pointers",
    )
    result.check("profiles" not in gate.get("scope", {}), "stable policy has no profile-all scope")
    result.check(
        gate.get("authority", {}).get("profile_definition")
        == "docs/architecture/REAL_DATA_GATE_PROFILE.yaml",
        "policy profile owner path is canonical",
    )
    result.check(
        gate.get("evaluation_records", {}).get("namespace_pattern")
        == "artifacts/e11/gate-evaluations/<evaluation-id>.yaml",
        "policy declares the exact evaluation namespace",
    )
    result.check(
        gate.get("evaluation_records", {}).get("draft_can_support_open") is False
        and gate.get("evaluation_records", {}).get("sealed_content_immutable") is True,
        "policy requires DRAFT-to-SEALED fail-closed lifecycle",
    )
    result.check(
        set(gate.get("rdg_status_vocabulary", [])) == RDG_STATUSES,
        "policy has canonical RDG statuses",
    )
    requirements = gate.get("requirements", [])
    result.check(
        isinstance(requirements, list)
        and [item.get("id") for item in requirements if isinstance(item, dict)] == RDG_IDS,
        "stable policy retains RDG-01 through RDG-12 definitions",
    )
    result.check(
        not any(
            isinstance(item, dict) and ({"state", "evidence", "decision", "review"} & set(item))
            for item in requirements
        ),
        "stable policy has no per-candidate RDG state or evidence",
    )
    result.check(
        profile.get("status") == "ACCEPTED_STABLE_PROFILE_DEFINITION"
        and profile.get("authoritative") is True,
        "stable profile is authoritative",
    )
    result.check(
        isinstance(profile.get("profile_id"), str)
        and isinstance(profile.get("profile_version"), str),
        "stable profile has versioned identity",
    )
    result.check(
        profile.get("definition_lifecycle", {}).get("self_digest_forbidden") is True,
        "stable profile forbids self-owned digest",
    )
    result.check(
        not mapping_contains_any_key(profile, EXACT_EVALUATION_PROFILE_FIELDS),
        "stable profile has no exact evaluation, build, evidence, or decision fields",
    )


def terminal_accepted_state(current: dict[str, Any], epic_ids: list[str], next_epic: Any) -> bool:
    """Return whether STATE records the accepted final mapped epic."""
    return bool(epic_ids) and (
        current.get("id") == epic_ids[-1]
        and current.get("status") == "ACCEPTED"
        and next_epic is None
    )


def validate_epic_progression(
    result: Validation, state: dict[str, Any], epic_ids: list[str]
) -> None:
    """Validate accepted history and successor state for the mapped epics."""
    current = state.get("current_epic", {})
    next_epic = state.get("next_epic")
    next_epic_mapping = next_epic if isinstance(next_epic, dict) else {}
    current_id = current.get("id")
    accepted_entries = state.get("accepted_epics", [])
    accepted_ids = {
        entry if isinstance(entry, str) else entry.get("id")
        for entry in accepted_entries
        if isinstance(entry, (str, dict))
    }
    terminal_current = bool(epic_ids) and current_id == epic_ids[-1]

    if terminal_current:
        result.check(next_epic is None, "terminal E11 has no fictional successor")
        result.check(
            set(epic_ids[:-1]).issubset(accepted_ids),
            "terminal E11 preparation preserves E00-E10 acceptance history",
        )
    else:
        result.check(isinstance(next_epic, dict), "non-terminal state has a successor mapping")
        result.check(next_epic_mapping.get("status") in ALLOWED_STATUS, "next epic status is valid")

    if current_id == "E00" and current.get("review_verdict") == "FIX_REQUIRED":
        result.check(current.get("status") == "IMPLEMENTED", "E00 implementation is awaiting fixes")
        result.check(next_epic_mapping.get("status") == "PLANNED", "E01 remains PLANNED")
        result.check(
            state.get("next_action", {}).get("prompt") == current.get("fix_prompt"),
            "next action points to the E00 fix prompt",
        )
        for field in ("fix_prompt", "acceptance_report", "deviation_record"):
            value = current.get(field)
            result.check(
                isinstance(value, str) and (ROOT / value).is_file(),
                f"E00 {field} reference exists",
            )
        result.check(not accepted_ids, "no implementation epic is prematurely accepted")
    elif current_id == "E00" and current.get("status") == "ACCEPTED":
        result.check("E00" in accepted_ids, "E00 acceptance is recorded")
        result.check(next_epic_mapping.get("id") == "E01", "E01 follows accepted E00")
        result.check(
            next_epic_mapping.get("status") == "PLANNED",
            "E01 remains PLANNED until JIT preparation",
        )
    elif current_id != "E00":
        result.check("E00" in accepted_ids, "accepted E00 precedes later epic work")
        if current.get("status") == "ACCEPTED":
            result.check(current_id in accepted_ids, "later current epic acceptance is recorded")
            if terminal_accepted_state(current, epic_ids, next_epic):
                result.check(next_epic is None, "accepted terminal epic has no successor")
            else:
                current_index = epic_ids.index(current_id) if current_id in epic_ids else -1
                expected_next_id = (
                    epic_ids[current_index + 1]
                    if 0 <= current_index < len(epic_ids) - 1
                    else None
                )
                result.check(
                    next_epic_mapping.get("id") == expected_next_id,
                    "mapped successor follows accepted later current epic",
                )
                result.check(
                    next_epic_mapping.get("status") == "PLANNED",
                    "successor remains PLANNED until JIT preparation",
                )
        else:
            result.check(
                current.get("status") in {"READY", "IN_PROGRESS", "IMPLEMENTED", "BLOCKED"},
                "later current epic has an actionable status",
            )
    else:
        result.check(current.get("status") == "READY", "E00 is READY")
        result.check(not accepted_ids, "no implementation epic is prematurely accepted")


def branch_matches_workflow(
    state: dict[str, Any], epic_ids: list[str], branch: str, candidate_branch: str | None
) -> bool:
    """Allow terminal post-roadmap work only on canonical or named codex/ branches."""
    current = state.get("current_epic", {})
    if terminal_accepted_state(current, epic_ids, state.get("next_epic")):
        return branch == state.get("git", {}).get("branch") or (
            branch.startswith("codex/") and len(branch) > len("codex/")
        )
    return branch == state.get("git", {}).get("branch") or (
        current.get("status") in {"IN_PROGRESS", "IMPLEMENTED", "BLOCKED"}
        and branch == candidate_branch
    )


def main() -> int:
    result = Validation()

    for relative in REQUIRED_PATHS:
        result.check((ROOT / relative).is_file(), f"required path exists: {relative}")

    try:
        state = load_yaml(STATE_PATH)
        result.check(True, "STATE.yaml parses as a mapping")
    except Exception as exc:  # validation entry point should report, not traceback
        result.failures.append(f"STATE.yaml parse failed: {exc}")
        state = {}

    try:
        gate = load_yaml(GATE_PATH)
        result.check(True, "REAL_DATA_GATE.yaml parses as a mapping")
    except Exception as exc:
        result.failures.append(f"REAL_DATA_GATE.yaml parse failed: {exc}")
        gate = {}

    try:
        profile = load_yaml(PROFILE_PATH)
        result.check(True, "REAL_DATA_GATE_PROFILE.yaml parses as a mapping")
    except Exception as exc:
        result.failures.append(f"REAL_DATA_GATE_PROFILE.yaml parse failed: {exc}")
        profile = {}

    current = state.get("current_epic", {})
    next_epic = state.get("next_epic")
    next_epic_mapping = next_epic if isinstance(next_epic, dict) else {}
    result.check(state.get("research", {}).get("converged") is True, "research is converged")
    validate_stable_gate_architecture(result, state, gate, profile)
    result.check(current.get("status") in ALLOWED_STATUS, "current epic status is valid")
    current_id = current.get("id")
    epic_text = EPIC_MAP_PATH.read_text(encoding="utf-8") if EPIC_MAP_PATH.is_file() else ""
    epic_matches = EPIC_RE.findall(epic_text)
    epic_ids = [epic_id for epic_id, _ in epic_matches]
    result.check(
        isinstance(current_id, str) and re.fullmatch(r"E\d{2}", current_id) is not None,
        "current epic id is valid",
    )
    terminal_current = bool(epic_ids) and current_id == epic_ids[-1]
    validate_epic_progression(result, state, epic_ids)

    for relative in nested_path_values(state):
        result.check((ROOT / relative).is_file(), f"state reference exists: {relative}")

    result.check(bool(epic_ids), "epic map contains epic headings")
    result.check(len(epic_ids) == len(set(epic_ids)), "epic IDs are unique")
    result.check(
        epic_ids == [f"E{index:02d}" for index in range(12)], "epic IDs are sequential E00-E11"
    )
    result.check(current.get("id") in epic_ids, "current epic exists in epic map")
    if terminal_current:
        result.check(next_epic is None, "terminal successor representation is null")
    else:
        result.check(next_epic_mapping.get("id") in epic_ids, "next epic exists in epic map")

    current_prompt_path = ROOT / str(current.get("prompt", ""))
    current_prompt_text = (
        current_prompt_path.read_text(encoding="utf-8") if current_prompt_path.is_file() else ""
    )
    result.check(
        isinstance(current_id, str) and current_id in current_prompt_text,
        "current prompt identifies current epic",
    )
    result.check(
        "REAL_DATA_GATE" in current_prompt_text and "CLOSED" in current_prompt_text,
        "current prompt explicitly keeps gate CLOSED",
    )
    result.check(
        "synthetic" in current_prompt_text.lower(), "current prompt requires synthetic data"
    )

    for relative in MARKDOWN_PATHS:
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        result.check(text.count("```") % 2 == 0, f"Markdown fences are balanced: {relative}")
        result.check(text.startswith("# "), f"Markdown has one leading title: {relative}")

    prompt_paths = [
        ROOT / "docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md",
        ROOT / "docs/prompts/deepseek/FIX_FINDINGS_TEMPLATE.md",
        ROOT / "docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md",
        ROOT / "docs/prompts/codex/PREPARE_NEXT_EPIC.md",
        ROOT / "docs/prompts/codex/HIGH_RISK_EPIC_REVIEW_TEMPLATE.md",
    ]
    for path in prompt_paths:
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        for pattern in FORBIDDEN_AUTHORIZATION:
            result.check(
                not pattern.search(text),
                f"no real-data authorization pattern in {path.relative_to(ROOT)}: {pattern.pattern}",
            )

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    candidate_match = re.search(r"\*\*Implementation branch:\*\* `([^`]+)`", current_prompt_text)
    candidate_branch = candidate_match.group(1) if candidate_match else None
    branch_matches = branch_matches_workflow(state, epic_ids, branch, candidate_branch)
    result.check(
        branch_matches,
        "Git branch matches canonical state or the current epic candidate",
    )

    for message in result.passes:
        print(f"PASS: {message}")
    for message in result.failures:
        print(f"FAIL: {message}")

    print(
        f"SUMMARY: {len(result.passes)} passed, {len(result.failures)} failed; "
        f"epics={len(epic_ids)}, gate_default={gate.get('fail_closed_default', 'UNKNOWN')}"
    )
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
