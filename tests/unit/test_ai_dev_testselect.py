"""Focused unit tests for the Wave 2 test-selection tournament accounting.

Covers mutation detection logic (a selector detects a mutation only when its
selected suite fails on a detector nodeid), scenario mutation application
(exact-once match), and full-pytest-truth semantics.
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_testselect  # noqa: E402


class TestDetection:
    def test_detects_when_selected_suite_fails_on_detector(self) -> None:
        summary = {"label": "x", "rc": 1, "failing_nodeids": ["tests/integration/test_a.py::test_bug"]}
        detectors = {"tests/integration/test_a.py::test_bug"}
        assert ai_dev_testselect._detects(summary, detectors) is True

    def test_no_detection_when_suite_passes(self) -> None:
        summary = {"label": "x", "rc": 0, "failing_nodeids": []}
        assert ai_dev_testselect._detects(summary, {"tests/a.py::t"}) is False

    def test_no_detection_when_fails_on_unrelated_test(self) -> None:
        # A non-zero rc on a NON-detector test is a different failure, not
        # mutation detection. This keeps detection evidence honest.
        summary = {"label": "x", "rc": 2, "failing_nodeids": ["tests/a.py::other"]}
        assert ai_dev_testselect._detects(summary, {"tests/b.py::t"}) is False

    def test_no_detection_without_detectors(self) -> None:
        summary = {"label": "x", "rc": 1, "failing_nodeids": ["a"]}
        assert ai_dev_testselect._detects(summary, set()) is False


class TestMutationApplication:
    def test_applies_exactly_once(self, tmp_path: Path) -> None:
        mod = tmp_path / "src" / "psyche_os"
        mod.mkdir(parents=True)
        f = mod / "leaf.py"
        f.write_text("def f():\n    return True\n", encoding="utf-8")
        scenario = {
            "scenario_id": "s1",
            "module": "src/psyche_os/leaf.py",
            "mutation": {"old": "return True", "new": "return False", "desc": "invert"},
        }
        ai_dev_testselect.apply_mutation(scenario, tmp_path)
        assert f.read_text(encoding="utf-8") == "def f():\n    return False\n"

    def test_fails_loudly_when_old_string_not_unique(self, tmp_path: Path) -> None:
        mod = tmp_path / "src"
        mod.mkdir(parents=True)
        f = mod / "x.py"
        f.write_text("a = 1\na = 1\n", encoding="utf-8")
        scenario = {
            "scenario_id": "s1",
            "module": "src/x.py",
            "mutation": {"old": "a = 1", "new": "a = 2", "desc": "dup"},
        }
        with pytest.raises(ai_dev_testselect.TestSelectError):
            ai_dev_testselect.apply_mutation(scenario, tmp_path)

    def test_fails_loudly_when_old_string_missing(self, tmp_path: Path) -> None:
        mod = tmp_path / "src"
        mod.mkdir(parents=True)
        (mod / "x.py").write_text("a = 1\n", encoding="utf-8")
        scenario = {
            "scenario_id": "s1",
            "module": "src/x.py",
            "mutation": {"old": "b = 9", "new": "b = 10", "desc": "missing"},
        }
        with pytest.raises(ai_dev_testselect.TestSelectError):
            ai_dev_testselect.apply_mutation(scenario, tmp_path)


class TestReportlogAccounting:
    def test_summary_captures_counts(self) -> None:
        assert ai_dev_testselect._summary(
            {"label": "x", "rc": 0, "duration_ms": 5.0, "reportlog": "no-such-file.jsonl"}
        )["selected"] == 0
