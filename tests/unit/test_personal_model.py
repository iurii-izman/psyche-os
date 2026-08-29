"""Personal Model V1: storage lifecycle, delta validation, privacy, planner."""

from __future__ import annotations

# ruff: noqa: RUF001
import sqlite3
import json

import pytest

from psyche_os.adapters.e07_provider import OpenAIReflectionProvider
from psyche_os.personal_mode.ai_interview import (
    MAX_MODEL_DELTA,
    PersonalAIError,
    PersonalAIInterviewService,
    validate_change_delta,
    validate_interview_output,
)
from psyche_os.personal_mode.package_format import (
    create_personal_package,
    restore_personal_package,
    verify_personal_package,
)
from psyche_os.personal_mode.schema import initialize_personal_v12, initialize_personal_v13, initialize_personal_v14


class FakeReflection:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")
        initialize_personal_v14(self.connection)
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


def change_proposal() -> dict[str, object]:
    return {
        "action": "PROPOSE", "kind": "EXPERIMENT", "target_model_aliases": ["M1"],
        "title": "Короткая пауза после встречи", "reason": "Проверить рабочую версию.",
        "instructions": "После встречи сделать короткую паузу без новой информации.",
        "observation_prompt": "Что произошло при переключении?", "expected_signal": "Переключаться немного легче.",
        "counter_signal": "Разницы нет или стало хуже.", "duration_days": 5,
        "stop_conditions": "Остановить в любой момент.", "risk_level": "LOW", "reversible": True, "self_directed": True,
    }


class FakeProvider:
    def __init__(self, deltas: list[dict[str, object]] | None = None) -> None:
        self.deltas = deltas or []
        self.change_delta: dict[str, object] | None = None
        self.calls = 0
        self.last_context: dict[str, object] = {}

    def invoke_ai_interview(
        self, _manifest: dict[str, object], context: dict[str, object], _key: str
    ) -> tuple[dict[str, object], str]:
        self.calls += 1
        self.last_context = context
        deltas, self.deltas = self.deltas, []
        aliases = [str(item["alias"]) for item in context["sources"]]
        result: dict[str, object] = {
            "schema_version": "personal-ai-interview-output-v3" if self.change_delta is not None else "personal-ai-interview-output-v2",
            "decision": "ASK",
            "question": "В каком конкретном эпизоде это было заметно?",
            "rationale": "Чтобы проверить рабочую версию на наблюдаемом эпизоде.",
            "basis_aliases": aliases,
            "summary": None,
            "next_direction": None,
            "inquiry_items": [],
            "model_delta": deltas,
        }
        if self.change_delta is not None:
            result["change_delta"] = self.change_delta
            self.change_delta = None
        return result, "gpt-5.6-luna"


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


def test_change_proposal_requires_exact_low_risk_model_target() -> None:
    proposal = {
        "action": "PROPOSE", "kind": "EXPERIMENT", "target_model_aliases": ["M1"],
        "title": "Короткая пауза", "reason": "Проверить рабочую версию.",
        "instructions": "После встречи сделать короткую паузу.",
        "observation_prompt": "Что изменилось при переключении?",
        "expected_signal": "Переключаться немного легче.",
        "counter_signal": "Разницы нет.", "duration_days": 5,
        "stop_conditions": "Остановить в любой момент.", "risk_level": "LOW",
        "reversible": True, "self_directed": True,
    }
    assert validate_change_delta(proposal, {"M1"})["kind"] == "EXPERIMENT"
    proposal["risk_level"] = "MEDIUM"
    with pytest.raises(PersonalAIError):
        validate_change_delta(proposal, {"M1"})


def test_provider_change_proposal_schema_uses_model_aliases_not_source_aliases() -> None:
    captured: list[object] = []

    class Response:
        def read(self, _limit: int) -> bytes:
            return json.dumps({"model": "gpt-5.6-luna", "output": [{"content": [{"type": "output_text", "text": "{}"}]}]}).encode()
        def __enter__(self) -> "Response": return self
        def __exit__(self, *_: object) -> bool: return False

    provider = OpenAIReflectionProvider(api_key="synthetic-key", transport=lambda request, timeout: captured.append(request) or Response())
    provider.invoke_ai_interview(
        {"profile_id": "local_personal_ai_interview_openai_windows_v1", "model": "gpt-5.6-luna"},
        {"sources": ({"alias": "S1", "content": "Synthetic source"},), "inquiry": (), "planning": (), "model": ({"alias": "M1", "kind": "HYPOTHESIS", "text": "Synthetic model", "temporal_scope": "UNCLEAR", "uncertainty": None, "supporting": [], "counterevidence": [], "state": "ACTIVE"},), "changes": ()},
        "synthetic-key",
    )
    schema = json.loads(captured[0].data)["text"]["format"]["schema"]["properties"]["change_delta"]["anyOf"]
    proposal_schema = next(item for item in schema if item.get("properties", {}).get("action", {}).get("enum") == ["PROPOSE"])
    assert proposal_schema["properties"]["target_model_aliases"]["items"]["enum"] == ["M1"]
    assert "S1" not in proposal_schema["properties"]["target_model_aliases"]["items"]["enum"]
    assert validate_change_delta(change_proposal(), {"M1"})["target_model_aliases"] == ["M1"]


def test_change_activation_and_observations_are_local_owner_source() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    provider.change_delta = change_proposal()
    value.submit(session_id, "proposal", "Синтетический ответ для плана.")
    plan = value.changes()["plans"][0]
    calls = provider.calls
    value.change_control(plan["plan_id"], "ACTIVATE")
    assert provider.calls == calls
    observation = value.observe_change(plan["plan_id"], "После паузы переключение было немного легче.", "BETTER")
    assert observation["source"] == "USER"
    assert reflection.connection.execute("SELECT actor FROM reflection_turns WHERE turn_id=?", (observation["turn_id"],)).fetchone() == ("USER",)
    assert value.changes()["plans"][0]["observations"][0]["ai_eligible"] is False
    value.allow_change_observations(plan["plan_id"], True)
    assert value.changes()["plans"][0]["observations"][0]["ai_eligible"] is True


def test_stopped_plan_stays_out_of_normal_context_but_enters_its_explicit_review() -> None:
    value, _reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    provider.change_delta = change_proposal()
    value.submit(session_id, "proposal", "Синтетический ответ для плана.")
    plan_id = value.changes()["plans"][0]["plan_id"]
    calls = provider.calls
    value.change_control(plan_id, "ACTIVATE")
    value.change_control(plan_id, "STOP")
    assert provider.calls == calls
    ordinary = ready(value)
    value.request_first_question(ordinary)
    assert provider.last_context["changes"] == ()
    review = value.start_change_review(plan_id)["interview_session_id"]
    value.grant_consent(review)
    value.request_first_question(review)
    changes = provider.last_context["changes"]
    assert len(changes) == 1 and changes[0]["alias"] == "C1"
    assert changes[0]["plan_id"] == plan_id and changes[0]["state"] == "STOPPED"
    assert changes[0]["review_target"] is True


def test_explicit_review_is_one_call_and_commits_distinct_outcomes_atomically() -> None:
    value, _reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    provider.change_delta = change_proposal()
    value.submit(session_id, "proposal", "Синтетический ответ для плана.")
    plan_id = value.changes()["plans"][0]["plan_id"]
    value.change_control(plan_id, "ACTIVATE")
    value.observe_change(plan_id, "Пауза не изменила переключение.", "SAME")
    value.allow_change_observations(plan_id, True)
    review_session = value.start_change_review(plan_id)["interview_session_id"]
    value.grant_consent(review_session)
    provider.change_delta = {
        "action": "REVIEW", "target_change_alias": "C1", "practical_effect": "NO_CLEAR_EFFECT",
        "epistemic_outcome": "WEAKENED", "summary": "Практического эффекта пока не видно.",
        "what_changed_in_understanding": "Это ослабляет рабочую версию о паузе.", "recommended_next": "COMPLETE",
    }
    before = provider.calls
    value.request_first_question(review_session)
    assert provider.calls == before + 1
    plan = value.changes()["plans"][0]
    assert plan["state"] == "COMPLETED"
    assert plan["review"]["practical_effect"] == "NO_CLEAR_EFFECT"
    assert plan["review"]["epistemic_outcome"] == "WEAKENED"


def test_deleting_review_observation_reopens_only_ai_completed_plan() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    provider.change_delta = change_proposal()
    value.submit(session_id, "proposal", "Синтетический ответ для плана.")
    plan_id = value.changes()["plans"][0]["plan_id"]
    value.change_control(plan_id, "ACTIVATE")
    observation = value.observe_change(plan_id, "Пауза не изменила переключение.", "SAME")
    value.allow_change_observations(plan_id, True)
    review_session = value.start_change_review(plan_id)["interview_session_id"]
    value.grant_consent(review_session)
    provider.change_delta = {"action": "REVIEW", "target_change_alias": "C1", "practical_effect": "NO_CLEAR_EFFECT", "epistemic_outcome": "WEAKENED", "summary": "Эффекта пока не видно.", "what_changed_in_understanding": "Версия ослаблена.", "recommended_next": "COMPLETE"}
    value.request_first_question(review_session)
    assert reflection.connection.execute("SELECT state,ended_at,completion_review_id FROM change_plans WHERE plan_id=?", (plan_id,)).fetchone()[0] == "COMPLETED"
    calls = provider.calls
    with reflection.connection:
        reflection.connection.execute("DELETE FROM reflection_turns WHERE turn_id=?", (observation["turn_id"],))
    assert provider.calls == calls
    assert reflection.connection.execute("SELECT count(*) FROM change_reviews WHERE plan_id=?", (plan_id,)).fetchone() == (0,)
    assert reflection.connection.execute("SELECT state,ended_at,completion_review_id FROM change_plans WHERE plan_id=?", (plan_id,)).fetchone() == ("ACTIVE", None, None)


def test_change_rejects_prohibited_intervention_language() -> None:
    proposal = change_proposal()
    proposal["instructions"] = "Изменить дозировку лекарства."
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_UNSAFE"):
        validate_change_delta(proposal, {"M1"})


def test_v14_change_package_round_trip_preserves_nonempty_plan_observation_and_review() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    provider.change_delta = change_proposal()
    value.submit(session_id, "proposal", "Синтетический ответ для плана.")
    plan_id = value.changes()["plans"][0]["plan_id"]
    value.change_control(plan_id, "ACTIVATE")
    value.observe_change(plan_id, "Пауза не изменила переключение.", "SAME")
    value.allow_change_observations(plan_id, True)
    review_session = value.start_change_review(plan_id)["interview_session_id"]
    value.grant_consent(review_session)
    provider.change_delta = {
        "action": "REVIEW", "target_change_alias": "C1", "practical_effect": "NO_CLEAR_EFFECT",
        "epistemic_outcome": "INCONCLUSIVE", "summary": "Данных пока недостаточно.",
        "what_changed_in_understanding": "Версия пока не отделена от контекста.", "recommended_next": "COMPLETE",
    }
    value.request_first_question(review_session)
    package = create_personal_package(reflection.connection)
    assert package["schema_version"] == 14 and verify_personal_package(package)
    restored = sqlite3.connect(":memory:")
    restored.execute("PRAGMA foreign_keys=ON")
    restore_personal_package(package, restored)
    assert create_personal_package(restored)["package_checksum"] == package["package_checksum"]


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


def test_contested_item_is_investigable_only_with_eligible_correction_lineage() -> None:
    value, reflection, provider = service(
        [create_delta("CREATE", kind="CONTRADICTION", supporting=["S1"])]
    )
    session_id = ready(value)
    turn_one(value, session_id)
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    assert provider.last_context["model"][0]["kind"] == "CONTRADICTION"
    item_id = value.model()["items"][0]["item_id"]
    value.challenge(item_id, "Синтетическое исправление владельца.")
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    # The owner correction turn has no cloud policy by default, so the
    # owner-challenged item is never transmitted (fail closed).
    assert provider.last_context["model"] == ()
    correction_turn = reflection.connection.execute(
        "SELECT turn_id FROM reflection_turns WHERE content=?",
        ("Синтетическое исправление владельца.",),
    ).fetchone()[0]
    value.set_source_policy([correction_turn], True)
    value.submit(session_id, "submission-4", "Синтетический четвёртый ответ.")
    # With explicitly eligible correction lineage the item becomes
    # investigable, transmitted explicitly as CONTESTED — never as
    # unqualified current truth.
    transmitted = provider.last_context["model"]
    assert len(transmitted) == 1
    assert transmitted[0]["state"] == "CONTESTED"
    assert transmitted[0]["kind"] == "CONTRADICTION"
    # Revoking the correction lineage closes transmission again.
    value.set_source_policy([correction_turn], False)
    value.submit(session_id, "submission-5", "Синтетический пятый ответ.")
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


# --- Fix 1: V13 non-empty package round-trip -----------------------------------


def _seed_non_empty_v13(connection: sqlite3.Connection) -> None:
    """A minimal but non-empty V13 vault: model item, revisions, evidence,
    owner challenge, and a transmitted model manifest."""
    with connection:
        connection.execute(
            "INSERT INTO reflection_sessions VALUES('s1','Synthetic','ACTIVE','ENCRYPTED_LOCAL','real_personal','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00',NULL,2)"
        )
        connection.execute(
            "INSERT INTO reflection_turns VALUES('t1','s1',1,'USER','2026-01-01T00:00:00+00:00','Синтетический ответ-основание')"
        )
        connection.execute(
            "INSERT INTO reflection_turns VALUES('t2','s1',2,'USER','2026-01-02T00:00:00+00:00','Синтетический контрпример')"
        )
        connection.execute(
            "INSERT INTO interview_sessions(interview_session_id,source_session_id,state,created_at,updated_at) VALUES('i1','s1','ACTIVE','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO interview_attempts(attempt_id,interview_session_id,purpose,provider_profile,model,config_id,schema_id,state,policy_enabled,source_item_count,source_char_count,inquiry_item_count,inquiry_char_count,context_char_count,model_item_count,model_char_count,created_at) VALUES('a1','i1','personal_ai_interview','local_personal_ai_interview_openai_windows_v1','gpt-5.6-luna','x','y','SUCCEEDED',1,1,10,0,0,10,1,20,'2026-01-03T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO interview_attempt_manifest_items VALUES('a1','S1','t1','p1',1,10)"
        )
        connection.execute(
            "INSERT INTO interview_derivations VALUES('d1','a1','VALIDATED','2026-01-03T00:00:00+00:00')"
        )
        connection.execute("INSERT INTO interview_derivation_sources VALUES('d1','t1','S1')")
        connection.execute(
            "INSERT INTO personal_model_items VALUES('m1','HYPOTHESIS','CONTESTED','2026-01-03T00:00:00+00:00','2026-01-05T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO personal_model_revisions VALUES('r1','m1',1,'HYPOTHESIS','Возможно, синтетическая рабочая версия.','UNCLEAR',NULL,'Первая версия.','d1',NULL,'SUPERSEDED','2026-01-03T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO personal_model_revisions VALUES('r2','m1',2,'HYPOTHESIS','Возможно, синтетическая рабочая версия.','UNCLEAR',NULL,'Оспорено: добавлен контрпример.','d1',NULL,'CURRENT','2026-01-04T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO personal_model_revision_sources VALUES('r1','t1','S1','SUPPORT')"
        )
        connection.execute(
            "INSERT INTO personal_model_revision_sources VALUES('r2','t1','S1','SUPPORT')"
        )
        connection.execute(
            "INSERT INTO personal_model_revision_sources VALUES('r2','t2','S2','COUNTEREVIDENCE')"
        )
        connection.execute(
            "INSERT INTO personal_model_challenges VALUES('ch1','m1','r1','t2','2026-01-05T00:00:00+00:00')"
        )
        connection.execute(
            "INSERT INTO interview_attempt_model_items VALUES('a1','M1','m1','r2','CONTESTED',1,20)"
        )


def test_v13_package_round_trip_preserves_non_empty_model_tables() -> None:
    connection = sqlite3.connect(":memory:")
    connection.execute("PRAGMA foreign_keys=ON")
    initialize_personal_v13(connection)
    _seed_non_empty_v13(connection)
    package = create_personal_package(connection)
    assert verify_personal_package(package)
    restored = sqlite3.connect(":memory:")
    restored.execute("PRAGMA foreign_keys=ON")
    restore_personal_package(package, restored)
    assert verify_personal_vault_tables(restored)
    recreated = create_personal_package(restored)
    assert recreated["package_checksum"] == package["package_checksum"]
    # Exact semantic equality of every Personal Model table.
    for table in (
        "personal_model_items",
        "personal_model_revisions",
        "personal_model_revision_sources",
        "personal_model_challenges",
        "interview_attempt_model_items",
    ):
        assert (
            connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            == restored.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
        ), table


def verify_personal_vault_tables(connection: sqlite3.Connection) -> bool:
    from psyche_os.personal_mode.schema import PERSONAL_V13_INVENTORY

    tables = {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    return tables == set(PERSONAL_V13_INVENTORY)


def test_v10_v11_v12_package_compatibility_remains_intact() -> None:
    from psyche_os.personal_mode.package_format import (
        PERSONAL_V11_FORMAT_VERSION,
        PERSONAL_V12_FORMAT_VERSION,
        PERSONAL_V13_FORMAT_VERSION,
        verify_personal_package_structure,
    )

    v12 = sqlite3.connect(":memory:")
    initialize_personal_v12(v12)
    with v12:
        v12.execute(
            "INSERT INTO reflection_sessions VALUES('s1','Synthetic','ACTIVE','ENCRYPTED_LOCAL','real_personal','2026-01-01T00:00:00+00:00','2026-01-01T00:00:00+00:00',NULL,0)"
        )
    package_v12 = create_personal_package(v12)
    assert package_v12["format_version"] == PERSONAL_V12_FORMAT_VERSION
    assert verify_personal_package_structure(package_v12)
    restored_v12 = sqlite3.connect(":memory:")
    restore_personal_package(package_v12, restored_v12)
    assert [
        row[0]
        for row in restored_v12.execute("SELECT version FROM schema_migrations ORDER BY version")
    ] == [10, 11, 12]
    assert PERSONAL_V11_FORMAT_VERSION == 4 and PERSONAL_V13_FORMAT_VERSION == 6


# --- Fix 2: transitive model lineage -------------------------------------------


def _fill_raw_packet(reflection: FakeReflection, session_id: str, count: int = 12) -> list[str]:
    """Insert newer synthetic USER turns so the first answer falls outside the
    raw top-12 provider source packet, and enable their source policies."""
    c = reflection.connection
    source_session = c.execute(
        "SELECT source_session_id FROM interview_sessions WHERE interview_session_id=?",
        (session_id,),
    ).fetchone()[0]
    turn_ids = []
    for index in range(count):
        turn_id = f"filler-turn-{index + 1}"
        with c:
            c.execute(
                "INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)",
                (turn_id, source_session, 100 + index, "USER", f"2027-01-{index + 1:02d}T00:00:00+00:00", f"Синтетический наполнитель {index + 1}."),
            )
        turn_ids.append(turn_id)
    return turn_ids


def test_downstream_revision_lineage_covers_ancestral_source_outside_raw_packet() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    first_turn = reflection.connection.execute(
        "SELECT turn_id FROM interview_submissions WHERE interview_session_id=? AND client_submission_id='submission-1'",
        (session_id,),
    ).fetchone()[0]
    fillers = _fill_raw_packet(reflection, session_id, 12)
    value.set_source_policy(fillers, True)
    # R1 exists; the next attempt transmits it as M1 while its own source T1
    # is no longer inside the raw top-12 packet.
    value._provider.deltas = [  # type: ignore[attr-defined]
        create_delta(
            "REVISE",
            text="Общая версия не подтверждается; паттерн может быть специфичен для встреч с зависимым результатом.",
            supporting=["S1"],
        )
    ]
    value.submit(session_id, "submission-2", "Синтетический второй ответ с уточнением.")
    attempt_id = value.get(session_id)["attempts"][0]["attempt_id"]
    manifest_turns = {
        str(row[0])
        for row in reflection.connection.execute(
            "SELECT turn_id FROM interview_attempt_manifest_items WHERE attempt_id=?",
            (attempt_id,),
        )
    }
    assert first_turn not in manifest_turns  # raw manifest excludes T1
    revision_id = reflection.connection.execute(
        "SELECT revision_id FROM personal_model_revisions WHERE status='CURRENT'"
    ).fetchone()[0]
    derivation_turns = {
        str(row[0])
        for row in reflection.connection.execute(
            "SELECT d.turn_id FROM personal_model_revisions r JOIN interview_derivation_sources d ON d.derivation_id=r.derivation_id WHERE r.revision_id=?",
            (revision_id,),
        )
    }
    assert first_turn in derivation_turns  # transitive lineage includes T1
    # Revoke T1 eligibility: the downstream revision must fail closed.
    value.set_source_policy([first_turn], False)
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    assert provider.last_context["model"] == ()
    calls_after_revoke = provider.calls
    # Delete T1: R1 and R2 must both die through existing local machinery,
    # with no provider call and no reconstruction of T1.
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (first_turn,)
        )
    assert provider.calls == calls_after_revoke
    item = value.model()["items"][0]
    assert item["state"] == "INVALIDATED"
    assert item["current"] is None
    receipt = value.disclosure(attempt_id)
    assert all("Синтетический ответ про встречи" not in str(entry) for entry in receipt["items"])
    assert receipt["model_items"] == []


# --- Fix 3: immutable CONTEST lifecycle ----------------------------------------


def test_contest_without_text_preserves_prior_revision_immutable() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    value.submit(session_id, "submission-2", "Синтетический второй ответ-контрпример.")
    old_revision = reflection.connection.execute(
        "SELECT revision_id FROM personal_model_revisions WHERE status='CURRENT'"
    ).fetchone()[0]
    before_text = reflection.connection.execute(
        "SELECT text FROM personal_model_revisions WHERE revision_id=?", (old_revision,)
    ).fetchone()[0]
    before_evidence = reflection.connection.execute(
        "SELECT turn_id,role FROM personal_model_revision_sources WHERE revision_id=? ORDER BY turn_id,role",
        (old_revision,),
    ).fetchall()
    value._provider.deltas = [  # type: ignore[attr-defined]
        create_delta("CONTEST", text="", supporting=[], counterevidence=["S2"], reason="Синтетический контрпример оспаривает версию.")
    ]
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    # R1 remains row-equivalent in text and evidence set, and is historical.
    assert reflection.connection.execute(
        "SELECT text FROM personal_model_revisions WHERE revision_id=?", (old_revision,)
    ).fetchone()[0] == before_text
    assert (
        reflection.connection.execute(
            "SELECT turn_id,role FROM personal_model_revision_sources WHERE revision_id=? ORDER BY turn_id,role",
            (old_revision,),
        ).fetchall()
        == before_evidence
    )
    assert (
        reflection.connection.execute(
            "SELECT status FROM personal_model_revisions WHERE revision_id=?",
            (old_revision,),
        ).fetchone()[0]
        == "SUPERSEDED"
    )
    # R2 is current, carries the copied support plus the new counterevidence.
    new_revision = reflection.connection.execute(
        "SELECT revision_id FROM personal_model_revisions WHERE status='CURRENT'"
    ).fetchone()[0]
    assert new_revision != old_revision
    evidence = reflection.connection.execute(
        "SELECT role,turn_id FROM personal_model_revision_sources WHERE revision_id=?",
        (new_revision,),
    ).fetchall()
    assert len(evidence) == 2
    item = value.model()["items"][0]
    assert item["state"] == "CONTESTED"
    assert [revision["status"] for revision in item["history"]] == ["SUPERSEDED", "CURRENT"]


def test_narrowed_contest_requires_support() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    value._provider.deltas = [  # type: ignore[attr-defined]
        create_delta(
            "CONTEST",
            text="Суженная версия без указания опоры.",
            supporting=[],
            counterevidence=["S1"],
            reason="Попытка заменить версию без опоры.",
        )
    ]
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    # No unsupported current meaning was created.
    assert (
        reflection.connection.execute(
            "SELECT count(*) FROM personal_model_revisions WHERE text='Суженная версия без указания опоры.'"
        ).fetchone()[0]
        == 0
    )
    assert (
        reflection.connection.execute(
            "SELECT count(*) FROM personal_model_revisions WHERE status='CURRENT'"
        ).fetchone()[0]
        == 1
    )


def test_contest_with_narrowed_text_becomes_evidence_backed_and_active() -> None:
    value, _reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    value.submit(session_id, "submission-2", "Синтетический второй ответ-контрпример.")
    value._provider.deltas = [  # type: ignore[attr-defined]
        create_delta(
            "CONTEST",
            text="Паттерн может быть специфичен для ситуаций с зависимым результатом.",
            supporting=["S2"],
            counterevidence=["S1"],
            reason="Контрпример сузил версию; замена опёрта на новый ответ.",
        )
    ]
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    item = value.model()["items"][0]
    assert item["state"] == "ACTIVE"
    assert item["current"]["text"].startswith("Паттерн может быть специфичен")
    assert len(item["current"]["support"]) == 1
    assert len(item["current"]["counterevidence"]) == 1


# --- Fix: owner challenge transitive lineage -----------------------------------


def test_owner_challenge_enters_transitive_lineage() -> None:
    value, reflection, provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    item_id = value.model()["items"][0]["item_id"]
    value.challenge(item_id, "Синтетическая коррекция владельца для линии.")
    correction_turn = reflection.connection.execute(
        "SELECT turn_id FROM reflection_turns WHERE content=?",
        ("Синтетическая коррекция владельца для линии.",),
    ).fetchone()[0]
    value.set_source_policy([correction_turn], True)
    # Push the correction turn outside the raw top-12 packet.
    fillers = _fill_raw_packet(reflection, session_id, 12)
    value.set_source_policy(fillers, True)
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    transmitted = provider.last_context["model"]
    assert len(transmitted) == 1
    assert transmitted[0]["state"] == "CONTESTED"
    value._provider.deltas = [  # type: ignore[attr-defined]
        create_delta(
            "REVISE",
            text="Общая версия не подтверждается; паттерн может быть специфичен для встреч с зависимым результатом.",
            supporting=["S1"],
        )
    ]
    value.submit(session_id, "submission-3", "Синтетический третий ответ с уточнением.")
    attempt_id = value.get(session_id)["attempts"][0]["attempt_id"]
    manifest_turns = {
        str(row[0])
        for row in reflection.connection.execute(
            "SELECT turn_id FROM interview_attempt_manifest_items WHERE attempt_id=?",
            (attempt_id,),
        )
    }
    assert correction_turn not in manifest_turns  # not falsely raw-transmitted
    revision_id = reflection.connection.execute(
        "SELECT revision_id FROM personal_model_revisions WHERE status='CURRENT'"
    ).fetchone()[0]
    lineage_turns = {
        str(row[0])
        for row in reflection.connection.execute(
            "SELECT d.turn_id FROM personal_model_revisions r JOIN interview_derivation_sources d ON d.derivation_id=r.derivation_id WHERE r.revision_id=?",
            (revision_id,),
        )
    }
    assert correction_turn in lineage_turns  # challenge lineage is transitive
    # Revoke the correction policy: downstream meaning fails closed.
    value.set_source_policy([correction_turn], False)
    value.submit(session_id, "submission-4", "Синтетический четвёртый ответ.")
    assert provider.last_context["model"] == ()
    calls_after_revoke = provider.calls
    # Delete the correction SOURCE: downstream meaning cannot stay valid.
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (correction_turn,)
        )
    assert provider.calls == calls_after_revoke
    item = value.model()["items"][0]
    assert item["state"] == "INVALIDATED"
    assert item["current"] is None
    receipt = value.disclosure(attempt_id)
    assert all("коррекция владельца" not in str(entry) for entry in receipt["items"])


# --- Fix: owner challenge overlay vs base AI lifecycle -------------------------


def test_owner_challenge_is_overlay_not_base_mutation() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    item_id = value.model()["items"][0]["item_id"]
    # Base ACTIVE + owner correction -> effective CONTESTED.
    value.challenge(item_id, "Синтетическая коррекция первая.")
    assert value.model()["items"][0]["state"] == "CONTESTED"
    correction_turn = reflection.connection.execute(
        "SELECT turn_id FROM reflection_turns WHERE content=?",
        ("Синтетическая коррекция первая.",),
    ).fetchone()[0]
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (correction_turn,)
        )
    # Overlay removed -> base ACTIVE resurfaces.
    assert value.model()["items"][0]["state"] == "ACTIVE"
    # AI CONTEST sets the BASE lifecycle state to CONTESTED.
    value.submit(session_id, "submission-2", "Синтетический второй ответ-контрпример.")
    value._provider.deltas = [  # type: ignore[attr-defined]
        create_delta("CONTEST", text="", supporting=[], counterevidence=["S2"], reason="Синтетический контрпример оспаривает версию.")
    ]
    value.submit(session_id, "submission-3", "Синтетический третий ответ.")
    assert value.model()["items"][0]["state"] == "CONTESTED"
    base_state = reflection.connection.execute(
        "SELECT state FROM personal_model_items WHERE item_id=?", (item_id,)
    ).fetchone()[0]
    assert base_state == "CONTESTED"
    # Owner correction on top of AI-CONTESTED base.
    value.challenge(item_id, "Синтетическая коррекция вторая.")
    assert value.model()["items"][0]["state"] == "CONTESTED"
    second_turn = reflection.connection.execute(
        "SELECT turn_id FROM reflection_turns WHERE content=?",
        ("Синтетическая коррекция вторая.",),
    ).fetchone()[0]
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (second_turn,)
        )
    # Deleting the overlay must NOT erase the AI-CONTESTED base state.
    assert value.model()["items"][0]["state"] == "CONTESTED"


# --- Fix: exact historical disclosure ------------------------------------------


def test_disclosure_model_state_is_historical_snapshot() -> None:
    value, reflection, _provider = service([create_delta("CREATE")])
    session_id = ready(value)
    turn_one(value, session_id)
    item_id = value.model()["items"][0]["item_id"]
    value.challenge(item_id, "Синтетическая коррекция для снимка.")
    correction_turn = reflection.connection.execute(
        "SELECT turn_id FROM reflection_turns WHERE content=?",
        ("Синтетическая коррекция для снимка.",),
    ).fetchone()[0]
    value.set_source_policy([correction_turn], True)
    value.submit(session_id, "submission-2", "Синтетический второй ответ.")
    attempt_id = value.get(session_id)["attempts"][0]["attempt_id"]
    assert value.disclosure(attempt_id)["model_items"][0]["state"] == "CONTESTED"
    # Later local lifecycle change must not rewrite the historical receipt.
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (correction_turn,)
        )
    assert value.model()["items"][0]["state"] == "ACTIVE"
    assert value.disclosure(attempt_id)["model_items"][0]["state"] == "CONTESTED"
    # Later policy revocation must not hide what WAS transmitted.
    answer_turn = reflection.connection.execute(
        "SELECT turn_id FROM interview_submissions WHERE interview_session_id=? AND client_submission_id='submission-1'",
        (session_id,),
    ).fetchone()[0]
    value.set_source_policy([answer_turn], False)
    receipt = value.disclosure(attempt_id)
    assert len(receipt["model_items"]) == 1
    assert receipt["model_items"][0]["text"].startswith("Возможно,")
    assert len(receipt["items"]) == 2  # raw manifest is historical too
    # Deleting the required supporting source removes reconstructive content
    # through the existing FK closure; content-free attempt facts survive.
    with reflection.connection:
        reflection.connection.execute(
            "DELETE FROM reflection_turns WHERE turn_id=?", (answer_turn,)
        )
    receipt = value.disclosure(attempt_id)
    assert receipt["model_items"] == []  # revision died with its derivation
    # Deleted source and correction content is not reconstructed; the
    # surviving transmitted turn and content-free audit facts remain.
    assert all("Синтетический ответ про встречи" not in str(entry) for entry in receipt["items"])
    assert all("коррекция для снимка" not in str(entry) for entry in receipt["items"])
    assert len(receipt["items"]) == 1
    assert receipt["state"] == "SUCCEEDED"
