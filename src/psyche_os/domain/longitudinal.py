"""Typed E05 longitudinal, sleep, context, and descriptive-analysis contracts.

The module intentionally accepts only closed value types.  Canonical writes are
performed separately by the package-owned fictional fixture service.
"""

from __future__ import annotations

from dataclasses import dataclass
import datetime as dt
from decimal import Decimal
from enum import StrEnum


class LongitudinalValidationError(ValueError):
    """A closed E05 domain invariant was violated."""


class ScheduleType(StrEnum):
    SIGNAL_CONTINGENT = "signal_contingent"
    EVENT_CONTINGENT = "event_contingent"
    INTERVAL_CONTINGENT = "interval_contingent"


class MissingnessState(StrEnum):
    OBSERVED = "observed"
    DELIBERATE_SKIP = "deliberate_skip"
    DECLINED = "declined"
    TECHNICAL_FAILURE = "technical_failure"
    UNAVAILABLE_CONTEXT = "unavailable_context"
    NOT_APPLICABLE = "not_applicable"


class ExposureState(StrEnum):
    NOT_EXPOSED = "not_exposed"
    PROMPT_EXPOSED = "prompt_exposed"


class FeedbackExposure(StrEnum):
    NONE = "none"
    SUMMARY_VIEWED = "summary_viewed"


class ContextState(StrEnum):
    RECORDED = "recorded"
    UNAVAILABLE = "unavailable"
    NOT_REQUESTED = "not_requested"


class ContextField(StrEnum):
    FICTIONAL_SETTING = "fictional_setting"
    TRAVEL_SCHEDULE = "travel_schedule"
    MEASUREMENT_EPOCH = "measurement_epoch"


class SleepSourceType(StrEnum):
    SUBJECTIVE_DIARY = "subjective_diary"
    ACTIGRAPHY = "actigraphy"
    CONSUMER_WEARABLE = "consumer_wearable"
    CLINICAL_TEST = "clinical_test"
    DERIVED_OR_INFERRED = "derived_or_inferred"


class ProcessingKind(StrEnum):
    DIRECT_RECORD = "direct_record"
    TRANSPARENT_DERIVATION = "transparent_derivation"
    BLACK_BOX_ESTIMATE = "black_box_estimate"


class ConfoundCategory(StrEnum):
    TRAVEL_OR_SHIFT = "travel_or_shift"
    MEASUREMENT_CHANGE = "measurement_change"


class ContextSource(StrEnum):
    FICTIONAL_SELF_REPORT = "fictional_self_report"
    PROTOCOL_LOG = "protocol_log"


class UncertaintyClass(StrEnum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    UNKNOWN = "unknown"


ALL_MISSINGNESS_STATES = tuple(MissingnessState)
DEVICE_REQUIRED_SOURCES = frozenset({SleepSourceType.ACTIGRAPHY, SleepSourceType.CONSUMER_WEARABLE})


def _aware(value: dt.datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


@dataclass(frozen=True, slots=True)
class SamplingProtocol:
    protocol_id: str
    version: str
    construct: str
    schedule_type: ScheduleType
    randomized_window_minutes: int | None
    max_prompts_per_day: int
    max_prompts_per_week: int
    burden_ceiling_minutes_per_day: int
    duration_days: int
    pause_rules: tuple[str, ...]
    stop_rules: tuple[str, ...]
    allowed_context_fields: tuple[ContextField, ...]
    allowed_missingness_reasons: tuple[MissingnessState, ...]
    feedback_policy: str
    timezone_behavior: str
    travel_behavior: str
    review_trigger: str
    approval_state: str

    def __post_init__(self) -> None:
        required_text = (
            self.protocol_id,
            self.version,
            self.construct,
            self.feedback_policy,
            self.timezone_behavior,
            self.travel_behavior,
            self.review_trigger,
        )
        if any(not item.strip() for item in required_text):
            raise LongitudinalValidationError("protocol text fields must be complete")
        if self.approval_state != "fictional_explicitly_approved":
            raise LongitudinalValidationError("fictional explicit approval is required")
        if not (1 <= self.max_prompts_per_day <= 8):
            raise LongitudinalValidationError("invalid daily prompt ceiling")
        if not (
            self.max_prompts_per_day <= self.max_prompts_per_week <= self.max_prompts_per_day * 7
        ):
            raise LongitudinalValidationError("invalid weekly prompt ceiling")
        if not (1 <= self.burden_ceiling_minutes_per_day <= 30):
            raise LongitudinalValidationError("invalid burden ceiling")
        if not (1 <= self.duration_days <= 366):
            raise LongitudinalValidationError("invalid protocol duration")
        if not self.pause_rules or not self.stop_rules:
            raise LongitudinalValidationError("pause and stop rules are required")
        if not self.allowed_context_fields:
            raise LongitudinalValidationError("allowed context fields are required")
        if tuple(self.allowed_missingness_reasons) != ALL_MISSINGNESS_STATES:
            raise LongitudinalValidationError("all six missingness states must be explicit")
        if self.schedule_type is ScheduleType.SIGNAL_CONTINGENT:
            if self.randomized_window_minutes is None or not (
                1 <= self.randomized_window_minutes <= 240
            ):
                raise LongitudinalValidationError("signal schedule requires a bounded window")
        elif self.randomized_window_minutes is not None:
            raise LongitudinalValidationError("randomized window does not match schedule")


@dataclass(frozen=True, slots=True)
class LongitudinalEvent:
    event_id: str
    protocol_id: str
    protocol_version: str
    scheduled_start: dt.datetime
    scheduled_end: dt.datetime
    actual_observation_time: dt.datetime | None
    exposure_state: ExposureState
    feedback_exposure: FeedbackExposure
    context_state: ContextState
    missingness: MissingnessState
    recorded_value: int | None

    def __post_init__(self) -> None:
        if not self.event_id or not self.protocol_id or not self.protocol_version:
            raise LongitudinalValidationError("event identity and protocol version are required")
        if not _aware(self.scheduled_start) or not _aware(self.scheduled_end):
            raise LongitudinalValidationError("event schedule must be timezone-aware")
        if self.scheduled_start >= self.scheduled_end:
            raise LongitudinalValidationError("event window must be non-empty")
        if self.missingness is MissingnessState.OBSERVED:
            if self.actual_observation_time is None or self.recorded_value is None:
                raise LongitudinalValidationError("observed event requires time and value")
            if not _aware(self.actual_observation_time):
                raise LongitudinalValidationError("observation time must be timezone-aware")
            if not self.scheduled_start <= self.actual_observation_time < self.scheduled_end:
                raise LongitudinalValidationError("observation falls outside scheduled window")
            if not 0 <= self.recorded_value <= 4:
                raise LongitudinalValidationError("recorded fictional value is out of range")
        elif self.actual_observation_time is not None or self.recorded_value is not None:
            raise LongitudinalValidationError("missing event cannot contain an observation")


@dataclass(frozen=True, slots=True)
class SleepRecord:
    record_id: str
    protocol_id: str
    protocol_version: str
    source_type: SleepSourceType
    window_start: dt.datetime
    window_end: dt.datetime
    duration_minutes: int
    processing_kind: ProcessingKind
    device_maker: str | None = None
    device_model: str | None = None
    firmware_version: str | None = None
    algorithm_epoch: str | None = None

    def __post_init__(self) -> None:
        if not self.record_id or not self.protocol_id or not self.protocol_version:
            raise LongitudinalValidationError("sleep identity and protocol version are required")
        if not _aware(self.window_start) or not _aware(self.window_end):
            raise LongitudinalValidationError("sleep window must be timezone-aware")
        if self.window_start >= self.window_end or not (0 <= self.duration_minutes <= 1440):
            raise LongitudinalValidationError("invalid sleep window or duration")
        metadata = (
            self.device_maker,
            self.device_model,
            self.firmware_version,
            self.algorithm_epoch,
        )
        if self.source_type in DEVICE_REQUIRED_SOURCES and any(not value for value in metadata):
            raise LongitudinalValidationError("device-derived sleep requires complete metadata")
        if self.source_type is SleepSourceType.CONSUMER_WEARABLE and (
            self.processing_kind is not ProcessingKind.BLACK_BOX_ESTIMATE
        ):
            raise LongitudinalValidationError(
                "consumer proprietary output must be black_box_estimate"
            )


@dataclass(frozen=True, slots=True)
class ConfoundContext:
    context_id: str
    protocol_id: str
    protocol_version: str
    category: ConfoundCategory
    source: ContextSource
    observed_at: dt.datetime
    uncertainty: UncertaintyClass
    version: str

    def __post_init__(self) -> None:
        if not all((self.context_id, self.protocol_id, self.protocol_version, self.version)):
            raise LongitudinalValidationError("context identity and versions are required")
        if not _aware(self.observed_at):
            raise LongitudinalValidationError("context time must be timezone-aware")


@dataclass(frozen=True, slots=True)
class DescriptiveSummary:
    analysis_window_start: dt.datetime
    analysis_window_end: dt.datetime
    eligible_event_count: int
    observed_count: int
    denominator: int
    coverage_ratio: Decimal
    missingness_counts: tuple[tuple[MissingnessState, int], ...]
    source_composition: tuple[tuple[SleepSourceType, int], ...]
    protocol_versions: tuple[str, ...]
    device_algorithm_epochs: tuple[str, ...]
    feedback_exposure_count: int
    reactivity_caution: str
    comparability_boundaries: tuple[str, ...]
    limitations: tuple[str, ...]
    language_ceiling: str = "C2_temporal_precedence"
    c3_enabled: bool = False


PROHIBITED_ASSERTIVE_PHRASES = (
    "caused",
    "causes",
    "because of",
    "leads to",
    "predicts",
    "risk of",
    "diagnostic of",
    "indicates disorder",
    "treatment",
    "should take",
    "should stop",
    "improved because",
    "worsened because",
    "noncompliant",
    "poor adherence",
)


def validate_output_wording(text: str) -> None:
    """Fail closed when an E05 output crosses its C0-C2 language ceiling."""
    lowered = text.casefold()
    if any(phrase in lowered for phrase in PROHIBITED_ASSERTIVE_PHRASES):
        raise LongitudinalValidationError("output exceeds the E05 language ceiling")


def describe_window(
    protocol: SamplingProtocol,
    events: tuple[LongitudinalEvent, ...],
    sleep_records: tuple[SleepRecord, ...],
    window_start: dt.datetime,
    window_end: dt.datetime,
) -> DescriptiveSummary:
    """Produce a deterministic, non-imputing C0-C2 summary."""
    if not _aware(window_start) or not _aware(window_end) or window_start >= window_end:
        raise LongitudinalValidationError("analysis window must be valid and timezone-aware")
    eligible = tuple(
        event for event in events if window_start <= event.scheduled_start < window_end
    )
    if any(
        event.protocol_id != protocol.protocol_id or event.protocol_version != protocol.version
        for event in eligible
    ):
        raise LongitudinalValidationError("silent protocol-version comparison is blocked")
    denominator = len(eligible)
    observed = sum(event.missingness is MissingnessState.OBSERVED for event in eligible)
    counts = tuple(
        (state, sum(event.missingness is state for event in eligible)) for state in MissingnessState
    )
    coverage = Decimal(observed) / Decimal(denominator) if denominator else Decimal("0")
    bounded_sleep = tuple(
        record
        for record in sleep_records
        if record.window_start < window_end and record.window_end > window_start
    )
    composition = tuple(
        (source, sum(record.source_type is source for record in bounded_sleep))
        for source in SleepSourceType
    )
    epochs = tuple(
        sorted(
            {
                f"{record.device_maker}/{record.device_model}/{record.firmware_version}/{record.algorithm_epoch}"
                for record in bounded_sleep
                if record.algorithm_epoch is not None
            }
        )
    )
    boundaries: list[str] = []
    if len(epochs) > 1:
        boundaries.append("device_or_algorithm_epoch_changed; series_kept_source_separated")
    feedback_count = sum(event.feedback_exposure is not FeedbackExposure.NONE for event in eligible)
    caution = (
        "Prompt or feedback exposure was recorded; repeated measurement may alter recorded experience."
        if any(event.exposure_state is ExposureState.PROMPT_EXPOSED for event in eligible)
        or feedback_count
        else "No prompt or feedback exposure was recorded in this window."
    )
    limitations = (
        "No missing observation was imputed; long gaps remain gaps.",
        "Event-contingent records cannot estimate event frequency without a missed-opportunity model.",
        "Sleep sources and device or algorithm epochs remain separate.",
        "The output is descriptive and provides no causal, clinical, diagnostic, treatment, association, or prediction claim.",
    )
    return DescriptiveSummary(
        analysis_window_start=window_start,
        analysis_window_end=window_end,
        eligible_event_count=denominator,
        observed_count=observed,
        denominator=denominator,
        coverage_ratio=coverage,
        missingness_counts=counts,
        source_composition=composition,
        protocol_versions=(protocol.version,),
        device_algorithm_epochs=epochs,
        feedback_exposure_count=feedback_count,
        reactivity_caution=caution,
        comparability_boundaries=tuple(boundaries),
        limitations=limitations,
    )


def assert_event_frequency_claim_allowed(protocol: SamplingProtocol) -> None:
    """E05 has no missed-opportunity model, so event-frequency claims fail closed."""
    if protocol.schedule_type is ScheduleType.EVENT_CONTINGENT:
        raise LongitudinalValidationError(
            "event frequency claim requires a missed-opportunity model"
        )
