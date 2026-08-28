"""Dedicated, bounded Personal AI Interview V1 service.

The provider is deliberately a stateless renderer behind this local service.
This module owns source-first persistence, local context selection, runtime-only
consent, disclosure receipts, validation and atomic derived-state commits.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from typing import Any

from psyche_os.adapters.e07_provider import ProviderTimeoutError, ProviderUnavailableError
from psyche_os.domain.ids import generate_id
from psyche_os.personal_mode.ai_working_formulation import OpenAIKeyStore, PersonalAIError

PROFILE_ID = "local_personal_ai_interview_openai_windows_v1"
MODEL = "gpt-5.6-luna"
CONFIG_ID = "personal-ai-interview-v1-conservative-12-8000"
SCHEMA_ID = "personal-ai-interview-output-v1"
PURPOSE = "personal_ai_interview"
MAX_SOURCE_ITEMS = 12
MAX_SOURCE_CHARS = 8_000
MAX_QUESTION = 480
MAX_RATIONALE = 480

_UNSAFE = (
    "диагноз", "diagnos", "депресси", "биполяр", "параной",
    "лекарств", "medication", "treatment", "лечени", "вытесненн",
    "recovered memory", "только я", "i need you", "я всегда рядом",
    "i am always here", "наблюдаю за", "спасу вас",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not (result := value.strip()) or len(result) > limit:
        raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
    return result


def _safe_text(value: str) -> str:
    lowered = value.casefold()
    if any(term in lowered for term in _UNSAFE):
        raise PersonalAIError("AI_OUTPUT_UNSAFE")
    return value


@dataclass(frozen=True, slots=True)
class ConsentCapability:
    session_id: str
    provider_profile: str
    policy_generation: str


class PersonalAIInterviewService:
    """Local authoritative interview boundary; never stores provider prose raw."""

    def __init__(self, reflection: Any, keys: OpenAIKeyStore, provider: Any) -> None:
        self._reflection, self._keys, self._provider = reflection, keys, provider
        self._consents: dict[str, ConsentCapability] = {}

    def status(self) -> dict[str, Any]:
        row = self._reflection.connection.execute(
            "SELECT enabled FROM interview_policy WHERE policy_id='personal_ai_interview_v1'"
        ).fetchone()
        return {
            "provider": "OpenAI", "profile_id": PROFILE_ID, "configured": self._keys.configured(),
            "policy_enabled": bool(row and row[0]), "model": MODEL, "config_id": CONFIG_ID,
            "context_bounds": {"max_source_items": MAX_SOURCE_ITEMS, "max_source_chars": MAX_SOURCE_CHARS},
        }

    def set_policy(self, enabled: Any) -> dict[str, Any]:
        if not isinstance(enabled, bool):
            raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        with self._reflection.connection:
            self._reflection.connection.execute(
                "UPDATE interview_policy SET enabled=?,updated_at=? WHERE policy_id='personal_ai_interview_v1'",
                (int(enabled), _now()),
            )
        if not enabled:
            self._consents.clear()
        return self.status()

    def start(self, owner_topic: Any = None) -> dict[str, Any]:
        if owner_topic is not None:
            owner_topic = _text(owner_topic, MAX_QUESTION)
        source = self._reflection.create_session("AI-исследование")
        session_id, now = generate_id(), _now()
        with self._reflection.connection:
            self._reflection.connection.execute(
                "INSERT INTO interview_sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (session_id, source["session_id"], "PAUSED", owner_topic, None, None, now, now, None),
            )
        return self.get(session_id)

    def list(self) -> dict[str, Any]:
        rows = self._reflection.connection.execute(
            "SELECT interview_session_id,state,owner_topic,summary,next_direction,created_at,updated_at,ended_at FROM interview_sessions ORDER BY updated_at DESC"
        ).fetchall()
        return {"sessions": [dict(zip(("interview_session_id", "state", "owner_topic", "summary", "next_direction", "created_at", "updated_at", "ended_at"), row, strict=True)) for row in rows]}

    def grant_consent(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        if not self.status()["policy_enabled"]:
            raise PersonalAIError("AI_POLICY_DISABLED")
        if not self._keys.configured():
            raise PersonalAIError("AI_NOT_CONFIGURED")
        if not self._session_exists(session_id):
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        self._consents[session_id] = ConsentCapability(session_id, PROFILE_ID, _now())
        return {"session_id": session_id, "consent": "ACTIVE_IN_MEMORY", "provider": "OpenAI", "profile_id": PROFILE_ID,
                "notice": "OpenAI получит только ограниченный локально выбранный материал; всё хранилище не передаётся, фоновых вызовов нет."}

    def revoke(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        self._consents.pop(session_id, None)
        return {"session_id": session_id, "consent": "ABSENT"}

    def request_first_question(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        state = self.get(session_id)
        if state["current_question"] is not None:
            return state
        return self._perform(session_id, None)

    def submit(self, session_id: Any, client_submission_id: Any, content: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        client_submission_id = _text(client_submission_id, 96)
        content = _text(content, 12_000)
        answer_turn_id = self._persist_answer(session_id, client_submission_id, content)
        return self._perform(session_id, answer_turn_id)

    def retry(self, session_id: Any, answer_turn_id: Any) -> dict[str, Any]:
        session_id, answer_turn_id = _text(session_id, 64), _text(answer_turn_id, 64)
        row = self._reflection.connection.execute(
            "SELECT 1 FROM interview_submissions WHERE interview_session_id=? AND turn_id=?", (session_id, answer_turn_id)
        ).fetchone()
        if row is None:
            raise PersonalAIError("INTERVIEW_RETRY_REJECTED")
        return self._perform(session_id, answer_turn_id)

    def control(self, session_id: Any, action: Any, topic: Any = None) -> dict[str, Any]:
        session_id, action = _text(session_id, 64), _text(action, 32)
        if action not in {"SKIP", "DECLINE", "CHANGE_TOPIC", "STOP", "END", "CONTINUE"}:
            raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        now = _now()
        with self._reflection.connection:
            if action in {"SKIP", "DECLINE"}:
                status = "SKIPPED" if action == "SKIP" else "DECLINED"
                self._reflection.connection.execute("UPDATE interview_questions SET status=? WHERE interview_session_id=? AND status='CURRENT'", (status, session_id))
                self._reflection.connection.execute("UPDATE interview_sessions SET state='ACTIVE',updated_at=? WHERE interview_session_id=?", (now, session_id))
            elif action == "CHANGE_TOPIC":
                self._reflection.connection.execute("UPDATE interview_questions SET status='SUPERSEDED' WHERE interview_session_id=? AND status='CURRENT'", (session_id,))
                self._reflection.connection.execute("UPDATE interview_sessions SET owner_topic=?,state='ACTIVE',updated_at=? WHERE interview_session_id=?", (_text(topic, MAX_QUESTION), now, session_id))
            elif action == "CONTINUE":
                self._reflection.connection.execute("UPDATE interview_sessions SET state='ACTIVE',updated_at=? WHERE interview_session_id=?", (now, session_id))
            else:
                self._reflection.connection.execute("UPDATE interview_sessions SET state=?,ended_at=?,updated_at=? WHERE interview_session_id=?", ("COMPLETED" if action == "END" else "PAUSED", now if action == "END" else None, now, session_id))
        if action in {"STOP", "END"}:
            self._consents.pop(session_id, None)
        return self.get(session_id)

    def disclosure(self, attempt_id: Any) -> dict[str, Any]:
        attempt_id = _text(attempt_id, 64)
        row = self._reflection.connection.execute(
            "SELECT attempt_id,interview_session_id,state,provider_profile,model,config_id,schema_id,source_item_count,source_char_count,created_at,sent_at,completed_at,error_code FROM interview_attempts WHERE attempt_id=?", (attempt_id,)
        ).fetchone()
        if row is None:
            raise PersonalAIError("DISCLOSURE_NOT_FOUND")
        fields = ("attempt_id", "interview_session_id", "state", "provider_profile", "model", "config_id", "schema_id", "source_item_count", "source_char_count", "created_at", "sent_at", "completed_at", "error_code")
        result = dict(zip(fields, row, strict=True))
        items = self._reflection.connection.execute(
            "SELECT m.alias,m.turn_id,m.ordinal,m.char_count,t.content FROM interview_attempt_manifest_items m JOIN reflection_turns t ON t.turn_id=m.turn_id WHERE m.attempt_id=? ORDER BY m.ordinal", (attempt_id,)
        ).fetchall()
        result["items"] = [dict(zip(("alias", "turn_id", "ordinal", "char_count", "content"), item, strict=True)) for item in items]
        return result

    def get(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        row = self._reflection.connection.execute(
            "SELECT interview_session_id,source_session_id,state,owner_topic,summary,next_direction,created_at,updated_at,ended_at FROM interview_sessions WHERE interview_session_id=?", (session_id,)
        ).fetchone()
        if row is None:
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        result = dict(zip(("interview_session_id", "source_session_id", "state", "owner_topic", "summary", "next_direction", "created_at", "updated_at", "ended_at"), row, strict=True))
        question = self._reflection.connection.execute(
            "SELECT question_id,question,rationale,decision,basis_aliases,created_at FROM interview_questions WHERE interview_session_id=? AND status='CURRENT'", (session_id,)
        ).fetchone()
        result["current_question"] = None if question is None else dict(zip(("question_id", "question", "rationale", "decision", "basis_aliases", "created_at"), question, strict=True))
        result["current_question"] and result["current_question"].update(basis_aliases=json.loads(result["current_question"]["basis_aliases"]))
        attempts = self._reflection.connection.execute("SELECT attempt_id,state,answer_turn_id,created_at,error_code FROM interview_attempts WHERE interview_session_id=? ORDER BY created_at DESC", (session_id,)).fetchall()
        result["attempts"] = [dict(zip(("attempt_id", "state", "answer_turn_id", "created_at", "error_code"), item, strict=True)) for item in attempts]
        result["consent"] = "ACTIVE_IN_MEMORY" if session_id in self._consents else "ABSENT"
        return result

    def _session_exists(self, session_id: str) -> bool:
        return self._reflection.connection.execute("SELECT 1 FROM interview_sessions WHERE interview_session_id=?", (session_id,)).fetchone() is not None

    def _require_consent(self, session_id: str) -> None:
        capability = self._consents.get(session_id)
        if capability is None or capability.provider_profile != PROFILE_ID:
            raise PersonalAIError("AI_CONSENT_REQUIRED")
        if not self.status()["policy_enabled"]:
            self._consents.pop(session_id, None)
            raise PersonalAIError("AI_POLICY_DISABLED")

    def _persist_answer(self, session_id: str, submission_id: str, content: str) -> str:
        connection, now = self._reflection.connection, _now()
        with connection:
            prior = connection.execute("SELECT turn_id FROM interview_submissions WHERE interview_session_id=? AND client_submission_id=?", (session_id, submission_id)).fetchone()
            if prior is not None:
                return str(prior[0])
            source = connection.execute("SELECT source_session_id,state FROM interview_sessions WHERE interview_session_id=?", (session_id,)).fetchone()
            if source is None or source[1] == "COMPLETED":
                raise PersonalAIError("INTERVIEW_NOT_ACTIVE")
            count = connection.execute("SELECT turn_count FROM reflection_sessions WHERE session_id=?", (source[0],)).fetchone()
            if count is None:
                raise PersonalAIError("INTERVIEW_NOT_FOUND")
            turn_id, sequence = generate_id(), int(count[0]) + 1
            connection.execute("INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)", (turn_id, source[0], sequence, "USER", now, content))
            connection.execute("UPDATE reflection_sessions SET turn_count=?,updated_at=? WHERE session_id=?", (sequence, now, source[0]))
            connection.execute("INSERT INTO interview_submissions VALUES(?,?,?,?)", (session_id, submission_id, turn_id, now))
            connection.execute("UPDATE interview_questions SET status='ANSWERED' WHERE interview_session_id=? AND status='CURRENT'", (session_id,))
            connection.execute("UPDATE interview_sessions SET state='ACTIVE',updated_at=? WHERE interview_session_id=?", (now, session_id))
        return turn_id

    def _select(self, session_id: str) -> tuple[dict[str, Any], ...]:
        """Deterministic source-only selector: current session first, then history."""
        rows = self._reflection.connection.execute(
            "SELECT turn_id,content,created_at FROM ("
            "SELECT t.turn_id AS turn_id,t.content AS content,t.created_at AS created_at FROM interview_sessions i JOIN reflection_turns t ON t.session_id=i.source_session_id WHERE i.interview_session_id=? "
            "UNION ALL SELECT t.turn_id AS turn_id,t.content AS content,t.created_at AS created_at FROM reflection_turns t JOIN reflection_sessions s ON s.session_id=t.session_id WHERE t.actor='USER' AND t.session_id NOT IN (SELECT source_session_id FROM interview_sessions WHERE interview_session_id=?)"
            ") ORDER BY created_at DESC,turn_id DESC",
            (session_id, session_id),
        ).fetchall()
        selected: list[dict[str, Any]] = []
        chars, seen = 0, set()
        for turn_id, content, _ in rows:
            if turn_id in seen or len(selected) == MAX_SOURCE_ITEMS or chars + len(content) > MAX_SOURCE_CHARS:
                continue
            seen.add(turn_id)
            selected.append({"alias": f"S{len(selected) + 1}", "turn_id": turn_id, "content": content, "char_count": len(content)})
            chars += len(content)
        return tuple(selected)

    def _perform(self, session_id: str, answer_turn_id: str | None) -> dict[str, Any]:
        self._require_consent(session_id)
        if not self._session_exists(session_id):
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        context = self._select(session_id)
        attempt_id, now = generate_id(), _now()
        connection = self._reflection.connection
        with connection:
            connection.execute("INSERT INTO interview_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (attempt_id, session_id, answer_turn_id, PURPOSE, PROFILE_ID, MODEL, CONFIG_ID, SCHEMA_ID, "PREPARED", 1, len(context), sum(item["char_count"] for item in context), now, None, None, None))
            for ordinal, item in enumerate(context, 1):
                connection.execute("INSERT INTO interview_attempt_manifest_items VALUES(?,?,?,?,?)", (attempt_id, item["alias"], item["turn_id"], ordinal, item["char_count"]))
        manifest = {"attempt_id": attempt_id, "purpose": PURPOSE, "profile_id": PROFILE_ID, "model": MODEL, "config_id": CONFIG_ID, "schema_id": SCHEMA_ID, "source_aliases": [item["alias"] for item in context], "max_source_items": MAX_SOURCE_ITEMS, "max_source_chars": MAX_SOURCE_CHARS}
        try:
            with connection:
                connection.execute("UPDATE interview_attempts SET state='SENT',sent_at=? WHERE attempt_id=?", (_now(), attempt_id))
            raw, actual_model = self._provider.invoke_ai_interview(manifest, context, self._keys._consume_for_request())
        except ProviderTimeoutError:
            with connection:
                connection.execute("UPDATE interview_attempts SET state='OUTCOME_UNKNOWN',completed_at=?,error_code='PROVIDER_OUTCOME_UNKNOWN' WHERE attempt_id=?", (_now(), attempt_id))
            raise PersonalAIError("PROVIDER_OUTCOME_UNKNOWN") from None
        except (ProviderUnavailableError, PersonalAIError) as exc:
            with connection:
                connection.execute("UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?", (_now(), getattr(exc, "code", "PROVIDER_FAILED"), attempt_id))
            raise PersonalAIError(getattr(exc, "code", "PROVIDER_FAILED")) from None
        if actual_model != MODEL:
            with connection:
                connection.execute("UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code='MODEL_NOT_AVAILABLE' WHERE attempt_id=?", (_now(), attempt_id))
            raise PersonalAIError("MODEL_NOT_AVAILABLE")
        try:
            parsed = validate_interview_output(raw, {item["alias"] for item in context})
        except PersonalAIError as exc:
            with connection:
                connection.execute("UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?", (_now(), exc.code, attempt_id))
            raise
        self._commit_derived(session_id, attempt_id, answer_turn_id, parsed, actual_model)
        return self.get(session_id)

    def _commit_derived(self, session_id: str, attempt_id: str, answer_turn_id: str | None, value: dict[str, Any], actual_model: str) -> None:
        now, connection = _now(), self._reflection.connection
        with connection:
            connection.execute("UPDATE interview_attempts SET state='SUCCEEDED',completed_at=?,model=? WHERE attempt_id=?", (now, actual_model, attempt_id))
            connection.execute("UPDATE interview_questions SET status='SUPERSEDED' WHERE interview_session_id=? AND status='CURRENT'", (session_id,))
            decision = value["decision"]
            if decision == "ASK":
                connection.execute("INSERT INTO interview_questions VALUES(?,?,?,?,?,?,?,?)", (generate_id(), session_id, value["question"], value["rationale"], decision, "CURRENT", json.dumps(value["basis_aliases"]), now))
            for item in value["inquiry_items"]:
                connection.execute("INSERT INTO interview_inquiry_items VALUES(?,?,?,?,?,?,?,?)", (generate_id(), session_id, item["kind"], item["text"], item["priority"], "ACTIVE", answer_turn_id, now))
            state = "END_RECOMMENDED" if decision == "END_RECOMMENDED" else "ACTIVE"
            connection.execute("UPDATE interview_sessions SET state=?,summary=?,next_direction=?,updated_at=? WHERE interview_session_id=?", (state, value["summary"], value["next_direction"], now, session_id))


def validate_interview_output(raw: Any, aliases: set[str]) -> dict[str, Any]:
    """Strict, content-free structured-output validation before any mutation."""
    required = {"schema_version", "decision", "question", "rationale", "basis_aliases", "summary", "next_direction", "inquiry_items"}
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema_version") != SCHEMA_ID:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    decision = raw.get("decision")
    if decision not in {"ASK", "END_RECOMMENDED"} or not isinstance(raw["basis_aliases"], list) or len(raw["basis_aliases"]) > MAX_SOURCE_ITEMS or len(set(raw["basis_aliases"])) != len(raw["basis_aliases"]) or not all(isinstance(alias, str) and alias in aliases for alias in raw["basis_aliases"]):
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    question = raw["question"]
    if decision == "ASK":
        question = _safe_text(_text(question, MAX_QUESTION))
        if question.count("?") != 1 or not question.endswith("?"):
            raise PersonalAIError("AI_OUTPUT_REJECTED")
    elif question is not None:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    rationale = _safe_text(_text(raw["rationale"], MAX_RATIONALE))
    summary = raw["summary"]
    next_direction = raw["next_direction"]
    if decision == "END_RECOMMENDED":
        summary, next_direction = _safe_text(_text(summary, MAX_RATIONALE)), _safe_text(_text(next_direction, MAX_RATIONALE))
    elif summary is not None or next_direction is not None:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    items = raw["inquiry_items"]
    if not isinstance(items, list) or len(items) > 6:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    parsed = []
    for item in items:
        if not isinstance(item, dict) or set(item) != {"kind", "text", "priority"} or item["kind"] not in {"THEME", "WHITE_SPOT", "REVISIT", "HYPOTHESIS", "CONTRADICTION", "UNKNOWN"} or not isinstance(item["priority"], int) or not 1 <= item["priority"] <= 5:
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        parsed.append({"kind": item["kind"], "text": _safe_text(_text(item["text"], MAX_QUESTION)), "priority": item["priority"]})
    return {"decision": decision, "question": question, "rationale": rationale, "basis_aliases": raw["basis_aliases"], "summary": summary, "next_direction": next_direction, "inquiry_items": parsed}
