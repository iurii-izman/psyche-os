"""Read-only validation of E11 exact-candidate gate-evaluation records.

Valid DRAFT records are expected to report CLOSED.  This command validates that
truthful closed state; it does not seal records or create a human attestation.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

import yaml

from psyche_os.release_evidence.e11_gate import evaluate_evaluation, load_evaluation

ROOT = Path(__file__).resolve().parents[1]
EVALUATIONS = ROOT / "artifacts" / "e11" / "gate-evaluations"
ATTESTATIONS = ROOT / "artifacts" / "e11" / "human-attestations"


def _attestation_for(evaluation_id: str) -> dict | None:
    path = ATTESTATIONS / f"{evaluation_id}.yaml"
    if not path.is_file():
        return None
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    return value if isinstance(value, dict) else None


def _stable_gate_is_closed() -> bool:
    state = yaml.safe_load((ROOT / "docs/development/STATE.yaml").read_text(encoding="utf-8"))
    policy = yaml.safe_load(
        (ROOT / "docs/architecture/REAL_DATA_GATE.yaml").read_text(encoding="utf-8")
    )
    return (
        isinstance(state, dict)
        and state.get("real_data_gate", {}).get("state") == "CLOSED"
        and isinstance(policy, dict)
        and policy.get("fail_closed_default") == "CLOSED"
    )


def validate_all(require_closed: bool) -> int:
    if not _stable_gate_is_closed():
        print("FAIL: stable REAL_DATA_GATE is not CLOSED")
        return 1
    paths = sorted(EVALUATIONS.glob("*.yaml"))
    if not paths:
        print("FAIL: no E11 gate-evaluation records found")
        return 1
    failed = 0
    for path in paths:
        try:
            evaluation = load_evaluation(path)
            evaluation_id = str(evaluation.get("evaluation_id", "UNKNOWN"))
            outcome = evaluate_evaluation(
                ROOT, evaluation, attestation=_attestation_for(evaluation_id)
            )
        except Exception as exc:
            print(f"FAIL: {path.relative_to(ROOT)}: {type(exc).__name__}: {exc}")
            failed += 1
            continue
        print(
            f"{outcome.state}: {path.relative_to(ROOT)} "
            f"lifecycle={outcome.lifecycle} reasons={','.join(outcome.reasons) or 'none'}"
        )
        if require_closed and outcome.state != "CLOSED":
            print(
                "FAIL: evaluation unexpectedly supports OPEN during the closed-gate E11 implementation"
            )
            failed += 1
    print(
        f"SUMMARY: {len(paths) - failed} closed evaluation record(s) inspected, {failed} failure(s)"
    )
    return 1 if failed else 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate E11 gate-evaluation artifacts read-only")
    parser.add_argument(
        "--require-closed", action="store_true", help="fail if any record evaluates OPEN"
    )
    args = parser.parse_args()
    return validate_all(args.require_closed)


if __name__ == "__main__":
    sys.exit(main())
