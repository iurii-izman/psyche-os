#!/usr/bin/env python3
"""AI Dev OS v2 — Acceleration Wave 2B: test-selection tournament.

FULL pytest remains truth/control; a selected-test system NEVER redefines
acceptance. Each scenario is a small deterministic behavior-breaking mutation
applied to a DISPOSABLE git worktree (mutated application code is never
committed). We measure which selectors would have caught the mutation:

    MUTATION DETECTION RECALL = did the selected set include a detecting test?

Selectors:
  full            FULL pytest control (truth)
  current         existing PR11 source->test selector (index test map)
  pytest-testmon  dependency-based selection (warm after collection)
  pytest-impacted static impacted selection (cold)

Evidence lands under `.ai-dev/evidence/performance/tournament/test-select/`;
probes are disposable worktrees under runs/tournament/probes/ (gitignored).
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any

REPO = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "tournament" / "test-select"
PROBES_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "runs" / "tournament" / "probes"
VENV_PY = REPO / ".venv" / "Scripts" / "python.exe"
SCENARIOS_FILE = REPO / ".ai-dev" / "performance" / "test-scenarios.yaml"

import yaml  # noqa: E402


class TestSelectError(Exception):
    pass


# --------------------------------------------------------------------------- scenarios


def list_scenarios() -> list[dict[str, Any]]:
    if not SCENARIOS_FILE.is_file():
        raise TestSelectError(f"no scenario definitions at {SCENARIOS_FILE}")
    data = yaml.safe_load(SCENARIOS_FILE.read_text(encoding="utf-8")) or {}
    scenarios = data.get("scenarios") or []
    return scenarios


def apply_mutation(scenario: dict[str, Any], worktree: Path) -> None:
    """Apply the scenario's deterministic mutation to the worktree module.

    The edit must be unique in the module (verified by apply; fails loudly if
    the old_string is not found exactly once). Mutated application code is
    NEVER committed.
    """
    old = scenario["mutation"]["old"]
    new = scenario["mutation"]["new"]
    module_path = worktree / scenario["module"]
    text = module_path.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise TestSelectError(
            f"scenario {scenario['scenario_id']}: mutation old_string found {count} times (expected 1) in {scenario['module']}"
        )
    module_path.write_text(text.replace(old, new), encoding="utf-8")


# --------------------------------------------------------------------------- pytest runner


def run_pytest_in(worktree: Path, args: list[str], *, label: str, timeout: int = 600) -> dict[str, Any]:
    """Run pytest in a worktree using the shared dev venv + worktree src shadow.

    PYTHONPATH points at the worktree's src so the mutation is what tests see
    (the venv's editable install is overridden — PYTHONPATH precedes site .pth).
    """
    rl = worktree / f".reportlog-{label}.jsonl"
    cmd = [
        str(VENV_PY),
        "-m",
        "pytest",
        *args,
        "-q",
        "--tb=short",
        "--no-header",
        "--report-log",
        str(rl),
    ]
    env = dict(os.environ)
    env["PYTHONPATH"] = str(worktree / "src")
    env.pop("PYTEST_DISABLE_PLUGIN_AUTOLOAD", None)
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(worktree), env=env, timeout=timeout)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    raw = worktree / f".raw-{label}.txt"
    raw.write_text(proc.stdout, encoding="utf-8", errors="replace")
    return {
        "label": label,
        "rc": proc.returncode,
        "duration_ms": round(duration_ms, 1),
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "reportlog": str(rl),
        "raw": str(raw),
    }


def parse_reportlog_counts(rl_path: Path) -> dict[str, Any]:
    """Parse the deterministic reportlog artifact into counts + failing nodeids."""
    collected = passed = failed = errors = skipped = 0
    failing: list[str] = []
    if not rl_path.is_file():
        return {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "failing": []}
    try:
        import ai_dev_reportlog  # type: ignore

        packet = ai_dev_reportlog.parse_reportlog(rl_path, command="pytest")
        coll = packet["collection"]
        collected, passed, failed, errors, skipped = (
            coll["collected"], coll["passed"], coll["failed"], coll["errors"], coll["skipped"],
        )
        for f in packet.get("failures", []) or []:
            failing.append(f.get("nodeid", "?"))
    except Exception:
        return {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "failing": []}
    return {"collected": collected, "passed": passed, "failed": failed, "errors": errors, "skipped": skipped, "failing": failing}


def _summary(run: dict[str, Any]) -> dict[str, Any]:
    counts = parse_reportlog_counts(Path(run["reportlog"]))
    return {
        "label": run["label"],
        "rc": run["rc"],
        "duration_ms": run["duration_ms"],
        "selected": counts["collected"],
        "failed": counts["failed"],
        "errors": counts["errors"],
        "failing_nodeids": counts["failing"],
    }


# --------------------------------------------------------------------------- selectors


def selector_full(worktree: Path) -> dict[str, Any]:
    return _summary(run_pytest_in(worktree, [], label="full"))


def selector_current(worktree: Path, scenario: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Existing PR11 selector: index reverse-dep closure -> mapped test files."""
    import ai_dev_perf  # type: ignore

    index = ai_dev_perf.build_index(config, repo=worktree)
    surface = ai_dev_perf.affected_surface(index, [scenario["module"]])
    tests = ai_dev_perf.select_test_paths(index, surface["affected_modules"])
    run = run_pytest_in(worktree, tests, label="current") if tests else {
        "label": "current", "rc": None, "duration_ms": 0.0, "reportlog": "", "stdout": "", "stderr": "", "raw": "",
    }
    summary = _summary(run)
    summary["selected_files"] = len(tests)
    summary["selected_module"] = scenario["module"]
    return summary


def selector_testmon(worktree: Path, scenario: dict[str, Any], *, warm: bool) -> dict[str, Any]:
    """pytest-testmon: dependency-based selection (warm = collection already done)."""
    args = ["--testmon"] if warm else ["--testmon", "--testmon-forcerun"]
    run = run_pytest_in(worktree, args, label="testmon")
    summary = _summary(run)
    summary["warm"] = warm
    return summary


def selector_impacted(worktree: Path, scenario: dict[str, Any]) -> dict[str, Any]:
    """pytest-impacted: static impacted selection from a module directory.

    The plugin's --impacted-module expects a package DIRECTORY path (it maps the
    name to a dir under cwd); our src layout means this may degrade to the full
    suite — that behavior is measured honestly.
    """
    module_dir = str(Path(scenario["module"]).parent).replace("\\", "/")
    run = run_pytest_in(worktree, ["--impacted", f"--impacted-module={module_dir}", "--impacted-tests-dir=tests"], label="impacted")
    summary = _summary(run)
    return summary


# --------------------------------------------------------------------------- scenario run


def _write_evidence(scenario_id: str, name: str, data: Any) -> None:
    d = EVIDENCE_ROOT / scenario_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def run_test_select_scenario(scenario_id: str) -> dict[str, Any]:
    scenario = next((s for s in list_scenarios() if s["scenario_id"] == scenario_id), None)
    if not scenario:
        raise TestSelectError(f"unknown scenario: {scenario_id}")
    config = _load_perf_config()

    worktree = PROBES_ROOT / scenario_id
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)
    worktree.parent.mkdir(parents=True, exist_ok=True)
    _git_worktree_add(worktree)
    print(f"[test-select] scenario {scenario_id} ({scenario['class']}) — probe worktree ready", flush=True)
    try:
        # 1. Warm testmon collection on the UNMUTATED tree (also proves green baseline).
        if "pytest-testmon" in _selectors_enabled():
            baseline = run_pytest_in(worktree, ["--testmon"], label="testmon-warm")
            if baseline["rc"] != 0:
                raise TestSelectError(f"scenario {scenario_id}: warm testmon baseline is not green (rc={baseline['rc']})")

        # 2. Apply the mutation.
        apply_mutation(scenario, worktree)

        # 3. FULL truth run identifies the detecting tests.
        full = selector_full(worktree)
        detectors = set(full["failing_nodeids"])

        # 4. Each selector.
        results: dict[str, Any] = {}
        if full["rc"] == 0:
            results["full"] = {**full, "detected": False, "detection_note": "mutation not caught by any test (scenario invalid)"}
        else:
            results["full"] = {**full, "detected": True, "detectors": sorted(detectors)}

        cur = selector_current(worktree, scenario, config)
        cur["detected"] = _detects(cur, detectors)
        results["current"] = cur

        imp = selector_impacted(worktree, scenario)
        imp["detected"] = _detects(imp, detectors)
        results["pytest-impacted"] = imp

        tm = selector_testmon(worktree, scenario, warm=True)
        tm["detected"] = _detects(tm, detectors)
        results["pytest-testmon"] = tm
    finally:
        _git_worktree_remove(worktree)

    out = {
        "schema_version": 1,
        "ran_at": _now(),
        "scenario_id": scenario_id,
        "class": scenario["class"],
        "module": scenario["module"],
        "mutation_desc": scenario["mutation"]["desc"],
        "detectors": sorted(detectors),
        "selector_results": results,
        "detection_recall": {
            "full": True,
            "current": results["current"]["detected"],
            "pytest-testmon": results["pytest-testmon"]["detected"],
            "pytest-impacted": results["pytest-impacted"]["detected"],
        },
    }
    _write_evidence(scenario_id, "result", out)
    return out


def _detects(selector_summary: dict[str, Any], detectors: set[str]) -> bool:
    """A selector detected the mutation if its run failed on a detector nodeid."""
    if not detectors:
        return False
    if selector_summary.get("rc") != 0:
        return bool(set(selector_summary.get("failing_nodeids", [])) & detectors)
    return False


def run_test_select_all() -> dict[str, Any]:
    scenarios = list_scenarios()
    rows = []
    for s in scenarios:
        print(f"[test-select] === scenario {s['scenario_id']} ===", flush=True)
        rows.append(run_test_select_scenario(s["scenario_id"]))
    out = {
        "schema_version": 1,
        "ran_at": _now(),
        "scenarios": rows,
        "summary": {
            r["scenario_id"]: {
                "class": r["class"],
                "module": r["module"],
                "detectors": len(r["detectors"]),
                "detection_recall": r["detection_recall"],
            }
            for r in rows
        },
    }
    (EVIDENCE_ROOT / "comparison.json").parent.mkdir(parents=True, exist_ok=True)
    (EVIDENCE_ROOT / "comparison.json").write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- helpers


def _load_perf_config() -> dict[str, Any]:
    import ai_dev_perf  # type: ignore

    return ai_dev_perf.load_config()


def _selectors_enabled() -> list[str]:
    try:
        import ai_dev_adapters  # type: ignore

        cfg = ai_dev_adapters.load_tournament_config()
        return [c for c in cfg["test_selection"]["candidates"] if c != "full"] + ["full"]
    except Exception:
        return ["full", "current", "pytest-testmon", "pytest-impacted"]


def _git_worktree_add(worktree: Path) -> None:
    proc = subprocess.run(
        ["git", "worktree", "add", "--detach", str(worktree), "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace", cwd=str(REPO), timeout=120,
    )
    if proc.returncode != 0:
        raise TestSelectError(f"git worktree add failed: {proc.stderr[:300]}")


def _git_worktree_remove(worktree: Path) -> None:
    subprocess.run(["git", "worktree", "remove", "--force", str(worktree)], capture_output=True, text=True, cwd=str(REPO), timeout=120)


def _now() -> str:
    import datetime

    return datetime.datetime.now(datetime.UTC).isoformat()


def _require_venv() -> None:
    if not VENV_PY.is_file():
        raise TestSelectError(f"dev venv python not found: {VENV_PY}")
