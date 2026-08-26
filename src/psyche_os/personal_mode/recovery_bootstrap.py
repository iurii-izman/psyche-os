"""Bounded authenticated PMV1 recovery bootstrap for isolated backups."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import UTC, datetime
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from psyche_os.crypto.envelope import derive_domain_key
from psyche_os.personal_mode.key_envelope import PersonalKeyEnvelope, _no_duplicates

_FIELDS = frozenset(
    {
        "format",
        "version",
        "vault_id",
        "profile_id",
        "profile_version",
        "key_version",
        "db_salt_hex",
        "backup_salt_hex",
        "export_salt_hex",
        "manifest_salt_hex",
        "recovery",
        "backup_id",
        "payload_nonce_hex",
        "payload_length",
        "payload_sha256_hex",
        "bootstrap_auth",
    }
)
_V2_FIELDS = _FIELDS | {"created_at"}
_AUTH_FIELDS = frozenset({"nonce_hex", "ciphertext_tag_hex"})


class RecoveryBootstrapError(Exception):
    code = "RECOVERY_BOOTSTRAP_INVALID"


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


def _parse(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or not raw or len(raw) > 32 * 1024:
        raise RecoveryBootstrapError()
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
    except Exception as exc:
        raise RecoveryBootstrapError() from exc
    if (
        not isinstance(value, dict)
        or set(value) not in {_FIELDS, _V2_FIELDS}
        or value.get("format") != "PMV1-RECOVERY-BOOTSTRAP-V1"
        or value.get("version") not in {1, 2}
        or (value.get("version") == 1 and set(value) != _FIELDS)
        or (value.get("version") == 2 and set(value) != _V2_FIELDS)
    ):
        raise RecoveryBootstrapError()
    if (
        not isinstance(value.get("payload_length"), int)
        or isinstance(value["payload_length"], bool)
        or not 1 <= value["payload_length"] <= 512 * 1024 * 1024
    ):
        raise RecoveryBootstrapError()
    auth = value.get("bootstrap_auth")
    if not isinstance(auth, dict) or set(auth) != _AUTH_FIELDS:
        raise RecoveryBootstrapError()
    try:
        if value["version"] == 2:
            datetime.fromisoformat(value["created_at"])
        PersonalKeyEnvelope(
            {
                "format": "PMV1-KEY-ENVELOPE-V1",
                "version": 1,
                "vault_id": value["vault_id"],
                "profile_id": value["profile_id"],
                "profile_version": value["profile_version"],
                "key_version": value["key_version"],
                "key_state": "active",
                "db_salt_hex": value["db_salt_hex"],
                "backup_salt_hex": value["backup_salt_hex"],
                "export_salt_hex": value["export_salt_hex"],
                "manifest_salt_hex": value["manifest_salt_hex"],
                "dpapi_vmk_hex": "00" * 1024,
                "recovery": value["recovery"],
            }
        )
        if not isinstance(value["backup_id"], str) or not value["backup_id"]:
            raise ValueError
        for name, length in (("payload_nonce_hex", 24), ("payload_sha256_hex", 64)):
            if (
                not isinstance(value[name], str)
                or len(value[name]) != length
                or any(c not in "0123456789abcdef" for c in value[name])
            ):
                raise ValueError
        if (
            not isinstance(auth["nonce_hex"], str)
            or len(auth["nonce_hex"]) != 24
            or not isinstance(auth["ciphertext_tag_hex"], str)
            or len(auth["ciphertext_tag_hex"]) != 32
        ):
            raise ValueError
    except Exception as exc:
        raise RecoveryBootstrapError() from exc
    return value


def create_bootstrap(
    envelope: PersonalKeyEnvelope, recovery_secret: str, payload: bytes, backup_id: str
) -> tuple[bytes, bytes]:
    """Create encrypted payload and authenticated bounded bootstrap."""
    if not payload or not isinstance(backup_id, str) or not backup_id:
        raise RecoveryBootstrapError()
    value = envelope.value
    vmk = envelope.unwrap_recovery(recovery_secret)
    try:
        backup = derive_domain_key(vmk, "backup", bytes.fromhex(value["backup_salt_hex"]))
        manifest = derive_domain_key(vmk, "manifest", bytes.fromhex(value["manifest_salt_hex"]))
        nonce = secrets.token_bytes(12)
        ciphertext = AESGCM(backup.raw).encrypt(nonce, payload, backup_id.encode())
        bootstrap: dict[str, Any] = {
            key: value[key]
            for key in (
                "vault_id",
                "profile_id",
                "profile_version",
                "key_version",
                "db_salt_hex",
                "backup_salt_hex",
                "export_salt_hex",
                "manifest_salt_hex",
                "recovery",
            )
        }
        bootstrap.update(
            {
                "format": "PMV1-RECOVERY-BOOTSTRAP-V1",
                "version": 2,
                "backup_id": backup_id,
                "created_at": datetime.now(UTC).isoformat(),
                "payload_nonce_hex": nonce.hex(),
                "payload_length": len(ciphertext),
                "payload_sha256_hex": hashlib.sha256(ciphertext).hexdigest(),
            }
        )
        aad = b"PMV1-RECOVERY-BOOTSTRAP-V1|" + _canonical(bootstrap)
        auth_nonce = secrets.token_bytes(12)
        bootstrap["bootstrap_auth"] = {
            "nonce_hex": auth_nonce.hex(),
            "ciphertext_tag_hex": AESGCM(manifest.raw).encrypt(auth_nonce, b"", aad).hex(),
        }
        return _canonical(bootstrap), ciphertext
    except Exception as exc:
        raise RecoveryBootstrapError() from exc
    finally:
        vmk.clear()
        if "backup" in locals():
            backup.clear()
        if "manifest" in locals():
            manifest.clear()


def recover_bootstrap(raw: bytes, recovery_secret: str, payload: bytes) -> bytes:
    """Authenticate headers before decrypting any payload bytes."""
    value = _parse(raw)
    if (
        len(payload) != value["payload_length"]
        or hashlib.sha256(payload).hexdigest() != value["payload_sha256_hex"]
    ):
        raise RecoveryBootstrapError()
    try:
        envelope = PersonalKeyEnvelope(
            {
                "format": "PMV1-KEY-ENVELOPE-V1",
                "version": 1,
                "vault_id": value["vault_id"],
                "profile_id": value["profile_id"],
                "profile_version": value["profile_version"],
                "key_version": value["key_version"],
                "key_state": "active",
                "db_salt_hex": value["db_salt_hex"],
                "backup_salt_hex": value["backup_salt_hex"],
                "export_salt_hex": value["export_salt_hex"],
                "manifest_salt_hex": value["manifest_salt_hex"],
                "dpapi_vmk_hex": "00" * 1024,
                "recovery": value["recovery"],
            }
        )
        vmk = envelope.unwrap_recovery(recovery_secret)
        manifest = derive_domain_key(vmk, "manifest", bytes.fromhex(value["manifest_salt_hex"]))
        aad_value = {key: val for key, val in value.items() if key != "bootstrap_auth"}
        auth = value["bootstrap_auth"]
        AESGCM(manifest.raw).decrypt(
            bytes.fromhex(auth["nonce_hex"]),
            bytes.fromhex(auth["ciphertext_tag_hex"]),
            b"PMV1-RECOVERY-BOOTSTRAP-V1|" + _canonical(aad_value),
        )
        backup = derive_domain_key(vmk, "backup", bytes.fromhex(value["backup_salt_hex"]))
        return AESGCM(backup.raw).decrypt(
            bytes.fromhex(value["payload_nonce_hex"]), payload, value["backup_id"].encode()
        )
    except Exception as exc:
        raise RecoveryBootstrapError() from exc
    finally:
        if "vmk" in locals():
            vmk.clear()
        if "manifest" in locals():
            manifest.clear()
        if "backup" in locals():
            backup.clear()
