from datetime import UTC, datetime, timedelta

import pytest

from psyche_os.personal_mode import key_envelope
from psyche_os.personal_mode.admission import (
    AdmissionDecision,
    PersonalAdmissionGuard,
    PersonalNotAdmitted,
)
from psyche_os.personal_mode.key_envelope import EnvelopeError
from psyche_os.personal_mode.runtime import PersonalRuntime, PersonalRuntimeError
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


class _DPAPI:
    available = True
    def protect(self, value: bytes, description: str) -> bytes:
        return b"x" * 1024


def _decision(expiry):
    return AdmissionDecision(True, "evaluation", "digest", "attestation", "profile", "candidate", expiry)


def test_closed_personal_setup_creates_no_root(tmp_path) -> None:
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, PersonalAdmissionGuard(), os_wrapper_factory=_DPAPI)
    with pytest.raises(PersonalNotAdmitted):
        runtime.setup("fictional secret")
    assert not paths.root.exists()


def test_admitted_setup_reopens_real_personal_v10_and_expiry_blocks_reads(tmp_path) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    decision = _decision(now + timedelta(minutes=1))
    paths = personal_runtime_paths(local_app_data=tmp_path)
    runtime = PersonalRuntime(paths, PersonalAdmissionGuard(lambda: decision, clock=lambda: now), os_wrapper_factory=_DPAPI)
    runtime.setup("fictional secret")
    session = runtime.reflection.create_session("Fictional Personal session")
    runtime.reflection.add_user_turn(session["session_id"], "Synthetic private turn")
    runtime.lock()
    runtime = PersonalRuntime(paths, PersonalAdmissionGuard(lambda: decision, clock=lambda: now), os_wrapper_factory=_DPAPI)
    runtime.unlock("fictional secret")
    assert runtime.reflection.get_session(session["session_id"])["turns"][0]["content"] == "Synthetic private turn"
    now += timedelta(minutes=2)
    with pytest.raises(PersonalNotAdmitted):
        runtime.reflection.list_sessions()
    with pytest.raises(PersonalNotAdmitted):
        runtime.reflection.get_session(session["session_id"])


def test_independent_recovery_verification_failure_prevents_personal_setup(tmp_path, monkeypatch) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    original = key_envelope.RecoveryWrapper
    created = []

    class ControlledRecoveryWrapper:
        def __init__(self) -> None:
            self._inner = original()
            created.append(self)

        @property
        def available(self):
            return self._inner.available

        def wrap(self, *args, **kwargs):
            return self._inner.wrap(*args, **kwargs)

        def unwrap(self, *args, **kwargs):
            if len(created) == 2:
                raise EnvelopeError()
            return self._inner.unwrap(*args, **kwargs)

    monkeypatch.setattr(key_envelope, "RecoveryWrapper", ControlledRecoveryWrapper)
    runtime = PersonalRuntime(
        paths,
        PersonalAdmissionGuard(lambda: _decision(now + timedelta(minutes=1)), clock=lambda: now),
        os_wrapper_factory=_DPAPI,
    )
    with pytest.raises(PersonalRuntimeError) as error:
        runtime.setup("fictional secret")
    assert error.value.code == "PERSONAL_RUNTIME_UNAVAILABLE" and str(error.value) == ""
    assert len(created) == 2 and created[0] is not created[1]
    assert not paths.root.exists()
    with pytest.raises(PersonalRuntimeError):
        runtime.reflection.create_session("must not persist")
