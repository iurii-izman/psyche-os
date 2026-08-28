from __future__ import annotations

# ruff: noqa: RUF001
import sqlite3

import pytest

from psyche_os.adapters.e07_provider import ProviderTimeoutError, ProviderUnavailableError
from psyche_os.personal_mode.ai_interview import (
    PersonalAIError,
    PersonalAIInterviewService,
    validate_interview_output,
)
from psyche_os.personal_mode.schema import initialize_personal_v12


class FakeReflection:
    def __init__(self) -> None:
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")
        initialize_personal_v12(self.connection)
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


class FakeProvider:
    def __init__(self, variant: str = "ask") -> None:
        self.variant, self.calls, self.last_context = variant, 0, {}

    def invoke_ai_interview(
        self, _manifest: dict[str, object], context: dict[str, object], _key: str
    ) -> tuple[dict[str, object], str]:
        self.calls += 1
        self.last_context = context
        if self.variant == "timeout":
            raise ProviderTimeoutError()
        if self.variant == "failed":
            raise ProviderUnavailableError("PROVIDER_FAILED")
        if self.variant == "malformed":
            return {"schema_version": "wrong"}, "gpt-5.6-luna"
        aliases = [str(item["alias"]) for item in context["sources"]]
        if self.variant == "end":
            return {
                "schema_version": "personal-ai-interview-output-v1",
                "decision": "END_RECOMMENDED",
                "question": None,
                "rationale": "Синтетическая линия получила достаточно материала.",
                "basis_aliases": aliases,
                "summary": "Синтетическое краткое резюме.",
                "next_direction": "Вернуться к синтетической линии позже.",
                "inquiry_items": [
                    {"kind": "REVISIT", "text": "Синтетический вопрос для возврата", "priority": 3}
                ],
            }, "gpt-5.6-luna"
        return {
            "schema_version": "personal-ai-interview-output-v1",
            "decision": "ASK",
            "question": "В каком конкретном эпизоде это было заметно?",
            "rationale": "Чтобы проверить общее объяснение на наблюдаемом эпизоде.",
            "basis_aliases": aliases,
            "summary": None,
            "next_direction": None,
            "inquiry_items": [
                {"kind": "THEME", "text": "Переход после насыщенного общения", "priority": 3}
            ],
        }, "gpt-5.6-luna"


def service(
    variant: str = "ask",
) -> tuple[PersonalAIInterviewService, FakeReflection, FakeProvider]:
    reflection, provider = FakeReflection(), FakeProvider(variant)
    value = PersonalAIInterviewService(reflection, FakeKeys(), provider)
    return value, reflection, provider


def ready(value: PersonalAIInterviewService) -> str:
    value.set_policy(True)
    session_id = value.start()["interview_session_id"]
    value.grant_consent(session_id)
    return session_id


def historical_turn(
    reflection: FakeReflection, content: str, created_at: str = "2026-01-01T00:00:00+00:00"
) -> str:
    session_id = reflection.create_session("Synthetic history")["session_id"]
    turn_id = f"history-turn-{reflection._next}"
    with reflection.connection:
        reflection.connection.execute(
            "INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)",
            (turn_id, session_id, 1, "USER", created_at, content),
        )
        reflection.connection.execute(
            "UPDATE reflection_sessions SET turn_count=1 WHERE session_id=?", (session_id,)
        )
    return turn_id


def test_no_consent_means_zero_provider_calls_and_no_disclosure() -> None:
    value, _reflection, provider = service()
    session_id = value.start()["interview_session_id"]
    with pytest.raises(PersonalAIError, match="AI_CONSENT_REQUIRED"):
        value.request_first_question(session_id)
    assert provider.calls == 0
    assert value.get(session_id)["attempts"] == []


def test_answer_is_source_before_provider_failure_and_retry_never_duplicates_it() -> None:
    value, reflection, provider = service("failed")
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="PROVIDER_FAILED"):
        value.submit(session_id, "client-1", "Синтетический ответ о наблюдаемом эпизоде.")
    rows = reflection.connection.execute(
        "SELECT turn_id FROM interview_submissions WHERE interview_session_id=?", (session_id,)
    ).fetchall()
    assert len(rows) == 1
    answer_turn_id = rows[0][0]
    assert value.get(session_id)["current_question"] is None
    provider.variant = "ask"
    value.retry(session_id, answer_turn_id)
    assert (
        reflection.connection.execute(
            "SELECT count(*) FROM interview_submissions WHERE interview_session_id=?", (session_id,)
        ).fetchone()[0]
        == 1
    )
    assert provider.calls == 2


def test_restart_reconstruction_has_no_runtime_consent() -> None:
    value, reflection, _provider = service()
    session_id = ready(value)
    replacement = PersonalAIInterviewService(reflection, FakeKeys(), FakeProvider())
    assert replacement.get(session_id)["consent"] == "ABSENT"
    with pytest.raises(PersonalAIError, match="AI_CONSENT_REQUIRED"):
        replacement.request_first_question(session_id)


def test_manifest_is_exact_context_and_malformed_output_has_no_derived_mutations() -> None:
    value, reflection, provider = service("malformed")
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        value.request_first_question(session_id)
    assert (
        reflection.connection.execute("SELECT count(*) FROM interview_questions").fetchone()[0] == 0
    )
    attempt = value.get(session_id)["attempts"][0]
    assert attempt["state"] == "FAILED"
    assert provider.calls == 1


def test_timeout_is_ambiguous_and_never_automatically_resends() -> None:
    value, _reflection, provider = service("timeout")
    session_id = ready(value)
    with pytest.raises(PersonalAIError, match="PROVIDER_OUTCOME_UNKNOWN"):
        value.request_first_question(session_id)
    assert value.get(session_id)["attempts"][0]["state"] == "OUTCOME_UNKNOWN"
    assert provider.calls == 1


def test_v12_migration_is_additive_and_policy_defaults_closed() -> None:
    connection = sqlite3.connect(":memory:")
    initialize_personal_v12(connection)
    assert [
        row[0]
        for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")
    ] == [10, 11, 12]
    assert connection.execute("SELECT enabled FROM interview_policy").fetchone() == (0,)


@pytest.mark.parametrize(
    "unsafe", ["У вас диагноз.", "Начните лечение.", "Я всегда рядом.", "Это вытесненная память."]
)
def test_safety_boundary_rejects_unsafe_question_quality_output(unsafe: str) -> None:
    raw = {
        "schema_version": "personal-ai-interview-output-v1",
        "decision": "ASK",
        "question": f"{unsafe}?",
        "rationale": "Проверить синтетический эпизод.",
        "basis_aliases": [],
        "summary": None,
        "next_direction": None,
        "inquiry_items": [],
    }
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_UNSAFE"):
        validate_interview_output(raw, set())


def test_multiple_primary_questions_and_hallucinated_alias_are_rejected() -> None:
    raw = {
        "schema_version": "personal-ai-interview-output-v1",
        "decision": "ASK",
        "question": "Что произошло? И что было дальше?",
        "rationale": "Проверить эпизод.",
        "basis_aliases": ["invented"],
        "summary": None,
        "next_direction": None,
        "inquiry_items": [],
    }
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        validate_interview_output(raw, {"S1"})


def test_historical_sources_fail_closed_then_exact_owner_policy_controls_manifest() -> None:
    value, reflection, provider = service()
    blocked = historical_turn(reflection, "Blocked synthetic history")
    allowed = historical_turn(reflection, "Allowed synthetic history", "2026-01-02T00:00:00+00:00")
    session_id = ready(value)
    value.request_first_question(session_id)
    assert provider.last_context["sources"] == ()
    value.control(session_id, "SKIP")
    value.set_source_policy([allowed], True)
    value.request_first_question(session_id)
    assert [item["turn_id"] for item in provider.last_context["sources"]] == [allowed]
    value.control(session_id, "SKIP")
    value.set_source_policy([allowed], False)
    value.grant_consent(session_id)
    value.request_first_question(session_id)
    assert blocked not in [item["turn_id"] for item in provider.last_context["sources"]]
    assert provider.last_context["sources"] == ()


def test_current_answer_gets_explicit_session_consent_policy_and_retry_keeps_exact_receipt() -> (
    None
):
    value, reflection, provider = service()
    session_id = ready(value)
    value.submit(session_id, "source-policy", "Current synthetic answer")
    attempt = value.get(session_id)["attempts"][0]
    answer = attempt["answer_turn_id"]
    policy = reflection.connection.execute(
        "SELECT enabled,purpose,provider_profile,assigned_by FROM interview_source_policies WHERE turn_id=?",
        (answer,),
    ).fetchone()
    assert policy == (
        1,
        "personal_ai_interview",
        "local_personal_ai_interview_openai_windows_v1",
        "SESSION_CONSENT",
    )
    receipt = value.disclosure(attempt["attempt_id"])
    assert receipt["items"][0]["turn_id"] == answer
    assert receipt["transmission"] == "SENT"
    assert provider.last_context["sources"][0]["policy_id"] == receipt["items"][0]["policy_id"]


def test_never_cloud_and_third_party_policy_axes_fail_closed_despite_consent() -> None:
    value, reflection, provider = service()
    source = historical_turn(reflection, "Synthetic restricted source")
    session_id = ready(value)
    value.set_source_policy([source], True)
    with reflection.connection:
        reflection.connection.execute(
            "UPDATE interview_source_policies SET cloud_policy='never_cloud' WHERE turn_id=?",
            (source,),
        )
    value.request_first_question(session_id)
    assert provider.last_context["sources"] == ()
    value.control(session_id, "SKIP")
    with reflection.connection:
        reflection.connection.execute(
            "UPDATE interview_source_policies SET cloud_policy='named_purpose_and_provider',third_party_scope='material' WHERE turn_id=?",
            (source,),
        )
    value.request_first_question(session_id)
    assert provider.last_context["sources"] == ()


def test_bounded_planner_carries_topic_controls_and_only_eligible_derived_inquiry() -> None:
    value, reflection, provider = service()
    source = historical_turn(reflection, "Synthetic anchor")
    session_id = value.start("Synthetic owner topic")["interview_session_id"]
    value.set_policy(True)
    value.set_source_policy([source], True)
    value.grant_consent(session_id)
    value.request_first_question(session_id)
    value.control(session_id, "DECLINE")
    value.request_first_question(session_id)
    planning = provider.last_context["planning"]
    assert {item["kind"] for item in planning} >= {"OWNER_TOPIC", "QUESTION_CONTROL"}
    assert (
        next(item for item in planning if item["kind"] == "QUESTION_CONTROL")["state"] == "DECLINED"
    )
    assert provider.last_context["inquiry"]
    value.set_source_policy([source], False)
    value.control(session_id, "SKIP")
    value.request_first_question(session_id)
    assert provider.last_context["inquiry"] == ()


def test_thin_history_uses_local_onboarding_mode_and_session_trail_keeps_roles_distinct() -> None:
    value, _reflection, provider = service()
    session_id = ready(value)
    value.request_first_question(session_id)
    assert any(item["kind"] == "ONBOARDING" for item in provider.last_context["planning"])
    value.submit(session_id, "trail-answer", "Синтетический ответ о текущей ситуации.")
    trail = value.get(session_id)["session_trail"]
    assert {item["actor"] for item in trail} == {"PSYCHE", "YOU"}


def test_exact_normalized_duplicate_inquiry_item_is_not_accumulated() -> None:
    value, reflection, provider = service()
    source = historical_turn(reflection, "Synthetic duplicate support")
    session_id = ready(value)
    value.set_source_policy([source], True)
    value.request_first_question(session_id)
    value.control(session_id, "SKIP")
    value.request_first_question(session_id)
    assert reflection.connection.execute(
        "SELECT count(*) FROM interview_inquiry_items WHERE kind='THEME'"
    ).fetchone()[0] == 1


def test_exact_derivation_basis_and_source_deletion_remove_dependent_meaning() -> None:
    value, reflection, _provider = service()
    source = historical_turn(reflection, "Synthetic support")
    session_id = ready(value)
    value.set_source_policy([source], True)
    state = value.request_first_question(session_id)
    question = state["current_question"]
    assert question is not None
    attempt_id = question["attempt_id"]
    assert reflection.connection.execute(
        "SELECT turn_id FROM interview_question_basis WHERE question_id=?",
        (question["question_id"],),
    ).fetchall() == [(source,)]
    assert reflection.connection.execute(
        "SELECT attempt_id FROM interview_derivations WHERE derivation_id=?",
        (question["derivation_id"],),
    ).fetchone() == (attempt_id,)
    with reflection.connection:
        reflection.connection.execute("DELETE FROM reflection_turns WHERE turn_id=?", (source,))
    assert reflection.connection.execute("SELECT count(*) FROM interview_questions").fetchone() == (
        0,
    )
    assert reflection.connection.execute(
        "SELECT count(*) FROM interview_inquiry_items"
    ).fetchone() == (0,)
    assert value.disclosure(attempt_id)["items"] == []


def test_end_direction_is_provenanced_and_available_to_later_session_only_when_eligible() -> None:
    value, reflection, provider = service("ask")
    source = historical_turn(reflection, "Synthetic continuity")
    session_id = ready(value)
    value.set_source_policy([source], True)
    provider.variant = "end"
    value.request_first_question(session_id)
    result = value.get(session_id)
    assert result["state"] == "END_RECOMMENDED"
    assert (
        reflection.connection.execute(
            "SELECT summary_derivation_id,next_direction_derivation_id FROM interview_sessions WHERE interview_session_id=?",
            (session_id,),
        ).fetchone()[0]
        is not None
    )
    later = value.start()["interview_session_id"]
    value.grant_consent(later)
    provider.variant = "ask"
    value.request_first_question(later)
    assert any(item["kind"] == "SAVED_DIRECTION" for item in provider.last_context["planning"])


def test_source_deletion_clears_end_summary_and_direction_before_fk_nulling() -> None:
    value, reflection, provider = service("end")
    source = historical_turn(reflection, "Synthetic end support")
    session_id = ready(value)
    value.set_source_policy([source], True)
    value.request_first_question(session_id)
    attempt_id = value.get(session_id)["attempts"][0]["attempt_id"]
    derivation_id = reflection.connection.execute(
        "SELECT derivation_id FROM interview_derivations WHERE attempt_id=?", (attempt_id,)
    ).fetchone()[0]
    calls_before_delete = provider.calls
    with reflection.connection:
        reflection.connection.execute("DELETE FROM reflection_turns WHERE turn_id=?", (source,))
    assert (
        reflection.connection.execute(
            "SELECT 1 FROM interview_derivations WHERE derivation_id=?", (derivation_id,)
        ).fetchone()
        is None
    )
    assert reflection.connection.execute(
        "SELECT summary,summary_derivation_id,next_direction,next_direction_derivation_id FROM interview_sessions WHERE interview_session_id=?",
        (session_id,),
    ).fetchone() == (None, None, None, None)
    assert reflection.connection.execute(
        "SELECT count(*) FROM interview_inquiry_items"
    ).fetchone() == (0,)
    assert value.disclosure(attempt_id)["items"] == []
    assert provider.calls == calls_before_delete


@pytest.mark.parametrize(
    "question",
    [
        "Были ли у вас раньше периоды депрессивного настроения?",
        "Обращались ли вы когда-нибудь за лечением?",
    ],
)
def test_neutral_symptom_and_treatment_history_questions_are_allowed(question: str) -> None:
    raw = {
        "schema_version": "personal-ai-interview-output-v1",
        "decision": "ASK",
        "question": question,
        "rationale": "Проверить синтетический эпизод.",
        "basis_aliases": [],
        "summary": None,
        "next_direction": None,
        "inquiry_items": [],
    }
    assert validate_interview_output(raw, set())["question"] == question
