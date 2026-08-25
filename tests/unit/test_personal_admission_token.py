from datetime import UTC, datetime, timedelta

from psyche_os.personal_mode.admission_token import create_token, revoke_token, token_evaluator


class _DPAPI:
    def protect(self, value: bytes, description: str = "") -> bytes:
        return b"dpapi:" + value

    def unprotect(self, value: bytes) -> bytes:
        if not value.startswith(b"dpapi:"):
            raise ValueError("wrong context")
        return value.removeprefix(b"dpapi:")


def _token(root, now):
    return create_token(
        root, evaluation_id="eval-1", sealed_evaluation_sha256="a" * 64,
        owner_attestation_sha256="b" * 64, candidate_identity="a" * 40,
        profile_id="local_personal_evidence_reflection_windows_v1", profile_digest="c" * 64,
        issued_at=now, expires_at=now + timedelta(hours=1), wrapper=_DPAPI(),
    )


def test_token_is_exact_identity_bound_and_revocable(tmp_path) -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    path = _token(tmp_path, now)
    evaluator = token_evaluator(tmp_path, candidate_identity="a" * 40, profile_id="local_personal_evidence_reflection_windows_v1", profile_digest="c" * 64, wrapper_factory=_DPAPI, clock=lambda: now)
    assert evaluator().currently_open(now)
    assert not token_evaluator(tmp_path, candidate_identity="d" * 40, profile_id="local_personal_evidence_reflection_windows_v1", profile_digest="c" * 64, wrapper_factory=_DPAPI, clock=lambda: now)().admitted
    path.write_bytes(b"tampered")
    assert not evaluator().admitted
    _token(tmp_path, now)
    revoke_token(tmp_path)
    assert not evaluator().admitted


def test_expired_and_wrong_dpapi_context_fail_closed(tmp_path) -> None:
    now = datetime(2026, 8, 25, tzinfo=UTC)
    _token(tmp_path, now)
    evaluator = token_evaluator(tmp_path, candidate_identity="a" * 40, profile_id="local_personal_evidence_reflection_windows_v1", profile_digest="c" * 64, wrapper_factory=_DPAPI, clock=lambda: now + timedelta(hours=2))
    assert not evaluator().admitted
    evaluator = token_evaluator(tmp_path, candidate_identity="a" * 40, profile_id="local_personal_evidence_reflection_windows_v1", profile_digest="c" * 64, wrapper_factory=lambda: object(), clock=lambda: now)
    assert not evaluator().admitted
