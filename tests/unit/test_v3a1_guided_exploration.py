from __future__ import annotations

from pathlib import Path

import pytest

from psyche_os.application.guided_exploration import GuidedExplorationService
from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
)


def test_guided_exploration_versions_proposals_and_cascade(tmp_path: Path) -> None:
    sessions = ReflectionSessionService(tmp_path)
    session = sessions.create_session("Синтетическая V3-A1")
    sessions.add_user_turn(session["session_id"], "SYNTHETIC: трудно начать задачу")
    guided = GuidedExplorationService(sessions)
    initial = guided.start(session["session_id"])
    assert len(initial["hypotheses"]) == 3
    assert len([item for item in initial["context"] if item["kind"] == "KNOWN"]) == 1
    assert initial["next_question"] is not None
    assert len([item for item in initial["context"] if item["kind"] == "CONTRADICTION"]) == 0

    updated = guided.answer(initial["next_question"]["question_id"], "Синтетически: заметнее вечером")
    assert len(updated["snapshots"]) == 2
    assert updated["next_question"] is not None
    assert updated["next_question"]["question_id"] != initial["next_question"]["question_id"]
    proposal = guided.propose_formulation(session["session_id"])
    assert proposal["status"] == "PROPOSED"
    assert "не диагноз" in proposal["summary"]
    corrected = guided.correct_formulation(proposal["formulation_id"], "Синтетическое уточнение")
    assert corrected["version"] == proposal["version"] + 1
    assert guided.set_formulation_status(corrected["formulation_id"], "ACCEPTED")["status"] == "ACCEPTED"
    sessions.close_session(session["session_id"])
    with pytest.raises(ReflectionSessionError, match="SESSION_CLOSED"):
        guided.propose_formulation(session["session_id"])
    sessions.delete_session(session["session_id"], "DELETE REFLECTION SESSION")
    assert sessions.connection.execute("SELECT COUNT(*) FROM reflection_exploration_snapshots").fetchone()[0] == 0
    sessions.close()


def test_skip_is_explicit_and_does_not_fabricate_answer(tmp_path: Path) -> None:
    sessions = ReflectionSessionService(tmp_path)
    session = sessions.create_session("Пропуск")
    sessions.add_user_turn(session["session_id"], "SYNTHETIC: исходное сообщение")
    guided = GuidedExplorationService(sessions)
    state = guided.start(session["session_id"])
    skipped = guided.skip(state["next_question"]["question_id"])
    assert any(item["state"] == "SKIPPED" for item in skipped["context"])
    assert len(sessions.get_session(session["session_id"])["turns"]) == 1
