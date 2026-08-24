from datetime import UTC, datetime, timedelta

import pytest

from psyche_os.personal_mode.admission import (
    AdmissionDecision,
    PersonalAdmissionGuard,
    PersonalNotAdmitted,
)
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


def _open(*, expiry: datetime) -> AdmissionDecision:
    return AdmissionDecision(True, "evaluation", "eval-digest", "attestation-digest", "profile-digest", "candidate", expiry)


def test_closed_admission_is_content_free_and_does_not_create_personal_root(tmp_path) -> None:
    paths = personal_runtime_paths(local_app_data=tmp_path)
    guard = PersonalAdmissionGuard()
    assert not paths.root.exists()
    with pytest.raises(PersonalNotAdmitted):
        guard.require()
    assert not paths.root.exists()
    assert guard.status() == {"local_personal": "NOT_ADMITTED"}


def test_guard_rechecks_expiry_and_identity_before_reads() -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    decision = _open(expiry=now + timedelta(minutes=1))
    cleared = []
    guard = PersonalAdmissionGuard(lambda: decision, clock=lambda: now, clear_key_material=lambda: cleared.append(True))
    assert guard.require() == decision
    now += timedelta(minutes=2)
    with pytest.raises(PersonalNotAdmitted):
        guard.require()
    assert guard.locked and cleared
