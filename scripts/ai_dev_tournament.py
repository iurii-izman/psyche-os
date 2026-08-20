#!/usr/bin/env python3
"""AI Dev OS v2 — Acceleration Wave 2: intelligence tournament runner.

A SMALL orchestration layer around the existing JIT capability launcher and the
frozen benchmark tasks. It calls a candidate, captures runtime/output, normalizes
only comparable fields, scores objective metrics, retains raw evidence, and
produces compact comparisons. It does NOT decide repository authority — the
developer (and future real epics) do.

Commands:
  list                           tournament candidates + registry state
  code-intel --task <id>         run all candidates on one frozen historical task
  code-intel --all-tasks         run the full historical code-intelligence tournament
  code-intel --prepare-e11       PREPARE E11 code-intel tournament (read-only)
  test-select --scenario <id>    run one test-selection mutation scenario
  test-select --all              run all mutation scenarios (builds probes, runs selectors)

Run:  uv run python scripts/ai_dev_tournament.py <command> [options]
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time
from typing import Any

import yaml

try:
    import ai_dev_adapters  # type: ignore

    _HAS_ADAPTERS = True
except Exception:  # pragma: no cover
    ai_dev_adapters = None  # type: ignore[assignment]
    _HAS_ADAPTERS = False

try:
    import ai_dev_perf  # type: ignore

    _HAS_PERF = True
except Exception:  # pragma: no cover
    ai_dev_perf = None  # type: ignore[assignment]
    _HAS_PERF = False

try:
    import ai_dev_capability  # type: ignore

    _HAS_CAP = True
except Exception:  # pragma: no cover
    ai_dev_capability = None  # type: ignore[assignment]
    _HAS_CAP = False

REPO = Path(__file__).resolve().parent.parent
EVIDENCE_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "tournament"
RUNS_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "runs" / "tournament"
TREES_ROOT = RUNS_ROOT / "trees"
PROBES_ROOT = RUNS_ROOT / "probes"
CONFIG = REPO / ".ai-dev" / "performance" / "tournament.yaml"

SCHEMA_VERSION = 1

# Default candidate order for the code-intelligence tournament (controls first).
DEFAULT_CODE_INTEL = ["v1", "v2", "code-review-graph", "codebase-memory", "pathfinder", "aider-repo-map", "symlens"]


class TournamentError(Exception):
    pass


def _now() -> str:
    import datetime

    return datetime.datetime.now(datetime.UTC).isoformat()


def load_tasks() -> list[dict[str, Any]]:
    if not _HAS_PERF:
        raise TournamentError("ai_dev_perf unavailable")
    return ai_dev_perf.load_bench_tasks()


def materialize_base_tree(task: dict[str, Any], *, fresh: bool = False) -> Path:
    if not _HAS_PERF:
        raise TournamentError("ai_dev_perf unavailable")
    dest = TREES_ROOT / task["task_id"]
    if fresh or not (dest / "src").is_dir():
        shutil.rmtree(dest, ignore_errors=True)
        dest.mkdir(parents=True, exist_ok=True)
        ai_dev_perf.materialize_tree(task["base_sha"], dest)
    return dest


def build_index_for(base_repo: Path, config: dict[str, Any]) -> Any:
    if not _HAS_PERF:
        raise TournamentError("ai_dev_perf unavailable")
    index, _ = ai_dev_perf.get_index(config, use_cache=False, repo=base_repo)
    return index


def _candidate_allowed(name: str) -> tuple[bool, str]:
    """Capability-state gate for tournament candidates, sharing the launcher's
    ONE decision primitive (ai_dev_capability.execution_allowed). DISABLED /
    QUARANTINED cannot be bypassed by the tournament; LAB runs here because a
    tournament invocation is explicit."""
    if not _HAS_CAP:
        return False, "capability_module_unavailable"
    try:
        rec = ai_dev_capability.load_registry().get(name)
    except Exception:
        return False, "registry_unreadable"
    if not rec:
        return False, "not_registered"
    return ai_dev_capability.execution_allowed(rec.get("state"), explicit=True)


# --------------------------------------------------------------------------- code-intel tournament


def run_code_intel_task(
    task: dict[str, Any],
    config: dict[str, Any],
    candidates: list[str],
    *,
    target: int,
    fresh_trees: bool = False,
) -> dict[str, Any]:
    """Run every candidate on one frozen historical task; return the comparison.

    Each candidate gets a PRISTINE copy of the materialized base tree so tools
    that write artifacts (aider .aider*, crg .code-review-graph, pathfinder
    .pathfinder) can never contaminate a later candidate's retrieval.
    """
    tools = ai_dev_perf.check_tools(["rg"]) if _HAS_PERF else {}
    base_repo = materialize_base_tree(task, fresh=fresh_trees)

    results: list[dict[str, Any]] = []
    workdirs: list[Path] = []
    try:
        for name in candidates:
            allowed, reason = _candidate_allowed(name)
            if not allowed:
                refused = ai_dev_adapters.failure_result(name, task["task_id"], f"refused by capability state: {reason}")
                score = ai_dev_adapters.score_task_result(refused, task)
                _persist_task_result(task["task_id"], name, refused, score)
                results.append(score)
                continue
            adapter = ai_dev_adapters.get_adapter(name)
            if adapter is None:
                continue
            workdir = _candidate_workdir(base_repo, name)
            workdirs.append(workdir)
            index = build_index_for(workdir, config) if name == "v2" else None
            try:
                if name == "v2":
                    result = adapter(task, workdir, config, tools, target, index)
                else:
                    result = adapter(task, workdir, config, tools, target)
            except Exception as exc:  # a candidate failure never fails the tournament
                result = ai_dev_adapters.failure_result(name, task["task_id"], f"unhandled adapter error: {exc}")
            score = ai_dev_adapters.score_task_result(result, task)
            _persist_task_result(task["task_id"], name, result, score)
            results.append(score)
    finally:
        for d in workdirs:
            _force_rmtree(d)
    return {
        "schema_version": SCHEMA_VERSION,
        "ran_at": _now(),
        "task_id": task["task_id"],
        "class": task["class"],
        "token_target": target,
        "base_sha": task["base_sha"],
        "result_sha": task["result_sha"],
        "results": results,
    }


def _candidate_workdir(base_repo: Path, candidate: str) -> Path:
    """A fresh per-candidate copy of the pristine base tree (small, fast).

    Copies are git-initialized: code-review-graph and aider repo-map detect the
    repository root via git; the .git metadata is inert for v1/v2/rg retrieval.
    """
    dest = base_repo.parent / f"{base_repo.name}-{candidate}"
    _force_rmtree(dest)
    shutil.copytree(base_repo, dest, ignore=shutil.ignore_patterns(".git", ".aider*", ".pathfinder", ".code-review-graph", "__pycache__"))
    subprocess.run(["git", "init", "-q"], cwd=str(dest), check=True, capture_output=True)
    return dest


def _force_rmtree(path: Path) -> None:
    """Remove a tree on Windows even when git-init left read-only object files."""

    def _onerror(func: Any, p: Any, exc_info: Any) -> None:
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            pass

    if not path.exists():
        return
    shutil.rmtree(path, onerror=_onerror)


def _persist_task_result(task_id: str, candidate: str, result: dict[str, Any], score: dict[str, Any]) -> None:
    d = EVIDENCE_ROOT / "code-intel" / task_id
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{candidate}.json").write_text(
        json.dumps({"result": result, "score": score}, ensure_ascii=False, sort_keys=True), encoding="utf-8"
    )


def _write_evidence(rel_path: Path, data: Any) -> None:
    rel_path.parent.mkdir(parents=True, exist_ok=True)
    rel_path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def run_code_intel_tournament(
    tasks: list[dict[str, Any]], config: dict[str, Any], candidates: list[str], *, target: int, fresh_trees: bool = False, shadow: bool = False
) -> dict[str, Any]:
    rows = []
    for task in tasks:
        print(f"[tournament] task {task['task_id']} ({task['class']}) ...", flush=True)
        rows.append(run_code_intel_task(task, config, candidates, target=target, fresh_trees=fresh_trees))
    comparison = {
        "schema_version": SCHEMA_VERSION,
        "ran_at": _now(),
        "candidates": candidates,
        "token_target": target,
        "shadow": shadow,
        "tasks": rows,
        "summary": _code_intel_summary(rows, candidates),
    }
    if shadow:
        # Shadow evidence is telemetry-only: it lives in its own subtree and is
        # never read by the agent-facing context path or any acceptance check.
        target_dir = EVIDENCE_ROOT / "shadow" / "code-intel" / f"run-{int(time.time())}"
    else:
        target_dir = EVIDENCE_ROOT / "code-intel"
    _write_evidence(target_dir / "comparison.json", comparison)
    return comparison


def _code_intel_summary(rows: list[dict[str, Any]], candidates: list[str]) -> dict[str, Any]:
    import statistics

    per_candidate: dict[str, dict[str, Any]] = {c: {"tasks": 0, "recalls": [], "context_tokens": [], "durations": []} for c in candidates}
    for row in rows:
        for r in row["results"]:
            c = per_candidate.get(r["candidate"])
            if c is None:
                continue
            if r["status"] != "ok":
                continue
            c["tasks"] += 1
            if r["source_recall"] is not None:
                c["recalls"].append(r["source_recall"])
            c["context_tokens"].append(r["context_tokens_estimate"])
            c["durations"].append(r["duration_ms"])
    out: dict[str, Any] = {}
    for name, c in per_candidate.items():
        rec = c["recalls"]
        ctx = c["context_tokens"]
        out[name] = {
            "tasks_ok": c["tasks"],
            "source_recall_mean": round(sum(rec) / len(rec), 3) if rec else None,
            "context_tokens_median": round(statistics.median(ctx)) if ctx else None,
            "context_tokens_total": sum(ctx) if ctx else None,
            "duration_ms_mean": round(sum(c["durations"]) / len(c["durations"]), 1) if c["durations"] else None,
        }
    return out


# --------------------------------------------------------------------------- PREPARE E11


def run_prepare_e11(config: dict[str, Any], candidates: list[str], *, target: int, chosen: str | None = None) -> dict[str, Any]:
    """PREPARE E11 code-intel tournament on the CURRENT tree (read-only).

    TWO outputs: comparison evidence (every candidate) and ONE agent-facing
    context pack (the chosen candidate only). No context soup.
    """
    from ai_dev_perf import E11_TERMS  # type: ignore

    tools = ai_dev_perf.check_tools(["rg"])
    task = {"task_id": "prepare-e11", "terms": E11_TERMS, "changed_sources": [], "changed_tests": []}
    index = build_index_for(REPO, config) if "v2" in candidates else None

    results: list[dict[str, Any]] = []
    for name in candidates:
        allowed, reason = _candidate_allowed(name)
        if not allowed:
            refused = ai_dev_adapters.failure_result(name, "prepare-e11", f"refused by capability state: {reason}")
            score = ai_dev_adapters.score_task_result(refused, {"task_id": "prepare-e11"})
            results.append(score)
            _persist_task_result("prepare-e11", name, refused, score)
            continue
        adapter = ai_dev_adapters.get_adapter(name)
        if adapter is None:
            continue
        try:
            if name == "v2":
                result = adapter(task, REPO, config, tools, target, index)
            else:
                result = adapter(task, REPO, config, tools, target)
        except Exception as exc:
            result = ai_dev_adapters.failure_result(name, "prepare-e11", f"unhandled adapter error: {exc}")
        score = ai_dev_adapters.score_task_result(result, task)
        results.append(score)
        _persist_task_result("prepare-e11", name, result, score)

    files_by_candidate = {r["candidate"]: [f["path"] for f in _files_for(r)] for r in results}
    chosen = chosen or _select_provisional(results, terms=E11_TERMS, files_by_candidate=files_by_candidate)
    chosen_score = next((r for r in results if r["candidate"] == chosen), None)
    pack = _render_context_pack(task, chosen, chosen_score, results)
    pack_path = EVIDENCE_ROOT / "prepare-e11" / "agent-context-pack.md"
    pack_path.parent.mkdir(parents=True, exist_ok=True)
    pack_path.write_text(pack, encoding="utf-8")

    comparison = {
        "schema_version": SCHEMA_VERSION,
        "ran_at": _now(),
        "e11_not_implemented": True,
        "real_data_gate": _real_data_gate_status(),
        "candidates": candidates,
        "chosen_candidate": chosen,
        "selection_reason": _selection_reason(chosen_score, results),
        "results": results,
        "agent_context_pack": str(pack_path),
        "pack_tokens_estimate": ai_dev_adapters.estimate_tokens(pack),
    }
    _write_evidence(EVIDENCE_ROOT / "prepare-e11" / "comparison.json", comparison)
    _cleanup_tool_artifacts()
    return comparison


def _cleanup_tool_artifacts() -> None:
    """Remove per-run tool artifacts from the current tree (resource governor).

    External tools may write local caches/indexes into the repo root during a
    run on the CURRENT tree; they are removed after the experiment. Indexes on
    disk are otherwise allowed; these are run-local scratch, not retained.
    """
    for name in (".code-review-graph", ".pathfinder"):
        d = REPO / name
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
    for p in REPO.glob(".aider*"):
        if p.is_file() or p.is_dir():
            with contextlib.suppress(OSError):
                p.unlink() if p.is_file() else shutil.rmtree(p, ignore_errors=True)


def _real_data_gate_status() -> str:
    p = REPO / "docs" / "architecture" / "REAL_DATA_GATE.yaml"
    try:
        data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        return str(data.get("status") or "CLOSED").upper()
    except Exception:
        return "CLOSED"


def _select_provisional(results: list[dict[str, Any]], *, terms: list[str] | None = None, files_by_candidate: dict[str, list[str]] | None = None) -> str:
    """Provisional selection: HIGH RECALL with SMALL USEFUL CONTEXT.

    Score = coverage*1000 + verification_value - context economy. A candidate
    is penalized proportionally to its missed coverage, so returning almost
    nothing can NEVER win. For PREPARE E11 (no ground truth) coverage is the
    fraction of E11 terms that appear in the candidate's selected files, and a
    matched TEST file adds verification value (E11 planning needs tests).
    """
    files_by_candidate = files_by_candidate or {}
    best = None
    best_score = -float("inf")
    for r in results:
        if r["status"] != "ok":
            continue
        if terms:
            selected = files_by_candidate.get(r["candidate"], [])
            matched = {t for t in terms if _term_matches_files(t, selected)}
            coverage = len(matched) / len(terms) if terms else 0.0
            matched_tests = sum(1 for f in selected if f.startswith("tests/") and any(_term_matches_files(t, [f]) for t in terms))
            s = coverage * 1000.0 + matched_tests * 10.0 - max(1, r["context_tokens_estimate"]) * 0.05
        else:
            recall = r["source_recall"] or 0.0
            ctx = max(1, r["context_tokens_estimate"])
            s = recall * 1000.0 - ctx * (1.0 - recall)
        if s > best_score:
            best_score = s
            best = r["candidate"]
    return best or "v1"


def _term_matches_files(term: str, files: list[str]) -> bool:
    stem = term.lower().replace("_", "").replace("/", "").replace(".", "")
    for f in files:
        fstem = f.lower().replace("_", "").replace("/", "").replace(".", "")
        if stem in fstem or fstem in stem:
            return True
    return False


def _selection_reason(chosen: dict[str, Any] | None, results: list[dict[str, Any]]) -> str:
    if not chosen:
        return "no candidate produced a usable result"
    return (
        f"chosen {chosen['candidate']}: recall={chosen['source_recall']}, "
        f"context={chosen['context_tokens_estimate']} tokens est, "
        f"files={chosen['selected_files']}, raw={chosen['raw_output_bytes']}B, "
        f"duration={chosen['duration_ms']}ms"
    )


def _render_context_pack(
    task: dict[str, Any], chosen: str, chosen_score: dict[str, Any] | None, results: list[dict[str, Any]]
) -> str:
    lines: list[str] = []
    lines.append("# PREPARE E11 — Code Intelligence Tournament Context Pack")
    lines.append("")
    lines.append("**Status: `E11 NOT IMPLEMENTED` — read-only preparation.**")
    lines.append(f"**`REAL_DATA_GATE`: {_real_data_gate_status()}**")
    lines.append("")
    lines.append("## Single-candidate context (ONE selected structural owner)")
    lines.append("")
    if chosen_score is None:
        lines.append(f"- chosen candidate: `{chosen}` (no usable output)")
    else:
        lines.append(f"- candidate: `{chosen_score['candidate']}`  (version {chosen_score['version'] or 'unknown'})")
        lines.append(f"- context: {chosen_score['context_tokens_estimate']} tokens est, {chosen_score['context_bytes']} bytes")
        lines.append(f"- selected files ({chosen_score['selected_files']}):")
        for f in sorted({f["path"] for f in _files_for(chosen_score)}):
            lines.append(f"  - `{f}`")
    lines.append("")
    lines.append("## Comparison evidence (metrics only, NOT agent context)")
    lines.append("")
    lines.append("| candidate | status | files | ctx tok | raw B | duration ms | src recall |")
    lines.append("|---|---|---|---|---|---|---|")
    for r in results:
        lines.append(
            f"| {r['candidate']} | {r['status']} | {r['selected_files']} | {r['context_tokens_estimate']} | "
            f"{r['raw_output_bytes']} | {r['duration_ms']} | {r['source_recall'] or '-'} |"
        )
    lines.append("")
    lines.append(f"Full raw evidence and normalized results: `{EVIDENCE_ROOT / 'prepare-e11'}`.")
    lines.append("")
    lines.append("---")
    lines.append(f"_`E11 NOT IMPLEMENTED`. Generated by `scripts/ai_dev_tournament.py code-intel --prepare-e11` ({_now()})._")
    return "\n".join(lines)


def _files_for(score: dict[str, Any]) -> list[dict[str, Any]]:
    # Re-derive files from the persisted result (score has no file list).
    path = EVIDENCE_ROOT / "code-intel" / "prepare-e11" / f"{score['candidate']}.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["result"]["files"]
    except Exception:
        return []


# --------------------------------------------------------------------------- list


def cmd_list(args: argparse.Namespace) -> int:
    if not _HAS_ADAPTERS:
        print("ai_dev_adapters unavailable", file=sys.stderr)
        return 1
    config = ai_dev_adapters.load_tournament_config()
    caps = ai_dev_capability.load_registry()
    names = list(config["code_intelligence"]["control"]) + list(config["code_intelligence"]["candidates"])
    rows = []
    for name in names:
        rec = caps.get(name, {})
        version = rec.get("version")
        rows.append(
            {
                "candidate": name,
                "state": rec.get("state", "?"),
                "type": rec.get("type", "?"),
                "installed": bool(rec.get("installed") or rec.get("command")),
                "version": version,
                "source": rec.get("source"),
            }
        )
    if args.json:
        print(json.dumps({"schema_version": SCHEMA_VERSION, "candidates": rows}, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"{'candidate':<20}{'state':<13}{'type':<28}{'installed':<10}version")
    for r in rows:
        print(f"{r['candidate']:<20}{r['state']:<13}{r['type']:<28}{r['installed']!s:<10}{r['version'] or '-'}")
    return 0


# --------------------------------------------------------------------------- test selection (Wave 2B)


def cmd_code_intel(args: argparse.Namespace, config: dict[str, Any]) -> int:
    candidates = args.candidates or DEFAULT_CODE_INTEL
    target = args.target or int(config["context_token_target"])
    if args.prepare_e11:
        comparison = run_prepare_e11(config, candidates, target=target, chosen=args.choose)
        print(f"PREPARE E11 tournament — E11 NOT IMPLEMENTED, REAL_DATA_GATE {comparison['real_data_gate']}")
        print(f"chosen candidate: {comparison['chosen_candidate']}")
        print(f"agent context pack: {comparison['agent_context_pack']}")
        print(f"pack tokens (est): {comparison['pack_tokens_estimate']}")
        return 0
    tasks = load_tasks()
    if args.task:
        tasks = [t for t in tasks if t["task_id"] == args.task]
        if not tasks:
            print(f"unknown task: {args.task}", file=sys.stderr)
            return 1
    comparison = run_code_intel_tournament(tasks, config, candidates, target=target, fresh_trees=args.fresh_trees, shadow=args.shadow)
    if args.json:
        print(json.dumps(comparison, ensure_ascii=False, sort_keys=True))
    else:
        _print_comparison(comparison)
    return 0


def _print_comparison(comparison: dict[str, Any]) -> None:
    print()
    print(f"code-intel tournament — {comparison['ran_at']}")
    print(f"tasks: {', '.join(t['task_id'] for t in comparison['tasks'])}")
    print()
    print(f"{'candidate':<20}{'ok':<4}{'src recall':<11}{'ctx tok (med)':<14}{'ctx tok (tot)':<14}{'dur ms (mean)'}")
    for name, s in comparison["summary"].items():
        print(
            f"{name:<20}{s['tasks_ok']:<4}{s['source_recall_mean']!s:<11}{s['context_tokens_median']!s:<14}"
            f"{s['context_tokens_total']!s:<14}{s['duration_ms_mean']!s}"
        )


# --------------------------------------------------------------------------- CLI


def _make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ai_dev_tournament", description="AI Dev OS v2 intelligence tournament runner")
    ap.add_argument("--version", action="store_true", help="print runner version and exit")
    sub = ap.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="tournament candidates + registry state")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(fn=cmd_list)

    p_ci = sub.add_parser("code-intel", help="code-intelligence tournament")
    p_ci.add_argument("--task", default=None, help="one frozen task_id")
    p_ci.add_argument("--all-tasks", action="store_true", help="run all frozen tasks")
    p_ci.add_argument("--prepare-e11", action="store_true", help="PREPARE E11 code-intel tournament")
    p_ci.add_argument("--choose", default=None, help="PREPARE E11: force the agent-facing candidate")
    p_ci.add_argument("--candidates", nargs="*", default=None, help="override candidate list")
    p_ci.add_argument("--target", type=int, default=None)
    p_ci.add_argument("--fresh-trees", action="store_true", help="re-materialize historical base trees")
    p_ci.add_argument("--shadow", action="store_true", help="LAB shadow mode: telemetry-only evidence (never affects context/acceptance)")
    p_ci.add_argument("--json", action="store_true")
    p_ci.set_defaults(fn=cmd_code_intel)

    p_ts = sub.add_parser("test-select", help="test-selection tournament (mutation probes)")
    p_ts.add_argument("--scenario", default=None, help="one scenario_id")
    p_ts.add_argument("--all", action="store_true", help="run all scenarios")
    p_ts.add_argument("--list-scenarios", action="store_true", help="list scenario definitions")
    p_ts.add_argument("--revalidate", action="store_true", help="A1/A2-repaired revalidation: FULL + retained current selector only")
    p_ts.add_argument("--json", action="store_true")
    p_ts.set_defaults(fn=cmd_test_select)

    return ap


def cmd_test_select(args: argparse.Namespace) -> int:
    from ai_dev_testselect import (  # type: ignore
        list_scenarios,
        revalidate_retained_selector,
        run_test_select_all,
        run_test_select_scenario,
    )

    scenarios = list_scenarios()
    if args.list_scenarios:
        for s in scenarios:
            print(f"{s['scenario_id']:<28}{s['class']:<22}{s['module']}")
        return 0
    if args.revalidate:
        result = revalidate_retained_selector()
    elif args.scenario:
        if not any(s["scenario_id"] == args.scenario for s in scenarios):
            print(f"unknown scenario: {args.scenario}", file=sys.stderr)
            return 1
        result = run_test_select_scenario(args.scenario)
    elif args.all:
        result = run_test_select_all()
    else:
        ap = _make_parser()
        ap.parse_args(["test-select", "--help"])
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = _make_parser()
    args = ap.parse_args(argv)
    if args.version:
        print(f"ai_dev_tournament {SCHEMA_VERSION}.0")
        return 0
    if not args.command:
        ap.print_help()
        return 1
    if args.command in ("list", "test-select"):
        return args.fn(args)
    config = ai_dev_perf.load_config() if _HAS_PERF else {}
    return args.fn(args, config)


if __name__ == "__main__":
    try:
        rc = main()
    except TournamentError as exc:
        print(f"error: {exc}", file=sys.stderr)
        rc = 1
    except KeyboardInterrupt:
        sys.exit(130)
    if rc:
        sys.exit(rc)
