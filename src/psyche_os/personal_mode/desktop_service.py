"""Exact local-only Personal desktop command boundary.

This module intentionally does not import the Synthetic desktop service or any
provider, archive, action, longitudinal, importer, telemetry, or network
module.  It is the only dispatcher used by the Personal profile sidecar.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
import os
import secrets
from typing import Any, Final

from psyche_os.application.guided_exploration import GuidedExplorationService
from psyche_os.application.reflection_sessions import ReflectionSessionError
from psyche_os.personal_mode.admission import (
    AdmissionDecision,
    PersonalAdmissionGuard,
    PersonalNotAdmittedError,
)
from psyche_os.personal_mode.lifecycle import PersonalLifecycleError
from psyche_os.personal_mode.runtime import PersonalRuntime, PersonalRuntimeError
from psyche_os.personal_mode.runtime_profile import PersonalRuntimePaths
from psyche_os.personal_mode.ai_working_formulation import OpenAIKeyStore, PersonalAIError, PersonalWorkingFormulationService
from psyche_os.adapters.e07_provider import OpenAIReflectionProvider

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
        self._ai_enabled = os.environ.get("PSYCHE_OS_PERSONAL_PROFILE_ID") == AI_PROFILE_ID
        self._ai: PersonalWorkingFormulationService | None = None

    def close(self) -> None:
        self._session_token = None
        self._runtime.lock()

    def dispatch(
        self, command: str, payload: dict[str, Any], session_token: str | None
    ) -> dict[str, Any]:
        if command not in PERSONAL_ALLOWED_COMMANDS:
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        if command.startswith("ai.") and not self._ai_enabled:
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
            "runtime_profile": "LOCAL_PERSONAL_BOUNDED_OPENAI" if self._ai_enabled else "LOCAL_PERSONAL",
            "local_personal": admission["local_personal"],
            "real_data_gate": "OPEN" if admission["local_personal"] != "NOT_ADMITTED" else "CLOSED",
            "admission_expires_at": admission.get("admission_expires_at"),
            "inbound_listener": "NONE",
            "outbound_provider": "OPENAI_EXPLICIT_OPT_IN" if self._ai_enabled else "NOT_CONFIGURED",
            "network": "OPENAI_EXPLICIT_ONE_CALL_ONLY" if self._ai_enabled else "OFFLINE_NO_LISTENER",
            "privacy": {
                "core_processing_location": "LOCAL",
                "cloud_storage": "DISABLED",
                "cloud_disclosure": "NEVER_CLOUD",
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
        return {"session_token": self._session_token, "locked": False}

    def _ai_service(self) -> PersonalWorkingFormulationService:
        if not self._ai_enabled:
            raise PersonalDesktopServiceError("UNKNOWN_COMMAND")
        if self._ai is None:
            self._ai = PersonalWorkingFormulationService(self._runtime.reflection, OpenAIKeyStore(self._runtime._paths.root), OpenAIReflectionProvider())
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

    def _lock(self, payload: Any) -> dict[str, Any]:
        _exact(payload, set())
        self._session_token = None
        self._runtime.lock()
        return {"locked": True}

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
        values = _exact(payload, {"query", "state", "limit", "offset"})
        return self._runtime.reflection.search(**values)

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
