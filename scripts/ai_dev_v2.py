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
import re
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

# Recursive packet sanitization — aligned with V1 telemetry redaction semantics.
# Drop whole fields whose names are content (raw prompt / tool IO / transcript / CoT);
# redact values whose keys are secret-like; and redact bounded secret patterns in
# string values. Nested mappings/lists are sanitized recursively.
_DROP_FIELDS = {
    "raw_prompt", "prompt", "messages", "tool_output", "tool_input",
    "transcript", "chain_of_thought", "reasoning", "cot",
    "source_code_dump", "full_diff",
}
_SECRET_VALUE_KEYS = (
    "api_key", "apikey", "token", "secret", "password", "passwd",
    "authorization", "cookie", "credential", "private_key",
    "client_secret", "access_key", "session_key", "bearer_token",
)
_SECRET_PATTERNS = [
    re.compile(r"(?i)(sk|pk|rk)-[a-z0-9]{16,}"),
    re.compile(r"(?i)ghp_[a-z0-9]{36,}"),
    re.compile(r"(?i)github_pat_[a-z0-9_]{22,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)bearer\s+[a-z0-9._~+/=-]{16,}"),
]

REDACT = "[REDACTED]"


def _key_dropped(key: str) -> bool:
    return str(key).lower().replace("-", "_") in _DROP_FIELDS


def _key_secret(key: str) -> bool:
    k = str(key).lower().replace("-", "_")
    return any(s in k for s in _SECRET_VALUE_KEYS)


def sanitize(obj: Any) -> Any:
    """Recursively sanitize bounded packet input (fail-safe, no secret/raw content)."""
    if isinstance(obj, dict):
        out: dict = {}
        for k, v in obj.items():
            if _key_dropped(k):
                continue
            if _key_secret(k):
                out[k] = REDACT
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    if isinstance(obj, str):
        for pat in _SECRET_PATTERNS:
            obj = pat.sub(REDACT, obj)
        return obj
    return obj


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
    """Return the matched alias rule for `provider`, or None.

    Scoped strictly to the named provider: an alias belonging to a different
    provider is never used. A documented deterministic provider alias mapping
    supports MAPPED_BY_PROVIDER_CONTRACT; it is never stronger than CONFIRMED.
    """
    if not harness_model or not provider:
        return None
    providers = mapping.get("provider_mapping") or {}
    pdata = providers.get(provider)
    if not isinstance(pdata, dict):
        return None
    for alias in pdata.get("aliases") or []:
        pattern = str(alias.get("pattern", ""))
        if pattern and pattern.lower() in harness_model.lower():
            return alias
    return None


def _endpoint_matches_provider(host: str | None, provider: str | None) -> bool:
    """True only when the endpoint host directly identifies the provider's own domain."""
    if not host or not provider:
        return False
    h = host.lower()
    if provider.lower() == "deepseek":
        return "deepseek" in h and "127.0.0.1" not in h and "localhost" not in h
    return False


def _mapping_context(
    configured_provider: str | None,
    endpoint_identity: str | None,
    active_upstream_provider: str | None,
) -> tuple[bool, list[str]]:
    """A provider mapping contract applies only if its applicability to the active
    endpoint/upstream is itself supported by observable evidence.

    Proven when (a) the configured endpoint host directly identifies the provider's
    domain, or (b) an explicitly-parsed active upstream provider config names that
    provider. A localhost/proxy endpoint plus a merely-present key does NOT prove it.
    """
    if not configured_provider:
        return False, []
    if _endpoint_matches_provider(endpoint_identity, configured_provider):
        return True, [f"endpoint host '{endpoint_identity}' identifies {configured_provider}"]
    if active_upstream_provider and active_upstream_provider.lower() == configured_provider.lower():
        return True, [f"active upstream provider config = {configured_provider}"]
    return False, []


def attest(
    requested_model: str | None = None,
    harness_reported_model: str | None = None,
    configured_provider: str | None = None,
    configured_model: str | None = None,
    endpoint_identity: str | None = None,
    active_upstream_provider: str | None = None,
    direct_backend_provider: str | None = None,
    direct_backend_model: str | None = None,
    provider_mapping: dict | None = None,
    evidence_source: list[str] | None = None,
) -> dict:
    """Compute a bounded model/provider attestation without unsupported inference.

    - requested_model is NEVER copied into effective state.
    - A harness-reported model is harness evidence only (HARNESS_ONLY).
    - A provider mapping yields MAPPED_BY_PROVIDER_CONTRACT ONLY when the mapping's
      applicability to the active endpoint/upstream is itself supported by evidence.
    - A direct backend provider without an observed backend model is NOT model-level
      CONFIRMED.
    - A contradiction with configured provider/model or an applicable mapping is
      surfaced as CONFLICT, never silently resolved.
    """
    evidence: list[str] = list(evidence_source or [])
    contradictions: list[str] = []
    status = "UNKNOWN"
    effective_backend_model: str | None = None
    observable = False
    mapping_summary: str | None = None

    mapping_proven, mapping_reasons = _mapping_context(
        configured_provider, endpoint_identity, active_upstream_provider
    )
    evidence.extend(mapping_reasons)

    if direct_backend_provider is not None:
        if direct_backend_model:
            observable = True
            effective_backend_model = direct_backend_model
            conflict = False
            if configured_provider and direct_backend_provider.lower() != configured_provider.lower():
                contradictions.append(
                    f"configured provider '{configured_provider}' conflicts with observed "
                    f"backend provider '{direct_backend_provider}'"
                )
                conflict = True
            if configured_model and direct_backend_model != configured_model:
                contradictions.append(
                    f"configured model '{configured_model}' conflicts with observed "
                    f"backend model '{direct_backend_model}'"
                )
                conflict = True
            if mapping_proven and harness_reported_model:
                rule = resolve_mapping(
                    harness_reported_model, configured_provider, provider_mapping or {}
                )
                if rule and rule.get("maps_to") and rule["maps_to"] != direct_backend_model:
                    contradictions.append(
                        f"observed backend model '{direct_backend_model}' contradicts applicable "
                        f"mapping ({rule.get('pattern')} -> {rule.get('maps_to')})"
                    )
                    conflict = True
            status = "CONFLICT" if conflict else "CONFIRMED"
        else:
            observable = False
            effective_backend_model = "UNKNOWN"
            status = "UNKNOWN"
            evidence.append(f"direct backend provider observed: {direct_backend_provider}")
    elif configured_provider and harness_reported_model and mapping_proven:
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
    """Best-effort local configuration evidence (presence only, never secret values).

    The returned provider is a *declared/configured* provider derived from key
    presence/endpoint host. It is NOT proof of the active upstream for a request.
    """
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


def inspect_cc_switch(home: str | None = None) -> dict:
    """Secret-safe, conservative inspection of the active cc-switch provider.

    Returns {"active_provider", "endpoint_host", "evidence"}. Reads ONLY the current
    provider name and endpoint host for the Claude Code CLI harness app-type
    (`claude`); it never reads settings_config / API keys / tokens. If the active
    upstream cannot be determined unambiguously, active_provider is None.
    """
    import sqlite3
    from urllib.parse import urlparse

    home = home or os.path.expanduser("~")
    db = os.path.join(home, ".cc-switch", "cc-switch.db")
    empty: dict = {"active_provider": None, "endpoint_host": None, "evidence": []}
    if not os.path.isfile(db):
        return empty

    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        rows = list(
            con.execute(
                "SELECT app_type, name FROM providers "
                "WHERE is_current = 1 AND app_type IN ('claude', 'claude-code')"
            )
        )
        con.close()
    except Exception:
        return empty

    if not rows:
        return {
            "active_provider": None,
            "endpoint_host": None,
            "evidence": ["cc-switch: no current claude-harness provider (upstream unproven)"],
        }

    name = rows[0]["name"]
    host = None
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT pe.url FROM provider_endpoints pe "
            "JOIN providers p ON p.id = pe.provider_id "
            "WHERE p.name = ? AND p.app_type IN ('claude', 'claude-code') LIMIT 1",
            (name,),
        ).fetchone()
        con.close()
        if row and row["url"]:
            parsed = urlparse(row["url"])
            if not (parsed.username or parsed.password):
                host = parsed.hostname
    except Exception:
        host = None

    evidence = [f"cc-switch active claude provider: {name}" + (f" (host={host})" if host else "")]
    return {"active_provider": name.lower(), "endpoint_host": host, "evidence": evidence}


def gather_endpoint_context(
    environ: dict | None = None, home: str | None = None
) -> tuple[str | None, str | None, list[str]]:
    """Return (endpoint_identity, active_upstream_provider, evidence) — bounded, secret-safe."""
    env = environ if environ is not None else os.environ
    evidence: list[str] = []
    endpoint_identity: str | None = None
    if "ANTHROPIC_BASE_URL" in env:
        endpoint_identity = _endpoint_host(env["ANTHROPIC_BASE_URL"])
    cc = inspect_cc_switch(home=home)
    evidence.extend(cc["evidence"])
    return endpoint_identity, cc["active_provider"], evidence


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


REQUIRED_BASELINE_FIELDS = (
    "tool", "tool_version", "config_fingerprint", "baseline_commit",
    "finding_count", "finding_identities", "finding_identity_digest", "captured_at",
)


def _verify_baseline(baseline: dict) -> tuple[bool, str]:
    """Fail-closed integrity check: required fields + digest/count consistency."""
    missing = [f for f in REQUIRED_BASELINE_FIELDS if f not in baseline]
    if missing:
        return False, f"missing fields {sorted(missing)}"
    identities = baseline.get("finding_identities")
    if not isinstance(identities, list):
        return False, "finding_identities is not a list"
    recomputed = _sha256("\n".join(str(i) for i in identities))
    if recomputed != baseline.get("finding_identity_digest"):
        return False, "finding_identity_digest does not match finding_identities (tampered or corrupt)"
    if baseline.get("finding_count") != len(identities):
        return False, "finding_count does not match finding_identities length"
    return True, ""


def ratchet_compare(baseline: dict, current: dict) -> dict:
    """Compare a current capture against a persisted baseline (fail-closed)."""
    ok, why = _verify_baseline(baseline)
    if not ok:
        return {"status": "FAIL", "detail": f"malformed baseline: {why}"}
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
    ac = contract.get("authority_conflicts")
    if not isinstance(ac, dict):
        return "none"  # absent (legacy default); guard_decision flags V2-missing separately
    status = ac.get("status", "none")
    return status if status in CONFLICT_STATUSES else "unresolved"


def is_v2_authority(contract: dict) -> bool:
    """V2 contracts use the structured dict authority shape; legacy V1 uses a flat list."""
    return isinstance(contract.get("authority"), dict)


def _precedence_violations(auth: dict, items: list) -> list[str]:
    violations: list[str] = []
    highest = set(auth["highest"])
    precedent = set(auth["implementation_precedent"])
    overlap = highest & precedent
    if overlap:
        violations.append(
            f"authority listed as both highest and implementation_precedent: {sorted(overlap)}"
        )
    for item in items:
        if not isinstance(item, dict):
            violations.append("malformed authority conflict item (not a mapping)")
            continue
        refs = {str(r) for r in item.get("refs", [])}
        outranks = str(item.get("outranks", ""))
        if outranks in precedent and refs & highest:
            violations.append(
                f"conflict item has implementation_precedent '{outranks}' outranking normative authority"
            )
    return violations


def _malformed_resolution(items: list, status: str) -> list[str]:
    if status != "resolved":
        return []
    problems: list[str] = []
    for item in items:
        if not isinstance(item, dict):
            problems.append("authority conflict item is not a mapping")
            continue
        if item.get("blocks_acceptance") is True:
            problems.append("resolved conflict item still blocks acceptance")
        if not item.get("outranks") or not item.get("disposition"):
            problems.append("resolved conflict item missing outranks/disposition")
    return problems


def guard_decision(contract: dict) -> dict:
    """Single authoritative authority/contract guard decision.

    Used by `contract check`, Task Packet generation, Review Packet generation, and
    any future acceptance-ready decision exposed by this CLI.
    """
    risk = str(contract.get("risk", "")).strip().lower()
    high_critical = risk in ("high", "critical")
    auth = normalize_authority(contract)
    v2 = is_v2_authority(contract)
    ac = contract.get("authority_conflicts")
    has_ac = isinstance(ac, dict)
    status = authority_conflict_status(contract)
    items = ac.get("items", []) if has_ac else []
    if not isinstance(items, list):
        items = []

    blocked = False
    reasons: list[str] = []
    violations = _precedence_violations(auth, items)

    if high_critical:
        if v2:
            if not has_ac:
                blocked = True
                reasons.append("HIGH/CRITICAL V2 contract missing authority_conflicts structure")
            else:
                if status == "unresolved":
                    blocked = True
                    reasons.append("authority_conflicts.status is unresolved/invalid")
                malformed = _malformed_resolution(items, status)
                if malformed:
                    blocked = True
                    reasons.append("malformed authority conflict resolution")
                    violations.extend(malformed)
                if violations:
                    blocked = True
                    reasons.append("authority precedence violation")
        else:
            # Legacy V1 flat authority: readable under legacy semantics. Block only if
            # it explicitly carries an unresolved conflict.
            if has_ac and status == "unresolved":
                blocked = True
                reasons.append("authority_conflicts.status is unresolved")

    return {
        "risk": risk,
        "high_critical": high_critical,
        "v2_authority": v2,
        "authority": auth,
        "conflict_status": status,
        "acceptance_blocked": blocked,
        "block_reasons": reasons,
        "violations": violations,
    }


def acceptance_blocked(contract: dict) -> tuple[bool, str]:
    decision = guard_decision(contract)
    reason = "; ".join(decision["block_reasons"])
    return decision["acceptance_blocked"], reason


def check_authority_guard(contract: dict) -> dict:
    """Backward-compatible wrapper around the single guard decision."""
    return guard_decision(contract)


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
        if key in mapping:
            lines.append(f"- {key}: {mapping[key]}")
    for key in sorted(mapping):
        if key not in keys:
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
    decision = guard_decision(contract)
    blocked = decision["acceptance_blocked"]
    reason = "; ".join(decision["block_reasons"])
    auth = decision["authority"]
    contract = sanitize(contract)
    attestation = sanitize(attestation) if attestation else None
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
    decision = guard_decision(contract)
    blocked = decision["acceptance_blocked"]
    reason = "; ".join(decision["block_reasons"])
    auth = decision["authority"]
    contract = sanitize(contract)
    state = sanitize(state or {})
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


def _write_baseline(tool: str, repo: Path, baseline: dict, reason: str, previous: dict | None = None) -> Path:
    path = baseline_path(tool, repo)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_yaml_dump(baseline), encoding="utf-8")
    record = {
        "action": "capture" if reason == "initial" else "rebaseline",
        "tool": tool,
        "tool_version": baseline.get("tool_version"),
        "config_fingerprint": baseline.get("config_fingerprint"),
        "baseline_commit": baseline.get("baseline_commit"),
        "finding_count": baseline.get("finding_count"),
        "finding_identity_digest": baseline.get("finding_identity_digest"),
        "captured_at": baseline.get("captured_at"),
        "reason": reason,
    }
    if previous is not None:
        record["previous"] = {
            "tool_version": previous.get("tool_version"),
            "config_fingerprint": previous.get("config_fingerprint"),
            "baseline_commit": previous.get("baseline_commit"),
            "finding_count": previous.get("finding_count"),
            "finding_identity_digest": previous.get("finding_identity_digest"),
        }
    _append_history(repo, record)
    return path


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def _cmd_attest(args: argparse.Namespace) -> int:
    repo = Path(args.repo)
    provider, evidence = gather_config_evidence()
    endpoint_identity, active_upstream, ctx_evidence = gather_endpoint_context()
    evidence.extend(ctx_evidence)
    mapping = _read_provider_mapping(repo)
    result = attest(
        requested_model=args.requested_model,
        harness_reported_model=args.harness_model,
        configured_provider=args.configured_provider or provider,
        configured_model=args.configured_model,
        endpoint_identity=args.endpoint_identity or endpoint_identity,
        active_upstream_provider=args.active_upstream_provider or active_upstream,
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
        if not args.reason:
            print("rebaseline requires --reason (fail-closed: no silent rebaseline)")
            return 2
        for tool in tools:
            path = baseline_path(tool, repo)
            previous = _yaml_load(path) if path.is_file() else None
            baseline = capture_baseline(tool, repo, commit)
            _write_baseline(tool, repo, baseline, reason=args.reason, previous=previous)
            print(f"rebaselined {tool} -> {path} ({baseline['finding_count']} findings)")
        return 0
    return 2


def _cmd_contract(args: argparse.Namespace) -> int:
    contract = _yaml_load(Path(args.contract))
    guard = guard_decision(contract)
    print(_yaml_dump(guard), end="")
    if guard["violations"] or guard["acceptance_blocked"]:
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
    p_attest.add_argument("--endpoint-identity", help="bounded endpoint host identity")
    p_attest.add_argument("--active-upstream-provider", help="proven active upstream provider")
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
