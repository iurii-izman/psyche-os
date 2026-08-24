from datetime import UTC, datetime, timedelta

from psyche_os.crypto.envelope import SensitiveBytes
from psyche_os.personal_mode.admission import AdmissionDecision, PersonalAdmissionGuard
from psyche_os.personal_mode.reflection import PersonalReflectionService
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


def test_admitted_personal_reflection_uses_v10_real_personal_root(tmp_path) -> None:
    now = datetime(2026, 8, 24, tzinfo=UTC)
    decision = AdmissionDecision(True, "evaluation", "eval", "attestation", "profile", "candidate", now + timedelta(minutes=10))
    guard = PersonalAdmissionGuard(lambda: decision, clock=lambda: now)
    paths = personal_runtime_paths(local_app_data=tmp_path)
    vmk = SensitiveBytes(b"f" * 32)
    service = PersonalReflectionService(paths, guard, lambda: SensitiveBytes(vmk.raw))
    try:
        session = service.create_session("Fictional Cyrillic сессия")
        assert paths.vault.exists()
        assert service.get_session(session["session_id"])["title"] == "Fictional Cyrillic сессия"
        assert service.connection.execute("SELECT data_mode FROM reflection_sessions").fetchone() == ("real_personal",)
        assert service.connection.execute("PRAGMA foreign_key_check").fetchall() == []
    finally:
        service.close()
        vmk.clear()
