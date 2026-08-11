"""Unit tests for temporal layer."""

import datetime

import pytest

from psyche_os.temporal.temporal import (
    CertaintyClass,
    Precision,
    TemporalRole,
    TemporalValue,
    ValueKind,
    interval_from_precision,
)


class TestTemporalValue:
    def test_construction_minimal(self) -> None:
        tv = TemporalValue(
            value_kind=ValueKind.UNKNOWN,
            precision=Precision.UNKNOWN,
        )
        assert tv.is_valid() is True
        assert tv.value_kind == ValueKind.UNKNOWN

    def test_instant_construction(self) -> None:
        tv = TemporalValue(
            temporal_role=TemporalRole.OCCURRED,
            value_kind=ValueKind.INSTANT,
            lower_value=datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC),
            precision=Precision.DAY,
        )
        assert tv.is_valid() is True
        assert tv.value_kind == ValueKind.INSTANT

    def test_closed_interval_construction(self) -> None:
        tv = TemporalValue(
            value_kind=ValueKind.CLOSED_INTERVAL,
            lower_value=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            upper_value=datetime.datetime(2026, 1, 31, tzinfo=datetime.UTC),
            precision=Precision.DAY,
        )
        assert tv.is_valid() is True

    def test_invalid_closed_interval_missing_upper(self) -> None:
        tv = TemporalValue(
            value_kind=ValueKind.CLOSED_INTERVAL,
            lower_value=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            upper_value=None,
            precision=Precision.DAY,
        )
        assert tv.is_valid() is False

    def test_invalid_lower_gt_upper(self) -> None:
        tv = TemporalValue(
            value_kind=ValueKind.CLOSED_INTERVAL,
            lower_value=datetime.datetime(2026, 2, 1, tzinfo=datetime.UTC),
            upper_value=datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC),
            precision=Precision.DAY,
        )
        assert tv.is_valid() is False

    def test_invalid_instant_no_value(self) -> None:
        tv = TemporalValue(
            value_kind=ValueKind.INSTANT,
            lower_value=None,
            precision=Precision.DAY,
        )
        assert tv.is_valid() is False

    def test_as_dict(self) -> None:
        tv = TemporalValue(
            temporal_role=TemporalRole.OCCURRED,
            value_kind=ValueKind.INSTANT,
            lower_value=datetime.datetime(2026, 1, 15, tzinfo=datetime.UTC),
            precision=Precision.DAY,
            original_literal="Jan 15, 2026",
        )
        d = tv.as_dict()
        assert d["value_kind"] == "instant"
        assert d["precision"] == "day"
        assert d["original_literal"] == "Jan 15, 2026"
        assert d["temporal_role"] == "occurred"

    def test_frozen_dataclass(self) -> None:
        tv = TemporalValue()
        with pytest.raises(Exception):
            tv.precision = Precision.DAY  # type: ignore[misc]


class TestPrecisionLevels:
    def test_core_precision_levels(self) -> None:
        precisions = [p.value for p in Precision]
        assert "year" in precisions
        assert "month" in precisions
        assert "day" in precisions
        assert "hour" in precisions
        assert "minute" in precisions
        assert "second" in precisions

    def test_season_precision(self) -> None:
        result = interval_from_precision(
            datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC),
            Precision.SEASON,
        )
        assert result is not None
        assert len(result) == 2

    def test_decade_precision(self) -> None:
        # UNKNOWN precision returns None — does NOT fabricate a point interval
        result = interval_from_precision(
            datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC),
            Precision.UNKNOWN,
        )
        assert result is None  # Unknown time is preserved as unknown


class TestValueKind:
    def test_value_kinds(self) -> None:
        kinds = [k.value for k in ValueKind]
        assert "instant" in kinds
        assert "closed_interval" in kinds
        assert "open_interval" in kinds
        assert "calendar_period" in kinds
        assert "recurring" in kinds
        assert "unknown" in kinds


class TestCertaintyClass:
    def test_certainty_classes(self) -> None:
        classes = [c.value for c in CertaintyClass]
        assert "certain" in classes
        assert "probable" in classes
        assert "possible" in classes
        assert "unknown" in classes
        assert "disputed" in classes


class TestIntervalFromPrecision:
    def test_year_precision(self) -> None:
        dt = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        start, end = interval_from_precision(dt, Precision.YEAR)
        assert start == datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        assert end == datetime.datetime(2027, 1, 1, tzinfo=datetime.UTC)

    def test_month_precision(self) -> None:
        dt = datetime.datetime(2026, 6, 15, tzinfo=datetime.UTC)
        start, end = interval_from_precision(dt, Precision.MONTH)
        assert start == datetime.datetime(2026, 6, 1, tzinfo=datetime.UTC)
        assert end == datetime.datetime(2026, 7, 1, tzinfo=datetime.UTC)

    def test_day_precision(self) -> None:
        dt = datetime.datetime(2026, 6, 15, 10, 30, tzinfo=datetime.UTC)
        start, end = interval_from_precision(dt, Precision.DAY)
        # start is unchanged (DAY doesn't normalize start)
        assert start == dt
        assert end == datetime.datetime(2026, 6, 16, tzinfo=datetime.UTC)

    def test_hour_precision(self) -> None:
        dt = datetime.datetime(2026, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        start, end = interval_from_precision(dt, Precision.HOUR)
        # start is unchanged
        assert start == dt
        assert end == datetime.datetime(2026, 6, 15, 15, 0, 0, tzinfo=datetime.UTC)

    def test_minute_precision(self) -> None:
        dt = datetime.datetime(2026, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        start, end = interval_from_precision(dt, Precision.MINUTE)
        # start is unchanged
        assert start == dt
        assert end == datetime.datetime(2026, 6, 15, 14, 31, 0, tzinfo=datetime.UTC)

    def test_second_precision(self) -> None:
        dt = datetime.datetime(2026, 6, 15, 14, 30, 45, tzinfo=datetime.UTC)
        start, end = interval_from_precision(dt, Precision.SECOND)
        assert start == dt
        assert end == dt + datetime.timedelta(seconds=1)
