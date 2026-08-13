"""Synthetic-only E05 application service and repository-owned fixture pack."""

from __future__ import annotations

import datetime as dt
import sqlite3
from typing import Any, ClassVar

from psyche_os.domain.longitudinal import (
    ALL_MISSINGNESS_STATES,
    ConfoundCategory,
    ConfoundContext,
    ContextField,
    ContextSource,
    ContextState,
    DescriptiveSummary,
    ExposureState,
    FeedbackExposure,
    LongitudinalEvent,
    MissingnessState,
    ProcessingKind,
    SamplingProtocol,
    ScheduleType,
    SleepRecord,
    SleepSourceType,
    UncertaintyClass,
    describe_window,
)
from psyche_os.storage.migrations import Migrator


class E05LongitudinalError(ValueError):
    """The requested operation is outside the fixed synthetic E05 authority."""


UTC = dt.UTC
WINDOW_START = dt.datetime(2044, 4, 1, tzinfo=UTC)
WINDOW_END = dt.datetime(2044, 4, 15, tzinfo=UTC)
PROTOCOL_ID = "fictional-lantern-activation"
PROTOCOL_VERSION = "1.0.0"


def _protocol() -> SamplingProtocol:
    return SamplingProtocol(
        protocol_id=PROTOCOL_ID,
        version=PROTOCOL_VERSION,
        construct="fictional_activation_level",
        schedule_type=ScheduleType.SIGNAL_CONTINGENT,
        randomized_window_minutes=60,
        max_prompts_per_day=2,
        max_prompts_per_week=10,
        burden_ceiling_minutes_per_day=4,
        duration_days=14,
        pause_rules=("fictional_pause_available",),
        stop_rules=("fictional_stop_on_request", "fictional_stop_at_duration"),
        allowed_context_fields=tuple(ContextField),
        allowed_missingness_reasons=ALL_MISSINGNESS_STATES,
        feedback_policy="bounded_descriptive_summary_only",
        timezone_behavior="store_aware_instants_and_named_utc_fixture_zone",
        travel_behavior="keep_original_schedule_and_mark_travel_context",
        review_trigger="fictional_burden_or_version_change",
        approval_state="fictional_explicitly_approved",
    )


def _event(
    index: int,
    day: int,
    state: MissingnessState,
    *,
    feedback: FeedbackExposure = FeedbackExposure.NONE,
    value: int | None = None,
) -> LongitudinalEvent:
    start = dt.datetime(2044, 4, day, 9, tzinfo=UTC)
    observed_at = start + dt.timedelta(minutes=20) if state is MissingnessState.OBSERVED else None
    return LongitudinalEvent(
        event_id=f"lantern-event-{index:02d}",
        protocol_id=PROTOCOL_ID,
        protocol_version=PROTOCOL_VERSION,
        scheduled_start=start,
        scheduled_end=start + dt.timedelta(hours=1),
        actual_observation_time=observed_at,
        exposure_state=ExposureState.PROMPT_EXPOSED,
        feedback_exposure=feedback,
        context_state=(
            ContextState.UNAVAILABLE
            if state is MissingnessState.UNAVAILABLE_CONTEXT
            else ContextState.RECORDED
        ),
        missingness=state,
        recorded_value=value,
    )


def _events() -> tuple[LongitudinalEvent, ...]:
    return (
        _event(1, 1, MissingnessState.OBSERVED, value=1),
        _event(2, 2, MissingnessState.DELIBERATE_SKIP),
        _event(3, 3, MissingnessState.OBSERVED, value=2),
        _event(4, 4, MissingnessState.DECLINED),
        _event(5, 5, MissingnessState.TECHNICAL_FAILURE),
        _event(6, 6, MissingnessState.UNAVAILABLE_CONTEXT),
        _event(7, 7, MissingnessState.NOT_APPLICABLE),
        # The five-day interval below remains an uninterpolated long gap.
        _event(8, 12, MissingnessState.OBSERVED, feedback=FeedbackExposure.SUMMARY_VIEWED, value=3),
        _event(9, 13, MissingnessState.OBSERVED, value=2),
        _event(10, 14, MissingnessState.OBSERVED, value=4),
    )


def _sleep_records() -> tuple[SleepRecord, ...]:
    base = dt.datetime(2044, 4, 2, 22, tzinfo=UTC)
    return (
        SleepRecord(
            "sleep-diary",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            SleepSourceType.SUBJECTIVE_DIARY,
            base,
            base + dt.timedelta(hours=8),
            430,
            ProcessingKind.DIRECT_RECORD,
        ),
        SleepRecord(
            "sleep-actigraphy",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            SleepSourceType.ACTIGRAPHY,
            base + dt.timedelta(days=1),
            base + dt.timedelta(days=1, hours=8),
            421,
            ProcessingKind.TRANSPARENT_DERIVATION,
            "Fictional Lab",
            "A-1",
            "fw-1",
            "algo-a1",
        ),
        SleepRecord(
            "sleep-consumer",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            SleepSourceType.CONSUMER_WEARABLE,
            base + dt.timedelta(days=2),
            base + dt.timedelta(days=2, hours=8),
            405,
            ProcessingKind.BLACK_BOX_ESTIMATE,
            "Fictional Maker",
            "W-2",
            "fw-7",
            "proprietary-2044-04",
        ),
        SleepRecord(
            "sleep-clinical",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            SleepSourceType.CLINICAL_TEST,
            base + dt.timedelta(days=3),
            base + dt.timedelta(days=3, hours=8),
            438,
            ProcessingKind.DIRECT_RECORD,
        ),
        SleepRecord(
            "sleep-derived",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            SleepSourceType.DERIVED_OR_INFERRED,
            base + dt.timedelta(days=4),
            base + dt.timedelta(days=4, hours=8),
            426,
            ProcessingKind.TRANSPARENT_DERIVATION,
        ),
    )


def _contexts() -> tuple[ConfoundContext, ...]:
    return (
        ConfoundContext(
            "context-travel",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            ConfoundCategory.TRAVEL_OR_SHIFT,
            ContextSource.FICTIONAL_SELF_REPORT,
            dt.datetime(2044, 4, 6, 12, tzinfo=UTC),
            UncertaintyClass.MODERATE,
            "1.0.0",
        ),
        ConfoundContext(
            "context-epoch",
            PROTOCOL_ID,
            PROTOCOL_VERSION,
            ConfoundCategory.MEASUREMENT_CHANGE,
            ContextSource.PROTOCOL_LOG,
            dt.datetime(2044, 4, 4, 12, tzinfo=UTC),
            UncertaintyClass.LOW,
            "1.0.0",
        ),
    )


class E05LongitudinalService:
    """Narrow named operations over the single bundled fictional pack."""

    _ALLOWED: ClassVar[set[tuple[str, str]]] = {
        ("LOAD_FICTIONAL_LANTERN", "fictional_lantern_v1"),
        ("ANALYZE_FICTIONAL_LANTERN", "full_window"),
        ("DELETE_FICTIONAL_LANTERN", "confirmed_fixture_only"),
    }

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        *,
        backup_verified: bool = False,
        export_verified: bool = False,
    ) -> None:
        self.connection = connection or sqlite3.connect(":memory:")
        self.connection.execute("PRAGMA foreign_keys=ON")
        report = Migrator(self.connection).apply(
            3, backup_verified=backup_verified, export_verified=export_verified
        )
        if not report.success:
            raise E05LongitudinalError("MIGRATION_FAILED")
        self._results: dict[str, Any] = {}

    def operate(self, operation: str, choice: str, idempotency_key: str) -> Any:
        if (operation, choice) not in self._ALLOWED:
            raise E05LongitudinalError("INVALID_NAMED_OPERATION")
        if not idempotency_key or len(idempotency_key) > 80:
            raise E05LongitudinalError("INVALID_IDEMPOTENCY_KEY")
        if idempotency_key in self._results:
            return self._results[idempotency_key]
        if operation == "LOAD_FICTIONAL_LANTERN":
            result: Any = self._load()
        elif operation == "ANALYZE_FICTIONAL_LANTERN":
            result = self._analyze()
        else:
            result = self._delete()
        self._results[idempotency_key] = result
        return result

    def _load(self) -> dict[str, int | str]:
        protocol = _protocol()
        events = _events()
        sleep_records = _sleep_records()
        contexts = _contexts()
        with self.connection:
            self.connection.execute(
                "INSERT OR IGNORE INTO sampling_protocols VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    protocol.protocol_id,
                    protocol.version,
                    3,
                    protocol.construct,
                    protocol.schedule_type.value,
                    protocol.randomized_window_minutes,
                    protocol.max_prompts_per_day,
                    protocol.max_prompts_per_week,
                    protocol.burden_ceiling_minutes_per_day,
                    protocol.duration_days,
                    "|".join(protocol.pause_rules),
                    "|".join(protocol.stop_rules),
                    "|".join(item.value for item in protocol.allowed_context_fields),
                    "|".join(item.value for item in protocol.allowed_missingness_reasons),
                    protocol.feedback_policy,
                    protocol.timezone_behavior,
                    protocol.travel_behavior,
                    protocol.review_trigger,
                    protocol.approval_state,
                    WINDOW_START.isoformat(),
                ),
            )
            for event in events:
                self.connection.execute(
                    "INSERT OR IGNORE INTO longitudinal_events VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        event.event_id,
                        3,
                        event.protocol_id,
                        event.protocol_version,
                        event.scheduled_start.isoformat(),
                        event.scheduled_end.isoformat(),
                        event.actual_observation_time.isoformat()
                        if event.actual_observation_time
                        else None,
                        event.exposure_state.value,
                        event.feedback_exposure.value,
                        event.context_state.value,
                        event.missingness.value,
                        event.recorded_value,
                    ),
                )
            for record in sleep_records:
                self.connection.execute(
                    "INSERT OR IGNORE INTO sleep_records VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        record.record_id,
                        3,
                        record.protocol_id,
                        record.protocol_version,
                        record.source_type.value,
                        record.window_start.isoformat(),
                        record.window_end.isoformat(),
                        record.duration_minutes,
                        record.processing_kind.value,
                        record.device_maker,
                        record.device_model,
                        record.firmware_version,
                        record.algorithm_epoch,
                    ),
                )
            for context in contexts:
                self.connection.execute(
                    "INSERT OR IGNORE INTO confound_contexts VALUES(?,?,?,?,?,?,?,?,?)",
                    (
                        context.context_id,
                        3,
                        context.protocol_id,
                        context.protocol_version,
                        context.category.value,
                        context.source.value,
                        context.observed_at.isoformat(),
                        context.uncertainty.value,
                        context.version,
                    ),
                )
        return {
            "protocols": 1,
            "events": len(events),
            "sleep_records": len(sleep_records),
            "contexts": len(contexts),
            "data_mode": "synthetic_only",
        }

    def _analyze(self) -> DescriptiveSummary:
        if (
            self.connection.execute(
                "SELECT COUNT(*) FROM sampling_protocols WHERE protocol_id=?", (PROTOCOL_ID,)
            ).fetchone()[0]
            != 1
        ):
            raise E05LongitudinalError("FIXTURE_NOT_LOADED")
        return describe_window(_protocol(), _events(), _sleep_records(), WINDOW_START, WINDOW_END)

    def _delete(self) -> dict[str, bool | int]:
        with self.connection:
            deleted = self.connection.execute(
                "DELETE FROM sampling_protocols WHERE protocol_id=? AND protocol_version=?",
                (PROTOCOL_ID, PROTOCOL_VERSION),
            ).rowcount
        remaining = sum(
            self.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "sampling_protocols",
                "longitudinal_events",
                "sleep_records",
                "confound_contexts",
            )
        )
        return {
            "protocols_deleted": deleted,
            "dependency_rows_remaining": remaining,
            "canonical_absence": remaining == 0,
        }
