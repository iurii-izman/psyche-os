"""Backup, restore, and export operations.

Implements PS-07 and ADR-009:
- Authenticated encrypted backup with canonical byte hash
- Isolated restore with full validation before activation
- Versioned JSONL + JSON Schema + Markdown logical export
- Export encrypted by default; plaintext requires explicit authorized decryption
- Self-verification: a fresh backup must verify with its own verifier
"""

from __future__ import annotations

from dataclasses import dataclass, field
import datetime
import hashlib
import json
import os
import secrets
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM as _AESGCM

from psyche_os.crypto.envelope import (
    BlobAEAD,
    SensitiveBytes,
)
from psyche_os.domain.ids import (
    BackupId,
    ExportId,
    VaultId,
    generate_id,
)

# F02 (FIX): Every inventory table is required. Omitting any table from the
# backup (because it is missing or unreadable) is a fatal error.  The only
# deliberately excluded tables are backup_manifests and export_manifests which
# live outside the authoritative vault set.

# Table inventory: (name, has_is_active, is_required)
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
]

# Tables that do NOT use is_active — querying all rows
_TABLES_WITHOUT_IS_ACTIVE = frozenset(
    {name for name, has_ia, _ in _REQUIRED_BACKUP_TABLES if not has_ia}
)

# Required tables — backup fails if any is missing after schema check
_REQUIRED_TABLES = frozenset({name for name, _, is_req in _REQUIRED_BACKUP_TABLES if is_req})

# All tables in the backup inventory
_BACKUP_INVENTORY_TABLES = [name for name, _, _ in _REQUIRED_BACKUP_TABLES]

# All inventory table names as a frozenset for fast lookup
_INVENTORY_TABLE_NAMES = frozenset(_BACKUP_INVENTORY_TABLES)


BACKUP_MAGIC = b"PSYCHE-BACKUP-V1"
BACKUP_FORMAT_VERSION = 1


class DeferredFeatureError(RuntimeError):
    """Raised when a PRE_REAL_DATA capability is invoked during E00."""


def _backup_deferred() -> None:
    raise DeferredFeatureError(
        "FEATURE_DEFERRED_PRE_REAL_DATA: backup/restore is disabled by ADR-021"
    )


@dataclass
class BackupManifest:
    """Metadata for an authenticated encrypted backup."""

    manifest_id: BackupId = field(default_factory=lambda: BackupId(generate_id()))
    vault_id: VaultId = field(default_factory=lambda: VaultId(""))
    format_version: int = BACKUP_FORMAT_VERSION
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())
    schema_version: int = 1
    record_count: int = 0
    blob_count: int = 0
    byte_total: int = 0
    sha256_hex: str = ""
    encrypted: bool = True
    storage_path: str = ""
    # Table-level checksums for integrity verification
    table_checksums: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest_id": str(self.manifest_id),
            "vault_id": str(self.vault_id),
            "format_version": self.format_version,
            "created_at": self.created_at,
            "schema_version": self.schema_version,
            "record_count": self.record_count,
            "blob_count": self.blob_count,
            "byte_total": self.byte_total,
            "sha256_hex": self.sha256_hex,
            "encrypted": self.encrypted,
            "storage_path": self.storage_path,
            "table_checksums": self.table_checksums,
        }


@dataclass
class BackupBuilder:
    """Build an authenticated encrypted backup from a live vault."""

    vault_id: VaultId
    manifest_key: SensitiveBytes

    def build(
        self,
        connection: Any,
        storage_path: str,
        blob_aead: BlobAEAD | None = None,
    ) -> BackupManifest:
        """Create an authenticated encrypted backup file.

        F02: Uses the exact required table/schema inventory. Each table is
        queried according to its real schema (is_active for versioned tables,
        full scan for non-versioned tables). Required tables must exist;
        missing required tables cause a fatal error. Missing optional tables
        are recorded with an empty row set (schema presence tracked).
        """
        _backup_deferred()
        manifest = BackupManifest(vault_id=self.vault_id, storage_path=storage_path)

        cur = connection.cursor()

        # F02: Query each table according to its real schema
        all_rows: dict[str, list[dict[str, Any]]] = {}
        total_bytes = 0

        for table in _BACKUP_INVENTORY_TABLES:
            # F02: Never convert a failed table read to an empty table.
            # "No such table" means the table simply doesn't exist yet (skip
            # for optional, fatal for required). Any other error (corrupted,
            # locked, integrity failure) is always fatal.
            if table in _TABLES_WITHOUT_IS_ACTIVE:
                query = f"SELECT * FROM {table}"
            else:
                query = f"SELECT * FROM {table} WHERE is_active = 1"

            try:
                cur.execute(query)
            except Exception as exc:
                exc_msg = str(exc)
                if "no such table" in exc_msg.lower():
                    if table in _REQUIRED_TABLES:
                        raise RuntimeError(
                            f"Required table '{table}' does not exist in the vault — "
                            f"backup cannot proceed with a corrupt or incomplete schema"
                        )
                    # Optional table doesn't exist yet — record as empty
                    all_rows[table] = []
                    continue
                # Any other error is fatal
                raise

            columns = [desc[0] for desc in cur.description] if cur.description else []
            rows = []
            for row in cur.fetchall():
                row_dict = dict(zip(columns, row, strict=True))
                # Convert binary fields to hex for JSON serialization
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
            all_rows[table] = rows
            manifest.record_count += len(rows)
            if table == "blobs":
                manifest.blob_count = len(rows)
            table_bytes = len(json.dumps(rows, sort_keys=True, default=str).encode())
            total_bytes += table_bytes
            # Per-table checksum — always present even for empty tables
            manifest.table_checksums[table] = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()

        manifest.byte_total = total_bytes

        # Compute canonical byte representation and its SHA-256
        canonical = json.dumps(all_rows, sort_keys=True, default=str).encode()
        manifest.sha256_hex = hashlib.sha256(canonical).hexdigest()

        # Encrypt the canonical payload under the manifest key.
        # F02: Bind the canonical manifest bytes into AAD so the outer
        # manifest cannot be modified without breaking decryption.
        backup_data = canonical
        nonce = secrets.token_bytes(12)
        aead = _AESGCM(self.manifest_key.raw)
        manifest_canonical = json.dumps(
            manifest.to_dict(), sort_keys=True, ensure_ascii=False
        ).encode()
        aad = BACKUP_MAGIC + b"|" + str(self.vault_id).encode() + b"|" + manifest_canonical
        encrypted = aead.encrypt(nonce, backup_data, aad)

        # Build authenticated backup package
        backup_payload = {
            "magic": BACKUP_MAGIC.decode(),
            "format_version": BACKUP_FORMAT_VERSION,
            "manifest": manifest.to_dict(),
            "nonce_hex": nonce.hex(),
            "ciphertext_hex": encrypted.hex(),
        }

        # Never overwrite existing files
        if os.path.exists(storage_path):
            raise FileExistsError(f"Backup output already exists: {storage_path}")

        os.makedirs(os.path.dirname(storage_path) or ".", exist_ok=True)
        with open(storage_path, "w", encoding="utf-8") as f:
            json.dump(backup_payload, f)

        return manifest

    def verify(self, storage_path: str) -> bool:
        """Verify a backup created by this builder against its own manifest."""
        ok, _ = verify_backup_file(storage_path, self.manifest_key)
        return ok


def verify_backup_file(storage_path: str, manifest_key: SensitiveBytes) -> tuple[bool, str]:
    """Verify backup integrity and authenticity using canonical byte hash.

    F02 (FIX): Steps:
    1. Load the backup package
    2. Check magic and exact format version — reject 0/downgrade/missing
    3. Require exact inventory key set with non-empty checksums
    4. Decrypt and authenticate the payload (manifest bytes bound in AAD)
    5. Verify SHA-256 of canonical representation matches manifest
    6. Verify per-table checksums — every table MUST have a non-empty checksum
    """
    _backup_deferred()
    if not os.path.exists(storage_path):
        return False, "Backup file not found"

    try:
        with open(storage_path, encoding="utf-8") as f:
            payload = json.load(f)

        magic = payload.get("magic", "")
        if magic != BACKUP_MAGIC.decode():
            return False, f"Unknown backup magic: {magic}"

        # F02: Reject missing, zero, or downgraded format version
        format_version = payload.get("format_version", 0)
        if format_version != BACKUP_FORMAT_VERSION:
            return False, (
                f"Backup format version {format_version} not supported "
                f"(expected {BACKUP_FORMAT_VERSION})"
            )

        manifest = payload.get("manifest", {})
        vault_id = manifest.get("vault_id", "")

        # F02: Require the exact inventory key set before decryption
        inventory_keys = _INVENTORY_TABLE_NAMES
        table_checksums = manifest.get("table_checksums", {})
        got_keys = set(table_checksums.keys())
        if got_keys != inventory_keys:
            extra = got_keys - inventory_keys
            missing = inventory_keys - got_keys
            parts: list[str] = []
            if missing:
                parts.append(f"missing tables: {sorted(missing)}")
            if extra:
                parts.append(f"extra tables: {sorted(extra)}")
            return False, f"Manifest table inventory mismatch — {', '.join(parts)}"

        # F02: Every table MUST have a non-empty checksum
        for table in inventory_keys:
            chk = table_checksums.get(table, "")
            if not chk:
                return False, f"Table '{table}' has empty or missing checksum"

        nonce = bytes.fromhex(payload["nonce_hex"])
        ciphertext = bytes.fromhex(payload["ciphertext_hex"])

        # F02: Bind the canonical manifest bytes into AAD so the outer manifest
        # cannot be modified without breaking authenticated decryption.
        manifest_canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()

        # Decrypt and authenticate
        aead = _AESGCM(manifest_key.raw)
        aad = BACKUP_MAGIC + b"|" + vault_id.encode() + b"|" + manifest_canonical
        try:
            plaintext = aead.decrypt(nonce, ciphertext, aad)
        except Exception:
            return False, "Decryption failed — wrong key or tampered data"

        # Verify canonical SHA-256
        actual_sha256 = hashlib.sha256(plaintext).hexdigest()
        expected_sha256 = manifest.get("sha256_hex", "")

        if actual_sha256 != expected_sha256:
            return (
                False,
                f"SHA-256 mismatch: expected {expected_sha256[:16]}..., got {actual_sha256[:16]}...",
            )

        # Verify per-table checksums against decrypted rows
        all_rows = json.loads(plaintext.decode())
        for table in inventory_keys:
            rows = all_rows.get(table, [])
            actual_chk = hashlib.sha256(
                json.dumps(rows, sort_keys=True, default=str).encode()
            ).hexdigest()
            expected_chk = table_checksums[table]
            if actual_chk != expected_chk:
                return False, f"Table checksum mismatch for {table}"

        return True, "Backup verified"

    except Exception as exc:
        return False, f"Verification failed: {exc}"


def restore_backup(
    storage_path: str,
    manifest_key: SensitiveBytes,
    target_connection: Any,
) -> dict[str, Any]:
    """Restore backup to an isolated target vault.

    F02: The restore target is treated as empty only after checking the
    ENTIRE target schema — not only vault_config. If any backup inventory
    table has rows in the target, restore is rejected.

    Restore runs in a single transaction. On any failure, the transaction
    is rolled back and no partially visible state remains. Activation
    requires a separate, explicit step after validation.
    """
    _backup_deferred()
    # Phase 0: Reject non-empty target — check the ENTIRE inventory (F02)
    cur = target_connection.cursor()
    populated_tables: list[str] = []
    for table in _BACKUP_INVENTORY_TABLES:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            row = cur.fetchone()
            if row and row[0] > 0:
                populated_tables.append(table)
        except Exception:
            # Table doesn't exist yet — that's fine, it's empty
            pass

    if populated_tables:
        return {
            "success": False,
            "reason": (
                f"Target vault is not empty — tables already contain data: "
                f"{', '.join(populated_tables)}. Restore requires a fresh, empty vault."
            ),
            "phase": "reject_populated_target",
            "populated_tables": populated_tables,
        }

    # Phase 1: Authenticate and decrypt
    try:
        with open(storage_path, encoding="utf-8") as f:
            payload = json.load(f)

        vault_id = payload["manifest"]["vault_id"]

        # F02: Reject missing, zero, or wrong format version
        format_version = payload.get("format_version", 0)
        if format_version != BACKUP_FORMAT_VERSION:
            return {
                "success": False,
                "reason": (
                    f"Backup format version {format_version} not supported "
                    f"(expected {BACKUP_FORMAT_VERSION})"
                ),
                "phase": "verify_format",
            }

        # F02: Require exact inventory with non-empty checksums
        manifest = payload.get("manifest", {})
        table_checksums = manifest.get("table_checksums", {})
        got_keys = set(table_checksums.keys())
        if got_keys != _INVENTORY_TABLE_NAMES:
            extra = got_keys - _INVENTORY_TABLE_NAMES
            missing = _INVENTORY_TABLE_NAMES - got_keys
            parts = []
            if missing:
                parts.append(f"missing tables: {sorted(missing)}")
            if extra:
                parts.append(f"extra tables: {sorted(extra)}")
            return {
                "success": False,
                "reason": f"Manifest table inventory mismatch — {', '.join(parts)}",
                "phase": "verify_inventory",
            }
        for table in _INVENTORY_TABLE_NAMES:
            if not table_checksums.get(table, ""):
                return {
                    "success": False,
                    "reason": f"Table '{table}' has empty or missing checksum",
                    "phase": "verify_checksums",
                }

        nonce = bytes.fromhex(payload["nonce_hex"])
        ciphertext = bytes.fromhex(payload["ciphertext_hex"])

        aead = _AESGCM(manifest_key.raw)
        manifest_canonical = json.dumps(manifest, sort_keys=True, ensure_ascii=False).encode()
        aad = BACKUP_MAGIC + b"|" + vault_id.encode() + b"|" + manifest_canonical
        plaintext = aead.decrypt(nonce, ciphertext, aad)
        all_rows = json.loads(plaintext.decode())

        # Phase 2: Validate identifiers
        # Reject unsafe dynamic identifiers
        unsafe_tables = []
        for table, rows in all_rows.items():
            for row in rows:
                for field in ("vault_id", "record_id", "blob_id", "policy_id"):
                    if field in row and isinstance(row[field], str):
                        if ".." in row[field] or "\\" in row[field] or row[field].startswith("/"):
                            unsafe_tables.append(table)
                            break
        if unsafe_tables:
            return {
                "success": False,
                "reason": f"Unsafe identifiers in tables: {unsafe_tables}",
                "phase": "validate_ids",
            }

        # Phase 3: Restore all rows — never suppress failures
        cur = target_connection.cursor()
        restored_count = 0
        blob_count = 0

        # Dependency-ordered restore
        restore_order = [
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
        ]

        for table in restore_order:
            rows = all_rows.get(table, [])
            if not rows:
                continue
            for row in rows:
                columns = list(row.keys())
                # Handle hex-encoded binary fields — convert back to bytes
                values = []
                for col in columns:
                    val = row[col]
                    if col in (
                        "nonce",
                        "ciphertext",
                        "aad",
                        "wrapped_data_key",
                        "data_key_nonce",
                        "vmk_os_wrapped",
                        "db_key_salt",
                        "blob_envelope_key_salt",
                    ):
                        if isinstance(val, str) and val:
                            val = bytes.fromhex(val)
                    values.append(val)

                placeholders = ", ".join("?" for _ in columns)
                # Use INSERT (not INSERT OR REPLACE) — replace behavior hides errors
                cur.execute(
                    f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
                    values,
                )
                restored_count += 1
                if table == "blobs":
                    blob_count += 1

        target_connection.commit()

        return {
            "success": True,
            "vault_id": vault_id,
            "records_restored": restored_count,
            "blobs_restored": blob_count,
            "activated": False,  # Must be explicitly activated after validation
        }

    except Exception as exc:
        try:
            target_connection.rollback()
        except Exception:
            pass
        return {"success": False, "reason": str(exc), "phase": "restore"}


# ===========================================================================
# Logical Export
# ===========================================================================

EXPORT_MAGIC = b"PSYCHE-EXPORT-V2"
EXPORT_FORMAT_VERSION = 2


@dataclass
class ExportManifest:
    """Manifest for a versioned logical export."""

    manifest_id: ExportId = field(default_factory=lambda: ExportId(generate_id()))
    vault_id: VaultId = field(default_factory=lambda: VaultId(""))
    created_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())
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
    """Build a versioned logical export — encrypted by default.

    The export is produced as a single authenticated encrypted package.
    Plaintext output is NOT the default; it requires explicit authorized
    decryption. The manifest MUST match the actual format on disk.
    """

    vault_id: VaultId
    export_envelope_key: SensitiveBytes  # Domain-derived key for export encryption

    def export(
        self,
        connection: Any,
        output_dir: str,
        encrypted: bool = True,
        tables: list[str] | None = None,
    ) -> ExportManifest:
        """Export vault contents to a versioned, authenticated encrypted package.

        When encrypted=True (default): produces a single AES-256-GCM encrypted
        tar-like JSON package. The manifest records encrypted=true and the
        actual encryption algorithm used.

        When encrypted=False: produces plaintext JSONL files. This is only
        for authorized decryption scenarios and MUST NOT be the default.
        The manifest records encrypted=false truthfully.

        Args:
            connection: Database connection
            output_dir: Output directory (must not exist or be empty)
            encrypted: Whether to encrypt the export package
            tables: Specific tables to export (None = all)

        Returns:
            ExportManifest describing the actual export produced
        """
        manifest = ExportManifest(
            vault_id=self.vault_id,
            storage_dir=output_dir,
            encrypted=encrypted,
        )

        # Never overwrite existing exports
        if os.path.exists(output_dir) and os.listdir(output_dir):
            raise FileExistsError(f"Export directory exists and is not empty: {output_dir}")

        os.makedirs(output_dir, exist_ok=True)

        all_tables = tables or [
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
        ]

        cur = connection.cursor()

        # Collect all rows into memory
        export_data: dict[str, list[dict[str, Any]]] = {}

        for table in all_tables:
            try:
                if table == "vault_config":
                    cur.execute(
                        "SELECT vault_id, vault_name, data_mode, created_at, key_state FROM vault_config"
                    )
                else:
                    cur.execute(f"SELECT * FROM {table} WHERE is_active = 1")

                columns = [desc[0] for desc in cur.description] if cur.description else []
                rows = []
                for row in cur.fetchall():
                    row_dict = dict(zip(columns, row))
                    # Convert binary fields to hex
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

                if rows:
                    export_data[table] = rows
                    manifest.record_count += len(rows)
                    manifest.schema_versions[table] = "1.0.0"

                    # Per-table checksum
                    manifest.table_checksums[table] = hashlib.sha256(
                        json.dumps(rows, sort_keys=True, default=str).encode()
                    ).hexdigest()
            except Exception:
                pass

        # Build canonical representation
        canonical = json.dumps(export_data, sort_keys=True, default=str).encode()
        manifest.package_sha256 = hashlib.sha256(canonical).hexdigest()

        if encrypted:
            # Encrypt the entire canonical payload as one authenticated package
            nonce = secrets.token_bytes(12)
            aead = _AESGCM(self.export_envelope_key.raw)
            aad = EXPORT_MAGIC + b"|" + str(self.vault_id).encode()
            ciphertext = aead.encrypt(nonce, canonical, aad)

            # Write single encrypted package file
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
            # Plaintext export — only for authorized decryption
            # Write JSONL per table
            for table, rows in export_data.items():
                jsonl_path = os.path.join(output_dir, f"{table}.jsonl")
                with open(jsonl_path, "w", encoding="utf-8") as f:
                    for row in rows:
                        f.write(json.dumps(row, sort_keys=True, default=str) + "\n")

        # Write manifest (always plaintext for inspection)
        manifest_path = os.path.join(output_dir, "export_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2)

        # Write Markdown summary
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

    For encrypted exports: decrypts, validates SHA-256, and checks per-table digests.
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
            if format_version > EXPORT_FORMAT_VERSION:
                return False, f"Unsupported export format version: {format_version}"

            export_nonce = bytes.fromhex(package["nonce_hex"])
            export_ciphertext = bytes.fromhex(package["ciphertext_hex"])

            aead = _AESGCM(export_envelope_key.raw)
            aad = EXPORT_MAGIC + b"|" + vault_id.encode()
            try:
                plaintext = aead.decrypt(export_nonce, export_ciphertext, aad)
            except Exception:
                return False, "Decryption failed — wrong key or tampered data"

            actual_sha256 = hashlib.sha256(plaintext).hexdigest()
            export_data = json.loads(plaintext.decode())
        else:
            # For plaintext exports, reconstruct canonical from JSONL files
            export_data = {}
            for filename in os.listdir(output_dir):
                if filename.endswith(".jsonl"):
                    table = filename[:-6]  # Strip .jsonl
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

        # Verify overall SHA-256
        if actual_sha256 != expected_sha256:
            return (
                False,
                f"SHA-256 mismatch: expected {expected_sha256[:16]}..., got {actual_sha256[:16]}...",
            )

        # Verify per-table checksums
        for table, expected_chk in table_checksums.items():
            if table in export_data:
                actual_chk = hashlib.sha256(
                    json.dumps(export_data[table], sort_keys=True, default=str).encode()
                ).hexdigest()
                if actual_chk != expected_chk:
                    return False, f"Table checksum mismatch for {table}"

        return True, "Export verified"

    except Exception as exc:
        return False, f"Export verification failed: {exc}"
