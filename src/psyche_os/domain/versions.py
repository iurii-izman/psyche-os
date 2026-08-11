"""Immutable version rows and half-open transaction-time intervals.

Every mutable semantic record has:
- stable record_id
- distinct version_id
- schema_version
- half-open [transaction_from, transaction_to) interval
- change_reason_code
- optional supersedes_version_id
- created_by_actor_id
- optional derivation_id

At most one version is active (transaction_to is NULL) per record_id.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime

from psyche_os.domain.ids import (
    ActorId,
    DerivationId,
    RecordId,
    VersionId,
)


@dataclass(frozen=True, slots=True)
class VersionRow:
    """Base class for all versioned semantic records."""

    record_id: RecordId
    version_id: VersionId
    schema_version: int
    transaction_from: datetime.datetime
    transaction_to: datetime.datetime | None  # NULL = currently active
    change_reason_code: str
    supersedes_version_id: VersionId | None
    created_by_actor_id: ActorId
    derivation_id: DerivationId | None

    @property
    def is_active(self) -> bool:
        return self.transaction_to is None

    @property
    def transaction_interval_closed(self) -> bool:
        return self.transaction_to is not None

    def close_version(self, at_time: datetime.datetime) -> VersionRow:
        """Return a new VersionRow with transaction_to set, closing this version.

        F05 (FIX): Uses dataclasses.replace() to preserve all subtype fields
        including non-default values. The previous implementation used
        type(self)(…) with only base-class fields, which dropped subtype
        fields and reset non-default values to defaults.
        """
        if self.transaction_to is not None:
            raise ValueError(f"Version {self.version_id} is already closed")
        if at_time <= self.transaction_from:
            raise ValueError(
                f"Close time {at_time} must be after transaction_from {self.transaction_from}"
            )
        import dataclasses

        return dataclasses.replace(self, transaction_to=at_time)


@dataclass(frozen=True, slots=True)
class VersionConflict:
    """Result when optimistic version check fails."""

    record_id: RecordId
    expected_version_id: VersionId
    actual_active_version_id: VersionId
    detail: str


class VersionConflictError(Exception):
    """Raised when an optimistic version write detects a conflict."""

    def __init__(self, conflict: VersionConflict) -> None:
        super().__init__(
            f"Version conflict on {conflict.record_id}: "
            f"expected {conflict.expected_version_id}, "
            f"actual active {conflict.actual_active_version_id}: "
            f"{conflict.detail}"
        )
        self.conflict = conflict


# Change reason codes
CHANGE_REASON_CORRECTION = "correction"
CHANGE_REASON_SUPERSESSION = "supersession"
CHANGE_REASON_REJECTION = "rejection"
CHANGE_REASON_INVALIDATION = "invalidation"
CHANGE_REASON_DELETION = "deletion"
CHANGE_REASON_DERIVATION = "derivation"
CHANGE_REASON_INITIAL = "initial"

VALID_CHANGE_REASONS = frozenset(
    {
        CHANGE_REASON_CORRECTION,
        CHANGE_REASON_SUPERSESSION,
        CHANGE_REASON_REJECTION,
        CHANGE_REASON_INVALIDATION,
        CHANGE_REASON_DELETION,
        CHANGE_REASON_DERIVATION,
        CHANGE_REASON_INITIAL,
    }
)
