from __future__ import annotations

from pathlib import Path

import pytest

from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
)


def test_reflection_workspace_persists_closes_and_deletes(tmp_path: Path) -> None:
    first = ReflectionSessionService(tmp_path)
    session = first.create_session("Синтетическая сессия")
    turn = first.add_user_turn(session["session_id"], "SYNTHETIC-V3A0-CANARY")
    assert turn["sequence"] == 1
    first.close()

    resumed = ReflectionSessionService(tmp_path)
    loaded = resumed.get_session(session["session_id"])
    assert loaded["turns"][0]["content"] == "SYNTHETIC-V3A0-CANARY"
    resumed.close_session(session["session_id"])
    with pytest.raises(ReflectionSessionError, match="SESSION_CLOSED"):
        resumed.add_user_turn(session["session_id"], "ещё")
    receipt = resumed.delete_session(session["session_id"], "DELETE REFLECTION SESSION")
    assert receipt["content_in_receipt"] is False
    with pytest.raises(ReflectionSessionError, match="SESSION_NOT_FOUND"):
        resumed.get_session(session["session_id"])
    resumed.close()


def test_reflection_content_is_not_plaintext_database_bytes(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    session = service.create_session("Тест")
    service.add_user_turn(session["session_id"], "V3A0-RAW-DB-CANARY")
    service.close()
    assert b"V3A0-RAW-DB-CANARY" not in (tmp_path / "reflection-workspace.db").read_bytes()
