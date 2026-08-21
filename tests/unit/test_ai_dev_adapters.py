"""Focused unit tests for the Wave 2 normalized candidate adapters.

Covers normalization shape, deterministic failure propagation, and objective
scoring (recall/precision + context economy — a candidate that returns almost
nothing can never win). External-tool smokes are guarded by skipif so the suite
stays hermetic.
"""
from __future__ import annotations

from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_adapters  # noqa: E402


def _task(**overrides) -> dict:
    task = {
        "task_id": "t1",
        "class": "localized",
        "base_sha": "a",
        "result_sha": "b",
        "description": "x",
        "terms": ["e10_professional_handoff"],
        "changed_sources": ["src/psyche_os/application/e10_professional_handoff.py"],
        "changed_tests": ["tests/unit/test_e10_professional.py"],
        "changed_other": [],
    }
    task.update(overrides)
    return task


class TestNormalization:
    def test_make_result_shape(self) -> None:
        r = ai_dev_adapters.make_result(
            candidate="c",
            version="1.0",
            task_id="t1",
            files=[{"path": "src/a.py", "score": None, "reason": "x", "relation": "lexical"}],
            symbols=[{"path": "src/a.py", "symbol": "Foo", "range": [1, 10], "kind": "class"}],
            relations=[],
            normalized_context="hello world",
            duration_ms=12.3,
            raw_output_bytes=500,
            index_build_ms=40.0,
            index_size_bytes=1000,
            tool_calls=2,
            cold=True,
            raw_evidence="/tmp/x.txt",
        )
        assert r["candidate"] == "c"
        assert r["metrics"]["selected_files"] == 1
        assert r["metrics"]["selected_ranges"] == 1
        assert r["metrics"]["normalized_output_bytes"] == len(b"hello world")
        assert r["tokens_estimate"] == ai_dev_adapters.estimate_tokens("hello world")

    def test_failure_result_is_normalized(self) -> None:
        r = ai_dev_adapters.failure_result("c", "t1", "boom")
        assert r["status"] == "error"
        assert r["error"] == "boom"
        assert r["files"] == []
        assert r["metrics"]["selected_files"] == 0
        # A failure must never win: empty context AND zero recall.
        assert r["tokens_estimate"] == 1

    def test_failure_result_not_ok(self) -> None:
        r = ai_dev_adapters.failure_result("c", "t1", "boom")
        assert r["status"] != "ok"


class TestScoring:
    def test_full_recall_and_precision(self) -> None:
        task = _task()
        r = ai_dev_adapters.make_result(
            candidate="c", version=None, task_id="t1",
            files=[{"path": "src/psyche_os/application/e10_professional_handoff.py", "score": None, "reason": "x", "relation": None},
                   {"path": "tests/unit/test_e10_professional.py", "score": None, "reason": "x", "relation": None}],
            symbols=[], relations=[], normalized_context="xx", duration_ms=1.0, raw_output_bytes=2,
            index_build_ms=None, index_size_bytes=None, tool_calls=1, cold=False,
        )
        s = ai_dev_adapters.score_task_result(r, task)
        assert s["source_recall"] == 1.0
        assert s["source_precision"] == 0.5  # one of two retrieved files is ground truth
        assert s["test_recall"] == 1.0
        assert s["missed_source"] == []

    def test_empty_retrieval_cannot_win(self) -> None:
        task = _task()
        r = ai_dev_adapters.failure_result("c", "t1", "tool missing")
        s = ai_dev_adapters.score_task_result(r, task)
        assert s["source_recall"] == 0.0
        assert s["source_precision"] == 0.0
        assert s["status"] == "error"

    def test_missed_files_recorded(self) -> None:
        task = _task()
        r = ai_dev_adapters.make_result(
            candidate="c", version=None, task_id="t1",
            files=[{"path": "src/psyche_os/adapters/e10_filesystem.py", "score": None, "reason": "x", "relation": None}],
            symbols=[], relations=[], normalized_context="x", duration_ms=1.0, raw_output_bytes=1,
            index_build_ms=None, index_size_bytes=None, tool_calls=1, cold=False,
        )
        s = ai_dev_adapters.score_task_result(r, task)
        assert s["source_recall"] == 0.0
        assert "src/psyche_os/application/e10_professional_handoff.py" in s["missed_source"]

    def test_no_ground_truth_is_not_a_wall(self) -> None:
        task = _task(changed_sources=[], changed_tests=[])
        r = ai_dev_adapters.make_result(
            candidate="c", version=None, task_id="t1", files=[], symbols=[], relations=[],
            normalized_context="", duration_ms=0.0, raw_output_bytes=0, index_build_ms=None,
            index_size_bytes=None, tool_calls=0, cold=False,
        )
        s = ai_dev_adapters.score_task_result(r, task)
        assert s["source_recall"] is None  # no ground truth -> recall undefined


class TestPathfinderCollect:
    def test_unescapes_backslash_paths(self) -> None:
        # Pathfinder's search response JSON carries escaped backslashes; a
        # regex on raw text would yield double slashes and break scoring.
        text = '{"matches": [{"file": "src\\\\psyche_os\\\\application\\\\e10_professional_handoff.py", "line": 3}]}'
        files: dict = {}
        n = ai_dev_adapters._pf_collect(text, "e10_professional_handoff", files)
        assert n == 1
        assert "src/psyche_os/application/e10_professional_handoff.py" in files

    def test_skips_dotfiles(self) -> None:
        text = '{"matches": [{"file": ".aider.chat.history.md", "line": 1}]}'
        files: dict = {}
        assert ai_dev_adapters._pf_collect(text, "t", files) == 0

    def test_invalid_json_is_zero(self) -> None:
        assert ai_dev_adapters._pf_collect("not json", "t", {}) == 0


class TestRelPath:
    def test_relativize_windows_absolute(self) -> None:
        base = Path("/repo") if sys.platform != "win32" else Path("C:/repo")
        assert ai_dev_adapters.rel_path(r"C:\repo\src\a.py", base) == "src/a.py"

    def test_relativize_repo_relative_unchanged(self) -> None:
        base = Path("C:/repo")
        assert ai_dev_adapters.rel_path("src/a.py", base) == "src/a.py"

    def test_dedupe_files(self, tmp_path: Path) -> None:
        raw = ["C:/repo/src/a.py", "src/a.py", ".ai-dev/x.md", "src/b.py", "src/a.py"]
        out = ai_dev_adapters.dedupe_files(raw, Path("C:/repo"), reason="test")
        assert [f["path"] for f in out] == ["src/a.py", "src/b.py"]
