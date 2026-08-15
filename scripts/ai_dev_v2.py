#!/usr/bin/env python3
"""AI Dev OS v2.0 Control Canary — unified deterministic CLI/helper.

Components (all deterministic, no LLM call, no network call):
  A  model/provider attestation          -> `attest`
  B  versioned diagnostic ratchet        -> `ratchet capture|compare|rebaseline`
  D  authority / contract guard          -> `contract check`
  E  task / review packet compiler       -> `packet task|review`

Stdlib + PyYAML only (PyYAML is already a repository dependency). Run via
`uv run python scripts/ai_dev_v2.py <command>`.

Determinism contract: the packet renderer and attestation are pure functions of
their inputs; no timestamps or random IDs are injected into packet content.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tomllib
from typing import Any

try:  # PyYAML is a repository dependency; available under `uv run`.
    import yaml
except Exception:  # pragma: no cover - system python without the venv
    yaml = None

REPO = Path(__file__).resolve().parents[1]
AI_DEV = REPO / ".ai-dev"

ATTEST_STATUSES = (
    "CONFIRMED",
    "MAPPED_BY_PROVIDER_CONTRACT",
    "HARNESS_ONLY",
    "UNKNOWN",
    "CONFLICT",
)

RATCHET_TOOLS = ("ruff", "mypy")

CONFLICT_STATUSES = ("none", "unresolved", "resolved")

# Keys that must never appear in rendered packets (mirrors telemetry redaction).
_DROP_KEYS = {
    "raw_prompt", "prompt", "messages", "tool_output", "tool_input",
    "transcript", "chain_of_thought", "reasoning", "cot",
    "source_code_dump", "full_diff",
}
_SECRET_SUBSTR = (
    "api_key", "apikey", "token", "secret", "password", "passwd",
    "authorization", "auth", "cookie", "credential", "private_key",
    "client_secret", "access_key", "session_key",
)


def _sensitive_key(key: str) -> bool:
    k = str(key).lower().replace("-", "_")
    return k in _DROP_KEYS or any(s in k for s in _SECRET_SUBSTR)


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
def _yaml_load(path: Path) -> Any:
    if yaml is None:
        raise RuntimeError("PyYAML is required; run via `uv run python scripts/ai_dev_v2.py`")
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


def _yaml_dump(obj: Any) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML is required; run via `uv run python scripts/ai_dev_v2.py`")
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)


# --------------------------------------------------------------------------- #
# A. model / provider attestation
# --------------------------------------------------------------------------- #
def _read_provider_mapping(repo: Path) -> dict:
    path = repo / ".ai-dev" / "routing" / "provider-mapping.yaml"
    return _yaml_load(path) if path.is_file() else {}


def resolve_mapping(harness_model: str | None, provider: str | None, mapping: dict) -> dict | None:
    """Return the matched alias rule (dict) or None.

    A documented deterministic provider alias mapping supports
    MAPPED_BY_PROVIDER_CONTRACT; it is never stronger than CONFIRMED.
    """
    if not harness_model or not provider:
        return None
    providers = mapping.get("provider_mapping") or {}
    for key in (provider, None):
        if key is not None and key in providers:
            for alias in providers[key].get("aliases") or []:
                pattern = str(alias.get("pattern", ""))
                if pattern and pattern.lower() in harness_model.lower():
                    return alias
        if key is None:
            for pdata in providers.values():
                for alias in pdata.get("aliases") or []:
                    pattern = str(alias.get("pattern", ""))
                    if pattern and pattern.lower() in harness_model.lower():
                        return alias
    return None


def attest(
    requested_model: str | None = None,
    harness_reported_model: str | None = None,
    configured_provider: str | None = None,
    configured_model: str | None = None,
    direct_backend_provider: str | None = None,
    direct_backend_model: str | None = None,
    provider_mapping: dict | None = None,
    evidence_source: list[str] | None = None,
) -> dict:
    """Compute a bounded model/provider attestation without unsupported inference.

    - requested_model is NEVER copied into effective state.
    - A harness-reported model is harness evidence only (HARNESS_ONLY).
    - A deterministic provider mapping yields MAPPED_BY_PROVIDER_CONTRACT, never CONFIRMED.
    - Direct runtime backend evidence that contradicts configuration yields CONFLICT.
    - Direct runtime backend evidence that matches yields CONFIRMED.
    """
    evidence: list[str] = list(evidence_source or [])
    contradictions: list[str] = []
    status = "UNKNOWN"
    effective_backend_model: str | None = None
    observable = False
    mapping_summary: str | None = None

    if direct_backend_provider:
        observable = True
        effective_backend_model = direct_backend_model
        if configured_provider and direct_backend_provider.lower() != configured_provider.lower():
            contradictions.append(
                f"configured provider '{configured_provider}' conflicts with observed backend "
                f"'{direct_backend_provider}'"
            )
            status = "CONFLICT"
        else:
            status = "CONFIRMED"
    elif configured_provider and harness_reported_model:
        rule = resolve_mapping(harness_reported_model, configured_provider, provider_mapping or {})
        if rule:
            status = "MAPPED_BY_PROVIDER_CONTRACT"
            effective_backend_model = str(rule.get("maps_to", "")) or None
            mapping_summary = (
                f"{rule.get('pattern', '?')}* -> {rule.get('maps_to', '?')} "
                "(DeepSeek Anthropic-compatible contract)"
            )
        else:
            status = "HARNESS_ONLY"
    elif harness_reported_model:
        status = "HARNESS_ONLY"
    else:
        status = "UNKNOWN"

    if status in ("HARNESS_ONLY", "UNKNOWN"):
        effective_backend_model = "UNKNOWN"

    result: dict = {
        "configured_provider": configured_provider,
        "configured_model": configured_model,
        "requested_model": requested_model,
        "harness_reported_model": harness_reported_model,
        "provider_mapping": mapping_summary,
        "effective_backend_model": effective_backend_model,
        "effective_backend_observable": observable,
        "attestation_status": status,
        "evidence_source": evidence,
    }
    if contradictions:
        result["contradictions"] = contradictions
    return result


def _endpoint_host(url: str) -> str:
    """Bounded, non-secret endpoint identity (hostname only)."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            return "present (credentials redacted)"
        return parsed.hostname or "present"
    except Exception:
        return "present"


def gather_config_evidence(environ: dict | None = None) -> tuple[str | None, list[str]]:
    """Best-effort local configuration evidence (presence only, never secret values)."""
    env = environ if environ is not None else os.environ
    provider: str | None = None
    evidence: list[str] = []
    if "DEEPSEEK_API_KEY" in env:
        provider = provider or "deepseek"
        evidence.append("env:DEEPSEEK_API_KEY present")
    if "ANTHROPIC_BASE_URL" in env:
        host = _endpoint_host(env["ANTHROPIC_BASE_URL"])
        evidence.append(f"env:ANTHROPIC_BASE_URL present (host={host})")
        if "deepseek" in host.lower():
            provider = provider or "deepseek"
    if os.path.isdir(os.path.join(os.path.expanduser("~"), ".cc-switch")):
        evidence.append("config:cc-switch present")
    return provider, evidence


# --------------------------------------------------------------------------- #
# B. versioned diagnostic baseline ratchet
# --------------------------------------------------------------------------- #
def _tool_version(tool: str, repo: Path) -> str:
    if tool == "ruff":
        out = _run(["uv", "run", "ruff", "--version"], repo).stdout.strip()
        return out.split()[-1] if out else "unknown"
    if tool == "mypy":
        out = _run(["uv", "run", "mypy", "--version"], repo).stdout.strip()
        return out.split()[1] if len(out.split()) > 1 else "unknown"
    raise ValueError(f"unsupported tool: {tool}")


def config_fingerprint(tool: str, repo: Path) -> str:
    """Deterministic sha256 over the tool's pyproject configuration section."""
    data = tomllib.loads((repo / "pyproject.toml").read_text(encoding="utf-8"))
    tool_data = data.get("tool", {})
    if tool == "ruff":
        section = {k: v for k, v in tool_data.items() if k.startswith("ruff")}
    elif tool == "mypy":
        section = tool_data.get("mypy", {})
    else:
        raise ValueError(f"unsupported tool: {tool}")
    canonical = json.dumps(section, sort_keys=True, default=str)
    return _sha256(canonical)


def _relpath(repo: Path, path: str) -> str:
    try:
        return os.path.relpath(path, str(repo)).replace("\\", "/")
    except ValueError:
        return path.replace("\\", "/")


def collect_findings(tool: str, repo: Path) -> list[str]:
    """Collect normalized, sorted finding identities for a tool."""
    if tool == "ruff":
        proc = _run(["uv", "run", "ruff", "check", "--output-format=json", "."], repo)
        items = json.loads(proc.stdout) if proc.stdout.strip() else []
        ids = []
        for item in items:
            fn = _relpath(repo, str(item.get("filename", "")))
            loc = item.get("location", {})
            ids.append(
                f"{fn}:{loc.get('row')}:{loc.get('column')}:"
                f"{item.get('code')}:{item.get('message')}"
            )
        return sorted(set(ids))
    if tool == "mypy":
        proc = _run(["uv", "run", "mypy", "src"], repo)
        ids = []
        for line in (proc.stdout or "").splitlines():
            line = line.strip()
            if not line or ": error: " not in line:
                continue
            head, _, message = line.partition(": error: ")
            loc_parts = head.split(":")
            if len(loc_parts) < 2:
                continue
            fn = loc_parts[0].replace("\\", "/")
            line_no = loc_parts[1]
            col = loc_parts[2] if len(loc_parts) > 2 else ""
            ids.append(f"{fn}:{line_no}:{col}:{message}")
        return sorted(set(ids))
    raise ValueError(f"unsupported tool: {tool}")


def capture_baseline(tool: str, repo: Path, commit: str) -> dict:
    version = _tool_version(tool, repo)
    fingerprint = config_fingerprint(tool, repo)
    findings = collect_findings(tool, repo)
    return {
        "tool": tool,
        "tool_version": version,
        "config_fingerprint": fingerprint,
        "baseline_commit": commit,
        "finding_identity_digest": _sha256("\n".join(findings)),
        "finding_count": len(findings),
        "finding_identities": findings,
        "captured_at": datetime.datetime.now(datetime.UTC).isoformat(),
    }


def compare_findings(baseline_ids: list[str], current_ids: list[str]) -> dict:
    """Identity-aware comparison — never count-only."""
    base = set(baseline_ids)
    curr = set(current_ids)
    new = sorted(curr - base)
    removed = sorted(base - curr)
    return {"new_findings": new, "removed_findings": removed}


REQUIRED_BASELINE_FIELDS = ("tool", "tool_version", "config_fingerprint", "baseline_commit", "finding_count")


def ratchet_compare(baseline: dict, current: dict) -> dict:
    """Compare a current capture against a persisted baseline."""
    missing = [f for f in REQUIRED_BASELINE_FIELDS if f not in baseline]
    if missing:
        return {"status": "FAIL", "detail": f"malformed baseline: missing fields {missing}"}
    same_version = baseline.get("tool_version") == current.get("tool_version")
    same_config = baseline.get("config_fingerprint") == current.get("config_fingerprint")
    if not (same_version and same_config):
        return {
            "status": "BASELINE_INCOMPATIBLE",
            "detail": (
                "tool version or config fingerprint changed; direct comparison is not valid"
            ),
            "baseline_tool_version": baseline.get("tool_version"),
            "current_tool_version": current.get("tool_version"),
            "baseline_config_fingerprint": baseline.get("config_fingerprint"),
            "current_config_fingerprint": current.get("config_fingerprint"),
        }

    diff = compare_findings(
        list(baseline.get("finding_identities", [])), list(current.get("finding_identities", []))
    )
    new = diff["new_findings"]
    removed = diff["removed_findings"]
    if new:
        return {
            "status": "FAIL",
            "detail": f"{len(new)} new finding(s) detected",
            "new_findings": new,
            "removed_findings": removed,
            "baseline_count": baseline.get("finding_count"),
            "current_count": current.get("finding_count"),
        }
    if removed:
        return {
            "status": "PASS",
            "detail": f"{len(removed)} finding(s) removed (no new diagnostics)",
            "removed_findings": removed,
            "baseline_count": baseline.get("finding_count"),
            "current_count": current.get("finding_count"),
        }
    return {
        "status": "PASS",
        "detail": "no new diagnostics",
        "baseline_count": baseline.get("finding_count"),
        "current_count": current.get("finding_count"),
    }


# --------------------------------------------------------------------------- #
# D. authority / contract guard
# --------------------------------------------------------------------------- #
def normalize_authority(contract: dict) -> dict:
    """Normalize V1 (flat list) and V2 (dict) authority shapes."""
    auth = contract.get("authority")
    if isinstance(auth, list):
        return {"highest": [str(x) for x in auth], "supporting": [], "implementation_precedent": []}
    if isinstance(auth, dict):
        return {
            "highest": [str(x) for x in auth.get("highest", [])],
            "supporting": [str(x) for x in auth.get("supporting", [])],
            "implementation_precedent": [
                str(x) for x in auth.get("implementation_precedent", [])
            ],
        }
    return {"highest": [], "supporting": [], "implementation_precedent": []}


def authority_conflict_status(contract: dict) -> str:
    status = (contract.get("authority_conflicts") or {}).get("status", "none")
    return status if status in CONFLICT_STATUSES else "unresolved"


def acceptance_blocked(contract: dict) -> tuple[bool, str]:
    """HIGH/CRITICAL with an unresolved authority conflict cannot be acceptance-ready."""
    risk = str(contract.get("risk", "")).strip().lower()
    high_critical = risk in ("high", "critical")
    unresolved = authority_conflict_status(contract) == "unresolved"
    if high_critical and unresolved:
        return True, "HIGH/CRITICAL task with unresolved authority conflict"
    return False, ""


def check_authority_guard(contract: dict) -> dict:
    """Deterministic authority/contract guard checks (no semantic conflict discovery)."""
    auth = normalize_authority(contract)
    status = authority_conflict_status(contract)
    blocked, reason = acceptance_blocked(contract)
    violations: list[str] = []

    highest = set(auth["highest"])
    precedent = set(auth["implementation_precedent"])
    overlap = highest & precedent
    if overlap:
        violations.append(
            f"authority listed as both highest and implementation_precedent: {sorted(overlap)}"
        )

    items = (contract.get("authority_conflicts") or {}).get("items") or []
    for item in items:
        refs = {str(r) for r in item.get("refs", [])}
        outranks = str(item.get("outranks", ""))
        if outranks in precedent and refs & highest:
            violations.append(
                f"conflict item has implementation_precedent '{outranks}' outranking normative authority"
            )

    return {
        "authority": auth,
        "conflict_status": status,
        "acceptance_blocked": blocked,
        "block_reason": reason,
        "violations": violations,
    }


# --------------------------------------------------------------------------- #
# E. task / review packet compiler
# --------------------------------------------------------------------------- #
def _bullet(name: str, values: list[str]) -> str:
    if not values:
        return f"- {name}: (none)\n"
    lines = [f"- {name}: {values[0]}"]
    lines.extend(f"  {v}" for v in values[1:])
    return "\n".join(lines) + "\n"


def _kv_block(keys: list[str], mapping: dict) -> str:
    lines = []
    for key in keys:
        if key in mapping and not _sensitive_key(key):
            lines.append(f"- {key}: {mapping[key]}")
    for key in sorted(mapping):
        if key not in keys and not _sensitive_key(key):
            lines.append(f"- {key}: {mapping[key]}")
    return "\n".join(lines) + ("\n" if lines else "")


def _attest_block(attestation: dict) -> str:
    order = [
        "configured_provider",
        "configured_model",
        "requested_model",
        "harness_reported_model",
        "provider_mapping",
        "effective_backend_model",
        "effective_backend_observable",
        "attestation_status",
        "evidence_source",
        "contradictions",
    ]
    return _kv_block(order, attestation)


def _blocked_banner(blocked: bool, reason: str) -> str:
    if not blocked:
        return ""
    return f"> **BLOCKED** — acceptance not ready: {reason}.\n\n"


def render_task_packet(contract: dict, attestation: dict | None = None) -> str:
    blocked, reason = acceptance_blocked(contract)
    auth = normalize_authority(contract)
    conflict = (contract.get("authority_conflicts") or {})
    items = conflict.get("items") or []
    out: list[str] = [f"# Task Packet — {contract.get('task_id', 'UNKNOWN')}", ""]
    out.append(_blocked_banner(blocked, reason))
    out.extend(
        [
            f"- task_id: {contract.get('task_id', 'UNKNOWN')}",
            f"- base_sha: {contract.get('base_sha', 'UNKNOWN')}",
            f"- risk: {contract.get('risk', 'UNKNOWN')}",
            f"- profile: {contract.get('profile', 'UNKNOWN')}",
            f"- acceptance_blocked: {'true' if blocked else 'false'}",
            "",
            "## Goal",
            _bullet("goal", _as_list(contract.get("goal"))),
            "## Non-goals",
            _bullet("non_goals", _as_list(contract.get("non_goals"))),
            "## Authority",
            _bullet("highest", auth["highest"]),
            _bullet("supporting", auth["supporting"]),
            _bullet("implementation_precedent", auth["implementation_precedent"]),
            "## Authority conflicts",
            f"- status: {conflict.get('status', 'none')}",
        ]
    )
    if items:
        for idx, item in enumerate(items):
            out.append(f"- item[{idx}]: {json.dumps(item, sort_keys=True, default=str)}")
    else:
        out.append("- items: (none)")
    out.extend(
        [
            "",
            "## Expected scope",
            _bullet("expected_scope", _as_list(contract.get("expected_scope"))),
            "## Protected scope",
            _bullet("protected_scope", _as_list(contract.get("protected_scope"))),
            "## Acceptance",
            _bullet("acceptance", _as_list(contract.get("acceptance"))),
            "## Verification",
            _bullet("verification", _as_list(contract.get("verification"))),
            "## Permissions",
            _kv_block(
                ["network", "dependencies", "migrations", "destructive", "control_plane_change"],
                contract.get("permissions") or {},
            ),
            "## Routing / model request",
            _kv_block(["initial", "max_grounded_retry", "escalation"], contract.get("routing") or {}),
        ]
    )
    if attestation:
        out.extend(["## Attestation summary", _attest_block(attestation)])
    return "\n".join(out).rstrip() + "\n"


def render_review_packet(contract: dict, state: dict | None = None) -> str:
    state = state or {}
    blocked, reason = acceptance_blocked(contract)
    auth = normalize_authority(contract)
    conflict = (contract.get("authority_conflicts") or {})
    items = conflict.get("items") or []
    out: list[str] = [f"# Review Packet — {contract.get('task_id', 'UNKNOWN')}", ""]
    out.append(_blocked_banner(blocked, reason))
    out.extend(
        [
            f"- task_id: {contract.get('task_id', 'UNKNOWN')}",
            f"- base_sha: {contract.get('base_sha', 'UNKNOWN')}",
            f"- candidate_sha: {state.get('candidate_sha', 'UNKNOWN')}",
            f"- risk: {contract.get('risk', 'UNKNOWN')}",
            f"- acceptance_blocked: {'true' if blocked else 'false'}",
            "",
            "## Changed files",
            _bullet("changed_files", _as_list(state.get("changed_files"))),
            "## Frozen acceptance / invariants",
            _bullet("acceptance", _as_list(contract.get("acceptance"))),
            "## Authority",
            _bullet("highest", auth["highest"]),
            _bullet("supporting", auth["supporting"]),
            _bullet("implementation_precedent", auth["implementation_precedent"]),
            "## Authority conflicts",
            f"- status: {conflict.get('status', 'none')}",
        ]
    )
    if items:
        for idx, item in enumerate(items):
            out.append(f"- item[{idx}]: {json.dumps(item, sort_keys=True, default=str)}")
    else:
        out.append("- items: (none)")
    out.extend(
        [
            "",
            "## Verification evidence",
            _kv_block(sorted((state.get("verification_evidence") or {}).keys()),
                      state.get("verification_evidence") or {}),
            "## Model / provider attestation",
            _attest_block(state.get("attestation") or {}),
            "## Known residuals",
            _bullet("residuals", _as_list(state.get("residuals"))),
            "## Blockers",
            _bullet("blockers", _as_list(state.get("blockers"))),
            "## Review questions / verdict requested",
            _bullet("review_questions", _as_list(state.get("review_questions")))
            or "- review_questions: (none)\n",
            "- verdict requested: ACCEPT_CANARY | FIX_REQUIRED | REDESIGN_REQUIRED",
        ]
    )
    return "\n".join(out).rstrip() + "\n"


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    if isinstance(value, str):
        return [value]
    return [str(value)]


# --------------------------------------------------------------------------- #
# repository paths
# --------------------------------------------------------------------------- #
def baseline_dir(repo: Path) -> Path:
    return repo / ".ai-dev" / "evidence" / "diagnostics"


def baseline_path(tool: str, repo: Path) -> Path:
    return baseline_dir(repo) / f"{tool}.baseline.yaml"


def baseline_history_path(repo: Path) -> Path:
    return baseline_dir(repo) / "history.jsonl"


def _append_history(repo: Path, record: dict) -> None:
    path = baseline_history_path(repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, sort_keys=True, default=str) + "\n")


def _write_baseline(tool: str, repo: Path, baseline: dict, reason: str) -> Path:
    path = baseline_path(tool, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_yaml_dump(baseline), encoding="utf-8")
    _append_history(
        repo,
        {
            "action": "capture" if reason == "initial" else "rebaseline",
            "tool": tool,
            "tool_version": baseline.get("tool_version"),
            "config_fingerprint": baseline.get("config_fingerprint"),
            "baseline_commit": baseline.get("baseline_commit"),
            "finding_count": baseline.get("finding_count"),
            "finding_identity_digest": baseline.get("finding_identity_digest"),
            "captured_at": baseline.get("captured_at"),
            "reason": reason,
        },
    )
    return path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_attest(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    provider, evidence = gather_config_evidence()
    mapping = _read_provider_mapping(repo)
    result = attest(
        requested_model=args.requested_model,
        harness_reported_model=args.harness_model,
        configured_provider=args.configured_provider or provider,
        configured_model=args.configured_model,
        direct_backend_provider=args.direct_backend_provider,
        direct_backend_model=args.direct_backend_model,
        provider_mapping=mapping,
        evidence_source=evidence,
    )
    print(_yaml_dump(result), end="")
    return 0


def _cmd_ratchet(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    tools = [args.tool] if args.tool else list(RATCHET_TOOLS)
    commit = args.commit or _run(["git", "rev-parse", "HEAD"], repo).stdout.strip()
    if args.action == "capture":
        for tool in tools:
            baseline = capture_baseline(tool, repo, commit)
            path = _write_baseline(tool, repo, baseline, reason="initial")
            print(f"captured {tool} baseline -> {path} ({baseline['finding_count']} findings)")
        return 0
    if args.action == "compare":
        code = 0
        for tool in tools:
            path = baseline_path(tool, repo)
            if not path.is_file():
                print(f"{tool}: FAIL — baseline missing at {path}")
                code = 1
                continue
            baseline = _yaml_load(path)
            current = capture_baseline(tool, repo, commit)
            result = ratchet_compare(baseline, current)
            print(f"{tool}: {result['status']} — {result.get('detail', '')}")
            if result["status"] == "FAIL":
                for finding in result.get("new_findings", []):
                    print(f"  NEW: {finding}")
            if result["status"] != "PASS":
                code = 1
        return code
    if args.action == "rebaseline":
        for tool in tools:
            baseline = capture_baseline(tool, repo, commit)
            path = _write_baseline(tool, repo, baseline, reason=args.reason or "manual rebaseline")
            print(f"rebaselined {tool} -> {path} ({baseline['finding_count']} findings)")
        return 0
    return 2


def _cmd_contract(args: argparse.Namespace) -> int:
    contract = _yaml_load(Path(args.contract))
    guard = check_authority_guard(contract)
    print(_yaml_dump(guard), end="")
    if guard["violations"]:
        return 1
    return 0


def _cmd_packet(args: argparse.Namespace) -> int:
    contract = _yaml_load(Path(args.contract))
    state = {}
    if args.state:
        state = _yaml_load(Path(args.state))
    if args.kind == "task":
        attestation = state.get("attestation")
        text = render_task_packet(contract, attestation=attestation)
    else:
        text = render_review_packet(contract, state=state)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text)} bytes)")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai_dev_v2", description="AI Dev OS v2.0 Control Canary")
    parser.add_argument("--repo", default=str(REPO), help="repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    p_attest = sub.add_parser("attest", help="render a model/provider attestation")
    p_attest.add_argument("--requested-model")
    p_attest.add_argument("--harness-model")
    p_attest.add_argument("--configured-provider")
    p_attest.add_argument("--configured-model")
    p_attest.add_argument("--direct-backend-provider")
    p_attest.add_argument("--direct-backend-model")
    p_attest.set_defaults(func=_cmd_attest)

    p_ratchet = sub.add_parser("ratchet", help="versioned diagnostic baseline ratchet")
    p_ratchet.add_argument("action", choices=["capture", "compare", "rebaseline"])
    p_ratchet.add_argument("--tool", choices=list(RATCHET_TOOLS))
    p_ratchet.add_argument("--commit", help="baseline commit (default: current HEAD)")
    p_ratchet.add_argument("--reason", help="rebaseline reason (rebaseline only)")
    p_ratchet.set_defaults(func=_cmd_ratchet)

    p_contract = sub.add_parser("contract", help="authority/contract guard check")
    p_contract.add_argument("contract")
    p_contract.set_defaults(func=_cmd_contract)

    p_packet = sub.add_parser("packet", help="deterministic packet compiler")
    p_packet.add_argument("kind", choices=["task", "review"])
    p_packet.add_argument("contract")
    p_packet.add_argument("--state", help="bounded task/evidence state YAML")
    p_packet.add_argument("--out", required=True, help="output markdown path")
    p_packet.set_defaults(func=_cmd_packet)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
