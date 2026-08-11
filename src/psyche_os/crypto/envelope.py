"""Cryptographic layer — key envelopes, OS wrap, recovery wrap, and blob AEAD.

Implements PS-04–PS-06 and ADR-008:
- Random 256-bit Vault Master Key from CSPRNG
- Domain-separated keys via HKDF-SHA256
- OS-protected convenience wrap (Windows DPAPI)
- Independent Argon2id recovery wrap
- Versioned per-object AEAD envelope with independent data keys
- Key lifecycle and rotation states
- Secret input outside argv/env/logs

Algorithm profile (F0):
  - VMK:           CSPRNG 256-bit (secrets.token_bytes)
  - Domain KDF:    HKDF-SHA256, 32-byte salt, domain-specific info labels
  - OS wrap:       Windows DPAPI (CryptProtectData with CRYPTPROTECT_UI_FORBIDDEN, current-user only)
  - Recovery wrap: Argon2id (time_cost=3, memory_cost=65536, parallelism=4, hash_len=32)
  - Blob AEAD:     AES-256-GCM, 12-byte random nonce, versioned AAD
  - Data key wrap: AES-256-GCM, unique nonce per wrap
  - Envelope AAD:  magic | version | vault_id | blob_id | key_version | content_len

Residual risks (documented per PS-04):
  - Python cannot guarantee memory zeroization (best-effort only)
  - Unlocked same-user endpoint is a documented residual risk (TM-03)
  - OS key wrapping is tied to the current Windows user profile
  - Loss of both OS wrapping context and recovery secret means total data loss
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass, field
from enum import Enum
import secrets
from typing import Protocol

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from psyche_os.domain.ids import BlobId, VaultId

# ---------------------------------------------------------------------------
# Key states
# ---------------------------------------------------------------------------


class KeyState(str, Enum):
    GENERATED = "generated"
    ACTIVE = "active"
    ROTATION_PENDING = "rotation_pending"
    RETIRED_FOR_WRITE = "retired_for_write"
    RETAINED_FOR_READ = "retained_for_read"
    DESTROYED = "destroyed"


# ---------------------------------------------------------------------------
# Key material — best-effort zeroization
# ---------------------------------------------------------------------------


class SensitiveBytes:
    """Holder for sensitive key material with best-effort clearing.

    Python cannot guarantee zeroization, but we clear immediately on del.
    This is a documented residual risk per PS-04.
    """

    def __init__(self, data: bytes) -> None:
        self._data = bytearray(data)

    @property
    def raw(self) -> bytes:
        return bytes(self._data)

    def clear(self) -> None:
        for i in range(len(self._data)):
            self._data[i] = 0

    def __del__(self) -> None:
        self.clear()

    def __len__(self) -> int:
        return len(self._data)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SensitiveBytes):
            return bytes(self._data) == bytes(other._data)
        return False


def generate_vmk() -> SensitiveBytes:
    """Generate a random 256-bit Vault Master Key using CSPRNG."""
    return SensitiveBytes(secrets.token_bytes(32))


# ---------------------------------------------------------------------------
# Domain-separated key derivation (HKDF-SHA256)
# ---------------------------------------------------------------------------

DOMAIN_LABELS = {
    "database": b"psyche-os-v1-database-key",
    "blob": b"psyche-os-v1-blob-key",
    "manifest": b"psyche-os-v1-manifest-key",
    "blob_envelope": b"psyche-os-v1-blob-envelope-key",
    "backup": b"psyche-os-v1-backup-key",
    "export": b"psyche-os-v1-export-key",
}


def derive_domain_key(
    vmk: SensitiveBytes, domain: str, salt: bytes | None = None
) -> SensitiveBytes:
    """Derive a domain-specific 256-bit key from the VMK using HKDF-SHA256.

    Algorithm: HKDF-SHA256 (RFC 5869)
    - Salt: 32-byte (all-zero default, or per-vault random)
    - Info: domain-specific label from DOMAIN_LABELS
    - Output: 32 bytes (256-bit)
    """
    if domain not in DOMAIN_LABELS:
        raise ValueError(f"Unknown key domain: {domain}")
    if salt is None:
        salt = b"\x00" * 32
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        info=DOMAIN_LABELS[domain],
    )
    derived = hkdf.derive(vmk.raw)
    return SensitiveBytes(derived)


# ---------------------------------------------------------------------------
# Blob AEAD envelope — per-object independent data key
# ---------------------------------------------------------------------------

ENVELOPE_VERSION = 1
ENVELOPE_MAGIC = b"PSYCHE-BLOB-V1"
DATA_KEY_WRAP_VERSION = 1
DATA_KEY_LENGTH = 32  # AES-256


@dataclass(frozen=True, slots=True)
class BlobEnvelope:
    """Independently authenticated per-object encrypted envelope.

    Each blob gets its own random 256-bit data key, wrapped under the
    blob-envelope domain key. This ensures unique key material per object.

    AAD includes: magic, envelope version, vault ID, blob ID,
    key version, content length.

    Fields:
      blob_id: Opaque blob identifier
      vault_id: Owning vault
      ciphertext: AES-256-GCM encrypted plaintext
      nonce: 12-byte random nonce
      wrapped_data_key: Data key encrypted under blob envelope key
      data_key_nonce: 12-byte nonce for data key wrap
      key_version: Envelope key version used for wrapping
      envelope_version: Envelope format version
    """

    blob_id: BlobId
    vault_id: VaultId
    ciphertext: bytes
    nonce: bytes  # 12 bytes for AES-256-GCM
    wrapped_data_key: bytes = b""  # AES-256-GCM encrypted data key
    data_key_nonce: bytes = b""  # 12-byte nonce for data key wrap
    key_version: int = 1
    envelope_version: int = ENVELOPE_VERSION

    @property
    def aad(self) -> bytes:
        """Build authenticated associated data.

        Format: magic | version | vault_id | blob_id | key_version | ciphertext_len
        """
        return b"|".join(
            [
                ENVELOPE_MAGIC,
                str(self.envelope_version).encode(),
                str(self.vault_id).encode(),
                str(self.blob_id).encode(),
                str(self.key_version).encode(),
                str(len(self.ciphertext)).encode(),
            ]
        )

    def verify_aad(self, other_aad: bytes) -> bool:
        """Verify AAD matches expected."""
        return self.aad == other_aad


class BlobAEAD:
    """Encrypt/decrypt blobs with per-object independent data keys.

    Algorithm: AES-256-GCM for both content encryption and data key wrapping.
    Each blob gets a fresh random 256-bit data key.
    The data key is wrapped under the blob-envelope domain key.
    """

    def __init__(self, blob_envelope_key: SensitiveBytes) -> None:
        self._key = blob_envelope_key
        self._wrap_aead = AESGCM(self._key.raw)

    def encrypt(self, plaintext: bytes, blob_id: BlobId, vault_id: VaultId) -> BlobEnvelope:
        """Encrypt plaintext with a fresh random data key, wrap under envelope key.

        Steps:
        1. Generate random 256-bit per-object data key
        2. Encrypt plaintext under data key with AES-256-GCM
        3. Wrap data key under blob-envelope domain key with AES-256-GCM
        """
        # 1. Generate per-object data key
        data_key = secrets.token_bytes(DATA_KEY_LENGTH)
        data_aead = AESGCM(data_key)

        # 2. Encrypt content under data key
        content_nonce = secrets.token_bytes(12)

        # Pre-compute AAD for content encryption
        aad_data = b"|".join(
            [
                ENVELOPE_MAGIC,
                str(ENVELOPE_VERSION).encode(),
                str(vault_id).encode(),
                str(blob_id).encode(),
                b"1",  # key_version
                str(len(plaintext) + 16).encode(),  # GCM tag = 16 bytes
            ]
        )
        ciphertext = data_aead.encrypt(content_nonce, plaintext, aad_data)

        # 3. Wrap data key under blob-envelope domain key
        wrap_nonce = secrets.token_bytes(12)
        wrap_aad = b"|".join(
            [
                b"PSYCHE-DATAKEY-WRAP-V1",
                str(vault_id).encode(),
                str(blob_id).encode(),
            ]
        )
        wrapped_data_key = self._wrap_aead.encrypt(wrap_nonce, data_key, wrap_aad)

        # 4. Clear data key
        for i in range(len(data_key)):
            data_key = data_key[:i] + b"\x00" + data_key[i + 1 :]

        return BlobEnvelope(
            blob_id=blob_id,
            vault_id=vault_id,
            ciphertext=ciphertext,
            nonce=content_nonce,
            wrapped_data_key=wrapped_data_key,
            data_key_nonce=wrap_nonce,
            key_version=1,
            envelope_version=ENVELOPE_VERSION,
        )

    def decrypt(self, envelope: BlobEnvelope) -> bytes:
        """Decrypt and authenticate blob envelope. Raises on tamper.

        Steps:
        1. Unwrap the data key using the blob-envelope domain key
        2. Decrypt content using the unwrapped data key
        """
        # 1. Unwrap data key
        wrap_aad = b"|".join(
            [
                b"PSYCHE-DATAKEY-WRAP-V1",
                str(envelope.vault_id).encode(),
                str(envelope.blob_id).encode(),
            ]
        )
        try:
            data_key = self._wrap_aead.decrypt(
                envelope.data_key_nonce,
                envelope.wrapped_data_key,
                wrap_aad,
            )
        except Exception:
            raise ValueError("Data key unwrap failed — tampered or corrupted envelope")

        # 2. Decrypt content under data key
        try:
            data_aead = AESGCM(data_key)
            plaintext = data_aead.decrypt(
                envelope.nonce,
                envelope.ciphertext,
                envelope.aad,
            )
        finally:
            # Best-effort clear data key
            for i in range(len(data_key)):
                data_key = data_key[:i] + b"\x00" + data_key[i + 1 :]

        return plaintext

    @staticmethod
    def decrypt_with_key(
        key: SensitiveBytes,
        envelope: BlobEnvelope,
    ) -> bytes:
        """Decrypt with an explicit key (for recovery scenarios).

        Uses the provided key as the blob-envelope domain key to unwrap
        the per-object data key, then decrypts content.
        """
        wrap_aead = AESGCM(key.raw)
        wrap_aad = b"|".join(
            [
                b"PSYCHE-DATAKEY-WRAP-V1",
                str(envelope.vault_id).encode(),
                str(envelope.blob_id).encode(),
            ]
        )
        try:
            data_key = wrap_aead.decrypt(
                envelope.data_key_nonce,
                envelope.wrapped_data_key,
                wrap_aad,
            )
        except Exception:
            raise ValueError("Data key unwrap failed with provided key")

        try:
            data_aead = AESGCM(data_key)
            return data_aead.decrypt(envelope.nonce, envelope.ciphertext, envelope.aad)
        finally:
            for i in range(len(data_key)):
                data_key = data_key[:i] + b"\x00" + data_key[i + 1 :]


# ---------------------------------------------------------------------------
# OS key wrapping — Windows DPAPI
# ---------------------------------------------------------------------------


class OSKeyWrapError(Exception):
    """Raised when OS key wrapping fails."""


class OSKeyWrapper:
    """Protect/unprotect data using Windows DPAPI (CryptProtectData / CryptUnprotectData).

    Algorithm: Windows DPAPI with CRYPTPROTECT_LOCAL_MACHINE flag.
    The key is tied to the current Windows user profile.
    No custom entropy blob is provided.

    Residual risk: An attacker operating as the unlocked Windows user
    can unprotect the VMK. This is documented per TM-03.
    """

    def __init__(self) -> None:
        self._available = False
        try:
            self._crypt32 = ctypes.windll.crypt32
            self._kernel32 = ctypes.windll.kernel32
            self._available = True
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def protect(self, data: bytes, description: str = "") -> bytes:
        """Encrypt data under the current user's DPAPI key.

        Uses CRYPTPROTECT_UI_FORBIDDEN only — key is scoped to the
        current Windows user profile. Machine-wide access is NOT used.
        No entropy blob is provided.
        """
        if not self._available:
            raise OSKeyWrapError("Windows DPAPI not available on this platform")

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

        data_in = DATA_BLOB()
        data_in.cbData = len(data)
        data_in.pbData = ctypes.cast(
            ctypes.create_string_buffer(data, len(data)),
            ctypes.POINTER(ctypes.c_ubyte),
        )

        data_out = DATA_BLOB()

        CRYPTPROTECT_UI_FORBIDDEN = 0x1

        if not self._crypt32.CryptProtectData(
            ctypes.byref(data_in),
            description.encode("utf-8") if description else None,
            None,  # entropy
            None,  # reserved
            None,  # prompt struct
            CRYPTPROTECT_UI_FORBIDDEN,  # current-user scope only, no machine-wide access
            ctypes.byref(data_out),
        ):
            raise OSKeyWrapError("CryptProtectData failed")

        result = ctypes.string_at(data_out.pbData, data_out.cbData)
        self._kernel32.LocalFree(data_out.pbData)
        return result

    def unprotect(self, protected_data: bytes) -> bytes:
        """Decrypt data protected by DPAPI.

        Only succeeds for the same Windows user that protected the data.
        """
        if not self._available:
            raise OSKeyWrapError("Windows DPAPI not available on this platform")

        class DATA_BLOB(ctypes.Structure):
            _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_ubyte))]

        data_in = DATA_BLOB()
        data_in.cbData = len(protected_data)
        data_in.pbData = ctypes.cast(
            ctypes.create_string_buffer(protected_data, len(protected_data)),
            ctypes.POINTER(ctypes.c_ubyte),
        )

        data_out = DATA_BLOB()

        result_code = self._crypt32.CryptUnprotectData(
            ctypes.byref(data_in),
            None,  # description out
            None,  # entropy
            None,  # reserved
            None,  # prompt struct
            0,  # flags
            ctypes.byref(data_out),
        )

        if not result_code:
            raise OSKeyWrapError("CryptUnprotectData failed — wrong user or corrupted data")

        result = ctypes.string_at(data_out.pbData, data_out.cbData)
        self._kernel32.LocalFree(data_out.pbData)
        return result


# ---------------------------------------------------------------------------
# Independent recovery wrapping — Argon2id
# ---------------------------------------------------------------------------

RECOVERY_WRAP_VERSION = 1
RECOVERY_WRAP_MAGIC = b"PSYCHE-RECOVERY-V1"

# Argon2id parameters (bounded, documented per PS-05):
#   time_cost=3 (iterations) — min 1, max 10
#   memory_cost=65536 (64 MiB) — min 8192, max 262144
#   parallelism=4 — min 1, max 8
#   hash_len=32 (256-bit output) — fixed
#   salt=32 random bytes per vault
# These are fixed for F0; a future version may expose tuning.

# Conservative parameter bounds — prevents DoS via excessive KDF work
_ARAGON2_TIME_COST_MIN = 1
_ARAGON2_TIME_COST_MAX = 10
_ARAGON2_MEMORY_COST_MIN = 8192  # 8 MiB
_ARAGON2_MEMORY_COST_MAX = 262144  # 256 MiB
_ARAGON2_PARALLELISM_MIN = 1
_ARAGON2_PARALLELISM_MAX = 8
_ARAGON2_HASH_LEN = 32


def _validate_argon2_params(
    time_cost: int, memory_cost: int, parallelism: int, hash_len: int
) -> None:
    """Validate Argon2 parameters are within conservative bounds before allocation/KDF work."""
    if not (_ARAGON2_TIME_COST_MIN <= time_cost <= _ARAGON2_TIME_COST_MAX):
        raise ValueError(
            f"Argon2 time_cost {time_cost} outside bounds "
            f"[{_ARAGON2_TIME_COST_MIN}, {_ARAGON2_TIME_COST_MAX}]"
        )
    if not (_ARAGON2_MEMORY_COST_MIN <= memory_cost <= _ARAGON2_MEMORY_COST_MAX):
        raise ValueError(
            f"Argon2 memory_cost {memory_cost} outside bounds "
            f"[{_ARAGON2_MEMORY_COST_MIN}, {_ARAGON2_MEMORY_COST_MAX}]"
        )
    if not (_ARAGON2_PARALLELISM_MIN <= parallelism <= _ARAGON2_PARALLELISM_MAX):
        raise ValueError(
            f"Argon2 parallelism {parallelism} outside bounds "
            f"[{_ARAGON2_PARALLELISM_MIN}, {_ARAGON2_PARALLELISM_MAX}]"
        )
    if hash_len != _ARAGON2_HASH_LEN:
        raise ValueError(f"Argon2 hash_len must be {_ARAGON2_HASH_LEN}, got {hash_len}")


@dataclass(frozen=True, slots=True)
class RecoveryWrapHeader:
    """Argon2id parameters and wrapped VMK, stored with the vault.

    All parameters are explicit and bounded. The header is stored
    alongside (not inside) the encrypted database for recovery.
    """

    version: int = RECOVERY_WRAP_VERSION
    salt: bytes = field(default_factory=lambda: secrets.token_bytes(32))
    time_cost: int = 3  # Argon2id iterations
    memory_cost: int = 65536  # 64 MiB
    parallelism: int = 4
    hash_len: int = 32
    wrapped_key: bytes = b""  # nonce (12) + AES-GCM ciphertext
    vault_id: str = ""

    def to_dict(self) -> dict:
        """Serialize to dict for JSON storage."""
        return {
            "version": self.version,
            "salt_hex": self.salt.hex(),
            "time_cost": self.time_cost,
            "memory_cost": self.memory_cost,
            "parallelism": self.parallelism,
            "hash_len": self.hash_len,
            "wrapped_key_hex": self.wrapped_key.hex(),
            "vault_id": self.vault_id,
        }

    @classmethod
    def from_dict(cls, d: dict) -> RecoveryWrapHeader:
        """Deserialize from dict."""
        return cls(
            version=d.get("version", RECOVERY_WRAP_VERSION),
            salt=bytes.fromhex(d["salt_hex"]),
            time_cost=d.get("time_cost", 3),
            memory_cost=d.get("memory_cost", 65536),
            parallelism=d.get("parallelism", 4),
            hash_len=d.get("hash_len", 32),
            wrapped_key=bytes.fromhex(d["wrapped_key_hex"]),
            vault_id=d.get("vault_id", ""),
        )


class RecoveryWrapper:
    """Wrap/unwrap VMK with Argon2id derived from user recovery secret.

    Algorithm:
    1. Derive 256-bit key from recovery secret using Argon2id
       (time_cost=3, memory_cost=65536, parallelism=4, hash_len=32)
    2. Encrypt VMK under derived key using AES-256-GCM
       (12-byte random nonce, RECOVERY_WRAP_MAGIC as AAD)
    3. Store nonce + ciphertext + parameters in RecoveryWrapHeader

    The recovery secret is never a database key and is never embedded
    in backups. It is read via injected SecretSource (masked TTY in CLI,
    in-memory in tests).
    """

    def __init__(self) -> None:
        try:
            from argon2.low_level import Type, hash_secret_raw

            self._hash_secret_raw = hash_secret_raw
            self._Type = Type
            self._available = True
        except Exception:
            self._available = False

    @property
    def available(self) -> bool:
        return self._available

    def wrap(
        self,
        vmk: SensitiveBytes,
        recovery_secret: str,
        vault_id: VaultId | str,
    ) -> RecoveryWrapHeader:
        """Wrap VMK under Argon2id-derived key.

        Args:
            vmk: The Vault Master Key to wrap
            recovery_secret: User-provided recovery secret (never logged)
            vault_id: Vault identifier for authenticated binding

        Returns:
            RecoveryWrapHeader with parameters and wrapped key
        """
        if not self._available:
            raise OSError("Argon2id not available for recovery wrapping — install argon2-cffi")

        time_cost = 3
        memory_cost = 65536
        parallelism = 4
        hash_len = 32
        _validate_argon2_params(time_cost, memory_cost, parallelism, hash_len)

        salt = secrets.token_bytes(32)
        derived_key = self._hash_secret_raw(
            secret=recovery_secret.encode("utf-8"),
            salt=salt,
            time_cost=time_cost,
            memory_cost=memory_cost,
            parallelism=parallelism,
            hash_len=hash_len,
            type=self._Type.ID,
        )

        # Encrypt VMK with derived key using AES-GCM
        nonce = secrets.token_bytes(12)
        aead = AESGCM(derived_key)
        # Bind to vault_id for authenticated recovery
        recovery_aad = RECOVERY_WRAP_MAGIC + b"|" + str(vault_id).encode()
        wrapped = aead.encrypt(nonce, vmk.raw, recovery_aad)

        # Store nonce + wrapped_key together (12 + len(ciphertext))
        wrapped_key = nonce + wrapped

        # Clear derived key
        for i in range(len(derived_key)):
            derived_key = derived_key[:i] + b"\x00" + derived_key[i + 1 :]

        return RecoveryWrapHeader(
            version=RECOVERY_WRAP_VERSION,
            salt=salt,
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            wrapped_key=wrapped_key,
            vault_id=str(vault_id),
        )

    def unwrap(
        self,
        header: RecoveryWrapHeader,
        recovery_secret: str,
    ) -> SensitiveBytes:
        """Unwrap VMK using recovery secret and header parameters.

        Args:
            header: RecoveryWrapHeader with parameters and wrapped key
            recovery_secret: User-provided recovery secret

        Returns:
            SensitiveBytes containing the unwrapped VMK

        Raises:
            OSError: If unwrapping fails (wrong secret, corrupted data, etc.)
        """
        if not self._available:
            raise OSError("Argon2id not available for recovery unwrapping — install argon2-cffi")

        # Validate header version — reject unsupported versions
        if header.version != RECOVERY_WRAP_VERSION:
            raise OSError(
                f"Unsupported recovery header version: {header.version} "
                f"(expected {RECOVERY_WRAP_VERSION})"
            )

        # Validate parameters before allocation/KDF — prevent DoS
        _validate_argon2_params(
            header.time_cost,
            header.memory_cost,
            header.parallelism,
            header.hash_len,
        )

        derived_key = self._hash_secret_raw(
            secret=recovery_secret.encode("utf-8"),
            salt=header.salt,
            time_cost=header.time_cost,
            memory_cost=header.memory_cost,
            parallelism=header.parallelism,
            hash_len=header.hash_len,
            type=self._Type.ID,
        )

        try:
            # Decrypt VMK
            nonce = header.wrapped_key[:12]
            ciphertext = header.wrapped_key[12:]
            aead = AESGCM(derived_key)
            recovery_aad = RECOVERY_WRAP_MAGIC + b"|" + header.vault_id.encode()
            vmk_bytes = aead.decrypt(nonce, ciphertext, recovery_aad)
        except Exception:
            raise OSError("Recovery unwrap failed — wrong secret or corrupted data")
        finally:
            # Best-effort clear derived key
            for i in range(len(derived_key)):
                derived_key = derived_key[:i] + b"\x00" + derived_key[i + 1 :]

        return SensitiveBytes(vmk_bytes)


# ---------------------------------------------------------------------------
# Secret input protocol
# ---------------------------------------------------------------------------


class SecretSource(Protocol):
    """Injected secret input — never from argv/env/logs."""

    def read_secret(self, prompt: str) -> str: ...


class TTYSecretSource:
    """Read secret from masked TTY prompt (Windows/MSVCRT)."""

    def read_secret(self, prompt: str) -> str:
        import sys

        if sys.stdin.isatty():
            try:
                import msvcrt

                sys.stderr.write(prompt)
                sys.stderr.flush()
                chars: list[str] = []
                while True:
                    ch = msvcrt.getwch()
                    if ch in ("\r", "\n"):
                        sys.stderr.write("\n")
                        break
                    if ch == "\x08":  # backspace
                        if chars:
                            chars.pop()
                            sys.stderr.write("\b \b")
                    elif ch == "\x03":  # Ctrl+C
                        sys.stderr.write("\n")
                        raise KeyboardInterrupt
                    else:
                        chars.append(ch)
                        sys.stderr.write("*")
                    sys.stderr.flush()
                return "".join(chars)
            except ImportError:
                pass
        # Fallback for non-TTY: use getpass
        import getpass

        return getpass.getpass(prompt)


class InMemorySecretSource:
    """Test-only secret source — never use with real secrets."""

    def __init__(self, secret: str) -> None:
        self._secret = secret

    def read_secret(self, prompt: str) -> str:
        return self._secret
