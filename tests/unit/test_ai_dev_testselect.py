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
        summary = {"label": "x", "rc": 1, "status": "TEST_FAILURE", "failing_nodeids": ["tests/integration/test_a.py::test_bug"]}
        detectors = {"tests/integration/test_a.py::test_bug"}
        assert ai_dev_testselect._detects(summary, detectors) is True

    def test_no_detection_when_suite_passes(self) -> None:
        summary = {"label": "x", "rc": 0, "status": "PASS", "failing_nodeids": []}
        assert ai_dev_testselect._detects(summary, {"tests/a.py::t"}) is False

    def test_no_detection_when_fails_on_unrelated_test(self) -> None:
        # A non-zero rc on a NON-detector test is a different failure, not
        # mutation detection. This keeps detection evidence honest.
        summary = {"label": "x", "rc": 2, "status": "INFRA_ERROR", "failing_nodeids": ["tests/a.py::other"]}
        assert ai_dev_testselect._detects(summary, {"tests/b.py::t"}) is False

    def test_no_detection_without_detectors(self) -> None:
        summary = {"label": "x", "rc": 1, "status": "TEST_FAILURE", "failing_nodeids": ["a"]}
        assert ai_dev_testselect._detects(summary, set()) is False

    def test_no_detection_from_infra_status_even_on_detector(self) -> None:
        # A2: pytest rc=4 (usage error) with detector-like nodeids must NOT count
        # as detection — only a trustworthy TEST_FAILURE may establish it.
        summary = {"label": "x", "rc": 4, "status": "INFRA_ERROR", "failing_nodeids": ["tests/b.py::t"]}
        assert ai_dev_testselect._detects(summary, {"tests/b.py::t"}) is False


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


class TestPytestStatusClassification:
    """A2: explicit deterministic pytest-result status semantics."""

    def test_rc0_clean_is_pass(self) -> None:
        assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeids": []}, 0) == "PASS"

    def test_rc1_with_failures_is_test_failure(self) -> None:
        packet = {"truncated": False, "failure_nodeids": ["tests/a.py::t"]}
        assert ai_dev_testselect.classify_run(packet, 1) == "TEST_FAILURE"

    def test_infrastructure_rcs_are_infra_error(self) -> None:
        # rc 2 = interrupted, 3 = internal error, 4 = usage error.
        for rc in (2, 3, 4):
            assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeids": []}, rc) == "INFRA_ERROR"

    def test_rc5_is_no_tests(self) -> None:
        assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeids": []}, 5) == "NO_TESTS"

    def test_truncated_reportlog_is_incomplete_even_with_rc1(self) -> None:
        assert ai_dev_testselect.classify_run({"truncated": True, "failure_nodeids": ["a"]}, 1) == "INCOMPLETE"

    def test_nonzero_rc_without_failures_is_infra(self) -> None:
        # rc=1 but a clean session with no parsed failures is untrustworthy.
        assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeids": []}, 1) == "INFRA_ERROR"

    def test_missing_reportlog_is_incomplete(self) -> None:
        counts = ai_dev_testselect.parse_reportlog_counts(Path("no-such-artifact.jsonl"))
        assert counts["status"] == "INCOMPLETE"
        assert counts["failing"] == []

    def test_malformed_reportlog_is_incomplete(self, tmp_path: Path) -> None:
        p = tmp_path / "bad.jsonl"
        p.write_text('{"$report_type": "SessionStart"}\nNOT_JSON\n', encoding="utf-8")
        counts = ai_dev_testselect.parse_reportlog_counts(p)
        assert counts["status"] == "INCOMPLETE"
        assert counts["failing"] == []


class TestCompleteMachineAccounting:
    """A1: the selector reads COMPLETE detector identities, never the bounded
    AI-facing failure presentation."""

    def test_failing_nodeids_are_complete_beyond_presentation_cap(self, tmp_path: Path) -> None:
        import json

        lines = ['{"pytest_version": "9.1.1", "$report_type": "SessionStart"}']
        for i in range(20):
            lines.append(
                json.dumps(
                    {
                        "nodeid": f"tests/t.py::test_{i}",
                        "when": "call",
                        "outcome": "failed",
                        "longrepr": {"reprcrash": {"message": f"AssertionError: f{i}"}},
                        "$report_type": "TestReport",
                    }
                )
            )
        lines.append('{"exitstatus": 1, "$report_type": "SessionFinish"}')
        p = tmp_path / "many.jsonl"
        p.write_text("\n".join(lines), encoding="utf-8")

        counts = ai_dev_testselect.parse_reportlog_counts(p, rc=1)
        assert counts["status"] == "TEST_FAILURE"
        expected = {f"tests/t.py::test_{i}" for i in range(20)}
        assert set(counts["failing"]) == expected  # complete, not the capped 10
