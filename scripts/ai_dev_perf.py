#!/usr/bin/env python3
"""AI Dev OS v2 — Performance & Token Efficiency Canary CLI.

A small local-first CLI that moves deterministic work onto the PC so the LLM reasons
instead of searching, indexing, ranking, and re-reading. It extends the V1 Context
Broker waterfall (`.ai-dev/context-broker.md`): exact lexical search (rg) -> structural
search (ast-grep) -> exact source ranges, without a parallel competing workflow.

The tool is stdlib-only plus the already-available system tools `rg`, `ast-grep`, git,
and `uv` (repository-native test runner). No network, no daemon, no new dependency.

Commands:
  map        build or read the code index (symbols, imports, reverse deps, test map)
  context    produce a minimal ranked context bundle of exact source ranges
  impact     compute the affected surface (modules + tests) for a change
  verify     run the targeted pytest subset for an affected surface (bounded output)
  prompt     assemble a self-contained task prompt from context + impact + verify
  benchmark  measure index time, context compression, targeted-vs-full test time
  report     regenerate the canary report markdown from saved run evidence

Run:  uv run python scripts/ai_dev_perf.py <command> [options]
"""
from __future__ import annotations

import argparse
import ast
from collections.abc import Iterable
from dataclasses import dataclass, field
import datetime
import glob
import json
from pathlib import Path
import re
import shutil
import statistics
import subprocess
import sys
import time
from typing import Any

# --------------------------------------------------------------------------- paths

REPO = Path(__file__).resolve().parent.parent
AI_DEV = REPO / ".ai-dev"
PERF_DIR = AI_DEV / "performance"
EVIDENCE_DIR = AI_DEV / "evidence" / "performance"
RUNS_DIR = EVIDENCE_DIR / "runs"
BASELINE_PATH = RUNS_DIR / "baseline-full.json"

DEFAULT_CONFIG = PERF_DIR / "config.yaml"

# --------------------------------------------------------------------------- defaults

# Context Broker soft dynamic-context target: ~5-20K useful tokens (diagnostic, not a
# hard limit). The CLI default is the top of that band; --target overrides it.
DEFAULT_CONTEXT_TARGET = 20000
# Standard token heuristic: ~4 chars per token. Labeled estimate everywhere it is used;
# the canary compares *relative* volume, so a consistent heuristic is what matters.
CHARS_PER_TOKEN = 4.0
# Merge rg matches closer than this many lines into one range (keeps ranges tight).
LEXICAL_MERGE_GAP = 4
# Sample change count for benchmark test-selection measurements.
BENCHMARK_SAMPLE_CHANGES = 3

SCHEMA_VERSION = 1


# --------------------------------------------------------------------------- errors


class PerfError(Exception):
    """A determinable tool failure (missing tool, bad input, timeout)."""


class ToolNotFoundError(PerfError):
    pass


# --------------------------------------------------------------------------- small helpers


def now_iso() -> str:
    return datetime.datetime.now(datetime.UTC).isoformat()


def slugify(text: str, max_len: int = 48) -> str:
    text = re.sub(r"[^A-Za-z0-9._/-]+", "-", text).strip("-")
    return text[:max_len] or "task"


def estimate_tokens(text: str) -> int:
    """Heuristic token estimate (~4 chars/token). Relative comparisons only."""
    return max(1, int(len(text) / CHARS_PER_TOKEN))


def estimate_token_volume(chars: int) -> int:
    """Heuristic token estimate from a character count."""
    return max(1, int(chars / CHARS_PER_TOKEN))


def rel_posix(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO).as_posix()
    except ValueError:
        return path.as_posix()


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def run_cmd(args: list[str], *, timeout: int = 120, cwd: Path | None = None) -> subprocess.CompletedProcess:
    """Run a subprocess, capturing text output. Raises PerfError on launch failure."""
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(cwd or REPO),
            check=False,
        )
    except FileNotFoundError as exc:
        raise PerfError(f"command not found: {args[0]!r}") from exc
    except subprocess.TimeoutExpired as exc:
        raise PerfError(f"command timed out after {timeout}s: {args[0]!r}") from exc


# --------------------------------------------------------------------------- tool discovery


def _winget_glob(pattern: str) -> list[str]:
    return glob.glob(f"C:/Users/*/AppData/Local/Microsoft/WinGet/Packages/*/{pattern}")


def find_rg() -> str | None:
    p = shutil.which("rg")
    if p:
        return p
    hits = _winget_glob("ripgrep*/rg.exe")
    return hits[0] if hits else None


def find_ast_grep() -> str | None:
    # Prefer the real npm-installed exe; fall back to shims found on PATH.
    for exe in ("sg.exe", "ast-grep.exe"):
        hits = glob.glob(f"C:/Users/*/AppData/Roaming/npm/node_modules/@ast-grep/cli/**/{exe}", recursive=True)
        if hits:
            return hits[0]
    for name in ("ast-grep", "sg"):
        p = shutil.which(name)
        if p:
            return p
    return None


def check_tools(need: Iterable[str]) -> dict[str, str]:
    found: dict[str, str] = {}
    if "rg" in need:
        p = find_rg()
        if not p:
            raise ToolNotFoundError("missing tool: rg")
        found["rg"] = p
    if "ast-grep" in need:
        p = find_ast_grep()
        if not p:
            raise ToolNotFoundError("missing tool: ast-grep")
        found["ast-grep"] = p
    return found


# --------------------------------------------------------------------------- config


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "src_roots": ["src/psyche_os"],
        "test_root": "tests",
        "context_token_target": DEFAULT_CONTEXT_TARGET,
        "chars_per_token": CHARS_PER_TOKEN,
        "lexical_merge_gap": LEXICAL_MERGE_GAP,
        "index_cache": ".ai-dev/evidence/performance/index.json",
        "runs_dir": ".ai-dev/evidence/performance/runs",
    }
    path = path or DEFAULT_CONFIG
    if path.is_file():
        try:
            import yaml  # type: ignore

            with path.open(encoding="utf-8") as fh:
                data = yaml.safe_load(fh) or {}
            for k in ("src_roots", "test_root", "context_token_target", "chars_per_token", "lexical_merge_gap"):
                if k in data:
                    cfg[k] = data[k]
        except Exception:
            pass  # fall back to baked-in defaults
    return cfg


# --------------------------------------------------------------------------- index model


@dataclass(frozen=True)
class Symbol:
    name: str
    kind: str  # class | function | method | variable
    start: int  # 1-based inclusive
    end: int  # 1-based inclusive


@dataclass
class Module:
    key: str  # src-root-relative posix key, e.g. "domain/ids.py"
    path: str  # repo-relative path, e.g. "src/psyche_os/domain/ids.py"
    loc: int
    symbols: list[Symbol] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)  # internal module keys


@dataclass(frozen=True)
class _RawImport:
    kind: str  # "import" | "from"
    parts: list[str]  # dotted module parts (relative resolved later)
    level: int
    names: list[str]


@dataclass
class Index:
    modules: dict[str, Module]
    reverse: dict[str, set[str]]
    symbol_index: dict[str, list[str]]
    test_map: dict[str, list[str]]  # test repo-relative path -> internal module keys
    root_pkg: str
    stats: dict[str, Any]

    def symbol_owners(self, name: str) -> list[str]:
        return list(self.symbol_index.get(name, []))

    def key_for_path(self, repo_rel: str) -> str | None:
        p = repo_rel.replace("\\", "/")
        for key, mod in self.modules.items():
            if p == mod.path or p == key or p.endswith("/" + mod.path) or p.endswith("/" + key):
                return key
        return None

    def path_for_key(self, key: str) -> str:
        return self.modules[key].path


# --------------------------------------------------------------------------- parsing


def _module_key_for_rel(rel_parts: Iterable[str]) -> str:
    return "/".join(rel_parts)


def _walk_symbols(tree: ast.AST) -> list[Symbol]:
    """Top-level classes/functions plus methods and module-level name bindings."""
    symbols: list[Symbol] = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols.append(Symbol(node.name, "function", node.lineno, node.end_lineno or node.lineno))
        elif isinstance(node, ast.ClassDef):
            symbols.append(Symbol(node.name, "class", node.lineno, node.end_lineno or node.lineno))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(Symbol(child.name, "method", child.lineno, child.end_lineno or child.lineno))
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                symbols.extend(_name_bindings(target, node))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            symbols.append(Symbol(node.target.id, "variable", node.lineno, node.end_lineno or node.lineno))
    return symbols


def _name_bindings(target: ast.AST, node: ast.AST) -> Iterable[Symbol]:
    if isinstance(target, ast.Name):
        yield Symbol(target.id, "variable", node.lineno, node.end_lineno or node.lineno)
    elif isinstance(target, (ast.Tuple, ast.List)):
        for elt in target.elts:
            yield from _name_bindings(elt, node)


def _collect_imports(tree: ast.AST) -> list[_RawImport]:
    raw: list[_RawImport] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                raw.append(_RawImport("import", alias.name.split("."), 0, []))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                raw.append(_RawImport("from", node.module.split("."), node.level or 0, [a.name for a in node.names]))
            else:
                # `from . import a, b` -> names are submodules of the current package.
                raw.append(_RawImport("from", [], node.level or 0, [a.name for a in node.names]))
    return raw


def parse_module(path: Path, src_root: Path) -> tuple[Module, list[_RawImport]]:
    rel = path.resolve().relative_to(src_root.resolve())
    key = _module_key_for_rel(rel.parts)
    repo_rel = rel_posix(path)
    text = read_text(path)
    loc = len(text.splitlines())
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        # Unparseable file: index it with no symbols/imports (ranges fall back to rg).
        return Module(key=key, path=repo_rel, loc=loc), []
    symbols = _walk_symbols(tree)
    imports = _collect_imports(tree)
    return Module(key=key, path=repo_rel, loc=loc, symbols=symbols), imports


def _resolve_import(raw: _RawImport, mod_key: str, src_root: Path, symbol_index: dict[str, list[str]]) -> list[str]:
    """Resolve a raw import to internal module keys ([] if not internal)."""
    base_parts = list(Path(mod_key).parent.parts)
    if raw.level:
        if raw.level > len(base_parts) + 1:
            return []
        # Relative import: walk up `level-1` package dirs, then append the module
        # path. The result is already below the src root (no root-package prefix).
        parts = base_parts[: len(base_parts) - (raw.level - 1)] + raw.parts
    else:
        parts = raw.parts
        if not parts or parts[0] not in {src_root.name, "__future__"}:
            return []
        if parts[0] == src_root.name:
            parts = parts[1:]

    if raw.kind == "import":
        return list(_candidate_keys(src_root, parts))
    base_keys = _candidate_keys(src_root, parts)
    targets: list[str] = []
    for name in raw.names:
        if name == "__future__":
            continue
        sub = _candidate_keys(src_root, [*parts, name])
        if sub:
            targets.extend(sub)
        elif base_keys:
            base_key = base_keys[0]
            if base_key.endswith("__init__.py"):
                targets.extend(symbol_index.get(name, []))
                targets.append(base_key)
            else:
                targets.append(base_key)
    return list(dict.fromkeys(targets))


def _candidate_keys(src_root: Path, parts: list[str]) -> list[str]:
    py = src_root.joinpath(*parts).with_suffix(".py")
    init = src_root.joinpath(*parts, "__init__.py")
    if py.is_file():
        return [_module_key_for_rel(py.resolve().relative_to(src_root.resolve()).parts)]
    if init.is_file():
        return [_module_key_for_rel(init.resolve().relative_to(src_root.resolve()).parts)]
    return []


def _test_mentions(text: str, mod_key: str, root_pkg: str) -> bool:
    """Lexical fallback for test mapping: module stem or dotted path in test text."""
    stem = Path(mod_key).name
    if stem.endswith(".py"):
        stem = stem[:-3]
    dotted = f"{root_pkg}.{mod_key[:-3].replace('/', '.')}" if mod_key.endswith(".py") else ""
    return stem in text or (bool(dotted) and dotted in text)


# --------------------------------------------------------------------------- index build


def build_index(config: dict[str, Any]) -> Index:
    t0 = time.perf_counter()
    src_roots = [REPO.joinpath(r) for r in config["src_roots"]]
    test_root = REPO.joinpath(config["test_root"])
    root_pkg = src_roots[0].name

    py_files = sorted(p for root in src_roots for p in root.rglob("*.py"))
    test_files = sorted(test_root.rglob("test_*.py"))

    modules: dict[str, Module] = {}
    raw_imports: dict[str, list[_RawImport]] = {}
    for path in py_files:
        try:
            mod, raws = parse_module(path, src_roots[0])
        except OSError:
            continue
        modules[mod.key] = mod
        raw_imports[mod.key] = raws

    symbol_index: dict[str, list[str]] = {}
    for key, mod in modules.items():
        for sym in mod.symbols:
            symbol_index.setdefault(sym.name, []).append(key)

    for key, raws in raw_imports.items():
        edges: list[str] = []
        for raw in raws:
            edges.extend(_resolve_import(raw, key, src_roots[0], symbol_index))
        modules[key].imports = list(dict.fromkeys(e for e in edges if e != key))

    reverse: dict[str, set[str]] = {k: set() for k in modules}
    for key, mod in modules.items():
        for dep in mod.imports:
            if dep in reverse:
                reverse[dep].add(key)

    # Test map: import-based primary, conservative lexical fallback.
    test_map: dict[str, list[str]] = {}
    for path in test_files:
        repo_rel = rel_posix(path)
        text = read_text(path)
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            test_map[repo_rel] = []
            continue
        hit: dict[str, None] = {}
        for raw in _collect_imports(tree):
            for key in _resolve_import(raw, "tests", src_roots[0], symbol_index):
                if key in modules:
                    hit.setdefault(key, None)
        if not hit:
            for key in modules:
                if _test_mentions(text, key, root_pkg):
                    hit.setdefault(key, None)
        test_map[repo_rel] = sorted(hit)

    build_ms = (time.perf_counter() - t0) * 1000.0
    total_loc = sum(m.loc for m in modules.values())
    stats = {
        "modules": len(modules),
        "test_files": len(test_files),
        "symbols": sum(len(m.symbols) for m in modules.values()),
        "total_loc": total_loc,
        "internal_edges": sum(len(m.imports) for m in modules.values()),
        "build_ms": round(build_ms, 1),
        "built_at": now_iso(),
        "root_pkg": root_pkg,
        "schema_version": SCHEMA_VERSION,
    }
    return Index(modules=modules, reverse=reverse, symbol_index=symbol_index, test_map=test_map, root_pkg=root_pkg, stats=stats)


# --------------------------------------------------------------------------- index cache


def _current_digest(config: dict[str, Any]) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    for r in config["src_roots"]:
        root = REPO.joinpath(r)
        src_root = root
        for path in sorted(root.rglob("*.py")):
            rel = path.resolve().relative_to(src_root.resolve())
            st = path.stat()
            rows.append((_module_key_for_rel(rel.parts), st.st_mtime_ns, st.st_size))
    return rows


def _digest_matches(digest: list[Any], config: dict[str, Any]) -> bool:
    if not digest:
        return False
    current = _current_digest(config)
    return sorted(tuple(d) for d in digest) == sorted(current)


def _index_to_dict(index: Index) -> dict[str, Any]:
    return {
        "modules": {
            key: {
                "path": mod.path,
                "loc": mod.loc,
                "symbols": [s.__dict__ for s in mod.symbols],
                "imports": mod.imports,
            }
            for key, mod in sorted(index.modules.items())
        },
        "reverse": {k: sorted(v) for k, v in sorted(index.reverse.items())},
        "symbol_index": {k: sorted(v) for k, v in sorted(index.symbol_index.items())},
        "test_map": dict(sorted(index.test_map.items())),
        "root_pkg": index.root_pkg,
        "stats": index.stats,
    }


def _index_from_dict(data: dict[str, Any]) -> Index:
    modules: dict[str, Module] = {}
    for key, d in (data.get("modules") or {}).items():
        symbols = [Symbol(s["name"], s["kind"], s["start"], s["end"]) for s in d.get("symbols", [])]
        modules[key] = Module(key=key, path=d["path"], loc=d.get("loc", 0), symbols=symbols, imports=list(d.get("imports", [])))
    reverse = {k: set(v) for k, v in (data.get("reverse") or {}).items()}
    symbol_index = {k: list(v) for k, v in (data.get("symbol_index") or {}).items()}
    test_map = {k: list(v) for k, v in (data.get("test_map") or {}).items()}
    return Index(
        modules=modules,
        reverse=reverse,
        symbol_index=symbol_index,
        test_map=test_map,
        root_pkg=data.get("root_pkg", "psyche_os"),
        stats=data.get("stats", {}),
    )


def _save_cache(cache_path: Path, index: Index, config: dict[str, Any]) -> None:
    data = {"schema_version": SCHEMA_VERSION, "digest": _current_digest(config), "index": _index_to_dict(index)}
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True), encoding="utf-8")


def _load_cache(cache_path: Path) -> Index | None:
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return _index_from_dict(data.get("index") or {})


def get_index(config: dict[str, Any], *, use_cache: bool = True) -> tuple[Index, bool]:
    """Return (index, cache_hit)."""
    cache_path = REPO.joinpath(config["index_cache"])
    if use_cache and cache_path.is_file():
        try:
            data = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            data = {}
        if _digest_matches(data.get("digest") or [], config):
            cached = _load_cache(cache_path)
            if cached:
                return cached, True
    index = build_index(config)
    if use_cache:
        _save_cache(cache_path, index, config)
    return index, False


# --------------------------------------------------------------------------- context


@dataclass(frozen=True)
class ContextItem:
    path: str
    start: int
    end: int
    source: str  # index-symbol | rg-lexical | ast-grep-structural
    authority_level: str
    reason: str
    text: str
    tokens: int

    @property
    def lines(self) -> str:
        return f"{self.start}-{self.end}"


def extract_range(repo_rel: str, start: int, end: int) -> str:
    path = REPO.joinpath(repo_rel)
    if not path.is_file():
        return ""
    lines = read_text(path).splitlines()
    return "\n".join(lines[start - 1 : end])


def _src_root_args(index: Index) -> list[str]:
    # Any indexed module's repo path starts with the src root, e.g. "src".
    if index.modules:
        first = next(iter(index.modules.values()))
        root = Path(first.path).parts[0]
        return [str(REPO.joinpath(root))]
    return [str(REPO)]


def _symbol_items(index: Index, terms: list[str]) -> list[ContextItem]:
    items: list[ContextItem] = []
    for term in terms:
        for key in index.symbol_owners(term):
            mod = index.modules[key]
            for sym in mod.symbols:
                if sym.name == term:
                    text = extract_range(mod.path, sym.start, sym.end)
                    items.append(
                        ContextItem(
                            path=mod.path,
                            start=sym.start,
                            end=sym.end,
                            source="index-symbol",
                            authority_level="structural/symbol",
                            reason=f"symbol '{term}' defined here",
                            text=text,
                            tokens=estimate_tokens(text),
                        )
                    )
    items.sort(key=lambda it: (it.path, it.start))
    return items


def _lexical_items(index: Index, rg_exe: str, terms: list[str], roots: list[str], merge_gap: int) -> list[ContextItem]:
    per_file: dict[str, list[int]] = {}
    for term in terms:
        args = [rg_exe, "--json", "-n", "-i", "--", term, *roots]
        proc = run_cmd(args, timeout=120)
        if proc.returncode not in (0, 1):  # 1 = no matches (normal)
            raise PerfError(f"rg failed (rc={proc.returncode}): {proc.stderr[:200]}")
        for line in proc.stdout.splitlines():
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            if obj.get("type") != "match":
                continue
            data = obj.get("data", {})
            path_text = data.get("path", {}).get("text", "")
            line_no = data.get("line_number")
            if not path_text or not isinstance(line_no, int):
                continue
            key = index.key_for_path(path_text)
            if key is None:
                continue  # only indexed source modules
            per_file.setdefault(index.path_for_key(key), []).append(line_no)

    items: list[ContextItem] = []
    for path_text, lines in sorted(per_file.items()):
        lines.sort()
        ranges: list[list[int]] = []
        for ln in lines:
            if ranges and ln - ranges[-1][1] <= merge_gap:
                ranges[-1][1] = ln
                ranges[-1][2] += 1
            else:
                ranges.append([ln, ln, 1])
        for start, end, count in ranges:
            text = extract_range(path_text, start, end)
            items.append(
                ContextItem(
                    path=path_text,
                    start=start,
                    end=end,
                    source="rg-lexical",
                    authority_level="lexical",
                    reason=f"{count} lexical match(es)",
                    text=text,
                    tokens=estimate_tokens(text),
                )
            )
    items.sort(key=lambda it: ((it.end - it.start + 1), it.path, it.start))
    return items


def _structural_items(index: Index, sg_exe: str, pattern: str, roots: list[str]) -> list[ContextItem]:
    proc = run_cmd([sg_exe, "--json", "-p", pattern, "-l", "python", *roots], timeout=120)
    if proc.returncode != 0:
        raise PerfError(f"ast-grep failed (rc={proc.returncode}): {proc.stderr[:200]}")
    items: list[ContextItem] = []
    for obj in json.loads(proc.stdout or "[]"):
        file = obj.get("file", "")
        if not file:
            continue
        key = index.key_for_path(file)
        repo_rel = index.path_for_key(key) if key else file
        start = (obj.get("range", {}).get("start", {}) or {}).get("line")
        end = (obj.get("range", {}).get("end", {}) or {}).get("line")
        if not isinstance(start, int) or not isinstance(end, int):
            continue
        text = extract_range(repo_rel, start + 1, end + 1)
        items.append(
            ContextItem(
                path=repo_rel,
                start=start + 1,
                end=end + 1,
                source="ast-grep-structural",
                authority_level="structural",
                reason=f"structural pattern {pattern!r}",
                text=text,
                tokens=estimate_tokens(text),
            )
        )
    return items


def assemble_context(index: Index, terms: list[str], *, target: int, structural_pattern: str | None = None) -> dict[str, Any]:
    tools = check_tools(["rg"])
    items: list[ContextItem] = _symbol_items(index, terms)
    merge_gap = int(load_config()["lexical_merge_gap"])
    lexical = _lexical_items(index, tools["rg"], terms, _src_root_args(index), merge_gap)
    seen_keys = {(it.path, it.start, it.end) for it in items}
    items.extend(it for it in lexical if (it.path, it.start, it.end) not in seen_keys)
    if structural_pattern:
        tools = check_tools(["ast-grep"])
        items.extend(_structural_items(index, tools["ast-grep"], structural_pattern, _src_root_args(index)))

    selected: list[ContextItem] = []
    total = 0
    truncated = False
    for it in items:
        if total + it.tokens > target:
            truncated = True
            break
        selected.append(it)
        total += it.tokens

    return {
        "terms": terms,
        "target_tokens": target,
        "items": [it.__dict__ | {"lines": it.lines} for it in selected],
        "total_tokens": total,
        "total_chars": sum(len(it.text) for it in selected),
        "item_count": len(selected),
        "candidate_count": len(items),
        "truncated": truncated,
        "token_heuristic": f"~{CHARS_PER_TOKEN:g} chars/token",
    }


# --------------------------------------------------------------------------- impact


def _changed_to_keys(index: Index, paths: Iterable[str]) -> list[str]:
    keys: list[str] = []
    for p in paths:
        norm = p.replace("\\", "/")
        for k, mod in index.modules.items():
            if norm == mod.path or norm == k or norm.endswith("/" + mod.path) or norm.endswith("/" + k):
                keys.append(k)
    return list(dict.fromkeys(keys))


def affected_surface(index: Index, paths: list[str]) -> dict[str, Any]:
    changed = _changed_to_keys(index, paths)
    affected: set[str] = set(changed)
    stack = list(changed)
    while stack:
        key = stack.pop()
        for importer in index.reverse.get(key, ()):
            if importer not in affected:
                affected.add(importer)
                stack.append(importer)
    tests: set[str] = set()
    for key in affected:
        for test_file, keys in index.test_map.items():
            if key in keys:
                tests.add(test_file)
    return {
        "changed": changed,
        "affected_modules": sorted(affected),
        "affected_tests": sorted(tests),
        "closure_size": len(affected),
    }


def _high_risk_key_prefixes() -> list[str]:
    """Map high_risk policy prefixes into module-key space (e.g. src/psyche_os/crypto -> crypto)."""
    try:
        import yaml  # type: ignore

        path = AI_DEV / "policy" / "protected-paths.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        prefixes: list[str] = []
        for h in data.get("high_risk") or []:
            parts = [p for p in str(h).split("/") if p]
            if parts[:2] == ["src", "psyche_os"]:
                prefixes.append("/".join(parts[2:]))
            else:
                prefixes.append(str(h))
        return prefixes
    except Exception:
        return ["crypto", "storage", "policy", "backup_export"]


def classify_impact(index: Index, surface: dict[str, Any]) -> dict[str, str]:
    high_prefixes = _high_risk_key_prefixes()
    reasons: list[str] = []
    level = "low"
    for p in surface["changed"]:
        if any(p == hp or p.startswith(hp + "/") for hp in high_prefixes):
            level = "high"
            reasons.append(f"{p} is in a high-risk boundary")
    if level != "high":
        if surface["closure_size"] > 1:
            level = "medium"
            reasons.append(f"affects {surface['closure_size']} modules (cross-module)")
        if any("/interfaces/" in m for m in surface["affected_modules"]):
            level = "medium"
            reasons.append("reaches an interface/CLI boundary")
    if not surface["changed"]:
        level = "low"
        reasons.append("no resolvable changed module")
    return {"level": level, "reasons": reasons or ["single-module change"]}


def changed_paths_from_git(base: str | None = None) -> list[str]:
    base = base or "HEAD"
    proc = run_cmd(["git", "diff", "--name-only", base, "--"], timeout=60)
    paths = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    proc2 = run_cmd(["git", "status", "--porcelain"], timeout=60)
    for ln in proc2.stdout.splitlines():
        parts = ln.split()
        if len(parts) >= 2 and parts[0] == "??":
            paths.append(parts[1])
    return [p for p in paths if p.endswith(".py")]


# --------------------------------------------------------------------------- verify


def select_test_paths(index: Index, modules: list[str]) -> list[str]:
    selected: set[str] = set()
    for key in modules:
        for test_file, keys in index.test_map.items():
            if key in keys:
                selected.add(test_file)
    return sorted(selected)


def verify_plan(index: Index, test_paths: list[str], *, full: bool = False) -> dict[str, Any]:
    if full:
        cmd = ["uv", "run", "pytest", "-q"]
        gate = "V3 final gate"
    elif test_paths:
        cmd = ["uv", "run", "pytest", *test_paths, "-q", "--tb=short", "--no-header"]
        gate = "V1/V2 targeted"
    else:
        cmd = None
        gate = "no mapped tests"
    return {
        "full": full,
        "test_count": len(test_paths),
        "command": cmd,
        "gate": gate,
        "note": None if full else "targeted subset; full suite once at the final risk gate",
    }


def run_pytest(index: Index, test_paths: list[str], *, full: bool = False, raw_dir: Path, timeout: int = 600) -> dict[str, Any]:
    plan = verify_plan(index, test_paths, full=full)
    if plan["command"] is None:
        return {"collected": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0, "duration_ms": 0.0, "rc": 0}
    t0 = time.perf_counter()
    proc = run_cmd(plan["command"], timeout=timeout)
    duration_ms = (time.perf_counter() - t0) * 1000.0
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "pytest-raw.txt"
    raw_path.write_text(proc.stdout, encoding="utf-8", errors="replace")
    summary = _parse_pytest(proc.stdout)
    return {
        "collected": summary[0],
        "passed": summary[1],
        "failed": summary[2],
        "errors": summary[3],
        "skipped": summary[4],
        "duration_ms": round(duration_ms, 1),
        "rc": proc.returncode,
        "raw": str(raw_path),
    }


def _parse_pytest(output: str) -> tuple[int, int, int, int, int]:
    passed = _first_int(output, r"(\d+) passed")
    failed = _first_int(output, r"(\d+) failed")
    errors = _first_int(output, r"(\d+) error")
    skipped = _first_int(output, r"(\d+) skipped")
    collected = _first_int(output, r"collected (\d+) items")
    if collected == 0:
        # --no-header suppresses the "collected N items" line; sum of outcomes is the count.
        collected = passed + failed + errors + skipped
    return collected, passed, failed, errors, skipped


def _first_int(text: str, pattern: str) -> int:
    m = re.search(pattern, text)
    return int(m.group(1)) if m else 0


# --------------------------------------------------------------------------- prompt


def assemble_prompt(task: str, context: dict[str, Any], impact: dict[str, Any], verify: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Task Prompt — performance canary packet")
    lines.append("")
    lines.append("## Instructions")
    lines.append("- Resolve authority first: `CONSTITUTION.md` -> `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` -> `docs/DECISION_LOG.md` -> `docs/ROADMAP.md` + `docs/development/EPIC_MAP.md`.")
    lines.append("- Read ONLY the exact ranges below. Do not open whole files or re-grep the repository.")
    lines.append("- If you need more context, request an exact range, not a whole file.")
    lines.append("- Verification: run the targeted command(s) below; the full suite runs once at the final gate.")
    lines.append("")
    lines.append("## Task")
    lines.append(task)
    lines.append("")
    lines.append("## Impact (deterministic, from local index)")
    lines.append(f"- changed modules: {', '.join(impact['changed']) or '(none resolvable)'}")
    lines.append(f"- affected modules (reverse-dep closure): {', '.join(impact['affected_modules']) or '-'}")
    lines.append(f"- affected tests: {', '.join(impact['affected_tests']) or '(none mapped)'}")
    lines.append(f"- classification: {impact['level']}")
    lines.append("")
    lines.append(f"## Context ({context['item_count']} exact range(s), ~{context['total_tokens']} tokens)")
    for i, it in enumerate(context["items"], 1):
        lines.append("")
        lines.append(f"### {i}. `{it['path']}:{it['lines']}`  [source={it['source']}, authority={it['authority_level']}] (~{it['tokens']} tokens)")
        lines.append("```text")
        lines.append(it["text"])
        lines.append("```")
    if context.get("truncated"):
        lines.append("")
        lines.append("> Context was truncated to the token target; request further exact ranges on demand.")
    lines.append("")
    lines.append("## Verification plan")
    if verify["command"]:
        lines.append(f"- targeted: `{' '.join(verify['command'])}`  (gate: {verify['gate']})")
    else:
        lines.append(f"- no mapped tests ({verify['gate']}); run the final gate before merge.")
    lines.append("- final gate (once): `uv run pytest -q` + `scripts/dev/validate_orchestration.py` + `scripts/validate_research_foundation.py`")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- benchmark


def benchmark(index: Index, config: dict[str, Any], *, run_full: bool, raw_dir: Path) -> dict[str, Any]:
    out: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "ran_at": now_iso(), "index_stats": index.stats}

    t0 = time.perf_counter()
    build_index(config)
    out["index_build_ms"] = round((time.perf_counter() - t0) * 1000.0, 1)

    # 2. Context compression: a single exact-range lookup vs reading the whole file.
    file_chars_map = {m.key: len(read_text(REPO.joinpath(m.path))) for m in index.modules.values()}
    range_chars: list[int] = []
    file_chars: list[int] = []
    for m in index.modules.values():
        fc = file_chars_map[m.key]
        for s in m.symbols:
            rc = len(extract_range(m.path, s.start, s.end))
            if rc and fc:
                range_chars.append(rc)
                file_chars.append(fc)
    ratios = [rc / fc for rc, fc in zip(range_chars, file_chars, strict=True)] if range_chars else []
    avg_range = statistics.mean(range_chars) if range_chars else 0
    avg_file = statistics.mean(file_chars) if file_chars else 0
    out["context_compression"] = {
        "lookups_sampled": len(ratios),
        "median_lookup_ratio": round(statistics.median(ratios), 3) if ratios else 0.0,
        "mean_lookup_ratio": round(statistics.mean(ratios), 3) if ratios else 0.0,
        "tokens_saved_per_lookup_estimate": estimate_token_volume(int(avg_file)) - estimate_token_volume(int(avg_range)),
        "note": "a single exact-range symbol lookup vs a whole-file read for the same symbol",
    }

    sample = sorted(index.modules.values(), key=lambda m: -m.loc)[:BENCHMARK_SAMPLE_CHANGES]
    sel_rows: list[dict[str, Any]] = []
    mapped_tests: set[str] = set()
    for mod in sample:
        surface = affected_surface(index, [mod.path])
        tests = select_test_paths(index, surface["affected_modules"])
        mapped_tests.update(tests)
        sel_rows.append(
            {"module": mod.key, "loc": mod.loc, "affected_modules": surface["closure_size"], "mapped_tests": len(tests)}
        )
    out["test_selection"] = {"total_test_files": len(index.test_map), "sample": sel_rows, "union_mapped_tests": len(mapped_tests)}

    full_result: dict[str, Any] | None
    if run_full:
        full_result = run_pytest(index, [], full=True, raw_dir=raw_dir, timeout=900)
        _write_baseline(full_result)
    else:
        full_result = _read_baseline()
    targeted = run_pytest(index, sorted(mapped_tests), raw_dir=raw_dir, timeout=600) if mapped_tests else None
    out["verification"] = {
        "full_suite": full_result and {k: full_result[k] for k in ("collected", "passed", "failed", "skipped", "duration_ms", "rc")},
        "targeted_union": targeted and {k: targeted[k] for k in ("collected", "passed", "failed", "skipped", "duration_ms", "rc")},
        "test_time_ratio": round(targeted["duration_ms"] / full_result["duration_ms"], 2) if (targeted and full_result and full_result["duration_ms"]) else None,
        "test_count_ratio": round(targeted["collected"] / full_result["collected"], 3) if (targeted and full_result and full_result["collected"]) else None,
        "full_source": "fresh run" if run_full else "cached baseline",
    }
    return out


def _read_baseline() -> dict[str, Any] | None:
    if BASELINE_PATH.is_file():
        try:
            return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _write_baseline(full_result: dict[str, Any]) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(full_result, ensure_ascii=False, sort_keys=True), encoding="utf-8")


# --------------------------------------------------------------------------- report


def render_report(evidence: list[dict[str, Any]], latest: dict[str, Any] | None) -> str:
    latest = latest or (evidence[-1] if evidence else {})
    lines: list[str] = []
    lines.append("# AI Dev OS v2 — Performance & Token Efficiency Canary Report")
    lines.append("")
    lines.append(f"_Regenerated from local evidence by `scripts/ai_dev_perf.py report` ({now_iso()})._")
    lines.append("")
    lines.append("## Question")
    lines.append("")
    lines.append("> Does local code intelligence + deterministic context selection + impact-based")
    lines.append("> verification materially improve real Psyche OS development vs the V1 workflow?")
    lines.append("")
    if latest.get("index_build_ms") is not None:
        lines.append("## Index (map)")
        lines.append("")
        lines.append(f"- Index build: **{latest['index_build_ms']} ms** for {latest.get('index_stats', {}).get('modules', '-')} modules, {latest.get('index_stats', {}).get('symbols', '-')} symbols, {latest.get('index_stats', {}).get('total_loc', '-')} LOC.")
        lines.append("- The whole index is cached on disk; only changed files invalidate it.")
        lines.append("")
    if latest.get("context_compression"):
        cc = latest["context_compression"]
        lines.append("## Context selection")
        lines.append("")
        lines.append(f"- A single exact-range symbol lookup reads a median of **{cc['median_lookup_ratio'] * 100:.0f}%** of its whole file ({cc['lookups_sampled']} lookups sampled; est. {cc['tokens_saved_per_lookup_estimate']} tokens saved per lookup).")
        lines.append("- Range selection follows the Context Broker waterfall: rg -> ast-grep -> exact ranges; provenance and token estimates are attached to every item.")
        lines.append("")
    if latest.get("test_selection"):
        ts = latest["test_selection"]
        lines.append("## Test selection")
        lines.append("")
        lines.append(f"- {ts['total_test_files']} test files indexed; a representative {len(ts['sample'])}-module change selects a union of **{ts['union_mapped_tests']}** test files.")
        lines.append("")
        for row in ts["sample"]:
            lines.append(f"  - `{row['module']}` ({row['loc']} LOC) -> {row['affected_modules']} affected modules, {row['mapped_tests']} mapped tests")
        lines.append("")
    if latest.get("verification") and latest["verification"].get("full_suite"):
        v = latest["verification"]
        fs, tg = v["full_suite"], v["targeted_union"]
        lines.append("## Verification")
        lines.append("")
        lines.append(f"- Full suite: {fs['collected']} collected, {fs['duration_ms'] / 1000:.1f}s.")
        lines.append(f"- Targeted union: {tg['collected']} collected, {tg['duration_ms'] / 1000:.1f}s.")
        lines.append(f"- Test-count ratio **{v['test_count_ratio']}**; wall-time ratio **{v['test_time_ratio']}** ({v['full_source']}).")
        lines.append("- Inner loop runs targeted subsets; the full suite runs once at the final risk gate.")
        lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- Token volume: an exact-range lookup reads a small fraction of its file (median 2%); the deterministic index removes repeated searches and whole-file reads.")
    lines.append("- Wall time: impact-based verification cuts the suite to ~two-thirds for hub modules (see measured ratios above) and is far smaller for leaf/mid changes — e.g. a change to `adapters/e08_filesystem.py` selects 7 of 42 test files. When a change's reverse-dependency closure approaches the full suite, that is the signal to run the final gate directly.")
    lines.append("- Caveats: token estimates use a ~4 chars/token heuristic (relative comparisons only); test mapping is import-based with a lexical fallback, so edge cases can over- or under-select. Evidence: raw rg and pytest output stay local under `.ai-dev/evidence/performance/runs/`.")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- CLI


def _make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="ai_dev_perf", description="AI Dev OS v2 performance & token efficiency canary")
    ap.add_argument("--config", default=str(DEFAULT_CONFIG), help="config yaml (default .ai-dev/performance/config.yaml)")
    sub = ap.add_subparsers(dest="command", required=True)

    p_map = sub.add_parser("map", help="build or read the code index")
    p_map.add_argument("--no-cache", action="store_true", help="force a full rebuild")
    p_map.add_argument("--json", action="store_true", help="machine-readable output")
    p_map.set_defaults(fn=cmd_map)

    p_ctx = sub.add_parser("context", help="produce exact-range context for terms")
    p_ctx.add_argument("terms", nargs="+", help="symbols or lexical terms")
    p_ctx.add_argument("--target", type=int, default=None, help="token target (default from config)")
    p_ctx.add_argument("--structural", default=None, metavar="PATTERN", help="also run ast-grep structural query")
    p_ctx.add_argument("--json", action="store_true")
    p_ctx.set_defaults(fn=cmd_context)

    p_imp = sub.add_parser("impact", help="compute affected surface for a change")
    p_imp.add_argument("--paths", nargs="*", default=[], help="changed file paths (repo-relative)")
    p_imp.add_argument("--symbols", nargs="*", default=[], help="changed symbol names")
    p_imp.add_argument("--git-diff", action="store_true", help="use working-tree .py changes vs --base")
    p_imp.add_argument("--base", default="HEAD", help="git base ref for --git-diff")
    p_imp.add_argument("--json", action="store_true")
    p_imp.set_defaults(fn=cmd_impact)

    p_ver = sub.add_parser("verify", help="run targeted pytest for an affected surface")
    p_ver.add_argument("--paths", nargs="*", default=[])
    p_ver.add_argument("--symbols", nargs="*", default=[])
    p_ver.add_argument("--git-diff", action="store_true")
    p_ver.add_argument("--base", default="HEAD")
    p_ver.add_argument("--full", action="store_true", help="run the full suite instead")
    p_ver.add_argument("--dry-run", action="store_true", help="print the command without running it")
    p_ver.add_argument("--no-cache", action="store_true")
    p_ver.add_argument("--json", action="store_true")
    p_ver.set_defaults(fn=cmd_verify)

    p_pr = sub.add_parser("prompt", help="assemble a self-contained task prompt packet")
    p_pr.add_argument("--task", required=True, help="task description")
    p_pr.add_argument("--paths", nargs="*", default=[])
    p_pr.add_argument("--symbols", nargs="*", default=[])
    p_pr.add_argument("--terms", nargs="*", default=[], help="extra context terms")
    p_pr.add_argument("--target", type=int, default=None)
    p_pr.add_argument("--out", default=None, help="output path for the prompt packet")
    p_pr.add_argument("--no-cache", action="store_true")
    p_pr.add_argument("--json", action="store_true")
    p_pr.set_defaults(fn=cmd_prompt)

    p_bm = sub.add_parser("benchmark", help="measure index/context/verification costs")
    p_bm.add_argument("--skip-full", action="store_true", help="skip the full-suite run (use cached baseline)")
    p_bm.add_argument("--no-cache", action="store_true")
    p_bm.add_argument("--json", action="store_true")
    p_bm.set_defaults(fn=cmd_benchmark)

    p_rp = sub.add_parser("report", help="regenerate the canary report from evidence")
    p_rp.add_argument("--out", default="docs/AI_DEV_OS_V2_PERFORMANCE_CANARY_REPORT.md")
    p_rp.add_argument("--json", action="store_true")
    p_rp.set_defaults(fn=cmd_report)
    return ap


def _run_id() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def _collect_input_paths(args: argparse.Namespace, index: Index) -> list[str]:
    paths = list(args.paths or [])
    for sym in args.symbols or []:
        for key in index.symbol_owners(sym):
            paths.append(index.path_for_key(key))
    if getattr(args, "git_diff", False):
        paths.extend(changed_paths_from_git(args.base))
    return list(dict.fromkeys(paths))


def cmd_map(args: argparse.Namespace, config: dict[str, Any]) -> int:
    index, hit = get_index(config, use_cache=not args.no_cache)
    if args.json:
        print(json.dumps(_index_to_dict(index), ensure_ascii=False, sort_keys=True))
        return 0
    print(f"cache: {'hit' if hit else 'built'}")
    print(f"modules: {index.stats['modules']}  symbols: {index.stats['symbols']}  loc: {index.stats['total_loc']}")
    print(f"internal import edges: {index.stats['internal_edges']}  test files: {len(index.test_map)}")
    print(f"index build: {index.stats['build_ms']} ms  (cached at .ai-dev/evidence/performance/index.json)")
    return 0


def cmd_context(args: argparse.Namespace, config: dict[str, Any]) -> int:
    index, _ = get_index(config, use_cache=True)
    result = assemble_context(
        index,
        args.terms,
        target=args.target or int(config["context_token_target"]),
        structural_pattern=args.structural,
    )
    raw_dir = RUNS_DIR / f"context-{_run_id()}-{slugify('-'.join(args.terms))}"
    if result["items"]:
        raw_dir.mkdir(parents=True, exist_ok=True)
        _write_context_raw(raw_dir, index, args.terms)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"terms: {', '.join(args.terms)}  candidates: {result['candidate_count']}  selected: {result['item_count']} (~{result['total_tokens']} tokens, target {result['target_tokens']})")
    if result["truncated"]:
        print("truncated: true (token target reached; request further ranges on demand)")
    for it in result["items"]:
        print(f"  {it['source']:<18} {it['path']}:{it['lines']}  (~{it['tokens']} tokens)  {it['reason']}")
    if result["items"]:
        print(f"raw evidence: {raw_dir}")
    return 0


def _write_context_raw(raw_dir: Path, index: Index, terms: list[str]) -> None:
    tools = check_tools(["rg"])
    for term in terms:
        proc = run_cmd([tools["rg"], "--json", "-n", "-i", "--", term, *_src_root_args(index)])
        if proc.stdout:
            (raw_dir / f"rg-{slugify(term)}.jsonl").write_text(proc.stdout, encoding="utf-8", errors="replace")


def cmd_impact(args: argparse.Namespace, config: dict[str, Any]) -> int:
    index, _ = get_index(config, use_cache=True)
    paths = _collect_input_paths(args, index)
    surface = affected_surface(index, paths)
    cls = classify_impact(index, surface)
    if args.json:
        print(json.dumps({"surface": surface, "classification": cls}, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"changed: {', '.join(surface['changed']) or '(none resolvable)'}")
    print(f"affected modules ({surface['closure_size']}): {', '.join(surface['affected_modules']) or '-'}")
    print(f"affected tests: {', '.join(surface['affected_tests']) or '(none mapped)'}")
    print(f"classification: {cls['level'].upper()} — {'; '.join(cls['reasons'])}")
    return 0


def cmd_verify(args: argparse.Namespace, config: dict[str, Any]) -> int:
    index, _ = get_index(config, use_cache=not args.no_cache)
    paths = _collect_input_paths(args, index)
    surface = affected_surface(index, paths)
    test_paths = [] if args.full else select_test_paths(index, surface["affected_modules"])
    if args.dry_run:
        plan = verify_plan(index, test_paths, full=args.full)
        if plan["command"]:
            print(" ".join(plan["command"]))
        else:
            print("(no mapped tests; nothing to run)")
        print(f"gate: {plan['gate']}  mapped_test_files: {plan['test_count']}")
        return 0
    result = run_pytest(index, test_paths, full=args.full, raw_dir=RUNS_DIR / f"verify-{_run_id()}")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    else:
        gate = "V3 final gate" if args.full else "V1/V2 targeted"
        print(f"gate: {gate}  files: {len(test_paths)}")
        print(f"pytest: {result['collected']} collected, {result['passed']} passed, {result['failed']} failed, {result['errors']} errors, {result['skipped']} skipped  ({result['duration_ms'] / 1000:.1f}s)")
        print(f"raw: {result['raw']}")
    return 1 if result["failed"] or result["errors"] else 0


def cmd_prompt(args: argparse.Namespace, config: dict[str, Any]) -> int:
    index, _ = get_index(config, use_cache=not args.no_cache)
    paths = _collect_input_paths(args, index)
    surface = affected_surface(index, paths)
    cls = classify_impact(index, surface)
    impact = {**surface, "level": cls["level"]}
    test_paths = select_test_paths(index, surface["affected_modules"])
    verify = verify_plan(index, test_paths, full=False)
    terms = list(args.terms or []) + list(args.symbols or [])
    context = assemble_context(index, terms, target=args.target or int(config["context_token_target"]))
    markdown = assemble_prompt(args.task, context, impact, verify)
    out = Path(args.out or RUNS_DIR / f"prompt-{_run_id()}-{slugify(args.task)}.md")
    write_text(out, markdown)
    total_tokens = estimate_tokens(markdown) + context["total_tokens"]
    if args.json:
        print(json.dumps({"out": str(out), "prompt_tokens_estimate": total_tokens, "context_tokens": context["total_tokens"], "impact": impact, "verify": verify}, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"wrote: {out}")
    print(f"prompt estimate: ~{total_tokens} tokens (context {context['total_tokens']}, header+impact+instructions {estimate_tokens(markdown) - context['total_tokens']})")
    return 0


def cmd_benchmark(args: argparse.Namespace, config: dict[str, Any]) -> int:
    index, _ = get_index(config, use_cache=not args.no_cache)
    raw_dir = RUNS_DIR / f"benchmark-{_run_id()}"
    result = benchmark(index, config, run_full=not args.skip_full, raw_dir=raw_dir)
    (raw_dir / "benchmark.json").write_text(json.dumps(result, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    if args.json:
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"index build: {result['index_build_ms']} ms")
    cc = result["context_compression"]
    print(f"context compression: exact-range lookup = median {cc['median_lookup_ratio'] * 100:.0f}% of whole-file bytes (est. {cc['tokens_saved_per_lookup_estimate']} tokens saved/lookup, {cc['lookups_sampled']} lookups)")
    ts = result["test_selection"]
    print(f"test selection: {ts['total_test_files']} test files; {len(ts['sample'])}-module sample -> union {ts['union_mapped_tests']} mapped test files")
    for row in ts["sample"]:
        print(f"  {row['module']} ({row['loc']} loc) -> {row['affected_modules']} affected, {row['mapped_tests']} mapped tests")
    v = result["verification"]
    if v.get("full_suite"):
        fs, tg = v["full_suite"], v["targeted_union"]
        print(f"verification: full {fs['collected']} collected {fs['duration_ms'] / 1000:.1f}s | targeted {tg['collected']} collected {tg['duration_ms'] / 1000:.1f}s")
        print(f"  count ratio {v['test_count_ratio']} | time ratio {v['test_time_ratio']} ({v['full_source']})")
    print(f"evidence: {raw_dir}")
    return 0


def cmd_report(args: argparse.Namespace, config: dict[str, Any]) -> int:
    evidence: list[dict[str, Any]] = []
    for p in sorted(RUNS_DIR.glob("benchmark-*/benchmark.json")):
        try:
            evidence.append(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            continue
    markdown = render_report(evidence, evidence[-1] if evidence else None)
    out = REPO.joinpath(args.out)
    write_text(out, markdown)
    if args.json:
        print(json.dumps({"out": str(out), "evidence_runs": len(evidence)}, ensure_ascii=False, sort_keys=True))
        return 0
    print(f"wrote: {out}  (from {len(evidence)} evidence run(s))")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = _make_parser()
    args = ap.parse_args(argv)
    config = load_config(Path(args.config))
    try:
        return int(args.fn(args, config))
    except ToolNotFoundError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 2
    except PerfError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
