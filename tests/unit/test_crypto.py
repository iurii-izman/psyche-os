"""Unit tests for crypto layer."""

import pytest

from psyche_os.crypto.envelope import (
    ENVELOPE_VERSION,
    RECOVERY_WRAP_VERSION,
    BlobAEAD,
    BlobEnvelope,
    InMemorySecretSource,
    KeyState,
    SensitiveBytes,
    derive_domain_key,
    generate_vmk,
)
from psyche_os.domain.ids import BlobId, VaultId, generate_id


class TestSensitiveBytes:
    def test_generation(self) -> None:
        sb = SensitiveBytes(b"hello world")
        assert len(sb) == 11
        assert sb.raw == b"hello world"

    def test_clear(self) -> None:
        sb = SensitiveBytes(b"secret data")
        sb.clear()
        assert sb.raw == b"\x00" * 11

    def test_generate_vmk_length(self) -> None:
        vmk = generate_vmk()
        assert len(vmk) == 32  # 256 bits


class TestKeyDerivation:
    def test_derive_database_key(self) -> None:
        vmk = generate_vmk()
        db_key = derive_domain_key(vmk, "database")
        assert len(db_key) == 32

    def test_derive_different_domains(self) -> None:
        vmk = generate_vmk()
        k1 = derive_domain_key(vmk, "database")
        k2 = derive_domain_key(vmk, "blob")
        assert k1.raw != k2.raw

    def test_derive_same_domain_same_key(self) -> None:
        vmk = generate_vmk()
        k1 = derive_domain_key(vmk, "blob_envelope")
        k2 = derive_domain_key(vmk, "blob_envelope")
        assert k1.raw == k2.raw

    def test_derive_with_salt(self) -> None:
        vmk = generate_vmk()
        k1 = derive_domain_key(vmk, "database", salt=b"\x01" * 32)
        k2 = derive_domain_key(vmk, "database", salt=b"\x02" * 32)
        assert k1.raw != k2.raw

    def test_unknown_domain_raises(self) -> None:
        vmk = generate_vmk()
        with pytest.raises(ValueError, match="Unknown key domain"):
            derive_domain_key(vmk, "nonexistent")


class TestBlobEnvelope:
    def test_encrypt_decrypt_roundtrip(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"test blob content"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)
        assert envelope.envelope_version == ENVELOPE_VERSION
        assert len(envelope.nonce) == 12
        assert envelope.ciphertext != plaintext

        decrypted = aead.decrypt(envelope)
        assert decrypted == plaintext

    def test_tampered_ciphertext_fails(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"test blob content"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)

        # Tamper with ciphertext
        tampered_ciphertext = envelope.ciphertext[:-1] + bytes([envelope.ciphertext[-1] ^ 0x01])
        tampered = BlobEnvelope(
            blob_id=envelope.blob_id,
            vault_id=envelope.vault_id,
            ciphertext=tampered_ciphertext,
            nonce=envelope.nonce,
            key_version=envelope.key_version,
        )

        with pytest.raises(Exception):
            aead.decrypt(tampered)

    def test_tampered_aad_fails(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"test blob content"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)

        # Try to decrypt with wrong vault_id (changes AAD verification)
        wrong_envelope = BlobEnvelope(
            blob_id=envelope.blob_id,
            vault_id=VaultId("wrong-vault"),  # Different vault
            ciphertext=envelope.ciphertext,
            nonce=envelope.nonce,
            key_version=envelope.key_version,
        )

        with pytest.raises(Exception):
            aead.decrypt(wrong_envelope)

    def test_static_decrypt_with_key(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"recovery test"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)

        # Decrypt with explicit key
        decrypted = BlobAEAD.decrypt_with_key(blob_key, envelope)
        assert decrypted == plaintext


class TestKeyState:
    def test_key_state_values(self) -> None:
        states = [s.value for s in KeyState]
        assert "generated" in states
        assert "active" in states
        assert "rotation_pending" in states
        assert "retired_for_write" in states
        assert "retained_for_read" in states
        assert "destroyed" in states


class TestRecoveryWrap:
    def test_recovery_wrap_available(self) -> None:
        from psyche_os.crypto.envelope import RecoveryWrapper

        rw = RecoveryWrapper()
        assert rw.available is True

    def test_recovery_wrap_roundtrip(self) -> None:
        from psyche_os.crypto.envelope import RecoveryWrapper

        rw = RecoveryWrapper()
        if not rw.available:
            pytest.skip("Argon2id not available")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        secret = "test recovery secret phrase"

        header = rw.wrap(vmk, secret, vault_id)
        assert header.version == RECOVERY_WRAP_VERSION
        assert len(header.salt) == 32
        assert len(header.wrapped_key) == 12 + 32 + 16  # nonce + encrypted key + tag

        unwrapped = rw.unwrap(header, secret)
        assert unwrapped.raw == vmk.raw

    def test_recovery_wrap_wrong_secret_fails(self) -> None:
        from psyche_os.crypto.envelope import RecoveryWrapper

        rw = RecoveryWrapper()
        if not rw.available:
            pytest.skip("Argon2id not available")

        vmk = generate_vmk()
        vault_id = VaultId(generate_id())
        secret = "correct secret"

        header = rw.wrap(vmk, secret, vault_id)

        with pytest.raises(OSError, match="wrong secret"):
            rw.unwrap(header, "wrong secret")


class TestSecretSource:
    def test_in_memory_secret_source(self) -> None:
        source = InMemorySecretSource("test-secret")
        assert source.read_secret("Prompt: ") == "test-secret"
