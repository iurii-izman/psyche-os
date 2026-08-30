"""Exact local-only Personal desktop command boundary.

This module intentionally does not import the Synthetic desktop service or any
provider, archive, action, longitudinal, importer, telemetry, or network
module.  It is the only dispatcher used by the Personal profile sidecar.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import os
from pathlib import Path
import secrets
from typing import Any, Final

from psyche_os.adapters.e07_provider import OpenAIReflectionProvider
from psyche_os.application.guided_exploration import GuidedExplorationService
from psyche_os.application.reflection_sessions import ReflectionSessionError
from psyche_os.personal_mode.admission import (
    AdmissionDecision,
    PersonalAdmissionGuard,
    PersonalNotAdmittedError,
)
from psyche_os.personal_mode.ai_interview import PROFILE_ID as INTERVIEW_PROFILE_ID
from psyche_os.personal_mode.ai_interview import PersonalAIInterviewService
from psyche_os.personal_mode.ai_working_formulation import (
    OpenAIKeyStore,
    PersonalAIError,
    PersonalWorkingFormulationService,
)
from psyche_os.personal_mode.context_retrieval import PersonalContextRetrievalService
from psyche_os.personal_mode.external_evidence import (
    SOURCE_ID,
    ExternalEvidenceError,
    ExternalEvidenceService,
)
from psyche_os.personal_mode.lifecycle import PersonalLifecycleError
from psyche_os.personal_mode.runtime import PersonalRuntime, PersonalRuntimeError
from psyche_os.personal_mode.runtime_profile import PersonalRuntimePaths

PROTOCOL_VERSION: Final = "1.0"
MAX_SECRET: Final = 256
AI_PROFILE_ID: Final = "local_personal_bounded_openai_reflection_windows_v1"

PERSONAL_ALLOWED_COMMANDS: Final = frozenset(
    {
        "status.get",
        "session.unlock",
        "session.lock",
        "reflection_session.create",
        "reflection_session.list",
        "reflection_session.get",
        "reflection_session.add_turn",
        "reflection_session.close",
        "reflection_session.delete",
        "reflection.search",
        "reflection_exploration.start",
        "reflection_exploration.get",
        "reflection_exploration.answer",
        "reflection_exploration.skip",
        "reflection_exploration.formulation.propose",
        "reflection_exploration.formulation.correct",
        "reflection_exploration.formulation.accept",
        "reflection_exploration.formulation.reject",
        "backup.create",
        "recovery.restore_isolated",
        "recovery.status",
        "export.owner",
        "rotation.rotate",
        "ai.provider.status",
        "ai.provider.configure",
        "ai.provider.delete",
        "ai.working_formulation.prepare",
        "ai.working_formulation.authorize_execute",
        "ai.interview.status",
        "ai.interview.policy",
        "ai.interview.source_policy",
        "ai.interview.start",
        "ai.interview.list",
        "ai.interview.grant_consent",
        "ai.interview.revoke_consent",
        "ai.interview.first_question",
        "ai.interview.submit",
        "ai.interview.retry",
        "ai.interview.control",
        "ai.interview.get",
        "ai.interview.disclosure",
        "ai.model.list",
        "ai.model.correct",
        "external.source.status",
        "external.source.configure",
        "external.scan",
        "sleep.history",
        "sleep.delete_record",
    }
)

PERSONAL_SESSION_COMMANDS: Final = PERSONAL_ALLOWED_COMMANDS - {
    "status.get",
    "session.unlock",
    "session.lock",
    "recovery.status",
}


class PersonalDesktopServiceError(Exception):
    """Stable, content-free error for the renderer-facing Personal boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _exact(payload: Any, keys: set[str]) -> dict[str, Any]:
    if not isinstance(payload, dict) or set(payload) != keys:
        raise PersonalDesktopServiceError("INVALID_PAYLOAD")
    return payload


def _secret(payload: Any) -> str:
    secret = _exact(payload, {"secret"})["secret"]
    if not isinstance(secret, str) or not secret or len(secret) > MAX_SECRET:
        raise PersonalDesktopServiceError("INVALID_PAYLOAD")
    return secret


class PersonalDesktopApplicationService:
    """Trusted composition for only the accepted Personal v1 capabilities."""

    def __init__(
        self,
        paths: PersonalRuntimePaths,
        *,
        evaluator: Callable[[], AdmissionDecision] | None = None,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
        runtime_factory: Callable[[PersonalRuntimePaths, PersonalAdmissionGuard], PersonalRuntime]
        | None = None,
    ) -> None:
        self._guard = PersonalAdmissionGuard(evaluator, clock=clock)
        factory = runtime_factory or (lambda value, guard: PersonalRuntime(value, guard))
        self._runtime = factory(paths, self._guard)
        self._guard.bind_key_clearer(self._runtime._clear)
        self._session_token: str | None = None
        profile_id = os.environ.get("PSYCHE_OS_PERSONAL_PROFILE_ID")
        self._ai_enabled = profile_id == AI_PROFILE_ID
        self._interview_enabled = profile_id == INTERVIEW_PROFILE_ID
        self._ai: PersonalWorkingFormulationService | None = None
        self._interview: PersonalAIInterviewService | None = None

    def close(self) -> None:
        self._session_token = None
        if self._interview is not None:
            self._interview._consents.clear()
        self._runtime.lock()

    def dispatch(
        self, command: str, payload: dict[str, Any], session_token: str | None
    ) -> dict[str, Any]:
        if command not in PERSONAL_ALLOWED_COMMANDS:
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        if command.startswith("ai.working_formulation") and not self._ai_enabled:
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        if (
            command.startswith("ai.interview") or command.startswith("ai.model")
        ) and not self._interview_enabled:
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        try:
            if command in PERSONAL_SESSION_COMMANDS:
                self._require_session(session_token)
                # This explicit per-command check protects operations which use
                # shared deterministic exploration helpers over the raw DB.
                self._guard.require()
            handlers = {
                "status.get": self._status,
                "session.unlock": self._unlock,
                "session.lock": self._lock,
                "reflection_session.create": self._create_session,
                "reflection_session.list": self._list_sessions,
                "reflection_session.get": self._get_session,
                "reflection_session.add_turn": self._add_turn,
                "reflection_session.close": self._close_session,
                "reflection_session.delete": self._delete_session,
                "reflection.search": self._search,
                "reflection_exploration.start": self._exploration_start,
                "reflection_exploration.get": self._exploration_get,
                "reflection_exploration.answer": self._exploration_answer,
                "reflection_exploration.skip": self._exploration_skip,
                "reflection_exploration.formulation.propose": self._formulation_propose,
                "reflection_exploration.formulation.correct": self._formulation_correct,
                "reflection_exploration.formulation.accept": self._formulation_accept,
                "reflection_exploration.formulation.reject": self._formulation_reject,
                "backup.create": self._backup,
                "recovery.restore_isolated": self._restore_isolated,
                "recovery.status": self._recovery_status,
                "export.owner": self._export,
                "rotation.rotate": self._rotate,
                "ai.provider.status": self._ai_status,
                "ai.provider.configure": self._ai_configure,
                "ai.provider.delete": self._ai_delete,
                "ai.working_formulation.prepare": self._ai_prepare,
                "ai.working_formulation.authorize_execute": self._ai_authorize_execute,
                "ai.interview.status": self._interview_status,
                "ai.interview.policy": self._interview_policy,
                "ai.interview.source_policy": self._interview_source_policy,
                "ai.interview.external_policy": self._interview_external_policy,
                "ai.interview.start": self._interview_start,
                "ai.interview.list": self._interview_list,
                "ai.interview.grant_consent": self._interview_grant_consent,
                "ai.interview.revoke_consent": self._interview_revoke_consent,
                "ai.interview.first_question": self._interview_first_question,
                "ai.interview.submit": self._interview_submit,
                "ai.interview.retry": self._interview_retry,
                "ai.interview.control": self._interview_control,
                "ai.interview.get": self._interview_get,
                "ai.interview.disclosure": self._interview_disclosure,
                "ai.model.list": self._model_list,
                "ai.model.correct": self._model_correct,
                "external.source.status": self._external_source_status,
                "external.source.configure": self._external_source_configure,
                "external.scan": self._external_scan,
                "sleep.history": self._sleep_history,
                "sleep.delete_record": self._sleep_delete_record,
                "ai.change.list": self._change_list,
                "ai.change.control": self._change_control,
                "ai.change.observe": self._change_observe,
                "ai.change.allow_observations": self._change_allow_observations,
                "ai.change.start_review": self._change_start_review,
            }
            return handlers[command](payload)
        except PersonalNotAdmittedError as exc:
            self._session_token = None
            raise PersonalDesktopServiceError("NOT_ADMITTED") from exc
        except (PersonalRuntimeError, PersonalLifecycleError) as exc:
            raise PersonalDesktopServiceError("PERSONAL_OPERATION_FAILED") from exc
        except ReflectionSessionError as exc:
            raise PersonalDesktopServiceError(exc.code) from exc
        except PersonalAIError as exc:
            raise PersonalDesktopServiceError(exc.code) from exc
        except ExternalEvidenceError as exc:
            raise PersonalDesktopServiceError(str(exc)) from exc

    def _require_session(self, token: str | None) -> None:
        if (
            not isinstance(token, str)
            or self._session_token is None
            or not secrets.compare_digest(token, self._session_token)
        ):
            raise PersonalDesktopServiceError("SESSION_REQUIRED")

    def _status(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        admission = self._guard.status()
        return {
            "locked": self._guard.locked,
            "setup_required": not self._runtime._paths.envelope.exists(),
            "runtime_profile": "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI"
            if self._interview_enabled
            else "LOCAL_PERSONAL_BOUNDED_OPENAI"
            if self._ai_enabled
            else "LOCAL_PERSONAL",
            "local_personal": admission["local_personal"],
            "real_data_gate": "OPEN" if admission["local_personal"] != "NOT_ADMITTED" else "CLOSED",
            "admission_expires_at": admission.get("admission_expires_at"),
            "inbound_listener": "NONE",
            "outbound_provider": "OPENAI_EXPLICIT_OPT_IN"
            if (self._ai_enabled or self._interview_enabled)
            else "NOT_CONFIGURED",
            "network": "OPENAI_FOREGROUND_BOUNDED"
            if self._interview_enabled
            else "OPENAI_EXPLICIT_ONE_CALL_ONLY"
            if self._ai_enabled
            else "OFFLINE_NO_LISTENER",
            "privacy": {
                "core_processing_location": "LOCAL",
                "cloud_storage": "DISABLED",
                "cloud_disclosure": "EXPLICIT_SESSION_CONSENT_OPENAI_ONLY"
                if self._interview_enabled
                else "EXPLICIT_OPT_IN_OPENAI_ONLY"
                if self._ai_enabled
                else "NEVER_CLOUD",
                "telemetry": "OFF",
            },
        }

    def _unlock(self, payload: Any) -> dict[str, Any]:
        secret = _secret(payload)
        # Guard precedes the envelope/path existence probe and all byte access.
        self._guard.require()
        if self._runtime._paths.envelope.exists():
            self._runtime.unlock(secret)
        else:
            self._runtime.setup(secret)
        self._session_token = secrets.token_urlsafe(32)
        # The only automatic import is a single bounded scan after an owner
        # opens the local Personal store.  There is no listener, daemon, or
        # filesystem access exposed to the renderer.
        self._scan_configured_inbox()
        return {"session_token": self._session_token, "locked": False}

    def _ai_service(self) -> PersonalWorkingFormulationService:
        if not (self._ai_enabled or self._interview_enabled):
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        if self._ai is None:
            self._ai = PersonalWorkingFormulationService(
                self._runtime.reflection,
                OpenAIKeyStore(self._runtime._paths.root),
                OpenAIReflectionProvider(),
            )
        return self._ai

    def _ai_status(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return self._ai_service().status()

    def _ai_configure(self, payload: Any) -> dict[str, Any]:
        key = _exact(payload, {"api_key"})["api_key"]
        if not isinstance(key, str):
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        self._ai_service()._keys.configure(key)
        return {"configured": True}

    def _ai_delete(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        self._ai_service()._keys.delete()
        return {"configured": False}

    def _ai_prepare(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"session_id", "selected_turn_ids"})
        return self._ai_service().prepare(values["session_id"], values["selected_turn_ids"])

    def _ai_authorize_execute(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"interaction_id", "preview_id"})
        return self._ai_service().authorize_execute(values["interaction_id"], values["preview_id"])

    def _interview_service(self) -> PersonalAIInterviewService:
        if not self._interview_enabled:
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        if self._interview is None:
            self._interview = PersonalAIInterviewService(
                self._runtime.reflection,
                OpenAIKeyStore(self._runtime._paths.root),
                OpenAIReflectionProvider(),
            )
        return self._interview

    def _interview_status(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return self._interview_service().status()

    def _interview_policy(self, payload: Any) -> dict[str, Any]:
        return self._interview_service().set_policy(_exact(payload, {"enabled"})["enabled"])

    def _interview_source_policy(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"turn_ids", "enabled"})
        return self._interview_service().set_source_policy(values["turn_ids"], values["enabled"])

    def _interview_external_policy(self, payload: Any) -> dict[str, Any]:
        return self._interview_service().set_external_policy(_exact(payload, {"enabled"})["enabled"])

    def _interview_start(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"owner_topic"})
        return self._interview_service().start(values["owner_topic"])

    def _interview_list(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return self._interview_service().list()

    def _interview_grant_consent(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"interview_session_id", "include_sleep"})
        return self._interview_service().grant_consent(values["interview_session_id"], values["include_sleep"])

    def _interview_revoke_consent(self, payload: Any) -> dict[str, Any]:
        return self._interview_service().revoke(
            _exact(payload, {"interview_session_id"})["interview_session_id"]
        )

    def _interview_first_question(self, payload: Any) -> dict[str, Any]:
        return self._interview_service().request_first_question(
            _exact(payload, {"interview_session_id"})["interview_session_id"]
        )

    def _interview_submit(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"interview_session_id", "client_submission_id", "content"})
        return self._interview_service().submit(
            values["interview_session_id"], values["client_submission_id"], values["content"]
        )

    def _interview_retry(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"interview_session_id", "answer_turn_id"})
        return self._interview_service().retry(
            values["interview_session_id"], values["answer_turn_id"]
        )

    def _interview_control(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"interview_session_id", "action", "topic"})
        return self._interview_service().control(
            values["interview_session_id"], values["action"], values["topic"]
        )

    def _interview_get(self, payload: Any) -> dict[str, Any]:
        return self._interview_service().get(
            _exact(payload, {"interview_session_id"})["interview_session_id"]
        )

    def _interview_disclosure(self, payload: Any) -> dict[str, Any]:
        return self._interview_service().disclosure(_exact(payload, {"attempt_id"})["attempt_id"])

    def _model_list(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return self._interview_service().model()

    def _model_correct(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"item_id", "content"})
        return self._interview_service().challenge(values["item_id"], values["content"])

    def _change_list(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return self._interview_service().changes()

    def _change_control(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"plan_id", "action"})
        return self._interview_service().change_control(values["plan_id"], values["action"])

    def _change_observe(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"plan_id", "content", "signal"})
        return self._interview_service().observe_change(
            values["plan_id"], values["content"], values["signal"]
        )

    def _change_allow_observations(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"plan_id", "enabled"})
        return self._interview_service().allow_change_observations(
            values["plan_id"], values["enabled"]
        )

    def _change_start_review(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"plan_id"})
        return self._interview_service().start_change_review(values["plan_id"])

    def _lock(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        self._session_token = None
        if self._interview is not None:
            self._interview._consents.clear()
        self._runtime.lock()
        return {"locked": True}

    def _external(self) -> ExternalEvidenceService:
        return ExternalEvidenceService(self._runtime.reflection.connection)

    def _scan_configured_inbox(self) -> None:
        row = self._runtime.reflection.connection.execute(
            "SELECT inbox_path FROM external_sources WHERE source_id=?", (SOURCE_ID,)
        ).fetchone()
        if row is None or not isinstance(row[0], str):
            return
        try:
            self._external().scan_inbox(Path(row[0]))
        except ExternalEvidenceError:
            # A failed background scan is never a failed unlock.  The owner
            # sees ERROR in source status and can explicitly retry after
            # correcting the local inbox.
            with self._runtime.reflection.connection:
                self._runtime.reflection.connection.execute(
                    "UPDATE external_sources SET state='ERROR',updated_at=? WHERE source_id=?",
                    (datetime.now(UTC).isoformat(), SOURCE_ID),
                )

    def _mark_external_error(self) -> None:
        with self._runtime.reflection.connection:
            self._runtime.reflection.connection.execute(
                "UPDATE external_sources SET state='ERROR',updated_at=? WHERE source_id=?",
                (datetime.now(UTC).isoformat(), SOURCE_ID),
            )

    def _external_source_status(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        row = self._runtime.reflection.connection.execute(
            "SELECT label,state,inbox_path,last_imported_at FROM external_sources WHERE source_id=?",
            (SOURCE_ID,),
        ).fetchone()
        snapshot = self._runtime.reflection.connection.execute(
            "SELECT snapshot_status,issue_count FROM external_import_batches "
            "WHERE source_id=? ORDER BY imported_at DESC,batch_id DESC LIMIT 1",
            (SOURCE_ID,),
        ).fetchone()
        return {
            "configured": row is not None,
            "label": row[0] if row else None,
            "state": row[1] if row else "DISABLED",
            "inbox_path": row[2] if row else None,
            "last_imported_at": row[3] if row else None,
            "snapshot_status": snapshot[0] if snapshot else None,
            "issue_count": snapshot[1] if snapshot else None,
            "nights": self._runtime.reflection.connection.execute(
                "SELECT count(*) FROM sleep_episodes"
            ).fetchone()[0],
        }

    def _external_source_configure(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"inbox_path"})
        inbox = values["inbox_path"]
        if not isinstance(inbox, str) or not inbox or len(inbox) > 1024:
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        self._external().configure_source(inbox_path=inbox)
        return self._external_source_status({})

    def _external_scan(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        row = self._runtime.reflection.connection.execute(
            "SELECT inbox_path FROM external_sources WHERE source_id=?", (SOURCE_ID,)
        ).fetchone()
        if row is None or not isinstance(row[0], str):
            raise PersonalDesktopServiceError("INBOX_UNAVAILABLE")
        try:
            return self._external().scan_inbox(Path(row[0]))
        except ExternalEvidenceError:
            self._mark_external_error()
            raise

    def _sleep_history(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"days"})
        if not isinstance(values["days"], int) or not 1 <= values["days"] <= 30:
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        return {"episodes": self._external().sleep_history(values["days"])}

    def _sleep_delete_record(self, payload: Any) -> dict[str, Any]:
        record_id = _exact(payload, {"external_record_id"})["external_record_id"]
        if not isinstance(record_id, str) or not record_id:
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        self._external().delete_external_record(record_id)
        return {"deleted": True}

    def _create_session(self, payload: Any) -> dict[str, Any]:
        return self._runtime.reflection.create_session(_exact(payload, {"title"})["title"])

    def _list_sessions(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return self._runtime.reflection.list_sessions()

    def _get_session(self, payload: Any) -> dict[str, Any]:
        return self._runtime.reflection.get_session(_exact(payload, {"session_id"})["session_id"])

    def _add_turn(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"session_id", "content"})
        return self._runtime.reflection.add_user_turn(values["session_id"], values["content"])

    def _close_session(self, payload: Any) -> dict[str, Any]:
        return self._runtime.reflection.close_session(_exact(payload, {"session_id"})["session_id"])

    def _delete_session(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"session_id", "confirmation"})
        return self._runtime.lifecycle.delete_session(
            self._runtime.reflection, values["session_id"], values["confirmation"]
        )

    def _search(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        legacy = {"query", "state", "limit", "offset"}
        current = {*legacy, "content", "period", "formulation_status"}
        if set(payload) == legacy:
            values = {**payload, "content": "ALL", "period": "ALL", "formulation_status": "ALL"}
        elif set(payload) == current:
            values = payload
        else:
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        return PersonalContextRetrievalService(self._runtime.reflection).search(**values)

    def _exploration(self) -> GuidedExplorationService:
        self._guard.require()
        return GuidedExplorationService(self._runtime.reflection)  # type: ignore[arg-type]

    def _exploration_start(self, payload: Any) -> dict[str, Any]:
        return self._exploration().start(_exact(payload, {"session_id"})["session_id"])

    def _exploration_get(self, payload: Any) -> dict[str, Any]:
        return self._exploration().get(_exact(payload, {"session_id"})["session_id"])

    def _exploration_answer(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"question_id", "answer_text"})
        return self._exploration().answer(values["question_id"], values["answer_text"])

    def _exploration_skip(self, payload: Any) -> dict[str, Any]:
        return self._exploration().skip(_exact(payload, {"question_id"})["question_id"])

    def _formulation_propose(self, payload: Any) -> dict[str, Any]:
        return self._exploration().propose_formulation(
            _exact(payload, {"session_id"})["session_id"]
        )

    def _formulation_correct(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"formulation_id", "correction_text"})
        return self._exploration().correct_formulation(
            values["formulation_id"], values["correction_text"]
        )

    def _formulation_accept(self, payload: Any) -> dict[str, Any]:
        return self._exploration().set_formulation_status(
            _exact(payload, {"formulation_id"})["formulation_id"], "CURRENT"
        )

    def _formulation_reject(self, payload: Any) -> dict[str, Any]:
        return self._exploration().set_formulation_status(
            _exact(payload, {"formulation_id"})["formulation_id"], "REJECTED"
        )

    def _backup(self, payload: Any) -> dict[str, Any]:
        return self._runtime.lifecycle.create_backup(_secret(payload))

    def _restore_isolated(self, payload: Any) -> dict[str, Any]:
        values = _exact(payload, {"backup_id", "secret"})
        if (
            not isinstance(values["secret"], str)
            or not values["secret"]
            or len(values["secret"]) > MAX_SECRET
        ):
            raise PersonalDesktopServiceError("INVALID_PAYLOAD")
        return self._runtime.lifecycle.restore_isolated(values["backup_id"], values["secret"])

    def _recovery_status(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        return {
            "local_personal": self._guard.status()["local_personal"],
            "rotation": "STATUS_UNAVAILABLE_WHILE_LOCKED" if self._guard.locked else "READY",
        }

    def _export(self, payload: Any) -> dict[str, Any]:
        return self._runtime.lifecycle.create_owner_export(_secret(payload))

    def _rotate(self, payload: Any) -> dict[str, Any]:
        return self._runtime.rotate(_secret(payload))
