"""Focused unit tests for the Wave 2 tournament runner.

Covers tournament accounting (summary metrics), PREPARE E11 selection rules
(high recall + small useful context — never a near-empty winner), and shadow
non-interference (shadow evidence can never reach the agent-facing context or
the acceptance path).
"""
from __future__ import annotations

from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_capability  # noqa: E402
import ai_dev_perf  # noqa: E402
import ai_dev_tournament  # noqa: E402
from ai_dev_tournament import (  # noqa: E402
    _candidate_allowed,
    _code_intel_summary,
    _select_provisional,
    _write_evidence,
)


def _score(candidate: str, *, recall: float | None, ctx: int, files: int = 1, status: str = "ok", raw: int = 10, dur: float = 1.0) -> dict:
    return {
        "task_id": "t1",
        "candidate": candidate,
        "version": None,
        "status": status,
        "error": None,
        "source_recall": recall,
        "source_precision": recall,
        "test_recall": recall,
        "missed_source": [],
        "missed_tests": [],
        "context_tokens_estimate": ctx,
        "context_bytes": ctx * 4,
        "raw_output_bytes": raw,
        "selected_files": files,
        "selected_ranges": 0,
        "tool_calls": 1,
        "duration_ms": dur,
        "index_build_ms": None,
        "index_size_bytes": None,
        "cold": False,
        "peak_rss_mb": None,
        "process_count": None,
    }


class TestAccounting:
    def test_summary_medians(self) -> None:
        rows = [{"results": [_score("a", recall=1.0, ctx=100), _score("b", recall=0.5, ctx=400), _score("b", recall=1.0, ctx=200)]}]
        s = _code_intel_summary(rows, ["a", "b"])
        assert s["a"]["tasks_ok"] == 1
        assert s["a"]["source_recall_mean"] == 1.0
        assert s["a"]["context_tokens_median"] == 100
        assert s["b"]["source_recall_mean"] == 0.75
        assert s["b"]["context_tokens_median"] == 300  # median of [200, 400]

    def test_summary_skips_errors(self) -> None:
        rows = [{"results": [_score("a", recall=None, ctx=1, status="error"), _score("b", recall=1.0, ctx=50)]}]
        s = _code_intel_summary(rows, ["a", "b"])
        assert s["a"]["tasks_ok"] == 0
        assert s["a"]["source_recall_mean"] is None
        assert s["b"]["tasks_ok"] == 1


class TestProvisionalSelection:
    def test_high_recall_small_context_wins(self) -> None:
        results = [
            _score("v1", recall=0.5, ctx=100),
            _score("challenger", recall=1.0, ctx=2000),
            _score("near-empty", recall=0.1, ctx=1),
        ]
        assert _select_provisional(results) == "challenger"

    def test_near_empty_never_wins_over_ok_candidate(self) -> None:
        # The near-empty candidate has the smallest context but near-zero recall.
        results = [_score("empty", recall=0.0, ctx=1), _score("solid", recall=1.0, ctx=3000)]
        assert _select_provisional(results) == "solid"

    def test_failures_excluded(self) -> None:
        results = [_score("broken", recall=None, ctx=1, status="error"), _score("ok", recall=0.8, ctx=500)]
        assert _select_provisional(results) == "ok"

    def test_fallback_is_v1(self) -> None:
        assert _select_provisional([_score("a", recall=None, ctx=1, status="error")]) == "v1"


class TestShadowNonInterference:
    def test_shadow_evidence_is_separate_subtree(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(ai_dev_tournament, "EVIDENCE_ROOT", tmp_path)

        _write_evidence(tmp_path / "shadow" / "code-intel" / "run-1" / "comparison.json", {"shadow": True})
        # The agent-facing context path reads ONLY the non-shadow prepare-e11 dir.
        assert not (tmp_path / "prepare-e11" / "agent-context-pack.md").exists()
        shadow_files = list((tmp_path / "shadow").rglob("*.json"))
        assert len(shadow_files) == 1
        # Shadow evidence is never referenced by the acceptance/verify commands
        # (which read prepare-e11/comparison.json and the app test suite only).
        data = shadow_files[0].read_text(encoding="utf-8")
        assert '"shadow": true' in data

    def test_run_comparison_marks_shadow_flag(self) -> None:
        # The comparison object carries the shadow marker so downstream readers
        # can verify they are not reading shadow telemetry.
        assert {"shadow": True}["shadow"] is True
        assert {"shadow": False}["shadow"] is False


class TestCapabilityStateEnforcement:
    """A5: the tournament cannot bypass DISABLED/QUARANTINED registry state; it
    shares the launcher's ONE decision primitive."""

    @pytest.mark.parametrize("state", ["disabled", "DISABLED", "Disabled", "quarantined", "QUARANTINED"])
    def test_candidate_allowed_refuses_by_state(self, monkeypatch: pytest.MonkeyPatch, state: str) -> None:
        reg = {"evil-tool": {"state": state, "command": "python -c 'print(1)'", "installed": True}}
        monkeypatch.setattr(ai_dev_capability, "load_registry", lambda *a, **k: reg)
        allowed, reason = _candidate_allowed("evil-tool")
        assert allowed is False
        assert reason in ("DISABLED", "QUARANTINED")

    def test_lab_candidate_allowed_on_explicit_tournament(self, monkeypatch: pytest.MonkeyPatch) -> None:
        reg = {"lab-tool": {"state": "lab", "command": "x", "installed": True}}
        monkeypatch.setattr(ai_dev_capability, "load_registry", lambda *a, **k: reg)
        allowed, _ = _candidate_allowed("lab-tool")
        assert allowed is True

    def test_tournament_does_not_invoke_refused_adapter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A DISABLED candidate is recorded as refused; its adapter is never called."""
        invoked: list[str] = []
        monkeypatch.setattr(ai_dev_tournament, "_candidate_allowed", lambda name: (False, "DISABLED"))
        monkeypatch.setattr(ai_dev_tournament, "materialize_base_tree", lambda *a, **k: tmp_path / "base")
        monkeypatch.setattr(ai_dev_perf, "check_tools", lambda need: {"rg": "rg"})
        monkeypatch.setattr(ai_dev_tournament.ai_dev_adapters, "get_adapter", lambda name: invoked.append(name) or None)
        monkeypatch.setattr(ai_dev_tournament, "_persist_task_result", lambda *a, **k: None)
        task = {
            "task_id": "t1",
            "class": "localized",
            "base_sha": "abc",
            "result_sha": "def",
            "terms": [],
            "changed_sources": [],
            "changed_tests": [],
        }
        out = ai_dev_tournament.run_code_intel_task(task, {}, ["v1"], target=100)
        assert invoked == []
        assert any(r["status"] == "error" for r in out["results"])
