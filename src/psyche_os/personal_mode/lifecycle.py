"""Guarded Personal V10 lifecycle operations.

The module deliberately keeps plaintext packages in memory only.  Persistent
artifacts are either SQLCipher databases or AES-GCM authenticated packages.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
from typing import Any, cast

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlcipher3 import dbapi2  # type: ignore[import-untyped]

from psyche_os.crypto.envelope import OSKeyWrapper, SensitiveBytes, derive_domain_key
from psyche_os.personal_mode.admission import PersonalAdmissionGuard
from psyche_os.personal_mode.integrity import verify_personal_vault
from psyche_os.personal_mode.key_envelope import PersonalKeyEnvelope
from psyche_os.personal_mode.package_format import (
    PERSONAL_V11_FORMAT_VERSION,
    PERSONAL_V12_FORMAT_VERSION,
    PERSONAL_V13_FORMAT_VERSION,
    create_personal_package,
    restore_personal_package,
    verify_personal_package,
)
from psyche_os.personal_mode.recovery_bootstrap import (
    create_bootstrap,
    recover_bootstrap,
)
from psyche_os.personal_mode.runtime_profile import PersonalRuntimePaths


class PersonalLifecycleError(Exception):
    """Content-free error returned by all lifecycle failures."""

    code = "PERSONAL_LIFECYCLE_FAILED"


class RotationFaultPoint(StrEnum):
    AFTER_PREPARED = "after_prepared"
    DURING_EXPORT = "during_export"
    AFTER_CANDIDATE_VERIFIED = "after_candidate_verified"
    AFTER_ACTIVATION_STARTED = "after_activation_started"
    AFTER_DB_REPLACEMENT = "after_db_replacement"
    AFTER_DB_N_PLUS_1_VERIFIED = "after_db_n_plus_1_verified"
    DURING_RETAINED_PUBLICATION = "during_retained_publication"
    AFTER_RETAINED_N_PUBLISHED = "after_retained_n_published"
    AFTER_ENVELOPE_N_PLUS_1_PROMOTED = "after_envelope_n_plus_1_promoted"
    AFTER_ROTATION_COMPLETE = "after_rotation_complete"
    BEFORE_JOURNAL_CLEANUP = "before_journal_cleanup"


class RotationProcessInterrupted(BaseException):
    """Test-only process-death signal; deliberately bypasses normal cleanup."""


_JOURNAL_STAGES = frozenset(
    {
        "prepared",
        "candidate_verified",
        "activation_started",
        "db_n_plus_1_verified",
        "retained_n_published",
        "envelope_n_plus_1_promoted",
        "rotation_complete",
    }
)
_JOURNAL_FIELDS = frozenset(
    {
        "format",
        "version",
        "vault_id",
        "profile_id",
        "profile_version",
        "from_key_version",
        "to_key_version",
        "stage",
        "created_at",
        "candidate_id",
        "auth_nonce_hex",
        "auth_ciphertext_hex",
    }
)


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise PersonalLifecycleError()
        value[key] = item
    return value


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _open(path: Path, key: bytes, *, create: bool = False) -> Any:
    if not create and not path.exists():
        raise PersonalLifecycleError()
    connection = dbapi2.connect(str(path))
    connection.execute(f"PRAGMA key = \"x'{key.hex()}'\"")
    connection.execute("PRAGMA foreign_keys = ON")
    if not connection.execute("PRAGMA cipher_version").fetchone()[0]:
        connection.close()
        raise PersonalLifecycleError()
    return connection


def _verify_db(connection: Any, envelope: PersonalKeyEnvelope) -> None:
    try:
        verify_personal_vault(connection, envelope)
    except Exception as exc:
        raise PersonalLifecycleError() from exc


class PersonalLifecycleService:
    """Lifecycle boundary; every public method checks the central guard first."""

    def __init__(
        self,
        paths: PersonalRuntimePaths,
        guard: PersonalAdmissionGuard,
        *,
        os_wrapper_factory: Callable[[], OSKeyWrapper] = OSKeyWrapper,
        rotation_fault_hook: Callable[[RotationFaultPoint], None] | None = None,
    ) -> None:
        self._paths = paths
        self._guard = guard
        self._os_wrapper_factory = os_wrapper_factory
        self._rotation_fault_hook = rotation_fault_hook

    def _fault(self, point: RotationFaultPoint) -> None:
        if self._rotation_fault_hook is not None:
            self._rotation_fault_hook(point)

    def _active_envelope(self) -> PersonalKeyEnvelope:
        self._guard.require()
        try:
            return PersonalKeyEnvelope.parse(self._paths.envelope.read_bytes())
        except Exception as exc:
            raise PersonalLifecycleError() from exc

    def _read_journal(
        self, old: PersonalKeyEnvelope, old_vmk: SensitiveBytes
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Strictly authenticate the N-bound journal before using its payload."""
        try:
            raw = self._paths.rotation_journal.read_bytes()
            if not raw or len(raw) > 64 * 1024:
                raise PersonalLifecycleError()
            public = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
            if not isinstance(public, dict) or set(public) != _JOURNAL_FIELDS:
                raise PersonalLifecycleError()
            if (
                public.get("format") != "PMV1-ROTATION-JOURNAL-V1"
                or public.get("version") != 1
                or public.get("stage") not in _JOURNAL_STAGES
            ):
                raise PersonalLifecycleError()
            if (
                any(
                    public[key] != old.value[key]
                    for key in ("vault_id", "profile_id", "profile_version")
                )
                or public["from_key_version"] != old.value["key_version"]
            ):
                raise PersonalLifecycleError()
            nonce = bytes.fromhex(cast(str, public["auth_nonce_hex"]))
            ciphertext = bytes.fromhex(cast(str, public["auth_ciphertext_hex"]))
            if len(nonce) != 12 or not ciphertext:
                raise PersonalLifecycleError()
            aad = {
                key: value
                for key, value in public.items()
                if key not in {"auth_nonce_hex", "auth_ciphertext_hex"}
            }
            manifest = derive_domain_key(
                old_vmk, "manifest", bytes.fromhex(old.value["manifest_salt_hex"])
            )
            try:
                plain = AESGCM(manifest.raw).decrypt(
                    nonce, ciphertext, b"PMV1-ROTATION-JOURNAL-V1|" + _canonical(aad)
                )
            finally:
                manifest.clear()
            body = json.loads(plain.decode("utf-8"), object_pairs_hook=_no_duplicates)
            if not isinstance(body, dict) or set(body) != {
                "pending_envelope",
                "pending_envelope_sha256",
                "old_envelope_sha256",
                "active_db_identity",
                "candidate_db_relative_path",
                "previous_db_relative_path",
                "candidate_db_sha256",
                "candidate_schema_fingerprint",
            }:
                raise PersonalLifecycleError()
            pending = PersonalKeyEnvelope._validate(body["pending_envelope"], pending=True)
            if (
                pending["key_version"] != public["to_key_version"]
                or hashlib.sha256(_canonical(pending)).hexdigest()
                != body["pending_envelope_sha256"]
                or hashlib.sha256(old.canonical_bytes()).hexdigest() != body["old_envelope_sha256"]
            ):
                raise PersonalLifecycleError()
            for key in ("candidate_db_relative_path", "previous_db_relative_path"):
                if (
                    not isinstance(body[key], str)
                    or not body[key].startswith("staging/")
                    or ".." in body[key]
                    or "\\" in body[key]
                ):
                    raise PersonalLifecycleError()
            return public, body
        except PersonalLifecycleError:
            raise
        except Exception as exc:
            raise PersonalLifecycleError() from exc

    def reconcile_rotation(self, recovery_secret: str) -> str:
        """Classify durable rotation state without mtime/name heuristics.

        Before promotion journal authentication uses active N; after promotion it
        must use the immutable retained N envelope.  Any contradiction is closed.
        """
        self._guard.require()
        active = self._active_envelope()
        try:
            old = active
            if self._paths.rotation_journal.exists() and active.value["key_version"] > 1:
                retained = (
                    self._paths.retained_keys
                    / f"key-envelope-v{active.value['key_version'] - 1}.pmv1.json"
                )
                if not retained.exists():
                    raise PersonalLifecycleError()
                old = PersonalKeyEnvelope.parse(retained.read_bytes())
            old_vmk = old.unwrap_recovery(recovery_secret)
            public, body = self._read_journal(old, old_vmk)
            pending_value = PersonalKeyEnvelope._validate(body["pending_envelope"], pending=True)
            pending_value["key_state"] = "active"
            pending_active = PersonalKeyEnvelope(pending_value)
            pending_vmk = pending_active.unwrap_recovery(recovery_secret)
            pending_key = self._db_key(pending_vmk, pending_active)
            try:
                probe = _open(self._paths.vault, pending_key.raw)
                try:
                    _verify_db(probe, pending_active)
                finally:
                    probe.close()
                new_db = True
            except Exception:
                new_db = False
            finally:
                pending_key.clear()
                pending_vmk.clear()
            if active.value["key_version"] == old.value["key_version"]:
                if new_db:
                    # DB activation happened; no envelope promotion is allowed
                    # until retained N can be published/reopened.
                    self._publish_retained(old, old_vmk, retirement=None)
                    _atomic_write(self._paths.envelope, pending_active.canonical_bytes())
                    self._publish_retained(old, old_vmk, retirement=datetime.now(UTC).isoformat())
                    previous = self._paths.root / body["previous_db_relative_path"]
                    previous.unlink(missing_ok=True)
                    self._paths.rotation_journal.unlink()
                    return "ACTIVE_N_PLUS_1"
                if public["stage"] in {"prepared", "candidate_verified", "activation_started"}:
                    return "ACTIVE_N"
                raise PersonalLifecycleError()
            if active.value["key_version"] == pending_active.value["key_version"] and new_db:
                # Once the promoted N+1 envelope and database have both been
                # independently verified through the N-authenticated journal,
                # the previous N database is no longer a recovery input.  Do
                # not leave it as a spurious retained-key destruction blocker.
                previous = self._paths.root / body["previous_db_relative_path"]
                previous.unlink(missing_ok=True)
                self._paths.rotation_journal.unlink()
                return "ACTIVE_N_PLUS_1"
            raise PersonalLifecycleError()
        except PersonalLifecycleError:
            raise
        except Exception as exc:
            raise PersonalLifecycleError() from exc
        finally:
            if "old_vmk" in locals():
                old_vmk.clear()

    def destruction_dependencies(self, key_version: int) -> tuple[str, ...]:
        """Inspectable dependency oracle; it never relies on generation age."""
        dependencies: list[str] = []
        for metadata in self._paths.backups.glob("*.pmv1/metadata.json"):
            try:
                if json.loads(metadata.read_text(encoding="utf-8"))["key_version"] == key_version:
                    dependencies.append("backup")
            except Exception:
                dependencies.append("backup")
        if self._paths.rotation_journal.exists():
            dependencies.append("journal")
        if any(self._paths.staging.glob("**/vault.sqlite")) or any(
            self._paths.staging.glob("**/previous-N.sqlite")
        ):
            dependencies.append("staging")
        return tuple(sorted(set(dependencies)))

    def destroy_retained(self, key_version: int) -> dict[str, str]:
        self._guard.require()
        if (
            not isinstance(key_version, int)
            or key_version < 1
            or self.destruction_dependencies(key_version)
        ):
            raise PersonalLifecycleError()
        retained = self._paths.retained_keys / f"key-envelope-v{key_version}.pmv1.json"
        metadata = self._paths.retained_keys / f"key-v{key_version}.pmv1.metadata.json"
        if not retained.exists() or not metadata.exists():
            raise PersonalLifecycleError()
        retained.unlink()
        metadata.unlink()
        receipt = self._paths.retained_keys / f"key-v{key_version}.destroyed.json"
        _atomic_write(
            receipt,
            _canonical(
                {
                    "format": "PMV1-RETAINED-KEY-DESTRUCTION-RECEIPT-V1",
                    "key_version": key_version,
                    "destroyed_at": datetime.now(UTC).isoformat(),
                }
            ),
        )
        return {"key_version": str(key_version), "state": "destroyed"}

    @staticmethod
    def _db_key(vmk: SensitiveBytes, envelope: PersonalKeyEnvelope) -> SensitiveBytes:
        return derive_domain_key(vmk, "database", bytes.fromhex(envelope.value["db_salt_hex"]))

    def create_backup(self, recovery_secret: str) -> dict[str, str]:
        self._guard.require()
        envelope = self._active_envelope()
        vmk = envelope.unwrap_recovery(recovery_secret)
        key = self._db_key(vmk, envelope)
        try:
            connection = _open(self._paths.vault, key.raw)
            try:
                _verify_db(connection, envelope)
                package = create_personal_package(connection)
                if package[
                    "format_version"
                ] != PERSONAL_V13_FORMAT_VERSION or not verify_personal_package(package):
                    raise PersonalLifecycleError()
                backup_id = secrets.token_hex(16)
                bootstrap, payload = create_bootstrap(
                    envelope, recovery_secret, _canonical(package), backup_id
                )
            finally:
                connection.close()
            target = self._paths.backups / f"{backup_id}.pmv1"
            target.mkdir(parents=True, exist_ok=False)
            _atomic_write(target / "bootstrap.json", bootstrap)
            _atomic_write(target / "payload.bin", payload)
            _atomic_write(
                target / "metadata.json",
                _canonical(
                    {
                        "format": "PMV1-BACKUP-V11",
                        "key_version": envelope.value["key_version"],
                        "backup_id": backup_id,
                    }
                ),
            )
            # File publication is not a successful backup.  Authenticate it,
            # rebuild it only in staging, and prove the rebuilt vault through
            # the canonical oracle before it can be called recoverable.
            candidate = self.restore_isolated(backup_id, recovery_secret)
            candidate_root = self._paths.staging / candidate["candidate_id"]
            shutil.rmtree(candidate_root)
            bootstrap_value = json.loads(bootstrap.decode("utf-8"))
            return {
                "backup_id": backup_id,
                "key_version": str(envelope.value["key_version"]),
                "verified": "RECOVERABLE",
                "created_at": str(bootstrap_value["created_at"]),
            }
        except Exception as exc:
            if "target" in locals():
                shutil.rmtree(target, ignore_errors=True)
            raise PersonalLifecycleError() from exc
        finally:
            key.clear()
            vmk.clear()

    def restore_isolated(self, backup_id: str, recovery_secret: str) -> dict[str, str]:
        self._guard.require()
        if not isinstance(backup_id, str) or not backup_id or "/" in backup_id or "\\" in backup_id:
            raise PersonalLifecycleError()
        package_root = self._paths.backups / f"{backup_id}.pmv1"
        try:
            raw = recover_bootstrap(
                (package_root / "bootstrap.json").read_bytes(),
                recovery_secret,
                (package_root / "payload.bin").read_bytes(),
            )
            package = json.loads(raw.decode("utf-8"))
            if not verify_personal_package(package) or package["format_version"] not in {3, PERSONAL_V11_FORMAT_VERSION, PERSONAL_V12_FORMAT_VERSION, PERSONAL_V13_FORMAT_VERSION}:
                raise PersonalLifecycleError()
            bootstrap = json.loads((package_root / "bootstrap.json").read_text(encoding="utf-8"))
            envelope = PersonalKeyEnvelope(
                {
                    "format": "PMV1-KEY-ENVELOPE-V1",
                    "version": 1,
                    "vault_id": bootstrap["vault_id"],
                    "profile_id": bootstrap["profile_id"],
                    "profile_version": bootstrap["profile_version"],
                    "key_version": bootstrap["key_version"],
                    "key_state": "active",
                    "db_salt_hex": bootstrap["db_salt_hex"],
                    "backup_salt_hex": bootstrap["backup_salt_hex"],
                    "export_salt_hex": bootstrap["export_salt_hex"],
                    "manifest_salt_hex": bootstrap["manifest_salt_hex"],
                    "dpapi_vmk_hex": "00" * 1024,
                    "recovery": bootstrap["recovery"],
                }
            )
            vmk = envelope.unwrap_recovery(recovery_secret)
            key = self._db_key(vmk, envelope)
            candidate_id = secrets.token_hex(16)
            candidate = self._paths.staging / candidate_id / "vault.sqlite"
            candidate.parent.mkdir(parents=True, exist_ok=False)
            connection = _open(candidate, key.raw, create=True)
            try:
                restore_personal_package(package, connection)
                _verify_db(connection, envelope)
            finally:
                connection.close()
                key.clear()
                vmk.clear()
            # A second independent open is mandatory before reporting success.
            verification_vmk = envelope.unwrap_recovery(recovery_secret)
            verification_key = self._db_key(verification_vmk, envelope)
            verification = _open(candidate, verification_key.raw)
            try:
                _verify_db(verification, envelope)
            finally:
                verification.close()
                verification_key.clear()
                verification_vmk.clear()
            source_version = int(envelope.value["key_version"])
            active_version = int(self._active_envelope().value["key_version"])
            return {
                "candidate_id": candidate_id,
                "key_version": str(source_version),
                "verified": "RECOVERABLE",
                "created_at": str(bootstrap.get("created_at", "UNKNOWN_LEGACY_BACKUP")),
                "freshness": "CURRENT_GENERATION" if source_version == active_version else "HISTORICAL_GENERATION",
                "activation": "NOT_AUTOMATIC",
            }
        except Exception as exc:
            raise PersonalLifecycleError() from exc

    def create_owner_export(self, recovery_secret: str) -> dict[str, str]:
        self._guard.require()
        envelope = self._active_envelope()
        vmk = envelope.unwrap_recovery(recovery_secret)
        db_key = self._db_key(vmk, envelope)
        export_key = derive_domain_key(
            vmk, "export", bytes.fromhex(envelope.value["export_salt_hex"])
        )
        try:
            connection = _open(self._paths.vault, db_key.raw)
            try:
                _verify_db(connection, envelope)
                payload = _canonical(create_personal_package(connection))
            finally:
                connection.close()
            export_id = secrets.token_hex(16)
            nonce = secrets.token_bytes(12)
            metadata = {
                "format": "PMV1-OWNER-EXPORT-V1",
                "vault_id": envelope.value["vault_id"],
                "profile_id": envelope.value["profile_id"],
                "key_version": envelope.value["key_version"],
                "export_id": export_id,
                "audience": "OWNER_ONLY",
                "nonce_hex": nonce.hex(),
            }
            ciphertext = AESGCM(export_key.raw).encrypt(
                nonce, payload, b"PMV1-OWNER-EXPORT-V1|" + _canonical(metadata)
            )
            target = self._paths.exports / f"{export_id}.pmv1"
            _atomic_write(
                target, _canonical({"metadata": metadata, "ciphertext_hex": ciphertext.hex()})
            )
            return {"export_id": export_id, "audience": "OWNER_ONLY"}
        except Exception as exc:
            raise PersonalLifecycleError() from exc
        finally:
            db_key.clear()
            export_key.clear()
            vmk.clear()

    def delete_session(self, reflection: Any, session_id: str, confirmation: str) -> dict[str, Any]:
        self._guard.require()
        return cast(dict[str, Any], reflection.delete_session(session_id, confirmation))

    def _write_journal(
        self,
        envelope: PersonalKeyEnvelope,
        vmk: SensitiveBytes,
        stage: str,
        pending: PersonalKeyEnvelope,
        candidate: Path,
        previous: Path,
    ) -> None:
        if stage not in _JOURNAL_STAGES:
            raise PersonalLifecycleError()
        manifest = derive_domain_key(
            vmk, "manifest", bytes.fromhex(envelope.value["manifest_salt_hex"])
        )
        try:
            public = {
                "format": "PMV1-ROTATION-JOURNAL-V1",
                "version": 1,
                "vault_id": envelope.value["vault_id"],
                "profile_id": envelope.value["profile_id"],
                "profile_version": envelope.value["profile_version"],
                "from_key_version": envelope.value["key_version"],
                "to_key_version": pending.value["key_version"],
                "stage": stage,
                "created_at": datetime.now(UTC).isoformat(),
                "candidate_id": candidate.parent.name,
            }
            plain = {
                "pending_envelope": pending.value,
                "pending_envelope_sha256": hashlib.sha256(pending.canonical_bytes()).hexdigest(),
                "old_envelope_sha256": hashlib.sha256(envelope.canonical_bytes()).hexdigest(),
                "active_db_identity": {
                    "path": "vault.sqlite",
                    "vault_id": envelope.value["vault_id"],
                    "profile_id": envelope.value["profile_id"],
                },
                "candidate_db_relative_path": str(candidate.relative_to(self._paths.root)).replace(
                    "\\", "/"
                ),
                "previous_db_relative_path": str(previous.relative_to(self._paths.root)).replace(
                    "\\", "/"
                ),
                "candidate_db_sha256": hashlib.sha256(candidate.read_bytes()).hexdigest()
                if candidate.exists()
                else "",
                "candidate_schema_fingerprint": "v10",
            }
            nonce = secrets.token_bytes(12)
            ciphertext = AESGCM(manifest.raw).encrypt(
                nonce, _canonical(plain), b"PMV1-ROTATION-JOURNAL-V1|" + _canonical(public)
            )
            record = {
                **public,
                "auth_nonce_hex": nonce.hex(),
                "auth_ciphertext_hex": ciphertext.hex(),
            }
            if set(record) != _JOURNAL_FIELDS or len(_canonical(record)) > 64 * 1024:
                raise PersonalLifecycleError()
            _atomic_write(self._paths.rotation_journal, _canonical(record))
        finally:
            manifest.clear()

    def _publish_retained(
        self, envelope: PersonalKeyEnvelope, vmk: SensitiveBytes, *, retirement: str | None
    ) -> None:
        retained = (
            self._paths.retained_keys / f"key-envelope-v{envelope.value['key_version']}.pmv1.json"
        )
        if not retained.exists():
            envelope.write_new(retained)
        if (
            PersonalKeyEnvelope.parse(retained.read_bytes()).canonical_bytes()
            != envelope.canonical_bytes()
        ):
            raise PersonalLifecycleError()
        manifest = derive_domain_key(
            vmk, "manifest", bytes.fromhex(envelope.value["manifest_salt_hex"])
        )
        try:
            metadata = {
                "format": "PMV1-RETAINED-KEY-METADATA-V1",
                "version": 1,
                "vault_id": envelope.value["vault_id"],
                "profile_id": envelope.value["profile_id"],
                "key_version": envelope.value["key_version"],
                "retained_envelope_sha256": hashlib.sha256(envelope.canonical_bytes()).hexdigest(),
                "state": "prepared_for_retention" if retirement is None else "retained_for_read",
                "created_at": datetime.now(UTC).isoformat(),
                "active_from": None,
                "retired_for_write_at": retirement,
                "retained_for_read_until": None,
            }
            nonce = secrets.token_bytes(12)
            metadata["auth_nonce_hex"] = nonce.hex()
            metadata["auth_ciphertext_hex"] = (
                AESGCM(manifest.raw)
                .encrypt(nonce, b"", b"PMV1-RETAINED-KEY-METADATA-V1|" + _canonical(metadata))
                .hex()
            )
            _atomic_write(
                self._paths.retained_keys
                / f"key-v{envelope.value['key_version']}.pmv1.metadata.json",
                _canonical(metadata),
            )
        finally:
            manifest.clear()

    def rotate(
        self, recovery_secret: str, *, close_active: Callable[[], None] | None = None
    ) -> dict[str, str]:
        """Isolated SQLCipher N→N+1 re-encryption; never uses ``PRAGMA rekey``."""
        self._guard.require()
        old = self._active_envelope()
        old_vmk = old.unwrap_recovery(recovery_secret)
        old_key = self._db_key(old_vmk, old)
        pending: PersonalKeyEnvelope | None = None
        pending_vmk: SensitiveBytes | None = None
        candidate = self._paths.staging / secrets.token_hex(16) / "vault.sqlite"
        previous = self._paths.staging / candidate.parent.name / "previous-N.sqlite"
        try:
            pending, pending_vmk = PersonalKeyEnvelope.create(
                vault_id=old.value["vault_id"],
                profile_id=old.value["profile_id"],
                profile_version=old.value["profile_version"],
                recovery_secret=recovery_secret,
                key_version=int(old.value["key_version"]) + 1,
                os_wrapper=self._os_wrapper_factory(),
            )
            # The N+1 envelope is protected material but is not active until
            # after retained N has been published.  Its journal representation
            # therefore carries the accepted pending state.
            pending.value["key_state"] = "pending"
            candidate.parent.mkdir(parents=True, exist_ok=False)
            self._write_journal(old, old_vmk, "prepared", pending, candidate, previous)
            self._fault(RotationFaultPoint.AFTER_PREPARED)
            source = _open(self._paths.vault, old_key.raw)
            next_key = self._db_key(pending_vmk, pending)
            try:
                _verify_db(source, old)
                source.execute(
                    f"ATTACH DATABASE '{str(candidate).replace("'", "''")}' AS rotated KEY \"x'{next_key.raw.hex()}'\""
                )
                self._fault(RotationFaultPoint.DURING_EXPORT)
                source.execute("SELECT sqlcipher_export('rotated')")
                source.execute("DETACH DATABASE rotated")
            finally:
                source.close()
            probe = _open(candidate, next_key.raw)
            try:
                _verify_db(probe, pending)
            finally:
                probe.close()
            self._write_journal(old, old_vmk, "candidate_verified", pending, candidate, previous)
            self._fault(RotationFaultPoint.AFTER_CANDIDATE_VERIFIED)
            self._write_journal(old, old_vmk, "activation_started", pending, candidate, previous)
            self._fault(RotationFaultPoint.AFTER_ACTIVATION_STARTED)
            if close_active is not None:
                close_active()
            os.replace(self._paths.vault, previous)
            os.replace(candidate, self._paths.vault)
            self._fault(RotationFaultPoint.AFTER_DB_REPLACEMENT)
            probe = _open(self._paths.vault, next_key.raw)
            try:
                _verify_db(probe, pending)
            finally:
                probe.close()
            self._write_journal(old, old_vmk, "db_n_plus_1_verified", pending, candidate, previous)
            self._fault(RotationFaultPoint.AFTER_DB_N_PLUS_1_VERIFIED)
            self._fault(RotationFaultPoint.DURING_RETAINED_PUBLICATION)
            self._publish_retained(old, old_vmk, retirement=None)
            self._write_journal(old, old_vmk, "retained_n_published", pending, candidate, previous)
            self._fault(RotationFaultPoint.AFTER_RETAINED_N_PUBLISHED)
            promoted = dict(pending.value)
            promoted["key_state"] = "active"
            _atomic_write(self._paths.envelope, PersonalKeyEnvelope(promoted).canonical_bytes())
            # Reopen the promoted envelope using independent recovery before the
            # lifecycle metadata changes.
            check = PersonalKeyEnvelope.parse(self._paths.envelope.read_bytes()).unwrap_recovery(
                recovery_secret
            )
            check.clear()
            self._publish_retained(old, old_vmk, retirement=datetime.now(UTC).isoformat())
            self._write_journal(
                old, old_vmk, "envelope_n_plus_1_promoted", pending, candidate, previous
            )
            self._fault(RotationFaultPoint.AFTER_ENVELOPE_N_PLUS_1_PROMOTED)
            self._write_journal(old, old_vmk, "rotation_complete", pending, candidate, previous)
            self._fault(RotationFaultPoint.AFTER_ROTATION_COMPLETE)
            self._fault(RotationFaultPoint.BEFORE_JOURNAL_CLEANUP)
            self._paths.rotation_journal.unlink(missing_ok=True)
            previous.unlink(missing_ok=True)
            return {
                "from_key_version": str(old.value["key_version"]),
                "to_key_version": str(pending.value["key_version"]),
            }
        except Exception as exc:
            raise PersonalLifecycleError() from exc
        finally:
            old_key.clear()
            old_vmk.clear()
            if pending_vmk is not None:
                pending_vmk.clear()
            if "next_key" in locals():
                next_key.clear()
