"""Security tests for crypto, SQLCipher, and plaintext detection."""

import hashlib
import os
import tempfile

import pytest

from psyche_os.crypto.envelope import (
    BlobAEAD,
    SensitiveBytes,
    derive_domain_key,
    generate_vmk,
)
from psyche_os.domain.ids import BlobId, VaultId, generate_id

pytestmark = [pytest.mark.security]


class TestVMKGeneration:
    def test_vmk_is_256_bit(self) -> None:
        for _ in range(10):
            vmk = generate_vmk()
            assert len(vmk) == 32

    def test_vmk_is_random(self) -> None:
        """Generate 50 VMKs and verify all are unique."""
        keys = {generate_vmk().raw for _ in range(50)}
        assert len(keys) == 50

    def test_vmk_not_all_zeros(self) -> None:
        for _ in range(10):
            vmk = generate_vmk()
            assert vmk.raw != b"\x00" * 32

    def test_sensitive_bytes_clear(self) -> None:
        sb = SensitiveBytes(b"x" * 32)
        sb.clear()
        assert sb.raw == b"\x00" * 32


class TestKeyDerivationDomainSeparation:
    def test_database_vs_blob_key_different(self) -> None:
        vmk = generate_vmk()
        db_key = derive_domain_key(vmk, "database")
        blob_key = derive_domain_key(vmk, "blob")
        assert db_key.raw != blob_key.raw

    def test_different_salts_different_keys(self) -> None:
        vmk = generate_vmk()
        k1 = derive_domain_key(vmk, "database", salt=os.urandom(32))
        k2 = derive_domain_key(vmk, "database", salt=os.urandom(32))
        assert k1.raw != k2.raw

    def test_same_params_same_key(self) -> None:
        vmk = generate_vmk()
        salt = os.urandom(32)
        k1 = derive_domain_key(vmk, "database", salt=salt)
        k2 = derive_domain_key(vmk, "database", salt=salt)
        assert k1.raw == k2.raw


class TestBlobAEADSecurity:
    def test_encrypt_produces_different_ciphertexts(self) -> None:
        """Same plaintext, same key → different ciphertexts (unique nonces)."""
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"same content"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        e1 = aead.encrypt(plaintext, blob_id, vault_id)
        e2 = aead.encrypt(plaintext, blob_id, vault_id)

        # Different nonces → different ciphertexts
        assert e1.ciphertext != e2.ciphertext
        assert e1.nonce != e2.nonce

    def test_decrypt_different_vault_fails(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"test"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)

        # Create envelope with different vault_id
        from psyche_os.crypto.envelope import BlobEnvelope

        tampered = BlobEnvelope(
            blob_id=blob_id,
            vault_id=VaultId("different-vault"),
            ciphertext=envelope.ciphertext,
            nonce=envelope.nonce,
            key_version=envelope.key_version,
        )

        with pytest.raises(Exception):
            aead.decrypt(tampered)

    def test_bit_flip_detected(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"test content for integrity"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)

        # Flip a single bit in the ciphertext
        ct = bytearray(envelope.ciphertext)
        ct[5] ^= 0x01

        from psyche_os.crypto.envelope import BlobEnvelope

        tampered = BlobEnvelope(
            blob_id=blob_id,
            vault_id=vault_id,
            ciphertext=bytes(ct),
            nonce=envelope.nonce,
            key_version=envelope.key_version,
        )

        with pytest.raises(Exception):
            aead.decrypt(tampered)

    def test_nonce_tamper_detected(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b"test"
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)

        from psyche_os.crypto.envelope import BlobEnvelope

        tampered_nonce = envelope.nonce[:-1] + bytes([envelope.nonce[-1] ^ 0xFF])
        tampered = BlobEnvelope(
            blob_id=blob_id,
            vault_id=vault_id,
            ciphertext=envelope.ciphertext,
            nonce=tampered_nonce,
            key_version=envelope.key_version,
        )

        with pytest.raises(Exception):
            aead.decrypt(tampered)

    def test_empty_plaintext(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        plaintext = b""
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)
        decrypted = aead.decrypt(envelope)
        assert decrypted == b""

    def test_large_blob(self) -> None:
        vmk = generate_vmk()
        blob_key = derive_domain_key(vmk, "blob_envelope")
        aead = BlobAEAD(blob_key)

        # 1 MB blob
        plaintext = os.urandom(1_000_000)
        blob_id = BlobId(generate_id())
        vault_id = VaultId(generate_id())

        envelope = aead.encrypt(plaintext, blob_id, vault_id)
        decrypted = aead.decrypt(envelope)
        assert decrypted == plaintext
        assert hashlib.sha256(decrypted).hexdigest() == hashlib.sha256(plaintext).hexdigest()


class TestSQLCipherSecurity:
    def test_wrong_key_gate(self) -> None:
        """Verify wrong-key probe works correctly."""
        import os
        import secrets

        from sqlcipher3 import dbapi2

        db_path = os.path.join(tempfile.gettempdir(), f"_sec_test_{secrets.token_hex(4)}.db")
        try:
            con = dbapi2.connect(db_path)
            con.execute("PRAGMA key = 'correct_key';")
            con.execute("CREATE TABLE t(x);")
            con.execute("INSERT INTO t VALUES (1);")
            con.commit()
            con.close()

            with pytest.raises(Exception):
                con2 = dbapi2.connect(db_path)
                con2.execute("PRAGMA key = 'wrong_key';")
                cur = con2.cursor()
                cur.execute("SELECT * FROM t;")
                cur.fetchall()
                con2.close()
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass

    def test_encrypted_header_not_plaintext(self) -> None:
        """Verify database header is not plaintext SQLite."""
        import os
        import secrets

        from sqlcipher3 import dbapi2

        db_path = os.path.join(tempfile.gettempdir(), f"_sec_head_{secrets.token_hex(4)}.db")
        try:
            con = dbapi2.connect(db_path)
            con.execute("PRAGMA key = 'header_test_key';")
            con.execute("CREATE TABLE t(x);")
            con.commit()
            con.close()

            with open(db_path, "rb") as f:
                header = f.read(16)

            assert not header.startswith(b"SQLite format 3\x00"), (
                f"Header is plaintext: {header.hex()}"
            )
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass

    def test_plaintext_sqlite_rejected_under_encrypted_profile(self) -> None:
        """A plaintext SQLite file opened with a key should error."""
        import os
        import secrets
        import sqlite3 as plain_sqlite

        db_path = os.path.join(tempfile.gettempdir(), f"_sec_reject_{secrets.token_hex(4)}.db")
        try:
            con = plain_sqlite.connect(db_path)
            con.execute("CREATE TABLE t(x);")
            con.commit()
            con.close()

            from sqlcipher3 import dbapi2

            con2 = dbapi2.connect(db_path)
            con2.execute("PRAGMA key = 'test_key';")
            cur = con2.cursor()

            # Reading a plaintext file with encryption key should fail
            with pytest.raises(Exception):
                cur.execute("SELECT * FROM sqlite_master;")
                cur.fetchall()
            con2.close()
        finally:
            try:
                os.unlink(db_path)
            except OSError:
                pass
