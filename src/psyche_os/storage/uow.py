"""Unit of work with crash-safe blob and version row protocol.

Every logical write produces a pair: a new version row closes the
previous active version, and an operation log entry records the write.
Blobs follow a state machine: created → stored → verified → (corrupted | deleted).

F05 (FIX): UoW now enforces blob stage ordering (created → stored → verified),
prevents stored-state claims for absent blobs, uses allowlist-based table/column
validation, persists vault identity with keyed digest, and restricts audit
reasons to content-free enum values. Deletion closure is tracked via
closure_marker propagation with subtype field preservation.
"""

from __future__ import annotations

from contextlib import contextmanager
from collections.abc import Generator
from dataclasses import dataclass, field
import datetime
import hashlib
import hmac
import json
from typing import Any

from psyche_os.crypto.envelope import (
    BlobAEAD,
    BlobEnvelope,
)
from psyche_os.domain.ids import (
    AuditEventId,
    BlobId,
    RecordId,
    VaultId,
    VersionId,
    generate_id,
)
from psyche_os.domain.versions import (
    CHANGE_REASON_INITIAL,
)

# F07: Lazy import to avoid circular imports; the actual validation uses
# the module-level _is_valid_authority helper called from _commit.

# ---------------------------------------------------------------------------
# Content-free audit reason enum (F05)
# ---------------------------------------------------------------------------

# F07: Authority validation — used by UoW._commit to reject direct writes
def _is_valid_authority(auth: Any) -> bool:
    """Return True if auth is a fully-initialized FixtureAuthority.

    Checks via duck typing to avoid a hard import dependency on
    psyche_os.application.ports at module load time.
    """
    try:
        return bool(
            auth.__class__.__module__ == "psyche_os.application.ports"
            and auth.__class__.__name__ == "FixtureAuthority"
            and hasattr(auth, "is_valid")
            and auth.is_valid
            and hasattr(auth, "_token")
            and len(auth._token) == 64
            and bool(auth._bound_fixture_id)
            and len(auth._bound_digest) == 64
        )
    except Exception:
        return False

# ---------------------------------------------------------------------------
# Content-free audit reason enum (F05)
# ---------------------------------------------------------------------------

# Allowed audit event kinds — no free-form text in operation/reason fields
AUDIT_EVENT_KIND_WRITE = "write"
AUDIT_EVENT_KIND_DELETE = "delete"
AUDIT_EVENT_KIND_CLOSE = "close"
AUDIT_EVENT_KIND_VERIFY = "verify"

ALLOWED_AUDIT_EVENT_KINDS: frozenset[str] = frozenset(
    {
        AUDIT_EVENT_KIND_WRITE,
        AUDIT_EVENT_KIND_DELETE,
        AUDIT_EVENT_KIND_CLOSE,
        AUDIT_EVENT_KIND_VERIFY,
    }
)

# Content-free audit reasons — no user-generated text, only enumeration
AUDIT_REASON_INITIAL = "initial"
AUDIT_REASON_UPDATE = "update"
AUDIT_REASON_CLOSURE = "closure"
AUDIT_REASON_POLICY_CHANGE = "policy_change"
AUDIT_REASON_DELETION = "deletion"
AUDIT_REASON_VERIFICATION = "verification"

ALLOWED_AUDIT_REASONS: frozenset[str] = frozenset(
    {
        AUDIT_REASON_INITIAL,
        AUDIT_REASON_UPDATE,
        AUDIT_REASON_CLOSURE,
        AUDIT_REASON_POLICY_CHANGE,
        AUDIT_REASON_DELETION,
        AUDIT_REASON_VERIFICATION,
    }
)

# ---------------------------------------------------------------------------
# Table allowlist — no dynamic table/column SQL (F05)
# ---------------------------------------------------------------------------

ALLOWED_TABLES: frozenset[str] = frozenset(
    {
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
        "deletion_requests",
        "deletion_plans",
        "deletion_receipts",
        "backup_manifests",
        "export_manifests",
    }
)

# Tables that support versioned rows (record_id + version_id + tx_from/tx_to + is_active)
VERSIONED_TABLES: frozenset[str] = frozenset(
    {
        "actors",
        "subjects",
        "source_artifacts",
        "reports",
        "observations",
        "assertions",
        "claims",
        "data_policies",
    }
)

# F05: Per-table column allowlists for DML — column names from caller data
# must appear in the table-specific set. Even though the table name itself
# is allowlisted, column names are NOT interpolated unchecked.
_TABLE_COLUMN_ALLOWLISTS: dict[str, frozenset[str]] = {
    "vault_config": frozenset(
        {
            "vault_id",
            "vault_name",
            "data_mode",
            "created_at",
            "vmk_os_wrapped",
            "vmk_recovery_header",
            "key_state",
            "db_key_salt",
            "blob_envelope_key_salt",
        }
    ),
    "actors": frozenset({"actor_id", "actor_kind", "actor_label", "closure_marker"}),
    "subjects": frozenset(
        {"subject_id", "subject_label", "anonymous", "data_mode", "closure_marker"}
    ),
    "source_artifacts": frozenset(
        {
            "artifact_id",
            "source_kind",
            "source_label",
            "uri_or_path",
            "mime_type",
            "blob_id",
            "locator_id",
            "ingested_at",
            "provided_by_actor",
            "source_metadata",
            "closure_marker",
        }
    ),
    "blobs": frozenset(
        {
            "blob_id",
            "record_id",
            "envelope_version",
            "key_version",
            "nonce",
            "ciphertext",
            "aad",
            "wrapped_data_key",
            "data_key_nonce",
            "blob_sha256",
            "byte_length",
            "state",
            "vault_keyed_digest",
        }
    ),
    "reports": frozenset(
        {
            "report_id",
            "title",
            "source_ids",
            "observation_ids",
            "assertion_ids",
            "claim_ids",
            "summary",
            "structured_data",
            "authored_at",
            "closure_marker",
        }
    ),
    "observations": frozenset(
        {
            "observation_id",
            "subject_id",
            "source_artifact_id",
            "method",
            "raw_value",
            "structured_data",
            "observed_at",
            "observer_actor_id",
            "derivation_id",
            "temporal_ref",
            "closure_marker",
        }
    ),
    "assertions": frozenset(
        {
            "assertion_id",
            "subject_id",
            "assertion_type",
            "predicate",
            "support_ids",
            "contra_ids",
            "confidence",
            "derivation_id",
            "provenance_ref",
            "closure_marker",
        }
    ),
    "claims": frozenset(
        {
            "claim_id",
            "subject_id",
            "claim_type",
            "claim_status",
            "claim_origin",
            "claim_body",
            "evidence_ids",
            "contradiction_set_id",
            "resolution",
            "derivation_id",
            "provenance_ref",
            "closure_marker",
        }
    ),
    "data_policies": frozenset(
        {
            "policy_id",
            "target_record_id",
            "sensitivity",
            "processing_location",
            "cloud_policy",
            "purpose",
            "purpose_expiry",
            "third_party_scope",
            "retention_policy_id",
            "retention_review",
            "export_rule",
            "export_audience",
            "lineage_rule",
            "closure_marker",
        }
    ),
    "policy_lineage": frozenset({"parent_policy_id", "child_policy_id", "created_at"}),
    "derivation_runs": frozenset(
        {
            "derivation_id",
            "method_kind",
            "code_rule_model_tool",
            "code_rule_model_version",
            "parameters_config_digest",
            "environment_profile",
            "started_at",
            "ended_at",
            "actor_id",
            "purpose",
            "validation_outcomes",
            "review_state",
            "failure_reason",
        }
    ),
    "derivation_io": frozenset({"derivation_id", "record_id", "role"}),
    "audit_events": frozenset(
        {
            "event_id",
            "event_kind",
            "occurred_at",
            "actor_id",
            "target_record_ids",
            "operation",
            "outcome",
            "reason",
            "content_preview",
            "search_terms",
            "response_summary",
            "affected_paths",
            "subject_names",
            "secret_hashes",
        }
    ),
    "deletion_requests": frozenset(
        {
            "request_id",
            "actor_id",
            "reason",
            "scope",
            "target_ids",
            "approved_by",
            "approved_at",
            "status",
            "created_at",
        }
    ),
    "deletion_plans": frozenset(
        {
            "plan_id",
            "request_id",
            "target_record_ids",
            "exclusive_descendant_ids",
            "mixed_descendant_ids",
            "invalidate_ids",
            "recompute_ids",
            "dependency_graph_snapshot",
            "executed_at",
            "receipt_id",
            "status",
            "created_at",
        }
    ),
    "deletion_receipts": frozenset(
        {
            "receipt_id",
            "plan_id",
            "request_id",
            "records_deleted",
            "records_invalidated",
            "records_recomputed",
            "verification_hash",
            "executed_by",
            "executed_at",
            "created_at",
        }
    ),
    "backup_manifests": frozenset(
        {
            "manifest_id",
            "vault_id",
            "created_at",
            "schema_version",
            "record_count",
            "blob_count",
            "byte_total",
            "sha256_hex",
            "encrypted",
            "recovery_header",
            "storage_path",
        }
    ),
    "export_manifests": frozenset(
        {
            "manifest_id",
            "vault_id",
            "created_at",
            "export_version",
            "record_count",
            "blob_count",
            "encrypted",
            "schema_versions",
            "storage_path",
        }
    ),
}

# Columns that are always system-managed (never user-settable via data dict)
_SYSTEM_COLUMNS: frozenset[str] = frozenset(
    {
        "record_id",
        "tx_from",
        "tx_to",
        "is_active",
        "created_at",
        "version_id",
        "previous_version_id",
    }
)

# ---------------------------------------------------------------------------
# Blob state machine
# ---------------------------------------------------------------------------


class BlobState:
    CREATED = "created"
    STORED = "stored"
    VERIFIED = "verified"
    CORRUPTED = "corrupted"
    DELETED = "deleted"

    VALID_TRANSITIONS = {
        CREATED: {STORED},
        STORED: {VERIFIED, CORRUPTED, DELETED},
        VERIFIED: {CORRUPTED, DELETED},
        CORRUPTED: {DELETED},
        DELETED: set(),
    }

    @classmethod
    def can_transition(cls, from_state: str, to_state: str) -> bool:
        return to_state in cls.VALID_TRANSITIONS.get(from_state, set())

    @classmethod
    def transition(cls, from_state: str, to_state: str) -> str:
        if not cls.can_transition(from_state, to_state):
            raise ValueError(f"Invalid blob state transition: {from_state} → {to_state}")
        return to_state


# ---------------------------------------------------------------------------
# Unit of work
# ---------------------------------------------------------------------------


@dataclass
class Operation:
    """A single write operation within a unit of work."""

    table: str
    record_id: RecordId
    version_id: VersionId
    data: dict[str, Any]
    previous_version_id: str = ""
    change_reason: str = CHANGE_REASON_INITIAL


@dataclass
class BlobOperation:
    """A blob write operation."""

    blob_id: BlobId
    record_id: RecordId
    plaintext: bytes
    vault_id: VaultId
    envelope: BlobEnvelope | None = None


@dataclass
class UnitOfWork:
    """Collects operations within a transaction boundary.

    Committed atomically. On crash, the partially-written unit
    is discarded and the previous active version stays active.

    F09b (FIX): actor_id and purpose are typed security-boundary fields
    — they must be non-empty for any non-initial write. The purpose is
    a content-free audit enum value, not an arbitrary string.
    """

    unit_id: str = field(default_factory=lambda: generate_id())
    started_at: str = field(default_factory=lambda: datetime.datetime.now(datetime.UTC).isoformat())
    operations: list[Operation] = field(default_factory=list)
    blob_operations: list[BlobOperation] = field(default_factory=list)
    actor_id: str = ""
    purpose: str = AUDIT_REASON_INITIAL  # Must be from ALLOWED_AUDIT_REASONS
    completed_at: str | None = None

    def add_operation(
        self,
        table: str,
        record_id: RecordId,
        data: dict[str, Any],
        previous_version_id: str = "",
        change_reason: str = CHANGE_REASON_INITIAL,
    ) -> Operation:
        # F05: validate table against allowlist
        if table not in ALLOWED_TABLES:
            raise UnitOfWorkError(f"Table '{table}' is not in the storage allowlist")
        # F05: validate change_reason against content-free enum
        if change_reason not in ALLOWED_AUDIT_REASONS:
            raise UnitOfWorkError(f"Change reason '{change_reason}' is not an allowed audit reason")
        # F05: reject system-managed columns in user data
        for col in _SYSTEM_COLUMNS:
            if col in data:
                raise UnitOfWorkError(
                    f"Column '{col}' is system-managed and must not appear in data dict"
                )
        # F05: Per-table column allowlist — reject caller-controlled column names
        # that are not declared for the target table, even if the table is allowed.
        allowed_cols = _TABLE_COLUMN_ALLOWLISTS.get(table)
        if allowed_cols is not None:
            for col in data:
                if col not in allowed_cols:
                    raise UnitOfWorkError(
                        f"Column '{col}' is not in the column allowlist for table '{table}'"
                    )
        op = Operation(
            table=table,
            record_id=record_id,
            version_id=VersionId(generate_id()),
            data=data,
            previous_version_id=previous_version_id,
            change_reason=change_reason,
        )
        self.operations.append(op)
        return op

    def add_blob(
        self, blob_id: BlobId, record_id: RecordId, plaintext: bytes, vault_id: VaultId
    ) -> BlobOperation:
        bop = BlobOperation(
            blob_id=blob_id,
            record_id=record_id,
            plaintext=plaintext,
            vault_id=vault_id,
        )
        self.blob_operations.append(bop)
        return bop

    def complete(self) -> None:
        self.completed_at = datetime.datetime.now(datetime.UTC).isoformat()

    @property
    def total_operations(self) -> int:
        return len(self.operations) + len(self.blob_operations)


# ---------------------------------------------------------------------------
# UnitOfWorkManager — commits atomically to a SQLCipher database
# ---------------------------------------------------------------------------


class UnitOfWorkError(Exception):
    """Raised when a unit of work cannot be committed."""


class UnitOfWorkManager:
    """Manages transaction-scoped units of work over SQLCipher.

    F07 (FIX): Accepts an optional _authority that gates content writes.
    When _authority is None/empty, _commit raises UnitOfWorkError before
    any SQL or filesystem mutation.  The only successful content write path
    is through the package-owned fixture loader which supplies a validated
    FixtureAuthority.
    """

    def __init__(
        self,
        connection: Any,
        blob_aead: BlobAEAD | None = None,
        vault_digest_key: bytes | None = None,
        _authority: Any | None = None,
    ) -> None:
        self._con = connection
        self._blob_aead = blob_aead
        self._vault_digest_key = vault_digest_key or b""
        self._authority = _authority

    @contextmanager
    def begin(
        self, actor_id: str = "", purpose: str = ""
    ) -> Generator[UnitOfWork, None, None]:
        """Begin a new unit of work. Commits on clean exit, rolls back on exception."""
        uow = UnitOfWork(actor_id=actor_id, purpose=purpose)
        try:
            yield uow
            self._commit(uow)
        except Exception:
            self._rollback(uow)
            raise

    def _commit(self, uow: UnitOfWork) -> None:
        """Commit all operations atomically.

        F05: Validates table names against allowlist, persists vault identity
        with keyed digest on blobs, and restricts audit reasons to content-free
        enum values. Subtype closure_marker fields are preserved during version
        close/invalidation.

        F07 (FIX): Rejects content writes before any SQL mutation when
        _authority is None or not valid.  The only path that supplies a
        valid authority is the package-owned fixture loader.
        """
        # ADR-021: Blob persistence is a PRE_REAL_DATA capability and remains
        # unavailable even to the bundled fixture path during E00.
        if uow.blob_operations:
            raise UnitOfWorkError(
                "FEATURE_DEFERRED_PRE_REAL_DATA: blob writes are disabled by ADR-021"
            )

        # F07: Block ordinary content writes before any side effect.
        # The package-owned fixture loader must supply a validated authority.
        if uow.operations or uow.blob_operations:
            if self._authority is None:
                raise UnitOfWorkError(
                    "CONTENT_WRITE_REJECTED: no fixture authority supplied. "
                    "Direct writes are not permitted in synthetic-only F0. "
                    "Use the package-owned fixture loader to write content."
                )
            # Validate the authority is a real FixtureAuthority, not a forged one
            if not _is_valid_authority(self._authority):
                raise UnitOfWorkError(
                    "CONTENT_WRITE_REJECTED: invalid or forged fixture authority. "
                    "Authority tokens cannot be self-issued."
                )
        now = datetime.datetime.now(datetime.UTC).isoformat()
        cur = self._con.cursor()

        try:
            # F05: validate all table names before any mutation
            for op in uow.operations:
                if op.table not in ALLOWED_TABLES:
                    raise UnitOfWorkError(f"Table '{op.table}' is not in the storage allowlist")

            # V10 owns policy identity internally. A first version establishes
            # its immutable mapping; later versions must prove the same pair
            # before any active version is closed or a new row is inserted.
            has_policy_registry = cur.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='policy_identities'"
            ).fetchone()
            if has_policy_registry:
                for op in uow.operations:
                    if op.table != "data_policies":
                        continue
                    policy_id = str(op.data["policy_id"])
                    record_id = str(op.record_id)
                    cur.execute(
                        "INSERT OR IGNORE INTO policy_identities(policy_id, record_id) VALUES (?, ?)",
                        (policy_id, record_id),
                    )
                    pair = cur.execute(
                        "SELECT record_id FROM policy_identities WHERE policy_id=?",
                        (policy_id,),
                    ).fetchone()
                    if pair != (record_id,):
                        raise UnitOfWorkError("POLICY_IDENTITY_MISMATCH")

            # 1. Close previous active versions — preserve closure_marker
            for op in uow.operations:
                if op.table in VERSIONED_TABLES:
                    cur.execute(
                        f"UPDATE {op.table} SET tx_to = ?, is_active = 0 "
                        f"WHERE record_id = ? AND is_active = 1",
                        (now, str(op.record_id)),
                    )

            # 2. Insert new version rows — inject system-managed columns (F05)
            for op in uow.operations:
                columns = list(op.data.keys())
                # F05: reject any system-column in data
                for col in columns:
                    if col in _SYSTEM_COLUMNS:
                        raise UnitOfWorkError(
                            f"Column '{col}' is system-managed and must not appear in data dict"
                        )
                # Inject system-managed columns automatically
                full_data = dict(op.data)
                full_data["record_id"] = str(op.record_id)
                full_data["tx_from"] = now
                full_data["is_active"] = 1
                full_data["created_at"] = now
                # version_id only for tables that actually have the column
                if op.table in VERSIONED_TABLES:
                    full_data["version_id"] = str(op.version_id)
                    if op.previous_version_id:
                        full_data["previous_version_id"] = op.previous_version_id

                all_columns = list(full_data.keys())
                placeholders = ", ".join("?" for _ in full_data)
                values = list(full_data.values())
                cur.execute(
                    f"INSERT INTO {op.table} ({', '.join(all_columns)}) VALUES ({placeholders})",
                    values,
                )

            # 3. Encrypt and store blobs — with vault identity keyed digest (F05)
            if self._blob_aead and uow.blob_operations:
                for bop in uow.blob_operations:
                    envelope = self._blob_aead.encrypt(bop.plaintext, bop.blob_id, bop.vault_id)
                    bop.envelope = envelope
                    sha256 = hashlib.sha256(bop.plaintext).hexdigest()

                    # F05: keyed digest — HMAC-SHA256(vault_digest_key, blob_sha256)
                    # Persists vault identity in the stored blob so that a
                    # blob copied to another vault fails verification.
                    # F05 (FIX): vault_keyed_digest MUST be non-empty.
                    # A blob write with an empty vault digest key is rejected.
                    if not self._vault_digest_key:
                        raise UnitOfWorkError(
                            "Cannot write blob: vault digest key is empty or unconfigured"
                        )
                    vault_keyed_digest = hmac.new(
                        self._vault_digest_key,
                        sha256.encode("utf-8"),
                        "sha256",
                    ).hexdigest()

                    # F05 (FIX): Insert blob with state='created' first, then
                    # transition to 'stored'.  CREATED is the only valid initial
                    # state for new blobs.
                    cur.execute(
                        """INSERT INTO blobs (blob_id, record_id, vault_id, envelope_version,
                           key_version, nonce, ciphertext, aad, wrapped_data_key,
                           data_key_nonce, blob_sha256, byte_length, state,
                           created_at, tx_from, is_active, vault_keyed_digest)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'created', ?, ?, 1, ?)""",
                        (
                            str(bop.blob_id),
                            str(bop.record_id),
                            str(bop.vault_id),
                            envelope.envelope_version,
                            envelope.key_version,
                            envelope.nonce,
                            envelope.ciphertext,
                            envelope.aad,
                            envelope.wrapped_data_key,
                            envelope.data_key_nonce,
                            sha256,
                            len(bop.plaintext),
                            now,
                            now,
                            vault_keyed_digest,
                        ),
                    )

            # 4. Write audit events — F05: content-free enum only
            for op in uow.operations:
                # Validate change_reason before writing
                if op.change_reason not in ALLOWED_AUDIT_REASONS:
                    raise UnitOfWorkError(
                        f"Audit reason '{op.change_reason}' is not in the allowed enum"
                    )
                event_kind = AUDIT_EVENT_KIND_WRITE

                event_id = AuditEventId(generate_id())
                cur.execute(
                    """INSERT INTO audit_events (event_id, event_kind, occurred_at,
                       actor_id, target_record_ids, operation, outcome, reason,
                       version_id, created_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        str(event_id),
                        event_kind,
                        now,
                        uow.actor_id,
                        json.dumps([str(op.record_id)]),
                        op.change_reason,
                        "committed",
                        op.change_reason,
                        str(op.version_id),
                        now,
                    ),
                )

            self._con.commit()
            uow.complete()

        except UnitOfWorkError:
            self._con.rollback()
            raise
        except Exception:
            self._con.rollback()
            raise

    def _rollback(self, uow: UnitOfWork) -> None:
        """Rollback the unit of work."""
        try:
            self._con.rollback()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Crash-safe blob protocol
# ---------------------------------------------------------------------------


@dataclass
class BlobVerification:
    """Result of verifying a stored blob."""

    blob_id: BlobId
    verified: bool
    expected_sha256: str
    actual_sha256: str | None = None
    error: str = ""


def verify_blob(connection: Any, blob_id: BlobId, blob_aead: BlobAEAD) -> BlobVerification:
    """Verify a stored blob by decrypting and checking SHA-256."""
    cur = connection.cursor()
    cur.execute(
        "SELECT blob_id, nonce, ciphertext, wrapped_data_key, data_key_nonce, blob_sha256, state FROM blobs WHERE blob_id = ? AND is_active = 1",
        (str(blob_id),),
    )
    row = cur.fetchone()
    if row is None:
        return BlobVerification(
            blob_id=blob_id, verified=False, expected_sha256="", error="Blob not found"
        )

    blob_id_str, nonce, ciphertext, wrapped_data_key, data_key_nonce, expected_sha256, state = row

    if state == BlobState.DELETED:
        return BlobVerification(
            blob_id=blob_id, verified=False, expected_sha256=expected_sha256, error="Blob deleted"
        )

    try:
        # Reconstruct envelope and decrypt
        from psyche_os.crypto.envelope import BlobEnvelope

        envelope = BlobEnvelope(
            blob_id=BlobId(blob_id_str),
            vault_id=VaultId(""),  # Unknown at this level
            ciphertext=ciphertext,
            nonce=nonce,
            wrapped_data_key=wrapped_data_key or b"",
            data_key_nonce=data_key_nonce or b"",
        )
        plaintext = blob_aead.decrypt(envelope)
        actual_sha256 = hashlib.sha256(plaintext).hexdigest()

        verified = actual_sha256 == expected_sha256

        if verified:
            cur.execute(
                "UPDATE blobs SET state = ? WHERE blob_id = ?",
                (BlobState.VERIFIED, blob_id_str),
            )
            connection.commit()

        return BlobVerification(
            blob_id=blob_id,
            verified=verified,
            expected_sha256=expected_sha256,
            actual_sha256=actual_sha256,
            error="" if verified else "SHA-256 mismatch",
        )
    except Exception as exc:
        return BlobVerification(
            blob_id=blob_id,
            verified=False,
            expected_sha256=expected_sha256,
            error=str(exc),
        )
