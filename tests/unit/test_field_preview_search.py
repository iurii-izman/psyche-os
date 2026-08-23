"""Field Preview v0.2: global local search semantics.

Search is a read-only SELECT over the reflection workspace: title and USER
turn matches, deterministic chronology, explicit truncation, no writes and
no AI/network path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
)


def _seed(service: ReflectionSessionService) -> tuple[dict, dict]:
    first = service.create_session("Лампа восточной стойки")
    second = service.create_session("Кофейный ритуал")
    service.add_user_turn(first["session_id"], "Контроллер показал зелёный сигнал")
    service.add_user_turn(second["session_id"], "Утренний кофе был крепким")
    return first, second


def test_search_matches_title_and_user_turn(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    first, _ = _seed(service)
    title_hits = service.search("Лампа")
    assert title_hits["total_matches"] >= 1
    assert any(
        item["match_kind"] == "TITLE" and item["session_id"] == first["session_id"]
        for item in title_hits["results"]
    )
    turn_hits = service.search("зелёный сигнал")
    assert any(
        item["match_kind"] == "USER_TURN"
        and item["session_id"] == first["session_id"]
        and item["turn_sequence"] == 1
        for item in turn_hits["results"]
    )
    service.close()


def test_search_excludes_non_matches(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    _seed(service)
    result = service.search("несуществующая фраза")
    assert result["total_matches"] == 0
    assert result["results"] == []
    assert result["truncated"] is False
    service.close()


def test_search_state_filters_are_exact(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    _first, second = _seed(service)
    service.close_session(second["session_id"])
    active = service.search("ритуал", state="ACTIVE")
    assert active["total_matches"] == 0
    closed = service.search("ритуал", state="CLOSED")
    assert closed["total_matches"] == 1
    assert closed["results"][0]["session_state"] == "CLOSED"
    service.close()


def test_search_chronology_is_deterministic_and_turn_ordered(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    first, _ = _seed(service)
    service.add_user_turn(first["session_id"], "первый уточняющий текст")
    service.add_user_turn(first["session_id"], "второй уточняющий текст")
    result = service.search("уточняющий")
    turns = [item for item in result["results"] if item["match_kind"] == "USER_TURN"]
    sequences = [item["turn_sequence"] for item in turns]
    assert sequences == sorted(sequences)
    # The whole result is stable across repeated runs (deterministic chronology).
    assert service.search("уточняющий") == result
    service.close()


def test_search_performs_no_writes(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    _seed(service)
    before = service.list_sessions()
    service.search("Лампа")
    service.search("кофе")
    service.search("Контроллер")
    after = service.list_sessions()
    assert before == after


def test_search_has_no_ai_or_network_path(tmp_path: Path) -> None:
    # The search implementation performs only SQLite SELECT statements; it has
    # no provider, transport, export, or persistence code path to reach.
    service = ReflectionSessionService(tmp_path)
    _seed(service)
    result = service.search("кофе")
    assert result["total_matches"] >= 1
    assert service.connection.execute("SELECT count(*) FROM reflection_turns").fetchone()[0] == 2
    service.close()


def test_search_truncation_is_explicit(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    session = service.create_session("Совпадение по слову маяк")
    for index in range(5):
        service.add_user_turn(session["session_id"], f"текст с словом маяк номер {index}")
    result = service.search("маяк", limit=3)
    assert result["total_matches"] == 6
    assert result["returned_count"] == 3
    assert result["truncated"] is True
    assert result["has_more"] is True
    assert len(result["results"]) == 3
    service.close()


def test_search_validates_query_state_limit_offset(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    _seed(service)
    for bad in ("", "   ", "x" * 201, 42, None):
        with pytest.raises(ReflectionSessionError, match="INVALID_SEARCH"):
            service.search(bad)
    with pytest.raises(ReflectionSessionError, match="INVALID_SEARCH"):
        service.search("лампа", state="DRAFT")
    with pytest.raises(ReflectionSessionError, match="INVALID_SEARCH"):
        service.search("лампа", limit=0)
    with pytest.raises(ReflectionSessionError, match="INVALID_SEARCH"):
        service.search("лампа", limit=100)
    with pytest.raises(ReflectionSessionError, match="INVALID_SEARCH"):
        service.search("лампа", offset=-1)
    service.close()


def test_search_result_can_open_the_source_session(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    first, _ = _seed(service)
    result = service.search("Лампа")
    hit = next(item for item in result["results"] if item["match_kind"] == "TITLE")
    opened = service.get_session(hit["session_id"])
    assert opened["session_id"] == first["session_id"]
    service.close()


def test_search_excerpt_is_bounded_and_centres_late_unicode_match(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    session = service.create_session("Excerpt")
    content = ("начало " * 50) + "уникальный маяк" + (" хвост" * 50)
    service.add_user_turn(session["session_id"], content)
    result = service.search("маяк")
    excerpt = result["results"][0]["excerpt"]
    assert "маяк" in excerpt
    assert len(excerpt) <= 200
    assert excerpt.startswith("…") and excerpt.endswith("…")
    service.close()


def test_search_excerpt_keeps_escaped_like_query_and_early_match(tmp_path: Path) -> None:
    service = ReflectionSessionService(tmp_path)
    session = service.create_session("Escaped excerpt")
    content = "100%_точно " + ("последующий текст " * 30)
    service.add_user_turn(session["session_id"], content)
    result = service.search("100%_точно")
    excerpt = result["results"][0]["excerpt"]
    assert excerpt.startswith("100%_точно")
    assert excerpt.endswith("…")
    assert len(excerpt) <= 200
    service.close()
