from __future__ import annotations

from pathlib import Path

import pytest

from psyche_os.application.action_planning import TEMPLATE_VERSION, ActionPlanningService
from psyche_os.application.guided_exploration import GuidedExplorationService
from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
)


def _workspace(
    tmp_path: Path,
) -> tuple[
    ReflectionSessionService, GuidedExplorationService, ActionPlanningService, dict[str, object]
]:
    sessions = ReflectionSessionService(tmp_path)
    session = sessions.create_session("Синтетическая V3-A3")
    sessions.add_user_turn(session["session_id"], "SYNTHETIC: исходный ответ")
    guided = GuidedExplorationService(sessions)
    guided.start(session["session_id"])
    proposal = guided.propose_formulation(session["session_id"])
    guided.set_formulation_status(proposal["formulation_id"], "CURRENT")
    return sessions, guided, ActionPlanningService(sessions), session


def test_templates_are_closed_unranked_and_unknown_anchor_is_validated(tmp_path: Path) -> None:
    sessions, guided, actions, session = _workspace(tmp_path)
    sid = str(session["session_id"])
    without_anchor = actions.options(sid)
    assert [option["template_id"] for option in without_anchor["options"]] == [
        "PAUSE",
        "OBSERVE_ONE_EXAMPLE",
        "FORMULATE_HUMAN_QUESTION",
    ]
    assert all(
        set(option) == {"template_id", "template_version", "text"}
        for option in without_anchor["options"]
    )
    assert all(
        option["template_version"] == TEMPLATE_VERSION for option in without_anchor["options"]
    )
    unknown = next(
        item
        for item in guided.get(sid)["context"]
        if item["kind"] == "UNKNOWN" and item["state"] == "OPEN"
    )
    with_unknown = actions.options(sid, "UNKNOWN", unknown["context_item_id"])
    assert [option["template_id"] for option in with_unknown["options"]] == [
        "PAUSE",
        "OBSERVE_ONE_EXAMPLE",
        "CLARIFY_ONE_UNKNOWN",
        "FORMULATE_HUMAN_QUESTION",
    ]
    foreign = sessions.create_session("Другая синтетическая сессия")
    with pytest.raises(ReflectionSessionError, match="INVALID_ANCHOR"):
        actions.options(foreign["session_id"], "UNKNOWN", unknown["context_item_id"])


def test_plans_capture_backend_basis_preserve_history_and_outcomes_are_not_evidence(
    tmp_path: Path,
) -> None:
    sessions, guided, actions, session = _workspace(tmp_path)
    sid = str(session["session_id"])
    unknown = next(
        item
        for item in guided.get(sid)["context"]
        if item["kind"] == "UNKNOWN" and item["state"] == "OPEN"
    )
    before = {
        table: sessions.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in (
            "reports",
            "observations",
            "assertions",
            "claims",
            "evidence_links",
            "personal_model_snapshots",
        )
    }
    first = actions.create(
        sid,
        "Моя синтетическая цель",
        "CLARIFY_ONE_UNKNOWN",
        "Мой изменённый текст шага",
        "UNKNOWN",
        unknown["context_item_id"],
    )
    assert first["status"] == "CURRENT"
    assert first["basis_snapshot_id"] is not None
    assert first["basis_formulation_id"] is not None
    second = actions.create(sid, "Другая синтетическая цель", "PAUSE", "Оставить вопрос открытым")
    history = actions.list(sid)["plans"]
    assert [plan["status"] for plan in history] == ["CURRENT", "SUPERSEDED"]
    assert second["supersedes_plan_id"] == first["plan_id"]
    outcome = actions.record_outcome(
        second["plan_id"], "DONE", "Синтетическая отметка пользователя"
    )
    assert outcome["status"] == "DONE"
    assert actions.list(sid)["plans"][0]["status"] == "CLOSED"
    assert {
        table: sessions.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in before
    } == before
    with pytest.raises(ReflectionSessionError, match="PLAN_NOT_CURRENT"):
        actions.record_outcome(second["plan_id"], "DONE")


def test_closed_session_rejects_action_writes_and_session_deletion_cascades(tmp_path: Path) -> None:
    sessions, _guided, actions, session = _workspace(tmp_path)
    sid = str(session["session_id"])
    plan = actions.create(sid, "Синтетическая цель", "PAUSE", "Пауза")
    actions.record_outcome(plan["plan_id"], "UNKNOWN", "Синтетическая отметка")
    current = actions.create(sid, "Следующая синтетическая цель", "PAUSE", "Пауза")
    sessions.close_session(sid)
    with pytest.raises(ReflectionSessionError, match="SESSION_CLOSED"):
        actions.create(sid, "Другая цель", "PAUSE", "Пауза")
    with pytest.raises(ReflectionSessionError, match="SESSION_CLOSED"):
        actions.record_outcome(current["plan_id"], "UNKNOWN")
    sessions.delete_session(sid, "DELETE REFLECTION SESSION")
    assert (
        sessions.connection.execute("SELECT COUNT(*) FROM reflection_action_plans").fetchone()[0]
        == 0
    )
    assert (
        sessions.connection.execute("SELECT COUNT(*) FROM reflection_action_outcomes").fetchone()[0]
        == 0
    )
