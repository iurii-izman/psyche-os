"""Personal Model V1: storage lifecycle, delta validation, privacy, planner."""

from __future__ import annotations

# ruff: noqa: RUF001
import sqlite3

import pytest

from psyche_os.personal_mode.ai_interview import (
    MAX_MODEL_DELTA,
    PersonalAIError,
    PersonalAIInterviewService,
    validate_interview_output,
)
from psyche_os.personal_mode.schema import initialize_personal_v12, initialize_personal_v13


class FakeReflection:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")
        initialize_personal_v13(self.connection)
        self._next = 0

    def create_session(self, title: str) -> dict[str, str]:
        self._next += 1
        value = f"reflection-{self._next}"
        with self.connection:
            self.connection.execute(
                "INSERT INTO reflection_sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    value,
                    title,
                    "ACTIVE",
                    "ENCRYPTED_LOCAL",
                    "real_personal",
                    "2026-01-01T00:00:00+00:00",
                    "2026-01-01T00:00:00+00:00",
                    None,
                    0,
                ),
            )
        return {"session_id": value}


class FakeKeys:
    def configured(self) -> bool:
        return True

    def _consume_for_request(self) -> str:
        return "sk-synthetic"


def create_delta(action: str, **overrides: object) -> dict[str, object]:
    value: dict[str, object] = {
        "action": action,
        "target": "" if action == "CREATE" else "M1",
        "kind": "HYPOTHESIS",
        "text": "Возможно, после насыщенных встреч трудно переключиться на отдых.",
        "temporal_scope": "UNCLEAR",
        "uncertainty": "",
        "supporting": ["S1"],
        "counterevidence": [],
        "reason": "Синтетическое основание из ответа.",
    }
    value.update(overrides)
    return value


class FakeProvider:
    def __init__(self, deltas: list[dict[str, object]] | None = None) -> None:
        self.deltas = deltas or []
        self.calls = 0
        self.last_context: dict[str, object] = {}

    def invoke_ai_interview(
        self, _manifest: dict[str, object], context: dict[str, object], _key: str
    ) -> tuple[dict[str, object], str]:
        self.calls += 1
        self.last_context = context
        deltas, self.deltas = self.deltas, []
        aliases = [str(item["alias"]) for item in context["sources"]]
        return {
            "schema_version": "personal-ai-interview-output-v2",
            "decision": "ASK",
            "question": "В каком конкретном эпизоде это было заметно?",
            "rationale": "Чтобы проверить рабочую версию на наблюдаемом эпизоде.",
            "basis_aliases": aliases,
            "summary": None,
            "next_direction": None,
            "inquiry_items": [],
            "model_delta": deltas,
        }, "gpt-5.6-luna"


def service(
    deltas: list[dict[str, object]] | None = None,
) -> tuple[PersonalAIInterviewService, FakeReflection, FakeProvider]:
    reflection, provider = FakeReflection(), FakeProvider(deltas)
    value = PersonalAIInterviewService(reflection, FakeKeys(), provider)
    return value, reflection, provider


def ready(value: PersonalAIInterviewService) -> str:
    value.set_policy(True)
    session_id = value.start()["interview_session_id"]
    value.grant_consent(session_id)
    return session_id


def turn_one(value: PersonalAIInterviewService, session_id: str) -> dict[str, object]:
    return value.submit(session_id, "submission-1", "Синтетический ответ про встречи и отдых.")


# --- Storage / model lifecycle -------------------------------------------------


def test_create_model_item_from_valid_source_basis_is_derived() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    items = value.model()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "HYPOTHESIS"
    assert item["state"] == "ACTIVE"
    assert item["current"] is not None
    assert item["current"]["support"][0]["content"] == "Синтетический ответ про встречи и отдых."
    # The model item is DERIVED: its revision resolves to an attempt derivation
    # whose basis is the USER source turn, never a SOURCE row itself.
    derivation = reflection.connection.execute(
        "SELECT derivation_id FROM personal_model_revisions WHERE item_id=?",
        (item["item_id"],),
    ).fetchone()[0]
    sources = reflection.connection.execute(
        "SELECT turn_id FROM interview_derivation_sources WHERE derivation_id=?",
        (derivation,),
    ).fetchall()
    assert len(sources) == 1
    assert reflection.connection.execute(
        "SELECT actor FROM reflection_turns WHERE turn_id=?", (sources[0][0],)
    ).fetchone()[0] == "USER"


def test_revision_preserves_old_revision_and_current_view_resolves_newest() -> None:
    value, _reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    provider.deltas = [
        create_delta(
            "REVISE",
            text="Общая версия не подтверждается; паттерн может быть специфичен для встреч с зависимым результатом.",
            supporting=["S1"],
        )
    ]
    value.submit(session_id, "submission-2", "Синтетический второй ответ с уточнением.")
    items = value.model()["items"]
    assert len(items) == 1
    assert items[0]["current"]["text"].startswith("Общая версия не подтверждается")
    statuses = [revision["status"] for revision in items[0]["history"]]
    assert statuses == ["SUPERSEDED", "CURRENT"]
    assert items[0]["history"][0]["text"] == "Возможно, после насыщенных встреч трудно переключиться на отдых."


def test_counterevidence_is_separate_from_supporting_evidence() -> None:
    value, _reflection, _provider = service(
        [create_delta("CREATE", counterevidence=["S1"], supporting=["S1"])]
    )
    session_id = ready(value)
    turn_one(value, session_id)
    current = value.model()["items"][0]["current"]
    assert len(current["support"]) == 1
    assert len(current["counterevidence"]) == 1


def test_owner_correction_is_source_and_contests_without_provider_call() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    calls_before = provider.calls
    item_id = value.model()["items"][0]["item_id"]
    value.challenge(item_id, "Это было верно только для 2021–2022.")
    assert provider.calls == calls_before
    item = value.model()["items"][0]
    assert item["state"] == "CONTESTED"
    assert item["challenges"][0]["text"] == "Это было верно только для 2021–2022."
    # The correction itself is a USER SOURCE turn, inspectable and never AI.
    correction = reflection.connection.execute(
        "SELECT actor,content FROM reflection_turns WHERE content=?",
        ("Это было верно только для 2021–2022.",),
    ).fetchone()
    assert correction == ("USER", "Это было верно только для 2021–2022.")
    # Old AI text remains inspectable in history.
    assert item["history"][-1]["text"] == item["current"]["text"]


def test_resolved_item_is_not_current_active_meaning() -> None:
    value, _reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    # RESOLVE through a second provider turn targeting the item.
    _reflection = None  # keep naming clear
    provider_deltas = [create_delta("RESOLVE", text="", reason="Версия больше не нужна.")]
    value._provider.deltas = provider_deltas  # type: ignore[attr-defined]
    value.submit(session_id, "submission-2", "Синтетический ответ для разрешения версии.")
    item = value.model()["items"][0]
    assert item["state"] == "RESOLVED"
    assert item["current"] is not None  # revision history stays inspectable


def test_deleting_supporting_source_invalidates_dependent_meaning() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    answer_turn = reflection.connection.execute(
        "SELECT turn_id FROM interview_submissions WHERE interview_session_id=?",
        (session_id,),
    ).fetchone()[0]
    with reflection.connection:
        reflection.connection.execute("DELETE FROM reflection_turns WHERE turn_id=?", (answer_turn,))
    item = value.model()["items"][0]
    assert item["state"] == "INVALIDATED"
    assert item["current"] is None


def test_deleted_source_cannot_be_reconstructed_from_model_or_disclosure() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    attempt_id = value.get(session_id)["attempts"][0]["attempt_id"]
    answer_turn = reflection.connection.execute(
        "SELECT turn_id FROM interview_submissions WHERE interview_session_id=?",
        (session_id,),
    ).fetchone()[0]
    with reflection.connection:
        reflection.connection.execute("DELETE FROM reflection_turns WHERE turn_id=?", (answer_turn,))
    # Disclosure keeps content-free attempt facts but no deleted content and
    # no transmitted model item whose lineage died with the source.
    receipt = value.disclosure(attempt_id)
    assert receipt["state"] == "SUCCEEDED"
    assert all("Синтетический ответ" not in str(item) for item in receipt["items"])
    assert receipt["model_items"] == []
    assert value.model()["items"][0]["current"] is None


def test_deleting_owner_correction_source_removes_challenge_relation() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    item_id = value.model()["items"][0]["item_id"]
    value.challenge(item_id, "Синтетическое исправление владельца.")
    assert value.model()["items"][0]["state"] == "CONTESTED"
    correction_turn = reflection.connection.execute(
        "SELECT turn_id FROM reflection_turns WHERE content=?",
        ("Синтетическое исправление владельца.",),
    ).fetchone()[0]
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (correction_turn,)
        )
    item = value.model()["items"][0]
    assert item["state"] == "ACTIVE"
    assert item["challenges"] == []


def test_v13_migration_is_additive_and_semantic_data_neutral() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    initialize_personal_v12(connection)
    with connection:
        connection.execute(
            "INSERT INTO reflection_sessions VALUES('s1','Synthetic','ACTIVE','ENCRYPTED_LOCAL','real_personal','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00',NULL,1)"
        )
        connection.execute(
            "INSERT INTO reflection_turns VALUES('t1','s1',1,'USER','2026-01-01T00:00:00+00:00','Синтетическая запись')"
        )
    initialize_personal_v13(connection)
    versions = [
        row[0]
        for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")
    ]
    assert versions == [10, 11, 12, 13]
    # No semantic backfill: existing rows unchanged, model tables empty.
    assert connection.execute("SELECT count(*) FROM personal_model_items").fetchone() == (0,)
    assert connection.execute(
        "SELECT content FROM reflection_turns WHERE turn_id='t1'"
    ).fetchone() == ("Синтетическая запись",)
    assert connection.execute("SELECT count(*) FROM interview_inquiry_items").fetchone() == (0,)


# --- Provider / model delta ----------------------------------------------------


def test_one_provider_call_applies_question_and_model_delta_atomically() -> None:
    value, _reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    result = turn_one(value, session_id)
    assert provider.calls == 1
    assert result["current_question"] is not None
    assert len(value.model()["items"]) == 1


def test_invalid_model_delta_leaves_answer_durable_without_derived_commit() -> None:
    value, reflection, _provider = service(
        [create_delta("CREATE", supporting=["invented-alias"])]
    )
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        turn_one(value, session_id)
    # USER answer stays durable as SOURCE.
    assert (
        reflection.connection.execute("SELECT count(*) FROM reflection_turns").fetchone()[0] == 1
    )
    # No derived partial commit anywhere.
    assert reflection.connection.execute(
        "SELECT count(*) FROM personal_model_items"
    ).fetchone()[0] == 0
    assert reflection.connection.execute(
        "SELECT count(*) FROM interview_questions"
    ).fetchone()[0] == 0
    assert reflection.connection.execute(
        "SELECT state FROM interview_attempts"
    ).fetchone()[0] == "FAILED"


def test_hallucinated_model_alias_is_rejected() -> None:
    value, _reflection, _provider = service([create_delta("REVISE", target="M9")])
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        turn_one(value, session_id)


def test_duplicate_conflicting_target_updates_are_rejected() -> None:
    value, _reflection, _provider = service(
        [create_delta("CREATE"), create_delta("CREATE")]
    )
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        turn_one(value, session_id)


def test_pattern_with_inadequate_support_is_rejected() -> None:
    value, _reflection, _provider = service(
        [create_delta("CREATE", kind="PATTERN", supporting=["S1"])]
    )
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        turn_one(value, session_id)


def test_create_without_evidence_is_rejected() -> None:
    value, _reflection, _provider = service([create_delta("CREATE", supporting=[])])
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        turn_one(value, session_id)


def test_absolute_trait_wording_is_rejected() -> None:
    raw = {
        "schema_version": "personal-ai-interview-output-v2",
        "decision": "ASK",
        "question": "Что произошло дальше?",
        "rationale": "Проверить эпизод.",
        "basis_aliases": [],
        "summary": None,
        "next_direction": None,
        "inquiry_items": [],
        "model_delta": [
            create_delta("CREATE", text="Вы всегда избегаете конфликтов, это точно.")
        ],
    }
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_UNSAFE"):
        validate_interview_output(raw, {"S1"}, {"M1"})


def test_model_delta_count_is_bounded() -> None:
    value, _reflection, _provider = service(
        [create_delta("CREATE") for _ in range(MAX_MODEL_DELTA + 1)]
    )
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        turn_one(value, session_id)


# --- Privacy / planner ---------------------------------------------------------


def test_model_item_with_ineligible_lineage_is_not_transmitted() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    # The item exists after turn one; on the next turn it is eligible context.
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    assert len(provider.last_context["model"]) == 1
    # Revoke the source policy: the model item's lineage becomes ineligible.
    answer_turn = reflection.connection.execute(
        "SELECT turn_id FROM interview_submissions WHERE interview_session_id=?",
        (session_id,),
    ).fetchone()[0]
    value.set_source_policy([answer_turn], False)
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    assert provider.last_context["model"] == ()
    # Locally the item remains useful and inspectable.
    assert len(value.model()["items"]) == 1


def test_unresolved_contradiction_is_available_to_planner_and_contested_is_not() -> None:
    value, _reflection, provider = service(
        [create_delta("CREATE", kind="CONTRADICTION", supporting=["S1"])]
    )
    session_id = ready(value)
    turn_one(value, session_id)
    # The item exists after turn one; the next turn carries it as context.
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    assert provider.last_context["model"][0]["kind"] == "CONTRADICTION"
    item_id = value.model()["items"][0]["item_id"]
    value.challenge(item_id, "Синтетическое исправление владельца.")
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    # Owner-corrected item is never sent as unqualified current truth.
    assert provider.last_context["model"] == ()


def test_disclosure_lists_transmitted_model_context_separately() -> None:
    value, _reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    attempt_id = value.get(session_id)["attempts"][0]["attempt_id"]
    receipt = value.disclosure(attempt_id)
    assert len(receipt["items"]) == 2
    assert len(receipt["model_items"]) == 1
    model_item = receipt["model_items"][0]
    assert model_item["kind"] == "HYPOTHESIS"
    assert model_item["text"].startswith("Возможно,")
    assert model_item["temporal_scope"] == "UNCLEAR"
