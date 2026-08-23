# Personal key envelope and portable recovery

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW**. Design ID: `PMV1-KEY-ENVELOPE-V1`. Existing algorithms are reused unchanged: 32-byte CSPRNG VMK; current-user DPAPI `OSKeyWrapper`; Argon2id/AES-GCM `RecoveryWrapper`; HKDF-SHA256 `derive_domain_key`.

## Active envelope

Path: `%LOCALAPPDATA%\\PSYCHE OS\\Personal\\key-envelope.pmv1.json`; the file and its parent have current-user-only Windows ACLs. UTF-8 JSON, no BOM, is canonicalized as sorted keys / compact separators for digests. Format is exactly:

```json
{"format":"PMV1-KEY-ENVELOPE","version":1,"vault_id":"<bounded id>","profile_id":"local_personal_evidence_reflection_windows_v1","profile_version":"1.0","key_version":1,"key_state":"active","db_salt_hex":"64 lowercase hex","backup_salt_hex":"64 lowercase hex","export_salt_hex":"64 lowercase hex","manifest_salt_hex":"64 lowercase hex","dpapi_vmk_hex":"lowercase hex","recovery":{"version":1,"salt_hex":"64 lowercase hex","time_cost":3,"memory_cost":65536,"parallelism":4,"hash_len":32,"wrapped_key_hex":"lowercase hex","vault_id":"same id"}}
```

No unknown fields, duplicate keys, floats, non-canonical hex, overlong values, unsupported version, mismatched vault/profile/key state, or malformed recovery header is accepted. IDs are ASCII `[A-Za-z0-9_-]`, 1–128 bytes; DPAPI blob is 1–16 KiB; recovery ciphertext is 28–128 bytes. Recovery bounds are exactly the existing wrapper bounds: time 1–10, memory 8192–262144 KiB, parallelism 1–8, hash length 32. Corruption/replacement fails closed; it never creates a VMK or silently repairs metadata. Rollback to an older envelope is rejected when its key version/state differs from the active DB and manifest binding; restore is the only recovery route.

`Kdb`, `Kbackup`, `Kexport`, and `Kmanifest` use the four distinct per-vault 32-byte salts above with literal existing domains `database`, `backup`, `export`, and `manifest`. This resolves compatibility: current legacy backup/export uses the zero default; Personal V1 uses per-vault per-domain salts, carried in its outer bootstrap. Rotation changes VMK/key version and all four salts; it never changes a backup's recorded bootstrap.

## Atomic first publication

Generate VMK/salts in memory, obtain independently re-entered recovery secret, create/unwrap-verify RecoveryWrapper and DPAPI wraps, then write a restrictive-ACL sibling staging file. Flush file and directory, atomically publish with a no-replace exclusive rename/create, reopen and parse/verify it, then create/open the Personal V10 DB. If the target exists, publication fails; it never overwrites a winner. If any stage fails, remove only private unactivated staging and do not activate a DB. Existing metadata is never replaced by generation.

## Portable outer bootstrap and binding

Every Personal backup contains a bounded unencrypted `PMV1-RECOVERY-BOOTSTRAP` header before its encrypted payload: `format`, `version`, `vault_id`, `profile_id`, `profile_version`, `key_version`, four salt fields, exact serialized `RecoveryWrapHeader`, `backup_id`, payload nonce/length/SHA-256, and `bootstrap_digest`. It contains no plaintext VMK, recovery secret, or derived key. It is copied from the active envelope only after exact parse/validation.

RecoveryWrapper authenticates its wrapped VMK to `RECOVERY_WRAP_MAGIC|vault_id`; a salt/header/VMK ciphertext swap therefore fails during unwrap unless it is a same-vault valid wrapper. After VMK recovery, derive `Kmanifest` with `manifest_salt`; authenticate the canonical bootstrap and payload descriptor using existing AES-GCM manifest-domain protection, then derive `Kbackup` with `backup_salt` and authenticate/decrypt the existing backup payload. Thus profile, version, key version, salts, backup ID, payload digest/length and vault ID are authenticated after VMK recovery; a wrong vault/header, swapped bootstrap/payload, salt swap or key-version mismatch fails closed before staging activation. No new primitive is introduced.

Probe: the repository's `RecoveryWrapper` successfully recovered a synthetic VMK and derived a 32-byte backup key. Its V1 header was `salt=32`, wrapped VMK `=60`, Argon2 `3/65536/4/32`; malformed `time_cost=999999` was rejected before KDF allocation. This also proves the necessary guard exists.

## Disaster recovery and required rotation

From only backup bundle plus recovery secret: parse bounded outer header → validate version/length/hex/KDF bounds → unwrap VMK → derive/authenticate manifest binding → derive `Kbackup`, authenticate/decrypt to private staging → derive `Kdb`, open DB → integrity/FK/schema/semantic checks → create a new current-user DPAPI wrap → explicit owner activation. No old DPAPI context, cloud escrow, plaintext VMK, or hidden file is required.

**Rotation is required before initial Personal opening.** `REAL_DATA_GATE.yaml` names RDG-02 `key_rotation_and_independent_recovery_verified`; the master spec §16.2 and §25 require versioned rotation and rotation testing. Personal v1 implements a bounded, crash-safe testable lifecycle: `active → rotation_pending → retained_for_read → retired_for_write`; preflight verified backup/recovery, create version N+1 envelope and wraps in staging, verify both unwrap paths, atomically publish, retain old recovery material for read/restore until declared backup expiry, then retire/destroy only under deletion/expiry policy. Crash points retain either verified N or verified N+1, never an active DB with no published envelope.
