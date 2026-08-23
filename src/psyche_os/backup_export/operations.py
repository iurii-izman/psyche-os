"""Backup, restore, and export operations.

Implements PS-17-PS-18 and ADR-021:
- Authenticated encrypted backup with domain-derived key
- Transactional consistent snapshot (never races live reads)
- Isolated restore with full multi-phase validation before activation
- Atomic activation - active vault bytes unchanged on failure
- Versioned JSONL + JSON Schema + Markdown logical export
- Backup/restore activated for E01; blob writes remain deferred

E01 REPAIR (2026-08-11):
  TARGET 1: BEGIN IMMEDIATE fail-closed, ALL rows (active+inactive), scoped
             BackupPackageStore publication, no plaintext staging.
  TARGET 2: restore_backup creates its own isolated SQLCipher target.
  TARGET 3: activate_restored_vault performs atomic file-level swap with
             previous-vault preservation.
  TARGET 4: Fault hooks at required points; active persisted + semantic
             state comparison.
  TARGET 5: Argon2id recovery wrap/unwrap integrated into recover_and_restore.
  TARGET 6: Production path uses BackupPackageStore exclusively.
  TARGET 7: Evidence validator rejects PENDING/BLOCKED/missing evidence.

Key design:
  - Backup key = derive_domain_key(vmk, "backup") - never embedded in package
  - AAD binds magic, format_version, vault_id, schema_version, table inventory,
    sequence_number, key_wrap_version, deletion_state_digest, manifest_canonical
  - Package format V1 (no schema version bump required for E01 activation)
  - Publication exclusively through BackupPackageStore (handle-bound, no-overwrite)
  - Restore creates isolated SQLCipher target, never mutates caller connection
  - Activation is separate atomic file-level swap
  - Recovery uses Argon2id unwrap, never retains raw VMK in package
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM

from psyche_os.crypto.envelope import (
    RecoveryWrapHeader,
    RecoveryWrapper,
    SensitiveBytes,
    derive_domain_key,
)
from psyche_os.domain.ids import (
    BackupId,
    ExportId,
    VaultId,
    generate_id,
)
from psyche_os.storage.schema import CURRENT_SCHEMA_VERSION

# ===========================================================================
# E01: Backup/restore is now ACTIVATED for the synthetic database-only profile.
# The _backup_deferred() gate is removed. Blob writes and general filesystem
# mutation remain DEFERRED via their own separate guards.
# ===========================================================================

# ---------------------------------------------------------------------------
# Table inventory - must match the exact schema
# ---------------------------------------------------------------------------

# Table inventory: (name, has_is_active, is_required)
# E01 REPAIR: All schema tables INCLUDING schema_migrations are backed up.
# schema_migrations is authenticated as frozen V1 migration evidence; its
# checksum is verified against the frozen V1_CHECKSUM constant, never fabricated.
_REQUIRED_BACKUP_TABLES: list[tuple[str, bool, bool]] = [
    ("vault_config", False, True),
    ("actors", True, True),
    ("subjects", True, True),
    ("source_artifacts", True, True),
    ("blobs", True, True),
    ("reports", True, True),
    ("observations", True, True),
    ("assertions", True, True),
    ("claims", True, True),
    ("data_policies", True, True),
    ("policy_lineage", False, True),
    ("derivation_runs", False, True),
    ("derivation_io", False, True),
    ("audit_events", False, True),
    ("deletion_requests", False, True),
    ("deletion_plans", False, True),
    ("deletion_receipts", False, True),
    ("backup_manifests", False, True),
    ("export_manifests", False, True),
    ("schema_migrations", False, True),
]

# Tables that do NOT use is_active - querying all rows
_TABLES_WITHOUT_IS_ACTIVE = frozenset(
    {name for name, has_ia, _ in _REQUIRED_BACKUP_TABLES if not has_ia}
)

# Required tables - backup fails if any is missing after schema check
_REQUIRED_TABLES = frozenset(
    {name for name, _, is_req in _REQUIRED_BACKUP_TABLES if is_req}
)

# All tables in the backup inventory (ordered for deterministic iteration)
_BACKUP_INVENTORY_TABLES = [name for name, _, _ in _REQUIRED_BACKUP_TABLES]

# All inventory table names as a frozenset for fast lookup
_INVENTORY_TABLE_NAMES = frozenset(_BACKUP_INVENTORY_TABLES)

# Tables intentionally excluded from backup (none — all schema tables are
# included for complete inventory and migration evidence authentication).
# schema_migrations is now included and its checksum is verified against
# the frozen V1_CHECKSUM.
_EXCLUDED_TABLES: frozenset[str] = frozenset()


BACKUP_MAGIC = b"PSYCHE-BACKUP-V1"
BACKUP_FORMAT_VERSION = 1
APP_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# E01: Structured error types for backup/restore operations
# ---------------------------------------------------------------------------

class BackupError(Exception):
    """Raised when a backup operation fails."""


class RestoreError(Exception):
    """Raised when a restore operation fails - content-free detail only."""


class ActivationError(Exception):
    """Raised when vault activation fails - content-free detail only."""


class ExportError(Exception):
    """Raised when a logical export cannot be produced safely."""


class DeferredFeatureError(RuntimeError):
    """Raised when a PRE_REAL_DATA capability is invoked during E00/E01."""


def _blob_deferred() -> None:
    raise DeferredFeatureError(
        "FEATURE_DEFERRED_PRE_REAL_DATA: blob writes are disabled by ADR-021"
    )


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------

@dataclass
class BackupManifest:
    """Metadata for an authenticated encrypted backup.

    E01 additions:
    - sequence_number: monotonically increasing per-vault backup counter
    - key_wrap_version: version of the key-wrapping scheme (1 = HKDF from VMK)
    - deletion_state_digest: SHA-256 of deletion receipt IDs active at backup time
    - table_inventory: sorted list of table names in the backup
    - app_version: version of the application that created the backup
    """

    manifest_id: BackupId = field(default_factory=lambda: BackupId(generate_id()))
    vault_id: VaultId = field(default_factory=lambda: VaultId(""))
    format_version: int = BACKUP_FORMAT_VERSION
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat()
    )
    schema_version: int = 1
    app_version: str = APP_VERSION
    record_count: int = 0
    blob_count: int = 0
    byte_total: int = 0
    sha256_hex: str = ""
    encrypted: bool = True
    storage_path: str = ""
    sequence_number: int = 0
    key_wrap_version: int = 1
    deletion_state_digest: str = ""
    table_inventory: list[str] = field(default_factory=list)
    # Table-level row counts and checksums for integrity verification
    table_checksums: dict[str, dict[str, Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": str(self.manifest_id),
            "vault_id": str(self.vault_id),
            "format_version": self.format_version,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "app_version": self.app_version,
            "record_count": self.record_count,
            "blob_count": self.blob_count,
            "byte_total": self.byte_total,
            "sha256_hex": self.sha256_hex,
            "encrypted": self.encrypted,
            "storage_path": self.storage_path,
            "sequence_number": self.sequence_number,
            "key_wrap_version": self.key_wrap_version,
            "deletion_state_digest": self.deletion_state_digest,
            "table_inventory": sorted(self.table_inventory),
            "table_checksums": self.table_checksums,
        }


# ---------------------------------------------------------------------------
# Fault injection hooks (E01 target 4)
# ---------------------------------------------------------------------------

# Global fault injection hooks for deterministic fault-preservation proofs.
# These are set by tests and cleared after use.  Production code never sets them.
_FAULT_HOOKS: dict[str, Any] = {}


def _check_fault_hook(hook_name: str) -> None:
    """If a fault hook is armed for *hook_name*, raise it now."""
    hook = _FAULT_HOOKS.get(hook_name)
    if hook is not None:
        # Clear after firing so it does not affect subsequent operations
        _FAULT_HOOKS.pop(hook_name, None)
        if isinstance(hook, Exception):
            raise hook
        if callable(hook):
            hook()


def arm_fault_hook(hook_name: str, exc_or_fn: Exception | Any) -> None:
    """Arm a named fault hook for testing.  Test-only; not for production."""
    _FAULT_HOOKS[hook_name] = exc_or_fn


def clear_fault_hooks() -> None:
    """Clear all armed fault hooks."""
    _FAULT_HOOKS.clear()


# Well-known hook names for the four required fault-injection points
HOOK_AFTER_PACKAGE_STAGING = "after_package_staging"
HOOK_AFTER_RESTORE_WRITE = "after_restore_write"
HOOK_DURING_VALIDATION = "during_validation"
HOOK_BEFORE_ACTIVATION = "before_activation"


# ---------------------------------------------------------------------------
# Active vault state capture (E01 target 4)
# ---------------------------------------------------------------------------

def capture_vault_state(db_path: str) -> dict[str, str]:
    """Capture SHA-256 digests of the active vault's persisted state.

    Returns a dict with 'main_db', 'wal', 'shm' digests (empty string if
    sidecar does not exist).  Used to prove active vault is unchanged after
    a fault during restore/validation/activation.
    """
    state: dict[str, str] = {}
    for suffix, key in [("", "main_db"), ("-wal", "wal"), ("-shm", "shm")]:
        path = db_path + suffix
        if os.path.exists(path):
            with open(path, "rb") as f:
                state[key] = hashlib.sha256(f.read()).hexdigest()
        else:
            state[key] = ""
    return state


def capture_semantic_state(connection: Any) -> dict[str, Any]:
    """Capture canonical content digests for every inventory table.

    Row counts alone cannot detect same-count corruption.  Missing or
    unreadable tables are errors because this helper is used as security
    evidence for fault preservation.
    """
    cur = connection.cursor()
    state: dict[str, Any] = {}
    for table in _BACKUP_INVENTORY_TABLES:
        cur.execute(f"SELECT * FROM {table}")
        columns = [desc[0] for desc in cur.description]
        rows = [_json_safe_row(columns, row) for row in cur.fetchall()]
        canonical = _canonical_rows(rows)
        state[table] = {
            "row_count": len(rows),
            "sha256_hex": hashlib.sha256(canonical).hexdigest(),
        }
    return state


def _json_safe_row(columns: list[str], row: Any) -> dict[str, Any]:
    result = dict(zip(columns, row, strict=True))
    for key, value in result.items():
        if isinstance(value, bytes):
            result[key] = value.hex()
    return result


def _canonical_rows(rows: list[dict[str, Any]]) -> bytes:
    encoded = [json.dumps(row, sort_keys=True, default=str) for row in rows]
    return json.dumps(sorted(encoded), separators=(",", ":")).encode()


def _require_exact_inventory(
    table_inventory: Any,
    table_checksums: Any,
    all_rows: Any | None = None,
) -> None:
    """Require identical, unique, exact inventory representations."""
    if not isinstance(table_inventory, list) or not all(
        isinstance(name, str) for name in table_inventory
    ):
        raise RestoreError("Manifest table_inventory is malformed")
    if len(table_inventory) != len(set(table_inventory)):
        raise RestoreError("Manifest table_inventory contains duplicate tables")
    if set(table_inventory) != _INVENTORY_TABLE_NAMES:
        raise RestoreError("Manifest table_inventory is not the exact frozen inventory")
    if not isinstance(table_checksums, dict) or set(table_checksums) != _INVENTORY_TABLE_NAMES:
        raise RestoreError("Manifest table_checksums is not the exact frozen inventory")
    if all_rows is not None:
        if not isinstance(all_rows, dict) or set(all_rows) != _INVENTORY_TABLE_NAMES:
            raise RestoreError("Decrypted payload is not the exact frozen inventory")
        if set(table_inventory) != set(table_checksums) or set(all_rows) != set(table_checksums):
            raise RestoreError("Inventory representations contradict one another")


def _require_manifest_security_fields(manifest: dict[str, Any]) -> None:
    if manifest.get("schema_version") != CURRENT_SCHEMA_VERSION:
        raise RestoreError("Manifest does not use the exact supported schema version")
    if manifest.get("key_wrap_version") != 1:
        raise RestoreError("Manifest key-wrap version is missing or unsupported")
    sequence = manifest.get("sequence_number")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise RestoreError("Manifest sequence state is missing or invalid")
    digest = manifest.get("deletion_state_digest")
    if not isinstance(digest, str) or len(digest) != 64:
        raise RestoreError("Manifest deletion-state digest is missing or invalid")
    try:
        bytes.fromhex(digest)
    except ValueError as exc:
        raise RestoreError("Manifest deletion-state digest is not hexadecimal") from exc
    if not manifest.get("vault_id"):
        raise RestoreError("Manifest vault identity is missing")


# ---------------------------------------------------------------------------
# BackupBuilder - E01 repaired implementation
# ---------------------------------------------------------------------------

@dataclass
class BackupBuilder:
    """Build an authenticated encrypted backup from a live vault.

    E01 REPAIR changes:
    - Uses domain-derived backup key (derive_domain_key(vmk, "backup"))
    - BEGIN IMMEDIATE fail-closed (no fallback to weak reads)
    - Backs up ALL rows (active + inactive version history, corrections,
      supersessions, deletion state)
    - Publishes exclusively through BackupPackageStore (encrypted before
      any plaintext touches disk outside in-memory staging)
    - No plaintext backup staging file
    - Rejects missing, extra, duplicate, unreadable, or ambiguous table entries
    """

    vault_id: VaultId
    backup_key: SensitiveBytes

    def build(
        self,
        connection: Any,
        store: Any,  # BackupPackageStore
        relative_path: str,
    ) -> BackupManifest:
        """Create an authenticated encrypted backup package.

        Steps:
        1. BEGIN IMMEDIATE - fail closed on any error
        2. Read ALL rows from every inventory table (no is_active filter)
        3. Verify table inventory completeness - reject missing/extra/ambiguous
        4. Compute per-table checksums and global SHA-256
        5. Read sequence_number and deletion state digest
        6. Close transaction (data is now in memory)
        7. Encrypt canonical payload under backup_key with extended AAD
        8. Build authenticated package bytes in memory
        9. Publish through BackupPackageStore (handle-bound, exclusive, no-overwrite)
        """
        # --- Step 1: Consistent snapshot - BEGIN IMMEDIATE fail-closed ---
        cur = connection.cursor()
        try:
            cur.execute("BEGIN IMMEDIATE")
        except Exception as exc:
            raise BackupError(
                "Cannot acquire consistent snapshot: BEGIN IMMEDIATE failed "
                "- backup aborted to prevent inconsistent data"
            ) from exc

        try:
            all_rows: dict[str, list[dict[str, Any]]] = {}

            # Verify schema completeness: every required table must exist
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            existing_tables = frozenset(row[0] for row in cur.fetchall())
            if existing_tables != _INVENTORY_TABLE_NAMES:
                missing = sorted(_INVENTORY_TABLE_NAMES - existing_tables)
                extra = sorted(existing_tables - _INVENTORY_TABLE_NAMES)
                raise BackupError(
                    "Required table inventory mismatch: "
                    f"missing={missing}, extra={extra}"
                )

            from psyche_os.storage.migrations import Migrator

            migration_report = Migrator(connection).verify()
            if (
                migration_report.errors
                or migration_report.target_version != CURRENT_SCHEMA_VERSION
            ):
                raise BackupError("Frozen migration evidence is missing or invalid")

            for table in _BACKUP_INVENTORY_TABLES:
                if table not in existing_tables:
                    if table in _REQUIRED_TABLES:
                        raise BackupError(
                            f"Required table '{table}' does not exist in the vault - "
                            f"backup cannot proceed with an incomplete schema"
                        )
                    # Non-required table doesn't exist - record as empty
                    all_rows[table] = []
                    continue

                # E01 REPAIR: Query ALL rows (remove is_active=1 filter).
                # Back up complete authoritative inventory: active, inactive,
                # version history, corrections, supersessions, deletion state.
                query = f"SELECT * FROM {table}"

                try:
                    cur.execute(query)
                except Exception as exc:
                    exc_msg = str(exc)
                    if "no such table" in exc_msg.lower():
                        if table in _REQUIRED_TABLES:
                            raise BackupError(
                                f"Required table '{table}' does not exist - "
                                f"backup cannot proceed with a corrupt or incomplete schema"
                            )
                        all_rows[table] = []
                        continue
                    raise BackupError(f"Failed to read table '{table}': {exc}")

                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = []
                for row in cur.fetchall():
                    row_dict = dict(zip(columns, row, strict=True))
                    if table == "vault_config" and row_dict.get("vmk_recovery_header"):
                        raise BackupError(
                            "Recovery material must be separate from backup packages"
                        )
                    # Convert binary fields to hex for JSON serialization
                    for key in (
                        "nonce",
                        "ciphertext",
                        "aad",
                        "wrapped_data_key",
                        "data_key_nonce",
                        "vmk_os_wrapped",
                        "vmk_recovery_header",
                        "db_key_salt",
                        "blob_envelope_key_salt",
                    ):
                        if key in row_dict and isinstance(row_dict[key], bytes):
                            row_dict[key] = row_dict[key].hex()
                    rows.append(row_dict)
                all_rows[table] = rows

            # --- Step 2b: Read sequence number from backup_manifests ---
            try:
                cur.execute(
                    "SELECT COUNT(*) FROM backup_manifests WHERE vault_id = ?",
                    (str(self.vault_id),),
                )
                row = cur.fetchone()
                if row is None or not isinstance(row[0], int) or row[0] < 0:
                    raise BackupError("Backup sequence state is missing or invalid")
                sequence_number = row[0] + 1
            except Exception as exc:
                raise BackupError(
                    "Failed to read sequence state; snapshot acquisition aborted"
                ) from exc

            # --- Step 2c: Read deletion state digest ---
            try:
                cur.execute("SELECT * FROM deletion_receipts ORDER BY receipt_id")
                deletion_columns = [desc[0] for desc in cur.description]
                deletion_rows = [
                    _json_safe_row(deletion_columns, row) for row in cur.fetchall()
                ]
                deletion_digest = hashlib.sha256(
                    _canonical_rows(deletion_rows)
                ).hexdigest()
            except Exception as exc:
                raise BackupError(
                    "Failed to read deletion state; snapshot acquisition aborted"
                ) from exc

            # --- Step 3: Close the read transaction ---
            cur.execute("COMMIT")

        except Exception:
            try:
                cur.execute("ROLLBACK")
            except Exception:
                pass
            # Re-raise as BackupError to keep errors content-free
            raise

        # --- Step 4-5: Build manifest with checksums ---
        manifest = BackupManifest(
            vault_id=self.vault_id,
            storage_path=relative_path,
            schema_version=1,
            sequence_number=sequence_number,
            deletion_state_digest=deletion_digest,
            table_inventory=sorted(all_rows.keys()),
        )

        total_bytes = 0
        for table in _BACKUP_INVENTORY_TABLES:
            rows = all_rows[table]
            manifest.record_count += len(rows)
            if table == "blobs":
                manifest.blob_count = len(rows)
            table_bytes = len(json.dumps(rows, sort_keys=True, default=str).encode())
            total_bytes += table_bytes

            chk = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()
            manifest.table_checksums[table] = {
                "row_count": len(rows),
                "sha256_hex": chk,
            }

        manifest.byte_total = total_bytes

        # Compute canonical byte representation and its SHA-256
        canonical = json.dumps(all_rows, sort_keys=True, default=str).encode()
        manifest.sha256_hex = hashlib.sha256(canonical).hexdigest()

        # --- Step 6: Verify exact inventory (reject missing/extra/duplicate) ---
        inventory_got = frozenset(all_rows.keys())
        if inventory_got != _INVENTORY_TABLE_NAMES:
            extra = inventory_got - _INVENTORY_TABLE_NAMES
            missing = _INVENTORY_TABLE_NAMES - inventory_got
            parts = []
            if missing:
                parts.append(f"missing: {sorted(missing)}")
            if extra:
                parts.append(f"extra: {sorted(extra)}")
            raise BackupError(f"Table inventory mismatch - {', '.join(parts)}")

        # --- Step 7: Encrypt under backup_key with extended AAD (in memory) ---
        backup_data = canonical
        nonce = secrets.token_bytes(12)
        aead = _AESGCM(self.backup_key.raw)

        # Build extended AAD
        manifest_canonical = json.dumps(
            manifest.to_dict(), sort_keys=True, ensure_ascii=False
        ).encode()

        table_inventory_str = ",".join(sorted(all_rows.keys()))
        aad_parts = [
            BACKUP_MAGIC,
            str(BACKUP_FORMAT_VERSION).encode(),
            str(self.vault_id).encode(),
            str(manifest.schema_version).encode(),
            APP_VERSION.encode(),
            table_inventory_str.encode(),
            str(sequence_number).encode(),
            str(manifest.key_wrap_version).encode(),
            deletion_digest.encode() if deletion_digest else b"",
            manifest_canonical,
        ]
        aad = b"|".join(aad_parts)

        encrypted = aead.encrypt(nonce, backup_data, aad)

        # --- Step 8: Build authenticated package bytes (in memory) ---
        backup_payload = {
            "magic": BACKUP_MAGIC.decode(),
            "format_version": BACKUP_FORMAT_VERSION,
            "manifest": manifest.to_dict(),
            "nonce_hex": nonce.hex(),
            "ciphertext_hex": encrypted.hex(),
        }
        package_bytes = json.dumps(backup_payload, indent=2).encode("utf-8")

        # E01 REPAIR: Fault hook after staging (before store publication)
        _check_fault_hook(HOOK_AFTER_PACKAGE_STAGING)

        # --- Step 9: Publish through BackupPackageStore ---
        # No plaintext staging file - encrypted/authenticated bytes go
        # directly to the scoped store with exclusive no-overwrite semantics.
        if store.exists(relative_path):
            raise BackupError(
                f"Backup package already exists at \"{relative_path}\" — "
                "write to a new path to prevent accidental overwrite"
            )
        try:
            store.write_package(relative_path, package_bytes)
        except Exception:
            raise BackupError(
                "Backup package publication failed - output path collision "
                "or store boundary violation"
            )

        return manifest

    def verify(self, store: Any, relative_path: str) -> bool:
        """Verify a backup created by this builder against its own manifest."""
        ok, _ = verify_backup_file(store, relative_path, self.backup_key)
        return ok


# ---------------------------------------------------------------------------
# Backup verification
# ---------------------------------------------------------------------------

def verify_backup_file(
    store: Any,  # BackupPackageStore
    relative_path: str,
    backup_key: SensitiveBytes,
) -> tuple[bool, str]:
    """Verify backup integrity and authenticity through BackupPackageStore.

    Steps:
    1. Read the backup package through the store
    2. Check magic and exact format version - reject 0/downgrade/missing
    3. Require exact inventory key set with non-empty checksums
    4. Decrypt and authenticate the payload (extended AAD)
    5. Verify SHA-256 of canonical representation matches manifest
    6. Verify per-table checksums - every table MUST have a non-empty checksum

    E01 REPAIR: Reads exclusively through BackupPackageStore (handle-bound).
    No direct pathname I/O.
    """
    try:
        raw_bytes = store.read_package(relative_path)
    except Exception as exc:
        return False, f"Cannot read backup package: {exc}"

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))

        magic = payload.get("magic", "")
        if magic != BACKUP_MAGIC.decode():
            return False, f"Unknown backup magic: {magic}"

        # Reject missing, zero, or downgraded format version
        format_version = payload.get("format_version", 0)
        if format_version != BACKUP_FORMAT_VERSION:
            return False, (
                f"Backup format version {format_version} not supported "
                f"(expected {BACKUP_FORMAT_VERSION})"
            )

        manifest_dict = payload.get("manifest", {})
        _require_manifest_security_fields(manifest_dict)
        vault_id = manifest_dict.get("vault_id", "")
        schema_version = manifest_dict.get("schema_version", 0)
        table_inventory = manifest_dict.get("table_inventory", [])
        sequence_number = manifest_dict.get("sequence_number", 0)
        key_wrap_version = manifest_dict.get("key_wrap_version", 0)
        deletion_state_digest = manifest_dict.get("deletion_state_digest", "")

        inventory_keys = _INVENTORY_TABLE_NAMES
        table_checksums = manifest_dict.get("table_checksums", {})
        try:
            _require_exact_inventory(table_inventory, table_checksums)
        except RestoreError as exc:
            return False, str(exc)

        # Every table MUST have a non-empty checksum dict with sha256_hex
        for table in inventory_keys:
            chk_info = table_checksums.get(table, {})
            if not isinstance(chk_info, dict):
                return False, f"Table '{table}' has malformed checksum entry"
            chk = chk_info.get("sha256_hex", "")
            if not chk:
                return False, f"Table '{table}' has empty or missing checksum"

        nonce = bytes.fromhex(payload["nonce_hex"])
        ciphertext = bytes.fromhex(payload["ciphertext_hex"])

        # Build AAD from manifest fields
        manifest_canonical = json.dumps(
            manifest_dict, sort_keys=True, ensure_ascii=False
        ).encode()

        table_inventory_str = ",".join(sorted(table_inventory)) if table_inventory else ""
        aad_parts = [
            BACKUP_MAGIC,
            str(format_version).encode(),
            vault_id.encode(),
            str(schema_version).encode(),
            APP_VERSION.encode(),
            table_inventory_str.encode(),
            str(sequence_number).encode(),
            str(key_wrap_version).encode(),
            deletion_state_digest.encode() if deletion_state_digest else b"",
            manifest_canonical,
        ]
        aad = b"|".join(aad_parts)

        # Decrypt and authenticate
        aead = _AESGCM(backup_key.raw)
        try:
            plaintext = aead.decrypt(nonce, ciphertext, aad)
        except Exception:
            return False, "Decryption failed - wrong key or tampered data"

        # Verify canonical SHA-256
        actual_sha256 = hashlib.sha256(plaintext).hexdigest()
        expected_sha256 = manifest_dict.get("sha256_hex", "")

        if actual_sha256 != expected_sha256:
            return (
                False,
                f"SHA-256 mismatch: expected {expected_sha256[:16]}..., "
                f"got {actual_sha256[:16]}...",
            )

        # Verify per-table checksums against decrypted rows
        all_rows = json.loads(plaintext.decode())
        try:
            _require_exact_inventory(table_inventory, table_checksums, all_rows)
        except RestoreError as exc:
            return False, str(exc)
        prior_for_vault = [
            row
            for row in all_rows["backup_manifests"]
            if row.get("vault_id") == vault_id
        ]
        if sequence_number != len(prior_for_vault) + 1:
            return False, "Backup sequence contradicts authenticated manifest history"
        for table in inventory_keys:
            rows = all_rows[table]
            actual_chk = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()
            expected_chk = table_checksums[table].get("sha256_hex", "")
            if actual_chk != expected_chk:
                return False, f"Table checksum mismatch for {table}"

            # Also verify row count
            expected_count = table_checksums[table].get("row_count", -1)
            if len(rows) != expected_count and expected_count >= 0:
                return False, (
                    f"Table '{table}' row count mismatch: "
                    f"expected {expected_count}, got {len(rows)}"
                )

        return True, "Backup verified"

    except Exception as exc:
        return False, f"Verification failed: {exc}"


# ---------------------------------------------------------------------------
# Atomic isolated restore (E01 target 2 repaired)
# ---------------------------------------------------------------------------

# Dependency-ordered restore (respects foreign key constraints)
_RESTORE_ORDER = [
    "vault_config",
    "actors",
    "subjects",
    "data_policies",
    "policy_lineage",
    "source_artifacts",
    "blobs",
    "reports",
    "observations",
    "assertions",
    "claims",
    "derivation_runs",
    "derivation_io",
    "audit_events",
    "deletion_requests",
    "deletion_plans",
    "deletion_receipts",
    "backup_manifests",
    "export_manifests",
    "schema_migrations",
]

# Binary columns that are stored as hex in the backup package and must be
# converted back to bytes on restore
_HEX_TO_BYTES_COLUMNS = frozenset(
    {
        "nonce",
        "ciphertext",
        "aad",
        "wrapped_data_key",
        "data_key_nonce",
        "vmk_os_wrapped",
        "vmk_recovery_header",
        "db_key_salt",
        "blob_envelope_key_salt",
    }
)


def _validate_restore_payload(
    payload: dict[str, Any],
    backup_key: SensitiveBytes,
) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    """Phase 1-2: Authenticate, decrypt, and validate a backup package.

    Returns (manifest_dict, all_rows) on success.
    Raises RestoreError on any validation or authentication failure.
    """
    # --- Phase 1: Load and authenticate ---
    magic = payload.get("magic", "")
    if magic != BACKUP_MAGIC.decode():
        raise RestoreError(f"Unknown or missing backup magic: {magic}")

    format_version = payload.get("format_version", 0)
    if format_version != BACKUP_FORMAT_VERSION:
        raise RestoreError(
            f"Backup format version {format_version} not supported "
            f"(expected {BACKUP_FORMAT_VERSION})"
        )

    manifest_dict = payload.get("manifest", {})
    if not isinstance(manifest_dict, dict):
        raise RestoreError("Backup manifest is malformed")
    _require_manifest_security_fields(manifest_dict)
    vault_id = manifest_dict.get("vault_id", "")
    schema_version = manifest_dict.get("schema_version", 0)
    sequence_number = manifest_dict.get("sequence_number", 0)
    key_wrap_version = manifest_dict.get("key_wrap_version", 0)
    deletion_state_digest = manifest_dict.get("deletion_state_digest", "")
    table_inventory = manifest_dict.get("table_inventory", [])

    table_checksums = manifest_dict.get("table_checksums", {})
    _require_exact_inventory(table_inventory, table_checksums)

    # Every table MUST have a non-empty checksum
    for table in _INVENTORY_TABLE_NAMES:
        chk_info = table_checksums.get(table, {})
        if not isinstance(chk_info, dict):
            raise RestoreError(f"Table '{table}' has malformed checksum entry")
        if not chk_info.get("sha256_hex", ""):
            raise RestoreError(f"Table '{table}' has empty or missing checksum")

    # Reject missing nonce/ciphertext
    if "nonce_hex" not in payload or "ciphertext_hex" not in payload:
        raise RestoreError("Backup package missing nonce or ciphertext")

    nonce = bytes.fromhex(payload["nonce_hex"])
    ciphertext = bytes.fromhex(payload["ciphertext_hex"])

    # Build AAD from manifest fields (must match builder exactly)
    manifest_canonical = json.dumps(
        manifest_dict, sort_keys=True, ensure_ascii=False
    ).encode()

    table_inventory_str = ",".join(sorted(table_inventory)) if table_inventory else ""
    aad_parts = [
        BACKUP_MAGIC,
        str(format_version).encode(),
        vault_id.encode(),
        str(schema_version).encode(),
        APP_VERSION.encode(),
        table_inventory_str.encode(),
        str(sequence_number).encode(),
        str(key_wrap_version).encode(),
        deletion_state_digest.encode() if deletion_state_digest else b"",
        manifest_canonical,
    ]
    aad = b"|".join(aad_parts)

    # Decrypt and authenticate
    aead = _AESGCM(backup_key.raw)
    try:
        plaintext = aead.decrypt(nonce, ciphertext, aad)
    except Exception as exc:
        raise RestoreError(
            "Decryption failed - wrong key or tampered data"
        ) from exc

    all_rows = json.loads(plaintext.decode())
    _require_exact_inventory(table_inventory, table_checksums, all_rows)

    # --- Phase 2: Validate payload ---

    # Verify global SHA-256
    actual_sha256 = hashlib.sha256(plaintext).hexdigest()
    expected_sha256 = manifest_dict.get("sha256_hex", "")
    if actual_sha256 != expected_sha256:
        raise RestoreError(
            f"SHA-256 mismatch: expected {expected_sha256[:16]}..., "
            f"got {actual_sha256[:16]}..."
        )

    # Verify per-table checksums
    for table in _INVENTORY_TABLE_NAMES:
        rows = all_rows[table]
        actual_chk = hashlib.sha256(
            json.dumps(rows, sort_keys=True, default=str).encode()
        ).hexdigest()
        expected_chk = table_checksums[table]["sha256_hex"]
        if actual_chk != expected_chk:
            raise RestoreError(f"Table checksum mismatch for {table}")

        expected_count = table_checksums[table].get("row_count", -1)
        if len(rows) != expected_count:
            raise RestoreError(
                f"Table '{table}' row count mismatch: "
                f"expected {expected_count}, got {len(rows)}"
            )

    # Bounded rollback consistency grounded in the authenticated package:
    # the next sequence must exactly follow the package's own manifest history
    # for this vault.  E01 does not invent an external monotonic service.
    prior_for_vault = [
        row
        for row in all_rows["backup_manifests"]
        if row.get("vault_id") == vault_id
    ]
    if sequence_number != len(prior_for_vault) + 1:
        raise RestoreError(
            "Backup sequence contradicts authenticated vault manifest history"
        )

    # Validate identifiers - reject unsafe dynamic identifiers
    unsafe_tables = []
    for table, rows in all_rows.items():
        for row in rows:
            for field in (
                "vault_id",
                "record_id",
                "blob_id",
                "policy_id",
                "actor_id",
                "subject_id",
                "artifact_id",
            ):
                if field in row and isinstance(row[field], str):
                    val = row[field]
                    if ".." in val or "\\" in val or val.startswith("/"):
                        unsafe_tables.append(table)
                        break
    if unsafe_tables:
        raise RestoreError(f"Unsafe identifiers detected in tables: {unsafe_tables}")

    # Verify schema version is compatible
    if schema_version != CURRENT_SCHEMA_VERSION:
        raise RestoreError(
            f"Unsupported schema version: {schema_version} "
            f"(expected exactly {CURRENT_SCHEMA_VERSION})"
        )

    return manifest_dict, all_rows


def restore_backup(
    store: Any,  # BackupPackageStore
    relative_path: str,
    backup_key: SensitiveBytes,
    restore_db_path: str,
    restore_db_key_hex: str,
) -> dict[str, Any]:
    """Restore backup to a new isolated SQLCipher target.

    E01 REPAIR: Creates its own isolated SQLCipher target at restore_db_path.
    Never mutates an active or caller-supplied vault.

    Phases:
    0. Pre-validation: target must not exist, package must be readable
    1. Read backup package through store
    2. Authenticate, decrypt, validate payload (checksums, invariants, identifiers)
    3. Create new SQLCipher database with schema
    4. Restore rows into the new target in a single transaction
       On failure: rollback transaction, delete target, active vault unchanged

    Activation is a SEPARATE step - this function restores data
    into the isolated target but does not activate it.

    Returns a dict with success status and restore metadata.
    """
    # --- Phase 0: Pre-validation ---
    # E01 REPAIR (Target 2): Remove exists-then-connect TOCTOU race.
    # The target path must not already be a valid, populated vault.
    # A file that exists as plaintext or a foreign binary will be rejected
    # by SQLCipher at connect/open time. A pre-existing SQLCipher database
    # is rejected by checking that it has no tables (fresh/empty state).
    from sqlcipher3 import dbapi2

    from psyche_os.backup_export.package_store import BackupPackageStore
    from psyche_os.storage.migrations import V1_CHECKSUM as _FROZEN_V1_CHECKSUM
    from psyche_os.storage.migrations import Migrator
    from psyche_os.storage.schema import apply_schema

    # --- Phase 1: Read backup package through store ---
    try:
        raw_bytes = store.read_package(relative_path)
    except Exception:
        return {
            "success": False,
            "reason": "Cannot read backup package through scoped authority",
            "phase": "pre_validation",
            "activated": False,
        }

    try:
        payload = json.loads(raw_bytes.decode("utf-8"))
    except json.JSONDecodeError as exc:
        return {
            "success": False,
            "reason": f"Backup package is not valid JSON: {exc}",
            "phase": "parse_package",
            "activated": False,
        }

    # --- Phase 2: Authenticate, decrypt, validate ---
    try:
        manifest_dict, all_rows = _validate_restore_payload(payload, backup_key)
    except RestoreError as exc:
        return {
            "success": False,
            "reason": str(exc),
            "phase": "validate_payload",
            "activated": False,
        }

    vault_id = manifest_dict["vault_id"]

    # --- Phase 3: Create an exclusive candidate in a narrow recovery scope ---
    candidate_path = Path(restore_db_path).resolve()
    candidate_store = BackupPackageStore(candidate_path.parent)
    candidate_relative = candidate_path.name
    try:
        candidate_store.reserve_candidate(candidate_relative)
    except Exception:
        return {
            "success": False,
            "reason": "Restore target already exists or cannot be exclusively reserved",
            "phase": "create_target",
            "activated": False,
        }

    restore_con = None
    try:
        restore_con = dbapi2.connect(str(candidate_path))
    except Exception:
        try:
            os.unlink(candidate_path)
        except OSError:
            pass
        return {
            "success": False,
            "reason": "Cannot create isolated restore target database",
            "phase": "create_target",
            "activated": False,
        }

    try:
        restore_con.execute(f"PRAGMA key = \"x'{restore_db_key_hex}'\"")
        cur = restore_con.cursor()

        # The O_EXCL reservation must still be empty when SQLCipher opens it.
        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            pre_existing_tables = [r[0] for r in cur.fetchall()]
        except Exception:
            return {
                "success": False,
                "reason": (
                    f"Restore target path already exists and cannot be read as a "
                    f"SQLCipher database (wrong key, non-database file, or "
                    f"corrupted): {restore_db_path}"
                ),
                "phase": "pre_validation",
                "activated": False,
            }

        if pre_existing_tables:
            raise RestoreError("Exclusively reserved restore target was substituted")

        apply_schema(restore_con)
        # E01 REPAIR: schema_migrations is now restored from backup data,
        # not fabricated. apply_schema() creates the table structure; the
        # actual migration rows come from the backed-up inventory.

        # --- Phase 4: Restore rows in dependency order ---
        restored_count = 0
        blob_count = 0

        cur = restore_con.cursor()
        for table in _RESTORE_ORDER:
            rows = all_rows[table]
            if not rows:
                continue
            for row in rows:
                columns = list(row.keys())
                # Convert hex-encoded binary fields back to bytes
                values = []
                for col in columns:
                    val = row[col]
                    if col in _HEX_TO_BYTES_COLUMNS:
                        if isinstance(val, str) and val:
                            val = bytes.fromhex(val)
                    values.append(val)

                placeholders = ", ".join("?" for _ in columns)
                cur.execute(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                    values,
                )
                restored_count += 1
                if table == "blobs":
                    blob_count += 1

        # Fault hook after at least one isolated write (or after the completed
        # write phase for a legitimately empty synthetic vault).
        _check_fault_hook(HOOK_AFTER_RESTORE_WRITE)

        # --- Phase 4b: actual production validation ---
        # Exact migration evidence, using the accepted migrator.
        cur.execute(
            "SELECT version, label, checksum FROM schema_migrations ORDER BY version"
        )
        mig_rows = cur.fetchall()
        if mig_rows != [(1, "f0_core_initial", _FROZEN_V1_CHECKSUM)]:
            raise RestoreError("Restored migration evidence is not exact frozen V1")
        migration_report = Migrator(restore_con).verify()
        if migration_report.errors or migration_report.target_version != CURRENT_SCHEMA_VERSION:
            raise RestoreError("Accepted migration verification failed")

        # Exact schema inventory; extra tables are as invalid as missing ones.
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        restored_tables = frozenset(r[0] for r in cur.fetchall())
        if restored_tables != _INVENTORY_TABLE_NAMES:
            raise RestoreError("Restored vault schema is not the exact frozen inventory")

        # The hook is inside the real validation sequence: migration/schema
        # checks completed, content/invariant checks have not yet completed.
        _check_fault_hook(HOOK_DURING_VALIDATION)

        # Verify vault_config singleton
        cur.execute("SELECT COUNT(*) FROM vault_config")
        if cur.fetchone()[0] != 1:
            raise RestoreError(
                "Restored vault must have exactly one vault_config row"
            )

        # Verify foreign key integrity
        try:
            cur.execute("PRAGMA foreign_key_check;")
            fk_violations = cur.fetchall()
            if fk_violations:
                raise RestoreError(
                    f"Foreign key violations in restored vault: {len(fk_violations)}"
                )
        except Exception as exc:
            exc_msg = str(exc).lower()
            if "foreign key mismatch" not in exc_msg:
                raise RestoreError(f"Foreign key check failed: {exc}")

        # Verify exact canonical content, counts and checksums.
        for table in _INVENTORY_TABLE_NAMES:
            chk_info = manifest_dict["table_checksums"][table]
            expected_count = chk_info["row_count"]
            try:
                cur.execute(f"SELECT * FROM {table}")
                columns = [desc[0] for desc in cur.description]
                restored_rows = [
                    _json_safe_row(columns, row) for row in cur.fetchall()
                ]
                actual_count = len(restored_rows)
                if actual_count != expected_count:
                    raise RestoreError(
                        f"Table '{table}' row count mismatch: "
                        f"expected {expected_count}, restored {actual_count}"
                    )
                if _canonical_rows(restored_rows) != _canonical_rows(all_rows[table]):
                    raise RestoreError(
                        f"Table '{table}' canonical semantic content differs after restore"
                    )
            except RestoreError:
                raise
            except Exception as exc:
                raise RestoreError(
                    f"Cannot verify canonical content for table '{table}': {exc}"
                )

        deletion_digest = hashlib.sha256(
            _canonical_rows(all_rows["deletion_receipts"])
        ).hexdigest()
        if deletion_digest != manifest_dict["deletion_state_digest"]:
            raise RestoreError("Deletion-state invariant does not match authenticated manifest")

        cur.execute("PRAGMA cipher_integrity_check;")
        integrity_rows = cur.fetchall()
        # The accepted SQLCipher gate treats an empty result as the documented
        # clean result and explicit rows as valid only when every row is "ok".
        if integrity_rows and any(row[0] != "ok" for row in integrity_rows):
            raise RestoreError("SQLCipher integrity validation failed")

        restore_con.commit()
        restore_con.close()
        restore_con = None
        candidate_store.verify_scoped_file(candidate_relative)

        return {
            "success": True,
            "vault_id": vault_id,
            "records_restored": restored_count,
            "blobs_restored": blob_count,
            "activated": False,  # Must be explicitly activated after validation
            "schema_version": manifest_dict.get("schema_version", 1),
            "manifest_id": manifest_dict.get("manifest_id", ""),
            "restored_db_path": str(candidate_path),
        }

    except Exception as exc:
        if restore_con is not None:
            try:
                restore_con.rollback()
            except Exception:
                pass
            try:
                restore_con.close()
            except Exception:
                pass
        # Clean up the failed restore target
        try:
            os.unlink(candidate_path)
        except OSError:
            pass
        return {
            "success": False,
            "reason": str(exc),
            "phase": "restore",
            "activated": False,
        }
    finally:
        if restore_con is not None:
            try:
                restore_con.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Atomic activation (E01 target 3 repaired)
# ---------------------------------------------------------------------------

def activate_restored_vault(
    restored_db_path: str,
    db_key_hex: str,
    active_db_path: str | None = None,
    backup_key: SensitiveBytes | None = None,
    activation_store: Any | None = None,
) -> dict[str, Any]:
    """Activate a restored vault by validating it and atomically swapping
    it into the active vault location.

    E01 REPAIR: Activation is separate from restore. Performs atomic
    file-level replacement with previous-vault preservation on failure.

    Args:
        restored_db_path: Path to the restored (and validated) SQLCipher DB
        db_key_hex: Hex-encoded database key for the restored vault
        active_db_path: If provided, atomically replace this path.
            If None, only validate (used for testing).
        backup_key: Optional backup key for cipher integrity validation

    Returns dict with success status and activation metadata.
    """
    # --- Step 1: Validate the restored vault ---
    from sqlcipher3 import dbapi2

    try:
        con = dbapi2.connect(restored_db_path)
        con.execute(f"PRAGMA key = \"x'{db_key_hex}'\"")
    except Exception as exc:
        return {
            "success": False,
            "reason": f"Cannot open restored vault for validation: {exc}",
            "phase": "activation_open",
        }

    try:
        cur = con.cursor()

        # Check 1: Verify we can read the database
        try:
            cur.execute("SELECT COUNT(*) FROM sqlite_master")
        except Exception as exc:
            return {
                "success": False,
                "reason": f"Cannot read restored vault: {exc}",
                "phase": "activation_read_check",
            }

        # Check 2: Verify all required tables exist
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        existing = frozenset(row[0] for row in cur.fetchall())
        if existing != _INVENTORY_TABLE_NAMES:
            return {
                "success": False,
                "reason": "Restored vault schema is not the exact frozen inventory",
                "phase": "activation_table_check",
            }

        from psyche_os.storage.migrations import Migrator

        migration_report = Migrator(con).verify()
        if migration_report.errors or migration_report.target_version != CURRENT_SCHEMA_VERSION:
            return {
                "success": False,
                "reason": "Accepted migration verification failed before activation",
                "phase": "activation_migration_check",
            }

        # Check 3: Vault config has exactly one row
        cur.execute("SELECT COUNT(*) FROM vault_config")
        vc_count = cur.fetchone()[0]
        if vc_count != 1:
            return {
                "success": False,
                "reason": f"Vault config has {vc_count} rows (expected 1)",
                "phase": "activation_vault_config",
            }

        # Check 4: Foreign key integrity (best-effort - SK enforcement varies)
        try:
            cur.execute("PRAGMA foreign_key_check;")
            fk_violations = cur.fetchall()
            if fk_violations:
                return {
                    "success": False,
                    "reason": f"Foreign key violations in restored vault: {len(fk_violations)} found",
                    "phase": "activation_fk_check",
                }
        except Exception as exc:
            exc_msg = str(exc).lower()
            if "foreign key mismatch" not in exc_msg:
                return {
                    "success": False,
                    "reason": f"Foreign key check failed: {exc}",
                    "phase": "activation_fk_check",
                }

        # Check 5: Cipher integrity (skip on :memory:)
        is_memory = False
        try:
            cur.execute("PRAGMA database_list;")
            db_list = cur.fetchall()
            for db_row in db_list:
                if len(db_row) >= 2 and db_row[1] == "main":
                    if len(db_row) >= 3 and db_row[2] == "":
                        is_memory = True
                    break
        except Exception:
            pass

        if not is_memory:
            try:
                cur.execute("PRAGMA cipher_integrity_check;")
                integrity_rows = cur.fetchall()
                if integrity_rows:
                    result = integrity_rows[0][0]
                    if result != "ok":
                        return {
                            "success": False,
                            "reason": f"Cipher integrity check failed: {result}",
                            "phase": "activation_integrity",
                        }
            except Exception as exc:
                return {
                    "success": False,
                    "reason": f"Cipher integrity check error: {exc}",
                    "phase": "activation_integrity",
                }

    finally:
        con.close()

    # --- Step 2: one scoped atomic activation boundary ---
    # E01 REPAIR (Target 3): When active_db_path is None, this is
    # VALIDATION-ONLY mode and MUST NOT return activated=True.
    # The active_db_path parameter must be explicitly provided for activation.
    if active_db_path is None:
        return {
            "success": True,
            "phase": "validation_only",
            "activated": False,  # E01 REPAIR: was incorrectly True
            "note": "Validation completed; use --active to activate",
        }

    if activation_store is None:
        return {
            "success": False,
            "reason": "A scoped backup/recovery authority is required for activation",
            "phase": "activation_authority",
            "activated": False,
        }

    # Installing a candidate onto itself is not an activation proof.
    if os.path.abspath(restored_db_path) == os.path.abspath(active_db_path):
        return {
            "success": False,
            "phase": "activation_target",
            "activated": False,
            "reason": "Restore candidate and active vault must be distinct",
        }

    try:
        root = Path(activation_store.backup_root).resolve()
        candidate = Path(restored_db_path).resolve().relative_to(root)
        active = Path(active_db_path).resolve().relative_to(root)
        retained_previous = activation_store.activate_database(
            candidate,
            active,
            before_atomic=lambda: _check_fault_hook(HOOK_BEFORE_ACTIVATION),
        )
        result = {"success": True, "phase": "activation_complete", "activated": True}
        if retained_previous is not None:
            result["previous_vault_retained"] = retained_previous
        return result
    except Exception as exc:
        return {
            "success": False,
            "reason": f"Activation swap failed: {exc}",
            "phase": "activation_swap",
            "activated": False,
        }


# ---------------------------------------------------------------------------
# Independent recovery with Argon2id (E01 target 5)
# ---------------------------------------------------------------------------

def recover_and_restore(
    store: Any,  # BackupPackageStore
    relative_path: str,
    recovery_header: RecoveryWrapHeader,
    recovery_secret: str,
    restore_db_path: str,
    restore_db_key_hex: str | None = None,
) -> dict[str, Any]:
    """Recover and restore a backup using independent Argon2id recovery.

    E01 REPAIR: This is the independent recovery path.  It does NOT
    require a previously retained raw VMK.  The only secrets needed are:
      - encrypted backup package (in the store)
      - recovery secret (user-provided password)
      - recovery header (stored alongside the vault database)

    Flow:
    1. Argon2id unwrap: recovery_secret + header → VMK
    2. HKDF derive backup key from VMK
    3. Decrypt/validate backup package
    4. Restore to new isolated SQLCipher target

    The original OS convenience wrapper (DPAPI) is NOT used.
    No raw VMK, backup key, or recovery secret is stored in the package.

    Returns restore result dict (same shape as restore_backup).
    """
    rw = RecoveryWrapper()
    if not rw.available:
        return {
            "success": False,
            "reason": "Argon2id recovery wrapping is not available on this platform",
            "phase": "recovery_init",
            "activated": False,
        }

    # Step 1: Argon2id unwrap VMK from recovery header
    try:
        vmk = rw.unwrap(recovery_header, recovery_secret)
    except Exception:
        return {
            "success": False,
            "reason": "Recovery unwrap failed - wrong secret or corrupted header",
            "phase": "recovery_unwrap",
            "activated": False,
        }

    try:
        # Step 2: Derive backup key from recovered VMK
        backup_key = derive_domain_key(vmk, "backup")

        # Derive a fresh-process database key from authenticated vault
        # metadata.  Recovery never needs a retained raw DB key.
        raw_package = store.read_package(relative_path)
        payload = json.loads(raw_package.decode("utf-8"))
        _, recovered_rows = _validate_restore_payload(payload, backup_key)
        vault_config_rows = recovered_rows["vault_config"]
        if len(vault_config_rows) != 1:
            raise RestoreError("Recovered vault metadata is not a singleton")
        salt_hex = vault_config_rows[0].get("db_key_salt")
        if not isinstance(salt_hex, str) or len(salt_hex) != 64:
            raise RestoreError("Recovered database-key salt is invalid")
        derived_db_key = derive_domain_key(vmk, "database", bytes.fromhex(salt_hex))
        effective_db_key_hex = restore_db_key_hex or derived_db_key.raw.hex()

        # Step 3-4: Restore using the standard path
        result = restore_backup(
            store=store,
            relative_path=relative_path,
            backup_key=backup_key,
            restore_db_path=restore_db_path,
            restore_db_key_hex=effective_db_key_hex,
        )
        return result

    except Exception:
        return {
            "success": False,
            "reason": "Recovery material or authenticated package validation failed",
            "phase": "recovery_validation",
            "activated": False,
        }

    finally:
        # Best-effort clear VMK after use
        vmk.clear()
        if "backup_key" in locals():
            backup_key.clear()
        if "derived_db_key" in locals():
            derived_db_key.clear()


# ===========================================================================
# Logical Export (unchanged from E00 - already active)
# ===========================================================================

EXPORT_MAGIC = b"PSYCHE-EXPORT-V2"
EXPORT_FORMAT_VERSION = 2

_DEFAULT_EXPORT_TABLES = (
    "vault_config",
    "actors",
    "subjects",
    "source_artifacts",
    "blobs",
    "reports",
    "observations",
    "assertions",
    "claims",
    "data_policies",
    "policy_lineage",
    "derivation_runs",
    "derivation_io",
    "audit_events",
)

_EXPORT_TABLE_HAS_IS_ACTIVE = {
    name: has_is_active for name, has_is_active, _required in _REQUIRED_BACKUP_TABLES
}

# These are the minimum columns needed to recognise a selected source as the
# canonical V1 table rather than a same-named, incompatible table.  Exporting
# every column remains intentional; this map is only a fail-closed preflight.
_EXPORT_REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "schema_migrations": frozenset({"version", "label", "checksum"}),
    "vault_config": frozenset(
        {"vault_id", "vault_name", "data_mode", "created_at", "key_state"}
    ),
    "actors": frozenset({"record_id", "actor_id", "is_active"}),
    "subjects": frozenset({"record_id", "subject_id", "is_active"}),
    "source_artifacts": frozenset({"record_id", "artifact_id", "is_active"}),
    "blobs": frozenset({"blob_id", "record_id", "is_active"}),
    "reports": frozenset({"record_id", "report_id", "is_active"}),
    "observations": frozenset({"record_id", "observation_id", "is_active"}),
    "assertions": frozenset({"record_id", "assertion_id", "is_active"}),
    "claims": frozenset({"record_id", "claim_id", "is_active"}),
    "data_policies": frozenset({"record_id", "policy_id", "is_active"}),
    "policy_lineage": frozenset({"parent_policy_id", "child_policy_id"}),
    "derivation_runs": frozenset({"derivation_id", "review_state"}),
    "derivation_io": frozenset({"derivation_id", "record_id", "role"}),
    "audit_events": frozenset({"event_id", "event_kind", "occurred_at"}),
    "deletion_requests": frozenset({"request_id", "status"}),
    "deletion_plans": frozenset({"plan_id", "request_id", "status"}),
    "deletion_receipts": frozenset({"receipt_id", "plan_id", "request_id"}),
    "backup_manifests": frozenset({"manifest_id", "vault_id", "schema_version"}),
    "export_manifests": frozenset({"manifest_id", "vault_id", "export_version"}),
}


@dataclass
class ExportManifest:
    """Manifest for a versioned logical export."""

    manifest_id: ExportId = field(default_factory=lambda: ExportId(generate_id()))
    vault_id: VaultId = field(default_factory=lambda: VaultId(""))
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat()
    )
    export_version: str = "1.0.0"
    format_version: int = EXPORT_FORMAT_VERSION
    record_count: int = 0
    blob_count: int = 0
    encrypted: bool = True
    encryption_algorithm: str = "AES-256-GCM"
    schema_versions: dict[str, str] = field(default_factory=dict)
    storage_dir: str = ""
    table_checksums: dict[str, str] = field(default_factory=dict)
    package_sha256: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": str(self.manifest_id),
            "vault_id": str(self.vault_id),
            "created_at": self.created_at,
            "export_version": self.export_version,
            "format_version": self.format_version,
            "record_count": self.record_count,
            "blob_count": self.blob_count,
            "encrypted": self.encrypted,
            "encryption_algorithm": self.encryption_algorithm,
            "schema_versions": self.schema_versions,
            "storage_dir": self.storage_dir,
            "table_checksums": self.table_checksums,
            "package_sha256": self.package_sha256,
        }


@dataclass
class ExportBuilder:
    """Build a versioned logical export - encrypted by default."""

    vault_id: VaultId
    export_envelope_key: SensitiveBytes

    def export(
        self,
        connection: Any,
        output_dir: str,
        encrypted: bool = True,
        tables: list[str] | None = None,
    ) -> ExportManifest:
        """Export vault contents to a versioned, authenticated encrypted package."""
        if tables is None:
            all_tables = list(_DEFAULT_EXPORT_TABLES)
        else:
            if not tables:
                raise ExportError("Export selection is empty")
            if any(not isinstance(table, str) for table in tables):
                raise ExportError("Export selection is invalid")
            if len(set(tables)) != len(tables):
                raise ExportError("Export selection contains duplicates")
            if any(table not in _EXPORT_REQUIRED_COLUMNS for table in tables):
                raise ExportError("Unsupported export source table")
            all_tables = list(tables)

        manifest = ExportManifest(
            vault_id=self.vault_id,
            storage_dir=output_dir,
            encrypted=encrypted,
        )

        if os.path.exists(output_dir) and os.listdir(output_dir):
            raise FileExistsError(f"Export directory exists and is not empty: {output_dir}")

        cur = connection.cursor()
        export_data: dict[str, list[dict[str, Any]]] = {}
        selected_record_count = 0
        snapshot_open = False

        try:
            try:
                cur.execute("SAVEPOINT psyche_export_snapshot")
                snapshot_open = True
            except Exception as exc:
                raise ExportError("Export source snapshot could not be acquired") from exc

            try:
                cur.execute(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
                existing_tables = frozenset(row[0] for row in cur.fetchall())
            except Exception as exc:
                raise ExportError("Export source inventory could not be read") from exc

            if "schema_migrations" in existing_tables:
                try:
                    cur.execute("PRAGMA table_info(schema_migrations)")
                    migration_columns = frozenset(row[1] for row in cur.fetchall())
                    if not _EXPORT_REQUIRED_COLUMNS["schema_migrations"].issubset(
                        migration_columns
                    ):
                        raise ExportError("Export source schema metadata is invalid")
                    cur.execute("SELECT MAX(version) FROM schema_migrations")
                    version_row = cur.fetchone()
                    source_schema_version = version_row[0] if version_row else None
                except ExportError:
                    raise
                except Exception as exc:
                    raise ExportError("Export source schema metadata is invalid") from exc

                if not isinstance(source_schema_version, int):
                    raise ExportError("Export source schema metadata is invalid")
                if source_schema_version != CURRENT_SCHEMA_VERSION:
                    raise ExportError("Export source schema is unsupported")

            for table in all_tables:
                if table not in existing_tables:
                    raise ExportError("Export source table is unavailable")

                try:
                    cur.execute(f"PRAGMA table_info({table})")
                    source_columns = frozenset(row[1] for row in cur.fetchall())
                except Exception as exc:
                    raise ExportError("Export source schema could not be inspected") from exc

                if not _EXPORT_REQUIRED_COLUMNS[table].issubset(source_columns):
                    raise ExportError("Export source table is missing required columns")

                if table == "vault_config":
                    select_query = (
                        "SELECT vault_id, vault_name, data_mode, created_at, "
                        "key_state FROM vault_config"
                    )
                    count_query = "SELECT COUNT(*) FROM vault_config"
                elif _EXPORT_TABLE_HAS_IS_ACTIVE[table]:
                    select_query = f"SELECT * FROM {table} WHERE is_active = 1"
                    count_query = f"SELECT COUNT(*) FROM {table} WHERE is_active = 1"
                else:
                    select_query = f"SELECT * FROM {table}"
                    count_query = f"SELECT COUNT(*) FROM {table}"

                try:
                    cur.execute(count_query)
                    count_row = cur.fetchone()
                    expected_count = count_row[0] if count_row else None
                    if not isinstance(expected_count, int) or expected_count < 0:
                        raise ExportError("Export source count is invalid")

                    cur.execute(select_query)
                    columns = (
                        [desc[0] for desc in cur.description]
                        if cur.description
                        else []
                    )
                    source_rows = cur.fetchall()
                except ExportError:
                    raise
                except Exception as exc:
                    raise ExportError("Export source query failed") from exc

                rows = []
                for row in source_rows:
                    try:
                        row_dict = dict(zip(columns, row, strict=True))
                    except (TypeError, ValueError) as exc:
                        raise ExportError("Export source row shape is invalid") from exc
                    for key in (
                        "nonce",
                        "ciphertext",
                        "aad",
                        "wrapped_data_key",
                        "data_key_nonce",
                        "vmk_os_wrapped",
                        "db_key_salt",
                        "blob_envelope_key_salt",
                    ):
                        if key in row_dict and isinstance(row_dict[key], bytes):
                            row_dict[key] = row_dict[key].hex()
                    rows.append(row_dict)

                if len(rows) != expected_count:
                    raise ExportError("Export source count mismatch")

                selected_record_count += expected_count
                if rows:
                    export_data[table] = rows
                    manifest.record_count += len(rows)
                    if table == "blobs":
                        manifest.blob_count = len(rows)
                    manifest.schema_versions[table] = "1.0.0"
                    manifest.table_checksums[table] = hashlib.sha256(
                        json.dumps(rows, sort_keys=True, default=str).encode()
                    ).hexdigest()

            payload_record_count = sum(len(rows) for rows in export_data.values())
            if payload_record_count != selected_record_count:
                raise ExportError("Export record count mismatch")
            if selected_record_count and not export_data:
                raise ExportError(
                    "Export source is non-empty but produced an empty package"
                )
            if manifest.record_count != payload_record_count:
                raise ExportError("Export manifest record count mismatch")

            try:
                cur.execute("RELEASE SAVEPOINT psyche_export_snapshot")
                snapshot_open = False
            except Exception as exc:
                raise ExportError("Export source snapshot could not be finalized") from exc
        except Exception:
            if snapshot_open:
                try:
                    cur.execute("ROLLBACK TO SAVEPOINT psyche_export_snapshot")
                    cur.execute("RELEASE SAVEPOINT psyche_export_snapshot")
                except Exception:
                    pass
            raise

        # Source validation and serialization complete before any export artifact
        # is created, so a rejected source cannot leave a plausible package.
        os.makedirs(output_dir, exist_ok=True)

        canonical = json.dumps(export_data, sort_keys=True, default=str).encode()
        manifest.package_sha256 = hashlib.sha256(canonical).hexdigest()

        if encrypted:
            nonce = secrets.token_bytes(12)
            aead = _AESGCM(self.export_envelope_key.raw)
            aad = EXPORT_MAGIC + b"|" + str(self.vault_id).encode()
            ciphertext = aead.encrypt(nonce, canonical, aad)

            package_path = os.path.join(output_dir, "export.enc")
            package = {
                "magic": EXPORT_MAGIC.decode(),
                "format_version": EXPORT_FORMAT_VERSION,
                "manifest": manifest.to_dict(),
                "nonce_hex": nonce.hex(),
                "ciphertext_hex": ciphertext.hex(),
            }
            with open(package_path, "w", encoding="utf-8") as f:
                json.dump(package, f)
        else:
            for table, rows in export_data.items():
                jsonl_path = os.path.join(output_dir, f"{table}.jsonl")
                with open(jsonl_path, "w", encoding="utf-8") as f:
                    for row in rows:
                        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")

        manifest_path = os.path.join(output_dir, "export_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        md_path = os.path.join(output_dir, "README.md")
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# PSYCHE OS Export\n\n")
            f.write(f"- **Vault:** {manifest.vault_id}\n")
            f.write(f"- **Export version:** {manifest.export_version}\n")
            f.write(f"- **Created:** {manifest.created_at}\n")
            f.write(f"- **Records:** {manifest.record_count}\n")
            f.write(f"- **Blobs:** {manifest.blob_count}\n")
            f.write(f"- **Encrypted:** {manifest.encrypted}\n")
            if manifest.encrypted:
                f.write(f"- **Encryption:** {manifest.encryption_algorithm}\n")
            f.write(f"- **Package SHA-256:** {manifest.package_sha256}\n\n")
            f.write("## Tables\n\n")
            for table, ver in sorted(manifest.schema_versions.items()):
                f.write(f"- **{table}** (schema v{ver})\n")

        return manifest


def verify_export(
    output_dir: str,
    export_envelope_key: SensitiveBytes,
) -> tuple[bool, str]:
    """Verify an export package end-to-end.

    For encrypted exports: decrypts, validates SHA-256, checks per-table digests.
    For plaintext exports: validates SHA-256 and per-table digests.
    """
    manifest_path = os.path.join(output_dir, "export_manifest.json")
    if not os.path.exists(manifest_path):
        return False, "Export manifest not found"

    try:
        with open(manifest_path, encoding="utf-8") as f:
            manifest_dict = json.load(f)

        vault_id = manifest_dict.get("vault_id", "")
        encrypted = manifest_dict.get("encrypted", True)
        expected_sha256 = manifest_dict.get("package_sha256", "")
        table_checksums = manifest_dict.get("table_checksums", {})
        schema_versions = manifest_dict.get("schema_versions", {})
        expected_record_count = manifest_dict.get("record_count")
        expected_blob_count = manifest_dict.get("blob_count")

        if manifest_dict.get("export_version") != "1.0.0":
            return False, "Unsupported export version"
        if not isinstance(expected_record_count, int) or isinstance(
            expected_record_count, bool
        ) or expected_record_count < 0:
            return False, "Export record count is invalid"
        if not isinstance(expected_blob_count, int) or isinstance(
            expected_blob_count, bool
        ) or expected_blob_count < 0:
            return False, "Export blob count is invalid"
        if not isinstance(table_checksums, dict) or not isinstance(
            schema_versions, dict
        ):
            return False, "Export table metadata is invalid"
        if any(
            table not in _EXPORT_REQUIRED_COLUMNS
            for table in set(table_checksums) | set(schema_versions)
        ):
            return False, "Unsupported export table"
        if any(version != "1.0.0" for version in schema_versions.values()):
            return False, "Unsupported export table schema version"

        if encrypted:
            package_path = os.path.join(output_dir, "export.enc")
            if not os.path.exists(package_path):
                return False, "Encrypted export package not found"

            with open(package_path, encoding="utf-8") as f:
                package = json.load(f)

            magic = package.get("magic", "")
            if magic != EXPORT_MAGIC.decode():
                return False, f"Unknown export magic: {magic}"
            format_version = package.get("format_version", 0)
            if format_version != EXPORT_FORMAT_VERSION:
                return False, f"Unsupported export format version: {format_version}"
            if package.get("manifest") != manifest_dict:
                return False, "Export manifest binding mismatch"

            export_nonce = bytes.fromhex(package["nonce_hex"])
            export_ciphertext = bytes.fromhex(package["ciphertext_hex"])

            aead = _AESGCM(export_envelope_key.raw)
            aad = EXPORT_MAGIC + b"|" + vault_id.encode()
            try:
                plaintext = aead.decrypt(export_nonce, export_ciphertext, aad)
            except Exception:
                return False, "Decryption failed - wrong key or tampered data"

            actual_sha256 = hashlib.sha256(plaintext).hexdigest()
            export_data = json.loads(plaintext.decode())
        else:
            export_data = {}
            for filename in os.listdir(output_dir):
                if filename.endswith(".jsonl"):
                    table = filename[:-6]
                    rows = []
                    filepath = os.path.join(output_dir, filename)
                    with open(filepath, encoding="utf-8") as f:
                        for line in f:
                            line = line.strip()
                            if line:
                                rows.append(json.loads(line))
                    if rows:
                        export_data[table] = rows

            canonical = json.dumps(export_data, sort_keys=True, default=str).encode()
            actual_sha256 = hashlib.sha256(canonical).hexdigest()

        if not isinstance(export_data, dict):
            return False, "Export payload shape is invalid"
        if any(
            table not in _EXPORT_REQUIRED_COLUMNS for table in export_data
        ):
            return False, "Unsupported export table"
        if any(
            not isinstance(rows, list)
            or any(not isinstance(row, dict) for row in rows)
            or not rows
            for rows in export_data.values()
        ):
            return False, "Export payload table shape is invalid"

        if actual_sha256 != expected_sha256:
            return (
                False,
                f"SHA-256 mismatch: expected {expected_sha256[:16]}..., "
                f"got {actual_sha256[:16]}...",
            )

        payload_tables = set(export_data)
        if payload_tables != set(table_checksums) or payload_tables != set(
            schema_versions
        ):
            return False, "Export table inventory mismatch"

        actual_record_count = sum(len(rows) for rows in export_data.values())
        if actual_record_count != expected_record_count:
            return False, "Export record count mismatch"
        actual_blob_count = len(export_data.get("blobs", []))
        if actual_blob_count != expected_blob_count:
            return False, "Export blob count mismatch"
        if expected_record_count and not export_data:
            return False, "Export payload unexpectedly empty"

        for table, expected_chk in table_checksums.items():
            actual_chk = hashlib.sha256(
                json.dumps(export_data[table], sort_keys=True, default=str).encode()
            ).hexdigest()
            if actual_chk != expected_chk:
                return False, f"Table checksum mismatch for {table}"

        return True, "Export verified"

    except Exception:
        return False, "Export verification failed"
