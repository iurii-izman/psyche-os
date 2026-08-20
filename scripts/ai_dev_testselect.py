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


def parse_reportlog_counts(rl_path: Path, rc: int | None = None) -> dict[str, Any]:
    """Parse a reportlog artifact into counts, COMPLETE failing nodeids, and a
    deterministic pytest status.

    A2: missing, malformed, or incomplete reportlogs are INCOMPLETE — never a
    green and never detection. The failing nodeids come from the parser's
    complete machine-accounting list (``failure_nodeids``), NOT the bounded
    AI-facing presentation, so presentation truncation can never truncate
    detector ground truth (A1).
    """
    base = {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "failing": [], "status": "INCOMPLETE"}
    if not rl_path.is_file():
        return base
    try:
        import ai_dev_reportlog  # type: ignore

        packet = ai_dev_reportlog.parse_reportlog(rl_path, command="pytest")
    except Exception:
        return base
    coll = packet["collection"]
    return {
        "collected": coll["collected"],
        "passed": coll["passed"],
        "failed": coll["failed"],
        "errors": coll["errors"],
        "skipped": coll["skipped"],
        "failing": list(packet.get("failure_nodeids") or []),
        "status": classify_run(packet, rc if rc is not None else packet.get("exit_code")),
    }


def classify_run(packet: dict[str, Any] | None, rc: int | None) -> str:
    """Deterministic pytest-result status semantics (A2).

    Only a trustworthy test failure — a clean SessionFinish, parsed failing node
    identities, pytest rc == 1 — may establish mutation detection. Everything
    else is PASS / INFRA_ERROR / INCOMPLETE / NO_TESTS and must never be treated
    as detection.

      PASS          rc 0, clean session
      TEST_FAILURE  rc 1 with parsed failing nodeids, clean session
      INFRA_ERROR   rc 2/3/4 (interrupted / internal error / usage error) or
                    non-zero rc without trustworthy parsed failures
      NO_TESTS      rc 5 (pytest: no tests collected)
      INCOMPLETE    missing/truncated/malformed reportlog (no trustworthy evidence)
    """
    if packet is None:
        return "INCOMPLETE"
    if packet.get("truncated"):
        return "INCOMPLETE"
    if rc == 0:
        return "PASS"
    if rc == 5:
        return "NO_TESTS"
    if rc in (2, 3, 4):
        return "INFRA_ERROR"
    if rc == 1 and (packet.get("failure_nodeids") or []):
        return "TEST_FAILURE"
    return "INFRA_ERROR"


def _summary(run: dict[str, Any]) -> dict[str, Any]:
    counts = parse_reportlog_counts(Path(run["reportlog"]), rc=run["rc"])
    return {
        "label": run["label"],
        "rc": run["rc"],
        "duration_ms": run["duration_ms"],
        "status": counts["status"],
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
        # 1. Warm testmon collection on the UNMUTATED tree (also proves green
        #    baseline) — only when the external selector is actually available.
        if _selector_available("pytest-testmon"):
            baseline = run_pytest_in(worktree, ["--testmon"], label="testmon-warm")
            if baseline["rc"] != 0:
                raise TestSelectError(f"scenario {scenario_id}: warm testmon baseline is not green (rc={baseline['rc']})")

        # 2. Apply the mutation.
        apply_mutation(scenario, worktree)

        # 3. FULL truth run identifies the detecting tests. FULL is valid for
        #    detection ONLY when it is a trustworthy test failure with complete
        #    parsed detector identities; anything else invalidates the scenario.
        full = selector_full(worktree)
        full_status = full["status"]
        if full_status != "TEST_FAILURE":
            detectors: set[str] = set()
            results: dict[str, Any] = {}
            results["full"] = {
                **full,
                "detected": False,
                "detection_note": (
                    f"FULL status {full_status!r} — not a trustworthy test failure; "
                    "scenario cannot establish detection"
                ),
            }
        else:
            detectors = set(full["failing_nodeids"])
            results = {
                "full": {**full, "detected": True, "detectors": sorted(detectors)},
            }

        # 4. Retained normal selector (always run in a clean canonical env).
        cur = selector_current(worktree, scenario, config)
        cur["detected"] = _detects(cur, detectors) if full_status == "TEST_FAILURE" else None
        results["current"] = cur

        # 5. External LAB selectors — run ONLY when configuration, capability
        #    state, and actual availability agree. Otherwise SKIPPED_UNAVAILABLE
        #    (not ERROR, not PASS, not a false negative).
        for name, kind in (("pytest-testmon", "testmon"), ("pytest-impacted", "impacted")):
            if _selector_available(name):
                if kind == "testmon":
                    sel = selector_testmon(worktree, scenario, warm=True)
                else:
                    sel = selector_impacted(worktree, scenario)
                sel["detected"] = _detects(sel, detectors) if full_status == "TEST_FAILURE" else None
            else:
                sel = _skipped_unavailable(name)
            results[name] = sel
    finally:
        _git_worktree_remove(worktree)

    out = {
        "schema_version": 1,
        "ran_at": _now(),
        "scenario_id": scenario_id,
        "class": scenario["class"],
        "module": scenario["module"],
        "mutation_desc": scenario["mutation"]["desc"],
        "detectors": sorted(detectors) if full_status == "TEST_FAILURE" else [],
        "selector_results": results,
        "detection_recall": {
            "full": full_status == "TEST_FAILURE",
            "current": results["current"].get("detected"),
            "pytest-testmon": results["pytest-testmon"].get("detected"),
            "pytest-impacted": results["pytest-impacted"].get("detected"),
        },
    }
    _write_evidence(scenario_id, "result", out)
    return out


def _detects(selector_summary: dict[str, Any], detectors: set[str]) -> bool:
    """A selector detects the mutation only when:
      1. its execution is valid and trustworthy (TEST_FAILURE), and
      2. its complete failing node set intersects the complete FULL detector set.
    Count-based inference and infra/parser failures never count as detection."""
    if not detectors:
        return False
    if selector_summary.get("status") != "TEST_FAILURE":
        return False
    return bool(set(selector_summary.get("failing_nodeids", [])) & detectors)


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


# --------------------------------------------------------------------------- A1/A2-repaired selector revalidation


def revalidate_retained_selector() -> dict[str, Any]:
    """Repaired revalidation (A1/A2): the five frozen mutation scenarios, FULL
    truth + the retained current selector ONLY. External selectors are never
    invoked here. This is the bounded evidence that decides whether the retained
    selector is trustworthy — NOT a universal proof, just the five probes."""
    rows = []
    for s in list_scenarios():
        print(f"[revalidate] === scenario {s['scenario_id']} ===", flush=True)
        rows.append(run_test_select_scenario(s["scenario_id"]))
    valid = [r for r in rows if r["detection_recall"]["full"] is True]
    detected = [r for r in valid if r["selector_results"]["current"].get("detected") is True]
    if len(valid) != 5:
        result = f"INCONCLUSIVE ({len(valid)}/5 scenarios had a trustworthy FULL test failure)"
    elif len(detected) == 5:
        result = "PASS (5/5 repaired bounded mutation probes detected by the retained current selector)"
    else:
        result = f"FAIL ({len(detected)}/5 detected)"
    out = {
        "schema_version": 1,
        "ran_at": _now(),
        "purpose": "A1/A2-repaired selector revalidation — FULL + retained current selector only (five frozen scenarios)",
        "scenarios": [
            {
                "scenario_id": r["scenario_id"],
                "class": r["class"],
                "module": r["module"],
                "full_status": r["selector_results"]["full"].get("status"),
                "full_valid": r["detection_recall"]["full"] is True,
                "detector_count": len(r["detectors"]),
                "current_status": r["selector_results"]["current"].get("status"),
                "current_selected_tests": r["selector_results"]["current"].get("selected"),
                "current_selected_files": r["selector_results"]["current"].get("selected_files"),
                "current_detected": r["selector_results"]["current"].get("detected"),
            }
            for r in rows
        ],
        "retained_selector_result": result,
    }
    (EVIDENCE_ROOT / "revalidation.json").write_text(json.dumps(out, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return out


# --------------------------------------------------------------------------- helpers


def _load_perf_config() -> dict[str, Any]:
    import ai_dev_perf  # type: ignore

    return ai_dev_perf.load_config()


def _skipped_unavailable(name: str) -> dict[str, Any]:
    return {
        "label": name,
        "rc": None,
        "duration_ms": 0.0,
        "status": "SKIPPED_UNAVAILABLE",
        "selected": 0,
        "failed": 0,
        "errors": 0,
        "failing_nodeids": [],
        "detected": None,
    }


_PLUGIN_MODULES = {"pytest-testmon": "testmon", "pytest-impacted": "pytest_impacted"}


def _plugin_importable(name: str) -> bool:
    import importlib.util

    mod = _PLUGIN_MODULES.get(name)
    if not mod:
        return False
    return importlib.util.find_spec(mod) is not None


def _selector_available(name: str) -> bool:
    """A candidate selector is invocable only when configuration, capability
    state, and actual availability all agree. Unavailable LAB candidates are
    SKIPPED_UNAVAILABLE — never invoked, never ERROR, never a false negative."""
    try:
        import ai_dev_adapters  # type: ignore

        cfg = ai_dev_adapters.load_tournament_config()
        if name not in list(cfg["test_selection"]["candidates"]):
            return False
    except Exception:
        return False
    try:
        import ai_dev_capability  # type: ignore

        rec = ai_dev_capability.load_registry().get(name)
    except Exception:
        return False
    if not rec:
        return False
    allowed, _ = ai_dev_capability.execution_allowed(rec.get("state"), explicit=True)
    if not allowed:
        return False
    if not (rec.get("installed") or rec.get("command")):
        return False
    return _plugin_importable(name)


def _selectors_enabled() -> list[str]:
    """Selectors that may actually run (availability-gated)."""
    out = ["full", "current"]
    for name in ("pytest-testmon", "pytest-impacted"):
        if _selector_available(name):
            out.append(name)
    return out


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
