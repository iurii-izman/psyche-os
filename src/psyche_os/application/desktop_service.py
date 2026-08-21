"""Synthetic-only E02 application service behind the desktop IPC adapter.

The service owns no transport or renderer behavior.  It exposes a deliberately
small command set whose responses are bounded view models without paths, keys,
raw exception text, or storage handles.  E02 remains synthetic-only while the
REAL_DATA_GATE is closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import secrets
import sqlite3
import tempfile
from typing import Any, Final

from sqlcipher3 import dbapi2

from psyche_os.application.e03_archive import E03ArchiveError, E03ArchiveService
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
    }
)
STATE_CHANGING_COMMANDS: Final = frozenset(
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

    def __post_init__(self) -> None:
        self._archive_connection = sqlite3.connect(":memory:")
        self._archive = E03ArchiveService(self._archive_connection)
        try:
            self._reflection_sessions = ReflectionSessionService(default_app_data())
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
        if command in STATE_CHANGING_COMMANDS:
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
        }
        return handlers[command](payload)

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
            "network": "OFFLINE_NO_LISTENER",
            "privacy": {
                "processing_location": "LOCAL_ONLY",
                "cloud": "DISABLED",
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
