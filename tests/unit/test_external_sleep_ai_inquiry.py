from __future__ import annotations

import sqlite3

import pytest

from psyche_os.personal_mode.ai_interview import PersonalAIError, validate_interview_output
from psyche_os.personal_mode.package_format import (
    create_personal_package,
    restore_personal_package,
    verify_personal_package,
)
from psyche_os.personal_mode.schema import initialize_personal_v15, initialize_personal_v16


def _output(*, supporting: list[str], basis: list[str]) -> dict[str, object]:
    return {
        "schema_version": "personal-ai-interview-output-v3", "decision": "ASK",
        "question": "Что вы замечали утром?", "rationale": "Проверить рабочую версию.",
        "basis_aliases": basis, "summary": None, "next_direction": None,
        "inquiry_items": [], "change_delta": None,
        "model_delta": [{"action": "CREATE", "target": "", "kind": "HYPOTHESIS", "text": "Одна рабочая версия: это могло совпасть с короткой ночью.", "temporal_scope": "UNCLEAR", "uncertainty": "", "supporting": supporting, "counterevidence": ["E1"], "reason": "Нужна проверка."}],
    }


def test_v16_is_additive_and_package_v9_round_trips() -> None:
    source, restored = sqlite3.connect(":memory:"), sqlite3.connect(":memory:")
    for connection in (source, restored):
        connection.execute("PRAGMA foreign_keys=ON")
    initialize_personal_v16(source)
    assert [row[0] for row in source.execute("SELECT version FROM schema_migrations")] == list(range(10, 17))
    package = create_personal_package(source)
    assert package["schema_version"] == 16 and package["format_version"] == 9 and verify_personal_package(package)
    restore_personal_package(package, restored)
    assert create_personal_package(restored)["package_checksum"] == package["package_checksum"]


def test_v15_migrates_atomically_to_v16() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_personal_v15(connection)
    initialize_personal_v16(connection)
    assert connection.execute("SELECT count(*) FROM interview_attempt_external_items").fetchone()[0] == 0


def test_external_question_is_allowed_but_model_create_needs_user_support() -> None:
    accepted = validate_interview_output(_output(supporting=["S1", "E1"], basis=["E1"]), {"S1", "E1"}, user_aliases=frozenset({"S1"}))
    assert accepted["basis_aliases"] == ["E1"]
    with pytest.raises(PersonalAIError):
        validate_interview_output(_output(supporting=["E1"], basis=["E1"]), {"S1", "E1"}, user_aliases=frozenset({"S1"}))


@pytest.mark.parametrize("text", ["Сон вызвал это состояние.", "Из-за недосыпа вам плохо.", "Sleep caused your state.", "Sleep leads to your psychological state."])
def test_external_causal_language_is_rejected(text: str) -> None:
    payload = _output(supporting=["S1", "E1"], basis=["E1"])
    payload["model_delta"] = [{**payload["model_delta"][0], "text": text}]  # type: ignore[index]
    with pytest.raises(PersonalAIError):
        validate_interview_output(payload, {"S1", "E1"}, user_aliases=frozenset({"S1"}))
