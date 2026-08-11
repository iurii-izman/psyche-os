"""Temporal layer — rich domain time.

Implements multi-clock temporal assertions:
- occurred, observed, reported, recorded, asserted, effective, scheduled
- instant, closed_interval, open_interval, calendar_period, recurring, unknown
- precision levels and timezone known/assumed
- Never invents timestamps from fuzzy descriptions
- FIX (F09): UNKNOWN precision returns None — no fabricated point interval
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime
from enum import Enum
from typing import Any


class TemporalRole(str, Enum):
    OCCURRED = "occurred"
    OBSERVED = "observed"
    REPORTED = "reported"
    RECORDED = "recorded"
    ASSERTED = "asserted"
    EFFECTIVE = "effective"
    SCHEDULED = "scheduled"


class ValueKind(str, Enum):
    INSTANT = "instant"
    CLOSED_INTERVAL = "closed_interval"
    OPEN_INTERVAL = "open_interval"
    CALENDAR_PERIOD = "calendar_period"
    RECURRING = "recurring"
    UNKNOWN = "unknown"


class Precision(str, Enum):
    SECOND = "second"
    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"
    MONTH = "month"
    SEASON = "season"
    YEAR = "year"
    LIFE_PERIOD = "life_period"
    UNKNOWN = "unknown"


class CertaintyClass(str, Enum):
    CERTAIN = "certain"
    PROBABLE = "probable"
    POSSIBLE = "possible"
    UNKNOWN = "unknown"
    DISPUTED = "disputed"


@dataclass(frozen=True, slots=True)
class TemporalValue:
    """An immutable temporal assertion value.

    "summer 2008" is stored as an interval with seasonal precision,
    not converted to 2008-07-01T00:00:00Z. Unknown time stays unknown.
    """

    temporal_role: TemporalRole = TemporalRole.OCCURRED
    value_kind: ValueKind = ValueKind.UNKNOWN
    lower_value: datetime.datetime | None = None
    upper_value: datetime.datetime | None = None
    lower_inclusive: bool = True
    upper_inclusive: bool = False
    precision: Precision = Precision.UNKNOWN
    original_literal: str = ""
    timezone_known: bool = False
    timezone_name: str = ""
    calendar: str = "gregorian"
    source_actor_id: str = ""
    assertion_actor_id: str = ""
    certainty_class: CertaintyClass = CertaintyClass.UNKNOWN
    certainty_rationale: str = ""

    def is_valid(self) -> bool:
        """Validate temporal semantics."""
        # Unknown value kind is always valid
        if self.value_kind == ValueKind.UNKNOWN:
            return True
        if self.precision == Precision.UNKNOWN:
            # Unknown precision with a value_kind — values may be kept as-is
            return True
        if self.value_kind == ValueKind.INSTANT and self.lower_value is None:
            return False
        if self.value_kind in (ValueKind.CLOSED_INTERVAL, ValueKind.OPEN_INTERVAL):
            if self.lower_value is None:
                return False
            if self.value_kind == ValueKind.CLOSED_INTERVAL and self.upper_value is None:
                return False
        if self.lower_value is not None and self.upper_value is not None:
            if self.lower_value > self.upper_value:
                return False
        return True

    def is_unknown(self) -> bool:
        """Whether this temporal value represents an unknown time.

        Unknown time is preserved as unknown — never fabricated into a point.
        """
        return self.value_kind == ValueKind.UNKNOWN or self.precision == Precision.UNKNOWN

    def as_dict(self) -> dict[str, Any]:
        """Serialize to stable dict for JSON/JSONL."""
        return {
            "temporal_role": self.temporal_role.value,
            "value_kind": self.value_kind.value,
            "lower_value": self.lower_value.isoformat() if self.lower_value else None,
            "upper_value": self.upper_value.isoformat() if self.upper_value else None,
            "lower_inclusive": self.lower_inclusive,
            "upper_inclusive": self.upper_inclusive,
            "precision": self.precision.value,
            "original_literal": self.original_literal,
            "timezone_known": self.timezone_known,
            "timezone_name": self.timezone_name,
            "calendar": self.calendar,
            "certainty_class": self.certainty_class.value,
            "certainty_rationale": self.certainty_rationale,
        }


def interval_from_precision(
    start: datetime.datetime,
    precision: Precision,
) -> tuple[datetime.datetime, datetime.datetime] | None:
    """Return the half-open interval implied by a precision level.

    Example: precision=MONTH gives [start_of_month, start_of_next_month).

    Returns None for UNKNOWN or LIFE_PERIOD precision — these preserve
    the unknown nature and do NOT fabricate a point interval.
    """
    if precision == Precision.UNKNOWN:
        return None
    if precision == Precision.LIFE_PERIOD:
        return None

    if precision == Precision.SECOND:
        end = start + datetime.timedelta(seconds=1)
    elif precision == Precision.MINUTE:
        end = start.replace(second=0, microsecond=0) + datetime.timedelta(minutes=1)
    elif precision == Precision.HOUR:
        end = start.replace(minute=0, second=0, microsecond=0) + datetime.timedelta(hours=1)
    elif precision == Precision.DAY:
        end = start.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
    elif precision == Precision.MONTH:
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1, day=1)
        else:
            end = start.replace(month=start.month + 1, day=1)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
        start = start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif precision == Precision.SEASON:
        month = start.month
        if month in (12, 1, 2):
            if month in (1, 2):
                start = start.replace(year=start.year - 1, month=12, day=1)
            else:
                start = start.replace(month=12, day=1)
            end = start.replace(year=start.year + 1, month=3, day=1)
        elif month in (3, 4, 5):
            start = start.replace(month=3, day=1)
            end = start.replace(month=6, day=1)
        elif month in (6, 7, 8):
            start = start.replace(month=6, day=1)
            end = start.replace(month=9, day=1)
        else:
            start = start.replace(month=9, day=1)
            end = start.replace(month=12, day=1)
        start = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end = end.replace(hour=0, minute=0, second=0, microsecond=0)
    elif precision == Precision.YEAR:
        start = start.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end = start.replace(year=start.year + 1)
    else:
        return None

    return (start, end)
