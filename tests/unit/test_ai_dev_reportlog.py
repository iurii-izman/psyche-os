"""Focused unit tests for the Wave 1 pytest-reportlog deterministic parser.

Covers: PASS parsing, failure parsing, malformed/incomplete logs, fail-closed
integration with `ai_dev_perf.run_pytest`, and raw-artifact linkage. Synthetic
artifacts only — never real data.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_perf  # noqa: E402
import ai_dev_reportlog  # noqa: E402


def _line(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False)


def _session_start() -> str:
    return _line({"pytest_version": "9.1.1", "$report_type": "SessionStart"})


def _session_finish(exitstatus: int) -> str:
    return _line({"exitstatus": exitstatus, "$report_type": "SessionFinish"})


def _test_report(nodeid: str, when: str, outcome: str, longrepr=None) -> str:
    return _line({"nodeid": nodeid, "when": when, "outcome": outcome, "longrepr": longrepr, "$report_type": "TestReport"})


def _collect(nodeid: str, outcome: str = "passed", longrepr=None) -> str:
    return _line({"nodeid": nodeid, "outcome": outcome, "longrepr": longrepr, "$report_type": "CollectReport"})


def _fail_longrepr(exc_type: str, msg: str) -> dict:
    return {
        "reprcrash": {"path": "x.py", "lineno": 1, "message": f"{exc_type}: {msg}"},
        "reprtraceback": {"reprentries": [{"data": {"lines": [f"E   {exc_type}: {msg}", "E   assert x"]}, "type": "ReprEntry"}], "style": "short"},
    }


@pytest.fixture
def pass_artifact(tmp_path: Path) -> Path:
    p = tmp_path / "pass.jsonl"
    p.write_text(
        "\n".join(
            [
                _session_start(),
                _collect("tests/t.py"),
                _test_report("tests/t.py::test_a", "setup", "passed"),
                _test_report("tests/t.py::test_a", "call", "passed"),
                _test_report("tests/t.py::test_a", "teardown", "passed"),
                _test_report("tests/t.py::test_b", "setup", "passed"),
                _test_report("tests/t.py::test_b", "call", "skipped"),
                _test_report("tests/t.py::test_b", "teardown", "passed"),
                _session_finish(0),
            ]
        ),
        encoding="utf-8",
    )
    return p


class TestReportLogParsing:
    def test_pass_parsing(self, pass_artifact: Path) -> None:
        result = ai_dev_reportlog.parse_reportlog(pass_artifact)
        assert result["exit_code"] == 0
        assert result["truncated"] is False
        coll = result["collection"]
        assert coll["collected"] == 2
        assert coll["passed"] == 1
        assert coll["skipped"] == 1
        assert coll["failed"] == 0
        assert coll["errors"] == 0
        assert result["failures"] == []

    def test_failure_parsing(self, tmp_path: Path) -> None:
        p = tmp_path / "fail.jsonl"
        p.write_text(
            "\n".join(
                [
                    _session_start(),
                    _test_report("tests/t.py::test_x", "setup", "passed"),
                    _test_report("tests/t.py::test_x", "call", "failed", _fail_longrepr("AssertionError", "boom")),
                    _test_report("tests/t.py::test_x", "teardown", "passed"),
                    _session_finish(1),
                ]
            ),
            encoding="utf-8",
        )
        result = ai_dev_reportlog.parse_reportlog(p)
        coll = result["collection"]
        assert coll["failed"] == 1
        assert result["exit_code"] == 1
        assert len(result["failures"]) == 1
        f = result["failures"][0]
        assert f["nodeid"] == "tests/t.py::test_x"
        assert f["phase"] == "call"
        assert f["error_type"] == "AssertionError"
        assert "boom" in f["message"]
        assert "E   AssertionError: boom" in f["traceback_excerpt"]

    def test_setup_error_counts_as_error(self, tmp_path: Path) -> None:
        p = tmp_path / "err.jsonl"
        p.write_text(
            "\n".join(
                [
                    _session_start(),
                    _test_report("tests/t.py::test_y", "setup", "failed", _fail_longrepr("RuntimeError", "fixture broken")),
                    _session_finish(1),
                ]
            ),
            encoding="utf-8",
        )
        result = ai_dev_reportlog.parse_reportlog(p)
        coll = result["collection"]
        assert coll["errors"] == 1
        assert coll["failed"] == 0
        assert result["failures"][0]["phase"] == "setup"

    def test_collection_error_counts_as_error(self, tmp_path: Path) -> None:
        p = tmp_path / "coll.jsonl"
        p.write_text(
            "\n".join(
                [
                    _session_start(),
                    _collect("tests/bad.py", "failed", "ImportError while importing test module"),
                    _session_finish(2),
                ]
            ),
            encoding="utf-8",
        )
        result = ai_dev_reportlog.parse_reportlog(p)
        assert result["collection"]["errors"] == 1
        assert result["exit_code"] == 2
        assert result["failures"][0]["phase"] == "collection"

    def test_malformed_and_incomplete_log_is_truncated(self, tmp_path: Path) -> None:
        p = tmp_path / "trunc.jsonl"
        p.write_text(_session_start() + "\nNOT_JSON\n" + _test_report("t.py::t", "call", "passed") + "\n", encoding="utf-8")
        result = ai_dev_reportlog.parse_reportlog(p)
        assert result["truncated"] is True
        assert result["exit_code"] is None
        assert result["malformed_lines"] == 1
        assert result["collection"]["passed"] == 1

    def test_missing_artifact_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ai_dev_reportlog.ReportLogError):
            ai_dev_reportlog.parse_reportlog(tmp_path / "nope.jsonl")

    def test_raw_artifact_linkage(self, pass_artifact: Path) -> None:
        result = ai_dev_reportlog.parse_reportlog(pass_artifact)
        assert result["raw_evidence"] == str(pass_artifact.resolve())
        assert "raw_evidence" in ai_dev_reportlog.render_summary(result)

    def test_render_summary_is_bounded_and_deterministic(self, tmp_path: Path) -> None:
        p = tmp_path / "many.jsonl"
        lines = [_session_start()]
        for i in range(30):
            lines.append(_test_report(f"tests/t.py::test_{i}", "setup", "passed"))
            lines.append(_test_report(f"tests/t.py::test_{i}", "call", "failed", _fail_longrepr("AssertionError", f"failure {i}")))
        lines.append(_session_finish(1))
        p.write_text("\n".join(lines), encoding="utf-8")
        result = ai_dev_reportlog.parse_reportlog(p)
        assert result["failures_truncated"] is True
        assert len(result["failures"]) <= ai_dev_reportlog.MAX_FAILURES
        assert result["collection"]["failed"] == 30
        s1 = ai_dev_reportlog.render_summary(result)
        s2 = ai_dev_reportlog.render_summary(result)
        assert s1 == s2  # deterministic


# --------------------------------------------------------------------------- fail-closed integration


class TestRunPytestReportLogFailClosed:
    def _fake_run_cmd(self, artifact: Path, rc: int, stdout: str):
        def _fake(args: list[str], **kwargs) -> subprocess.CompletedProcess:
            return subprocess.CompletedProcess(args, returncode=rc, stdout=stdout, stderr="")
        return _fake

    def test_rc0_clean_log_is_pass(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pass_artifact: Path) -> None:
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        artifact = raw_dir / "report-log.jsonl"
        artifact.write_text(pass_artifact.read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.setattr(ai_dev_perf, "run_cmd", self._fake_run_cmd(artifact, 0, "1 passed"))
        index = _dummy_index()
        result = ai_dev_perf.run_pytest(index, ["tests/t.py"], raw_dir=raw_dir, source_changed=True, reportlog=True)
        assert result["status"] == "PASS"
        assert result["reportlog"]["available"] is True
        assert result["collected"] == 2

    def test_rc_nonzero_with_parsed_failures_is_fail(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        artifact = raw_dir / "report-log.jsonl"
        artifact.write_text(
            "\n".join(
                [
                    _session_start(),
                    _test_report("tests/t.py::test_x", "call", "failed", _fail_longrepr("AssertionError", "boom")),
                    _session_finish(1),
                ]
            ),
            encoding="utf-8",
        )
        monkeypatch.setattr(ai_dev_perf, "run_cmd", self._fake_run_cmd(artifact, 1, "1 failed"))
        result = ai_dev_perf.run_pytest(_dummy_index(), ["tests/t.py"], raw_dir=raw_dir, source_changed=True, reportlog=True)
        assert result["rc"] == 1
        assert result["status"] == "FAIL"
        assert result["status"] != "PASS"

    def test_rc0_but_truncated_log_is_unknown_never_pass(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        artifact = raw_dir / "report-log.jsonl"
        artifact.write_text(_session_start() + "\n" + _test_report("t.py::t", "call", "passed") + "\n", encoding="utf-8")
        monkeypatch.setattr(ai_dev_perf, "run_cmd", self._fake_run_cmd(artifact, 0, "1 passed"))
        result = ai_dev_perf.run_pytest(_dummy_index(), ["tests/t.py"], raw_dir=raw_dir, source_changed=True, reportlog=True)
        assert result["status"] == "UNKNOWN"
        assert result["status"] != "PASS"

    def test_reportlog_missing_degrades_to_stdout_parse(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """If the plugin/artifact is unavailable, the plain stdout path still works."""
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        fake = subprocess.CompletedProcess(["uv", "run", "pytest"], returncode=0, stdout="1 passed", stderr="")
        monkeypatch.setattr(ai_dev_perf, "run_cmd", lambda *a, **k: fake)
        result = ai_dev_perf.run_pytest(_dummy_index(), ["tests/t.py"], raw_dir=raw_dir, source_changed=True, reportlog=True)
        assert result["status"] == "PASS"
        assert result["reportlog"] == {"available": False}

    def test_raw_artifact_path_preserved(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, pass_artifact: Path) -> None:
        raw_dir = tmp_path / "raw"
        raw_dir.mkdir()
        artifact = raw_dir / "report-log.jsonl"
        artifact.write_text(pass_artifact.read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.setattr(ai_dev_perf, "run_cmd", self._fake_run_cmd(artifact, 0, "1 passed"))
        result = ai_dev_perf.run_pytest(_dummy_index(), ["tests/t.py"], raw_dir=raw_dir, source_changed=True, reportlog=True)
        assert result["reportlog"]["packet"]["raw_evidence"] == str(artifact.resolve())


# --------------------------------------------------------------------------- A1 machine truth + A6 schema/redaction


class TestMachineTruthUncapped:
    """A1: complete deterministic machine accounting independent of the bounded
    AI-facing presentation."""

    def test_machine_failure_ids_complete_while_presentation_bounded(self, tmp_path: Path) -> None:
        p = tmp_path / "many.jsonl"
        n = 25
        lines = [_session_start()]
        for i in range(n):
            lines.append(_test_report(f"tests/t.py::test_{i}", "call", "failed", _fail_longrepr("AssertionError", f"failure {i}")))
        lines.append(_session_finish(1))
        p.write_text("\n".join(lines), encoding="utf-8")

        result = ai_dev_reportlog.parse_reportlog(p)
        expected = {f"tests/t.py::test_{i}" for i in range(n)}
        assert set(result["failure_nodeids"]) == expected
        assert result["failure_records_count"] == n
        assert result["collection"]["failed"] == n
        # Presentation stays bounded; machine truth does not.
        assert len(result["failures"]) <= ai_dev_reportlog.MAX_FAILURES
        assert result["failures_truncated"] is True
        assert len(result["failures"]) < n


class TestNonObjectJsonEvents:
    """A6: valid JSON that is not an object must not crash the parser."""

    @pytest.mark.parametrize("bad", ["null", "[]", '"string"', "123"])
    def test_non_object_event_is_malformed_not_crash(self, tmp_path: Path, bad: str) -> None:
        p = tmp_path / "bad.jsonl"
        p.write_text("\n".join([_session_start(), bad, _session_finish(0)]), encoding="utf-8")
        result = ai_dev_reportlog.parse_reportlog(p)
        assert result["malformed_lines"] == 1
        assert result["truncated"] is True
        assert result["exit_code"] == 0  # SessionFinish parsed; damage is still flagged
        # Callers see truncated -> UNKNOWN, never a green from the malformed line.
        assert result["collection"]["passed"] == 0

    def test_incomplete_stream_stays_non_green(self, tmp_path: Path) -> None:
        p = tmp_path / "cut.jsonl"
        p.write_text("\n".join([_session_start(), "null", _test_report("t::x", "call", "passed")]), encoding="utf-8")
        result = ai_dev_reportlog.parse_reportlog(p)
        assert result["truncated"] is True
        assert result["exit_code"] is None


class TestSecretRedaction:
    """A6: deterministic redaction before any AI-facing rendering."""

    def test_redaction_in_message_traceback_and_command(self, tmp_path: Path) -> None:
        secret = "sk-proj-synthetictestsecret123456"
        longrepr = {
            "reprcrash": {"path": "x.py", "lineno": 1, "message": f"AssertionError: token {secret} leaked"},
            "reprtraceback": {
                "reprentries": [{"data": {"lines": [f"E   AssertionError: token {secret} leaked", "E   assert x"]}, "type": "ReprEntry"}]
            },
        }
        p = tmp_path / "sec.jsonl"
        p.write_text(
            "\n".join(
                [
                    _session_start(),
                    _test_report("tests/t.py::t", "call", "failed", longrepr),
                    _session_finish(1),
                ]
            ),
            encoding="utf-8",
        )
        result = ai_dev_reportlog.parse_reportlog(p, command=f"uv run pytest --token {secret}")
        f = result["failures"][0]
        assert secret not in f["message"]
        assert secret not in f["traceback_excerpt"]
        assert "[REDACTED]" in f["message"]
        assert "[REDACTED]" in f["traceback_excerpt"]
        assert secret not in result["command"]
        assert secret not in result["failure_nodeids"]
        summary = ai_dev_reportlog.render_summary(result)
        assert secret not in summary

    def test_redaction_handles_bearer_and_api_key_assignments(self) -> None:
        text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz012345\napi_key=sk-secretvalue1234567890\n"
        redacted = ai_dev_reportlog.redact_secret(text)
        assert "abcdefghijklmnopqrstuvwxyz012345" not in redacted
        assert "sk-secretvalue1234567890" not in redacted
        assert "[REDACTED]" in redacted


# --------------------------------------------------------------------------- helpers


def _dummy_index():
    class _Dummy:
        def __init__(self) -> None:
            self.test_map: dict = {}
            self.modules: dict = {}

    return _Dummy()
