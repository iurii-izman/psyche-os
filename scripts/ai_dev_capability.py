#!/usr/bin/env python3
"""AI Dev OS v2 — JIT Capability Launcher (Acceleration Wave 1).

A tiny generic local launcher over the existing Capability Registry
(`.ai-dev/capabilities/registry.yaml`). It starts an external tool just-in-time,
captures bounded evidence, and exits. No daemon, no always-on process, no plugin
framework, no new telemetry system.

Commands:
  list                 table of registered capabilities
  info <name>          full registry record for one capability
  doctor <name>        verify availability + record the installed version
  run <name> [-- args] invoke the capability JIT and capture evidence

States are honored: DISABLED and QUARANTINED refuse to run; LAB runs only on
explicit invocation (which `run` is). There is no automatic LAB -> CORE
transition. A capability without a resolvable command is not directly invocable.

Run:  uv run python scripts/ai_dev_capability.py <command> [options]
"""
from __future__ import annotations

import argparse
import contextlib
from datetime import UTC, datetime
import glob
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any

import yaml

VERSION = "0.1.0"
REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / ".ai-dev" / "capabilities" / "registry.yaml"
RUNS_DIR = REPO / ".ai-dev" / "evidence" / "performance" / "runs" / "capability-runs"

REFUSED_STATES = {"disabled", "quarantined"}


class CapabilityError(Exception):
    """A deterministic launcher failure (unknown capability, refused, missing tool)."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _run_id() -> str:
    return datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")


def load_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    p = Path(path) if path else REGISTRY
    if not p.is_file():
        raise CapabilityError(f"capability registry not found: {p}")
    data = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    caps = data.get("capabilities") or {}
    if not isinstance(caps, dict):
        raise CapabilityError(f"registry {p} has no capabilities map")
    return caps


def find_exe(name: str) -> str | None:
    """Resolve a binary by PATH, then winget user-package dir (PATH may lag)."""
    p = shutil.which(name)
    if p:
        return p
    hits = glob.glob(f"C:/Users/*/AppData/Local/Microsoft/WinGet/Packages/*/{name}.exe")
    if hits:
        return hits[0]
    if name == "ast-grep":
        p = shutil.which("sg")
        if p:
            return p
    return None


def _resolve_command(record: dict[str, Any], name: str) -> list[str] | None:
    """Turn a registry `command` into an argv list, resolving bare binaries."""
    cmd = record.get("command")
    if not cmd:
        return None
    parts = shlex.split(cmd)
    if not parts:
        return None
    if parts[0] == "uv":
        # e.g. "uv run python scripts/..." — run via the project environment.
        return parts
    if len(parts) == 1:
        exe = find_exe(parts[0])
        if not exe:
            raise CapabilityError(f"capability {name!r}: binary {parts[0]!r} not found (is it installed?)")
        return [exe]
    return parts


def _probe_version(record: dict[str, Any], name: str, resolved: list[str] | None) -> str | None:
    check = record.get("check")
    argv: list[str] | None
    if check:
        argv = shlex.split(check)
        if argv and argv[0] != "uv":
            exe = find_exe(argv[0])
            argv = [exe, *argv[1:]] if exe else None
    elif resolved:
        argv = [*resolved, "--version"]
    else:
        return None
    if not argv:
        return None
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(REPO),
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    out = (proc.stdout or proc.stderr or "").strip().splitlines()
    return out[0] if out else None


def cmd_list(args: argparse.Namespace) -> int:
    caps = load_registry()
    rows = sorted(caps.items())
    if args.json:
        print(json.dumps({"capabilities": caps}, ensure_ascii=False, sort_keys=True))
        return 0
    width = max(len(n) for n, _ in rows) + 2
    print(f"{'name':<{width}}{'state':<13}{'type':<22}installed")
    for name, rec in rows:
        installed = "yes" if rec.get("installed") or rec.get("command") else "no"
        print(f"{name:<{width}}{rec.get('state', '-'):<13}{rec.get('type', '-'):<22}{installed}")
    return 0


def cmd_info(args: argparse.Namespace) -> int:
    caps = load_registry()
    name = args.name
    if name not in caps:
        print(f"unknown capability: {name}", file=sys.stderr)
        return 1
    rec = {"name": name, **caps[name]}
    if args.json:
        print(json.dumps(rec, ensure_ascii=False, sort_keys=True))
        return 0
    print(yaml.safe_dump(rec, sort_keys=False).rstrip())
    return 0


def cmd_doctor(args: argparse.Namespace) -> int:
    caps = load_registry()
    name = args.name
    if name not in caps:
        print(f"unknown capability: {name}", file=sys.stderr)
        return 1
    rec = caps[name]
    state = rec.get("state", "?")
    try:
        resolved = _resolve_command(rec, name)
    except CapabilityError as exc:
        print(f"[FAIL] {name}: {exc}")
        return 2
    version = _probe_version(rec, name, resolved)
    if version:
        print(f"[OK]   {name} ({state})  version: {version}")
        return 0
    if rec.get("installed") is False:
        print(f"[DEFER] {name} ({state}) — not installed (explicit LAB candidate)")
        return 0
    if resolved is None and rec.get("check"):
        print(f"[WARN] {name} ({state}) — no version probe; check present")
        return 0
    if resolved is None:
        print(f"[WARN] {name} ({state}) — no command/check; registry record only")
        return 0
    print(f"[FAIL] {name} ({state}) — command resolves but version probe failed")
    return 2


def _is_git_ref(tok: str) -> bool:
    proc = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", tok],
        capture_output=True,
        timeout=30,
        cwd=str(REPO),
        check=False,
    )
    return proc.returncode == 0


def _materialize_tree(sha: str, dest: Path) -> None:
    """Extract a git tree into dest (no .git metadata)."""
    proc = subprocess.run(
        ["git", "archive", "--format=tar", sha],
        capture_output=True,
        timeout=300,
        cwd=str(REPO),
        check=False,
    )
    if proc.returncode != 0:
        raise CapabilityError(f"git archive {sha} failed (rc={proc.returncode}): {proc.stderr.decode(errors='replace')[:200]}")
    tar = dest / ".tree.tar"
    tar.write_bytes(proc.stdout)
    ext = subprocess.run(["tar", "-xf", str(tar), "-C", str(dest)], capture_output=True, timeout=120, cwd=str(REPO), check=False)
    tar.unlink(missing_ok=True)
    if ext.returncode != 0:
        raise CapabilityError(f"tar extract {sha} failed (rc={ext.returncode}): {ext.stderr.decode(errors='replace')[:200]}")


def _build_argv(name: str, record: dict[str, Any], args: list[str]) -> list[str]:
    """Build the final subprocess argv from the registry command + user args."""
    resolved = _resolve_command(record, name)
    if resolved is None:
        if record.get("installed") is False:
            raise CapabilityError(f"capability {name!r} is not installed (explicit {record.get('state', 'lab')} candidate)")
        raise CapabilityError(f"capability {name!r} is not directly invocable (no command); use its documented integration instead")
    return resolved + args


def _prune_tree(root: Path, keep: list[str]) -> None:
    """Keep only the requested repo-relative paths in a materialized tree."""
    keep_set = {p.replace("\\", "/").lstrip("/") for p in keep}
    for p in list(root.rglob("*")):
        rel = p.relative_to(root).as_posix()
        if p.is_dir():
            continue
        if rel not in keep_set:
            p.unlink(missing_ok=True)
    # Drop now-empty directories (deepest first).
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), key=lambda x: -len(x.parts)):
        with contextlib.suppress(OSError):
            d.rmdir()


def _run_difft_git(argv0: list[str], sha1: str, sha2: str | None, extra: list[str], *, timeout: int) -> subprocess.CompletedProcess[str]:
    """difftastic adapter: materialize two sides and diff the directories.

    difftastic accepts paths, not git refs, so the repo-native `--git <sha1> <sha2>`
    form materializes both trees and runs `difft <dir1> <dir2>`. A single ref
    (`--git <sha1>`) diffs that tree against the current working tree (tracked
    files only). Optional trailing repo-relative paths limit the comparison.
    """
    td = Path(tempfile.mkdtemp(prefix="difft-git-"))
    try:
        t1, t2 = td / "old", td / "new"
        t1.mkdir()
        t2.mkdir()
        _materialize_tree(sha1, t1)
        if sha2 is not None:
            _materialize_tree(sha2, t2)
        else:
            _working_tree(t2, extra)
        if extra:
            _prune_tree(t1, extra)
            _prune_tree(t2, extra)
        argv = [*argv0, str(t1), str(t2)]
        return subprocess.run(
            argv,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            cwd=str(REPO),
            check=False,
        )
    finally:
        shutil.rmtree(td, ignore_errors=True)


def _working_tree(dest: Path, paths: list[str]) -> None:
    """Copy tracked working-tree files into dest (respecting the path filter)."""
    proc = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        cwd=str(REPO),
        check=False,
    )
    if proc.returncode != 0:
        raise CapabilityError(f"git ls-files failed (rc={proc.returncode}): {proc.stderr[:200]}")
    keep = {p.replace("\\", "/").lstrip("/") for p in paths}
    for line in proc.stdout.splitlines():
        rel = line.replace("\\", "/")
        if keep and rel not in keep:
            continue
        src = REPO / rel
        if src.is_file():
            dst = dest / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dst)


def cmd_run(args: argparse.Namespace) -> int:
    caps = load_registry()
    name = args.name
    if name not in caps:
        print(f"unknown capability: {name}", file=sys.stderr)
        return 1
    rec = caps[name]
    state = rec.get("state", "?")
    if state in REFUSED_STATES:
        print(f"refused: capability {name!r} is {state.upper()} and may not run", file=sys.stderr)
        return 2
    if state == "lab":
        print(f"notice: {name!r} is LAB — running by explicit invocation only", file=sys.stderr)

    # difftastic repo-native git-tree adapter: `--git <sha1> [<sha2>] [paths...]`.
    git_adapter: list[str] | None = None
    real_extra = list(args.extra)
    if name == "difftastic" and real_extra and real_extra[0] == "--git":
        refs = real_extra[1:]
        if not refs:
            print("error: difftastic --git requires: <sha1> [<sha2>] [paths...] (one ref = diff vs working tree)", file=sys.stderr)
            return 1
        sha1 = refs[0]
        rest = refs[1:]
        git_adapter = [sha1]
        if rest and _is_git_ref(rest[0]):
            git_adapter.append(rest[0])
            rest = rest[1:]
        real_extra = rest

    try:
        # The git adapter consumes the trailing paths as tree filters, so the
        # base command is built without them.
        argv = _build_argv(name, rec, [] if git_adapter else real_extra)
    except CapabilityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    t0 = time.perf_counter()
    started_at = _now()
    try:
        if git_adapter:
            proc = _run_difft_git(argv, git_adapter[0], git_adapter[1] if len(git_adapter) > 1 else None, real_extra, timeout=args.timeout)
        else:
            proc = subprocess.run(
                argv,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=args.timeout,
                cwd=str(REPO),
                check=False,
            )
    except FileNotFoundError:
        print(f"error: command not found: {argv[0]!r}", file=sys.stderr)
        return 1
    except subprocess.TimeoutExpired:
        print(f"error: capability {name!r} timed out after {args.timeout}s", file=sys.stderr)
        return 1
    duration_ms = (time.perf_counter() - t0) * 1000.0

    out_dir = RUNS_DIR / f"{name}-{_run_id()}"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "stdout.txt").write_text(proc.stdout, encoding="utf-8", errors="replace")
    if proc.stderr:
        (out_dir / "stderr.txt").write_text(proc.stderr, encoding="utf-8", errors="replace")
    evidence = {
        "capability": name,
        "state": state,
        "version": rec.get("version"),
        "git_adapter": git_adapter,
        "started_at": started_at,
        "finished_at": _now(),
        "duration_ms": round(duration_ms, 1),
        "exit_code": proc.returncode,
        "output_bytes": len(proc.stdout.encode("utf-8", errors="replace")),
        "raw_evidence_path": str(out_dir / "stdout.txt"),
        "argv": argv,
    }
    (out_dir / "evidence.json").write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True), encoding="utf-8")

    # Bounded AI-facing summary.
    out_text = proc.stdout
    preview = out_text[: args.preview]
    git_note = ""
    if git_adapter:
        git_note = f"  [--git {git_adapter[0]}" + (f" {git_adapter[1]}]" if len(git_adapter) > 1 else " (working tree)]")
    print(f"capability: {name}  ({state})  version: {rec.get('version') or '?'}{git_note}")
    print(f"exit_code: {proc.returncode}  duration_ms: {round(duration_ms, 1)}  output_bytes: {evidence['output_bytes']}")
    if preview:
        print("--- output (bounded) ---")
        print(preview)
        if len(out_text) > args.preview:
            print(f"... [truncated {len(out_text) - args.preview} bytes; full raw evidence at {out_dir / 'stdout.txt'}]")
    print(f"raw_evidence: {out_dir / 'stdout.txt'}")
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="ai_dev_capability", description="AI Dev OS JIT capability launcher")
    ap.add_argument("--version", action="store_true", help="print launcher version and exit")
    sub = ap.add_subparsers(dest="command")

    p_list = sub.add_parser("list", help="table of registered capabilities")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(fn=cmd_list)

    p_info = sub.add_parser("info", help="full registry record for one capability")
    p_info.add_argument("name")
    p_info.add_argument("--json", action="store_true")
    p_info.set_defaults(fn=cmd_info)

    p_doc = sub.add_parser("doctor", help="verify availability + installed version")
    p_doc.add_argument("name")
    p_doc.set_defaults(fn=cmd_doctor)

    p_run = sub.add_parser("run", help="invoke a capability JIT and capture evidence")
    p_run.add_argument("name")
    p_run.add_argument("extra", nargs=argparse.REMAINDER, help="args after -- are passed to the capability")
    p_run.add_argument("--timeout", type=int, default=300, help="subprocess timeout seconds (default 300)")
    p_run.add_argument("--preview", type=int, default=4000, help="max stdout bytes echoed (default 4000)")
    p_run.set_defaults(fn=cmd_run)

    args = ap.parse_args(argv)
    if args.version:
        print(f"ai_dev_capability {VERSION}")
        return 0
    if not args.command:
        ap.print_help()
        return 1
    return args.fn(args)


if __name__ == "__main__":
    try:
        rc = main()
    except CapabilityError as exc:
        print(f"error: {exc}", file=sys.stderr)
        rc = 1
    except KeyboardInterrupt:
        sys.exit(130)
    if rc:
        sys.exit(rc)
