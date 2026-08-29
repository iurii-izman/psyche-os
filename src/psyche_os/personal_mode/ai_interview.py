"""Bounded local planner for the stateless Personal AI Interview provider."""

from __future__ import annotations

from collections.abc import Sequence
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
CONFIG_ID = "personal-ai-interview-v3-change-v14-8000-m6-1600"
SCHEMA_ID = "personal-ai-interview-output-v3"
PURPOSE = "personal_ai_interview"
MAX_SOURCE_ITEMS, MAX_SOURCE_CHARS, MAX_INQUIRY_ITEMS, MAX_CONTEXT_CHARS = 12, 8000, 8, 8000
MAX_QUESTION = MAX_RATIONALE = 480
MAX_MODEL_ITEMS, MAX_MODEL_CHARS, MAX_MODEL_DELTA = 6, 1600, 3
MAX_CHANGE_ITEMS, MAX_CHANGE_CHARS = 2, 1600
MODEL_KINDS = ("HYPOTHESIS", "PATTERN", "CONTRADICTION", "UNKNOWN")
CHANGE_KINDS = ("OBSERVE", "EXPERIMENT")
CHANGE_SIGNALS = ("BETTER", "SAME", "WORSE", "UNCLEAR", "NOT_APPLICABLE")
PRACTICAL_EFFECTS = ("HELPED", "NO_CLEAR_EFFECT", "WORSE", "MIXED", "NOT_TESTED")
EPISTEMIC_OUTCOMES = ("SUPPORTED", "WEAKENED", "INCONCLUSIVE", "CONTEXT_DEPENDENT")
RECOMMENDED_NEXT = ("COMPLETE", "CONTINUE_OBSERVING", "RETURN_TO_INQUIRY")
TEMPORAL_SCOPES = ("CURRENT_STATE", "CONTEXTUAL_PATTERN", "CROSS_PERIOD_PATTERN", "HISTORICAL_CHANGED", "UNCLEAR")
DELTA_ACTIONS = ("CREATE", "REVISE", "CONTEST", "RESOLVE")
_UNSAFE = (
    r"(?:\u0443\s+вас|you\s+have)\s+(?:депресси\w*|биполяр\w*|параной\w*|diagnos\w*)",
    r"(?:диагноз\w*|diagnos\w*)",
    r"(?:начните\s+(?:лечени\w*|treatment\w*))",
    r"(?:вам\s+нужно|you\s+need\s+to)\s+(?:начать\s+)?(?:лечени\w*|treatment\w*)",
    r"(?:назначаю|принимайте|дозировк\w*|medication\s+directive)",
    r"(?:вытесненн\w*\s+памят\w*|recovered\s+memory)",
    r"(?:только\s+я|i\s+need\s+you|я\s+всегда\s+рядом|i\s+am\s+always\s+here|наблюдаю\s+за|спасу\s+вас)",
)
_CHANGE_UNSAFE = (
    r"(?:лекарств|медикамент|таблет|дозиров|препарат|medication|supplement|drug|substance)",
    r"(?:голодан|fasting|диет\w*|sleep\s+depriv|лишени\w*\s+сна|опасн\w*\s+упражнен)",
    r"(?:самоповреж|self-harm|вождени|driving|незакон|illegal|финансов\w*\s+обяз|кредит)",
    r"(?:увольн|quit\s+(?:your\s+)?job|расставан|relationship\s+break|разрыв\s+отношен)",
    r"(?:манипул|обман|deception|принужд|coerc|конфликт\w*\s+с\s+друг)",
    r"(?:диагноз|diagnos|терапи\w*|treatment)",
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


def _safe_change(value: str) -> str:
    if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in _CHANGE_UNSAFE):
        raise PersonalAIError("AI_OUTPUT_UNSAFE")
    return _safe(value)


def _canonical_inquiry_text(value: str) -> str:
    """Deliberately narrow duplicate key; this is not semantic/fuzzy merging."""
    return " ".join(value.casefold().split())


_ABSOLUTE_TRAIT = (
    r"вы\s+всегда\s+(?:были\s+)?(?:так\w*|таким)",
    r"вы\s+никогда\s+не\s+",
    r"ты\s+всегда\s+",
    r"это\s+точн",
    r"это\s+факт",
    r"точно\s+являетс",
    r"you\s+always\s+are",
    r"you\s+never\s+",
    r"definitely\s+is",
)


def _working_language(value: str) -> str:
    """Reject absolute stable-trait certainty; working language stays provisional."""
    if any(re.search(pattern, value, flags=re.IGNORECASE) for pattern in _ABSOLUTE_TRAIT):
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
        eligible = self._reflection.connection.execute(
            "SELECT count(*) FROM interview_source_policies WHERE enabled=1 AND purpose=? AND provider_profile=?",
            (PURPOSE, PROFILE_ID),
        ).fetchone()[0]
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
                "max_model_items": MAX_MODEL_ITEMS,
                "max_model_chars": MAX_MODEL_CHARS,
                "max_model_delta": MAX_MODEL_DELTA,
                "max_change_items": MAX_CHANGE_ITEMS,
                "max_change_chars": MAX_CHANGE_CHARS,
            },
            "eligible_source_count": int(eligible),
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
                {
                    **dict(zip(names, row, strict=True)),
                    "derived_items": self._derived_items(str(row[0])),
                }
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
            "SELECT m.alias,m.turn_id,m.policy_id,m.ordinal,m.char_count,t.content,t.created_at,t.session_id,s.title FROM interview_attempt_manifest_items m JOIN reflection_turns t ON t.turn_id=m.turn_id JOIN reflection_sessions s ON s.session_id=t.session_id WHERE m.attempt_id=? ORDER BY m.ordinal",
            (attempt_id,),
        ).fetchall()
        result["items"] = [
            dict(
                zip(
                    ("alias", "turn_id", "policy_id", "ordinal", "char_count", "content", "created_at", "session_id", "session_title"),
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
        model_items = self._reflection.connection.execute(
            "SELECT a.alias,r.kind,r.text,r.temporal_scope,r.uncertainty,a.sent_state,r.derivation_id FROM interview_attempt_model_items a "
            "JOIN personal_model_revisions r ON r.revision_id=a.revision_id "
            "WHERE a.attempt_id=? ORDER BY a.ordinal",
            (attempt_id,),
        ).fetchall()
        # Historical truth: this section answers "what was transmitted then",
        # using the immutable sent-state snapshot and the surviving immutable
        # revision.  Current policy must not rewrite it; deleted content
        # disappears through the existing FK deletion closure instead.
        result["model_items"] = [
            {
                "alias": str(alias),
                "kind": str(kind),
                "text": str(text),
                "temporal_scope": str(scope),
                "uncertainty": uncertainty,
                "state": str(sent_state),
            }
            for alias, kind, text, scope, uncertainty, sent_state, _derivation_id in model_items
        ]
        change_items = [] if self._reflection.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='interview_attempt_change_items'"
        ).fetchone() is None else self._reflection.connection.execute(
            "SELECT a.alias,p.kind,p.title,p.instructions,p.expected_signal,p.counter_signal,a.sent_state FROM interview_attempt_change_items a JOIN change_plans p ON p.plan_id=a.plan_id WHERE a.attempt_id=? ORDER BY a.ordinal",
            (attempt_id,),
        ).fetchall()
        result["change_items"] = [
            {"alias": str(alias), "kind": str(kind), "title": str(title), "instructions": str(instructions), "expected_signal": str(expected), "counter_signal": str(counter), "state": str(state)}
            for alias, kind, title, instructions, expected, counter, state in change_items
        ]
        return result

    def model(self) -> dict[str, Any]:
        """Local, inspectable Personal Model view; eligibility never hides local state."""
        items = []
        for item_id, kind, state, created_at, updated_at in self._reflection.connection.execute(
            "SELECT item_id,kind,state,created_at,updated_at FROM personal_model_items ORDER BY updated_at DESC,item_id ASC"
        ).fetchall():
            # Effective owner-facing state: an owner challenge overlays the
            # base AI lifecycle state without mutating it.
            challenges = self._reflection.connection.execute(
                "SELECT count(*) FROM personal_model_challenges WHERE item_id=?",
                (item_id,),
            ).fetchone()[0]
            effective_state = "CONTESTED" if challenges else str(state)
            revisions = self._reflection.connection.execute(
                "SELECT revision_id,ordinal,kind,text,temporal_scope,uncertainty,revision_reason,derivation_id,owner_turn_id,status,created_at FROM personal_model_revisions WHERE item_id=? ORDER BY ordinal ASC",
                (item_id,),
            ).fetchall()
            current = next((row for row in revisions if row[9] == "CURRENT"), None)

            def excerpts(revision_id: str, role: str) -> list[dict[str, str]]:
                rows = self._reflection.connection.execute(
                    "SELECT t.turn_id,t.content,t.created_at,t.session_id FROM personal_model_revision_sources s JOIN reflection_turns t ON t.turn_id=s.turn_id WHERE s.revision_id=? AND s.role=? ORDER BY t.created_at,t.turn_id",
                    (revision_id, role),
                ).fetchall()
                return [
                    {"turn_id": str(turn_id), "content": str(content), "created_at": str(created), "session_id": str(session_id)}
                    for turn_id, content, created, session_id in rows
                ]

            challenges = [
                {
                    "text": str(content),
                    "created_at": str(challenge_created),
                }
                for content, challenge_created in self._reflection.connection.execute(
                    "SELECT t.content,ch.created_at FROM personal_model_challenges ch JOIN reflection_turns t ON t.turn_id=ch.turn_id WHERE ch.item_id=? ORDER BY ch.created_at",
                    (item_id,),
                ).fetchall()
            ]
            history = [
                {
                    "ordinal": int(ordinal),
                    "kind": str(rev_kind),
                    "text": str(rev_text),
                    "temporal_scope": str(scope),
                    "revision_reason": reason,
                    "status": str(status),
                    "created_at": str(rev_created),
                }
                for _rid, ordinal, rev_kind, rev_text, scope, _unc, reason, _der, _oturn, status, rev_created in revisions
            ]
            items.append(
                {
                    "item_id": str(item_id),
                    "kind": str(kind),
                    "state": effective_state,
                    "created_at": str(created_at),
                    "updated_at": str(updated_at),
                    "current": None
                    if current is None
                    else {
                        "revision_id": str(current[0]),
                        "text": str(current[3]),
                        "temporal_scope": str(current[4]),
                        "uncertainty": current[5],
                        "created_at": str(current[10]),
                        "support": excerpts(str(current[0]), "SUPPORT"),
                        "counterevidence": excerpts(str(current[0]), "COUNTEREVIDENCE"),
                    },
                    "challenges": challenges,
                    "history": history,
                }
            )
        return {"items": items}

    def challenge(self, item_id: Any, content: Any) -> dict[str, Any]:
        """Record an owner correction as USER SOURCE; no provider call happens."""
        item_id, content = _text(item_id, 64), _text(content, 12000)
        c, now = self._reflection.connection, _now()
        with c:
            item = c.execute(
                "SELECT state FROM personal_model_items WHERE item_id=?",
                (item_id,),
            ).fetchone()
            if item is None:
                raise PersonalAIError("MODEL_ITEM_NOT_FOUND")
            revision = c.execute(
                "SELECT revision_id FROM personal_model_revisions WHERE item_id=? AND status='CURRENT'",
                (item_id,),
            ).fetchone()
            if revision is None:
                raise PersonalAIError("MODEL_ITEM_NOT_FOUND")
            session = c.execute(
                "SELECT session_id,turn_count FROM reflection_sessions WHERE title=? AND state='ACTIVE' ORDER BY created_at DESC LIMIT 1",
                ("Исправления рабочей модели",),
            ).fetchone()
            if session is None:
                session_id = self._reflection.create_session("Исправления рабочей модели")["session_id"]
                turn_count = 0
            else:
                session_id, turn_count = str(session[0]), int(session[1])
            turn_id, seq = generate_id(), turn_count + 1
            c.execute(
                "INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)",
                (turn_id, session_id, seq, "USER", now, content),
            )
            c.execute(
                "UPDATE reflection_sessions SET turn_count=?,updated_at=? WHERE session_id=?",
                (seq, now, session_id),
            )
            c.execute(
                "INSERT INTO personal_model_challenges VALUES(?,?,?,?,?)",
                (generate_id(), item_id, str(revision[0]), turn_id, now),
            )
            # Owner correction is an overlay on the base AI lifecycle state:
            # the challenge relation itself carries the owner-contested state,
            # so the base item row is never mutated here.
        return self.model()

    def changes(self) -> dict[str, Any]:
        rows = self._reflection.connection.execute("SELECT plan_id,kind,state,title,reason,instructions,observation_prompt,expected_signal,counter_signal,duration_days,stop_conditions,created_at,activated_at,ended_at FROM change_plans ORDER BY created_at DESC").fetchall()
        plans = [dict(zip(("plan_id","kind","state","title","reason","instructions","observation_prompt","expected_signal","counter_signal","duration_days","stop_conditions","created_at","activated_at","ended_at"), row, strict=True)) for row in rows]
        for plan in plans:
            plan["targets"] = [
                {"item_id": str(item_id), "revision_id": str(revision_id), "text": str(text), "kind": str(kind)}
                for item_id, revision_id, text, kind in self._reflection.connection.execute(
                    "SELECT t.item_id,t.revision_id,r.text,r.kind FROM change_plan_targets t JOIN personal_model_revisions r ON r.revision_id=t.revision_id WHERE t.plan_id=? ORDER BY t.item_id",
                    (plan["plan_id"],),
                ).fetchall()
            ]
            plan["observations"] = [
                {"turn_id": str(turn_id), "content": str(content), "signal": signal, "created_at": str(created_at), "ai_eligible": self._policy_for_turn(str(turn_id)) is not None}
                for turn_id, content, signal, created_at in self._reflection.connection.execute(
                    "SELECT t.turn_id,t.content,o.signal,o.created_at FROM change_observations o JOIN reflection_turns t ON t.turn_id=o.turn_id WHERE o.plan_id=? ORDER BY o.created_at",
                    (plan["plan_id"],),
                ).fetchall()
            ]
            review = self._reflection.connection.execute(
                "SELECT practical_effect,epistemic_outcome,summary,understanding,recommended_next,created_at FROM change_reviews WHERE plan_id=? ORDER BY created_at DESC,review_id DESC LIMIT 1",
                (plan["plan_id"],),
            ).fetchone()
            plan["review"] = None if review is None else dict(zip(("practical_effect", "epistemic_outcome", "summary", "understanding", "recommended_next", "created_at"), review, strict=True))
        return {"plans": plans}

    def allow_change_observations(self, plan_id: Any, enabled: Any) -> dict[str, Any]:
        plan_id = _text(plan_id, 64)
        if not isinstance(enabled, bool):
            raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        rows = self._reflection.connection.execute(
            "SELECT turn_id FROM change_observations WHERE plan_id=? ORDER BY created_at,observation_id",
            (plan_id,),
        ).fetchall()
        if not rows:
            raise PersonalAIError("CHANGE_OBSERVATIONS_NOT_FOUND")
        # Use the existing exact per-turn source policy, in its existing bounded batches.
        for offset in range(0, len(rows), MAX_SOURCE_ITEMS):
            self.set_source_policy([str(row[0]) for row in rows[offset:offset + MAX_SOURCE_ITEMS]], enabled)
        return self.changes()

    def start_change_review(self, plan_id: Any) -> dict[str, Any]:
        plan_id = _text(plan_id, 64)
        row = self._reflection.connection.execute(
            "SELECT state,derivation_id FROM change_plans WHERE plan_id=?", (plan_id,)
        ).fetchone()
        if row is None:
            raise PersonalAIError("CHANGE_NOT_FOUND")
        if str(row[0]) not in {"ACTIVE", "STOPPED"}:
            raise PersonalAIError("CHANGE_NOT_REVIEWABLE")
        if not self._derivation_eligible(str(row[1])):
            raise PersonalAIError("CHANGE_LINEAGE_NOT_ELIGIBLE")
        session = self.start(f"REVIEW_CHANGE {plan_id}")
        with self._reflection.connection:
            self._reflection.connection.execute(
                "INSERT INTO change_review_sessions VALUES(?,?)",
                (session["interview_session_id"], plan_id),
            )
        return self.get(session["interview_session_id"])

    def change_control(self, plan_id: Any, action: Any) -> dict[str, Any]:
        plan_id, action = _text(plan_id, 64), _text(action, 16)
        if action not in {"ACTIVATE", "DISMISS", "STOP"}: raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        c, now = self._reflection.connection, _now()
        with c:
            row = c.execute("SELECT kind,state FROM change_plans WHERE plan_id=?", (plan_id,)).fetchone()
            if row is None: raise PersonalAIError("CHANGE_NOT_FOUND")
            kind, state = str(row[0]), str(row[1])
            if action == "ACTIVATE":
                if state != "PROPOSED": raise PersonalAIError("CHANGE_NOT_ACTIVATABLE")
                if kind == "EXPERIMENT" and c.execute("SELECT 1 FROM change_plans WHERE kind='EXPERIMENT' AND state='ACTIVE'").fetchone(): raise PersonalAIError("ACTIVE_EXPERIMENT_EXISTS")
                if kind == "OBSERVE" and c.execute("SELECT count(*) FROM change_plans WHERE kind='OBSERVE' AND state='ACTIVE'").fetchone()[0] >= 2: raise PersonalAIError("ACTIVE_OBSERVE_LIMIT")
                c.execute("UPDATE change_plans SET state='ACTIVE',activated_at=? WHERE plan_id=?", (now, plan_id))
            elif action == "DISMISS" and state == "PROPOSED": c.execute("UPDATE change_plans SET state='DISMISSED',ended_at=? WHERE plan_id=?", (now, plan_id))
            elif action == "STOP" and state == "ACTIVE": c.execute("UPDATE change_plans SET state='STOPPED',ended_at=? WHERE plan_id=?", (now, plan_id))
            else: raise PersonalAIError("CHANGE_NOT_ACTIONABLE")
        return self.changes()

    def observe_change(self, plan_id: Any, content: Any, signal: Any = None) -> dict[str, Any]:
        plan_id, content = _text(plan_id, 64), _text(content, 12000)
        if signal is not None and signal not in CHANGE_SIGNALS: raise PersonalAIError("INVALID_INTERVIEW_PAYLOAD")
        c, now = self._reflection.connection, _now()
        with c:
            if c.execute("SELECT 1 FROM change_plans WHERE plan_id=? AND state='ACTIVE'", (plan_id,)).fetchone() is None: raise PersonalAIError("CHANGE_NOT_ACTIVE")
            session = self._reflection.create_session("Наблюдения изменений")
            turn_id = generate_id()
            c.execute("INSERT INTO reflection_turns VALUES(?,?,?,?,?,?)", (turn_id, session["session_id"], 1, "USER", now, content))
            c.execute("UPDATE reflection_sessions SET turn_count=1,updated_at=? WHERE session_id=?", (now, session["session_id"]))
            c.execute("INSERT INTO change_observations VALUES(?,?,?,?,?)", (generate_id(), plan_id, turn_id, signal, now))
        return {"turn_id": turn_id, "plan_id": plan_id, "source": "USER"}

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
            "SELECT attempt_id,state,answer_turn_id,created_at,error_code FROM interview_attempts WHERE interview_session_id=? ORDER BY created_at DESC,rowid DESC",
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
        result["session_trail"] = self._session_trail(session_id)
        result["derived_items"] = self._derived_items(session_id)
        return result

    def _session_trail(self, session_id: str) -> list[dict[str, str]]:
        """Small local-only trail: questions remain derived, answers remain sources."""
        rows = self._reflection.connection.execute(
            "SELECT 'PSYCHE' AS actor,q.question,q.created_at FROM interview_questions q WHERE q.interview_session_id=? "
            "UNION ALL "
            "SELECT 'YOU' AS actor,t.content,t.created_at FROM interview_submissions s JOIN reflection_turns t ON t.turn_id=s.turn_id WHERE s.interview_session_id=? "
            "ORDER BY created_at DESC LIMIT 8",
            (session_id, session_id),
        ).fetchall()
        return [
            {"actor": str(actor), "text": str(text), "created_at": str(created_at)}
            for actor, text, created_at in reversed(rows)
        ]

    def _derived_items(self, session_id: str) -> list[dict[str, Any]]:
        rows = self._reflection.connection.execute(
            "SELECT item_id,kind,text,priority,created_at,derivation_id FROM interview_inquiry_items "
            "WHERE interview_session_id=? AND state='ACTIVE' ORDER BY priority DESC,created_at DESC,item_id ASC LIMIT 8",
            (session_id,),
        ).fetchall()
        return [
            {"item_id": str(item_id), "kind": str(kind), "text": str(text), "priority": int(priority), "created_at": str(created_at)}
            for item_id, kind, text, priority, created_at, derivation_id in rows
            if self._derivation_eligible(str(derivation_id))
        ]

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

    def _model_context(self, sources: tuple[dict[str, Any], ...]) -> tuple[dict[str, Any], ...]:
        """Bounded, eligibility-filtered Personal Model context for one packet.

        Local planner only: the provider still receives an exact closed packet.
        Contested (owner-challenged) items are never transmitted; they stay
        locally useful without presenting challenged AI text as current truth.
        """
        alias_by_turn = {item["turn_id"]: item["alias"] for item in sources}
        rows = self._reflection.connection.execute(
            "SELECT i.item_id,i.state,i.updated_at,r.revision_id,r.kind,r.text,r.temporal_scope,r.uncertainty,r.derivation_id "
            "FROM personal_model_items i JOIN personal_model_revisions r ON r.item_id=i.item_id AND r.status='CURRENT' "
            "WHERE i.state IN ('ACTIVE','CONTESTED') "
            "ORDER BY CASE r.kind WHEN 'CONTRADICTION' THEN 0 WHEN 'HYPOTHESIS' THEN 1 WHEN 'PATTERN' THEN 2 ELSE 3 END,"
            "i.updated_at DESC,i.item_id ASC"
        ).fetchall()
        entries: list[dict[str, Any]] = []
        chars = 0
        for item_id, state, _updated_at, revision_id, kind, text, scope, uncertainty, derivation_id in rows:
            if len(entries) == MAX_MODEL_ITEMS:
                break
            if chars + len(text) > MAX_MODEL_CHARS:
                continue
            if not derivation_id or not self._derivation_eligible(str(derivation_id)):
                continue
            # Effective state: an owner challenge overlays the base AI
            # lifecycle state.  A challenged item may be investigated, but
            # only when the full reconstructive owner-correction lineage is
            # itself eligible; it is always transmitted explicitly as
            # CONTESTED, never as unqualified current truth.
            challenge_turns = self._reflection.connection.execute(
                "SELECT turn_id FROM personal_model_challenges WHERE item_id=?",
                (item_id,),
            ).fetchall()
            if challenge_turns and any(
                self._policy_for_turn(str(row[0])) is None for row in challenge_turns
            ):
                continue
            effective_state = "CONTESTED" if challenge_turns else str(state)
            supporting: list[str] = []
            counterevidence: list[str] = []
            for turn_id, role in self._reflection.connection.execute(
                "SELECT turn_id,role FROM personal_model_revision_sources WHERE revision_id=? ORDER BY turn_id",
                (revision_id,),
            ):
                alias = alias_by_turn.get(str(turn_id))
                if alias:
                    (supporting if role == "SUPPORT" else counterevidence).append(alias)
            entry = {
                "alias": f"M{len(entries) + 1}",
                "item_id": str(item_id),
                "revision_id": str(revision_id),
                "state": effective_state,
                "kind": str(kind),
                "text": str(text),
                "temporal_scope": str(scope),
                "uncertainty": uncertainty,
                "supporting": supporting,
                "counterevidence": counterevidence,
                "char_count": len(text),
            }
            entries.append(entry)
            chars += len(text)
        return tuple(entries)

    def _change_context(self, session_id: str) -> tuple[dict[str, Any], ...]:
        """Only current, lineage-eligible derived plans can enter a packet."""
        if self._reflection.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='change_review_sessions'"
        ).fetchone() is None:
            # Only retained legacy test/package shapes reach this branch;
            # current runtime initialization always migrates to V14.
            return ()
        review = self._reflection.connection.execute(
            "SELECT plan_id FROM change_review_sessions WHERE interview_session_id=?", (session_id,)
        ).fetchone()
        requested = str(review[0]) if review else None
        rows = self._reflection.connection.execute(
            "SELECT plan_id,derivation_id,kind,state,title,instructions,expected_signal,counter_signal,duration_days,activated_at FROM change_plans WHERE state IN ('ACTIVE','STOPPED') ORDER BY activated_at DESC,created_at DESC,plan_id ASC"
        ).fetchall()
        entries: list[dict[str, Any]] = []
        chars = 0
        for plan_id, derivation_id, kind, state, title, instructions, expected, counter, duration, activated in rows:
            if requested and str(plan_id) != requested:
                continue
            if not self._derivation_eligible(str(derivation_id)):
                continue
            text_size = sum(len(str(value or "")) for value in (title, instructions, expected, counter))
            if len(entries) == MAX_CHANGE_ITEMS or chars + text_size > MAX_CHANGE_CHARS:
                continue
            entries.append({
                "alias": f"C{len(entries) + 1}", "plan_id": str(plan_id), "derivation_id": str(derivation_id),
                "kind": str(kind), "state": str(state), "title": str(title), "instructions": str(instructions),
                "expected_signal": str(expected), "counter_signal": str(counter), "duration_days": duration,
                "activated_at": activated, "char_count": text_size,
                "review_target": str(plan_id) == requested,
            })
            chars += text_size
        if requested and not entries:
            raise PersonalAIError("CHANGE_LINEAGE_NOT_ELIGIBLE")
        return tuple(entries)

    def _select(
        self, session_id: str
    ) -> tuple[
        tuple[dict[str, Any], ...],
        tuple[dict[str, Any], ...],
        tuple[dict[str, Any], ...],
        tuple[dict[str, Any], ...],
        tuple[dict[str, Any], ...],
    ]:
        rows = self._reflection.connection.execute(
            "SELECT turn_id,content,created_at FROM (SELECT t.turn_id,t.content,t.created_at FROM interview_sessions i JOIN reflection_turns t ON t.session_id=i.source_session_id WHERE i.interview_session_id=? UNION ALL SELECT t.turn_id,t.content,t.created_at FROM reflection_turns t WHERE t.actor='USER' AND t.session_id NOT IN (SELECT source_session_id FROM interview_sessions WHERE interview_session_id=?)) ORDER BY created_at DESC,turn_id DESC",
            (session_id, session_id),
        ).fetchall()
        review_plan = None if self._reflection.connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='change_review_sessions'"
        ).fetchone() is None else self._reflection.connection.execute(
            "SELECT plan_id FROM change_review_sessions WHERE interview_session_id=?", (session_id,)
        ).fetchone()
        if review_plan is not None:
            observation_rows = self._reflection.connection.execute(
                "SELECT t.turn_id,t.content,t.created_at FROM change_observations o JOIN reflection_turns t ON t.turn_id=o.turn_id WHERE o.plan_id=? ORDER BY o.created_at DESC,o.observation_id DESC",
                (str(review_plan[0]),),
            ).fetchall()
            observation_ids = {str(row[0]) for row in observation_rows}
            rows = [*observation_rows, *(row for row in rows if str(row[0]) not in observation_ids)]
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
        if not sources:
            planning.append({"kind": "ONBOARDING", "text": "Little eligible history is available; begin with one meaningful current issue, transition, pattern, value tension, or concrete life domain."})
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
        model = list(self._model_context(sources))
        total += sum(x["char_count"] for x in model)
        # Model-derived text consumes the same bounded context budget; trim it
        # first, then planning, then inquiry, then sources.
        for group, key in ((model, "char_count"), (planning, "text"), (inquiry, "char_count"), (sources, "char_count")):
            while total > MAX_CONTEXT_CHARS and group:
                total -= len(group[-1][key]) if key == "text" else group[-1][key]
                group.pop()
        changes = list(self._change_context(session_id))
        total += sum(item["char_count"] for item in changes)
        while total > MAX_CONTEXT_CHARS and changes:
            total -= changes[-1]["char_count"]
            changes.pop()
        return tuple(sources), tuple(inquiry), tuple(planning), tuple(model), tuple(changes)

    def _perform(self, session_id: str, answer_turn_id: str | None) -> dict[str, Any]:
        self._require_consent(session_id)
        if not self._exists(session_id):
            raise PersonalAIError("INTERVIEW_NOT_FOUND")
        sources, inquiry, planning, model, changes = self._select(session_id)
        source_chars = sum(x["char_count"] for x in sources)
        inquiry_chars = sum(x["char_count"] for x in inquiry)
        model_chars = sum(x["char_count"] for x in model)
        change_chars = sum(x["char_count"] for x in changes)
        context_chars = source_chars + inquiry_chars + model_chars + change_chars + sum(len(x["text"]) for x in planning)
        attempt_id, now, c = generate_id(), _now(), self._reflection.connection
        with c:
            c.execute(
                "INSERT INTO interview_attempts(attempt_id,interview_session_id,answer_turn_id,purpose,provider_profile,model,config_id,schema_id,state,policy_enabled,source_item_count,source_char_count,inquiry_item_count,inquiry_char_count,context_char_count,model_item_count,model_char_count,created_at,sent_at,completed_at,error_code) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
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
                    len(model),
                    model_chars,
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
            for ordinal, item in enumerate(model, 1):
                c.execute(
                    "INSERT INTO interview_attempt_model_items VALUES(?,?,?,?,?,?,?)",
                    (attempt_id, item["alias"], item["item_id"], item["revision_id"], item["state"], ordinal, item["char_count"]),
                )
            for ordinal, item in enumerate(changes, 1):
                c.execute(
                    "INSERT INTO interview_attempt_change_items VALUES(?,?,?,?,?,?)",
                    (attempt_id, item["alias"], item["plan_id"], item["state"], ordinal, item["char_count"]),
                )
        manifest = {
            "attempt_id": attempt_id,
            "purpose": PURPOSE,
            "profile_id": PROFILE_ID,
            "model": MODEL,
            "config_id": CONFIG_ID,
            "schema_id": SCHEMA_ID,
            "source_aliases": [x["alias"] for x in sources],
            "model_aliases": [x["alias"] for x in model],
            "change_aliases": [x["alias"] for x in changes],
            "max_source_items": MAX_SOURCE_ITEMS,
            "max_source_chars": MAX_SOURCE_CHARS,
            "max_model_items": MAX_MODEL_ITEMS,
            "max_model_chars": MAX_MODEL_CHARS,
            "max_context_chars": MAX_CONTEXT_CHARS,
        }
        packet = {"sources": sources, "inquiry": inquiry, "planning": planning, "model": model, "changes": changes}
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
            parsed = validate_interview_output(
                raw,
                {x["alias"] for x in sources},
                frozenset(x["alias"] for x in model),
                frozenset(x["alias"] for x in changes),
            )
        except PersonalAIError as exc:
            with c:
                c.execute(
                    "UPDATE interview_attempts SET state='FAILED',completed_at=?,error_code=? WHERE attempt_id=?",
                    (_now(), exc.code, attempt_id),
                )
            raise
        self._commit(session_id, attempt_id, sources, model, changes, answer_turn_id, parsed, actual_model)
        return self.get(session_id)

    def _commit(
        self,
        session_id: str,
        attempt_id: str,
        sources: tuple[dict[str, Any], ...],
        model: tuple[dict[str, Any], ...],
        changes: tuple[dict[str, Any], ...],
        answer_turn_id: str | None,
        value: dict[str, Any],
        actual_model: str,
    ) -> None:
        now, c, derivation_id = _now(), self._reflection.connection, generate_id()
        by_alias = {x["alias"]: x for x in sources}
        model_by_alias = {x["alias"]: x for x in model}
        change_by_alias = {x["alias"]: x for x in changes}
        with c:
            c.execute(
                "UPDATE interview_attempts SET state='SUCCEEDED',completed_at=?,model=? WHERE attempt_id=?",
                (now, actual_model, attempt_id),
            )
            c.execute(
                "INSERT INTO interview_derivations VALUES(?,?,?,?)",
                (derivation_id, attempt_id, "VALIDATED", now),
            )
            # Materialize the complete reconstructive SOURCE lineage: the raw
            # transmitted manifest plus every USER source behind transmitted
            # model revisions, so deletion/privacy closure stays transitive
            # even when an ancestral source fell outside the current raw
            # top-N packet.  The manifest keeps meaning exactly what was
            # transmitted; this table means what the derived meaning needs.
            lineage: dict[str, str] = {}
            for item in sources:
                lineage[str(item["turn_id"])] = str(item["alias"])
            for entry in model:
                rows = c.execute(
                    "SELECT d.turn_id,d.alias FROM personal_model_revisions r "
                    "JOIN interview_derivation_sources d ON d.derivation_id=r.derivation_id "
                    "WHERE r.revision_id=? "
                    "UNION "
                    "SELECT s.turn_id,s.alias FROM personal_model_revisions r "
                    "JOIN personal_model_revision_sources s ON s.revision_id=r.revision_id "
                    "WHERE r.revision_id=? "
                    "ORDER BY 1",
                    (entry["revision_id"], entry["revision_id"]),
                ).fetchall()
                for turn_id, _alias in rows:
                    lineage.setdefault(str(turn_id), "INHERITED")
                # The transmitted state of a challenged item depends on the
                # owner-correction SOURCE; its turns join the reconstructive
                # lineage so downstream meaning cannot outlive the correction.
                for (challenge_turn,) in c.execute(
                    "SELECT turn_id FROM personal_model_challenges WHERE item_id=? ORDER BY turn_id",
                    (entry["item_id"],),
                ).fetchall():
                    lineage.setdefault(str(challenge_turn), "INHERITED")
            for entry in changes:
                for turn_id, _alias in c.execute(
                    "SELECT turn_id,alias FROM interview_derivation_sources WHERE derivation_id=? ORDER BY turn_id",
                    (entry["derivation_id"],),
                ).fetchall():
                    lineage.setdefault(str(turn_id), "INHERITED")
            for turn_id, alias in lineage.items():
                c.execute(
                    "INSERT INTO interview_derivation_sources VALUES(?,?,?)",
                    (derivation_id, turn_id, alias),
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
            active_items = {
                (str(kind), _canonical_inquiry_text(str(text)))
                for kind, text in c.execute(
                    "SELECT kind,text FROM interview_inquiry_items WHERE state='ACTIVE'"
                )
            }
            for item in value["inquiry_items"]:
                # Conservative deterministic hygiene: only exact normalized duplicates
                # are suppressed. Ambiguous similarities remain distinct evidence.
                if (item["kind"], _canonical_inquiry_text(item["text"])) in active_items:
                    continue
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
                active_items.add((item["kind"], _canonical_inquiry_text(item["text"])))
            self._apply_model_delta(c, value["model_delta"], model_by_alias, by_alias, derivation_id, now)
            change = value.get("change_delta")
            if change is not None:
                if change["action"] == "PROPOSE":
                    active_count = c.execute(
                        "SELECT count(*) FROM change_plans WHERE kind=? AND state='ACTIVE'", (change["kind"],)
                    ).fetchone()[0]
                    if (change["kind"] == "EXPERIMENT" and active_count) or (change["kind"] == "OBSERVE" and active_count >= 2):
                        raise PersonalAIError("ACTIVE_CHANGE_LIMIT")
                    duplicate = c.execute(
                        "SELECT 1 FROM change_plans WHERE kind=? AND lower(trim(title))=lower(trim(?)) AND state IN ('PROPOSED','ACTIVE')",
                        (change["kind"], change["title"]),
                    ).fetchone()
                    if duplicate:
                        raise PersonalAIError("DUPLICATE_CHANGE_PLAN")
                    plan_id = generate_id()
                    c.execute("INSERT INTO change_plans VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (plan_id, derivation_id, change["kind"], "PROPOSED", change["title"], change["reason"], change["instructions"], change["observation_prompt"], change["expected_signal"], change["counter_signal"], change["duration_days"], change["stop_conditions"], "LOW", 1, 1, now, None, None))
                    for alias in change["target_model_aliases"]:
                        target = model_by_alias[alias]
                        c.execute("INSERT INTO change_plan_targets VALUES(?,?,?)", (plan_id, target["item_id"], target["revision_id"]))
                else:
                    plan = change_by_alias[change["target_change_alias"]]
                    if not plan["review_target"] or plan["state"] not in {"ACTIVE", "STOPPED"}:
                        raise PersonalAIError("CHANGE_REVIEW_NOT_AUTHORIZED")
                    c.execute(
                        "INSERT INTO change_reviews VALUES(?,?,?,?,?,?,?,?,?)",
                        (generate_id(), plan["plan_id"], derivation_id, change["practical_effect"], change["epistemic_outcome"], change["summary"], change["what_changed_in_understanding"], change["recommended_next"], now),
                    )
                    if change["recommended_next"] == "COMPLETE" and plan["state"] == "ACTIVE":
                        c.execute("UPDATE change_plans SET state='COMPLETED',ended_at=? WHERE plan_id=?", (now, plan["plan_id"]))
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

    def _apply_model_delta(
        self,
        c: Any,
        deltas: Sequence[dict[str, Any]],
        model_by_alias: dict[str, dict[str, Any]],
        by_alias: dict[str, dict[str, Any]],
        derivation_id: str,
        now: str,
    ) -> None:
        """Apply the validated model delta inside the caller's transaction."""
        attached: set[tuple[str, str, str]] = set()
        for delta in deltas:
            kind, text = delta["kind"], delta["text"]
            if delta["action"] == "CREATE":
                item_id, revision_id = generate_id(), generate_id()
                c.execute(
                    "INSERT INTO personal_model_items VALUES(?,?,?,?,?)",
                    (item_id, kind, "ACTIVE", now, now),
                )
                c.execute(
                    "INSERT INTO personal_model_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (revision_id, item_id, 1, kind, text, delta["temporal_scope"], delta["uncertainty"], delta["reason"], derivation_id, None, "CURRENT", now),
                )
            else:
                target = model_by_alias[delta["target"]]
                item_id, current_revision_id = target["item_id"], target["revision_id"]
                if delta["action"] == "REVISE":
                    ordinal = c.execute(
                        "SELECT max(ordinal) FROM personal_model_revisions WHERE item_id=?",
                        (item_id,),
                    ).fetchone()[0] + 1
                    revision_id = generate_id()
                    c.execute(
                        "UPDATE personal_model_revisions SET status='SUPERSEDED' WHERE revision_id=? AND status='CURRENT'",
                        (current_revision_id,),
                    )
                    c.execute(
                        "INSERT INTO personal_model_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                        (revision_id, item_id, ordinal, kind, text, delta["temporal_scope"], delta["uncertainty"], delta["reason"], derivation_id, None, "CURRENT", now),
                    )
                    c.execute(
                        "UPDATE personal_model_items SET kind=?,updated_at=? WHERE item_id=?",
                        (kind, now, item_id),
                    )
                elif delta["action"] == "CONTEST":
                    # Revisions are immutable: a contest never mutates the
                    # existing evidence set; it always creates a successor
                    # revision and supersedes the previous one.
                    ordinal = c.execute(
                        "SELECT max(ordinal) FROM personal_model_revisions WHERE item_id=?",
                        (item_id,),
                    ).fetchone()[0] + 1
                    revision_id = generate_id()
                    c.execute(
                        "UPDATE personal_model_revisions SET status='SUPERSEDED' WHERE revision_id=? AND status='CURRENT'",
                        (current_revision_id,),
                    )
                    if text is None:
                        # Unresolved challenge: carry the prior meaning forward
                        # unchanged with its full evidence set, add the newly
                        # supplied counterevidence, and mark the item contested.
                        prior = c.execute(
                            "SELECT kind,text,temporal_scope,uncertainty FROM personal_model_revisions WHERE revision_id=?",
                            (current_revision_id,),
                        ).fetchone()
                        kind, text = str(prior[0]), str(prior[1])
                        c.execute(
                            "INSERT INTO personal_model_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (revision_id, item_id, ordinal, kind, text, str(prior[2]), prior[3], delta["reason"], derivation_id, None, "CURRENT", now),
                        )
                        for turn_id, alias, role in c.execute(
                            "SELECT turn_id,alias,role FROM personal_model_revision_sources WHERE revision_id=? ORDER BY turn_id,role",
                            (current_revision_id,),
                        ).fetchall():
                            attached.add((revision_id, str(turn_id), str(role)))
                            c.execute(
                                "INSERT INTO personal_model_revision_sources VALUES(?,?,?,?)",
                                (revision_id, turn_id, alias, role),
                            )
                        c.execute(
                            "UPDATE personal_model_items SET state='CONTESTED',updated_at=? WHERE item_id=?",
                            (now, item_id),
                        )
                    else:
                        # Narrowed replacement: validation required explicit
                        # valid SUPPORT; the item becomes investigable again.
                        c.execute(
                            "INSERT INTO personal_model_revisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                            (revision_id, item_id, ordinal, kind, text, delta["temporal_scope"], delta["uncertainty"], delta["reason"], derivation_id, None, "CURRENT", now),
                        )
                        c.execute(
                            "UPDATE personal_model_items SET kind=?,state='ACTIVE',updated_at=? WHERE item_id=?",
                            (kind, now, item_id),
                        )
                else:  # RESOLVE
                    revision_id = current_revision_id
                    c.execute(
                        "UPDATE personal_model_items SET state='RESOLVED',updated_at=? WHERE item_id=?",
                        (now, item_id),
                    )
            if delta["action"] != "RESOLVE":
                for role, key in (("SUPPORT", "supporting"), ("COUNTEREVIDENCE", "counterevidence")):
                    for alias in delta[key]:
                        turn_id = str(by_alias[alias]["turn_id"])
                        if (revision_id, turn_id, role) in attached:
                            continue
                        attached.add((revision_id, turn_id, role))
                        c.execute(
                            "INSERT INTO personal_model_revision_sources VALUES(?,?,?,?)",
                            (revision_id, turn_id, alias, role),
                        )


def validate_model_delta(raw: Any, aliases: set[str], model_aliases: set[str]) -> list[dict[str, Any]]:
    """Strict deterministic validation of the small declarative model delta."""
    if not isinstance(raw, list) or len(raw) > MAX_MODEL_DELTA:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    deltas, seen_targets, seen_creates = [], set(), set()
    for entry in raw:
        if not isinstance(entry, dict) or set(entry) != {
            "action",
            "target",
            "kind",
            "text",
            "temporal_scope",
            "uncertainty",
            "supporting",
            "counterevidence",
            "reason",
        }:
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        action, target = entry["action"], entry["target"]
        if action not in DELTA_ACTIONS or not isinstance(target, str):
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        if action == "CREATE":
            if target != "":
                raise PersonalAIError("AI_OUTPUT_REJECTED")
        elif not target or target not in model_aliases or target in seen_targets:
            # Hallucinated model alias, or a second conflicting delta against
            # the same target in one response, is rejected outright.
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        seen_targets.add(target)
        kind = entry["kind"]
        if kind not in MODEL_KINDS:
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        if entry["temporal_scope"] not in TEMPORAL_SCOPES:
            raise PersonalAIError("AI_OUTPUT_REJECTED")
        for key in ("supporting", "counterevidence"):
            value = entry[key]
            if (
                not isinstance(value, list)
                or len(set(value)) != len(value)
                or not all(isinstance(a, str) and a in aliases for a in value)
            ):
                raise PersonalAIError("AI_OUTPUT_REJECTED")
        supporting, counterevidence = entry["supporting"], entry["counterevidence"]
        reason = _safe(_text(entry["reason"], 240))
        uncertainty = entry["uncertainty"]
        uncertainty = None if uncertainty in ("", None) else _safe(_text(uncertainty, 160))
        if action in {"CREATE", "REVISE"}:
            text = _working_language(_safe(_text(entry["text"], MAX_QUESTION)))
            if not supporting:
                # No model item may exist without a valid SOURCE basis.
                raise PersonalAIError("AI_OUTPUT_REJECTED")
            if kind == "PATTERN" and len(supporting) < 2:
                # Conservative validation: a single ordinary source cannot
                # justify a stable pattern; the provider must use HYPOTHESIS.
                raise PersonalAIError("AI_OUTPUT_REJECTED")
            if action == "CREATE":
                create_key = (kind, _canonical_inquiry_text(text))
                if create_key in seen_creates:
                    raise PersonalAIError("AI_OUTPUT_REJECTED")
                seen_creates.add(create_key)
        else:
            text = entry["text"]
            if text in ("", None):
                text = None
            else:
                text = _working_language(_safe(_text(text, MAX_QUESTION)))
            if action == "CONTEST":
                if text is None:
                    # Unresolved challenge carries the prior evidence set;
                    # re-specifying support would mutate immutable history.
                    if supporting:
                        raise PersonalAIError("AI_OUTPUT_REJECTED")
                elif not supporting:
                    # A narrowed replacement must be evidence-backed; it may
                    # never create unsupported current meaning.
                    raise PersonalAIError("AI_OUTPUT_REJECTED")
            if action == "CONTEST" and not counterevidence and not reason:
                raise PersonalAIError("AI_OUTPUT_REJECTED")
        deltas.append(
            {
                "action": action,
                "target": target or None,
                "kind": kind,
                "text": text,
                "temporal_scope": entry["temporal_scope"],
                "uncertainty": uncertainty,
                "supporting": list(supporting),
                "counterevidence": list(counterevidence),
                "reason": reason,
            }
        )
    return deltas


def validate_change_delta(raw: Any, model_aliases: set[str], change_aliases: set[str] = set()) -> dict[str, Any] | None:
    if raw is None: return None
    if not isinstance(raw, dict): raise PersonalAIError("AI_OUTPUT_REJECTED")
    if raw.get("action") == "PROPOSE":
        keys = {"action","kind","target_model_aliases","title","reason","instructions","observation_prompt","expected_signal","counter_signal","duration_days","stop_conditions","risk_level","reversible","self_directed"}
        if raw.get("kind") not in CHANGE_KINDS or set(raw) != keys or not isinstance(raw["target_model_aliases"], list) or not raw["target_model_aliases"] or len(raw["target_model_aliases"]) > 3 or len(set(raw["target_model_aliases"])) != len(raw["target_model_aliases"]) or not all(x in model_aliases for x in raw["target_model_aliases"]): raise PersonalAIError("AI_OUTPUT_REJECTED")
        if raw["risk_level"] != "LOW" or raw["reversible"] is not True or raw["self_directed"] is not True: raise PersonalAIError("AI_OUTPUT_REJECTED")
        duration = raw["duration_days"]
        if duration is not None and (not isinstance(duration, int) or not 1 <= duration <= 31): raise PersonalAIError("AI_OUTPUT_REJECTED")
        result = {key: raw[key] for key in keys}
        for key, limit in (("title",160),("reason",480),("instructions",1200),("observation_prompt",480),("expected_signal",480),("counter_signal",480),("stop_conditions",480)):
            result[key] = _safe_change(_text(raw[key], limit))
        return result
    keys = {"action", "target_change_alias", "practical_effect", "epistemic_outcome", "summary", "what_changed_in_understanding", "recommended_next"}
    if raw.get("action") != "REVIEW" or set(raw) != keys or raw["target_change_alias"] not in change_aliases or raw["practical_effect"] not in PRACTICAL_EFFECTS or raw["epistemic_outcome"] not in EPISTEMIC_OUTCOMES or raw["recommended_next"] not in RECOMMENDED_NEXT:
        raise PersonalAIError("AI_OUTPUT_REJECTED")
    return {
        "action": "REVIEW", "target_change_alias": raw["target_change_alias"],
        "practical_effect": raw["practical_effect"], "epistemic_outcome": raw["epistemic_outcome"], "recommended_next": raw["recommended_next"],
        "summary": _safe(_text(raw["summary"], 480)),
        "what_changed_in_understanding": _safe(_text(raw["what_changed_in_understanding"], 480)),
    }


def validate_interview_output(
    raw: Any, aliases: set[str], model_aliases: frozenset[str] = frozenset(), change_aliases: frozenset[str] = frozenset()
) -> dict[str, Any]:
    required = {
        "schema_version",
        "decision",
        "question",
        "rationale",
        "basis_aliases",
        "summary",
        "next_direction",
        "inquiry_items",
        "model_delta", "change_delta",
    }
    legacy = isinstance(raw, dict) and set(raw) == required - {"change_delta"} and raw.get("schema_version") == "personal-ai-interview-output-v2"
    if not isinstance(raw, dict) or (set(raw) != required and not legacy) or raw.get("schema_version") not in {SCHEMA_ID, "personal-ai-interview-output-v2"}:
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
        "model_delta": validate_model_delta(raw["model_delta"], aliases, set(model_aliases)),
        "change_delta": None if legacy else validate_change_delta(raw["change_delta"], set(model_aliases), set(change_aliases)),
    }
