"""Synthetic-only E02 application service behind the desktop IPC adapter.

The service owns no transport or renderer behavior.  It exposes a deliberately
small command set whose responses are bounded view models without paths, keys,
raw exception text, or storage handles.  E02 remains synthetic-only while the
REAL_DATA_GATE is closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import secrets
import sqlite3
import tempfile
from typing import Any, Final

from sqlcipher3 import dbapi2

from psyche_os.application.action_planning import ActionPlanningService
from psyche_os.application.e03_archive import E03ArchiveError, E03ArchiveService
from psyche_os.application.e07_bounded_ai import (ALLOWED_ROLES_BY_CATEGORY, PURPOSE, BoundedAIProposalService, E07BoundaryError, ProviderRegistry, ProviderRegistryEntry)
from psyche_os.adapters.e07_provider import OpenAIReflectionProvider, SQLiteCanonicalRecordReader
from psyche_os.domain.ai_proposal import EvidenceRole, ProviderIdentity
from psyche_os.policy.engine import CloudPolicy, ExportRule, PolicyAxes, ProcessingLocation, Sensitivity, ThirdPartyScope
from psyche_os.application.guided_exploration import GuidedExplorationService
from psyche_os.application.reflection_sessions import (
    ReflectionSessionError,
    ReflectionSessionService,
    default_app_data,
)
from psyche_os.backup_export.operations import (
    BackupBuilder,
    ExportBuilder,
    activate_restored_vault,
    restore_backup,
    verify_backup_file,
    verify_export,
)
from psyche_os.backup_export.package_store import BackupPackageStore
from psyche_os.crypto.envelope import derive_domain_key, generate_vmk
from psyche_os.domain.ids import VaultId, generate_id
from psyche_os.storage.migrations import Migrator

PROTOCOL_VERSION: Final = "1.0"
BUILD_VERSION: Final = "0.2.0"
MAX_TEXT: Final = 512
MAX_SECRET: Final = 256
ALLOWED_EXPORT_PURPOSES: Final = frozenset({"portability", "review"})
ALLOWED_EXPORT_AUDIENCES: Final = frozenset({"owner", "trusted-reviewer"})
ALLOWED_EXPORT_SCOPES: Final = frozenset({"synthetic", "synthetic minimum"})
ALLOWED_COMMANDS: Final = frozenset(
    {
        "status.get",
        "session.unlock",
        "session.lock",
        "correction.apply",
        "deletion.plan",
        "deletion.execute",
        "backup.status",
        "backup.verify",
        "recovery.validate",
        "recovery.activate",
        "export.preview",
        "export.execute",
        "archive.operate",
        "archive.timeline",
        "archive.explorer",
        "archive.snapshot_diff",
        "archive.deletion.execute",
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
        "reflection_action.options",
        "reflection_action.list",
        "reflection_action.create",
        "reflection_action.record_outcome",
        "ai.status", "ai.list_eligible", "ai.prepare", "ai.authorize_execute",
    }
)
SESSION_REQUIRED_COMMANDS: Final = frozenset(
    {
        "session.lock",
        "correction.apply",
        "deletion.plan",
        "deletion.execute",
        "backup.verify",
        "recovery.validate",
        "recovery.activate",
        "export.preview",
        "export.execute",
        "archive.operate",
        "archive.timeline",
        "archive.explorer",
        "archive.snapshot_diff",
        "archive.deletion.execute",
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
        "reflection_action.options",
        "reflection_action.list",
        "reflection_action.create",
        "reflection_action.record_outcome",
        "ai.list_eligible", "ai.prepare", "ai.authorize_execute",
    }
)

class DesktopServiceError(Exception):
    """Stable content-free failure surfaced across the privileged boundary."""

    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


def _require_exact(payload: dict[str, Any], required: set[str]) -> None:
    if set(payload) != required:
        raise DesktopServiceError("INVALID_PAYLOAD")


def _bounded_text(value: Any, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or len(value) > MAX_TEXT:
        raise DesktopServiceError("INVALID_PAYLOAD")
    if not allow_empty and not value.strip():
        raise DesktopServiceError("INVALID_PAYLOAD")
    return value.strip()


class SyntheticVaultOperations:
    """Own a disposable synthetic vault while calling accepted E01 operations."""

    def __init__(self) -> None:
        self._temporary = tempfile.TemporaryDirectory(prefix="psyche-os-e02-synthetic-")
        self._root = Path(self._temporary.name)
        self._store = BackupPackageStore(str(self._root / "recovery"))
        self._active_path = Path(self._store.backup_root) / "active.db"
        self._backup_relative = "verified.psychebackup"
        self._vault_id = VaultId(generate_id())
        vmk = generate_vmk()
        try:
            self._backup_key = derive_domain_key(vmk, "backup")
            self._export_key = derive_domain_key(vmk, "export")
        finally:
            vmk.clear()
        self._active_db_key_hex = secrets.token_hex(32)
        self._candidate_path: Path | None = None
        self._candidate_db_key_hex: str | None = None
        self._create_synthetic_vault_and_backup()

    def _connect(self) -> Any:
        connection = dbapi2.connect(str(self._active_path))
        connection.execute(f"PRAGMA key = \"x'{self._active_db_key_hex}'\"")
        return connection

    def _create_synthetic_vault_and_backup(self) -> None:
        connection = self._connect()
        try:
            report = Migrator(connection).apply(1)
            if report.errors or report.applied != [1]:
                raise DesktopServiceError("SYNTHETIC_VAULT_FAILED")
            salt = b"\x00" * 32
            connection.execute(
                "INSERT INTO vault_config (vault_id, vault_name, data_mode, created_at, "
                "vmk_os_wrapped, db_key_salt, blob_envelope_key_salt, key_state) "
                "VALUES (?, 'E02 fictional vault', 'synthetic_only', datetime('now'), "
                "NULL, ?, ?, 'generated')",
                (str(self._vault_id), salt, salt),
            )
            connection.commit()
            BackupBuilder(self._vault_id, self._backup_key).build(
                connection, self._store, self._backup_relative
            )
        except DesktopServiceError:
            raise
        except Exception as exc:
            raise DesktopServiceError("SYNTHETIC_VAULT_FAILED") from exc
        finally:
            connection.close()

    def verify_backup(self) -> bool:
        verified, _detail = verify_backup_file(self._store, self._backup_relative, self._backup_key)
        return verified

    def validate_recovery(self) -> bool:
        candidate = Path(self._store.backup_root) / f"candidate-{secrets.token_hex(8)}.db"
        candidate_key = secrets.token_hex(32)
        result = restore_backup(
            store=self._store,
            relative_path=self._backup_relative,
            backup_key=self._backup_key,
            restore_db_path=str(candidate),
            restore_db_key_hex=candidate_key,
        )
        if not result.get("success") or result.get("activated") is not False:
            return False
        self._candidate_path = candidate
        self._candidate_db_key_hex = candidate_key
        return True

    def activate_recovery(self) -> bool:
        if self._candidate_path is None or self._candidate_db_key_hex is None:
            return False
        result = activate_restored_vault(
            restored_db_path=str(self._candidate_path),
            db_key_hex=self._candidate_db_key_hex,
            active_db_path=str(self._active_path),
            backup_key=self._backup_key,
            activation_store=self._store,
        )
        if not result.get("success") or result.get("activated") is not True:
            return False
        self._active_db_key_hex = self._candidate_db_key_hex
        self._candidate_path = None
        self._candidate_db_key_hex = None
        return True

    def export(self, export_id: str) -> bool:
        output = self._root / "exports" / export_id
        connection = self._connect()
        try:
            ExportBuilder(self._vault_id, self._export_key).export(
                connection=connection,
                output_dir=str(output),
                encrypted=True,
                tables=["vault_config"],
            )
        except Exception:
            return False
        finally:
            connection.close()
        verified, _detail = verify_export(str(output), self._export_key)
        return verified

    def close(self) -> None:
        self._backup_key.clear()
        self._export_key.clear()
        self._temporary.cleanup()


@dataclass(slots=True)
class DesktopApplicationService:
    """Bounded E02 synthetic workflow state.

    The accepted storage/backup primitives remain authoritative.  E02 proves
    the UI and authority semantics with repository-owned synthetic state; it
    does not enable arbitrary capture, paths, blobs, or real vault ingestion.
    """

    _session_token: str | None = None
    _locked: bool = True
    _record_deleted: bool = False
    _record_versions: list[str] = field(default_factory=lambda: ["Synthetic baseline observation"])
    _deletion_plans: dict[str, bool] = field(default_factory=dict)
    _recovery_candidate: str | None = None
    _active_generation: str = "synthetic-active-v1"
    _export_previews: dict[str, dict[str, Any]] = field(default_factory=dict)
    _vault_operations: SyntheticVaultOperations = field(
        default_factory=SyntheticVaultOperations, repr=False
    )
    _archive_connection: Any = field(init=False, repr=False)
    _archive: E03ArchiveService = field(init=False, repr=False)
    _reflection_sessions: ReflectionSessionService = field(init=False, repr=False)
    _guided_exploration: GuidedExplorationService = field(init=False, repr=False)
    _action_planning: ActionPlanningService = field(init=False, repr=False)
    _ai: BoundedAIProposalService = field(init=False, repr=False)
    _ai_prepared: Any = field(init=False, default=None, repr=False)

    def __post_init__(self) -> None:
        self._archive_connection = sqlite3.connect(":memory:")
        self._archive = E03ArchiveService(self._archive_connection)
        try:
            self._reflection_sessions = ReflectionSessionService(default_app_data())
            self._guided_exploration = GuidedExplorationService(self._reflection_sessions)
            self._action_planning = ActionPlanningService(self._reflection_sessions)
            self._seed_ai_lab()
        except ReflectionSessionError as exc:
            raise DesktopServiceError(exc.code) from exc

    def dispatch(
        self,
        command: str,
        payload: dict[str, Any],
        session_token: str | None,
    ) -> dict[str, Any]:
        if command not in ALLOWED_COMMANDS:
            raise DesktopServiceError("UNKNOWN_COMMAND")
        if not isinstance(payload, dict):
            raise DesktopServiceError("INVALID_PAYLOAD")
        if command in SESSION_REQUIRED_COMMANDS:
            self._require_session(session_token)

        handlers = {
            "status.get": self._status,
            "session.unlock": self._unlock,
            "session.lock": self._lock,
            "correction.apply": self._correction,
            "deletion.plan": self._plan_deletion,
            "deletion.execute": self._execute_deletion,
            "backup.status": self._backup_status,
            "backup.verify": self._verify_backup,
            "recovery.validate": self._validate_recovery,
            "recovery.activate": self._activate_recovery,
            "export.preview": self._preview_export,
            "export.execute": self._execute_export,
            "archive.operate": self._archive_operate,
            "archive.timeline": self._archive_timeline,
            "archive.explorer": self._archive_explorer,
            "archive.snapshot_diff": self._archive_snapshot_diff,
            "archive.deletion.execute": self._archive_execute_deletion,
            "reflection_session.create": self._reflection_create,
            "reflection_session.list": self._reflection_list,
            "reflection_session.get": self._reflection_get,
            "reflection_session.add_turn": self._reflection_add_turn,
            "reflection_session.close": self._reflection_close,
            "reflection_session.delete": self._reflection_delete,
            "reflection.search": self._reflection_search,
            "reflection_exploration.start": self._exploration_start,
            "reflection_exploration.get": self._exploration_get,
            "reflection_exploration.answer": self._exploration_answer,
            "reflection_exploration.skip": self._exploration_skip,
            "reflection_exploration.formulation.propose": self._exploration_formulation_propose,
            "reflection_exploration.formulation.correct": self._exploration_formulation_correct,
            "reflection_exploration.formulation.accept": self._exploration_formulation_accept,
            "reflection_exploration.formulation.reject": self._exploration_formulation_reject,
            "reflection_action.options": self._action_options,
            "reflection_action.list": self._action_list,
            "reflection_action.create": self._action_create,
            "reflection_action.record_outcome": self._action_record_outcome,
            "ai.status": self._ai_status, "ai.list_eligible": self._ai_list_eligible, "ai.prepare": self._ai_prepare, "ai.authorize_execute": self._ai_authorize_execute,
        }
        return handlers[command](payload)

    def _seed_ai_lab(self) -> None:
        self._archive.operate("CAPTURE_LAMP_REPORT", "reported_exact", "ai-lab-lamp")
        self._archive.operate("CAPTURE_COUNTERREPORT", "reported_exact", "ai-lab-counter")
        self._archive.operate("ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed", "ai-lab-unknown")
        fixture = {"assertion-lamp": "The fictional east-bench console appeared amber.", "assertion-counter": "The fictional maintenance ledger records a green console state in an unresolved window.", "unknown-lamp": "Which fictional controller state applied at the same clock?"}
        self._archive_connection.execute("UPDATE assertions SET object_value=? WHERE record_id='assertion-lamp' AND is_active=1", (fixture["assertion-lamp"],))
        self._archive_connection.execute("UPDATE assertions SET object_value=? WHERE record_id='assertion-counter' AND is_active=1", (fixture["assertion-counter"],))
        self._archive_connection.execute("UPDATE unknowns SET question=? WHERE record_id='unknown-lamp' AND is_active=1", (fixture["unknown-lamp"],))
        now = __import__('datetime').datetime.now(__import__('datetime').UTC)
        for record_id in fixture:
            self._archive_connection.execute("INSERT INTO data_policies(record_id,policy_id,version_id,previous_version_id,target_record_id,sensitivity,processing_location,cloud_policy,purpose,purpose_expiry,third_party_scope,retention_policy_id,retention_review,export_rule,export_audience,lineage_rule,tx_from,tx_to,is_active,created_at,closure_marker) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (f"record-policy-{record_id}", f"policy-{record_id}", f"policy-{record_id}-v1", "", record_id, "sensitive", "approved_cloud", "ask_each_time", PURPOSE, (now + __import__('datetime').timedelta(days=1)).isoformat(), "none", "ephemeral-e07", (now + __import__('datetime').timedelta(days=1)).isoformat(), "block", "e07-openai-evaluation", "most_restrictive_parent", now.isoformat(), None, 1, now.isoformat(), ""))
        identity = ProviderIdentity("openai", "gpt-5.6-luna", "responses-v1-store-false")
        self._ai = BoundedAIProposalService(SQLiteCanonicalRecordReader(self._archive_connection), ProviderRegistry((ProviderRegistryEntry(identity, "e07-synthetic-disclosure-v1", "knowledge-synthetic-v1", "2.0.0-research-final", True, identity.digest),)), OpenAIReflectionProvider())

    def _ai_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        return {
            "runtime_profile": "SYNTHETIC_LAB",
            "local_personal": "NOT_ADMITTED",
            "ai": "READY_SYNTHETIC_LAB" if os.environ.get("OPENAI_API_KEY") else "NOT_CONFIGURED",
            "provider": "OpenAI",
            "model": "gpt-5.6-luna",
        }

    def _ai_list_eligible(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        import datetime as dt
        records = self._ai.list_eligible(cutoff=dt.datetime.now(dt.UTC))
        return {"provider": "OpenAI", "model": "gpt-5.6-luna", "records": records, "notice": "Synthetic cloud-eligible records only; proposal only."}

    @staticmethod
    def _validate_ai_selection(value: Any) -> tuple[tuple[str, EvidenceRole], ...]:
        if not isinstance(value, list) or not value or len(value) > 8:
            raise DesktopServiceError("INVALID_SELECTION")
        selected: list[tuple[str, EvidenceRole]] = []
        seen: set[str] = set()
        for item in value:
            if not isinstance(item, dict) or set(item) != {"record_id", "role"}:
                raise DesktopServiceError("INVALID_SELECTION")
            record_id = item["record_id"]
            role_value = item["role"]
            if (
                not isinstance(record_id, str)
                or not record_id.strip()
                or len(record_id) > MAX_TEXT
                or role_value not in {"supporting", "counterevidence", "unknown"}
            ):
                raise DesktopServiceError("INVALID_SELECTION")
            record_id = record_id.strip()
            if record_id in seen:
                raise DesktopServiceError("INVALID_SELECTION")
            seen.add(record_id)
            selected.append((record_id, EvidenceRole(role_value)))
        roles = {role for _, role in selected}
        if roles != {EvidenceRole.SUPPORTING, EvidenceRole.COUNTEREVIDENCE, EvidenceRole.UNKNOWN}:
            raise DesktopServiceError("INVALID_SELECTION")
        return tuple(selected)

    def _ai_prepare(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"selected"})
        import datetime as dt, uuid
        selected = self._validate_ai_selection(payload["selected"])
        roles_by_id = dict(selected)
        # Backend-owned category/role compatibility: a renderer cannot assign
        # a role the record category does not allow, nor select a reflection
        # workspace id (it is never a canonical eligible record).
        for record_id, role in selected:
            category = self._ai.category_for(record_id)
            if category not in ALLOWED_ROLES_BY_CATEGORY or role not in ALLOWED_ROLES_BY_CATEGORY[category]:
                raise DesktopServiceError("INVALID_SELECTION")
        identity = ProviderIdentity("openai", "gpt-5.6-luna", "responses-v1-store-false")
        try:
            self._ai_prepared = self._ai.prepare(interaction_id=f"ai-lab-{uuid.uuid4()}", purpose=PURPOSE, selected=selected, provider_identity=identity, cutoff=dt.datetime.now(dt.UTC))
        except E07BoundaryError as exc: raise DesktopServiceError(exc.code) from exc
        preview = self._ai_prepared.preview
        selected_rows = [
            {"record_id": record_id, "version_id": version_id, "category": category, "role": roles_by_id[record_id].value}
            for record_id, version_id, category in preview.selected
        ]
        return {"preview_id": preview.preview_id, "selected": selected_rows, "provider": "OpenAI", "model": "gpt-5.6-luna", "purpose": preview.purpose, "retention": preview.retention, "notice": "Synthetic cloud-eligible records only; proposal only."}

    def _ai_authorize_execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"preview_id", "opt_in"})
        import datetime as dt
        if not os.environ.get("OPENAI_API_KEY"):
            raise DesktopServiceError("AI_NOT_CONFIGURED")
        if self._ai_prepared is None or payload["preview_id"] != self._ai_prepared.preview.preview_id or payload["opt_in"] is not True: raise DesktopServiceError("AUTHORIZATION_MISMATCH")
        now = dt.datetime.now(dt.UTC)
        try:
            authorization = self._ai.authorize(self._ai_prepared, authorized_at=now, expires_at=now + dt.timedelta(minutes=2), opt_in=True)
            result = self._ai.execute(self._ai_prepared, authorization, now=now)
        except E07BoundaryError as exc: raise DesktopServiceError(exc.code) from exc
        return {
            "proposal": {
                "status": result.proposal.status.value,
                "reflections": [
                    {
                        "statement_id": item.statement_id,
                        "text": item.text,
                        "supporting_evidence_ids": list(item.supporting_evidence_ids),
                        "uncertainty": item.uncertainty,
                        "claim_level": int(item.claim_level),
                    }
                    for item in result.proposal.reflections
                ],
                "counterevidence": list(result.proposal.counterevidence_ids),
                "unknowns": [
                    {
                        "unknown_id": item.unknown_id,
                        "uncertainty": item.uncertainty,
                    }
                    for item in result.proposal.unknowns
                ],
                "questions": [
                    {
                        "question_id": item.question_id,
                        "unknown_id": item.unknown_id,
                        "text": item.text,
                    }
                    for item in result.proposal.questions
                ],
            },
            "notice": "PROPOSED only; nothing was written back.",
        }

    def _reflection_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"title"})
        return self._reflection_call(self._reflection_sessions.create_session, payload["title"])

    def _reflection_list(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        return self._reflection_call(self._reflection_sessions.list_sessions)

    def _reflection_get(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id"})
        return self._reflection_call(self._reflection_sessions.get_session, payload["session_id"])

    def _reflection_add_turn(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id", "content"})
        return self._reflection_call(
            self._reflection_sessions.add_user_turn, payload["session_id"], payload["content"]
        )

    def _reflection_close(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id"})
        return self._reflection_call(self._reflection_sessions.close_session, payload["session_id"])

    def _reflection_delete(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id", "confirmation"})
        return self._reflection_call(
            self._reflection_sessions.delete_session, payload["session_id"], payload["confirmation"]
        )

    def _reflection_search(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"query", "state", "limit", "offset"})
        return self._reflection_call(
            self._reflection_sessions.search,
            payload["query"],
            payload["state"],
            payload["limit"],
            payload["offset"],
        )

    def _exploration_start(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id"})
        return self._reflection_call(self._guided_exploration.start, payload["session_id"])

    def _exploration_get(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id"})
        return self._reflection_call(self._guided_exploration.get, payload["session_id"])

    def _exploration_answer(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"question_id", "answer_text"})
        return self._reflection_call(
            self._guided_exploration.answer, payload["question_id"], payload["answer_text"]
        )

    def _exploration_skip(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"question_id"})
        return self._reflection_call(self._guided_exploration.skip, payload["question_id"])

    def _exploration_formulation_propose(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id"})
        return self._reflection_call(
            self._guided_exploration.propose_formulation, payload["session_id"]
        )

    def _exploration_formulation_correct(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"formulation_id", "correction_text"})
        return self._reflection_call(
            self._guided_exploration.correct_formulation,
            payload["formulation_id"],
            payload["correction_text"],
        )

    def _exploration_formulation_accept(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"formulation_id"})
        return self._reflection_call(
            self._guided_exploration.set_formulation_status, payload["formulation_id"], "CURRENT"
        )

    def _exploration_formulation_reject(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"formulation_id"})
        return self._reflection_call(
            self._guided_exploration.set_formulation_status, payload["formulation_id"], "REJECTED"
        )

    def _action_options(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id", "anchor_type", "anchor_id"})
        return self._reflection_call(
            self._action_planning.options,
            payload["session_id"],
            payload["anchor_type"],
            payload["anchor_id"],
        )

    def _action_list(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"session_id"})
        return self._reflection_call(self._action_planning.list, payload["session_id"])

    def _action_create(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(
            payload,
            {"session_id", "user_goal", "template_id", "action_text", "anchor_type", "anchor_id"},
        )
        return self._reflection_call(
            self._action_planning.create,
            payload["session_id"],
            payload["user_goal"],
            payload["template_id"],
            payload["action_text"],
            payload["anchor_type"],
            payload["anchor_id"],
        )

    def _action_record_outcome(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"plan_id", "status", "note_text"})
        return self._reflection_call(
            self._action_planning.record_outcome,
            payload["plan_id"],
            payload["status"],
            payload["note_text"],
        )

    @staticmethod
    def _reflection_call(operation: Any, *args: Any) -> dict[str, Any]:
        try:
            return operation(*args)
        except ReflectionSessionError as exc:
            raise DesktopServiceError(exc.code) from exc

    def _archive_operate(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"operation", "choice", "idempotency_key"})
        try:
            return self._archive.operate(
                _bounded_text(payload["operation"]),
                _bounded_text(payload["choice"]),
                _bounded_text(payload["idempotency_key"]),
            )
        except E03ArchiveError as exc:
            raise DesktopServiceError(exc.code) from exc

    def _archive_timeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"temporal_role"})
        try:
            role = _bounded_text(payload["temporal_role"])
            return {"selected_clock": role, "items": self._archive.timeline(role)}
        except E03ArchiveError as exc:
            raise DesktopServiceError(exc.code) from exc

    def _archive_explorer(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        return self._archive.explorer()

    def _archive_snapshot_diff(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        return self._archive.snapshot_diff()

    def _archive_execute_deletion(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"plan_id", "confirmation"})
        try:
            return self._archive.execute_deletion(
                _bounded_text(payload["plan_id"]), _bounded_text(payload["confirmation"])
            )
        except E03ArchiveError as exc:
            raise DesktopServiceError(exc.code) from exc

    def _require_session(self, token: str | None) -> None:
        if self._locked or not isinstance(token, str) or not self._session_token:
            raise DesktopServiceError("SESSION_REQUIRED")
        if not secrets.compare_digest(token, self._session_token):
            raise DesktopServiceError("SESSION_REQUIRED")

    def _status(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        return {
            "locked": self._locked,
            "data_mode": "SYNTHETIC_ONLY",
            "real_data_gate": "CLOSED",
            "inbound_listener": "NONE",
            "outbound_provider": "READY_EXPLICIT_E07" if os.environ.get("OPENAI_API_KEY") else "NOT_CONFIGURED",
            "runtime_profile": "SYNTHETIC_LAB",
            "build_version": BUILD_VERSION,
            "privacy": {
                "processing_location": "LOCAL_ONLY",
                "cloud_storage": "DISABLED",
                "cloud_disclosure": "SYNTHETIC_EXPLICIT_E07_ONLY",
                "telemetry": "OFF",
            },
        }

    def _unlock(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"secret"})
        secret = payload["secret"]
        if not isinstance(secret, str) or not secret or len(secret) > MAX_SECRET:
            raise DesktopServiceError("UNLOCK_REJECTED")
        # The launch profile is repository-owned synthetic data.  Any bounded
        # non-empty secret establishes an ephemeral local demonstration session.
        self._session_token = secrets.token_urlsafe(32)
        self._locked = False
        return {
            "session_token": self._session_token,
            "locked": False,
            "notice": "Synthetic local session. Real data remains prohibited.",
        }

    def _lock(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        self._locked = True
        self._session_token = None
        return {"locked": True}

    def _correction(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"record_id", "replacement", "reason"})
        if _bounded_text(payload["record_id"]) != "synthetic-observation-1":
            raise DesktopServiceError("RECORD_NOT_FOUND")
        replacement = _bounded_text(payload["replacement"])
        _bounded_text(payload["reason"])
        if self._record_deleted:
            raise DesktopServiceError("RECORD_NOT_FOUND")
        self._record_versions.append(replacement)
        return {
            "record_id": "synthetic-observation-1",
            "version_count": len(self._record_versions),
            "history_preserved": True,
            "current_text": replacement,
        }

    def _plan_deletion(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"record_id"})
        if _bounded_text(payload["record_id"]) != "synthetic-observation-1":
            raise DesktopServiceError("RECORD_NOT_FOUND")
        if self._record_deleted:
            raise DesktopServiceError("RECORD_NOT_FOUND")
        plan_id = f"plan-{secrets.token_hex(8)}"
        self._deletion_plans[plan_id] = False
        return {
            "plan_id": plan_id,
            "affected_counts": {"observations": 1, "versions": len(self._record_versions)},
            "backup_expiry": "Declared backup retention still applies.",
            "external_limitations": [
                "Previously exported or recipient-controlled copies are outside this deletion."
            ],
            "requires_confirmation": True,
        }

    def _execute_deletion(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"plan_id", "confirmation"})
        plan_id = _bounded_text(payload["plan_id"])
        if payload["confirmation"] != "DELETE SYNTHETIC RECORD":
            raise DesktopServiceError("CONFIRMATION_REQUIRED")
        if plan_id not in self._deletion_plans or self._deletion_plans[plan_id]:
            raise DesktopServiceError("PLAN_INVALID")
        self._deletion_plans[plan_id] = True
        self._record_deleted = True
        return {
            "receipt_id": f"receipt-{secrets.token_hex(8)}",
            "completion_status": "synthetic_session_complete",
            "counts": {"observations": 1, "versions": len(self._record_versions)},
            "content_in_receipt": False,
            "known_exclusions": ["External copies remain outside local control."],
        }

    def _backup_status(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        verified = self._vault_operations.verify_backup()
        return {
            "state": "VERIFIED_SYNTHETIC" if verified else "VERIFICATION_FAILED",
            "last_verified": "2026-08-13T00:00:00Z",
            "restore_tested": True,
            "export_is_backup": False,
        }

    def _verify_backup(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        if not self._vault_operations.verify_backup():
            raise DesktopServiceError("BACKUP_VERIFY_FAILED")
        return {"verified": True, "content_disclosed": False}

    def _validate_recovery(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, set())
        if not self._vault_operations.validate_recovery():
            raise DesktopServiceError("RECOVERY_VALIDATION_FAILED")
        self._recovery_candidate = f"candidate-{secrets.token_hex(8)}"
        return {
            "candidate_id": self._recovery_candidate,
            "validated": True,
            "activated": False,
            "active_vault_preserved": True,
        }

    def _activate_recovery(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"candidate_id", "confirmation"})
        candidate = _bounded_text(payload["candidate_id"])
        if candidate != self._recovery_candidate:
            raise DesktopServiceError("CANDIDATE_INVALID")
        if payload["confirmation"] != "ACTIVATE VALIDATED CANDIDATE":
            raise DesktopServiceError("CONFIRMATION_REQUIRED")
        if not self._vault_operations.activate_recovery():
            raise DesktopServiceError("RECOVERY_ACTIVATION_FAILED")
        previous = self._active_generation
        self._active_generation = candidate
        self._recovery_candidate = None
        return {
            "activated": True,
            "previous_vault_retained": True,
            "previous_generation": previous,
        }

    def _preview_export(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"purpose", "audience", "scope", "encrypted", "redacted"})
        purpose = _bounded_text(payload["purpose"])
        audience = _bounded_text(payload["audience"])
        scope = _bounded_text(payload["scope"])
        if not isinstance(payload["encrypted"], bool) or not isinstance(payload["redacted"], bool):
            raise DesktopServiceError("INVALID_PAYLOAD")
        if (
            purpose not in ALLOWED_EXPORT_PURPOSES
            or audience not in ALLOWED_EXPORT_AUDIENCES
            or scope not in ALLOWED_EXPORT_SCOPES
            or not payload["encrypted"]
            or not payload["redacted"]
        ):
            raise DesktopServiceError("POLICY_REQUIRED")
        preview_id = f"export-{secrets.token_hex(8)}"
        preview = {
            "preview_id": preview_id,
            "purpose": purpose,
            "audience": audience,
            "scope": scope,
            "encrypted": payload["encrypted"],
            "redacted": payload["redacted"],
            "export_is_backup": False,
            "requires_confirmation": True,
        }
        self._export_previews[preview_id] = preview
        return preview

    def _execute_export(self, payload: dict[str, Any]) -> dict[str, Any]:
        _require_exact(payload, {"preview_id", "confirmation"})
        preview_id = _bounded_text(payload["preview_id"])
        if preview_id not in self._export_previews:
            raise DesktopServiceError("PREVIEW_INVALID")
        if payload["confirmation"] != "EXPORT SYNTHETIC PACKAGE":
            raise DesktopServiceError("CONFIRMATION_REQUIRED")
        preview = self._export_previews.pop(preview_id)
        export_id = f"completed-{secrets.token_hex(8)}"
        if not self._vault_operations.export(export_id):
            raise DesktopServiceError("EXPORT_FAILED")
        return {
            "export_id": export_id,
            "purpose": preview["purpose"],
            "audience": preview["audience"],
            "scope": preview["scope"],
            "encrypted": preview["encrypted"],
            "redacted": preview["redacted"],
            "export_is_backup": False,
        }

    def close(self) -> None:
        self._archive_connection.close()
        self._vault_operations.close()
        self._reflection_sessions.close()
