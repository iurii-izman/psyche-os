from __future__ import annotations

from pathlib import Path

import pytest
from sqlcipher3 import dbapi2

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
    evidence_view = guided.get(session["session_id"])
    evidence_formulation = next(item for item in evidence_view["formulations"] if item["formulation_id"] == proposal["formulation_id"])
    assert evidence_formulation["origin"] == "DETERMINISTIC"
    known = next(item for item in initial["context"] if item["kind"] == "KNOWN")
    assert known["source_turn_ids"][0] in evidence_formulation["supporting_turn_ids"]
    assert len(evidence_formulation["supporting_turn_ids"]) == 2
    assert evidence_formulation["uncertainty_text"]
    corrected = guided.correct_formulation(proposal["formulation_id"], "Синтетическое уточнение")
    assert corrected["version"] == proposal["version"] + 1
    assert guided.set_formulation_status(corrected["formulation_id"], "CURRENT")["status"] == "CURRENT"
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


def test_snapshots_preserve_context_state_and_typed_hypothesis_references(tmp_path: Path) -> None:
    sessions = ReflectionSessionService(tmp_path)
    session = sessions.create_session("История состояния")
    sessions.add_user_turn(session["session_id"], "SYNTHETIC: исходное сообщение")
    guided = GuidedExplorationService(sessions)

    initial = guided.start(session["session_id"])
    first_snapshot = initial["snapshots"][0]
    initial_unknown = next(item for item in initial["context"] if item["dimension"] == initial["next_question"]["dimension"])
    assert initial_unknown["state"] == "OPEN"
    assert {ref["relation"] for hypothesis in initial["hypotheses"] for ref in hypothesis["context_refs"]} == {"UNKNOWN"}
    assert all(not hypothesis["support_context_ids"] for hypothesis in initial["hypotheses"])
    assert all(not hypothesis["counterevidence_context_ids"] for hypothesis in initial["hypotheses"])

    updated = guided.answer(initial["next_question"]["question_id"], "Синтетически: на прошлой неделе")
    second_snapshot = updated["snapshots"][0]
    first_context = guided.get_snapshot(first_snapshot["snapshot_id"])["context"]
    second_context = guided.get_snapshot(second_snapshot["snapshot_id"])["context"]
    assert next(item for item in first_context if item["context_item_id"] == initial_unknown["context_item_id"])["state"] == "OPEN"
    assert next(item for item in second_context if item["context_item_id"] == initial_unknown["context_item_id"])["state"] == "RESOLVED"
    assert all(ref["context_item_id"] in {item["context_item_id"] for item in first_context} for hypothesis in guided.get_snapshot(first_snapshot["snapshot_id"])["hypotheses"] for ref in hypothesis["context_refs"])


def test_question_budget_is_three_and_preserves_remaining_unknowns(tmp_path: Path) -> None:
    sessions = ReflectionSessionService(tmp_path)
    session = sessions.create_session("Лимит вопросов")
    sessions.add_user_turn(session["session_id"], "SYNTHETIC: исходное сообщение")
    guided = GuidedExplorationService(sessions)
    state = guided.start(session["session_id"])
    state = guided.answer(state["next_question"]["question_id"], "Синтетически: вчера")
    state = guided.skip(state["next_question"]["question_id"])
    state = guided.answer(state["next_question"]["question_id"], "Синтетически: немного")

    assert state["next_question"] is None
    assert sessions.connection.execute("SELECT COUNT(*) FROM reflection_questions WHERE session_id=?", (session["session_id"],)).fetchone()[0] == 3
    assert any(item["kind"] == "UNKNOWN" and item["state"] == "OPEN" for item in state["context"])


def test_current_formulation_is_unique_and_supersedes_previous(tmp_path: Path) -> None:
    sessions = ReflectionSessionService(tmp_path)
    session = sessions.create_session("Текущая формулировка")
    sessions.add_user_turn(session["session_id"], "SYNTHETIC: исходное сообщение")
    guided = GuidedExplorationService(sessions)
    guided.start(session["session_id"])

    first = guided.propose_formulation(session["session_id"])
    assert guided.set_formulation_status(first["formulation_id"], "CURRENT")["status"] == "CURRENT"
    second = guided.propose_formulation(session["session_id"])
    assert guided.set_formulation_status(second["formulation_id"], "CURRENT")["status"] == "CURRENT"
    statuses = {item["formulation_id"]: item["status"] for item in guided.get(session["session_id"])["formulations"]}
    assert statuses[first["formulation_id"]] == "SUPERSEDED"
    assert statuses[second["formulation_id"]] == "CURRENT"
    assert sessions.connection.execute("SELECT COUNT(*) FROM reflection_formulations WHERE session_id=? AND status='CURRENT'", (session["session_id"],)).fetchone()[0] == 1
    with pytest.raises(dbapi2.IntegrityError):
        sessions.connection.execute(
            "UPDATE reflection_formulations SET status='CURRENT' WHERE formulation_id=?", (first["formulation_id"],)
        )
