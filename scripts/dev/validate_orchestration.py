"""Validate the lean PSYCHE OS development-orchestration layer.

This deliberately checks documentation/state contracts only. It does not claim
that F0 exists, that security controls work, or that real data is permitted.
PyYAML is already used by the repository research validators.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[2]
STATE_PATH = ROOT / "docs/development/STATE.yaml"
GATE_PATH = ROOT / "docs/architecture/REAL_DATA_GATE.yaml"
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
    candidates = [
        state.get("real_data_gate", {}).get("authority"),
        state.get("current_epic", {}).get("prompt"),
        state.get("next_epic", {}).get("preparation_prompt"),
        state.get("architecture", {}).get("constitution"),
        state.get("architecture", {}).get("master_spec"),
        state.get("architecture", {}).get("decision_log"),
        state.get("architecture", {}).get("roadmap"),
        state.get("architecture", {}).get("epic_map"),
        state.get("next_action", {}).get("prompt"),
    ]
    return [value for value in candidates if isinstance(value, str)]


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

    current = state.get("current_epic", {})
    next_epic = state.get("next_epic", {})
    result.check(state.get("research", {}).get("converged") is True, "research is converged")
    result.check(state.get("real_data_gate", {}).get("state") == "CLOSED", "state gate is CLOSED")
    result.check(gate.get("status") == "CLOSED", "authoritative gate is CLOSED")
    result.check(
        gate.get("opening_rule", {}).get("automatic_opening_forbidden") is True,
        "automatic gate opening is forbidden",
    )
    result.check(current.get("status") in ALLOWED_STATUS, "current epic status is valid")
    result.check(next_epic.get("status") in ALLOWED_STATUS, "next epic status is valid")
    result.check(current.get("id") == "E00", "current epic is E00")
    result.check(current.get("status") == "READY", "E00 is READY")
    result.check(current.get("prompt") == "docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md", "E00 prompt path matches state")
    result.check(state.get("accepted_epics") == [], "no implementation epic is prematurely accepted")

    for relative in nested_path_values(state):
        result.check((ROOT / relative).is_file(), f"state reference exists: {relative}")

    epic_text = EPIC_MAP_PATH.read_text(encoding="utf-8") if EPIC_MAP_PATH.is_file() else ""
    epic_matches = EPIC_RE.findall(epic_text)
    epic_ids = [epic_id for epic_id, _ in epic_matches]
    result.check(bool(epic_ids), "epic map contains epic headings")
    result.check(len(epic_ids) == len(set(epic_ids)), "epic IDs are unique")
    result.check(epic_ids == [f"E{index:02d}" for index in range(12)], "epic IDs are sequential E00-E11")
    result.check(current.get("id") in epic_ids, "current epic exists in epic map")
    result.check(next_epic.get("id") in epic_ids, "next epic exists in epic map")

    e00_path = ROOT / str(current.get("prompt", ""))
    e00_text = e00_path.read_text(encoding="utf-8") if e00_path.is_file() else ""
    result.check("EPIC E00" in e00_text, "E00 prompt identifies E00")
    result.check("REAL_DATA_GATE = CLOSED" in e00_text, "E00 explicitly keeps gate CLOSED")
    result.check("synthetic" in e00_text.lower(), "E00 explicitly requires synthetic data")

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
            result.check(not pattern.search(text), f"no real-data authorization pattern in {path.relative_to(ROOT)}: {pattern.pattern}")

    branch = subprocess.run(
        ["git", "branch", "--show-current"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    ).stdout.strip()
    result.check(branch == state.get("git", {}).get("branch"), "STATE branch matches current Git branch")

    for message in result.passes:
        print(f"PASS: {message}")
    for message in result.failures:
        print(f"FAIL: {message}")

    print(
        f"SUMMARY: {len(result.passes)} passed, {len(result.failures)} failed; "
        f"epics={len(epic_ids)}, gate={gate.get('status', 'UNKNOWN')}"
    )
    return 1 if result.failures else 0


if __name__ == "__main__":
    sys.exit(main())
