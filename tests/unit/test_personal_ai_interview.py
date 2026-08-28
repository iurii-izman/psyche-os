from __future__ import annotations

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
                (value, title, "ACTIVE", "ENCRYPTED_LOCAL", "real_personal", "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", None, 0),
            )
        return {"session_id": value}


class FakeKeys:
    def configured(self) -> bool:
        return True

    def _consume_for_request(self) -> str:
        return "sk-synthetic"


class FakeProvider:
    def __init__(self, variant: str = "ask") -> None:
        self.variant, self.calls, self.last_context = variant, 0, ()

    def invoke_ai_interview(self, _manifest: dict[str, object], context: tuple[dict[str, object], ...], _key: str) -> tuple[dict[str, object], str]:
        self.calls += 1
        self.last_context = context
        if self.variant == "timeout":
            raise ProviderTimeoutError()
        if self.variant == "failed":
            raise ProviderUnavailableError("PROVIDER_FAILED")
        if self.variant == "malformed":
            return {"schema_version": "wrong"}, "gpt-5.6-luna"
        aliases = [str(item["alias"]) for item in context]
        return {"schema_version": "personal-ai-interview-output-v1", "decision": "ASK", "question": "В каком конкретном эпизоде это было заметно?", "rationale": "Чтобы проверить общее объяснение на наблюдаемом эпизоде.", "basis_aliases": aliases, "summary": None, "next_direction": None, "inquiry_items": [{"kind": "THEME", "text": "Переход после насыщенного общения", "priority": 3}]}, "gpt-5.6-luna"  # noqa: RUF001


def service(variant: str = "ask") -> tuple[PersonalAIInterviewService, FakeReflection, FakeProvider]:
    reflection, provider = FakeReflection(), FakeProvider(variant)
    value = PersonalAIInterviewService(reflection, FakeKeys(), provider)
    return value, reflection, provider


def ready(value: PersonalAIInterviewService) -> str:
    value.set_policy(True)
    session_id = value.start()["interview_session_id"]
    value.grant_consent(session_id)
    return session_id


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
        value.submit(session_id, "client-1", "Синтетический ответ о наблюдаемом эпизоде.")  # noqa: RUF001
    rows = reflection.connection.execute("SELECT turn_id FROM interview_submissions WHERE interview_session_id=?", (session_id,)).fetchall()
    assert len(rows) == 1
    answer_turn_id = rows[0][0]
    assert value.get(session_id)["current_question"] is None
    provider.variant = "ask"
    value.retry(session_id, answer_turn_id)
    assert reflection.connection.execute("SELECT count(*) FROM interview_submissions WHERE interview_session_id=?", (session_id,)).fetchone()[0] == 1
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
    assert reflection.connection.execute("SELECT count(*) FROM interview_questions").fetchone()[0] == 0
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
    assert [row[0] for row in connection.execute("SELECT version FROM schema_migrations ORDER BY version")] == [10, 11, 12]
    assert connection.execute("SELECT enabled FROM interview_policy").fetchone() == (0,)


@pytest.mark.parametrize("unsafe", ["У вас диагноз.", "Начните лечение.", "Я всегда рядом.", "Это вытесненная память."])  # noqa: RUF001
def test_safety_boundary_rejects_unsafe_question_quality_output(unsafe: str) -> None:
    raw = {"schema_version": "personal-ai-interview-output-v1", "decision": "ASK", "question": f"{unsafe}?", "rationale": "Проверить синтетический эпизод.", "basis_aliases": [], "summary": None, "next_direction": None, "inquiry_items": []}
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_UNSAFE"):
        validate_interview_output(raw, set())


def test_multiple_primary_questions_and_hallucinated_alias_are_rejected() -> None:
    raw = {"schema_version": "personal-ai-interview-output-v1", "decision": "ASK", "question": "Что произошло? И что было дальше?", "rationale": "Проверить эпизод.", "basis_aliases": ["invented"], "summary": None, "next_direction": None, "inquiry_items": []}
    with pytest.raises(PersonalAIError, match="AI_OUTPUT_REJECTED"):
        validate_interview_output(raw, {"S1"})
