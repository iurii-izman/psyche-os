from __future__ import annotations

from pathlib import Path
import threading

import pytest

from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
)


class _FakeOSKeyWrapper:
    available = True

    def protect(self, value: bytes, description: str = "") -> bytes:
        return b"fake-dpapi:" + value

    def unprotect(self, protected: bytes) -> bytes:
        if not protected.startswith(b"fake-dpapi:"):
            raise OSError("invalid test wrap")
        return protected.removeprefix(b"fake-dpapi:")


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


def test_reflection_first_start_key_publication_is_exclusive(tmp_path: Path) -> None:
    barrier = threading.Barrier(2)
    opened: list[bool] = []
    failures: list[ReflectionSessionError] = []

    def open_service() -> None:
        barrier.wait()
        try:
            service = ReflectionSessionService(tmp_path, key_wrapper_factory=_FakeOSKeyWrapper)
            service.close()
            opened.append(True)
        except ReflectionSessionError as exc:
            failures.append(exc)

    first = threading.Thread(target=open_service)
    second = threading.Thread(target=open_service)
    first.start()
    second.start()
    first.join(timeout=10)
    second.join(timeout=10)
    assert not first.is_alive() and not second.is_alive()
    assert opened
    assert all(error.code in {"LOCAL_KEY_UNAVAILABLE", "STORAGE_UNAVAILABLE"} for error in failures)

    winner = (tmp_path / "reflection-workspace.key.dpapi").read_bytes()
    assert winner.startswith(b"fake-dpapi:")
    resumed = ReflectionSessionService(tmp_path, key_wrapper_factory=_FakeOSKeyWrapper)
    session = resumed.create_session("Synthetic concurrent key proof")
    resumed.close()
    reopened = ReflectionSessionService(tmp_path, key_wrapper_factory=_FakeOSKeyWrapper)
    assert reopened.get_session(session["session_id"])["title"] == "Synthetic concurrent key proof"
    assert (tmp_path / "reflection-workspace.key.dpapi").read_bytes() == winner
    reopened.close()
