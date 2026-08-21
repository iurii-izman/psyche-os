"""Encrypted local persistence for the non-canonical Reflection workspace."""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path
import secrets
from typing import Any

from sqlcipher3 import dbapi2

from psyche_os.crypto.envelope import OSKeyWrapError, OSKeyWrapper
from psyche_os.domain.ids import generate_id
from psyche_os.domain.reflection_sessions import SessionRetention, SessionState, TurnActor
from psyche_os.storage.migrations import Migrator

MAX_TITLE = 160
MAX_CONTENT = 12_000


class ReflectionSessionError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: Any, maximum: int) -> str:
    if not isinstance(value, str):
        raise ReflectionSessionError("INVALID_PAYLOAD")
    result = value.strip()
    if not result or len(result) > maximum:
        raise ReflectionSessionError("INVALID_PAYLOAD")
    return result


class ReflectionSessionService:
    """Repository-owned encrypted workspace; no audit or canonical writes occur here."""

    def __init__(self, app_data: str | Path) -> None:
        self._root = Path(app_data)
        self._root.mkdir(parents=True, exist_ok=True)
        self._key_path = self._root / "reflection-workspace.key.dpapi"
        self._database_path = self._root / "reflection-workspace.db"
        self._connection = self._open()

    def _key(self) -> bytes:
        wrapper = OSKeyWrapper()
        if not wrapper.available:
            raise ReflectionSessionError("LOCAL_KEY_UNAVAILABLE")
        try:
            if self._key_path.exists():
                value = wrapper.unprotect(self._key_path.read_bytes())
                if len(value) != 32:
                    raise ReflectionSessionError("LOCAL_KEY_UNAVAILABLE")
                return value
            value = secrets.token_bytes(32)
            self._key_path.write_bytes(wrapper.protect(value, "PSYCHE OS reflection workspace"))
            return value
        except (OSError, OSKeyWrapError) as exc:
            raise ReflectionSessionError("LOCAL_KEY_UNAVAILABLE") from exc

    def _open(self) -> Any:
        key = self._key()
        try:
            connection = dbapi2.connect(str(self._database_path))
            connection.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
            connection.execute("PRAGMA foreign_keys = ON")
            row = connection.execute("PRAGMA cipher_version").fetchone()
            if not row or not row[0]:
                raise ReflectionSessionError("STORAGE_UNAVAILABLE")
            report = Migrator(connection).apply(6)
            if not report.success:
                raise ReflectionSessionError("STORAGE_UNAVAILABLE")
            return connection
        except ReflectionSessionError:
            raise
        except Exception as exc:
            raise ReflectionSessionError("STORAGE_UNAVAILABLE") from exc
        finally:
            key = b"\0" * len(key)

    def close(self) -> None:
        self._connection.close()

    def create_session(self, title: Any) -> dict[str, Any]:
        title = _text(title, MAX_TITLE)
        now = _utc_now()
        result = {
            "session_id": generate_id(),
            "title": title,
            "state": SessionState.ACTIVE.value,
            "retention": SessionRetention.ENCRYPTED_LOCAL.value,
            "created_at": now,
            "updated_at": now,
            "closed_at": None,
            "turn_count": 0,
        }
        with self._connection:
            self._connection.execute(
                "INSERT INTO reflection_sessions VALUES (?, ?, ?, ?, 'synthetic_only', ?, ?, ?, ?)",
                (*result.values(),),
            )
        return result

    def list_sessions(self) -> dict[str, Any]:
        rows = self._connection.execute(
            "SELECT session_id,title,state,retention,created_at,updated_at,closed_at,turn_count "
            "FROM reflection_sessions ORDER BY updated_at DESC, session_id DESC"
        ).fetchall()
        return {"sessions": [self._session(row) for row in rows]}

    def get_session(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        row = self._connection.execute(
            "SELECT session_id,title,state,retention,created_at,updated_at,closed_at,turn_count "
            "FROM reflection_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise ReflectionSessionError("SESSION_NOT_FOUND")
        result = self._session(row)
        turns = self._connection.execute(
            "SELECT turn_id,session_id,sequence,actor,created_at,content FROM reflection_turns "
            "WHERE session_id = ? ORDER BY sequence",
            (session_id,),
        ).fetchall()
        result["turns"] = [
            dict(
                zip(
                    ("turn_id", "session_id", "sequence", "actor", "created_at", "content"),
                    turn,
                    strict=True,
                )
            )
            for turn in turns
        ]
        return result

    def add_user_turn(self, session_id: Any, content: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        content = _text(content, MAX_CONTENT)
        now = _utc_now()
        turn_id = generate_id()
        try:
            with self._connection:
                row = self._connection.execute(
                    "SELECT state, turn_count FROM reflection_sessions WHERE session_id = ?",
                    (session_id,),
                ).fetchone()
                if row is None:
                    raise ReflectionSessionError("SESSION_NOT_FOUND")
                if row[0] != SessionState.ACTIVE.value:
                    raise ReflectionSessionError("SESSION_CLOSED")
                sequence = int(row[1]) + 1
                self._connection.execute(
                    "INSERT INTO reflection_turns VALUES (?, ?, ?, ?, ?, ?)",
                    (turn_id, session_id, sequence, TurnActor.USER.value, now, content),
                )
                self._connection.execute(
                    "UPDATE reflection_sessions SET turn_count=?, updated_at=? WHERE session_id=?",
                    (sequence, now, session_id),
                )
        except ReflectionSessionError:
            raise
        return {
            "turn_id": turn_id,
            "session_id": session_id,
            "sequence": sequence,
            "actor": TurnActor.USER.value,
            "created_at": now,
            "content": content,
        }

    def close_session(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        now = _utc_now()
        with self._connection:
            row = self._connection.execute(
                "SELECT state FROM reflection_sessions WHERE session_id=?", (session_id,)
            ).fetchone()
            if row is None:
                raise ReflectionSessionError("SESSION_NOT_FOUND")
            if row[0] != SessionState.ACTIVE.value:
                raise ReflectionSessionError("SESSION_CLOSED")
            self._connection.execute(
                "UPDATE reflection_sessions SET state='CLOSED', closed_at=?, updated_at=? WHERE session_id=?",
                (now, now, session_id),
            )
        return {"session_id": session_id, "state": SessionState.CLOSED.value, "closed_at": now}

    def delete_session(self, session_id: Any, confirmation: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        if confirmation != "DELETE REFLECTION SESSION":
            raise ReflectionSessionError("CONFIRMATION_REQUIRED")
        with self._connection:
            count = self._connection.execute(
                "DELETE FROM reflection_sessions WHERE session_id=?", (session_id,)
            ).rowcount
            if count != 1:
                raise ReflectionSessionError("SESSION_NOT_FOUND")
        return {
            "receipt_id": generate_id(),
            "session_id": session_id,
            "deleted": True,
            "content_in_receipt": False,
        }

    @staticmethod
    def _session(row: Any) -> dict[str, Any]:
        return dict(
            zip(
                (
                    "session_id",
                    "title",
                    "state",
                    "retention",
                    "created_at",
                    "updated_at",
                    "closed_at",
                    "turn_count",
                ),
                row,
                strict=True,
            )
        )


def default_app_data() -> Path:
    configured = os.environ.get("PSYCHE_OS_APP_DATA")
    if configured:
        return Path(configured)
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        raise ReflectionSessionError("STORAGE_UNAVAILABLE")
    return Path(local) / "PSYCHE OS"
