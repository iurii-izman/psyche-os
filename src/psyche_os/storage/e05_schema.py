"""Additive E05 V2-to-V3 schema delta."""

from __future__ import annotations

import hashlib
import sqlite3

from psyche_os.storage.e03_schema import V2_INVENTORY

V3_ADDED_TABLES: tuple[str, ...] = (
    "sampling_protocols",
    "longitudinal_events",
    "sleep_records",
    "confound_contexts",
)
V3_INVENTORY: tuple[str, ...] = V2_INVENTORY + V3_ADDED_TABLES


V3_MIGRATION_SQL = """
CREATE TABLE sampling_protocols (
 protocol_id TEXT NOT NULL CHECK(protocol_id='fictional-lantern-activation'),
 protocol_version TEXT NOT NULL CHECK(protocol_version='1.0.0'), schema_version INTEGER NOT NULL CHECK(schema_version=3),
 construct TEXT NOT NULL CHECK(construct='fictional_activation_level'),
 schedule_type TEXT NOT NULL CHECK(schedule_type IN ('signal_contingent','event_contingent','interval_contingent')),
 randomized_window_minutes INTEGER, max_prompts_per_day INTEGER NOT NULL CHECK(max_prompts_per_day BETWEEN 1 AND 8),
 max_prompts_per_week INTEGER NOT NULL CHECK(max_prompts_per_week BETWEEN max_prompts_per_day AND max_prompts_per_day*7),
 burden_ceiling_minutes_per_day INTEGER NOT NULL CHECK(burden_ceiling_minutes_per_day BETWEEN 1 AND 30),
 duration_days INTEGER NOT NULL CHECK(duration_days BETWEEN 1 AND 366),
 pause_rule TEXT NOT NULL CHECK(pause_rule='fictional_pause_available'),
 stop_rule TEXT NOT NULL CHECK(stop_rule='fictional_stop_on_request|fictional_stop_at_duration'),
 allowed_context_fields TEXT NOT NULL CHECK(allowed_context_fields='fictional_setting|travel_schedule|measurement_epoch'),
 allowed_missingness_reasons TEXT NOT NULL CHECK(allowed_missingness_reasons='observed|deliberate_skip|declined|technical_failure|unavailable_context|not_applicable'),
 feedback_policy TEXT NOT NULL CHECK(feedback_policy='bounded_descriptive_summary_only'),
 timezone_behavior TEXT NOT NULL CHECK(timezone_behavior='store_aware_instants_and_named_utc_fixture_zone'),
 travel_behavior TEXT NOT NULL CHECK(travel_behavior='keep_original_schedule_and_mark_travel_context'),
 review_trigger TEXT NOT NULL CHECK(review_trigger='fictional_burden_or_version_change'),
 approval_state TEXT NOT NULL CHECK(approval_state='fictional_explicitly_approved'), created_at TEXT NOT NULL,
 PRIMARY KEY(protocol_id,protocol_version),
 CHECK((schedule_type='signal_contingent' AND randomized_window_minutes BETWEEN 1 AND 240) OR
       (schedule_type!='signal_contingent' AND randomized_window_minutes IS NULL))
);
CREATE TRIGGER sampling_protocols_immutable BEFORE UPDATE ON sampling_protocols
BEGIN SELECT RAISE(ABORT,'sampling protocols are immutable; add a version'); END;
CREATE TABLE longitudinal_events (
 event_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL CHECK(schema_version=3), protocol_id TEXT NOT NULL,
 protocol_version TEXT NOT NULL, scheduled_start TEXT NOT NULL, scheduled_end TEXT NOT NULL,
 actual_observation_time TEXT, exposure_state TEXT NOT NULL CHECK(exposure_state IN ('not_exposed','prompt_exposed')),
 feedback_exposure TEXT NOT NULL CHECK(feedback_exposure IN ('none','summary_viewed')),
 context_state TEXT NOT NULL CHECK(context_state IN ('recorded','unavailable','not_requested')),
 missingness TEXT NOT NULL CHECK(missingness IN ('observed','deliberate_skip','declined','technical_failure','unavailable_context','not_applicable')),
 recorded_value INTEGER CHECK(recorded_value BETWEEN 0 AND 4),
 FOREIGN KEY(protocol_id,protocol_version) REFERENCES sampling_protocols(protocol_id,protocol_version) ON DELETE CASCADE,
 CHECK(scheduled_start < scheduled_end),
 CHECK((missingness='observed' AND actual_observation_time IS NOT NULL AND recorded_value IS NOT NULL AND
        actual_observation_time>=scheduled_start AND actual_observation_time<scheduled_end) OR
       (missingness!='observed' AND actual_observation_time IS NULL AND recorded_value IS NULL))
);
CREATE TRIGGER longitudinal_events_immutable BEFORE UPDATE ON longitudinal_events
BEGIN SELECT RAISE(ABORT,'longitudinal events are immutable'); END;
CREATE INDEX idx_longitudinal_events_protocol_window ON longitudinal_events(protocol_id,protocol_version,scheduled_start);
CREATE TABLE sleep_records (
 record_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL CHECK(schema_version=3), protocol_id TEXT NOT NULL,
 protocol_version TEXT NOT NULL, source_type TEXT NOT NULL CHECK(source_type IN ('subjective_diary','actigraphy','consumer_wearable','clinical_test','derived_or_inferred')),
 window_start TEXT NOT NULL, window_end TEXT NOT NULL, duration_minutes INTEGER NOT NULL CHECK(duration_minutes BETWEEN 0 AND 1440),
 processing_kind TEXT NOT NULL CHECK(processing_kind IN ('direct_record','transparent_derivation','black_box_estimate')),
 device_maker TEXT, device_model TEXT, firmware_version TEXT, algorithm_epoch TEXT,
 FOREIGN KEY(protocol_id,protocol_version) REFERENCES sampling_protocols(protocol_id,protocol_version) ON DELETE CASCADE,
 CHECK(window_start < window_end),
 CHECK(source_type NOT IN ('actigraphy','consumer_wearable') OR
       (device_maker IS NOT NULL AND device_model IS NOT NULL AND firmware_version IS NOT NULL AND algorithm_epoch IS NOT NULL)),
 CHECK(source_type!='consumer_wearable' OR processing_kind='black_box_estimate')
);
CREATE TRIGGER sleep_records_immutable BEFORE UPDATE ON sleep_records
BEGIN SELECT RAISE(ABORT,'sleep records are immutable'); END;
CREATE INDEX idx_sleep_records_protocol_window ON sleep_records(protocol_id,protocol_version,window_start);
CREATE TABLE confound_contexts (
 context_id TEXT PRIMARY KEY, schema_version INTEGER NOT NULL CHECK(schema_version=3), protocol_id TEXT NOT NULL,
 protocol_version TEXT NOT NULL, category TEXT NOT NULL CHECK(category IN ('travel_or_shift','measurement_change')),
 source TEXT NOT NULL CHECK(source IN ('fictional_self_report','protocol_log')), observed_at TEXT NOT NULL,
 uncertainty TEXT NOT NULL CHECK(uncertainty IN ('low','moderate','high','unknown')), context_version TEXT NOT NULL,
 FOREIGN KEY(protocol_id,protocol_version) REFERENCES sampling_protocols(protocol_id,protocol_version) ON DELETE CASCADE
);
CREATE TRIGGER confound_contexts_immutable BEFORE UPDATE ON confound_contexts
BEGIN SELECT RAISE(ABORT,'confound contexts are immutable'); END;
CREATE INDEX idx_confound_contexts_protocol_time ON confound_contexts(protocol_id,protocol_version,observed_at);
"""


def _split(script: str) -> tuple[str, ...]:
    statements: list[str] = []
    buffer = ""
    for char in script:
        buffer += char
        if char == ";" and sqlite3.complete_statement(buffer):
            statements.append(buffer.strip())
            buffer = ""
    if buffer.strip():
        raise ValueError("Incomplete E05 migration SQL")
    return tuple(statements)


V3_MIGRATION_STATEMENTS = _split(V3_MIGRATION_SQL)
V3_MIGRATION_CHECKSUM = hashlib.sha256(
    (";\n".join(V3_MIGRATION_STATEMENTS) + ";").encode()
).hexdigest()
