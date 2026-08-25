"""Installed-runtime, DPAPI-protected Personal admission token.

This module deliberately knows nothing about Git, E11 evidence locations, or
the renderer.  Those inputs are checked by the provisioning command before a
token is created; the installed sidecar checks only this compact trust token.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

from psyche_os.crypto.envelope import OSKeyWrapper
from psyche_os.personal_mode.admission import AdmissionDecision

TOKEN_NAME = "admission.pmv1.dpapi"
TOKEN_SCHEMA_VERSION = "PMV1-ADMISSION-TOKEN-1"
_FIELDS = frozenset(
    {
        "schema_version", "decision", "evaluation_id", "sealed_evaluation_sha256",
        "owner_attestation_sha256", "candidate_identity", "profile_id", "profile_digest",
        "issued_at", "expires_at",
    }
)


def admission_token_path(root: Path) -> Path:
    """The sole token location, below the trusted Personal root."""
    return root / TOKEN_NAME


def _canonical(value: dict[str, str]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _timestamp(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed.astimezone(UTC) if parsed.tzinfo else None


def _digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _parse(value: bytes) -> dict[str, str] | None:
    try:
        data: Any = json.loads(value)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or set(data) != _FIELDS or not all(isinstance(v, str) for v in data.values()):
        return None
    token: dict[str, str] = data
    if token["schema_version"] != TOKEN_SCHEMA_VERSION or token["decision"] != "OPEN":
        return None
    if not token["evaluation_id"] or not token["candidate_identity"] or not token["profile_id"]:
        return None
    if not all(_digest(token[name]) for name in ("sealed_evaluation_sha256", "owner_attestation_sha256", "profile_digest")):
        return None
    issued, expires = _timestamp(token["issued_at"]), _timestamp(token["expires_at"])
    if issued is None or expires is None or issued >= expires:
        return None
    return token


def create_token(
    root: Path,
    *,
    evaluation_id: str,
    sealed_evaluation_sha256: str,
    owner_attestation_sha256: str,
    candidate_identity: str,
    profile_id: str,
    profile_digest: str,
    issued_at: datetime,
    expires_at: datetime,
    wrapper: OSKeyWrapper | Any | None = None,
) -> Path:
    """Persist a validated token only after the release evaluator returned OPEN."""
    token = {
        "schema_version": TOKEN_SCHEMA_VERSION, "decision": "OPEN", "evaluation_id": evaluation_id,
        "sealed_evaluation_sha256": sealed_evaluation_sha256, "owner_attestation_sha256": owner_attestation_sha256,
        "candidate_identity": candidate_identity, "profile_id": profile_id, "profile_digest": profile_digest,
        "issued_at": issued_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        "expires_at": expires_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
    }
    if _parse(_canonical(token)) is None:
        raise ValueError("invalid admission token inputs")
    protected = (wrapper or OSKeyWrapper()).protect(_canonical(token), "PSYCHE OS Personal admission")
    root.mkdir(parents=True, exist_ok=True)
    path = admission_token_path(root)
    temporary = path.with_suffix(".tmp")
    temporary.write_bytes(protected)
    temporary.replace(path)
    return path


def revoke_token(root: Path) -> None:
    """Trusted local revocation; subsequent guarded operations re-evaluate closed."""
    admission_token_path(root).unlink(missing_ok=True)


def token_evaluator(
    root: Path,
    *,
    candidate_identity: str,
    profile_id: str,
    profile_digest: str,
    wrapper_factory: Callable[[], OSKeyWrapper] = OSKeyWrapper,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
) -> Callable[[], AdmissionDecision]:
    """Return a total, fail-closed evaluator for the installed sidecar."""
    def evaluate() -> AdmissionDecision:
        if candidate_identity == "UNBOUND" or not _digest(profile_digest):
            return AdmissionDecision(False)
        try:
            token = _parse(wrapper_factory().unprotect(admission_token_path(root).read_bytes()))
        except Exception:  # DPAPI/context/parser failures are intentionally indistinguishable.
            return AdmissionDecision(False)
        if token is None or token["candidate_identity"] != candidate_identity or token["profile_id"] != profile_id or token["profile_digest"] != profile_digest:
            return AdmissionDecision(False)
        expires = _timestamp(token["expires_at"])
        if expires is None or clock().astimezone(UTC) >= expires:
            return AdmissionDecision(False)
        return AdmissionDecision(True, token["evaluation_id"], token["sealed_evaluation_sha256"], token["owner_attestation_sha256"], token["profile_digest"], token["candidate_identity"], expires)
    return evaluate


def attestation_sha256(attestation: dict[str, Any]) -> str:
    """Digest the attestation payload as stored, independent of YAML formatting."""
    return hashlib.sha256(_canonical({str(k): str(v) for k, v in attestation.items()})).hexdigest()
