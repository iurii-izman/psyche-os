"""Focused unit tests for the Wave 2 test-selection tournament accounting.

Covers mutation detection logic (a selector detects a mutation only when its
selected suite fails on a detector fingerprint), scenario mutation application
(exact-once match), and full-pytest-truth semantics.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_testselect  # noqa: E402


def _fp(seed: str) -> str:
    """Deterministic stand-in SHA-256 fingerprint for a raw nodeid."""
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _session_start() -> str:
    return _line({"pytest_version": "9.1.1", "$report_type": "SessionStart"})


def _session_finish(exitstatus: int) -> str:
    return _line({"exitstatus": exitstatus, "$report_type": "SessionFinish"})


def _test_report(nodeid: str, when: str, outcome: str, longrepr=None) -> str:
    return _line({"nodeid": nodeid, "when": when, "outcome": outcome, "longrepr": longrepr, "$report_type": "TestReport"})


def _failure_artifact(tmp_path: Path, name: str, nodeid: str) -> Path:
    p = tmp_path / name
    p.write_text(
        "\n".join(
            [
                _session_start(),
                _test_report(nodeid, "call", "failed", {"reprcrash": {"message": "AssertionError: boom"}}),
                _session_finish(1),
            ]
        ),
        encoding="utf-8",
    )
    return p


class TestDetection:
    def test_detects_when_selected_suite_fails_on_detector(self) -> None:
        summary = {
            "label": "x", "rc": 1, "status": "TEST_FAILURE",
            "failing_nodeids": ["tests/integration/test_a.py::test_bug"],
            "failing_fingerprints": [_fp("tests/integration/test_a.py::test_bug")],
        }
        detectors = {_fp("tests/integration/test_a.py::test_bug")}
        assert ai_dev_testselect._detects(summary, detectors) is True

    def test_no_detection_when_suite_passes(self) -> None:
        summary = {"label": "x", "rc": 0, "status": "PASS", "failing_nodeids": [], "failing_fingerprints": []}
        assert ai_dev_testselect._detects(summary, {_fp("tests/a.py::t")}) is False

    def test_no_detection_when_fails_on_unrelated_test(self) -> None:
        # A non-zero rc on a NON-detector test is a different failure, not
        # mutation detection. This keeps detection evidence honest.
        summary = {
            "label": "x", "rc": 2, "status": "INFRA_ERROR",
            "failing_nodeids": ["tests/a.py::other"],
            "failing_fingerprints": [_fp("tests/a.py::other")],
        }
        assert ai_dev_testselect._detects(summary, {_fp("tests/b.py::t")}) is False

    def test_no_detection_without_detectors(self) -> None:
        summary = {
            "label": "x", "rc": 1, "status": "TEST_FAILURE",
            "failing_nodeids": ["a"], "failing_fingerprints": [_fp("a")],
        }
        assert ai_dev_testselect._detects(summary, set()) is False

    def test_no_detection_from_infra_status_even_on_detector(self) -> None:
        # A2: pytest rc=4 (usage error) with detector-like fingerprints must NOT
        # count as detection — only a trustworthy TEST_FAILURE may establish it.
        summary = {
            "label": "x", "rc": 4, "status": "INFRA_ERROR",
            "failing_nodeids": ["tests/b.py::t"],
            "failing_fingerprints": [_fp("tests/b.py::t")],
        }
        assert ai_dev_testselect._detects(summary, {_fp("tests/b.py::t")}) is False


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
        assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeid_fingerprints": []}, 0) == "PASS"

    def test_rc1_with_failures_is_test_failure(self) -> None:
        packet = {"truncated": False, "failure_nodeid_fingerprints": [_fp("tests/a.py::t")]}
        assert ai_dev_testselect.classify_run(packet, 1) == "TEST_FAILURE"

    def test_infrastructure_rcs_are_infra_error(self) -> None:
        # rc 2 = interrupted, 3 = internal error, 4 = usage error.
        for rc in (2, 3, 4):
            assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeid_fingerprints": []}, rc) == "INFRA_ERROR"

    def test_rc5_is_no_tests(self) -> None:
        assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeid_fingerprints": []}, 5) == "NO_TESTS"

    def test_truncated_reportlog_is_incomplete_even_with_rc1(self) -> None:
        assert ai_dev_testselect.classify_run({"truncated": True, "failure_nodeid_fingerprints": [_fp("a")]}, 1) == "INCOMPLETE"

    def test_nonzero_rc_without_failures_is_infra(self) -> None:
        # rc=1 but a clean session with no parsed failures is untrustworthy.
        assert ai_dev_testselect.classify_run({"truncated": False, "failure_nodeid_fingerprints": []}, 1) == "INFRA_ERROR"

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
        assert set(counts["failing"]) == expected  # complete display, not the capped 10
        assert len(counts["failing_fingerprints"]) == 20  # complete machine truth, not capped
        assert len(set(counts["failing_fingerprints"])) == 20  # exact identity preserved


class TestNodeidFingerprintMatching:
    """A6 closure: machine matching uses deterministic fingerprints, never raw
    or redacted display nodeids. Redaction must never create a false positive or
    collapse two distinct identities."""

    def test_same_raw_nodeid_matches_across_full_and_selected(self, tmp_path: Path) -> None:
        token = "sk-proj-" + "A" * 24
        nodeid = f"tests/t.py::test_x[{token}]"
        full = ai_dev_testselect.parse_reportlog_counts(_failure_artifact(tmp_path, "full.jsonl", nodeid), rc=1)
        selected = ai_dev_testselect.parse_reportlog_counts(_failure_artifact(tmp_path, "selected.jsonl", nodeid), rc=1)
        assert full["status"] == "TEST_FAILURE"
        assert set(full["failing_fingerprints"]) == set(selected["failing_fingerprints"])
        summary = {
            "label": "current", "rc": 1, "status": "TEST_FAILURE",
            "failing_nodeids": selected["failing"],
            "failing_fingerprints": selected["failing_fingerprints"],
        }
        assert ai_dev_testselect._detects(summary, set(full["failing_fingerprints"])) is True
        # The raw secret never enters either counts payload.
        assert token not in json.dumps(full)
        assert token not in json.dumps(selected)

    def test_distinct_secret_nodeids_do_not_false_match(self, tmp_path: Path) -> None:
        token_a = "sk-proj-" + "B" * 24
        token_b = "sk-proj-" + "C" * 24
        nodeid_a = f"tests/test_x.py::test_x[{token_a}]"
        nodeid_b = f"tests/test_x.py::test_x[{token_b}]"
        full = ai_dev_testselect.parse_reportlog_counts(_failure_artifact(tmp_path, "full.jsonl", nodeid_a), rc=1)
        selected = ai_dev_testselect.parse_reportlog_counts(_failure_artifact(tmp_path, "selected.jsonl", nodeid_b), rc=1)
        # The redacted display is identical — presentation collapses; machine truth must not.
        assert full["failing"] == selected["failing"]
        fp_full = set(full["failing_fingerprints"])
        fp_selected = set(selected["failing_fingerprints"])
        assert fp_full & fp_selected == set()
        summary = {
            "label": "current", "rc": 1, "status": "TEST_FAILURE",
            "failing_nodeids": selected["failing"],
            "failing_fingerprints": list(fp_selected),
        }
        assert ai_dev_testselect._detects(summary, fp_full) is False

    def test_persisted_selector_evidence_has_no_raw_secret(self, tmp_path: Path, monkeypatch) -> None:
        token = "sk-proj-" + "A" * 24
        nodeid = f"tests/t.py::test_x[{token}]"
        counts = ai_dev_testselect.parse_reportlog_counts(_failure_artifact(tmp_path, "run.jsonl", nodeid), rc=1)
        summary = {
            "label": "current", "rc": 1, "duration_ms": 5.0, "status": counts["status"],
            "selected": counts["collected"], "failed": counts["failed"], "errors": counts["errors"],
            "failing_nodeids": counts["failing"],
            "failing_fingerprints": counts["failing_fingerprints"],
        }
        out = {
            "schema_version": 1,
            "scenario_id": "synthetic-a6",
            "detectors": sorted(counts["failing_fingerprints"]),
            "selector_results": {"current": {**summary, "detected": True}},
        }
        evidence_root = tmp_path / "evidence"
        monkeypatch.setattr(ai_dev_testselect, "EVIDENCE_ROOT", evidence_root)
        ai_dev_testselect._write_evidence("synthetic-a6", "result", out)
        text = (evidence_root / "synthetic-a6" / "result.json").read_text(encoding="utf-8")
        assert token not in text
        assert "[REDACTED]" in text
        assert counts["failing_fingerprints"][0] in text  # machine truth persists as fingerprint
