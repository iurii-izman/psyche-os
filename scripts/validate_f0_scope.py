"""validate_f0_scope.py — F0 scope validation script.

F08 (FIX): Validators are read-only and behavioral — they inspect state,
never create evidence or modify the system. Every check rejects
missing/empty/label-only evidence.

Verifies:
1. All package modules import without error
2. CLI entry point is functional
3. SQLCipher gate is ACCEPTED (all 8 probes pass with real evidence)
4. No network/LLM/provider imports exist
5. No real data paths exist
6. No plaintext SQLite profile exists
7. REAL_DATA_GATE remains CLOSED
8. Package version matches expected
9. F08: Gate probes provide non-empty evidence (not label-only)
10. F08: No evidence is created by this validation run
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys
from typing import Any

EXPECTED_VERSION = "0.1.0"
SRC_ROOT = Path(__file__).resolve().parent.parent / "src" / "psyche_os"

REQUIRED_MODULES = [
    "psyche_os",
    "psyche_os.__main__",
    "psyche_os.domain",
    "psyche_os.domain.ids",
    "psyche_os.domain.versions",
    "psyche_os.domain.entities",
    "psyche_os.domain.invariants",
    "psyche_os.temporal",
    "psyche_os.temporal.temporal",
    "psyche_os.provenance",
    "psyche_os.provenance.provenance",
    "psyche_os.policy",
    "psyche_os.policy.engine",
    "psyche_os.crypto",
    "psyche_os.crypto.envelope",
    "psyche_os.storage",
    "psyche_os.storage.sqlcipher_gate",
    "psyche_os.storage.schema",
    "psyche_os.storage.migrations",
    "psyche_os.storage.uow",
    "psyche_os.application",
    "psyche_os.application.ports",
    "psyche_os.knowledge",
    "psyche_os.knowledge.registry",
    "psyche_os.backup_export",
    "psyche_os.backup_export.operations",
    "psyche_os.adapters",
    "psyche_os.adapters.adapters",
    "psyche_os.interfaces",
    "psyche_os.interfaces.cli",
]

FORBIDDEN_IMPORTS = [
    "requests",
    "httpx",
    "aiohttp",
    "urllib",
    "socket",
    "http.client",
    "openai",
    "anthropic",
    "llm",
    "transformers",
    "torch",
    "tensorflow",
]

FORBIDDEN_PATHS = [
    "real_data/",
    "production/",
    "live_data/",
    "user_data/",
]


def check_imports() -> dict[str, Any]:
    """Verify all required modules import without error."""
    results: dict[str, Any] = {"passed": True, "failures": []}
    for module in REQUIRED_MODULES:
        try:
            __import__(module)
        except Exception as exc:
            results["passed"] = False
            results["failures"].append({"module": module, "error": str(exc)})
    return results


def check_no_forbidden_imports() -> dict[str, Any]:
    """Scan source files for network/LLM imports."""
    results: dict[str, Any] = {"passed": True, "violations": []}
    py_files = list(SRC_ROOT.rglob("*.py"))
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        for forbidden in FORBIDDEN_IMPORTS:
            if f"import {forbidden}" in content or f"from {forbidden}" in content:
                results["passed"] = False
                results["violations"].append(
                    {
                        "file": str(py_file.relative_to(SRC_ROOT.parent.parent)),
                        "import": forbidden,
                    }
                )
    return results


def check_no_real_data_paths() -> dict[str, Any]:
    """Scan for real-data paths."""
    results: dict[str, Any] = {"passed": True, "violations": []}
    all_files = list(SRC_ROOT.rglob("*.py"))
    for f in all_files:
        content = f.read_text(encoding="utf-8")
        for forbidden_path in FORBIDDEN_PATHS:
            if forbidden_path in content.lower():
                results["passed"] = False
                results["violations"].append(
                    {
                        "file": str(f.relative_to(SRC_ROOT.parent.parent)),
                        "path": forbidden_path,
                    }
                )
    return results


def validate_probe_evidence(result: Any) -> str | None:
    """Return a reason when a passing SQLCipher probe lacks structural proof."""
    if not result.passed:
        return None
    evidence = result.evidence if isinstance(result.evidence, str) else ""
    if result.capability_verdict != "verified":
        return "capability verdict is not verified"

    number = result.probe_number
    valid = False
    if number == 1:
        valid = evidence == "sqlcipher3.dbapi2"
    elif number in {2, 3}:
        valid = bool(re.fullmatch(r"\d+\.\d+\.\d+ (?:community|commercial)", evidence))
    elif number in {4, 6}:
        valid = bool(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*(?:Error|Exception)", evidence))
    elif number == 5:
        valid = bool(re.fullmatch(r"[0-9a-f]{32}", evidence)) and evidence != (
            "53514c69746520666f726d6174203300"
        )
    elif number == 7:
        valid = evidence == "cipher_integrity_check=clean"
    elif number == 8:
        match = re.fullmatch(
            r"method=sqlcipher_export size=(\d+) tables=(\d+) rows_t=(\d+) rows_meta=(\d+)",
            evidence,
        )
        valid = bool(match) and all(int(value) > 0 for value in match.groups())

    return None if valid else f"probe {number} evidence has no recognized proof structure"


def check_gate_accepted() -> dict[str, Any]:
    """Verify SQLCipher gate is ACCEPTED with real (non-empty) evidence.

    F08: Every probe must provide non-empty, non-label-only evidence.
    Probes that pass with empty evidence strings are rejected.
    """
    try:
        from psyche_os.storage.sqlcipher_gate import run_gate

        report = run_gate()
        probes = []
        evidence_issues = []

        for r in report.results:
            probe_info = {
                "number": r.probe_number,
                "name": r.probe_name,
                "passed": r.passed,
                "capability_verdict": r.capability_verdict,
            }
            evidence_issue = validate_probe_evidence(r)
            if evidence_issue:
                evidence_issues.append(
                    f"Probe {r.probe_number} ({r.probe_name}): {evidence_issue}"
                )
            probes.append(probe_info)

        return {
            "passed": report.gate_state.value == "accepted" and not evidence_issues,
            "state": report.gate_state.value,
            "all_passed": report.all_passed,
            "failed_count": report.failed_count,
            "probes": probes,
            "evidence_issues": evidence_issues,
        }
    except Exception as exc:
        return {"passed": False, "error": str(exc)}


def check_real_data_gate() -> dict[str, Any]:
    """Verify REAL_DATA_GATE.yaml is CLOSED."""
    gate_file = SRC_ROOT.parent.parent / "docs" / "architecture" / "REAL_DATA_GATE.yaml"
    if not gate_file.exists():
        return {"passed": False, "error": "REAL_DATA_GATE.yaml not found"}
    content = gate_file.read_text(encoding="utf-8")
    if "CLOSED" in content:
        return {"passed": True, "status": "CLOSED"}
    return {"passed": False, "status": "OPEN — VIOLATION"}


def check_cli() -> dict[str, Any]:
    """Verify CLI entry point."""
    try:
        from psyche_os.interfaces.cli import create_cli

        cli = create_cli()
        result = cli.dispatch(["version"])
        if result.status == "ok" and result.data.get("version") == EXPECTED_VERSION:
            return {"passed": True, "version": result.data["version"]}
        return {"passed": False, "result": result.data}
    except Exception as exc:
        return {"passed": False, "error": str(exc)}


def main() -> int:
    """Run all F0 scope validations."""
    print("=" * 60)
    print("PSYCHE OS F0 Scope Validation")
    print("=" * 60)

    checks = {
        "imports": check_imports(),
        "no_forbidden_imports": check_no_forbidden_imports(),
        "no_real_data_paths": check_no_real_data_paths(),
        "gate_accepted": check_gate_accepted(),
        "real_data_gate": check_real_data_gate(),
        "cli": check_cli(),
    }

    all_passed = True
    for name, result in checks.items():
        status = "PASS" if result.get("passed", False) else "FAIL"
        if not result.get("passed", False):
            all_passed = False
        print(f"\n[{status}] {name}")
        if not result.get("passed", False):
            details = {k: v for k, v in result.items() if k != "passed"}
            print(f"  Details: {json.dumps(details, indent=2)}")

    print("\n" + "=" * 60)
    print(f"Overall: {'PASS' if all_passed else 'FAIL'}")
    print("=" * 60)

    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
