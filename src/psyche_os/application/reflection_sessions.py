"""Encrypted local persistence for the non-canonical Reflection workspace."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from importlib import import_module
import os
from pathlib import Path
import secrets
from typing import Any

from sqlcipher3 import dbapi2

from psyche_os.crypto.envelope import OSKeyWrapError, OSKeyWrapper
from psyche_os.domain.ids import generate_id
from psyche_os.domain.reflection_sessions import SessionRetention, SessionState, TurnActor

MAX_TITLE = 160
MAX_CONTENT = 12_000
MAX_SEARCH_QUERY = 200
SEARCH_STATES = ("ALL", "ACTIVE", "CLOSED")
SEARCH_DEFAULT_LIMIT = 20
SEARCH_MAX_LIMIT = 50
SEARCH_EXCERPT_LENGTH = 200


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


def _search_excerpt(content: str, query: str) -> str:
    """Return a bounded excerpt centred on a SQLite-matched query when possible."""
    if len(content) <= SEARCH_EXCERPT_LENGTH:
        return content
    match_start = content.casefold().find(query.casefold())
    if match_start < 0:
        # SQLite LIKE membership remains authoritative for Unicode edge cases.
        return content[:SEARCH_EXCERPT_LENGTH]
    match_end = match_start + len(query)
    if len(query) >= SEARCH_EXCERPT_LENGTH:
        return content[match_start:match_end]
    body_length = SEARCH_EXCERPT_LENGTH - 2
    start = max(0, match_start - max(0, (body_length - len(query)) // 2))
    start = min(start, len(content) - body_length)
    end = min(len(content), start + body_length)
    prefix = "…" if start else ""
    suffix = "…" if end < len(content) else ""
    return f"{prefix}{content[start:end]}{suffix}"


class ReflectionSessionService:
    """Repository-owned encrypted workspace; no audit or canonical writes occur here."""

    def __init__(
        self,
        app_data: str | Path,
        *,
        key_wrapper_factory: Callable[[], OSKeyWrapper] = OSKeyWrapper,
        data_mode: str = "synthetic_only",
        database_key_supplier: Callable[[], bytes] | None = None,
        schema_initializer: Callable[[Any], None] | None = None,
        schema_version: int = 9,
        database_filename: str = "reflection-workspace.db",
    ) -> None:
        if data_mode not in {"synthetic_only", "real_personal"}:
            raise ReflectionSessionError("STORAGE_UNAVAILABLE")
        self._root = Path(app_data)
        self._root.mkdir(parents=True, exist_ok=True)
        self._key_path = self._root / "reflection-workspace.key.dpapi"
        self._database_path = self._root / database_filename
        self._key_wrapper_factory = key_wrapper_factory
        self._data_mode = data_mode
        self._database_key_supplier = database_key_supplier
        self._schema_initializer = schema_initializer
        self._schema_version = schema_version
        self._connection = self._open()

    def _read_existing_key(self, wrapper: OSKeyWrapper) -> bytes:
        value = wrapper.unprotect(self._key_path.read_bytes())
        if len(value) != 32:
            raise ReflectionSessionError("LOCAL_KEY_UNAVAILABLE")
        return value

    def _key(self) -> bytes:
        if self._database_key_supplier is not None:
            value = self._database_key_supplier()
            if not isinstance(value, bytes) or len(value) != 32:
                raise ReflectionSessionError("LOCAL_KEY_UNAVAILABLE")
            return value
        wrapper = self._key_wrapper_factory()
        if not wrapper.available:
            raise ReflectionSessionError("LOCAL_KEY_UNAVAILABLE")
        try:
            if self._key_path.exists():
                return self._read_existing_key(wrapper)
            value = secrets.token_bytes(32)
            protected = wrapper.protect(value, "PSYCHE OS reflection workspace")
            try:
                descriptor = os.open(
                    self._key_path,
                    os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                    0o600,
                )
            except FileExistsError:
                # Another process won publication. Never overwrite or remove its bytes.
                value = b"\0" * len(value)
                return self._read_existing_key(wrapper)
            with os.fdopen(descriptor, "wb") as key_file:
                key_file.write(protected)
                key_file.flush()
                os.fsync(key_file.fileno())
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
            if self._schema_initializer is not None:
                self._schema_initializer(connection)
            else:
                migrator = import_module("psyche_os.storage." + "migrations").Migrator
                report = migrator(connection).apply(self._schema_version)
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

    @property
    def connection(self) -> Any:
        """Internal workspace connection for bounded V3-A1 operations only."""
        return self._connection

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
                "INSERT INTO reflection_sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    result["session_id"],
                    result["title"],
                    result["state"],
                    result["retention"],
                    self._data_mode,
                    result["created_at"],
                    result["updated_at"],
                    result["closed_at"],
                    result["turn_count"],
                ),
            )
        return result

    def list_sessions(self) -> dict[str, Any]:
        rows = self._connection.execute(
            "SELECT session_id,title,state,retention,created_at,updated_at,closed_at,turn_count "
            "FROM reflection_sessions ORDER BY updated_at DESC, session_id DESC"
        ).fetchall()
        return {"sessions": [self._session(row) for row in rows]}

    def search(
        self,
        query: Any,
        state: Any = "ALL",
        limit: Any = SEARCH_DEFAULT_LIMIT,
        offset: Any = 0,
    ) -> dict[str, Any]:
        """Read-only local search over session titles and USER turn text.

        Deterministic chronological sort, no relevance/ranking, explicit
        truncation truth. Never writes, never calls a provider, never opens
        network/export/persistence paths.
        """
        if not isinstance(query, str):
            raise ReflectionSessionError("INVALID_SEARCH")
        query = query.strip()
        if not query or len(query) > MAX_SEARCH_QUERY:
            raise ReflectionSessionError("INVALID_SEARCH")
        if state not in SEARCH_STATES:
            raise ReflectionSessionError("INVALID_SEARCH")
        if (
            not isinstance(limit, int)
            or not isinstance(offset, int)
            or limit < 1
            or limit > SEARCH_MAX_LIMIT
            or offset < 0
        ):
            raise ReflectionSessionError("INVALID_SEARCH")
        escaped = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{escaped}%"
        state_clause = "" if state == "ALL" else "AND s.state = ?"
        state_args = () if state == "ALL" else (state,)
        title_rows = self._connection.execute(
            "SELECT s.session_id, s.title, s.state, s.updated_at "
            "FROM reflection_sessions s "
            f"WHERE s.title LIKE ? ESCAPE '\\' {state_clause}",
            (pattern, *state_args),
        ).fetchall()
        turn_rows = self._connection.execute(
            "SELECT s.session_id, s.title, s.state, s.updated_at, t.turn_id, t.sequence, t.content "
            "FROM reflection_sessions s "
            "JOIN reflection_turns t ON t.session_id = s.session_id "
            f"WHERE t.actor = 'USER' AND t.content LIKE ? ESCAPE '\\' {state_clause}",
            (pattern, *state_args),
        ).fetchall()
        matches: list[dict[str, Any]] = []
        for row in title_rows:
            matches.append(
                {
                    "session_id": row[0],
                    "session_title": row[1],
                    "session_state": row[2],
                    "session_updated_at": row[3],
                    "match_kind": "TITLE",
                    "turn_id": None,
                    "turn_sequence": None,
                    "excerpt": row[1][:SEARCH_EXCERPT_LENGTH],
                }
            )
        for row in turn_rows:
            content = row[6]
            matches.append(
                {
                    "session_id": row[0],
                    "session_title": row[1],
                    "session_state": row[2],
                    "session_updated_at": row[3],
                    "match_kind": "USER_TURN",
                    "turn_id": row[4],
                    "turn_sequence": row[5],
                    "excerpt": _search_excerpt(content, query),
                }
            )
        matches.sort(
            key=lambda item: (
                item["session_updated_at"],
                item["session_id"],
                -(item["turn_sequence"] if item["turn_sequence"] is not None else 0),
            ),
            reverse=True,
        )
        total = len(matches)
        window = matches[offset : offset + limit]
        returned = len(window)
        has_more = offset + returned < total
        return {
            "query": query,
            "state": state,
            "total_matches": total,
            "returned_count": returned,
            "offset": offset,
            "limit": limit,
            "truncated": has_more,
            "has_more": has_more,
            "results": window,
        }

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
