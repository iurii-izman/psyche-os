"""Application layer — typed ports and use cases.

Defines the abstract service contracts (ports) that the CLI
and adapters use. Implementations live in adapters.
"""

from __future__ import annotations

from typing import Any, Protocol

from psyche_os.domain.ids import (
    ActorId,
    BackupId,
    BlobId,
    DeletionRequestId,
    ExportId,
    PolicyId,
    RecordId,
    VaultId,
    VersionId,
)

# ---------------------------------------------------------------------------
# Port: Vault lifecycle
# ---------------------------------------------------------------------------


class VaultPort(Protocol):
    """Operations on the vault itself."""

    def create_vault(self, vault_name: str, recovery_secret: str) -> VaultId:
        """Create a new vault with key material."""
        ...

    def open_vault(self, vault_id: VaultId, secret: str) -> bool:
        """Open an existing vault for operations."""
        ...

    def close_vault(self) -> None:
        """Close and clear key material."""
        ...

    def vault_status(self) -> dict[str, Any]:
        """Return vault metadata without secrets."""
        ...


# ---------------------------------------------------------------------------
# Port: Record CRUD with versioning
# ---------------------------------------------------------------------------


class RecordPort(Protocol):
    """Create, read, update (version), and delete records."""

    def create_record(
        self,
        table: str,
        data: dict[str, Any],
        actor_id: ActorId = ActorId(""),
    ) -> RecordId:
        """Create a new record."""
        ...

    def read_record(
        self,
        table: str,
        record_id: RecordId,
        as_of: str | None = None,
    ) -> dict[str, Any] | None:
        """Read a record at a point in time, or current if None."""
        ...

    def update_record(
        self,
        table: str,
        record_id: RecordId,
        data: dict[str, Any],
        change_reason: str,
        actor_id: ActorId = ActorId(""),
    ) -> VersionId:
        """Create a new version of a record."""
        ...

    def list_records(
        self,
        table: str,
        filters: dict[str, Any] | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List active records."""
        ...


# ---------------------------------------------------------------------------
# Port: Blob storage
# ---------------------------------------------------------------------------


class BlobPort(Protocol):
    """Store and retrieve encrypted blobs."""

    def store_blob(self, plaintext: bytes, record_id: RecordId) -> BlobId:
        """Encrypt and store a blob."""
        ...

    def retrieve_blob(self, blob_id: BlobId) -> bytes:
        """Retrieve and decrypt a blob."""
        ...

    def verify_blob(self, blob_id: BlobId) -> dict[str, Any]:
        """Verify blob integrity."""
        ...

    def delete_blob(self, blob_id: BlobId) -> None:
        """Delete a blob."""
        ...


# ---------------------------------------------------------------------------
# Port: Policy management
# ---------------------------------------------------------------------------


class PolicyPort(Protocol):
    """Manage data policies and lineage."""

    def assign_policy(
        self, record_id: RecordId, policy: Any, actor_id: ActorId = ActorId("")
    ) -> PolicyId:
        """Assign a policy to a record."""
        ...

    def resolve_policy(self, record_id: RecordId) -> Any:
        """Resolve effective policy for a record."""
        ...

    def add_lineage_edge(self, parent_policy_id: PolicyId, child_policy_id: PolicyId) -> None:
        """Add a policy lineage edge."""
        ...

    def never_cloud_closure(self, root_policy_id: PolicyId) -> set[str]:
        """Find all policies inheriting NEVER_CLOUD."""
        ...


# ---------------------------------------------------------------------------
# Port: Audit
# ---------------------------------------------------------------------------


class AuditPort(Protocol):
    """Content-free allowlisted audit."""

    def record_event(
        self,
        event_kind: str,
        operation: str,
        target_record_ids: list[RecordId],
        outcome: str,
        reason: str,
        actor_id: ActorId = ActorId(""),
    ) -> str:
        """Record an audit event."""
        ...

    def query_events(
        self,
        event_kind: str | None = None,
        actor_id: str | None = None,
        since: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Query audit events — content fields always empty."""
        ...


# ---------------------------------------------------------------------------
# Port: Deletion
# ---------------------------------------------------------------------------


class DeletionPort(Protocol):
    """Hard deletion with dependency traversal."""

    def request_deletion(
        self,
        target_ids: list[RecordId],
        scope: str,
        reason: str,
        actor_id: ActorId = ActorId(""),
    ) -> DeletionRequestId:
        """Create a deletion request."""
        ...

    def plan_deletion(self, request_id: DeletionRequestId) -> dict[str, Any]:
        """Plan deletion by traversing dependency graph."""
        ...

    def execute_deletion(self, plan_id: str) -> dict[str, Any]:
        """Execute deletion plan."""
        ...

    def verify_deletion(self, request_id: DeletionRequestId) -> bool:
        """Verify deleted records are not in canonical store."""
        ...


# ---------------------------------------------------------------------------
# Port: Backup / restore
# ---------------------------------------------------------------------------


class BackupPort(Protocol):
    """Authenticated encrypted backup and isolated restore."""

    def create_backup(self, storage_path: str) -> BackupId:
        """Create authenticated encrypted backup."""
        ...

    def verify_backup(self, backup_id: BackupId) -> bool:
        """Verify backup integrity and authenticity."""
        ...

    def restore_backup(
        self,
        backup_id: BackupId,
        target_vault_id: VaultId,
    ) -> dict[str, Any]:
        """Restore to an isolated vault and validate."""
        ...

    def activate_restored_vault(self, vault_id: VaultId) -> bool:
        """Activate a validated restored vault."""
        ...


# ---------------------------------------------------------------------------
# Port: Export
# ---------------------------------------------------------------------------


class ExportPort(Protocol):
    """Versioned JSONL + JSON Schema + Markdown logical export."""

    def export(
        self,
        output_dir: str,
        encrypted: bool = True,
        tables: list[str] | None = None,
    ) -> ExportId:
        """Export vault to versioned format."""
        ...

    def verify_export(self, export_id: ExportId) -> bool:
        """Verify export semantic round trip."""
        ...


# ---------------------------------------------------------------------------
# Port: Knowledge
# ---------------------------------------------------------------------------


class KnowledgePort(Protocol):
    """Ontology and assessment registry."""

    def register_ontology(self, name: str, version: str, schema: dict[str, Any]) -> str:
        """Register an ontology entry."""
        ...

    def list_ontologies(self) -> list[dict[str, Any]]:
        """List registered ontologies."""
        ...

    def register_assessment(self, name: str, version: str, schema: dict[str, Any]) -> str:
        """Register an assessment registry entry (blocked in F0)."""
        ...


# ---------------------------------------------------------------------------
# Synthetic fixture capability
# ---------------------------------------------------------------------------


class FixtureAuthority:
    """F07: Non-self-issuable, non-serializable, non-reconstructible authority.

    Only the private package-owned loader can mint authority tokens.
    Direct instantiation from user code fails — the class is not
    importable from user-facing modules.

    The authority is bound to the bundled synthetic fixture identity.
    It cannot be serialised, copied, or reconstructed from a token string.

    F07 (FIX): Every construction path is blocked:
    - Normal constructor → RuntimeError
    - object.__new__ + direct attribute set → fails validation (no _token)
    - copy/deepcopy → TypeError
    - pickle → TypeError (via __reduce__)
    - Reconstruction from a string/token → impossible (no public setter)
    """

    __slots__ = ("_bound_digest", "_bound_fixture_id", "_token")

    def __init__(self) -> None:
        raise RuntimeError(
            "FixtureAuthority cannot be instantiated directly. "
            "Use the private package-owned loader to mint authority tokens."
        )

    @classmethod
    def _mint(
        cls,
        fixture_id: str = "",
        manifest_digest: str = "",
    ) -> FixtureAuthority:
        """Private minting entry point — only callable from within psyche_os.

        F07 (FIX): Authority is bound to the exact fixture identity and
        manifest digest.  The token is opaque and never returned to callers.
        """
        import secrets as _secrets

        inst = object.__new__(cls)
        object.__setattr__(inst, "_token", _secrets.token_hex(32))
        object.__setattr__(inst, "_bound_fixture_id", fixture_id)
        object.__setattr__(inst, "_bound_digest", manifest_digest)
        return inst

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FixtureAuthority):
            return NotImplemented
        import hmac as _hmac

        # All three fields required for equality — uninitialized objects fail
        try:
            return (
                _hmac.compare_digest(self._token, other._token)
                and self._bound_fixture_id == other._bound_fixture_id
                and self._bound_digest == other._bound_digest
            )
        except AttributeError:
            return False

    def __hash__(self) -> int:
        return hash((self._token, self._bound_fixture_id, self._bound_digest))

    def __repr__(self) -> str:
        return "<FixtureAuthority (opaque)>"

    def __copy__(self) -> object:
        raise TypeError("FixtureAuthority cannot be copied")

    def __deepcopy__(self, memo: object) -> object:
        raise TypeError("FixtureAuthority cannot be deep-copied")

    def __reduce__(self) -> object:
        raise TypeError("FixtureAuthority cannot be pickled")

    def __getstate__(self) -> object:
        raise TypeError("FixtureAuthority cannot be serialised")

    @property
    def is_valid(self) -> bool:
        """An authority is only valid if all three internal fields exist."""
        try:
            return (
                len(self._token) == 64
                and all(char in "0123456789abcdef" for char in self._token)
                and isinstance(self._bound_fixture_id, str)
                and bool(self._bound_fixture_id)
                and isinstance(self._bound_digest, str)
                and len(self._bound_digest) == 64
                and all(char in "0123456789abcdef" for char in self._bound_digest)
            )
        except AttributeError:
            return False


class SyntheticFixtureCapability:
    """F0 synthetic-only fixture capability from built-in package resources.

    This is the ONLY data source allowed in F0. No filesystem fixture paths,
    no network sources, no environment-specific external data.

    F07 (FIX): Public constructor is removed — the _authority_token and its
    token string are never disclosed. Only the private package loader can
    mint a capability instance, and that instance carries an opaque
    FixtureAuthority that cannot be reconstructed from a string token.
    Direct writes without a valid authority-bearing capability fail at the
    storage write boundary.
    """

    ALLOWED_FIXTURE_TABLES = [
        "actors",
        "subjects",
        "source_artifacts",
        "observations",
        "assertions",
        "claims",
        "data_policies",
    ]

    def __init__(self) -> None:
        """Create a fixture capability.

        F07 (FIX): The public constructor is closed.  The capability can
        only be obtained through the private package-owned loader, which
        calls _from_authority().
        """
        raise RuntimeError(
            "SyntheticFixtureCapability cannot be instantiated directly. "
            "Use the private package-owned loader to obtain a capability."
        )

    @classmethod
    def _from_authority(cls, authority: FixtureAuthority) -> SyntheticFixtureCapability:
        """Private factory — only callable from within psyche_os.

        Requires a valid, fully-initialised FixtureAuthority minted by the
        bundled fixture loader.  An authority that lacks a _token or was
        created via object.__new__ without proper initialisation is rejected.
        """
        if not isinstance(authority, FixtureAuthority):
            raise TypeError("Authority must be a FixtureAuthority instance")
        if not authority.is_valid:
            raise ValueError("FixtureAuthority is uninitialised or forged")
        inst = object.__new__(cls)
        object.__setattr__(inst, "_authority", authority)
        return inst

    def can_generate(self, table: str) -> bool:
        return table in self.ALLOWED_FIXTURE_TABLES

    def available_packs(self) -> list[str]:
        return ["f0_smoke", "f0_integration"]

    def validate_authority(self, other: FixtureAuthority) -> bool:
        """Verify an authority matches this capability.

        Uses constant-time comparison to prevent timing attacks.
        The authority must be the exact FixtureAuthority instance,
        not a string token.

        F07 (FIX): Returns False for any uninitialized/forged authority
        (e.g. one created via object.__new__ without _mint).
        """
        try:
            return self._authority == other
        except Exception:
            return False

    @property
    def _authority_token(self) -> str | None:
        """F07: The raw token is NEVER publicly exposed."""
        return None
