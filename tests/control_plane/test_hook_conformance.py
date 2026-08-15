"""Cross-platform hook conformance suite (component C).

Deterministic tests over the existing dispatcher/security guard. They prove
equivalent protected-path semantics across supported path representations —
relative, dot-relative, absolute Windows, mixed separators, case variance,
worktree-absolute, traversal, exact protected file, and directory descendants —
plus that near-prefix lookalikes and ordinary source remain allowed.

These tests import the real `security_guard` module (the same module the hook
dispatcher uses), so they validate the production guard, not a copy.
"""
from __future__ import annotations

import os
from pathlib import Path

from modules import security_guard

REPO = str(Path(__file__).resolve().parents[2])

PROTECTED = [
    ".ai-dev/policy",
    ".ai-dev/verification",
    ".ai-dev/hooks",
    ".ai-dev/telemetry/schema.json",
    ".ai-dev/state.yaml",
    "AGENTS.md",
    "CONSTITUTION.md",
]


def _is_protected(target: str) -> bool:
    return security_guard._is_protected(target, REPO, PROTECTED)


class TestProtectedPathForms:
    def test_relative_protected(self) -> None:
        assert _is_protected(".ai-dev/state.yaml")

    def test_dot_relative_protected(self) -> None:
        assert _is_protected("./.ai-dev/state.yaml")

    def test_absolute_windows_protected(self) -> None:
        target = os.path.join(REPO, ".ai-dev", "state.yaml")
        assert "\\" in target  # Windows path form under test
        assert _is_protected(target)

    def test_mixed_separator_protected(self) -> None:
        # forward slash for the repo prefix, backslash for the protected suffix.
        target = REPO.replace("\\", "/") + "/.ai-dev\\state.yaml"
        assert _is_protected(target)

    def test_case_variant_protected(self) -> None:
        # Windows NTFS is case-insensitive: this is the same protected file.
        assert _is_protected(".AI-DEV/STATE.YAML")

    def test_case_variant_absolute_protected(self) -> None:
        target = os.path.join(REPO, ".AI-DEV", "State.Yaml")
        assert _is_protected(target)

    def test_worktree_absolute_protected(self) -> None:
        # an absolute path under the current (candidate) worktree.
        target = os.path.abspath(os.path.join(REPO, ".ai-dev", "state.yaml"))
        assert _is_protected(target)

    def test_traversal_form_protected(self) -> None:
        # `..` traversal through a non-protected parent still resolves to a protected file.
        target = os.path.join(REPO, "tmp", "..", ".ai-dev", "state.yaml")
        assert _is_protected(target)

    def test_relative_traversal_form_protected(self) -> None:
        assert _is_protected(".ai-dev/../.ai-dev/state.yaml")

    def test_exact_protected_file(self) -> None:
        assert _is_protected(".ai-dev/telemetry/schema.json")

    def test_protected_directory_descendant(self) -> None:
        assert _is_protected(".ai-dev/policy/risk.yaml")


class TestNonProtectedPathForms:
    def test_near_prefix_allowed(self) -> None:
        assert not _is_protected(".ai-dev/policy-notes/example.yaml")

    def test_near_prefix_file_allowed(self) -> None:
        assert not _is_protected(".ai-dev/state.yaml.backup")

    def test_root_file_suffix_allowed(self) -> None:
        assert not _is_protected("AGENTS.md.bak")

    def test_normal_source_allowed(self) -> None:
        assert not _is_protected("src/psyche_os/__main__.py")

    def test_normal_script_allowed(self) -> None:
        assert not _is_protected("scripts/ai_dev_v2.py")


class TestToolUseGuard:
    def test_edit_protected_blocked(self) -> None:
        blocked, reason = security_guard.check_tool_use(
            {"tool_name": "Edit", "tool_input": {"file_path": ".ai-dev/state.yaml"}}, REPO
        )
        assert blocked
        assert reason

    def test_edit_normal_allowed(self) -> None:
        blocked, reason = security_guard.check_tool_use(
            {"tool_name": "Edit", "tool_input": {"file_path": "scripts/ai_dev_v2.py"}}, REPO
        )
        assert not blocked
        assert reason == ""

    def test_write_absolute_protected_blocked(self) -> None:
        blocked, _ = security_guard.check_tool_use(
            {"tool_name": "Write", "tool_input": {"file_path": os.path.join(REPO, "AGENTS.md")}},
            REPO,
        )
        assert blocked

    def test_bash_destructive_blocked(self) -> None:
        blocked, _ = security_guard.check_tool_use(
            {"tool_name": "Bash", "tool_input": {"command": "git push --force origin main"}}, REPO
        )
        assert blocked

    def test_bash_normal_allowed(self) -> None:
        blocked, _ = security_guard.check_tool_use(
            {"tool_name": "Bash", "tool_input": {"command": "uv run pytest -q"}}, REPO
        )
        assert not blocked

    def test_stop_never_blocks(self) -> None:
        assert security_guard.check_stop({"stop_hook_active": False}) == ""
