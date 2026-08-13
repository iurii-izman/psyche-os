"""E02 T2/T4-T6 failure-driven desktop application-service tests."""

from __future__ import annotations

import pytest

from psyche_os.application.desktop_service import DesktopApplicationService, DesktopServiceError


def _unlock(service: DesktopApplicationService) -> str:
    result = service.dispatch("session.unlock", {"secret": "synthetic-demo"}, None)
    return str(result["session_token"])


def test_t2_unknown_command_and_unknown_field_fail_closed() -> None:
    service = DesktopApplicationService()
    with pytest.raises(DesktopServiceError, match="UNKNOWN_COMMAND"):
        service.dispatch("process.run", {}, None)
    with pytest.raises(DesktopServiceError, match="INVALID_PAYLOAD"):
        service.dispatch("session.unlock", {"secret": "demo", "shell": "cmd"}, None)


def test_t2_state_change_requires_current_session() -> None:
    service = DesktopApplicationService()
    with pytest.raises(DesktopServiceError, match="SESSION_REQUIRED"):
        service.dispatch("deletion.plan", {"record_id": "synthetic-observation-1"}, None)
    token = _unlock(service)
    service.dispatch("session.lock", {}, token)
    with pytest.raises(DesktopServiceError, match="SESSION_REQUIRED"):
        service.dispatch("backup.verify", {}, token)


def test_t4_correction_preserves_version_history() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    result = service.dispatch(
        "correction.apply",
        {
            "record_id": "synthetic-observation-1",
            "replacement": "Synthetic corrected observation",
            "reason": "Synthetic clarification",
        },
        token,
    )
    assert result["history_preserved"] is True
    assert result["version_count"] == 2


def test_t4_deletion_requires_plan_and_exact_confirmation_without_content_receipt() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    plan = service.dispatch(
        "deletion.plan", {"record_id": "synthetic-observation-1"}, token
    )
    with pytest.raises(DesktopServiceError, match="CONFIRMATION_REQUIRED"):
        service.dispatch(
            "deletion.execute",
            {"plan_id": plan["plan_id"], "confirmation": "cancel"},
            token,
        )
    # Cancellation/failure preserved state: the same plan is still executable.
    receipt = service.dispatch(
        "deletion.execute",
        {
            "plan_id": plan["plan_id"],
            "confirmation": "DELETE SYNTHETIC RECORD",
        },
        token,
    )
    assert receipt["content_in_receipt"] is False
    assert "Synthetic baseline observation" not in repr(receipt)
    assert receipt["known_exclusions"]


def test_t5_validation_is_not_activation_and_failed_activation_preserves_active() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    candidate = service.dispatch("recovery.validate", {}, token)
    assert candidate["validated"] is True
    assert candidate["activated"] is False
    assert candidate["active_vault_preserved"] is True
    with pytest.raises(DesktopServiceError, match="CONFIRMATION_REQUIRED"):
        service.dispatch(
            "recovery.activate",
            {"candidate_id": candidate["candidate_id"], "confirmation": "cancel"},
            token,
        )
    activated = service.dispatch(
        "recovery.activate",
        {
            "candidate_id": candidate["candidate_id"],
            "confirmation": "ACTIVATE VALIDATED CANDIDATE",
        },
        token,
    )
    assert activated["activated"] is True
    assert activated["previous_vault_retained"] is True


def test_t6_export_policy_and_confirmation_fail_closed() -> None:
    service = DesktopApplicationService()
    token = _unlock(service)
    with pytest.raises(DesktopServiceError, match="POLICY_REQUIRED"):
        service.dispatch(
            "export.preview",
            {
                "purpose": "missing-policy",
                "audience": "owner",
                "scope": "synthetic",
                "encrypted": True,
                "redacted": True,
            },
            token,
        )
    preview = service.dispatch(
        "export.preview",
        {
            "purpose": "portability",
            "audience": "owner",
            "scope": "synthetic",
            "encrypted": True,
            "redacted": True,
        },
        token,
    )
    with pytest.raises(DesktopServiceError, match="CONFIRMATION_REQUIRED"):
        service.dispatch(
            "export.execute",
            {"preview_id": preview["preview_id"], "confirmation": "cancel"},
            token,
        )
    completed = service.dispatch(
        "export.execute",
        {
            "preview_id": preview["preview_id"],
            "confirmation": "EXPORT SYNTHETIC PACKAGE",
        },
        token,
    )
    assert completed["purpose"] == "portability"
    assert completed["audience"] == "owner"
    assert completed["encrypted"] is True
    assert completed["redacted"] is True
    assert completed["export_is_backup"] is False
