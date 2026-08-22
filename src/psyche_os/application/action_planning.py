"""Deterministic V3-A3 action workspace; it never creates canonical evidence."""
# ruff: noqa: RUF001

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Final

from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
    _text,
)
from psyche_os.domain.ids import generate_id

METHOD_VERSION: Final = "v3a3-action-planning-v1"
TEMPLATE_VERSION: Final = "v1"
MAX_TEXT: Final = 12_000
OUTCOME_STATUSES: Final = frozenset({"DONE", "NOT_DONE", "CANCELLED", "UNKNOWN"})
TEMPLATES: Final = (
    ("PAUSE", "Ничего не предпринимать сейчас и оставить вопрос открытым."),
    (
        "OBSERVE_ONE_EXAMPLE",
        "Если подходящий пример естественно возникнет, записать один конкретный случай без намеренной провокации ситуации.",
    ),
    (
        "CLARIFY_ONE_UNKNOWN",
        "Вернуться к одному выбранному открытому вопросу и дополнить его, только если позже появятся новые фактические данные.",
    ),
    (
        "FORMULATE_HUMAN_QUESTION",
        "Сформулировать один вопрос, который пользователь при желании сможет обсудить с выбранным человеком или специалистом.",
    ),
)
TEMPLATE_TEXT: Final = dict(TEMPLATES)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ActionPlanningService:
    """Bounded user-authored plans and outcome notes in the reflection workspace."""

    def __init__(self, sessions: ReflectionSessionService) -> None:
        self.sessions, self.db = sessions, sessions.connection

    def _session(self, session_id: Any, *, mutable: bool) -> str:
        sid = _text(session_id, 64)
        row = self.db.execute(
            "SELECT state FROM reflection_sessions WHERE session_id=?", (sid,)
        ).fetchone()
        if not row:
            raise ReflectionSessionError("SESSION_NOT_FOUND")
        if mutable and row[0] != "ACTIVE":
            raise ReflectionSessionError("SESSION_CLOSED")
        return sid

    def _anchor(self, sid: str, anchor_type: Any, anchor_id: Any) -> tuple[str | None, str | None]:
        if anchor_type is None and anchor_id is None:
            return None, None
        if anchor_type not in {"UNKNOWN", "CONTRADICTION", "FORMULATION"} or not isinstance(
            anchor_id, str
        ):
            raise ReflectionSessionError("INVALID_ANCHOR")
        if anchor_type == "FORMULATION":
            row = self.db.execute(
                "SELECT 1 FROM reflection_formulations WHERE formulation_id=? AND session_id=?",
                (anchor_id, sid),
            ).fetchone()
        else:
            kind = anchor_type
            row = self.db.execute(
                "SELECT 1 FROM reflection_context_items WHERE context_item_id=? AND session_id=? AND kind=? AND state != 'RESOLVED'",
                (anchor_id, sid, kind),
            ).fetchone()
        if not row:
            raise ReflectionSessionError("INVALID_ANCHOR")
        return anchor_type, anchor_id

    def options(
        self, session_id: Any, anchor_type: Any = None, anchor_id: Any = None
    ) -> dict[str, Any]:
        sid = self._session(session_id, mutable=False)
        anchor_type, anchor_id = self._anchor(sid, anchor_type, anchor_id)
        options = [
            {"template_id": template_id, "template_version": TEMPLATE_VERSION, "text": text}
            for template_id, text in TEMPLATES
            if template_id != "CLARIFY_ONE_UNKNOWN" or anchor_type == "UNKNOWN"
        ]
        return {
            "session_id": sid,
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "options": options,
        }

    def _basis(self, sid: str) -> tuple[str | None, str | None]:
        snapshot = self.db.execute(
            "SELECT latest_snapshot_id FROM reflection_explorations WHERE session_id=?", (sid,)
        ).fetchone()
        formulation = self.db.execute(
            "SELECT formulation_id FROM reflection_formulations WHERE session_id=? AND status='CURRENT'",
            (sid,),
        ).fetchone()
        return (
            snapshot[0] if snapshot and snapshot[0] else None,
            formulation[0] if formulation else None,
        )

    def create(
        self,
        session_id: Any,
        user_goal: Any,
        template_id: Any,
        action_text: Any,
        anchor_type: Any = None,
        anchor_id: Any = None,
    ) -> dict[str, Any]:
        sid = self._session(session_id, mutable=True)
        goal, action = _text(user_goal, MAX_TEXT), _text(action_text, MAX_TEXT)
        anchor_type, anchor_id = self._anchor(sid, anchor_type, anchor_id)
        if template_id not in TEMPLATE_TEXT or (
            template_id == "CLARIFY_ONE_UNKNOWN" and anchor_type != "UNKNOWN"
        ):
            raise ReflectionSessionError("INVALID_TEMPLATE")
        now, plan_id = _now(), generate_id()
        snapshot_id, formulation_id = self._basis(sid)
        with self.db:
            previous = self.db.execute(
                "SELECT plan_id FROM reflection_action_plans WHERE session_id=? AND status='CURRENT'",
                (sid,),
            ).fetchone()
            version = self.db.execute(
                "SELECT COALESCE(MAX(version), 0) + 1 FROM reflection_action_plans WHERE session_id=?",
                (sid,),
            ).fetchone()[0]
            if previous:
                self.db.execute(
                    "UPDATE reflection_action_plans SET status='SUPERSEDED',updated_at=? WHERE plan_id=?",
                    (now, previous[0]),
                )
            self.db.execute(
                "INSERT INTO reflection_action_plans VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    plan_id,
                    sid,
                    version,
                    previous[0] if previous else None,
                    "CURRENT",
                    snapshot_id,
                    formulation_id,
                    anchor_type,
                    anchor_id,
                    goal,
                    template_id,
                    TEMPLATE_VERSION,
                    action,
                    METHOD_VERSION,
                    now,
                    now,
                ),
            )
        return self._plan(plan_id)

    def list(self, session_id: Any) -> dict[str, Any]:
        sid = self._session(session_id, mutable=False)
        rows = self.db.execute(
            "SELECT plan_id FROM reflection_action_plans WHERE session_id=? ORDER BY version DESC, plan_id DESC",
            (sid,),
        ).fetchall()
        return {"session_id": sid, "plans": [self._plan(row[0]) for row in rows]}

    def record_outcome(self, plan_id: Any, status: Any, note_text: Any = None) -> dict[str, Any]:
        pid = _text(plan_id, 64)
        if status not in OUTCOME_STATUSES:
            raise ReflectionSessionError("INVALID_OUTCOME")
        note = None if note_text is None else _text(note_text, MAX_TEXT)
        row = self.db.execute(
            "SELECT session_id,status FROM reflection_action_plans WHERE plan_id=?", (pid,)
        ).fetchone()
        if not row:
            raise ReflectionSessionError("PLAN_NOT_FOUND")
        self._session(row[0], mutable=True)
        if row[1] != "CURRENT":
            raise ReflectionSessionError("PLAN_NOT_CURRENT")
        now, outcome_id = _now(), generate_id()
        try:
            with self.db:
                self.db.execute(
                    "INSERT INTO reflection_action_outcomes VALUES (?,?,?,?,?)",
                    (outcome_id, pid, status, note, now),
                )
                self.db.execute(
                    "UPDATE reflection_action_plans SET status='CLOSED',updated_at=? WHERE plan_id=?",
                    (now, pid),
                )
        except Exception as exc:
            raise ReflectionSessionError("OUTCOME_ALREADY_RECORDED") from exc
        return {
            "outcome_id": outcome_id,
            "plan_id": pid,
            "status": status,
            "note_text": note,
            "created_at": now,
        }

    def _plan(self, plan_id: str) -> dict[str, Any]:
        row = self.db.execute(
            "SELECT plan_id,session_id,version,supersedes_plan_id,status,basis_snapshot_id,basis_formulation_id,anchor_type,anchor_id,user_goal,template_id,template_version,action_text,method_version,created_at,updated_at FROM reflection_action_plans WHERE plan_id=?",
            (plan_id,),
        ).fetchone()
        if not row:
            raise ReflectionSessionError("PLAN_NOT_FOUND")
        fields = (
            "plan_id",
            "session_id",
            "version",
            "supersedes_plan_id",
            "status",
            "basis_snapshot_id",
            "basis_formulation_id",
            "anchor_type",
            "anchor_id",
            "user_goal",
            "template_id",
            "template_version",
            "action_text",
            "method_version",
            "created_at",
            "updated_at",
        )
        result = dict(zip(fields, row, strict=True))
        outcome = self.db.execute(
            "SELECT outcome_id,status,note_text,created_at FROM reflection_action_outcomes WHERE plan_id=?",
            (plan_id,),
        ).fetchone()
        result["outcome"] = (
            dict(zip(("outcome_id", "status", "note_text", "created_at"), outcome, strict=True))
            if outcome
            else None
        )
        return result
