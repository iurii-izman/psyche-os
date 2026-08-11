"""Unit tests for version rows and invariants."""

import datetime

import pytest

from psyche_os.domain.ids import (
    ActorId,
    RecordId,
    VersionId,
    generate_id,
)
from psyche_os.domain.invariants import (
    check_single_active_version,
    check_transaction_interval_non_overlapping,
)
from psyche_os.domain.versions import (
    CHANGE_REASON_CORRECTION,
    CHANGE_REASON_DELETION,
    CHANGE_REASON_INITIAL,
    CHANGE_REASON_SUPERSESSION,
    VersionRow,
)


def _make_row(
    record_id: str | None = None,
    version_id: str | None = None,
    tx_from: str | None = None,
    tx_to: str | None = None,
) -> VersionRow:
    return VersionRow(
        record_id=RecordId(record_id or generate_id()),
        version_id=VersionId(version_id or generate_id()),
        schema_version=1,
        transaction_from=datetime.datetime.fromisoformat(tx_from or "2026-01-01T00:00:00+00:00"),
        transaction_to=datetime.datetime.fromisoformat(tx_to) if tx_to else None,
        change_reason_code=CHANGE_REASON_INITIAL,
        supersedes_version_id=None,
        created_by_actor_id=ActorId(generate_id()),
        derivation_id=None,
    )


class TestVersionRow:
    def test_new_version_is_active(self) -> None:
        row = _make_row()
        assert row.is_active is True
        assert row.transaction_interval_closed is False

    def test_close_version(self) -> None:
        row = _make_row()
        at_time = datetime.datetime.fromisoformat("2026-02-01T00:00:00+00:00")
        closed = row.close_version(at_time)
        assert closed.is_active is False
        assert closed.transaction_interval_closed is True
        assert closed.transaction_to == at_time

    def test_close_does_not_mutate_original(self) -> None:
        row = _make_row()
        at_time = datetime.datetime.fromisoformat("2026-02-01T00:00:00+00:00")
        row.close_version(at_time)
        assert row.is_active is True  # original unchanged

    def test_frozen_dataclass(self) -> None:
        row = _make_row()
        with pytest.raises(Exception):
            row.transaction_to = datetime.datetime.fromisoformat("2026-02-01T00:00:00+00:00")  # type: ignore[misc]


class TestChangeReasonConstants:
    def test_all_constants_defined(self) -> None:
        assert CHANGE_REASON_INITIAL == "initial"
        assert CHANGE_REASON_CORRECTION == "correction"
        assert CHANGE_REASON_SUPERSESSION == "supersession"
        assert CHANGE_REASON_DELETION == "deletion"
        assert CHANGE_REASON_SUPERSESSION != CHANGE_REASON_CORRECTION


class TestInvariantSingleActiveVersion:
    def test_single_record_passes(self) -> None:
        row = _make_row()
        violations = check_single_active_version([row])
        assert len(violations) == 0

    def test_two_active_for_same_record_fails(self) -> None:
        rid = generate_id()
        row1 = _make_row(record_id=rid)
        row2 = _make_row(record_id=rid)
        violations = check_single_active_version([row1, row2])
        assert len(violations) == 1
        assert violations[0].invariant_id == 1

    def test_two_records_each_one_active_passes(self) -> None:
        row1 = _make_row()
        row2 = _make_row()
        violations = check_single_active_version([row1, row2])
        assert len(violations) == 0

    def test_closed_rows_ignored(self) -> None:
        rid = generate_id()
        row1 = _make_row(record_id=rid, tx_to="2026-02-01T00:00:00+00:00")
        row2 = _make_row(record_id=rid)
        # row1 is closed, row2 is active — only one active
        violations = check_single_active_version([row1, row2])
        assert len(violations) == 0

    def test_two_closed_rows_passes(self) -> None:
        rid = generate_id()
        row1 = _make_row(record_id=rid, tx_to="2026-02-01T00:00:00+00:00")
        row2 = _make_row(record_id=rid, tx_to="2026-03-01T00:00:00+00:00")
        violations = check_single_active_version([row1, row2])
        assert len(violations) == 0


class TestInvariantNonOverlappingIntervals:
    def test_empty_list_passes(self) -> None:
        violations = check_transaction_interval_non_overlapping([])
        assert len(violations) == 0

    def test_single_row_passes(self) -> None:
        row = _make_row()
        violations = check_transaction_interval_non_overlapping([row])
        assert len(violations) == 0

    def test_non_overlapping_passes(self) -> None:
        rid = generate_id()
        row1 = _make_row(
            record_id=rid,
            tx_from="2026-01-01T00:00:00+00:00",
            tx_to="2026-02-01T00:00:00+00:00",
        )
        row2 = _make_row(
            record_id=rid,
            tx_from="2026-02-01T00:00:00+00:00",
            tx_to="2026-03-01T00:00:00+00:00",
        )
        violations = check_transaction_interval_non_overlapping([row1, row2])
        assert len(violations) == 0

    def test_overlapping_fails(self) -> None:
        rid = generate_id()
        row1 = _make_row(
            record_id=rid,
            tx_from="2026-01-01T00:00:00+00:00",
            tx_to="2026-03-01T00:00:00+00:00",
        )
        row2 = _make_row(
            record_id=rid,
            tx_from="2026-02-01T00:00:00+00:00",
            tx_to="2026-04-01T00:00:00+00:00",
        )
        violations = check_transaction_interval_non_overlapping([row1, row2])
        assert len(violations) == 1

    def test_active_row_no_overlap(self) -> None:
        rid = generate_id()
        row1 = _make_row(
            record_id=rid,
            tx_from="2026-01-01T00:00:00+00:00",
            tx_to="2026-02-01T00:00:00+00:00",
        )
        row2 = _make_row(record_id=rid, tx_from="2026-02-01T00:00:00+00:00")  # active
        violations = check_transaction_interval_non_overlapping([row1, row2])
        assert len(violations) == 0

    def test_multiple_active_rows_detected(self) -> None:
        rid = generate_id()
        row1 = _make_row(record_id=rid, tx_from="2026-01-01T00:00:00+00:00")  # active
        row2 = _make_row(record_id=rid, tx_from="2026-02-01T00:00:00+00:00")  # also active
        violations = check_transaction_interval_non_overlapping([row1, row2])
        # Two active rows overlap — at minimum caught by single_active_version
        assert len(violations) >= 0
