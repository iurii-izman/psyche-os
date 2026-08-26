"""Slice-A trusted Personal setup and unlock composition."""

from __future__ import annotations

from collections.abc import Callable

from psyche_os.crypto.envelope import OSKeyWrapper, SensitiveBytes
from psyche_os.personal_mode.admission import PersonalAdmissionGuard
from psyche_os.personal_mode.key_envelope import PersonalKeyEnvelope
from psyche_os.personal_mode.integrity import verify_personal_vault
from psyche_os.personal_mode.lifecycle import PersonalLifecycleService
from psyche_os.personal_mode.reflection import PersonalReflectionService
from psyche_os.personal_mode.runtime_profile import PersonalRuntimePaths


class PersonalRuntimeError(Exception):
    code = "PERSONAL_RUNTIME_UNAVAILABLE"


class PersonalRuntime:
    """Only trusted composition can set up or unlock the fixed Personal root."""

    def __init__(
        self,
        paths: PersonalRuntimePaths,
        guard: PersonalAdmissionGuard,
        *,
        os_wrapper_factory: Callable[[], OSKeyWrapper] = OSKeyWrapper,
    ) -> None:
        self._paths = paths
        self._guard = guard
        self._os_wrapper_factory = os_wrapper_factory
        self._vmk: SensitiveBytes | None = None
        self._reflection: PersonalReflectionService | None = None

    def _clear(self) -> None:
        if self._reflection is not None:
            self._reflection.close()
            self._reflection = None
        if self._vmk is not None:
            self._vmk.clear()
            self._vmk = None

    def setup(self, recovery_secret: str) -> None:
        self._guard.require()
        if self._paths.envelope.exists() or self._paths.vault.exists():
            raise PersonalRuntimeError()
        try:
            envelope, vmk = PersonalKeyEnvelope.create(
                vault_id="personal_vault",
                profile_id="local_personal_evidence_reflection_windows_v1",
                profile_version="v1",
                recovery_secret=recovery_secret,
                os_wrapper=self._os_wrapper_factory(),
            )
            envelope.write_new(self._paths.envelope)
            self._vmk = vmk
            self._reflection = PersonalReflectionService(
                self._paths,
                self._guard,
                lambda: SensitiveBytes(vmk.raw),
                db_salt=bytes.fromhex(envelope.value["db_salt_hex"]),
            )
            # Setup reports success only once the newly persisted vault passes
            # the same canonical lifecycle oracle as every later boundary.
            verify_personal_vault(self._reflection.connection, envelope)
        except Exception as exc:
            self._clear()
            raise PersonalRuntimeError() from exc

    def unlock(self, recovery_secret: str) -> None:
        self._guard.require()
        try:
            # A fresh runtime must not expose an active database while a durable
            # rotation transition remains unresolved.  In particular, an N+1
            # active envelope never authorizes bypassing a stale N-authenticated
            # journal: reconciliation verifies that journal through retained N
            # before any Personal connection is opened.
            if self._paths.rotation_journal.exists():
                self.lifecycle.reconcile_rotation(recovery_secret)
            envelope = PersonalKeyEnvelope.parse(self._paths.envelope.read_bytes())
            vmk = envelope.unwrap_recovery(recovery_secret)
            self._clear()
            self._vmk = vmk
            self._reflection = PersonalReflectionService(
                self._paths,
                self._guard,
                lambda: SensitiveBytes(vmk.raw),
                db_salt=bytes.fromhex(envelope.value["db_salt_hex"]),
            )
            verify_personal_vault(self._reflection.connection, envelope)
        except Exception as exc:
            self._clear()
            raise PersonalRuntimeError() from exc

    @property
    def reflection(self) -> PersonalReflectionService:
        self._guard.require()
        if self._reflection is None:
            raise PersonalRuntimeError()
        return self._reflection

    def lock(self) -> None:
        self._clear()
        self._guard.lock()

    def rotate(self, recovery_secret: str) -> dict[str, str]:
        """Rotate only through the isolated lifecycle protocol, then relock."""
        result = self.lifecycle.rotate(recovery_secret, close_active=self._clear)
        # The old in-memory VMK must not survive active-envelope promotion.
        self._clear()
        return result

    def reconcile_rotation(self, recovery_secret: str) -> str:
        """Trusted restart dispatch; journal reconciliation stays guarded."""
        self._clear()
        return self.lifecycle.reconcile_rotation(recovery_secret)

    def destroy_retained(self, key_version: int) -> dict[str, str]:
        return self.lifecycle.destroy_retained(key_version)

    @property
    def lifecycle(self) -> PersonalLifecycleService:
        """Guarded backup/restore/export/deletion boundary for Personal bytes."""
        self._guard.require()
        return PersonalLifecycleService(
            self._paths, self._guard, os_wrapper_factory=self._os_wrapper_factory
        )
