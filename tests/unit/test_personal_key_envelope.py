import json

import pytest

from psyche_os.crypto.envelope import RecoveryWrapper
from psyche_os.personal_mode import key_envelope
from psyche_os.personal_mode.key_envelope import EnvelopeError, PersonalKeyEnvelope


class _DPAPI:
    available = True

    def protect(self, value: bytes, description: str) -> bytes:
        assert description == "PSYCHE OS Personal VMK"
        return b"x" * 1024


def test_first_setup_requires_independent_recovery_unwrap() -> None:
    envelope, vmk = PersonalKeyEnvelope.create(
        vault_id="vault_1", profile_id="profile_1", profile_version="v1",
        recovery_secret="fictional recovery secret", os_wrapper=_DPAPI(),
    )
    try:
        assert envelope.unwrap_recovery("fictional recovery secret").raw == vmk.raw
        with pytest.raises(EnvelopeError):
            envelope.unwrap_recovery("wrong secret")
    finally:
        vmk.clear()


def test_first_setup_verifies_with_a_distinct_recovery_wrapper(monkeypatch) -> None:
    instances = []

    class TrackingRecoveryWrapper:
        def __init__(self) -> None:
            self._inner = RecoveryWrapper()
            self.unwrap_calls = 0
            instances.append(self)

        @property
        def available(self):
            return self._inner.available

        def wrap(self, *args, **kwargs):
            return self._inner.wrap(*args, **kwargs)

        def unwrap(self, *args, **kwargs):
            self.unwrap_calls += 1
            return self._inner.unwrap(*args, **kwargs)

    monkeypatch.setattr(key_envelope, "RecoveryWrapper", TrackingRecoveryWrapper)
    envelope, vmk = PersonalKeyEnvelope.create(
        vault_id="vault_1", profile_id="profile_1", profile_version="v1",
        recovery_secret="fictional recovery secret", os_wrapper=_DPAPI(),
    )
    try:
        assert len(instances) == 2
        assert instances[0] is not instances[1]
        assert instances[0].unwrap_calls == 0
        assert instances[1].unwrap_calls == 1
        recovered = envelope.unwrap_recovery("fictional recovery secret", instances[1])
        try:
            assert recovered.raw == vmk.raw
        finally:
            recovered.clear()
    finally:
        vmk.clear()


@pytest.mark.parametrize("mutate", [
    lambda value: value.__setitem__("unknown", True),
    lambda value: value.__setitem__("db_salt_hex", "0" * 63),
    lambda value: value["recovery"].__setitem__("memory_cost", 999999),
])
def test_envelope_rejects_unknown_or_malformed_fields(mutate) -> None:
    envelope, vmk = PersonalKeyEnvelope.create(
        vault_id="vault_1", profile_id="profile_1", profile_version="v1",
        recovery_secret="fictional recovery secret", os_wrapper=_DPAPI(),
    )
    try:
        value = json.loads(envelope.canonical_bytes())
        mutate(value)
        with pytest.raises(EnvelopeError):
            PersonalKeyEnvelope.parse(json.dumps(value).encode())
    finally:
        vmk.clear()


def test_envelope_rejects_duplicate_json_keys() -> None:
    raw = b'{"format":"PMV1-KEY-ENVELOPE-V1","format":"PMV1-KEY-ENVELOPE-V1"}'
    with pytest.raises(EnvelopeError):
        PersonalKeyEnvelope.parse(raw)
