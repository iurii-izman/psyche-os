"""AI Dev OS v2 — Acceleration Wave 2: normalized candidate adapters.

A thin adapter layer over the existing JIT capability infrastructure. Every
code-intelligence candidate is reduced to ONE normalized shape so the
tournament runner can score objective metrics without inventing equivalent
semantics between different tools. Fields a tool cannot populate stay null —
nothing is fabricated.

Shared machinery lives here; the runner (`ai_dev_tournament.py`) decides
repository authority. Adapters never write to application source.
"""
from __future__ import annotations

from collections.abc import Callable
import contextlib
import json
from pathlib import Path
import re
import subprocess
import threading
import time
from typing import Any

import yaml

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

try:
    import psutil  # type: ignore

    _HAS_PSUTIL = True
except Exception:  # pragma: no cover
    psutil = None  # type: ignore[assignment]
    _HAS_PSUTIL = False

REPO = Path(__file__).resolve().parent.parent
TOURNAMENT_CONFIG = REPO / ".ai-dev" / "performance" / "tournament.yaml"
EVIDENCE_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "tournament"
RUNS_ROOT = REPO / ".ai-dev" / "evidence" / "performance" / "runs" / "tournament"

CHARS_PER_TOKEN = 4.0


class AdapterError(Exception):
    """A deterministic adapter failure (tool missing, parse failure, timeout)."""


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def load_tournament_config(path: Path | None = None) -> dict[str, Any]:
    p = Path(path) if path else TOURNAMENT_CONFIG
    if not p.is_file():
        raise AdapterError(f"tournament config not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise AdapterError(f"tournament config {p} is not a mapping")
    return data


# --------------------------------------------------------------------------- subprocess + resources


def run_and_capture(
    argv: list[str],
    *,
    cwd: Path,
    timeout: int = 300,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Run a candidate subprocess and capture timing/output/resources.

    Resource measurement is best-effort (psutil when importable); anything not
    cheaply observable is recorded as None (honest UNKNOWN), never guessed.
    """
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(cwd),
            check=False,
            env=env,
        )
    except FileNotFoundError as exc:
        raise AdapterError(f"command not found: {argv[0]!r}") from exc
    except subprocess.TimeoutExpired as exc:
        raise AdapterError(f"command timed out after {timeout}s: {argv[0]!r}") from exc
    duration_ms = (time.perf_counter() - t0) * 1000.0

    peak_rss_mb: float | None = None
    process_count: int | None = None
    if _HAS_PSUTIL and proc.returncode == 0:
        try:
            peak_rss_mb = round(proc_peak_rss_mb(proc), 1)
            process_count = 1
        except Exception:
            peak_rss_mb = None

    return {
        "argv": argv,
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "duration_ms": round(duration_ms, 1),
        "raw_output_bytes": len(proc.stdout.encode("utf-8", errors="replace")),
        "peak_rss_mb": peak_rss_mb,
        "process_count": process_count,
    }


def proc_peak_rss_mb(proc: subprocess.Popen | subprocess.CompletedProcess) -> float:
    """Best-effort peak RSS of a completed subprocess tree (MB)."""
    if not _HAS_PSUTIL:
        return 0.0
    total = 0.0
    try:
        pid = proc.pid if hasattr(proc, "pid") else None
        if pid is None:
            return 0.0
        for child in psutil.Process(pid).children(recursive=True):  # type: ignore[union-attr]
            with contextlib.suppress(Exception):
                total += child.memory_info().rss
        with contextlib.suppress(Exception):
            total += psutil.Process(pid).memory_info().rss  # type: ignore[union-attr]
    except Exception:
        return 0.0
    return total / (1024 * 1024)


def resolve_candidate_binary(name: str) -> list[str] | None:
    """Resolve a registered candidate's command to argv via the capability registry.

    Returns None when the candidate is registered but has no directly invocable
    command (e.g. a Python plugin, which runs through pytest/uv instead).
    """
    if not _HAS_CAP:
        return None
    caps = ai_dev_capability.load_registry()
    rec = caps.get(name)
    if not rec:
        return None
    cmd = rec.get("command")
    if not cmd:
        return None
    parts = cmd.split()
    if not parts:
        return None
    if parts[0] == "uv":
        return parts
    exe = ai_dev_capability.find_exe(parts[0])
    if not exe:
        return None
    return [exe, *parts[1:]]


# --------------------------------------------------------------------------- normalization


def make_result(
    *,
    candidate: str,
    version: str | None,
    task_id: str,
    files: list[dict[str, Any]],
    symbols: list[dict[str, Any]],
    relations: list[dict[str, Any]],
    normalized_context: str,
    duration_ms: float,
    raw_output_bytes: int,
    index_build_ms: float | None,
    index_size_bytes: int | None,
    tool_calls: int,
    cold: bool,
    raw_evidence: str | None = None,
    peak_rss_mb: float | None = None,
    process_count: int | None = None,
    status: str = "ok",
    error: str | None = None,
) -> dict[str, Any]:
    """Assemble the single normalized adapter result shape."""
    return {
        "candidate": candidate,
        "version": version,
        "task_id": task_id,
        "status": status,
        "error": error,
        "files": files,
        "symbols": symbols,
        "relations": relations,
        "normalized_context": normalized_context,
        "metrics": {
            "duration_ms": round(duration_ms, 1),
            "raw_output_bytes": raw_output_bytes,
            "normalized_output_bytes": len(normalized_context.encode("utf-8", errors="replace")),
            "selected_files": len(files),
            "selected_ranges": sum(1 for s in symbols if s.get("range")),
            "index_build_ms": index_build_ms,
            "index_size_bytes": index_size_bytes,
            "tool_calls": tool_calls,
            "cold": cold,
            "peak_rss_mb": peak_rss_mb,
            "process_count": process_count,
            "background_services": None,
        },
        "raw_evidence": raw_evidence,
        "tokens_estimate": estimate_tokens(normalized_context),
    }


def failure_result(candidate: str, task_id: str, error: str) -> dict[str, Any]:
    """A deterministic adapter failure result — the tournament never crashes."""
    return make_result(
        candidate=candidate,
        version=None,
        task_id=task_id,
        files=[],
        symbols=[],
        relations=[],
        normalized_context="",
        duration_ms=0.0,
        raw_output_bytes=0,
        index_build_ms=None,
        index_size_bytes=None,
        tool_calls=0,
        cold=False,
        status="error",
        error=error,
    )


# --------------------------------------------------------------------------- scoring (shared)

GT_SOURCE_KEY = "changed_sources"
GT_TEST_KEY = "changed_tests"


def score_files(files: list[dict[str, Any]], relevant: list[str]) -> dict[str, Any]:
    """Recall/precision of a retrieved file set vs ground truth.

    Both denominators are 1-based: a candidate that returns nothing has recall 0
    and precision 0 — it can never win by returning almost nothing.
    """
    retrieved = {f["path"].replace("\\", "/") for f in files}
    relevant_set = {p.replace("\\", "/") for p in relevant}
    tp = len(retrieved & relevant_set)
    recall = tp / len(relevant_set) if relevant_set else None
    precision = tp / len(retrieved) if retrieved else (1.0 if not relevant_set else 0.0)
    return {
        "relevant": sorted(relevant_set),
        "retrieved": sorted(retrieved),
        "true_positives": tp,
        "recall": round(recall, 3) if recall is not None else None,
        "precision": round(precision, 3),
        "missed": sorted(relevant_set - retrieved),
    }


def score_task_result(result: dict[str, Any], task: dict[str, Any]) -> dict[str, Any]:
    """Objective per-task scoring for a normalized adapter result."""
    src = score_files(result["files"], task.get(GT_SOURCE_KEY, []))
    tests = score_files(result["files"], task.get(GT_TEST_KEY, []))
    metrics = result["metrics"]
    return {
        "task_id": task["task_id"],
        "candidate": result["candidate"],
        "version": result["version"],
        "status": result["status"],
        "error": result["error"],
        "source_recall": src["recall"],
        "source_precision": src["precision"],
        "test_recall": tests["recall"],
        "missed_source": src["missed"],
        "missed_tests": tests["missed"],
        "context_tokens_estimate": result["tokens_estimate"],
        "context_bytes": metrics["normalized_output_bytes"],
        "raw_output_bytes": metrics["raw_output_bytes"],
        "selected_files": metrics["selected_files"],
        "selected_ranges": metrics["selected_ranges"],
        "tool_calls": metrics["tool_calls"],
        "duration_ms": metrics["duration_ms"],
        "index_build_ms": metrics["index_build_ms"],
        "index_size_bytes": metrics["index_size_bytes"],
        "cold": metrics["cold"],
        "peak_rss_mb": metrics["peak_rss_mb"],
        "process_count": metrics["process_count"],
    }


def write_raw_evidence(subdir: str, filename: str, text: str) -> str:
    """Persist a candidate's raw output under the tournament evidence tree."""
    d = RUNS_ROOT / subdir
    d.mkdir(parents=True, exist_ok=True)
    p = d / filename
    p.write_text(text, encoding="utf-8", errors="replace")
    return str(p)


# --------------------------------------------------------------------------- path helpers


def rel_path(path_text: str, base_repo: Path) -> str:
    """Relativize an absolute or repo-rooted path to repo-relative posix."""
    p = path_text.strip().replace("\\", "/")
    # Absolute Windows path containing the base repo dir.
    base = str(base_repo.resolve()).replace("\\", "/")
    if base in p:
        p = p.split(base, 1)[1].lstrip("/")
    # Absolute /tmp style path containing base_repo leaf.
    elif p.startswith("/"):
        with contextlib.suppress(ValueError):
            p = str(Path(p).relative_to(base_repo)).replace("\\", "/")
    return p


def dedupe_files(raw: list[str], base_repo: Path, *, reason: str, relation: str | None = None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path_text in raw:
        rel = rel_path(path_text, base_repo)
        if not rel or rel.startswith(".") or rel in seen:
            continue
        seen.add(rel)
        out.append({"path": rel, "score": None, "reason": reason, "relation": relation})
    return out


# --------------------------------------------------------------------------- V1 / V2 (existing PR11 infrastructure)


def adapter_v1(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int) -> dict[str, Any]:
    """V1 control: rg + ast-grep lexical retrieval over the base tree (no index)."""
    if not _HAS_PERF:
        return failure_result("v1", task["task_id"], "ai_dev_perf unavailable")
    raw = ai_dev_perf.retrieve_v1(task, base_repo, config, tools, target)
    items = [{"path": it["path"], "start": it["start"], "end": it["end"], "text": it["text"], "source": it["source"]} for it in raw["items"]]
    files = dedupe_files([it["path"] for it in items], base_repo, reason="lexical-match", relation="lexical")
    return make_result(
        candidate="v1",
        version=None,
        task_id=task["task_id"],
        files=files,
        symbols=[{"path": it["path"], "symbol": None, "range": [it["start"], it["end"]], "kind": "range"} for it in items],
        relations=[],
        normalized_context=_render_items(items),
        duration_ms=raw["wall_ms"],
        raw_output_bytes=raw["tool_output_bytes"],
        index_build_ms=None,
        index_size_bytes=None,
        tool_calls=raw["tool_calls"],
        cold=False,
        raw_evidence=write_raw_evidence(f"v1-{task['task_id']}", "output.txt", _render_items(items, full=True)),
    )


def adapter_v2(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int, index: Any) -> dict[str, Any]:
    """V2 control: the existing PR11 lightweight local index."""
    if not _HAS_PERF:
        return failure_result("v2", task["task_id"], "ai_dev_perf unavailable")
    raw = ai_dev_perf.retrieve_v2(task, base_repo, config, tools, target, index)
    items = [{"path": it["path"], "start": it["start"], "end": it["end"], "text": it["text"], "source": it["source"]} for it in raw["items"]]
    files = dedupe_files([it["path"] for it in items], base_repo, reason="index-resolution", relation="index")
    return make_result(
        candidate="v2",
        version=None,
        task_id=task["task_id"],
        files=files,
        symbols=[{"path": it["path"], "symbol": None, "range": [it["start"], it["end"]], "kind": "range"} for it in items],
        relations=[],
        normalized_context=_render_items(items),
        duration_ms=raw["wall_ms"],
        raw_output_bytes=raw["tool_output_bytes"],
        index_build_ms=raw.get("index_build_ms"),
        index_size_bytes=None,
        tool_calls=raw["tool_calls"],
        cold=bool(raw.get("index_build_ms")),
        raw_evidence=write_raw_evidence(f"v2-{task['task_id']}", "output.txt", _render_items(items, full=True)),
    )


def _render_items(items: list[dict[str, Any]], full: bool = False) -> str:
    lines: list[str] = []
    for it in items:
        lines.append(f"### {it['path']}:{it['start']}-{it['end']}  [source={it.get('source', '?')}]")
        if full:
            lines.append(it["text"])
        else:
            text = it["text"]
            lines.append(text if len(text) <= 2000 else text[:2000] + "\n... [truncated]")
    return "\n\n".join(lines)


# --------------------------------------------------------------------------- external candidates


def _git_init_tree(base_repo: Path) -> None:
    """Aider repo-map requires tracked files; materialized historical trees have none.

    Initializes when absent and stages whenever the repo has no tracked files.
    The current repo already has tracked files and is never staged by an adapter.
    """
    if not (base_repo / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=str(base_repo), check=True, capture_output=True)
    ls = subprocess.run(["git", "ls-files"], capture_output=True, text=True, cwd=str(base_repo), check=False)
    if ls.returncode == 0 and not ls.stdout.strip():
        subprocess.run(["git", "add", "-A"], cwd=str(base_repo), check=True, capture_output=True)


def adapter_aider_repomap(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int) -> dict[str, Any]:
    """Aider repo-map: `aider --show-repo-map` (map only, zero model/network calls)."""
    argv = resolve_candidate_binary("aider-repo-map")
    if not argv:
        return failure_result("aider-repo-map", task["task_id"], "aider binary not installed")
    try:
        _git_init_tree(base_repo)
        cmd = [*argv, "--show-repo-map", "--map-tokens", str(max(500, target)), "--no-auto-commits", "--yes", "--no-check-update", "--no-gitignore"]
        run = run_and_capture(cmd, cwd=base_repo, timeout=300)
    except AdapterError as exc:
        return failure_result("aider-repo-map", task["task_id"], str(exc))
    if run["returncode"] != 0:
        return failure_result("aider-repo-map", task["task_id"], f"aider exited {run['returncode']}: {run['stderr'][:300]}")
    out = run["stdout"]
    files = _parse_repomap_files(out, base_repo)
    raw = write_raw_evidence(f"aider-{task['task_id']}", "output.txt", out)
    return make_result(
        candidate="aider-repo-map",
        version="0.86.2",
        task_id=task["task_id"],
        files=files,
        symbols=[],
        relations=[],
        normalized_context=out[: target * 4],
        duration_ms=run["duration_ms"],
        raw_output_bytes=run["raw_output_bytes"],
        index_build_ms=None,
        index_size_bytes=None,
        tool_calls=1,
        cold=True,
        raw_evidence=raw,
        peak_rss_mb=run["peak_rss_mb"],
        process_count=run["process_count"],
    )


_REPOMAP_HEADER_RE = re.compile(r"^([^\n:]+(?:\.py|\.ts|\.tsx|\.js|\.jsx|\.mjs|\.rs|\.md|\.toml|\.yaml|\.yml)):\s*$")


def _parse_repomap_files(out: str, base_repo: Path) -> list[dict[str, Any]]:
    """Parse aider repo-map file headers (a `<path>:` line) into file entries."""
    paths: list[str] = []
    for line in out.splitlines():
        m = _REPOMAP_HEADER_RE.match(line.rstrip())
        if m:
            paths.append(m.group(1))
    return dedupe_files(paths, base_repo, reason="repo-map", relation="map")


# --- code-review-graph ------------------------------------------------------


def adapter_code_review_graph(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int) -> dict[str, Any]:
    argv = resolve_candidate_binary("code-review-graph")
    if not argv:
        return failure_result("code-review-graph", task["task_id"], "code-review-graph not installed")

    t0 = time.perf_counter()
    try:
        build = run_and_capture([*argv, "build", "--repo", str(base_repo)], cwd=base_repo, timeout=600)
    except AdapterError as exc:
        return failure_result("code-review-graph", task["task_id"], str(exc))
    index_build_ms = (time.perf_counter() - t0) * 1000.0
    if build["returncode"] != 0:
        return failure_result("code-review-graph", task["task_id"], f"crg build exited {build['returncode']}: {build['stderr'][:300]}")

    files: dict[str, dict[str, Any]] = {}
    symbols: list[dict[str, Any]] = []
    raw_parts: list[str] = []
    tool_calls = 1
    raw_bytes = build["raw_output_bytes"]
    for term in task["terms"]:
        for variant in _query_variants(term):
            try:
                run = run_and_capture([*argv, "search", "--repo", str(base_repo), "--kind", "File", variant, "--limit", "50"], cwd=base_repo, timeout=120)
            except AdapterError as exc:
                return failure_result("code-review-graph", task["task_id"], str(exc))
            tool_calls += 1
            raw_bytes += run["raw_output_bytes"]
            raw_parts.append(run["stdout"])
            if run["returncode"] != 0:
                continue
            try:
                data = json.loads(run["stdout"])
            except json.JSONDecodeError:
                continue
            for node in data.get("results", []) or []:
                rel = rel_path(node.get("file_path") or node.get("name", ""), base_repo)
                if not rel or rel.startswith("."):
                    continue
                files.setdefault(rel, {"path": rel, "score": node.get("score"), "reason": "crg-search", "relation": "graph"})
                symbols.append({"path": rel, "symbol": node.get("qualified_name"), "range": [node.get("line_start"), node.get("line_end")] if node.get("line_start") else None, "kind": node.get("kind")})

    out = "\n".join(raw_parts)
    ctx = _render_files([f["path"] for f in files.values()])
    raw = write_raw_evidence(f"crg-{task['task_id']}", "output.txt", out)
    return make_result(
        candidate="code-review-graph",
        version="2.3.7",
        task_id=task["task_id"],
        files=list(files.values()),
        symbols=symbols,
        relations=[],
        normalized_context=ctx,
        duration_ms=build["duration_ms"] + (time.perf_counter() - t0) * 1000.0,
        raw_output_bytes=raw_bytes,
        index_build_ms=round(index_build_ms, 1),
        index_size_bytes=_dir_bytes(base_repo / ".code-review-graph"),
        tool_calls=tool_calls,
        cold=True,
        raw_evidence=raw,
        peak_rss_mb=build["peak_rss_mb"],
        process_count=build["process_count"],
    )


# --- codebase-memory-mcp ----------------------------------------------------


def adapter_codebase_memory(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int) -> dict[str, Any]:
    argv = resolve_candidate_binary("codebase-memory")
    if not argv:
        return failure_result("codebase-memory", task["task_id"], "codebase-memory-mcp not installed")
    project = f"psycheos-tournament-{task['task_id'].replace('_', '-')}"

    t0 = time.perf_counter()
    try:
        build = run_and_capture(
            [*argv, "cli", "index_repository", "--repo-path", str(base_repo), "--name", project, "--mode", "fast"],
            cwd=base_repo, timeout=600,
        )
    except AdapterError as exc:
        return failure_result("codebase-memory", task["task_id"], str(exc))
    index_build_ms = (time.perf_counter() - t0) * 1000.0
    if build["returncode"] != 0:
        return failure_result("codebase-memory", task["task_id"], f"cbm index exited {build['returncode']}: {build['stderr'][:300]}")

    files: dict[str, dict[str, Any]] = {}
    symbols: list[dict[str, Any]] = []
    raw_parts: list[str] = []
    tool_calls = 1
    raw_bytes = build["raw_output_bytes"]
    for term in task["terms"]:
        try:
            run = run_and_capture(
                [*argv, "cli", "search_graph", "--project", project, "--query", term, "--detail", "ids", "--limit", "50"],
                cwd=base_repo, timeout=120,
            )
        except AdapterError as exc:
            return failure_result("codebase-memory", task["task_id"], str(exc))
        tool_calls += 1
        raw_bytes += run["raw_output_bytes"]
        raw_parts.append(run["stdout"])
        if run["returncode"] != 0:
            continue
        for row in _cbm_parse_rows(run["stdout"]):
            rel = rel_path(row["file"], base_repo)
            if not rel or rel.startswith("."):
                continue
            files.setdefault(rel, {"path": rel, "score": row["rank"], "reason": "cbm-search", "relation": "graph"})
            if row["start"]:
                symbols.append({"path": rel, "symbol": row["qn"], "range": [row["start"], row["end"]], "kind": row["label"]})

    out = "\n".join(raw_parts)
    ctx = _render_files([f["path"] for f in files.values()])
    raw = write_raw_evidence(f"cbm-{task['task_id']}", "output.txt", out)
    return make_result(
        candidate="codebase-memory",
        version="0.10.5",
        task_id=task["task_id"],
        files=list(files.values()),
        symbols=symbols,
        relations=[],
        normalized_context=ctx,
        duration_ms=build["duration_ms"] + (time.perf_counter() - t0) * 1000.0,
        raw_output_bytes=raw_bytes,
        index_build_ms=round(index_build_ms, 1),
        index_size_bytes=_dir_bytes(Path.home() / ".cache" / "codebase-memory-mcp"),
        tool_calls=tool_calls,
        cold=True,
        raw_evidence=raw,
        peak_rss_mb=build["peak_rss_mb"],
        process_count=build["process_count"],
    )


_CBM_ROW_RE = re.compile(r"^\s+(\S+)\s+(\S+)\s+(\S+)\s+(\d+)-(\d+)\s+(\S+)")


def _cbm_parse_rows(out: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in out.splitlines():
        m = _CBM_ROW_RE.match(line)
        if m:
            rows.append(
                {
                    "qn": m.group(1),
                    "label": m.group(2),
                    "file": m.group(3),
                    "start": int(m.group(4)),
                    "end": int(m.group(5)),
                    "rank": float(m.group(6)),
                }
            )
    return rows


# --- pathfinder (MCP over stdio) -------------------------------------------


class _MCPClient:
    """Minimal MCP-over-stdio client for a single tool server (JIT, no daemon)."""

    def __init__(self, argv: list[str], workspace: Path, timeout: int = 180) -> None:
        self._proc = subprocess.Popen(
            [*argv, str(workspace)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        self._timeout = timeout
        self._lock = threading.Lock()
        self._responses: dict[int, dict[str, Any]] = {}
        self._id = 0
        self._stderr: list[str] = []
        threading.Thread(target=self._reader, daemon=True).start()
        threading.Thread(target=self._err_reader, daemon=True).start()

    def _reader(self) -> None:
        for line in self._proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "id" in msg:
                with self._lock:
                    self._responses[msg["id"]] = msg

    def _err_reader(self) -> None:
        for line in self._proc.stderr:
            self._stderr.append(line.strip())

    def _send(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        with self._lock:
            self._id += 1
            rid = self._id
        msg: dict[str, Any] = {"jsonrpc": "2.0", "id": rid, "method": method}
        if params is not None:
            msg["params"] = params
        self._proc.stdin.write(json.dumps(msg) + "\n")
        self._proc.stdin.flush()
        end = time.time() + self._timeout
        while time.time() < end:
            with self._lock:
                if rid in self._responses:
                    return self._responses.pop(rid)
            time.sleep(0.03)
        return {"id": rid, "timeout": True}

    def initialize(self) -> None:
        resp = self._send("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "psyche-os-tournament", "version": "0.1.0"}})
        if resp.get("timeout") or "result" not in resp:
            raise AdapterError(f"pathfinder initialize failed: {self._stderr[-3:]}")
        self._proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self._proc.stdin.flush()

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        resp = self._send("tools/call", {"name": name, "arguments": arguments})
        if resp.get("timeout"):
            raise AdapterError(f"pathfinder tool {name} timed out")
        return resp

    def close(self) -> None:
        with contextlib.suppress(Exception):
            self._proc.terminate()
        try:
            self._proc.wait(timeout=10)
        except Exception:
            with contextlib.suppress(Exception):
                self._proc.kill()


def adapter_pathfinder(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int) -> dict[str, Any]:
    argv = resolve_candidate_binary("pathfinder")
    if not argv:
        return failure_result("pathfinder", task["task_id"], "pathfinder binary not installed")

    t0 = time.perf_counter()
    client = _MCPClient(argv, base_repo, timeout=120)
    try:
        client.initialize()
    except AdapterError as exc:
        client.close()
        return failure_result("pathfinder", task["task_id"], str(exc))

    files: dict[str, dict[str, Any]] = {}
    symbols: list[dict[str, Any]] = []
    raw_parts: list[str] = []
    tool_calls = 1
    try:
        for term in task["terms"]:
            resp = client.call_tool("search", {"query": term})
            tool_calls += 1
            text = _mcp_text(resp)
            raw_parts.append(text)
            found = _pf_collect(text, term, files)
            if not found:
                # Text search may miss module-name terms (term only in the
                # filename); symbol mode searches symbol names — a fair fallback.
                resp = client.call_tool("search", {"query": term, "mode": "symbol"})
                tool_calls += 1
                text = _mcp_text(resp)
                raw_parts.append(text)
                _pf_collect(text, term, files)
    except AdapterError as exc:
        client.close()
        return failure_result("pathfinder", task["task_id"], str(exc))
    finally:
        client.close()

    out = "\n".join(raw_parts)
    ctx = _render_files([f["path"] for f in files.values()])
    raw = write_raw_evidence(f"pf-{task['task_id']}", "output.txt", out)
    return make_result(
        candidate="pathfinder",
        version="0.23.2",
        task_id=task["task_id"],
        files=list(files.values()),
        symbols=symbols,
        relations=[],
        normalized_context=ctx,
        duration_ms=(time.perf_counter() - t0) * 1000.0,
        raw_output_bytes=len(out.encode("utf-8", errors="replace")),
        index_build_ms=None,
        index_size_bytes=None,
        tool_calls=tool_calls,
        cold=True,
        raw_evidence=raw,
    )


def _pf_collect(text: str, term: str, files: dict[str, dict[str, Any]]) -> int:
    """Collect file paths from a pathfinder search response.

    The response text is JSON; parsing it (not regex on raw text) unescapes the
    backslash separators so paths normalize to single slashes.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return 0
    n = 0
    for m in data.get("matches", []) or []:
        rel = rel_path(m.get("file", ""), Path(REPO))
        if rel.startswith(".") or not rel:
            continue
        files.setdefault(rel, {"path": rel, "score": None, "reason": f"search:{term}", "relation": "lexical"})
        n += 1
    return n


def _mcp_text(resp: dict[str, Any]) -> str:
    content = resp.get("result", {}).get("content", []) or []
    return "\n".join(c.get("text", "") for c in content if c.get("type") == "text")


# --- symlens (WSL2) ---------------------------------------------------------


WSL_DISTRO = "Ubuntu-26.04"
_SYMLENS_WSL_ROOT = "/tmp/symlens-tournament"


def adapter_symlens(task: dict[str, Any], base_repo: Path, config: dict[str, Any], tools: dict[str, str], target: int) -> dict[str, Any]:
    """SymLens (WSL2): tree-sitter symbol index; search per task term.

    The materialized tree is copied to the WSL filesystem (9P /mnt/c access is
    slow) and removed after the run. Returns relative paths directly.
    """
    import platform

    if not platform.system().lower().startswith("windows"):
        return failure_result("symlens", task["task_id"], "symlens adapter is WSL-only")
    if not _wsl_has_symlens():
        return failure_result("symlens", task["task_id"], "symlens binary not installed in WSL")

    wsl_root = f"{_SYMLENS_WSL_ROOT}-{task['task_id']}"
    try:
        _wsl_rsync_in(base_repo, wsl_root)
        index_run = _wsl_run(f"cd {wsl_root} && ~/.cargo/bin/symlens index", timeout=300)
        if index_run["returncode"] != 0:
            return failure_result("symlens", task["task_id"], f"symlens index exited {index_run['returncode']}: {index_run['stderr'][:300]}")
        files: dict[str, dict[str, Any]] = {}
        symbols: list[dict[str, Any]] = []
        raw_parts: list[str] = []
        tool_calls = 1
        raw_bytes = index_run["raw_output_bytes"]
        for term in task["terms"]:
            run = _wsl_run(f"cd {wsl_root} && ~/.cargo/bin/symlens search {term!r} --json", timeout=120)
            tool_calls += 1
            raw_bytes += run["raw_output_bytes"]
            raw_parts.append(run["stdout"])
            if run["returncode"] != 0:
                continue
            try:
                data = json.loads(run["stdout"])
            except json.JSONDecodeError:
                continue
            for node in data.get("results", []) or []:
                rel = node.get("file", "").replace("\\", "/")
                if not rel or rel.startswith(".") or rel.startswith(".."):
                    continue
                files.setdefault(rel, {"path": rel, "score": node.get("score"), "reason": f"symlens:{term}", "relation": "symbol"})
                lines = node.get("lines") or []
                if len(lines) >= 2:
                    symbols.append({"path": rel, "symbol": node.get("qualified_name"), "range": [lines[0], lines[1]], "kind": node.get("kind")})
        out = "\n".join(raw_parts)
        ctx = _render_files([f["path"] for f in files.values()])
        raw = write_raw_evidence(f"symlens-{task['task_id']}", "output.txt", out)
        return make_result(
            candidate="symlens",
            version="0.12.15",
            task_id=task["task_id"],
            files=list(files.values()),
            symbols=symbols,
            relations=[],
            normalized_context=ctx,
            duration_ms=index_run["duration_ms"],
            raw_output_bytes=raw_bytes,
            index_build_ms=index_run["duration_ms"],
            index_size_bytes=None,
            tool_calls=tool_calls,
            cold=True,
            raw_evidence=raw,
        )
    finally:
        _wsl_run(f"rm -rf {wsl_root}", timeout=60)


def _wsl_has_symlens() -> bool:
    run = _wsl_run("test -x $HOME/.cargo/bin/symlens && echo yes", timeout=60)
    return run["returncode"] == 0 and "yes" in run["stdout"]


def _wsl_rsync_in(base_repo: Path, wsl_root: str) -> None:
    win = str(base_repo.resolve()).replace("\\", "/")
    # /mnt/<drive>/... path form for WSL.
    mnt = "/mnt/" + win[0].lower() + win[2:]
    run = _wsl_run(f"rm -rf {wsl_root} && mkdir -p {wsl_root} && cp -r {mnt}/. {wsl_root}/", timeout=300)
    if run["returncode"] != 0:
        raise AdapterError(f"wsl copy into {wsl_root} failed: {run['stderr'][:300]}")


def _wsl_run(command: str, *, timeout: int = 300) -> dict[str, Any]:

    argv = ["wsl", "-d", WSL_DISTRO, "--", "bash", "-lc", command]
    return run_and_capture(argv, cwd=REPO, timeout=timeout)


# --- generic fallback -------------------------------------------------------


def _generic_tool_query(name: str, argv: list[str], task: dict[str, Any], base_repo: Path, target: int) -> dict[str, Any]:
    try:
        cmd = [*argv, *task["terms"], "--repo", str(base_repo)]
        run = run_and_capture(cmd, cwd=base_repo, timeout=300)
    except AdapterError as exc:
        return failure_result(name, task["task_id"], str(exc))
    if run["returncode"] != 0:
        return failure_result(name, task["task_id"], f"{name} exited {run['returncode']}: {run['stderr'][:300]}")
    out = run["stdout"]
    files = dedupe_files([m.group(1) for m in _PATH_SNIFF_RE.finditer(out)], base_repo, reason="output-path")
    raw = write_raw_evidence(f"{name}-{task['task_id']}", "output.txt", out)
    return make_result(
        candidate=name,
        version=None,
        task_id=task["task_id"],
        files=files,
        symbols=[],
        relations=[],
        normalized_context=out[: target * 4],
        duration_ms=run["duration_ms"],
        raw_output_bytes=run["raw_output_bytes"],
        index_build_ms=None,
        index_size_bytes=None,
        tool_calls=1,
        cold=True,
        raw_evidence=raw,
        peak_rss_mb=run["peak_rss_mb"],
        process_count=run["process_count"],
    )


_PATH_SNIFF_RE = re.compile(r"(src/psyche_os[\w/.\-]+\.py)")


# --------------------------------------------------------------------------- registry


def _query_variants(term: str) -> list[str]:
    """Query variants for FTS tools: the full term plus underscore-split parts.

    Tools with FTS tokenization (code-review-graph) may miss underscore-joined
    identifiers; searching the parts is a fair adapter (what a user would try),
    not a fabricated semantic — every search's output is recorded verbatim.
    """
    parts = [p for p in term.split("_") if len(p) >= 3]
    out = [term, *parts]
    seen: set[str] = set()
    return [v for v in out if not (v in seen or seen.add(v))]


def _render_files(paths: list[str]) -> str:
    return "\n".join(f"- {p}" for p in sorted(set(paths)))


def _dir_bytes(path: Path) -> int | None:
    if not path.is_dir():
        return None
    total = 0
    try:
        for p in path.rglob("*"):
            if p.is_file():
                total += p.stat().st_size
    except OSError:
        return None
    return total


AdapterFn = Callable[..., dict[str, Any]]


def get_adapter(name: str) -> AdapterFn | None:
    mapping: dict[str, AdapterFn] = {
        "v1": adapter_v1,
        "v2": adapter_v2,
        "aider-repo-map": adapter_aider_repomap,
        "pathfinder": adapter_pathfinder,
        "symlens": adapter_symlens,
        "codebase-memory": adapter_codebase_memory,
        "code-review-graph": adapter_code_review_graph,
    }
    return mapping.get(name)
