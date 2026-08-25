"""Owner-operated provision/revoke command for a sealed Personal admission.

This is deliberately separate from the installed renderer and sidecar.  It
requires an exact E11 evaluation plus an owner-created attestation, validates
them with the repository evaluator, then writes only a DPAPI-wrapped token.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
import hashlib
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from psyche_os.personal_mode.admission_token import create_token, revoke_token  # noqa: E402
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths  # noqa: E402
from psyche_os.release_evidence.e11_gate import evaluate_evaluation, load_evaluation  # noqa: E402


def _canonical_digest(value: object) -> str:
    import json
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()).hexdigest()


def _load_mapping(path: Path) -> dict:
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("expected YAML mapping")
    return value


def provision(evaluation_path: Path, attestation_path: Path, build_id: str) -> int:
    evaluation, attestation = load_evaluation(evaluation_path), _load_mapping(attestation_path)
    outcome = evaluate_evaluation(ROOT, evaluation, attestation=attestation)
    if outcome.state != "OPEN" or evaluation.get("lifecycle") != "SEALED":
        print("REFUSED: evaluation is not owner-openable")
        return 2
    binding = evaluation["profile_binding"]
    if build_id != evaluation["candidate"]["build_id"]:
        print("REFUSED: supplied build identity does not match evaluation")
        return 2
    expires = datetime.fromisoformat(attestation["expires_at"].replace("Z", "+00:00")).astimezone(UTC)
    token = create_token(
        personal_runtime_paths().root,
        evaluation_id=evaluation["evaluation_id"],
        sealed_evaluation_sha256=evaluation["seal"]["payload_sha256"],
        owner_attestation_sha256=_canonical_digest(attestation),
        candidate_identity=build_id,
        profile_id=binding["profile_id"],
        profile_digest=binding["profile_definition_sha256"],
        issued_at=datetime.now(UTC), expires_at=expires,
    )
    print(f"PROVISIONED: {token}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Trusted local Personal admission provisioning")
    command = parser.add_subparsers(dest="command", required=True)
    provision_parser = command.add_parser("provision")
    provision_parser.add_argument("--evaluation", type=Path, required=True)
    provision_parser.add_argument("--owner-attestation", type=Path, required=True)
    provision_parser.add_argument("--build-id", required=True)
    command.add_parser("revoke")
    args = parser.parse_args()
    if args.command == "revoke":
        revoke_token(personal_runtime_paths().root)
        print("REVOKED")
        return 0
    return provision(args.evaluation, args.owner_attestation, args.build_id)


if __name__ == "__main__":
    raise SystemExit(main())
