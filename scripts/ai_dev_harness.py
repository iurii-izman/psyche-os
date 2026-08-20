#!/usr/bin/env python3
"""AI Dev OS v2 — Wave 3 harness tournament runner.

A SMALL orchestration layer for the frozen Wave 3 harness tournament (Claude Code
vs Reasonix vs OpenCode on the same DeepSeek CHEAP model class). It materializes a
disposable worktree at each frozen task's base SHA, pre-installs the test toolchain,
launches one autonomous harness session with the identical Task Contract, overlays
the accepted result-SHA tests, runs the deterministic verification, and records only
truthful observable metrics. Raw transcripts stay under the gitignored runs path;
only compact aggregates are committed.

Commands:
  list                          frozen tasks + contestants
  run --task <id> --harness <h>  run one session (creates+removes worktree)
  run-all                        run the full 6-run core tournament
  report                         rebuild the aggregate harness-comparison.json

Run:  uv run python scripts/ai_dev_harness.py <command> [options]
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any

import yaml

REPO = Path(__file__).resolve().parent.parent
TASKS_FILE = REPO / ".ai-dev" / "performance" / "harness-tasks.yaml"
RUNS_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "runs" / "harness"
EVIDENCE_FILE = REPO / ".ai-dev" / "evidence" / "performance" / "harness-comparison.json"


def _main_repo_root() -> Path:
    """Root of the main repository even when the runner runs inside a worktree."""
    proc = subprocess.run(
        ["git", "rev-parse", "--git-common-dir"], cwd=str(REPO), capture_output=True, text=True, timeout=60
    )
    common = Path((proc.stdout or "").strip())
    if common.is_absolute():
        return common.parent
    return (REPO / common).resolve().parent


MAIN_REPO = _main_repo_root()
WT_PREFIX = MAIN_REPO / ".claude" / "worktrees" / "w3-harness"

SCHEMA_VERSION = 1
# Per-task-class wall-clock budgets for a single harness session (seconds).
TASK_TIMEOUTS = {"A": 50 * 60, "B": 65 * 60}

# DeepSeek V4-Flash off-peak USD-per-1M-token rates (pricing basis 2026-08-17,
# off-peak = all hours outside Beijing 09-12/14-18). Used ONLY to estimate cost
# from real token counts where the harness does not report an effective cost.
DS_MISS_RATE_USD = 0.211  # ~= CNY 1.5 / 7.1
DS_HIT_RATE_USD = 0.007  # ~= CNY 0.05 / 7.1
DS_OUT_RATE_USD = 0.634  # ~= CNY 4.5 / 7.1
DS_PRICING_NOTE = "DeepSeek V4-Flash off-peak rates (2026-08-17 pricing); ESTIMATE"

COMMON_RULES = (
    "- Work autonomously: inspect the relevant source, implement the task, run the targeted\n"
    "  verification, fix your own immediate defects, then stop.\n"
    "- The repository is a synthetic-fixture research prototype. Never add real personal data.\n"
    "- Do not modify tests, configuration, or verification to make things pass. Do not weaken\n"
    "  any check.\n"
    "- Do not touch: CONSTITUTION.md, desktop/, .ai-dev/, .claude/, migrations (unless the task\n"
    "  explicitly requires it), or crypto/storage code outside the files listed in Scope.\n"
    "- Do not commit. Leave your changes in the working tree.\n"
    "- When you believe the task is complete and verified, print a concise summary (files\n"
    "  changed, verification result) and stop.\n"
)


class HarnessError(Exception):
    pass


def now_iso() -> str:
    return _dt.datetime.now(_dt.UTC).isoformat()


def load_tasks() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(TASKS_FILE.read_text(encoding="utf-8")) or {}
    return {t["task_id"]: t for t in data.get("tasks", [])}


def load_contestants() -> dict[str, dict[str, Any]]:
    data = yaml.safe_load(TASKS_FILE.read_text(encoding="utf-8")) or {}
    return data.get("contestants", {})


# --------------------------------------------------------------------------- prompt


def render_prompt(task: dict[str, Any]) -> str:
    verify_cmd = "uv run pytest " + " ".join(task["verification_tests"]) + " -q"
    lines = [
        "# Task Contract — autonomous implementation task",
        "",
        "You are an autonomous coding agent working in a disposable worktree checked out at the",
        "base commit of an accepted real task. Implement the task below and verify it.",
        "",
        COMMON_RULES.rstrip(),
        "",
        "## Task",
        "",
        task["contract"].strip(),
        "",
        "## Scope",
        "",
        f"- Expected implementation files: {', '.join(task['expected_implementation_files'])}",
        "- Limit your changes to those files unless a defect forces otherwise.",
        "",
        "## Verification",
        "",
        f"- `{verify_cmd}`",
        "- The test suite is the authority for correctness; keep existing behavior elsewhere",
        "  intact (no regressions).",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- worktree


def tree_path(task_id: str, harness: str) -> Path:
    return WT_PREFIX / f"{task_id}-{harness}"


def create_worktree(task_id: str, harness: str, base_sha: str) -> Path:
    dest = tree_path(task_id, harness)
    subprocess.run(["git", "worktree", "remove", "--force", str(dest)], capture_output=True, check=False)
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        ["git", "worktree", "add", "--detach", str(dest), base_sha],
        capture_output=True,
        text=True,
        timeout=180,
    )
    if proc.returncode != 0:
        raise HarnessError(f"worktree add failed: {proc.stderr[:400]}")
    return dest


def remove_worktree(tree: Path) -> None:
    subprocess.run(["git", "worktree", "remove", "--force", str(tree)], capture_output=True, check=False)
    if tree.exists():
        shutil.rmtree(tree, ignore_errors=True)


def setup_tree(tree: Path) -> dict[str, Any]:
    """Install the test toolchain (infrastructure, timed separately from the session)."""
    t0 = time.perf_counter()
    proc = subprocess.run(
        ["uv", "sync", "--extra", "dev"],
        cwd=str(tree),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=900,
    )
    ms = round((time.perf_counter() - t0) * 1000.0, 1)
    ok = proc.returncode == 0
    return {"ok": ok, "setup_ms": ms, "rc": proc.returncode, "tail": (proc.stderr or proc.stdout)[-400:]}


# --------------------------------------------------------------------------- harness launch


# npm-global CLI binaries. The bash shims cannot be executed by Windows
# CreateProcess, so each harness is resolved to its real native entry point.
NPM_ROOT = Path(os.path.expanduser("~/AppData/Roaming/npm"))


def _harness_bin(harness: str) -> list[str]:
    if harness == "claude-code":
        p = NPM_ROOT / "node_modules/@anthropic-ai/claude-code/bin/claude.exe"
        if not p.is_file():
            raise HarnessError(f"claude-code binary not found: {p}")
        return [str(p)]
    if harness == "reasonix":
        hits = sorted((NPM_ROOT / "node_modules/reasonix/node_modules").glob("@reasonix/cli-*/bin/reasonix.exe"))
        if not hits:
            raise HarnessError("reasonix binary not found")
        return [str(hits[0])]
    if harness == "opencode":
        p = NPM_ROOT / "node_modules/opencode-ai/bin/opencode.exe"
        if not p.is_file():
            raise HarnessError(f"opencode binary not found: {p}")
        return [str(p)]
    if harness == "codex":
        p = NPM_ROOT / "node_modules/@openai/codex/bin/codex.js"
        if not p.is_file():
            raise HarnessError(f"codex launcher not found: {p}")
        return ["node", str(p)]
    raise HarnessError(f"unknown harness {harness}")


def _env_for(harness: str) -> dict[str, str]:
    env = dict(os.environ)
    if harness == "claude-code":
        env["ANTHROPIC_BASE_URL"] = "https://api.deepseek.com/anthropic"
        env["ANTHROPIC_AUTH_TOKEN"] = os.environ.get("DEEPSEEK_API_KEY", "")
        env["ANTHROPIC_MODEL"] = "deepseek-v4-flash"
        env["ANTHROPIC_API_KEY"] = ""
        env["CLAUDE_CODE_HOST_AUTH_ENV_VAR"] = "ANTHROPIC_AUTH_TOKEN"
        env["CLAUDE_CODE_DISABLE_UNKNOWN_MODEL_WINDOW_ENFORCEMENT"] = "1"
    return env


def run_harness(
    harness: str, tree: Path, prompt: str, run_dir: Path, timeout: int
) -> dict[str, Any]:
    env = _env_for(harness)
    stdout_path = run_dir / "session.stdout"
    stderr_path = run_dir / "session.stderr"
    bin_cmd = _harness_bin(harness)

    if harness == "claude-code":
        cmd = [
            *bin_cmd, "-p", prompt, "--model", "deepseek-v4-flash",
            "--dangerously-skip-permissions", "--output-format", "json",
        ]
    elif harness == "reasonix":
        cmd = [
            *bin_cmd, "run", "--dir", str(tree), "--model", "deepseek-flash",
            "--permission-mode", "bypassPermissions",
            "--metrics", str(run_dir / "metrics.json"),
            "--events-jsonl", prompt,
        ]
    elif harness == "opencode":
        cmd = [
            *bin_cmd, "run", "--dir", str(tree), "--model", "deepseek/deepseek-v4-flash",
            "--format", "json", "--auto", prompt,
        ]
    elif harness == "codex":
        cmd = [
            *bin_cmd, "exec", "--json", "-C", str(tree),
            "-m", "gpt-5.5", "--dangerously-bypass-approvals-and-sandbox", prompt,
        ]
    else:
        raise HarnessError(f"unknown harness {harness}")

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(tree),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - timeout path
        proc = exc
        timed_out = True
        # TimeoutExpired carries partial output only if we used communicate; capture nothing extra.
    wall_ms = round((time.perf_counter() - t0) * 1000.0, 1)

    if timed_out:
        return {
            "started": True,
            "timed_out": True,
            "rc": None,
            "wall_ms": wall_ms,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }

    stdout_path.write_text(proc.stdout or "", encoding="utf-8", errors="replace")
    stderr_path.write_text(proc.stderr or "", encoding="utf-8", errors="replace")
    return {
        "started": True,
        "timed_out": False,
        "rc": proc.returncode,
        "wall_ms": wall_ms,
        "stdout_bytes": len((proc.stdout or "").encode("utf-8", errors="replace")),
        "stderr_bytes": len((proc.stderr or "").encode("utf-8", errors="replace")),
        "stdout_path": str(stdout_path),
        "stderr_path": str(stderr_path),
    }


# --------------------------------------------------------------------------- evaluation


def overlay_result_tests(task: dict[str, Any], tree: Path) -> None:
    result_sha = task["result_sha"]
    for rel in task["verification_tests"]:
        proc = subprocess.run(
            ["git", "show", f"{result_sha}:{rel}"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        if proc.returncode != 0:
            raise HarnessError(f"cannot read result test {rel}: {proc.stderr[:200]}")
        dest = tree / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(proc.stdout, encoding="utf-8")


def run_verification(task: dict[str, Any], tree: Path, run_dir: Path) -> dict[str, Any]:
    cmd = ["uv", "run", "pytest", *task["verification_tests"], "-q", "--no-header", "-p", "no:cacheprovider"]
    t0 = time.perf_counter()
    proc = subprocess.run(
        cmd, cwd=str(tree), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900
    )
    dur_ms = round((time.perf_counter() - t0) * 1000.0, 1)
    out = proc.stdout or ""
    (run_dir / "verification.out").write_text(out, encoding="utf-8")
    if proc.stderr:
        (run_dir / "verification.err").write_text(proc.stderr, encoding="utf-8")
    passed = _first_int(out, r"(\d+) passed")
    failed = _first_int(out, r"(\d+) failed")
    errors = _first_int(out, r"(\d+) error")
    skipped = _first_int(out, r"(\d+) skipped")
    collected = _first_int(out, r"collected (\d+) items")
    if collected == 0:
        # --no-header suppresses the collection line; sum of outcomes is the count.
        collected = passed + failed + errors + skipped
    status = "PASS" if (proc.returncode == 0 and errors == 0 and failed == 0) else "FAIL"
    if proc.returncode != 0 and failed == 0 and errors == 0 and "INTERRUPTED" in out.upper():
        status = "UNKNOWN"
    return {
        "status": status,
        "rc": proc.returncode,
        "collected": collected,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "skipped": skipped,
        "duration_ms": dur_ms,
        "summary": _bounded(out, 2400),
    }


def _first_int(text: str, pattern: str) -> int:
    import re

    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


def _bounded(text: str, limit: int) -> str:
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit // 2] + f"\n...[truncated {len(text) - limit}]...\n" + text[-limit // 2 :]


def git_diff_scope(tree: Path) -> dict[str, Any]:
    proc = subprocess.run(
        ["git", "diff", "--name-only"], cwd=str(tree), capture_output=True, text=True, timeout=120
    )
    names = [ln.strip().replace("\\", "/") for ln in (proc.stdout or "").splitlines() if ln.strip()]
    untracked = subprocess.run(
        ["git", "status", "--porcelain"], cwd=str(tree), capture_output=True, text=True, timeout=120
    )
    for ln in (untracked.stdout or "").splitlines():
        if ln.startswith("??"):
            names.append(ln[3:].strip().replace("\\", "/"))
    stat = subprocess.run(
        ["git", "diff", "--stat"], cwd=str(tree), capture_output=True, text=True, timeout=120
    )
    return {"changed_files": sorted(names), "diff_stat": (stat.stdout or "").strip()}


# --------------------------------------------------------------------------- metrics


def extract_metrics(
    task: dict[str, Any], harness: str, run_dir: Path, session: dict[str, Any]
) -> dict[str, Any]:
    base: dict[str, Any] = {
        "task_id": task["task_id"],
        "harness": harness,
        "requested_model": _requested_model(harness),
        "configured_model": _configured_model(harness),
        "effective_model": None,
    }
    if harness == "claude-code":
        base.update(_claude_metrics(run_dir, session))
    elif harness == "reasonix":
        base.update(_reasonix_metrics(run_dir))
    elif harness == "opencode":
        base.update(_opencode_metrics(run_dir, session))
    elif harness == "codex":
        base.update(_codex_metrics(run_dir))
    return base


def _requested_model(harness: str) -> str:
    return {
        "claude-code": "deepseek-v4-flash",
        "reasonix": "deepseek-flash (default) -> deepseek-v4-flash",
        "opencode": "deepseek/deepseek-v4-flash",
        "codex": "gpt-5.5 (STRONG reference; not same-model)",
    }[harness]


def _configured_model(harness: str) -> str:
    return {
        "claude-code": "deepseek-v4-flash (ANTHROPIC_BASE_URL=api.deepseek.com/anthropic)",
        "reasonix": "deepseek-v4-flash (provider deepseek-flash preset)",
        "opencode": "deepseek-v4-flash (built-in deepseek provider)",
        "codex": "codex exec -m gpt-5.5 (ChatGPT auth; STRONG reference, not same-model)",
    }[harness]


def _claude_metrics(run_dir: Path, session: dict[str, Any]) -> dict[str, Any]:
    # Prefer the --output-format json result object (aggregate, real tokens).
    agg: dict[str, Any] = {}
    stdout_path = run_dir / "session.stdout"
    result_obj: dict[str, Any] | None = None
    if stdout_path.is_file():
        try:
            result_obj = json.loads(stdout_path.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            result_obj = None
    if isinstance(result_obj, dict):
        usage = result_obj.get("usage") or {}
        agg = {
            "input_tokens": usage.get("input_tokens"),
            "cache_read_tokens": usage.get("cache_read_input_tokens"),
            "cache_creation_tokens": usage.get("cache_creation_input_tokens"),
            "output_tokens": usage.get("output_tokens"),
            "model_turns": result_obj.get("num_turns"),
            "reported_cost_usd": result_obj.get("total_cost_usd"),
            "reported_cost_basis": "claude-code total_cost_usd (Anthropic default pricing — NOT the effective DeepSeek cost)",
            "effective_model": ((result_obj.get("modelUsage") or {}).get("deepseek-v4-flash") or {}).get("canonicalModel"),
            "session_id": result_obj.get("session_id"),
        }
    # Cross-check / fill from the session transcript when the JSON lacks fields.
    transcript = _find_transcript(session)
    if transcript:
        usage = _sum_transcript_usage(transcript)
        if agg.get("input_tokens") is None and usage:
            agg.update(usage)
        if agg.get("effective_model") is None:
            agg["effective_model"] = _transcript_model(transcript)
        agg["transcript_path"] = str(transcript)
        agg["transcript_messages"] = usage.get("messages") if usage else None
    agg["cost_estimate_usd"] = _deepseek_cost_estimate(agg)
    agg["cost_estimate_note"] = DS_PRICING_NOTE
    return agg


def _find_transcript(session: dict[str, Any]) -> Path | None:
    start = session.get("started_at_epoch") or 0
    projects = Path(os.path.expanduser("~/.claude/projects"))
    hits: list[Path] = []
    for path in projects.glob("*/**/*.jsonl"):
        try:
            if path.stat().st_mtime >= start - 30:
                hits.append(path)
        except OSError:
            continue
    if not hits:
        return None
    return max(hits, key=lambda p: p.stat().st_mtime)


def _sum_transcript_usage(path: Path) -> dict[str, Any]:
    inp = out = cache_r = cache_c = 0
    turns = 0
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") != "assistant":
            continue
        usage = (obj.get("message") or {}).get("usage")
        if not isinstance(usage, dict):
            continue
        inp += usage.get("input_tokens") or 0
        out += usage.get("output_tokens") or 0
        cache_r += usage.get("cache_read_input_tokens") or 0
        cache_c += usage.get("cache_creation_input_tokens") or 0
        turns += 1
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": cache_r,
        "cache_creation_tokens": cache_c,
        "model_turns": turns,
        "messages": turns,
    }


def _transcript_model(path: Path) -> str | None:
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        model = (obj.get("message") or {}).get("model")
        if model:
            return model
    return None


def _deepseek_cost_estimate(m: dict[str, Any]) -> float | None:
    if m.get("input_tokens") is None or m.get("output_tokens") is None:
        return None
    inp = int(m["input_tokens"])
    cache_r = int(m.get("cache_read_tokens") or 0)
    uncached = max(0, inp - cache_r)
    out = int(m["output_tokens"])
    return round(
        (uncached * DS_MISS_RATE_USD + cache_r * DS_HIT_RATE_USD + out * DS_OUT_RATE_USD) / 1_000_000, 6
    )


def _reasonix_metrics(run_dir: Path) -> dict[str, Any]:
    path = run_dir / "metrics.json"
    try:
        m = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"metrics_unavailable": True}
    out = {
        "input_tokens": m.get("prompt_tokens"),
        "output_tokens": m.get("completion_tokens"),
        "cache_read_tokens": m.get("cache_hit_tokens"),
        "cache_miss_tokens": m.get("cache_miss_tokens"),
        "model_turns": None,
        "steps": m.get("steps"),
        "tool_calls": m.get("tool_calls"),
        "reported_cost_usd": m.get("cost"),
        "reported_cost_currency": m.get("currency"),
        "reported_cost_basis": "reasonix --metrics from DeepSeek official pricing table",
        "rate_band": (m.get("cost_quotes") or [{}])[0].get("rateBand") if m.get("cost_quotes") else None,
        "effective_model": (m.get("cost_quotes") or [{}])[0].get("modelRef") if m.get("cost_quotes") else None,
        "cost_complete": m.get("cost_complete"),
        "estimated": m.get("estimated"),
        "num_turns": m.get("steps"),
        "duration_ms": m.get("duration_ms"),
        "outcome": m.get("outcome"),
        "retries": m.get("retries"),
        "compactions": m.get("compactions"),
    }
    out["cache_creation_tokens"] = None  # reasonix reports hit/miss only
    out["cost_estimate_usd"] = m.get("cost")
    out["cost_estimate_note"] = "reasonix reported cost (official DeepSeek pricing table, off-peak)"
    return out


def _opencode_metrics(run_dir: Path, session: dict[str, Any]) -> dict[str, Any]:
    stdout_path = run_dir / "session.stdout"
    if not stdout_path.is_file():
        return {"metrics_unavailable": True}
    tot = {"input": 0, "output": 0, "reasoning": 0, "cache_read": 0, "cache_write": 0, "total": 0}
    cost = 0.0
    steps = 0
    effective = None
    for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        if obj.get("type") != "step_finish":
            continue
        part = obj.get("part") or {}
        tok = part.get("tokens") or {}
        tot["input"] += tok.get("input") or 0
        tot["output"] += tok.get("output") or 0
        tot["reasoning"] += tok.get("reasoning") or 0
        tot["cache_read"] += (tok.get("cache") or {}).get("read") or 0
        tot["cache_write"] += (tok.get("cache") or {}).get("write") or 0
        tot["total"] += tok.get("total") or 0
        cost += part.get("cost") or 0.0
        steps += 1
        if part.get("model"):
            effective = part["model"]
    return {
        "input_tokens": tot["input"] or None,
        "output_tokens": tot["output"] or None,
        "cache_read_tokens": tot["cache_read"] or None,
        "cache_creation_tokens": tot["cache_write"] or None,
        "model_turns": steps,
        "steps": steps,
        "reported_cost_usd": round(cost, 8) if steps else None,
        "reported_cost_basis": "opencode step_finish cost (provider pricing)",
        "effective_model": effective,
        "tool_calls": None,
        "cost_estimate_usd": round(cost, 8) if steps else None,
        "cost_estimate_note": "opencode reported cost (provider pricing)",
    }


def _codex_metrics(run_dir: Path) -> dict[str, Any]:
    stdout_path = run_dir / "session.stdout"
    if not stdout_path.is_file():
        return {"metrics_unavailable": True}
    usage: dict[str, Any] = {}
    turns = 0
    model = None
    for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except Exception:
            continue
        t = obj.get("type")
        if t in ("agent_message", "turn.completed"):
            turns += 1
        u = obj.get("usage")
        if isinstance(u, dict) and u:
            usage = u
        if isinstance(obj.get("model"), str):
            model = obj["model"]
    inp = usage.get("input_tokens") or usage.get("prompt_tokens") or usage.get("input")
    out = usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("output")
    cache_r = (
        usage.get("cache_read_input_tokens")
        or usage.get("cache_hit_tokens")
        or usage.get("cached_input_tokens")
        or usage.get("cache_read")
    )
    return {
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read_tokens": cache_r,
        "cache_creation_tokens": usage.get("cache_creation_input_tokens") or usage.get("cache_write"),
        "cache_miss_tokens": usage.get("cache_miss_tokens") or usage.get("cache_miss"),
        "reasoning_output_tokens": usage.get("reasoning_output_tokens"),
        "model_turns": turns or None,
        "steps": turns or None,
        "tool_calls": None,
        "reported_cost_usd": usage.get("total_cost_usd") or usage.get("cost"),
        "reported_cost_basis": "codex --json usage event (provider pricing; NOT DeepSeek)",
        "effective_model": model,
        "cost_estimate_usd": usage.get("total_cost_usd") or usage.get("cost"),
        "cost_estimate_note": "codex reported usage (different provider economics)",
    }


# --------------------------------------------------------------------------- run


def run_one(task_id: str, harness: str) -> dict[str, Any]:
    tasks = load_tasks()
    task = tasks.get(task_id)
    if not task:
        raise HarnessError(f"unknown task {task_id}")
    contestants = load_contestants()
    is_reference = harness == "codex"  # STRONG reference: not a same-model contestant
    if not is_reference and harness not in contestants:
        raise HarnessError(f"unknown harness {harness}")
    version = "0.130.0 (STRONG reference)" if is_reference else contestants[harness]["version"]
    run_dir = RUNS_ROOT / task_id / harness
    run_dir.mkdir(parents=True, exist_ok=True)

    base_sha = task["base_sha"]
    started_at = now_iso()
    started_epoch = time.time()
    session: dict[str, Any] = {"started_at": started_at, "started_at_epoch": started_epoch}

    record: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "task_id": task_id,
        "task_class": task["task_class"],
        "harness": harness,
        "harness_version": version,
        "is_reference": harness == "codex",
        "base_sha": base_sha,
        "result_sha": task["result_sha"],
        "started_at": started_at,
        "finished_at": None,
        "setup": None,
        "session": session,
        "evaluation": None,
        "metrics": None,
        "infra_retry": False,
        "human_correction": False,
        "errors": [],
    }

    try:
        tree = create_worktree(task_id, harness, base_sha)
        record["worktree"] = str(tree)
        try:
            record["setup"] = setup_tree(tree)
            if not record["setup"]["ok"]:
                raise HarnessError("uv sync --extra dev failed")
            prompt = render_prompt(task)
            (run_dir / "prompt.md").write_text(prompt, encoding="utf-8")
            timeout = TASK_TIMEOUTS[task["task_class"]]
            s = run_harness(harness, tree, prompt, run_dir, timeout)
            session.update(s)
            if not s["timed_out"] and s["rc"] is not None and s["rc"] != 0:
                record["errors"].append(f"harness exit code {s['rc']}")
            record["evaluation"] = _evaluate(task, tree, run_dir)
            record["metrics"] = extract_metrics(task, harness, run_dir, session)
        finally:
            remove_worktree(tree)
    except HarnessError as exc:
        record["errors"].append(str(exc))
    except Exception as exc:  # never lose a session record to an unexpected error
        record["errors"].append(f"{type(exc).__name__}: {exc}")
    record["finished_at"] = now_iso()

    out_path = run_dir / "run.json"
    out_path.write_text(json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return record


def _evaluate(task: dict[str, Any], tree: Path, run_dir: Path) -> dict[str, Any]:
    # Scope must be captured BEFORE the result tests are overlaid, or the
    # overlay would be misread as the harness's own edits.
    scope = git_diff_scope(tree)
    diff = subprocess.run(
        ["git", "diff"], cwd=str(tree), capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120
    )
    if diff.stdout:
        (run_dir / "harness.diff").write_text(diff.stdout, encoding="utf-8")
    overlay_result_tests(task, tree)
    verification = run_verification(task, tree, run_dir)
    expected = set(task["expected_implementation_files"])
    changed = set(scope["changed_files"]) - set(task["verification_tests"])
    unexpected = sorted(changed - expected)
    expected_missing = sorted(expected - changed)
    return {
        "verification": verification,
        "scope": scope,
        "unexpected_files": unexpected,
        "expected_files_missing": expected_missing,
        "acceptance": verification["status"],
        "human_correction_required": False,
    }


# --------------------------------------------------------------------------- report


def load_run_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(RUNS_ROOT.glob("*/**/run.json")):
        try:
            records.append(json.loads(path.read_text(encoding="utf-8")))
        except Exception:
            continue
    return records


def build_comparison() -> dict[str, Any]:
    tasks = load_tasks()
    contestants = load_contestants()
    records = load_run_records()
    rows = []
    for r in sorted(records, key=lambda x: (x["task_id"], x["harness"])):
        eval_ = r.get("evaluation") or {}
        verify = eval_.get("verification") or {}
        metrics = r.get("metrics") or {}
        rows.append(
            {
                "task_id": r["task_id"],
                "task_class": r.get("task_class"),
                "harness": r["harness"],
                "harness_version": r.get("harness_version"),
                "requested_model": metrics.get("requested_model"),
                "configured_model": metrics.get("configured_model"),
                "effective_model": metrics.get("effective_model"),
                "acceptance": eval_.get("acceptance"),
                "verification": {
                    k: verify.get(k)
                    for k in ("status", "rc", "collected", "passed", "failed", "errors", "duration_ms")
                },
                "unexpected_files": eval_.get("unexpected_files"),
                "expected_files_missing": eval_.get("expected_files_missing"),
                "human_correction_required": eval_.get("human_correction_required"),
                "wall_ms": (r.get("session") or {}).get("wall_ms"),
                "timed_out": (r.get("session") or {}).get("timed_out"),
                "rc": (r.get("session") or {}).get("rc"),
                "setup_ms": (r.get("setup") or {}).get("setup_ms"),
                "model_turns": metrics.get("model_turns"),
                "steps": metrics.get("steps"),
                "tool_calls": metrics.get("tool_calls"),
                "input_tokens": metrics.get("input_tokens"),
                "output_tokens": metrics.get("output_tokens"),
                "cache_read_tokens": metrics.get("cache_read_tokens"),
                "cache_creation_tokens": metrics.get("cache_creation_tokens"),
                "cache_miss_tokens": metrics.get("cache_miss_tokens"),
                "reported_cost_usd": metrics.get("reported_cost_usd"),
                "reported_cost_basis": metrics.get("reported_cost_basis"),
                "cost_estimate_usd": metrics.get("cost_estimate_usd"),
                "cost_estimate_note": metrics.get("cost_estimate_note"),
                "errors": r.get("errors"),
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "ran_at": now_iso(),
        "freeze_date": yaml.safe_load(TASKS_FILE.read_text(encoding="utf-8")).get("freeze_date"),
        "pricing_note": DS_PRICING_NOTE,
        "tasks": list(tasks.keys()),
        "contestants": contestants,
        "rows": rows,
    }


def write_comparison() -> dict[str, Any]:
    comp = build_comparison()
    EVIDENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    EVIDENCE_FILE.write_text(json.dumps(comp, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    return comp


# --------------------------------------------------------------------------- CLI


def cmd_list(_args: argparse.Namespace) -> int:
    tasks = load_tasks()
    contestants = load_contestants()
    print("frozen tasks:")
    for tid, t in tasks.items():
        print(f"  {tid}  class={t['task_class']}  base={t['base_sha'][:12]}  result={t['result_sha'][:12]}")
        print(f"    verification: {' '.join(t['verification_tests'])}")
    print("contestants:")
    for name, c in contestants.items():
        print(f"  {name}  v{c['version']}  model={c['model']}  provider={c['provider']}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    record = run_one(args.task, args.harness)
    print(json.dumps(_compact(record), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def _compact(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_id": record["task_id"],
        "harness": record["harness"],
        "acceptance": (record.get("evaluation") or {}).get("acceptance"),
        "wall_ms": (record.get("session") or {}).get("wall_ms"),
        "rc": (record.get("session") or {}).get("rc"),
        "errors": record.get("errors"),
    }


def cmd_run_all(_args: argparse.Namespace) -> int:
    tasks = load_tasks()
    order = [
        (tid, h)
        for h in ("claude-code", "reasonix", "opencode")
        for tid in tasks
    ]
    for i, (tid, h) in enumerate(order, 1):
        print(f"[{i}/{len(order)}] running {h} on {tid} ...", flush=True)
        record = run_one(tid, h)
        c = _compact(record)
        print(f"  -> acceptance={c['acceptance']} wall={c['wall_ms']}ms rc={c['rc']} errors={c['errors']}", flush=True)
    comp = write_comparison()
    print(f"wrote {EVIDENCE_FILE} ({len(comp['rows'])} rows)")
    return 0


def cmd_report(_args: argparse.Namespace) -> int:
    comp = write_comparison()
    print(json.dumps(comp, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ai_dev_harness", description="AI Dev OS v2 Wave 3 harness tournament runner")
    ap.add_argument("--version", action="store_true")
    sub = ap.add_subparsers(dest="command")

    p_list = sub.add_parser("list")
    p_list.set_defaults(fn=cmd_list)

    p_run = sub.add_parser("run")
    p_run.add_argument("--task", required=True)
    p_run.add_argument("--harness", required=True)
    p_run.set_defaults(fn=cmd_run)

    p_all = sub.add_parser("run-all")
    p_all.set_defaults(fn=cmd_run_all)

    p_rep = sub.add_parser("report")
    p_rep.set_defaults(fn=cmd_report)

    args = ap.parse_args(argv)
    if args.version:
        print(f"ai_dev_harness {SCHEMA_VERSION}.0")
        return 0
    if not args.command:
        ap.print_help()
        return 1
    return int(args.fn(args))


if __name__ == "__main__":
    try:
        rc = main()
    except HarnessError as exc:
        print(f"error: {exc}", file=sys.stderr)
        rc = 1
    except KeyboardInterrupt:
        sys.exit(130)
    if rc:
        sys.exit(rc)
