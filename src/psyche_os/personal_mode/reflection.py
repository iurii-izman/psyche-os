"""Guarded Personal reflection composition; no renderer-controlled roots."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from psyche_os.application.reflection_sessions import ReflectionSessionService
from psyche_os.crypto.envelope import SensitiveBytes, derive_domain_key
from psyche_os.personal_mode.admission import PersonalAdmissionGuard
from psyche_os.personal_mode.runtime_profile import PersonalRuntimePaths
from psyche_os.personal_mode.schema import initialize_personal_v12


class PersonalReflectionService:
    """Lazy Personal store: admission happens before root, envelope, or DB access."""

    def __init__(
        self,
        paths: PersonalRuntimePaths,
        guard: PersonalAdmissionGuard,
        vmk_supplier: Callable[[], SensitiveBytes],
        *,
        db_salt: bytes | None = None,
    ) -> None:
        self._paths = paths
        self._guard = guard
        self._vmk_supplier = vmk_supplier
        self._db_salt = db_salt or (b"\0" * 32)
        self._service: ReflectionSessionService | None = None

    def _inner(self) -> ReflectionSessionService:
        self._guard.require()
        if self._service is None:
            vmk = self._vmk_supplier()
            try:
                key = derive_domain_key(vmk, "database", self._db_salt)
                raw = bytearray(key.raw)
                key.clear()
            finally:
                vmk.clear()

            def take_key() -> bytes:
                value = bytes(raw)
                for index in range(len(raw)):
                    raw[index] = 0
                return value

            self._service = ReflectionSessionService(
                self._paths.root,
                data_mode="real_personal",
                database_key_supplier=take_key,
                schema_version=12,
                schema_initializer=initialize_personal_v12,
                database_filename="vault.sqlite",
            )
        return self._service

    def close(self) -> None:
        if self._service is not None:
            self._service.close()
            self._service = None

    @property
    def connection(self) -> Any:
        self._guard.require()
        return self._inner().connection

    def __getattr__(self, name: str) -> Any:
        """Guard every existing reflection operation, including reads."""
        operation = getattr(self._inner(), name)
        if not callable(operation):
            return operation

        def guarded(*args: Any, **kwargs: Any) -> Any:
            self._guard.require()
            return operation(*args, **kwargs)

        return guarded
