"""Focused unit tests for the Wave 3 harness-tournament runner.

Covers the deterministic accounting/parsing helpers and prompt rendering only;
real harness sessions are the tournament runs themselves (raw logs stay under
the gitignored runs path).
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_harness  # noqa: E402
from ai_dev_harness import (  # noqa: E402
    _bounded,
    _codex_metrics,
    _deepseek_cost_estimate,
    _env_for,
    _first_int,
    _opencode_metrics,
    _reasonix_metrics,
    _run_exit_code,
    overall_status,
    render_prompt,
    run_harness,
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


def test_harness_bin_resolves_optional_installed_entries() -> None:
    # Harness CLIs are optional developer-global tools, not repository dependencies.
    # When installed, their native entry points must resolve to a runnable command.
    for name in ("claude-code", "reasonix", "opencode", "codex"):
        try:
            cmd = ai_dev_harness._harness_bin(name)
        except ai_dev_harness.HarnessError:
            continue
        assert isinstance(cmd, list) and cmd


def test_harness_bin_fails_closed_when_optional_installation_is_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ai_dev_harness, "NPM_ROOT", tmp_path)

    for name in ("claude-code", "reasonix", "opencode", "codex"):
        with pytest.raises(ai_dev_harness.HarnessError):
            ai_dev_harness._harness_bin(name)


# --------------------------------------------------------------------------- A7 minimal harness environment


class TestMinimalHarnessEnv:
    def test_unrelated_parent_secret_not_inherited(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("UNRELATED_CLOUD_SECRET", "must-not-leak")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "synthetic-aws-secret")
        monkeypatch.setenv("OPENAI_API_KEY", "synthetic-openai-key")
        for harness in ("claude-code", "reasonix", "opencode", "codex"):
            env = _env_for(harness)
            assert "UNRELATED_CLOUD_SECRET" not in env
            assert "AWS_SECRET_ACCESS_KEY" not in env
            assert "OPENAI_API_KEY" not in env

    def test_claude_code_provider_auth_wired_without_printing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-synthetic-not-real-1234567890")
        env = _env_for("claude-code")
        assert env.get("ANTHROPIC_BASE_URL") == "https://api.deepseek.com/anthropic"
        assert env.get("ANTHROPIC_AUTH_TOKEN") == "sk-synthetic-not-real-1234567890"
        assert env.get("ANTHROPIC_MODEL") == "deepseek-v4-flash"

    def test_opencode_receives_only_deepseek_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-synthetic-not-real-1234567890")
        env = _env_for("opencode")
        assert env.get("DEEPSEEK_API_KEY") == "sk-synthetic-not-real-1234567890"
        assert "ANTHROPIC_AUTH_TOKEN" not in env

    def test_codex_gets_no_cloud_keys(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPENAI_API_KEY", "sk-synthetic-not-real-1234567890")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-synthetic-anthropic-not-real")
        env = _env_for("codex")
        assert "OPENAI_API_KEY" not in env
        assert "ANTHROPIC_API_KEY" not in env

    def test_reasonix_passes_no_credential_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-synthetic-not-real-1234567890")
        env = _env_for("reasonix")
        assert "DEEPSEEK_API_KEY" not in env


# --------------------------------------------------------------------------- A3 fail-closed overall status


class TestOverallStatusFailClosed:
    def test_timeout_can_never_be_pass(self) -> None:
        rec = {
            "session": {"timed_out": True, "rc": None},
            "setup": {"ok": True},
            "evaluation": {"acceptance": "PASS"},
            "errors": [],
        }
        assert overall_status(rec) == "TIMEOUT"

    def test_nonzero_harness_rc_can_never_be_pass(self) -> None:
        rec = {
            "session": {"timed_out": False, "rc": 2},
            "setup": {"ok": True},
            "evaluation": {"acceptance": "PASS"},
            "errors": ["harness exit code 2"],
        }
        assert overall_status(rec) == "HARNESS_FAILURE"

    def test_setup_failure_is_infra_failure(self) -> None:
        rec = {
            "session": {"timed_out": False, "rc": 0},
            "setup": {"ok": False, "rc": 1},
            "evaluation": {"acceptance": "PASS"},
            "errors": [],
        }
        assert overall_status(rec) == "INFRA_FAILURE"

    def test_recorded_error_is_infra_failure(self) -> None:
        rec = {
            "session": {"timed_out": False, "rc": 0},
            "setup": {"ok": True},
            "evaluation": {"acceptance": "PASS"},
            "errors": ["unexpected: boom"],
        }
        assert overall_status(rec) == "INFRA_FAILURE"

    def test_clean_pass_is_pass_and_clean_fail_is_fail(self) -> None:
        ok = {"session": {"timed_out": False, "rc": 0}, "setup": {"ok": True}, "evaluation": {"acceptance": "PASS"}, "errors": []}
        assert overall_status(ok) == "PASS"
        bad = {**ok, "evaluation": {"acceptance": "FAIL"}}
        assert overall_status(bad) == "FAIL"

    def test_single_run_cli_exit_only_zero_on_pass(self) -> None:
        assert _run_exit_code({"status": "PASS"}) == 0
        assert _run_exit_code({"status": "TIMEOUT"}) == 1
        assert _run_exit_code({"status": "HARNESS_FAILURE"}) == 1
        assert _run_exit_code({"status": "FAIL"}) == 1
        assert _run_exit_code({"status": "INFRA_FAILURE"}) == 1


class TestTimeoutProcessTreeCleanup:
    def test_timeout_kills_descendants_and_survivors(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """A synthetic sleeper parent + child prove bounded tree termination:
        timed out -> TIMEOUT session, cleanup outcome recorded, no survivor."""
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        parent_script = (
            "import subprocess, sys, time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])\n"
            "time.sleep(60)\n"
        )
        marker = "import time; time.sleep(30)"
        monkeypatch.setattr(ai_dev_harness, "_harness_bin", lambda harness: [sys.executable, "-c", parent_script])

        tree = tmp_path / "tree"
        tree.mkdir()
        run_dir = tmp_path / "run"
        run_dir.mkdir()

        session = run_harness("claude-code", tree, "prompt", run_dir, timeout=2)
        assert session["timed_out"] is True
        assert session["rc"] is None
        assert session["cleanup"]["remaining"] == 0

        import psutil

        survivors = []
        for p in psutil.process_iter(["pid", "cmdline"]):
            try:
                cmdline = p.info.get("cmdline") or []
            except (psutil.AccessDenied, psutil.NoSuchProcess):
                continue
            if marker in " ".join(cmdline):
                survivors.append(p.info)
        assert survivors == [], f"leaked processes: {survivors}"
