# Personal VMK and recovery design

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW; no crypto implementation authorized.** Design ID: `PMV1-VMK-RECOVERY-ENVELOPE-V1`.

The current Reflection workspace uses a random database key protected only by DPAPI. Personal v1 instead adopts the accepted ADR-008 envelope lifecycle: a CSPRNG 256-bit VMK, Windows current-user DPAPI convenience wrap, and independent `RecoveryWrapper` Argon2id wrap. It reuses `crypto/envelope.py` unchanged: HKDF-SHA256 `derive_domain_key`, DPAPI, RecoveryWrapper (versioned header, Argon2id parameters), and AES-GCM consumers.

`Kdb = derive_domain_key(VMK, "database", db_key_salt)`, `Kbackup = derive_domain_key(VMK, "backup", backup_key_salt)`, and `Kexport = derive_domain_key(VMK, "export", export_key_salt)`. Salts are random, versioned, non-secret bootstrap metadata; domain labels are literal and versioned. The implementation must reconcile existing backup salt semantics before code—no implicit new salt format.

Bootstrap metadata is a small ACL-scoped, integrity-checked sidecar owned by Python: vault/profile ID, format/version, DB/backup/export salts, key version/state, DPAPI-wrapped VMK, RecoveryWrapHeader, DB path identity, and no recovery secret or plaintext VMK. It is backed up inside the encrypted package and bound by AEAD manifest/AAD. It is not renderer-readable and it is not an export of secrets.

First use: generate VMK and salts in memory; require an independently re-entered recovery secret; create and verify both wraps before creating/activating the Personal database; derive Kdb; initialize V10 store; verify reopen through DPAPI and a separate isolated RecoveryWrapper path; only then mark key state `active`. Any failure deletes only unactivated staging material and leaves no usable Personal vault.

Unlock tries DPAPI as convenience. DPAPI loss/corruption or a new Windows user invokes recovery-secret unwrap, validates header/version/AAD, then re-wraps the same VMK for the current user after explicit confirmation. Wrong secret, corrupt header, bad authentication tag, or wrong vault ID fails closed without creating/replacing metadata. Rotation is a future explicit state machine (`active → rotation_pending → retained_for_read → retired_for_write`) that rewraps/rewrites only after backup and recovery proofs; it is not part of this implementation contract. VMK destruction is gated by deletion/backup-expiry policy. Remaining critical unknown: exact metadata file format/location and backup salt compatibility require independent review before implementation.
