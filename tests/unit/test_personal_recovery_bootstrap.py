import pytest

from psyche_os.personal_mode.key_envelope import PersonalKeyEnvelope
from psyche_os.personal_mode.recovery_bootstrap import (
    RecoveryBootstrapError,
    create_bootstrap,
    recover_bootstrap,
)


class _DPAPI:
    available = True
    def protect(self, value: bytes, description: str) -> bytes:
        return b"x" * 1024


def test_bootstrap_recovers_only_matching_authenticated_payload() -> None:
    envelope, vmk = PersonalKeyEnvelope.create(vault_id="vault_1", profile_id="profile_1", profile_version="v1", recovery_secret="fictional secret", os_wrapper=_DPAPI())
    try:
        bootstrap, payload = create_bootstrap(envelope, "fictional secret", b"fictional encrypted backup source", "backup_1")
        assert recover_bootstrap(bootstrap, "fictional secret", payload) == b"fictional encrypted backup source"
        with pytest.raises(RecoveryBootstrapError):
            recover_bootstrap(bootstrap, "wrong", payload)
        with pytest.raises(RecoveryBootstrapError):
            recover_bootstrap(bootstrap, "fictional secret", payload + b"x")
    finally:
        vmk.clear()
