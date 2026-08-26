from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from psyche_os.personal_mode.admission import AdmissionDecision, PersonalAdmissionGuard
from psyche_os.personal_mode.integrity import PersonalIntegrityError, verify_personal_vault
from psyche_os.personal_mode.key_envelope import EnvelopeError, validate_new_recovery_secret
from psyche_os.personal_mode.runtime import PersonalRuntime, PersonalRuntimeError
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


class _DPAPI:
    available = True

    def protect(self, value: bytes, description: str) -> bytes:
        return b"x" * 1024


def _runtime(tmp_path) -> PersonalRuntime:
    now = datetime(2026, 8, 26, tzinfo=UTC)
    guard = PersonalAdmissionGuard(
        lambda: AdmissionDecision(True, "evaluation", "digest", "attestation", "profile", "candidate", now + timedelta(minutes=5)),
        clock=lambda: now,
    )
    return PersonalRuntime(personal_runtime_paths(local_app_data=tmp_path), guard, os_wrapper_factory=_DPAPI)


def test_new_manual_recovery_secret_rejects_trivial_values() -> None:
    for secret in ("short", "a" * 32, "onlylowercasecharacters"):
        with pytest.raises(EnvelopeError):
            validate_new_recovery_secret(secret)
    assert validate_new_recovery_secret("Synthetic-Recovery-2026") == "Synthetic-Recovery-2026"


def test_integrity_oracle_fails_closed_for_schema_and_fk_drift(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    secret = "Synthetic-Recovery-2026"
    runtime.setup(secret)
    envelope = runtime.lifecycle._active_envelope()
    connection = runtime.reflection.connection
    verify_personal_vault(connection, envelope)
    connection.execute("CREATE TABLE unexpected_schema_drift (id INTEGER)")
    with pytest.raises(PersonalIntegrityError):
        verify_personal_vault(connection, envelope)
    connection.execute("DROP TABLE unexpected_schema_drift")
    connection.execute("PRAGMA foreign_keys=OFF")
    connection.execute("INSERT INTO reflection_turns VALUES('orphan','missing',1,'USER','2026-08-26T00:00:00+00:00','synthetic')")
    connection.commit()
    with pytest.raises(PersonalIntegrityError):
        verify_personal_vault(connection, envelope)


def test_wrong_recovery_secret_cannot_unlock(tmp_path) -> None:
    runtime = _runtime(tmp_path)
    runtime.setup("Synthetic-Recovery-2026")
    runtime.lock()
    with pytest.raises(PersonalRuntimeError):
        runtime.unlock("Synthetic-Wrong-Secret-2026")
