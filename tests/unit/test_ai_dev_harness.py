"""Focused unit tests for the Wave 3 harness-tournament runner.

Covers the deterministic accounting/parsing helpers and prompt rendering only;
real harness sessions are the tournament runs themselves (raw logs stay under
the gitignored runs path).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_harness  # noqa: E402
from ai_dev_harness import (  # noqa: E402
    _bounded,
    _codex_metrics,
    _deepseek_cost_estimate,
    _first_int,
    _opencode_metrics,
    _reasonix_metrics,
    render_prompt,
)


def test_first_int_parses_counters() -> None:
    assert _first_int("8 failed, 30 passed in 1.94s", r"(\d+) passed") == 30
    assert _first_int("no numbers here", r"(\d+) failed") == 0
    assert _first_int("collected 38 items", r"collected (\d+) items") == 38


def test_bounded_truncates_and_marks() -> None:
    short = _bounded("hello", 100)
    assert short == "hello"
    long = _bounded("x" * 50, 20)
    assert len(long) < 50 and "truncated" in long


def test_render_prompt_embeds_contract_and_verification(tmp_path: Path) -> None:
    task = {
        "contract": "Implement the thing.",
        "expected_implementation_files": ["src/psyche_os/a.py"],
        "verification_tests": ["tests/unit/test_a.py"],
        "base_sha": "abc123",
    }
    prompt = render_prompt(task)
    assert "Implement the thing." in prompt
    assert "uv run pytest tests/unit/test_a.py -q" in prompt
    assert "src/psyche_os/a.py" in prompt
    assert "Do not commit" in prompt


def test_deepseek_cost_estimate_matches_offpeak_rates() -> None:
    # 1M uncached input @ 0.211 + 1M cached @ 0.007 + 1M output @ 0.634
    m = {"input_tokens": 2_000_000, "cache_read_tokens": 1_000_000, "output_tokens": 1_000_000}
    est = _deepseek_cost_estimate(m)
    assert est is not None and abs(est - 0.852) < 0.001
    assert _deepseek_cost_estimate({"input_tokens": None, "output_tokens": 1}) is None


def test_reasonix_metrics_parses_summary(tmp_path: Path) -> None:
    metrics = {
        "prompt_tokens": 1000,
        "completion_tokens": 50,
        "cache_hit_tokens": 900,
        "cache_miss_tokens": 100,
        "steps": 3,
        "tool_calls": 2,
        "cost": 0.001,
        "currency": "USD",
        "cost_quotes": [{"modelRef": "deepseek-flash/deepseek-v4-flash", "rateBand": "off_peak"}],
    }
    p = tmp_path / "metrics.json"
    p.write_text(json.dumps(metrics), encoding="utf-8")
    out = _reasonix_metrics(tmp_path)
    assert out["input_tokens"] == 1000
    assert out["cache_read_tokens"] == 900
    assert out["effective_model"] == "deepseek-flash/deepseek-v4-flash"
    assert out["rate_band"] == "off_peak"


def test_opencode_metrics_sums_step_tokens(tmp_path: Path) -> None:
    stream = (
        '{"type":"step_finish","part":{"tokens":{"input":10,"output":2,"reasoning":0,'
        '"cache":{"read":100,"write":0},"total":112},"cost":0.001}}\n'
        '{"type":"step_finish","part":{"tokens":{"input":5,"output":1,"reasoning":0,'
        '"cache":{"read":50,"write":0},"total":56},"cost":0.0005}}\n'
    )
    p = tmp_path / "session.stdout"
    p.write_text(stream, encoding="utf-8")
    out = _opencode_metrics(tmp_path, {})
    assert out["input_tokens"] == 15
    assert out["output_tokens"] == 3
    assert out["cache_read_tokens"] == 150
    assert out["model_turns"] == 2
    assert abs(out["reported_cost_usd"] - 0.0015) < 1e-9


def test_codex_metrics_reads_turn_completed_usage(tmp_path: Path) -> None:
    stream = (
        '{"type":"turn.started"}\n'
        '{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":80,'
        '"output_tokens":10,"reasoning_output_tokens":3}}\n'
    )
    p = tmp_path / "session.stdout"
    p.write_text(stream, encoding="utf-8")
    out = _codex_metrics(tmp_path)
    assert out["input_tokens"] == 100
    assert out["cache_read_tokens"] == 80
    assert out["output_tokens"] == 10
    assert out["reasoning_output_tokens"] == 3
    assert out["model_turns"] == 1


def test_harness_bin_resolves_real_entries() -> None:
    # These resolve from the npm-global root; on machines without the tools the
    # assertion would fail, so only assert the three entries return non-empty lists.
    for name in ("claude-code", "reasonix", "opencode", "codex"):
        cmd = ai_dev_harness._harness_bin(name)
        assert isinstance(cmd, list) and cmd
