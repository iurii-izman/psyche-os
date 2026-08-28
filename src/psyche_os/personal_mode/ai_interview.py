"""Bounded local planner for the stateless Personal AI Interview provider."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
import re
from typing import Any

from psyche_os.adapters.e07_provider import ProviderTimeoutError, ProviderUnavailableError
from psyche_os.domain.ids import PolicyId, generate_id
from psyche_os.personal_mode.ai_working_formulation import OpenAIKeyStore, PersonalAIError
from psyche_os.policy.engine import (
    CloudPolicy,
    PolicyAxes,
    ProcessingLocation,
    ThirdPartyScope,
    resolve_effective_policy,
)

PROFILE_ID = "local_personal_ai_interview_openai_windows_v1"
MODEL = "gpt-5.6-luna"
CONFIG_ID = "personal-ai-interview-v1-conservative-12-8000"
SCHEMA_ID = "personal-ai-interview-output-v1"
PURPOSE = "personal_ai_interview"
MAX_SOURCE_ITEMS, MAX_SOURCE_CHARS, MAX_INQUIRY_ITEMS, MAX_CONTEXT_CHARS = 12, 8000, 8, 8000
MAX_QUESTION = MAX_RATIONALE = 480
_UNSAFE = (
    r"(?:\u0443\s+вас|you\s+have)\s+(?:депресси\w*|биполяр\w*|параной\w*|diagnos\w*)",
    r"(?:диагноз\w*|diagnos\w*)",
    r"(?:начните\s+(?:лечени\w*|treatment\w*))",
    r"(?:вам\s+нужно|you\s+need\s+to)\s+(?:начать\s+)?(?:лечени\w*|treatment\w*)",
    r"(?:назначаю|принимайте|дозировк\w*|medication\s+directive)",
    r"(?:вытесненн\w*\s+памят\w*|recovered\s+memory)",
    r"(?:только\s+я|i\s+need\s+you|я\s+всегда\s+рядом|i\s+am\s+always\s+here|наблюдаю\s+за|спасу\s+вас)",
)


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _text(value: Any, limit: int) -> str:
    if not isinstance(value, str) or not (result := value.strip()) or len(result) > limit:
        raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
    return result


def _safe(value: str) -> str:
    if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in _UNSAFE):
        raise PersonalAIError("AI_OUTPUT_UNSAFE")
    return value


@dataclass(frozen=True, slots=True)
class ConsentCapability:
    session_id: str
    provider_profile: str
    policy_generation: str


class PersonalAIInterviewService:
    def __init__(self, reflection: Any, keys: OpenAIKeyStore, provider: Any) -> None:
        self._reflection, self._keys, self._provider, self._consents = (
            reflection,
            keys,
            provider,
            {},
        )

    def status(self) -> dict[str, Any]:
        row = self._reflection.connection.execute(
            "SELECT enabled,updated_at FROM interview_policy WHERE policy_id='personal_ai_interview_v1'"
        ).fetchone()
        return {
            "provider": "OpenAI",
            "profile_id": PROFILE_ID,
            "configured": self._keys.configured(),
            "policy_enabled": bool(row and row[0]),
            "policy_generation": row[1] if row else None,
            "model": MODEL,
            "config_id": CONFIG_ID,
            "context_bounds": {
                "max_source_items": MAX_SOURCE_ITEMS,
                "max_source_chars": MAX_SOURCE_CHARS,
                "max_context_chars": MAX_CONTEXT_CHARS,
            },
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

    def set_source_policy(self, turn_ids: Any, enabled: Any) -> dict[str, Any]:
        if (
            not isinstance(enabled, bool)
            or not isinstance(turn_ids, list)
            or not turn_ids
            or len(turn_ids) > MAX_SOURCE_ITEMS
        ):
            raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        ids = [_text(value, 64) for value in turn_ids]
        if len(set(ids)) != len(ids):
            raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        found = {
            row[0]
            for row in self._reflection.connection.execute(
                f"SELECT turn_id FROM reflection_turns WHERE turn_id IN ({','.join('?' for _ in ids)})",
                ids,
            )
        }
        if found != set(ids):
            raise PersonalAIError("INTERVIEW_SOURCE_NOT_FOUND")
        with self._reflection.connection:
            for turn_id in ids:
                self._upsert_policy(turn_id, enabled, "OWNER_HISTORY_ACTION", _now())
        return {
            "turn_ids": ids,
            "enabled": enabled,
            "purpose": PURPOSE,
            "provider_profile": PROFILE_ID,
        }

    def start(self, owner_topic: Any = None) -> dict[str, Any]:
        if owner_topic is not None:
            owner_topic = _text(owner_topic, MAX_QUESTION)
        source, session_id, now = (
            self._reflection.create_session("AI-исследование"),
            generate_id(),
            _now(),
        )
        with self._reflection.connection:
            self._reflection.connection.execute(
                "INSERT INTO interview_sessions(interview_session_id,source_session_id,state,owner_topic,summary,next_direction,summary_derivation_id,next_direction_derivation_id,created_at,updated_at,ended_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (
                    session_id,
                    source["session_id"],
                    "PAUSED",
                    owner_topic,
                    None,
                    None,
                    None,
                    None,
                    now,
                    now,
                    None,
                ),
            )
        return self.get(session_id)

    def list(self) -> dict[str, Any]:
        names = (
            "interview_session_id",
            "state",
            "owner_topic",
            "summary",
            "next_direction",
            "created_at",
            "updated_at",
            "ended_at",
        )
        return {
            "sessions": [
                dict(zip(names, row, strict=True))
                for row in self._reflection.connection.execute(
                    "SELECT interview_session_id,state,owner_topic,summary,next_direction,created_at,updated_at,ended_at FROM interview_sessions ORDER BY updated_at DESC"
                )
            ]
        }

    def grant_consent(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        if not self.status()["policy_enabled"]:
            raise PersonalAIError("AI_POLICY_DISABLED")
        if not self._keys.configured():
            raise PersonalAIError("AI_NOT_CONFIGURED")
        if not self._exists(session_id):
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        self._consents[session_id] = ConsentCapability(
            session_id, PROFILE_ID, str(self.status()["policy_generation"])
        )
        return {
            "session_id": session_id,
            "consent": "ACTIVE_IN_MEMORY",
            "provider": "OpenAI",
            "profile_id": PROFILE_ID,
            "notice": "OpenAI получит только явно разрешённые для этой цели материалы; фоновых вызовов нет.",
        }

    def revoke(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        self._consents.pop(session_id, None)
        return {"session_id": session_id, "consent": "ABSENT"}

    def request_first_question(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        return (
            self.get(session_id)
            if self.get(session_id)["current_question"] is not None
            else self._perform(session_id, None)
        )

    def submit(self, session_id: Any, client_submission_id: Any, content: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        return self._perform(
            session_id,
            self._persist_answer(
                session_id, _text(client_submission_id, 96), _text(content, 12000)
            ),
        )

    def retry(self, session_id: Any, answer_turn_id: Any) -> dict[str, Any]:
        session_id, answer_turn_id = _text(session_id, 64), _text(answer_turn_id, 64)
        if (
            self._reflection.connection.execute(
                "SELECT 1 FROM interview_submissions WHERE interview_session_id=? AND turn_id=?",
                (session_id, answer_turn_id),
            ).fetchone()
            is None
        ):
            raise PersonalAIError("INTERVIEW_RETRY_REJECTED")
        return self._perform(session_id, answer_turn_id)

    def control(self, session_id: Any, action: Any, topic: Any = None) -> dict[str, Any]:
        session_id, action = _text(session_id, 64), _text(action, 32)
        if action not in {"SKIP", "DECLINE", "CHANGE_TOPIC", "STOP", "END", "CONTINUE"}:
            raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        now = _now()
        with self._reflection.connection:
            if action in {"SKIP", "DECLINE"}:
                self._reflection.connection.execute(
                    "UPDATE interview_questions SET status=? WHERE interview_session_id=? AND status='CURRENT'",
                    ("SKIPPED" if action == "SKIP" else "DECLINED", session_id),
                )
                self._reflection.connection.execute(
                    "UPDATE interview_sessions SET state='ACTIVE',updated_at=? WHERE interview_session_id=?",
                    (now, session_id),
                )
            elif action == "CHANGE_TOPIC":
                self._reflection.connection.execute(
                    "UPDATE interview_questions SET status='SUPERSEDED' WHERE interview_session_id=? AND status='CURRENT'",
                    (session_id,),
                )
                self._reflection.connection.execute(
                    "UPDATE interview_sessions SET owner_topic=?,state='ACTIVE',updated_at=? WHERE interview_session_id=?",
                    (_text(topic, MAX_QUESTION), now, session_id),
                )
            elif action == "CONTINUE":
                self._reflection.connection.execute(
                    "UPDATE interview_sessions SET state='ACTIVE',updated_at=? WHERE interview_session_id=?",
                    (now, session_id),
                )
            else:
                self._reflection.connection.execute(
                    "UPDATE interview_sessions SET state=?,ended_at=?,updated_at=? WHERE interview_session_id=?",
                    (
                        "COMPLETED" if action == "END" else "PAUSED",
                        now if action == "END" else None,
                        now,
                        session_id,
                    ),
                )
        if action in {"STOP", "END"}:
            self._consents.pop(session_id, None)
        return self.get(session_id)

    def disclosure(self, attempt_id: Any) -> dict[str, Any]:
        attempt_id = _text(attempt_id, 64)
        fields = (
            "attempt_id",
            "interview_session_id",
            "state",
            "provider_profile",
            "model",
            "config_id",
            "schema_id",
            "source_item_count",
            "source_char_count",
            "inquiry_item_count",
            "inquiry_char_count",
            "context_char_count",
            "created_at",
            "sent_at",
            "completed_at",
            "error_code",
        )
        row = self._reflection.connection.execute(
            "SELECT attempt_id,interview_session_id,state,provider_profile,model,config_id,schema_id,source_item_count,source_char_count,inquiry_item_count,inquiry_char_count,context_char_count,created_at,sent_at,completed_at,error_code FROM interview_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        if row is None:
            raise PersonalAIError("DISCLOSURE_NOT_FOUND")
        result = dict(zip(fields, row, strict=True))
        result["transmission"] = (
            "NOT_SENT"
            if result["state"] == "PREPARED"
            else "OUTCOME_UNKNOWN"
            if result["state"] == "OUTCOME_UNKNOWN"
            else "SENT"
            if result["sent_at"]
            else "NOT_SENT"
        )
        items = self._reflection.connection.execute(
            "SELECT m.alias,m.turn_id,m.policy_id,m.ordinal,m.char_count,t.content FROM interview_attempt_manifest_items m JOIN reflection_turns t ON t.turn_id=m.turn_id WHERE m.attempt_id=? ORDER BY m.ordinal",
            (attempt_id,),
        ).fetchall()
        result["items"] = [
            dict(
                zip(
                    ("alias", "turn_id", "policy_id", "ordinal", "char_count", "content"),
                    item,
                    strict=True,
                )
            )
            for item in items
        ]
        inquiry = self._reflection.connection.execute(
            "SELECT i.item_id,i.kind,i.text,i.priority,i.derivation_id FROM interview_attempt_inquiry_items a JOIN interview_inquiry_items i ON i.item_id=a.item_id WHERE a.attempt_id=? ORDER BY a.ordinal",
            (attempt_id,),
        ).fetchall()
        result["inquiry"] = [
            dict(zip(("item_id", "kind", "text", "priority"), row[:4], strict=True))
            for row in inquiry
            if self._derivation_eligible(str(row[4]))
        ]
        return result

    def get(self, session_id: Any) -> dict[str, Any]:
        session_id = _text(session_id, 64)
        names = (
            "interview_session_id",
            "source_session_id",
            "state",
            "owner_topic",
            "summary",
            "next_direction",
            "created_at",
            "updated_at",
            "ended_at",
        )
        row = self._reflection.connection.execute(
            "SELECT interview_session_id,source_session_id,state,owner_topic,summary,next_direction,created_at,updated_at,ended_at FROM interview_sessions WHERE interview_session_id=?",
            (session_id,),
        ).fetchone()
        if row is None:
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        result = dict(zip(names, row, strict=True))
        question = self._reflection.connection.execute(
            "SELECT q.question_id,q.question,q.rationale,q.decision,q.basis_aliases,q.created_at,q.derivation_id,d.attempt_id FROM interview_questions q JOIN interview_derivations d ON d.derivation_id=q.derivation_id WHERE q.interview_session_id=? AND q.status='CURRENT'",
            (session_id,),
        ).fetchone()
        if question is None:
            result["current_question"] = None
        else:
            result["current_question"] = dict(
                zip(
                    (
                        "question_id",
                        "question",
                        "rationale",
                        "decision",
                        "basis_aliases",
                        "created_at",
                        "derivation_id",
                        "attempt_id",
                    ),
                    question,
                    strict=True,
                )
            )
            result["current_question"]["basis_aliases"] = json.loads(
                result["current_question"]["basis_aliases"]
            )
        attempts = self._reflection.connection.execute(
            "SELECT attempt_id,state,answer_turn_id,created_at,error_code FROM interview_attempts WHERE interview_session_id=? ORDER BY created_at DESC",
            (session_id,),
        ).fetchall()
        result["attempts"] = [
            dict(
                zip(
                    ("attempt_id", "state", "answer_turn_id", "created_at", "error_code"),
                    item,
                    strict=True,
                )
            )
            for item in attempts
        ]
        result["consent"] = "ACTIVE_IN_MEMORY" if session_id in self._consents else "ABSENT"
        return result

    def _exists(self, session_id: str) -> bool:
        return (
            self._reflection.connection.execute(
                "SELECT 1 FROM interview_sessions WHERE interview_session_id=?", (session_id,)
            ).fetchone()
            is not None
        )

    def _require_consent(self, session_id: str) -> None:
        capability = self._consents.get(session_id)
        status = self.status()
        if capability is None or capability.provider_profile != PROFILE_ID:
            raise PersonalAIError("AI_CONSENT_REQUIRED")
        if not status["policy_enabled"] or capability.policy_generation != str(
            status["policy_generation"]
        ):
            self._consents.pop(session_id, None)
            raise PersonalAIError("AI_POLICY_DISABLED")

    def _upsert_policy(self, turn_id: str, enabled: bool, assigned_by: str, now: str) -> None:
        self._reflection.connection.execute(
            "INSERT INTO interview_source_policies(turn_id,policy_id,enabled,sensitivity,processing_location,cloud_policy,purpose,provider_profile,third_party_scope,lineage_rule,assigned_by,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(turn_id) DO UPDATE SET enabled=excluded.enabled,sensitivity=excluded.sensitivity,processing_location=excluded.processing_location,cloud_policy=excluded.cloud_policy,purpose=excluded.purpose,provider_profile=excluded.provider_profile,third_party_scope=excluded.third_party_scope,lineage_rule=excluded.lineage_rule,assigned_by=excluded.assigned_by,updated_at=excluded.updated_at",
            (
                turn_id,
                f"interview-source-{turn_id}",
                int(enabled),
                "sensitive",
                "approved_cloud",
                "named_purpose_and_provider",
                PURPOSE,
                PROFILE_ID,
                "none",
                "most_restrictive_parent",
                assigned_by,
                now,
            ),
        )

    def _persist_answer(self, session_id: str, submission_id: str, content: str) -> str:
        c, now = self._reflection.connection, _now()
        with c:
            prior = c.execute(
                "SELECT turn_id FROM interview_submissions WHERE interview_session_id=? AND client_submission_id=?",
                (session_id, submission_id),
            ).fetchone()
            if prior is not None:
                return str(prior[0])
            source = c.execute(
                "SELECT source_session_id,state FROM interview_sessions WHERE interview_session_id=?",
                (session_id,),
            ).fetchone()
            if source is None or source[1] == "COMPLETED":
                raise PersonalAIError("INTERVIEW_NOT_ACTIVE")
            count = c.execute(
                "SELECT turn_count FROM reflection_sessions WHERE session_id=?", (source[0],)
            ).fetchone()
            if count is None:
                raise PersonalAIError("INTERVIEW_NOT_FOUND")
            turn_id, seq = generate_id(), int(count[0]) + 1
            c.execute(
                "INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)",
                (turn_id, source[0], seq, "USER", now, content),
            )
            c.execute(
                "UPDATE reflection_sessions SET turn_count=?,updated_at=? WHERE session_id=?",
                (seq, now, source[0]),
            )
            c.execute(
                "INSERT INTO interview_submissions VALUES(?,?,?,?)",
                (session_id, submission_id, turn_id, now),
            )
            if session_id in self._consents:
                self._upsert_policy(turn_id, True, "SESSION_CONSENT", now)
            c.execute(
                "UPDATE interview_questions SET status='ANSWERED' WHERE interview_session_id=? AND status='CURRENT'",
                (session_id,),
            )
            c.execute(
                "UPDATE interview_sessions SET state='ACTIVE',updated_at=? WHERE interview_session_id=?",
                (now, session_id),
            )
        return turn_id

    def _policy_for_turn(self, turn_id: str) -> tuple[PolicyAxes, str] | None:
        row = self._reflection.connection.execute(
            "SELECT policy_id,enabled,sensitivity,processing_location,cloud_policy,purpose,provider_profile,third_party_scope,lineage_rule FROM interview_source_policies WHERE turn_id=?",
            (turn_id,),
        ).fetchone()
        if row is None or not row[1]:
            return None
        try:
            effective = resolve_effective_policy(
                [
                    PolicyAxes(
                        sensitivity=row[2],
                        processing_location=row[3],
                        cloud_policy=row[4],
                        purpose=row[5],
                        third_party_scope=row[7],
                        lineage_rule=row[8],
                    )
                ],
                [PolicyId(row[0])],
            ).effective
        except Exception:
            return None
        if (
            effective.processing_location != ProcessingLocation.APPROVED_CLOUD
            or effective.cloud_policy != CloudPolicy.NAMED_PURPOSE_AND_PROVIDER
            or effective.purpose != PURPOSE
            or row[6] != PROFILE_ID
            or effective.third_party_scope != ThirdPartyScope.NONE
        ):
            return None
        return effective, str(row[0])

    def _derivation_eligible(self, derivation_id: str) -> bool:
        rows = self._reflection.connection.execute(
            "SELECT turn_id FROM interview_derivation_sources WHERE derivation_id=?",
            (derivation_id,),
        ).fetchall()
        return bool(rows) and all(self._policy_for_turn(str(row[0])) is not None for row in rows)

    def _select(
        self, session_id: str
    ) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
        rows = self._reflection.connection.execute(
            "SELECT turn_id,content,created_at FROM (SELECT t.turn_id,t.content,t.created_at FROM interview_sessions i JOIN reflection_turns t ON t.session_id=i.source_session_id WHERE i.interview_session_id=? UNION ALL SELECT t.turn_id,t.content,t.created_at FROM reflection_turns t WHERE t.actor='USER' AND t.session_id NOT IN (SELECT source_session_id FROM interview_sessions WHERE interview_session_id=?)) ORDER BY created_at DESC,turn_id DESC",
            (session_id, session_id),
        ).fetchall()
        sources = []
        chars = 0
        for turn_id, content, _ in rows:
            policy = self._policy_for_turn(str(turn_id))
            if (
                policy is None
                or len(sources) == MAX_SOURCE_ITEMS
                or chars + len(content) > MAX_SOURCE_CHARS
            ):
                continue
            sources.append(
                {
                    "alias": f"S{len(sources) + 1}",
                    "turn_id": str(turn_id),
                    "content": str(content),
                    "char_count": len(content),
                    "policy_id": policy[1],
                }
            )
            chars += len(content)
        planning = []
        session = self._reflection.connection.execute(
            "SELECT owner_topic,next_direction,next_direction_derivation_id FROM interview_sessions WHERE interview_session_id=?",
            (session_id,),
        ).fetchone()
        if session and session[0]:
            planning.append({"kind": "OWNER_TOPIC", "text": str(session[0])})
        question = self._reflection.connection.execute(
            "SELECT question,status,derivation_id FROM interview_questions WHERE interview_session_id=? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if question and self._derivation_eligible(str(question[2])):
            planning.append(
                {"kind": "QUESTION_CONTROL", "text": str(question[0]), "state": str(question[1])}
            )
        if session and session[1] and session[2] and self._derivation_eligible(str(session[2])):
            planning.append({"kind": "NEXT_DIRECTION", "text": str(session[1])})
        prior = self._reflection.connection.execute(
            "SELECT next_direction,next_direction_derivation_id FROM interview_sessions WHERE interview_session_id<>? AND next_direction IS NOT NULL ORDER BY updated_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if prior and prior[1] and self._derivation_eligible(str(prior[1])):
            planning.append({"kind": "SAVED_DIRECTION", "text": str(prior[0])})
        inquiry = []
        for item_id, kind, text, priority, derivation_id in self._reflection.connection.execute(
            "SELECT item_id,kind,text,priority,derivation_id FROM interview_inquiry_items WHERE state='ACTIVE' ORDER BY priority DESC,created_at DESC,item_id ASC"
        ):
            if len(inquiry) < MAX_INQUIRY_ITEMS and self._derivation_eligible(str(derivation_id)):
                inquiry.append(
                    {
                        "item_id": str(item_id),
                        "kind": str(kind),
                        "text": str(text),
                        "priority": int(priority),
                        "char_count": len(text),
                    }
                )
        total = (
            sum(x["char_count"] for x in sources)
            + sum(x["char_count"] for x in inquiry)
            + sum(len(x["text"]) for x in planning)
        )
        for group, key in ((sources, "char_count"), (inquiry, "char_count"), (planning, "text")):
            while total > MAX_CONTEXT_CHARS and group:
                total -= len(group[-1][key]) if key == "text" else group[-1][key]
                group.pop()
        return tuple(sources), tuple(inquiry), tuple(planning)

    def _perform(self, session_id: str, answer_turn_id: str | None) -> dict[str, Any]:
        self._require_consent(session_id)
        if not self._exists(session_id):
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        sources, inquiry, planning = self._select(session_id)
        source_chars = sum(x["char_count"] for x in sources)
        inquiry_chars = sum(x["char_count"] for x in inquiry)
        context_chars = source_chars + inquiry_chars + sum(len(x["text"]) for x in planning)
        attempt_id, now, c = generate_id(), _now(), self._reflection.connection
        with c:
            c.execute(
                "INSERT INTO interview_attempts VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    attempt_id,
                    session_id,
                    answer_turn_id,
                    PURPOSE,
                    PROFILE_ID,
                    MODEL,
                    CONFIG_ID,
                    SCHEMA_ID,
                    "PREPARED",
                    1,
                    len(sources),
                    source_chars,
                    len(inquiry),
                    inquiry_chars,
                    context_chars,
                    now,
                    None,
                    None,
                    None,
                ),
            )
            for ordinal, item in enumerate(sources, 1):
                c.execute(
                    "INSERT INTO interview_attempt_manifest_items VALUES(?,?,?,?,?,?)",
                    (
                        attempt_id,
                        item["alias"],
                        item["turn_id"],
                        item["policy_id"],
                        ordinal,
                        item["char_count"],
                    ),
                )
            for ordinal, item in enumerate(inquiry, 1):
                c.execute(
                    "INSERT INTO interview_attempt_inquiry_items VALUES(?,?,?,?)",
                    (attempt_id, item["item_id"], ordinal, item["char_count"]),
                )
        manifest = {
            "attempt_id": attempt_id,
            "purpose": PURPOSE,
            "profile_id": PROFILE_ID,
            "model": MODEL,
            "config_id": CONFIG_ID,
            "schema_id": SCHEMA_ID,
            "source_aliases": [x["alias"] for x in sources],
            "max_source_items": MAX_SOURCE_ITEMS,
            "max_source_chars": MAX_SOURCE_CHARS,
            "max_context_chars": MAX_CONTEXT_CHARS,
        }
        packet = {"sources": sources, "inquiry": inquiry, "planning": planning}
        try:
            with c:
                c.execute(
                    "UPDATE interview_attempts SET state='SENT',sent_at=? WHERE attempt_id=?",
                    (_now(), attempt_id),
                )
            raw, actual_model = self._provider.invoke_ai_interview(
                manifest, packet, self._keys._consume_for_request()
            )
        except ProviderTimeoutError:
            with c:
                c.execute(
                    "UPDATE interview_attempts SET state='OUTCOME_UNKNOWN',completed_at=?,error_code='PROVIDER_OUTCOME_UNKNOWN' WHERE attempt_id=?",
                    (_now(), attempt_id),
                )
            raise PersonalAIError("PROVIDER_OUTCOME_UNKNOWN") from None
        except (ProviderUnavailableError, PersonalAIError) as exc:
            with c:
                c.execute(
                    "UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?",
                    (_now(), getattr(exc, "code", "PROVIDER_FAILED"), attempt_id),
                )
            raise PersonalAIError(getattr(exc, "code", "PROVIDER_FAILED")) from None
        if actual_model != MODEL:
            with c:
                c.execute(
                    "UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code='MODEL_NOT_AVAILABLE' WHERE attempt_id=?",
                    (_now(), attempt_id),
                )
            raise PersonalAIError("MODEL_NOT_AVAILABLE")
        try:
            parsed = validate_interview_output(raw, {x["alias"] for x in sources})
        except PersonalAIError as exc:
            with c:
                c.execute(
                    "UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?",
                    (_now(), exc.code, attempt_id),
                )
            raise
        self._commit(session_id, attempt_id, sources, answer_turn_id, parsed, actual_model)
        return self.get(session_id)

    def _commit(
        self,
        session_id: str,
        attempt_id: str,
        sources: tuple[dict[str, Any], ...],
        answer_turn_id: str | None,
        value: dict[str, Any],
        actual_model: str,
    ) -> None:
        now, c, derivation_id = _now(), self._reflection.connection, generate_id()
        by_alias = {x["alias"]: x for x in sources}
        with c:
            c.execute(
                "UPDATE interview_attempts SET state='SUCCEEDED',completed_at=?,model=? WHERE attempt_id=?",
                (now, actual_model, attempt_id),
            )
            c.execute(
                "INSERT INTO interview_derivations VALUES(?,?,?,?)",
                (derivation_id, attempt_id, "VALIDATED", now),
            )
            for item in sources:
                c.execute(
                    "INSERT INTO interview_derivation_sources VALUES(?,?,?)",
                    (derivation_id, item["turn_id"], item["alias"]),
                )
            c.execute(
                "UPDATE interview_questions SET status='SUPERSEDED' WHERE interview_session_id=? AND status='CURRENT'",
                (session_id,),
            )
            if value["decision"] == "ASK":
                question_id = generate_id()
                c.execute(
                    "INSERT INTO interview_questions VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        question_id,
                        session_id,
                        derivation_id,
                        value["question"],
                        value["rationale"],
                        value["decision"],
                        "CURRENT",
                        json.dumps(value["basis_aliases"]),
                        now,
                    ),
                )
                for alias in value["basis_aliases"]:
                    c.execute(
                        "INSERT INTO interview_question_basis VALUES(?,?,?)",
                        (question_id, alias, by_alias[alias]["turn_id"]),
                    )
            for item in value["inquiry_items"]:
                c.execute(
                    "INSERT INTO interview_inquiry_items VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        generate_id(),
                        session_id,
                        derivation_id,
                        item["kind"],
                        item["text"],
                        item["priority"],
                        "ACTIVE",
                        answer_turn_id,
                        now,
                    ),
                )
            state = "END_RECOMMENDED" if value["decision"] == "END_RECOMMENDED" else "ACTIVE"
            summary_id = derivation_id if value["summary"] is not None else None
            direction_id = derivation_id if value["next_direction"] is not None else None
            c.execute(
                "UPDATE interview_sessions SET state=?,summary=?,next_direction=?,summary_derivation_id=?,next_direction_derivation_id=?,updated_at=? WHERE interview_session_id=?",
                (
                    state,
                    value["summary"],
                    value["next_direction"],
                    summary_id,
                    direction_id,
                    now,
                    session_id,
                ),
            )


def validate_interview_output(raw: Any, aliases: set[str]) -> dict[str, Any]:
    required = {
        "schema_version",
        "decision",
        "question",
        "rationale",
        "basis_aliases",
        "summary",
        "next_direction",
        "inquiry_items",
    }
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema_version") != SCHEMA_ID:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    decision = raw.get("decision")
    if (
        decision not in {"ASK", "END_RECOMMENDED"}
        or not isinstance(raw["basis_aliases"], list)
        or len(raw["basis_aliases"]) > MAX_SOURCE_ITEMS
        or len(set(raw["basis_aliases"])) != len(raw["basis_aliases"])
        or not all(isinstance(a, str) and a in aliases for a in raw["basis_aliases"])
    ):
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    question = raw["question"]
    if decision == "ASK":
        question = _safe(_text(question, MAX_QUESTION))
        if question.count("?") != 1 or not question.endswith("?"):
            raise PersonalAIError("AI_OUTPUT_REJECTED")
    elif question is not None:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    rationale = _safe(_text(raw["rationale"], MAX_RATIONALE))
    summary, next_direction = raw["summary"], raw["next_direction"]
    if decision == "END_RECOMMENDED":
        summary, next_direction = (
            _safe(_text(summary, MAX_RATIONALE)),
            _safe(_text(next_direction, MAX_RATIONALE)),
        )
    elif summary is not None or next_direction is not None:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    if not isinstance(raw["inquiry_items"], list) or len(raw["inquiry_items"]) > 6:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    items = []
    for item in raw["inquiry_items"]:
        if (
            not isinstance(item, dict)
            or set(item) != {"kind", "text", "priority"}
            or item["kind"]
            not in {"THEME", "WHITE_SPOT", "REVISIT", "HYPOTHESIS", "CONTRADICTION", "UNKNOWN"}
            or not isinstance(item["priority"], int)
            or not 1 <= item["priority"] <= 5
        ):
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        items.append(
            {
                "kind": item["kind"],
                "text": _safe(_text(item["text"], MAX_QUESTION)),
                "priority": item["priority"],
            }
        )
    return {
        "decision": decision,
        "question": question,
        "rationale": rationale,
        "basis_aliases": raw["basis_aliases"],
        "summary": summary,
        "next_direction": next_direction,
        "inquiry_items": items,
    }
