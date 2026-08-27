# ruff: noqa: RUF001
"""V11 Personal retrieval stays local, evidence-linked, and read-only."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from psyche_os.application.guided_exploration import GuidedExplorationService
from psyche_os.application.reflection_sessions import ReflectionSessionService
from psyche_os.personal_mode.context_retrieval import PersonalContextRetrievalService
from psyche_os.personal_mode.schema import initialize_personal_v11


def _service(tmp_path: Path) -> ReflectionSessionService:
    return ReflectionSessionService(
        tmp_path,
        data_mode="real_personal",
        database_key_supplier=lambda: b"r" * 32,
        schema_initializer=initialize_personal_v11,
        schema_version=11,
    )


def _seed(tmp_path: Path) -> tuple[ReflectionSessionService, str, str, str, str]:
    sessions = _service(tmp_path)
    reflection = sessions.create_session("Синтетическое размышление о маяке")
    first = sessions.add_user_turn(
        reflection["session_id"], "Синтетический маяк горел зелёным утром"
    )
    second = sessions.add_user_turn(
        reflection["session_id"], "Позже синтетический маяк был красным"
    )
    guided = GuidedExplorationService(sessions)
    guided.start(reflection["session_id"])
    context_id = sessions.connection.execute(
        "SELECT context_item_id FROM reflection_context_items WHERE session_id=? AND kind='UNKNOWN' LIMIT 1",
        (reflection["session_id"],),
    ).fetchone()[0]
    sessions.connection.execute(
        "UPDATE reflection_context_items SET text='Синтетическая неясность о маяке.' WHERE context_item_id=?",
        (context_id,),
    )
    sessions.connection.execute(
        "INSERT INTO reflection_context_sources(context_item_id,turn_id) VALUES(?,?)",
        (context_id, first["turn_id"]),
    )
    contradiction = "synthetic-contradiction"
    sessions.connection.execute(
        "INSERT INTO reflection_context_items VALUES(?,?,?,?,?,?,?)",
        (
            contradiction,
            reflection["session_id"],
            "light",
            "CONTRADICTION",
            "Синтетические цвета маяка расходятся.",
            "UNRESOLVED",
            "2026-08-20T12:00:00+00:00",
        ),
    )
    for turn_id in (first["turn_id"], second["turn_id"]):
        sessions.connection.execute(
            "INSERT INTO reflection_context_sources(context_item_id,turn_id) VALUES(?,?)",
            (contradiction, turn_id),
        )
    formulation = guided.propose_formulation(reflection["session_id"])
    corrected = guided.correct_formulation(
        formulation["formulation_id"], "Синтетическое уточнение маяка"
    )
    guided.set_formulation_status(corrected["formulation_id"], "CURRENT")
    sessions.connection.execute(
        "INSERT INTO reflection_ai_provenance VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            formulation["formulation_id"],
            "AI",
            "OpenAI",
            "requested-model",
            "synthetic-model",
            "digest",
            "method",
            "manifest",
            "receipt",
            "2026-08-20T12:00:00+00:00",
        ),
    )
    sessions.connection.execute(
        "INSERT INTO reflection_ai_provenance_sources VALUES(?,?)",
        (formulation["formulation_id"], first["turn_id"]),
    )
    for table, column in (
        ("reflection_sessions", "created_at"),
        ("reflection_sessions", "updated_at"),
        ("reflection_turns", "created_at"),
        ("reflection_context_items", "created_at"),
        ("reflection_formulations", "created_at"),
        ("reflection_formulations", "updated_at"),
    ):
        sessions.connection.execute(f"UPDATE {table} SET {column}='2026-08-01T12:00:00+00:00'")
    sessions.connection.commit()
    return (
        sessions,
        reflection["session_id"],
        first["turn_id"],
        formulation["formulation_id"],
        corrected["formulation_id"],
    )


def test_retrieval_finds_source_derived_and_ai_with_exact_provenance(tmp_path: Path) -> None:
    sessions, session_id, turn_id, ai_id, current_id = _seed(tmp_path)
    view = PersonalContextRetrievalService(sessions).search(
        "синтетическ маяк", now=datetime(2026, 8, 27, tzinfo=UTC)
    )
    kinds = {item["result_type"] for item in view["results"]}
    assert {"USER_SOURCE", "UNKNOWN", "CONTRADICTION", "FORMULATION", "AI_PROPOSAL"} <= kinds
    source = next(item for item in view["results"] if item["result_id"] == f"turn:{turn_id}")
    assert source["session_id"] == session_id
    assert source["turn_id"] == turn_id
    ai = next(item for item in view["results"] if item["result_id"] == f"formulation:{ai_id}")
    assert ai["ai_provenance"] == {"provider": "OpenAI", "actual_model": "synthetic-model"}
    assert ai["source_turns"][0]["turn_id"] == turn_id
    current = next(
        item for item in view["results"] if item["result_id"] == f"formulation:{current_id}"
    )
    assert current["status"] == "CURRENT"
    assert current["parent_result_id"] == f"formulation:{ai_id}"
    assert "Формулировка" in current["why_here"]
    sessions.close()


def test_retrieval_filters_period_content_and_formulation_state(tmp_path: Path) -> None:
    sessions, _session_id, _turn_id, _ai_id, current_id = _seed(tmp_path)
    retrieval = PersonalContextRetrievalService(sessions)
    now = datetime(2026, 8, 27, tzinfo=UTC)
    unknowns = retrieval.search("неизвестно", content="UNKNOWN", now=now)
    assert unknowns["results"] and {item["result_type"] for item in unknowns["results"]} == {
        "UNKNOWN"
    }
    current = retrieval.search(
        "синтетическ", content="FORMULATION", formulation_status="CURRENT", now=now
    )
    assert [item["result_id"] for item in current["results"]] == [f"formulation:{current_id}"]
    recent = retrieval.search("маяк", period="7D", now=now)
    assert recent["results"] == []
    all_time = retrieval.search("маяк", period="ALL", now=now)
    assert all_time["total_matches"] > 0
    sessions.close()


def test_related_context_uses_only_stored_source_and_lineage_edges(tmp_path: Path) -> None:
    sessions, _session_id, turn_id, ai_id, current_id = _seed(tmp_path)
    view = PersonalContextRetrievalService(sessions).search(
        "синтетическ", now=datetime(2026, 8, 27, tzinfo=UTC)
    )
    ai = next(item for item in view["results"] if item["result_id"] == f"formulation:{ai_id}")
    relations = {(item["label"], item["why_related"]) for item in ai["related_context"]}
    assert ("Следующая версия", "Это следующая версия рабочей формулировки.") in relations
    assert any(item["result_id"] == f"turn:{turn_id}" for item in ai["related_context"])
    current = next(
        item for item in view["results"] if item["result_id"] == f"formulation:{current_id}"
    )
    assert any(item["label"] == "Предыдущая версия" for item in current["related_context"])
    sessions.close()
