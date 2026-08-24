"""Slice-C Personal profile dispatcher, protocol, and synthetic E2E proof."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import io
import json
import struct

import pytest

from psyche_os.interfaces.sidecar_protocol import run
from psyche_os.personal_mode.admission import AdmissionDecision
from psyche_os.personal_mode.desktop_service import (
    PERSONAL_ALLOWED_COMMANDS,
    PersonalDesktopApplicationService,
    PersonalDesktopServiceError,
)
from psyche_os.personal_mode.runtime import PersonalRuntime
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


class _DPAPI:
    available = True

    def protect(self, value: bytes, description: str) -> bytes:
        return b"x" * 1024


def _open(now: datetime) -> AdmissionDecision:
    return AdmissionDecision(
        True,
        "evaluation",
        "digest",
        "attestation",
        "profile",
        "candidate",
        now + timedelta(minutes=10),
    )


def _service(tmp_path, now: list[datetime]) -> PersonalDesktopApplicationService:
    return PersonalDesktopApplicationService(
        personal_runtime_paths(local_app_data=tmp_path),
        evaluator=lambda: _open(now[0]),
        clock=lambda: now[0],
        runtime_factory=lambda paths, guard: PersonalRuntime(
            paths, guard, os_wrapper_factory=_DPAPI
        ),
    )


def _request(command: str, payload: dict[str, object], token: str | None = None) -> bytes:
    body = json.dumps(
        {
            "version": "1.0",
            "command": command,
            "correlation_id": command,
            "session_token": token,
            "payload": payload,
        }
    ).encode()
    return struct.pack(">I", len(body)) + body


def test_closed_personal_sidecar_protocol_returns_not_admitted_without_personal_root(
    tmp_path,
) -> None:
    paths = personal_runtime_paths(local_app_data=tmp_path)
    closed = PersonalDesktopApplicationService(paths)
    output = io.BytesIO()
    assert (
        run(io.BytesIO(_request("session.unlock", {"secret": "synthetic secret"})), output, closed)
        == 0
    )
    response_size = struct.unpack(">I", output.getvalue()[:4])[0]
    response = json.loads(output.getvalue()[4 : 4 + response_size])
    assert response["error"] == {"code": "NOT_ADMITTED"}
    assert not paths.root.exists()


def test_personal_synthetic_e2e_across_dispatcher_and_lifecycle(tmp_path) -> None:
    now = [datetime(2026, 8, 24, 12, tzinfo=UTC)]
    content = "SLICE_C_PERSONAL_NEVER_CLOUD_SENTINEL"
    service = _service(tmp_path, now)
    token = service.dispatch("session.unlock", {"secret": "synthetic secret"}, None)[
        "session_token"
    ]
    created = service.dispatch(
        "reflection_session.create", {"title": "Synthetic Personal reflection"}, token
    )
    session_id = created["session_id"]
    service.dispatch(
        "reflection_session.add_turn", {"session_id": session_id, "content": content}, token
    )
    service.dispatch(
        "reflection_session.add_turn",
        {"session_id": session_id, "content": "Second synthetic USER turn"},
        token,
    )
    backup = service.dispatch("backup.create", {"secret": "synthetic secret"}, token)

    service.close()
    restarted = _service(tmp_path, now)
    token = restarted.dispatch("session.unlock", {"secret": "synthetic secret"}, None)[
        "session_token"
    ]
    assert (
        restarted.dispatch("reflection_session.list", {}, token)["sessions"][0]["session_id"]
        == session_id
    )
    assert (
        restarted.dispatch("reflection_session.get", {"session_id": session_id}, token)["turns"][0][
            "content"
        ]
        == content
    )
    assert (
        restarted.dispatch(
            "reflection.search",
            {"query": "NEVER_CLOUD", "state": "ALL", "limit": 20, "offset": 0},
            token,
        )["total_matches"]
        == 1
    )

    exploration = restarted.dispatch(
        "reflection_exploration.start", {"session_id": session_id}, token
    )
    formulation = restarted.dispatch(
        "reflection_exploration.formulation.propose", {"session_id": session_id}, token
    )
    restarted.dispatch(
        "reflection_exploration.formulation.accept",
        {"formulation_id": formulation["formulation_id"]},
        token,
    )
    assert exploration["context"]

    assert restarted.dispatch("rotation.rotate", {"secret": "synthetic secret"}, token) == {
        "from_key_version": "1",
        "to_key_version": "2",
    }
    token = restarted.dispatch("session.unlock", {"secret": "synthetic secret"}, None)[
        "session_token"
    ]
    assert (
        restarted.dispatch("reflection_session.get", {"session_id": session_id}, token)["turns"][0][
            "content"
        ]
        == content
    )
    candidate = restarted.dispatch(
        "recovery.restore_isolated",
        {"backup_id": backup["backup_id"], "secret": "synthetic secret"},
        token,
    )
    assert candidate["key_version"] == "1"
    assert (
        restarted.dispatch("reflection_session.get", {"session_id": session_id}, token)["turns"][0][
            "content"
        ]
        == content
    )
    export = restarted.dispatch("export.owner", {"secret": "synthetic secret"}, token)
    assert export["audience"] == "OWNER_ONLY"

    receipt = restarted.dispatch(
        "reflection_session.delete",
        {"session_id": session_id, "confirmation": "DELETE REFLECTION SESSION"},
        token,
    )
    assert receipt["deleted"] is True
    assert restarted.dispatch("reflection_session.list", {}, token) == {"sessions": []}
    restarted.dispatch("session.lock", {}, token)
    with pytest.raises(PersonalDesktopServiceError) as locked:
        restarted.dispatch("reflection_session.get", {"session_id": session_id}, token)
    assert locked.value.code == "SESSION_REQUIRED"

    # Expiry blocks reads at the central guard and returns no Personal content.
    fixed_decision = _open(now[0])
    admitted = PersonalDesktopApplicationService(
        personal_runtime_paths(local_app_data=tmp_path / "expiry"),
        evaluator=lambda: fixed_decision,
        clock=lambda: now[0],
        runtime_factory=lambda paths, guard: PersonalRuntime(paths, guard, os_wrapper_factory=_DPAPI),
    )
    expiry_token = admitted.dispatch(
        "session.unlock", {"secret": "another synthetic secret"}, None
    )["session_token"]
    now[0] += timedelta(minutes=11)
    with pytest.raises(PersonalDesktopServiceError) as expired:
        admitted.dispatch("reflection_session.list", {}, expiry_token)
    assert expired.value.code == "NOT_ADMITTED"


def test_personal_dispatcher_is_exact_and_provider_free() -> None:
    assert "ai.prepare" not in PERSONAL_ALLOWED_COMMANDS
    assert "reflection_action.create" not in PERSONAL_ALLOWED_COMMANDS
    assert "archive.operate" not in PERSONAL_ALLOWED_COMMANDS
    assert "import.parse" not in PERSONAL_ALLOWED_COMMANDS
