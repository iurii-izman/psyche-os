"""Failure-driven unit proofs for the E05 typed descriptive model."""

from dataclasses import replace
import datetime as dt

import pytest

from psyche_os.application.e05_longitudinal import (
    WINDOW_END,
    WINDOW_START,
    _events,
    _protocol,
    _sleep_records,
)
from psyche_os.domain.longitudinal import (
    ALL_MISSINGNESS_STATES,
    LongitudinalValidationError,
    MissingnessState,
    ProcessingKind,
    ScheduleType,
    SleepSourceType,
    assert_event_frequency_claim_allowed,
    describe_window,
    validate_output_wording,
)


def test_incomplete_protocol_and_invalid_burden_schedule_window_fail_before_write() -> None:
    protocol = _protocol()
    with pytest.raises(LongitudinalValidationError, match="burden"):
        replace(protocol, burden_ceiling_minutes_per_day=0)
    with pytest.raises(LongitudinalValidationError, match="pause and stop"):
        replace(protocol, pause_rules=())
    with pytest.raises(LongitudinalValidationError, match="window"):
        replace(protocol, randomized_window_minutes=None)
    with pytest.raises(LongitudinalValidationError, match="does not match"):
        replace(protocol, schedule_type=ScheduleType.INTERVAL_CONTINGENT)
    with pytest.raises(LongitudinalValidationError, match="six missingness"):
        replace(protocol, allowed_missingness_reasons=ALL_MISSINGNESS_STATES[:-1])


def test_out_of_window_event_is_rejected_and_all_missingness_states_remain_distinct() -> None:
    event = _events()[0]
    with pytest.raises(LongitudinalValidationError, match="outside scheduled window"):
        replace(event, actual_observation_time=event.scheduled_end)
    assert {event.missingness for event in _events()} == set(MissingnessState)


def test_denominator_is_deterministic_and_long_gap_is_not_imputed_or_moralized() -> None:
    first = describe_window(_protocol(), _events(), _sleep_records(), WINDOW_START, WINDOW_END)
    second = describe_window(_protocol(), _events(), _sleep_records(), WINDOW_START, WINDOW_END)
    assert first == second
    assert first.eligible_event_count == first.denominator == 10
    assert first.observed_count == 5
    assert first.coverage_ratio.as_tuple() == (0, (5,), -1)
    assert dict(first.missingness_counts) == {
        MissingnessState.OBSERVED: 5,
        MissingnessState.DELIBERATE_SKIP: 1,
        MissingnessState.DECLINED: 1,
        MissingnessState.TECHNICAL_FAILURE: 1,
        MissingnessState.UNAVAILABLE_CONTEXT: 1,
        MissingnessState.NOT_APPLICABLE: 1,
    }
    rendered = " ".join(first.limitations).casefold()
    assert "imputed" in rendered and "noncompliant" not in rendered
    assert "streak" not in rendered and "overdue" not in rendered and "shame" not in rendered


def test_feedback_triggers_reactivity_caution_and_event_frequency_claim_fails_closed() -> None:
    summary = describe_window(_protocol(), _events(), _sleep_records(), WINDOW_START, WINDOW_END)
    assert summary.feedback_exposure_count == 1
    assert "may alter recorded experience" in summary.reactivity_caution
    event_protocol = replace(
        _protocol(), schedule_type=ScheduleType.EVENT_CONTINGENT, randomized_window_minutes=None
    )
    with pytest.raises(LongitudinalValidationError, match="missed-opportunity"):
        assert_event_frequency_claim_allowed(event_protocol)


def test_sleep_sources_metadata_black_box_and_version_drift_are_explicit() -> None:
    records = _sleep_records()
    assert {record.source_type for record in records} == set(SleepSourceType)
    consumer = next(
        record for record in records if record.source_type is SleepSourceType.CONSUMER_WEARABLE
    )
    assert consumer.processing_kind is ProcessingKind.BLACK_BOX_ESTIMATE
    with pytest.raises(LongitudinalValidationError, match="complete metadata"):
        replace(consumer, firmware_version=None)
    with pytest.raises(LongitudinalValidationError, match="black_box_estimate"):
        replace(consumer, processing_kind=ProcessingKind.TRANSPARENT_DERIVATION)
    changed = replace(records[1], record_id="sleep-actigraphy-v2", algorithm_epoch="algo-a2")
    summary = describe_window(_protocol(), _events(), (*records, changed), WINDOW_START, WINDOW_END)
    assert summary.comparability_boundaries == (
        "device_or_algorithm_epoch_changed; series_kept_source_separated",
    )


def test_protocol_version_drift_c3_and_prohibited_language_fail_closed() -> None:
    drifted = replace(_events()[0], protocol_version="2.0.0")
    with pytest.raises(LongitudinalValidationError, match="silent protocol-version"):
        describe_window(_protocol(), (drifted,), (), WINDOW_START, WINDOW_END)
    summary = describe_window(_protocol(), _events(), _sleep_records(), WINDOW_START, WINDOW_END)
    assert summary.c3_enabled is False and summary.language_ceiling == "C2_temporal_precedence"
    for phrase in (
        "caused",
        "because of",
        "predicts",
        "diagnostic of",
        "treatment",
        "poor adherence",
    ):
        with pytest.raises(LongitudinalValidationError, match="language ceiling"):
            validate_output_wording(f"The fictional series {phrase} the other value")
    validate_output_wording("Recorded values changed within the exact described window.")


def test_analysis_window_requires_aware_ordered_instants() -> None:
    with pytest.raises(LongitudinalValidationError, match="analysis window"):
        describe_window(
            _protocol(), _events(), _sleep_records(), dt.datetime(2044, 4, 1), WINDOW_END
        )
