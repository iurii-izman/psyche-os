"""Strict PMV1 key-envelope serialization and first-setup primitive."""

from __future__ import annotations

from contextlib import suppress
import hmac
import json
import os
from pathlib import Path
import re
import secrets
from typing import Any

from psyche_os.crypto.envelope import (
    OSKeyWrapper,
    RecoveryWrapHeader,
    RecoveryWrapper,
    SensitiveBytes,
    generate_vmk,
)

_IDS = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_FIELDS = frozenset(
    {
        "format",
        "version",
        "vault_id",
        "profile_id",
        "profile_version",
        "key_version",
        "key_state",
        "db_salt_hex",
        "backup_salt_hex",
        "export_salt_hex",
        "manifest_salt_hex",
        "dpapi_vmk_hex",
        "recovery",
    }
)
_RECOVERY_FIELDS = frozenset(
    {
        "version",
        "salt_hex",
        "time_cost",
        "memory_cost",
        "parallelism",
        "hash_len",
        "wrapped_key_hex",
        "vault_id",
    }
)


class EnvelopeError(Exception):
    code = "KEY_ENVELOPE_INVALID"


def validate_new_recovery_secret(secret: Any) -> str:
    """Small deterministic floor for *new* manual recovery secrets.

    Existing serialized envelopes are intentionally never revalidated against
    this policy, so an upgrade neither locks an owner out nor rewrites a key.
    """
    if not isinstance(secret, str) or len(secret) < 16 or len(secret) > 256:
        raise EnvelopeError()
    classes = sum((any(c.islower() for c in secret), any(c.isupper() for c in secret), any(c.isdigit() for c in secret), any(not c.isalnum() for c in secret)))
    if classes < 2 or len(set(secret)) < 6:
        raise EnvelopeError()
    return secret


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeError()
        result[key] = value
    return result


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not _IDS.fullmatch(value):
        raise EnvelopeError()
    return value


def _hex(value: Any) -> str:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise EnvelopeError()
    return value


class PersonalKeyEnvelope:
    """Exactly one active protected VMK identity.

    This object never writes or replaces itself during parsing failures.
    Pending rotation envelopes are deliberately out of scope and belong solely
    to the authenticated rotation journal.
    """

    def __init__(self, value: dict[str, Any]) -> None:
        self.value = self._validate(value)

    @staticmethod
    def _validate(value: Any, *, pending: bool = False) -> dict[str, Any]:
        if not isinstance(value, dict) or set(value) != _FIELDS:
            raise EnvelopeError()
        if value["format"] != "PMV1-KEY-ENVELOPE-V1" or value["version"] != 1:
            raise EnvelopeError()
        for field in ("vault_id", "profile_id", "profile_version"):
            _identifier(value[field])
        if (
            not isinstance(value["key_version"], int)
            or isinstance(value["key_version"], bool)
            or not 1 <= value["key_version"] <= 2**31 - 1
        ):
            raise EnvelopeError()
        if value["key_state"] != ("pending" if pending else "active"):
            raise EnvelopeError()
        for field in ("db_salt_hex", "backup_salt_hex", "export_salt_hex", "manifest_salt_hex"):
            _hex(value[field])
        dpapi = value["dpapi_vmk_hex"]
        # DPAPI ciphertext length is provider-dependent; a 32-byte VMK has no
        # portable 1 KiB lower bound.  Preserve strict bounded hexadecimal
        # parsing without rejecting a valid current-user DPAPI envelope.
        if (
            not isinstance(dpapi, str)
            or not re.fullmatch(r"[0-9a-f]+", dpapi)
            or not 16 <= len(dpapi) // 2 <= 16384
        ):
            raise EnvelopeError()
        recovery = value["recovery"]
        if not isinstance(recovery, dict) or set(recovery) != _RECOVERY_FIELDS:
            raise EnvelopeError()
        if (
            not isinstance(recovery.get("time_cost"), int)
            or not 1 <= recovery["time_cost"] <= 10
            or not isinstance(recovery.get("memory_cost"), int)
            or not 8192 <= recovery["memory_cost"] <= 262144
            or not isinstance(recovery.get("parallelism"), int)
            or not 1 <= recovery["parallelism"] <= 8
            or recovery.get("hash_len") != 32
        ):
            raise EnvelopeError()
        try:
            header = RecoveryWrapHeader.from_dict(recovery)
        except Exception as exc:
            raise EnvelopeError() from exc
        if (
            header.vault_id != value["vault_id"]
            or len(header.salt) != 32
            or not 28 <= len(header.wrapped_key) <= 128
        ):
            raise EnvelopeError()
        return dict(value)

    @classmethod
    def parse(cls, raw: bytes) -> PersonalKeyEnvelope:
        if not isinstance(raw, bytes) or not raw or len(raw) > 64 * 1024:
            raise EnvelopeError()
        try:
            value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except Exception as exc:
            raise EnvelopeError() from exc
        return cls(value)

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode("utf-8")

    def unwrap_recovery(
        self, secret: str, wrapper: RecoveryWrapper | None = None
    ) -> SensitiveBytes:
        recovery = RecoveryWrapHeader.from_dict(self.value["recovery"])
        try:
            vmk = (wrapper or RecoveryWrapper()).unwrap(recovery, secret)
        except Exception as exc:
            raise EnvelopeError() from exc
        if len(vmk) != 32:
            vmk.clear()
            raise EnvelopeError()
        return vmk

    @classmethod
    def create(
        cls,
        *,
        vault_id: str,
        profile_id: str,
        profile_version: str,
        recovery_secret: str,
        key_version: int = 1,
        os_wrapper: OSKeyWrapper | None = None,
        recovery_wrapper: RecoveryWrapper | None = None,
    ) -> tuple[PersonalKeyEnvelope, SensitiveBytes]:
        _identifier(vault_id)
        _identifier(profile_id)
        _identifier(profile_version)
        validate_new_recovery_secret(recovery_secret)
        vmk = generate_vmk()
        try:
            os_wrap = os_wrapper or OSKeyWrapper()
            recovery_wrap = recovery_wrapper or RecoveryWrapper()
            if not os_wrap.available or not recovery_wrap.available:
                raise EnvelopeError()
            dpapi = os_wrap.protect(vmk.raw, "PSYCHE OS Personal VMK")
            header = recovery_wrap.wrap(vmk, recovery_secret, vault_id)
            value = {
                "format": "PMV1-KEY-ENVELOPE-V1",
                "version": 1,
                "vault_id": vault_id,
                "profile_id": profile_id,
                "profile_version": profile_version,
                "key_version": key_version,
                "key_state": "active",
                "db_salt_hex": secrets.token_bytes(32).hex(),
                "backup_salt_hex": secrets.token_bytes(32).hex(),
                "export_salt_hex": secrets.token_bytes(32).hex(),
                "manifest_salt_hex": secrets.token_bytes(32).hex(),
                "dpapi_vmk_hex": dpapi.hex(),
                "recovery": header.to_dict(),
            }
            envelope = cls(value)
            # Use a new RecoveryWrapper rather than the wrapping instance.  This
            # proves that the serialized recovery header is recoverable through
            # an independent recovery path before setup can create Personal data.
            verified = envelope.unwrap_recovery(recovery_secret)
            try:
                if not hmac.compare_digest(verified.raw, vmk.raw):
                    raise EnvelopeError()
            finally:
                verified.clear()
            return envelope, vmk
        except Exception:
            vmk.clear()
            raise

    def write_new(self, path: Path) -> None:
        """Publish only a new envelope; replacement is rotation-owned."""
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(f".{path.name}.{secrets.token_hex(16)}.tmp")
        try:
            with temporary.open("xb") as stream:
                stream.write(self.canonical_bytes())
                stream.flush()
                os.fsync(stream.fileno())
            # A hard-link publication is no-replace: an existing envelope wins
            # rather than being overwritten. Both paths are same-volume siblings.
            os.link(temporary, path)
            self.parse(path.read_bytes())
            temporary.unlink()
        except Exception as exc:
            with suppress(OSError):
                temporary.unlink(missing_ok=True)
            raise EnvelopeError() from exc
