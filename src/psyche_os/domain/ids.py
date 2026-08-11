"""Opaque random 128-bit identifiers for all canonical aggregates.

Identifiers do not encode content, time, person, or source.
External string form is UUID-compatible but generation uses CSPRNG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import NewType
import uuid

# Core ID types — opaque 128-bit
VaultId = NewType("VaultId", str)
SubjectId = NewType("SubjectId", str)
ActorId = NewType("ActorId", str)
RecordId = NewType("RecordId", str)
VersionId = NewType("VersionId", str)
BlobId = NewType("BlobId", str)
DerivationId = NewType("DerivationId", str)
PolicyId = NewType("PolicyId", str)
AuditEventId = NewType("AuditEventId", str)
DeletionRequestId = NewType("DeletionRequestId", str)
DeletionPlanId = NewType("DeletionPlanId", str)
BackupId = NewType("BackupId", str)
ExportId = NewType("ExportId", str)
MigrationId = NewType("MigrationId", str)
KnowledgeSourceId = NewType("KnowledgeSourceId", str)
KnowledgeSnapshotId = NewType("KnowledgeSnapshotId", str)
FixturePackId = NewType("FixturePackId", str)


def generate_id() -> str:
    """Generate a new opaque random 128-bit identifier (UUID4 string)."""
    return str(uuid.uuid4())


@dataclass(frozen=True, slots=True)
class OpaqueId:
    """Wrapper ensuring an ID was intentionally generated, not fabricated."""

    value: str = field(default_factory=generate_id)

    def __str__(self) -> str:
        return self.value

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OpaqueId):
            return self.value == other.value
        if isinstance(other, str):
            return self.value == other
        return False
