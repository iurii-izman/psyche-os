"""Local-only Health Connect evidence ingestion and sleep projections.

This module deliberately has no provider or AI dependency.  It accepts a
small loss-minimising JSON/NDJSON adapter contract, retains verbatim records,
and projects only the current version into the daily-use sleep view.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any


class ExternalEvidenceError(ValueError):
    """Content-free failure for invalid or incomplete untrusted imports."""


SOURCE_ID = "health-connect-health-md"
SOURCE_KIND = "HEALTH_CONNECT_HEALTH_MD"
_STAGES = {"AWAKE", "AWAKE_IN_BED", "LIGHT", "DEEP", "REM", "SLEEPING", "OUT_OF_BED", "UNKNOWN"}
_METRICS = {
    "HEART_RATE": ("bpm", "HEART_RATE"),
    "RESTING_HEART_RATE": ("bpm", "RESTING_HEART_RATE"),
    "SPO2": ("percent", "SPO2"),
    "OXYGEN_SATURATION": ("percent", "SPO2"),
    "RESPIRATORY_RATE": ("breaths_per_min", "RESPIRATORY_RATE"),
    "RESTINGHEARTRATE": ("bpm", "RESTING_HEART_RATE"),
    "OXYGENSATURATION": ("percent", "SPO2"),
    "RESPIRATORYRATE": ("breaths_per_min", "RESPIRATORY_RATE"),
    "HEARTRATE": ("bpm", "HEART_RATE"),
}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _id(prefix: str, *values: str) -> str:
    return f"{prefix}_{hashlib.sha256('|'.join(values).encode()).hexdigest()[:32]}"


def _first(value: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in value and value[key] is not None:
            return value[key]
    return None


def _timestamp(value: Any) -> str | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExternalEvidenceError("INVALID_TIMESTAMP") from exc
    return value


def parse_health_md(raw: bytes) -> list[dict[str, Any]]:
    """Validate the supported raw snapshot or NDJSON representation.

    Health.md versions label records differently, so the adapter intentionally
    permits ``recordType``/``type`` and either a top-level ``records`` list or
    NDJSON.  It fails closed instead of guessing arbitrary JSON shapes.
    """
    if not raw or len(raw) > 32 * 1024 * 1024:
        raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from exc
    try:
        parsed = json.loads(decoded)
        records = parsed.get("records") if isinstance(parsed, dict) else parsed
        if not isinstance(records, list):
            raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT")
    except json.JSONDecodeError:
        try:
            records = [json.loads(line) for line in decoded.splitlines() if line.strip()]
        except json.JSONDecodeError as exc:
            raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from exc
    if not records or any(not isinstance(record, dict) for record in records):
        raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT")
    for record in records:
        if not isinstance(_first(record, "recordType", "type"), str):
            raise ExternalEvidenceError("UNSUPPORTED_RECORD")
    return records


def _record_identity(
    record: dict[str, Any],
) -> tuple[str, str, str, str | None, str | None, str, str | None, str | None]:
    record_type = str(_first(record, "recordType", "type")).upper()
    metadata = record.get("metadata") if isinstance(record.get("metadata"), dict) else {}
    native_id = _first(record, "id", "uuid") or _first(metadata, "id", "recordId")
    # A deterministic fallback is valid only within this adapter/source.
    if not isinstance(native_id, str) or not native_id:
        native_id = "fallback:" + _hash(
            {k: v for k, v in record.items() if k not in {"lastModifiedTime", "lastModifiedAt"}}
        )
    start = _timestamp(_first(record, "startTime", "startAt", "time"))
    end = _timestamp(_first(record, "endTime", "endAt"))
    if record_type in {"SLEEPSESSION", "SLEEP_SESSION"} and (
        start is None or end is None or end <= start
    ):
        raise ExternalEvidenceError("INVALID_SLEEP_SESSION")
    origin = _first(record, "dataOrigin", "origin") or metadata.get("dataOrigin") or {}
    if not isinstance(origin, (dict, str)):
        raise ExternalEvidenceError("INVALID_ORIGIN")
    modified = _timestamp(_first(record, "lastModifiedTime", "lastModifiedAt"))
    source_version = _first(record, "clientRecordVersion", "version")
    if source_version is not None and not isinstance(source_version, (str, int)):
        raise ExternalEvidenceError("INVALID_VERSION")
    return (
        native_id,
        record_type,
        _canonical(origin),
        start,
        end,
        _canonical(record),
        modified,
        str(source_version) if source_version is not None else None,
    )


def _stage_rows(record: dict[str, Any]) -> Iterable[tuple[str, str, str]]:
    stages = _first(record, "stages", "sleepStages") or []
    if not isinstance(stages, list):
        raise ExternalEvidenceError("INVALID_STAGES")
    for stage in stages:
        if not isinstance(stage, dict):
            raise ExternalEvidenceError("INVALID_STAGES")
        category = (
            str(_first(stage, "stage", "type", "category", "stageType") or "UNKNOWN")
            .upper()
            .replace(" ", "_")
        )
        if category not in _STAGES:
            category = "UNKNOWN"
        start = _timestamp(_first(stage, "startTime", "startAt"))
        end = _timestamp(_first(stage, "endTime", "endAt"))
        if start is None or end is None or end <= start:
            raise ExternalEvidenceError("INVALID_STAGES")
        yield category, start, end


def _sample(record: dict[str, Any], record_type: str) -> tuple[str, str, float, str] | None:
    metric_info = _METRICS.get(record_type)
    if metric_info is None:
        return None
    observed = _timestamp(_first(record, "time", "timestamp", "startTime", "startAt"))
    value = _first(record, "value", "bpm", "percentage", "rate")
    if observed is None or not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ExternalEvidenceError("INVALID_SAMPLE")
    return metric_info[1], observed, float(value), str(_first(record, "unit") or metric_info[0])


class ExternalEvidenceService:
    """Transaction-scoped immutable import and projection service."""

    def __init__(self, connection: Any) -> None:
        self.connection = connection

    def configure_source(
        self, *, label: str = "Amazfit / Zepp через Health Connect", inbox_path: str | None = None
    ) -> None:
        now = _now()
        with self.connection:
            self.connection.execute(
                "INSERT INTO external_sources(source_id,source_kind,label,state,processing_policy,inbox_path,created_at,updated_at) VALUES(?,?,?,'ACTIVE','LOCAL_ONLY',?,?,?) ON CONFLICT(source_id) DO UPDATE SET label=excluded.label,inbox_path=excluded.inbox_path,updated_at=excluded.updated_at",
                (SOURCE_ID, SOURCE_KIND, label, inbox_path, now, now),
            )

    def import_artifact(
        self, raw: bytes, *, artifact_name: str = "health-md.json"
    ) -> dict[str, int]:
        records = parse_health_md(raw)  # validate fully before changing state
        artifact_hash = hashlib.sha256(raw).hexdigest()
        self.configure_source()
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            if self.connection.execute(
                "SELECT 1 FROM external_import_batches WHERE source_id=? AND artifact_sha256=?",
                (SOURCE_ID, artifact_hash),
            ).fetchone():
                self.connection.rollback()
                return {"records": 0, "versions": 0}
            batch_id = _id("batch", SOURCE_ID, artifact_hash)
            self.connection.execute(
                "INSERT INTO external_import_batches(batch_id,source_id,artifact_name,artifact_sha256,imported_at,record_count) VALUES(?,?,?,?,?,?)",
                (batch_id, SOURCE_ID, artifact_name, artifact_hash, now, len(records)),
            )
            versions = 0
            for record in records:
                versions += self._import_record(record, batch_id, now)
            self.connection.execute(
                "UPDATE external_sources SET last_imported_at=?,state='ACTIVE',updated_at=? WHERE source_id=?",
                (now, now, SOURCE_ID),
            )
            self.connection.commit()
            return {"records": len(records), "versions": versions}
        except Exception as exc:
            self.connection.rollback()
            if isinstance(exc, ExternalEvidenceError):
                raise
            raise ExternalEvidenceError("IMPORT_FAILED") from exc

    def _import_record(self, record: dict[str, Any], batch_id: str, now: str) -> int:
        native_id, record_type, origin, start, end, raw_payload, modified, source_version = (
            _record_identity(record)
        )
        record_id = _id("record", SOURCE_ID, record_type, native_id)
        payload_hash = hashlib.sha256(raw_payload.encode()).hexdigest()
        exists = self.connection.execute(
            "SELECT external_record_id FROM external_records WHERE external_record_id=?",
            (record_id,),
        ).fetchone()
        if not exists:
            self.connection.execute(
                "INSERT INTO external_records(external_record_id,source_id,native_id,record_type,origin_json,start_at,end_at,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)",
                (record_id, SOURCE_ID, native_id, record_type, origin, start, end, now, now),
            )
        elif self.connection.execute(
            "SELECT 1 FROM external_record_versions WHERE external_record_id=? AND payload_sha256=?",
            (record_id, payload_hash),
        ).fetchone():
            return 0
        else:
            self.connection.execute(
                "UPDATE external_records SET origin_json=?,start_at=?,end_at=?,updated_at=? WHERE external_record_id=?",
                (origin, start, end, now, record_id),
            )
        prior = self.connection.execute(
            "SELECT version_id,ordinal FROM external_record_versions WHERE external_record_id=? AND is_current=1",
            (record_id,),
        ).fetchone()
        ordinal = (prior[1] if prior else 0) + 1
        version_id = _id("version", record_id, payload_hash)
        if prior:
            self.connection.execute(
                "UPDATE external_record_versions SET is_current=0 WHERE version_id=?", (prior[0],)
            )
        self.connection.execute(
            "INSERT INTO external_record_versions(version_id,external_record_id,batch_id,ordinal,payload_sha256,raw_payload,source_modified_at,source_version,is_current,supersedes_version_id,imported_at) VALUES(?,?,?,?,?,?,?,?,1,?,?)",
            (
                version_id,
                record_id,
                batch_id,
                ordinal,
                payload_hash,
                raw_payload,
                modified,
                source_version,
                prior[0] if prior else None,
                now,
            ),
        )
        if record_type in {"SLEEPSESSION", "SLEEP_SESSION"}:
            self._project_sleep(record, record_id, version_id, start, end, now)
        sample = _sample(record, record_type)
        if sample:
            self.connection.execute(
                "DELETE FROM physiological_samples WHERE external_record_id=?", (record_id,)
            )
            metric, observed, value, unit = sample
            self.connection.execute(
                "INSERT INTO physiological_samples(sample_id,external_record_id,source_version_id,metric,classification,observed_at,value,unit) VALUES(?,?,?,?,?,?,?,?)",
                (
                    _id("sample", version_id, metric, observed),
                    record_id,
                    version_id,
                    metric,
                    "MEASUREMENT",
                    observed,
                    value,
                    unit,
                ),
            )
        return 1

    def _project_sleep(
        self,
        record: dict[str, Any],
        record_id: str,
        version_id: str,
        start: str | None,
        end: str | None,
        now: str,
    ) -> None:
        if start is None or end is None:
            raise ExternalEvidenceError("INVALID_SLEEP_SESSION")
        observation = self.connection.execute(
            "SELECT observation_id,episode_id FROM sleep_observations WHERE external_record_id=?",
            (record_id,),
        ).fetchone()
        if observation is None:
            episode_id = _id("episode", record_id)
            observation_id = _id("observation", record_id)
            self.connection.execute(
                "INSERT INTO sleep_episodes(episode_id,started_at,ended_at,created_at,updated_at) VALUES(?,?,?,?,?)",
                (episode_id, start, end, now, now),
            )
            self.connection.execute(
                "INSERT INTO sleep_observations(observation_id,episode_id,external_record_id,current_version_id,source_kind,classification,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)",
                (
                    observation_id,
                    episode_id,
                    record_id,
                    version_id,
                    SOURCE_KIND,
                    "VENDOR_DERIVED",
                    now,
                    now,
                ),
            )
        else:
            observation_id, episode_id = observation
            self.connection.execute(
                "UPDATE sleep_episodes SET started_at=?,ended_at=?,updated_at=? WHERE episode_id=?",
                (start, end, now, episode_id),
            )
            self.connection.execute(
                "UPDATE sleep_observations SET current_version_id=?,updated_at=? WHERE observation_id=?",
                (version_id, now, observation_id),
            )
            self.connection.execute(
                "DELETE FROM sleep_stages WHERE observation_id=?", (observation_id,)
            )
        for index, (category, stage_start, stage_end) in enumerate(_stage_rows(record)):
            self.connection.execute(
                "INSERT INTO sleep_stages(stage_id,observation_id,source_version_id,category,started_at,ended_at) VALUES(?,?,?,?,?,?)",
                (
                    _id("stage", version_id, str(index)),
                    observation_id,
                    version_id,
                    category,
                    stage_start,
                    stage_end,
                ),
            )

    def scan_inbox(self, inbox: Path) -> dict[str, int]:
        if not inbox.is_dir():
            raise ExternalEvidenceError("INBOX_UNAVAILABLE")
        total = {"records": 0, "versions": 0}
        for path in sorted(inbox.glob("*.json")) + sorted(inbox.glob("*.ndjson")):
            # Stable read: an artifact must have an unchanged size over two stats.
            first = path.stat()
            raw = path.read_bytes()
            second = path.stat()
            if first.st_size != second.st_size or len(raw) != first.st_size:
                continue
            result = self.import_artifact(raw, artifact_name=path.name)
            total = {key: total[key] + result[key] for key in total}
        return total

    def delete_external_record(self, external_record_id: str) -> None:
        with self.connection:
            self.connection.execute(
                "DELETE FROM external_records WHERE external_record_id=?", (external_record_id,)
            )
            self.connection.execute(
                "DELETE FROM sleep_episodes WHERE NOT EXISTS (SELECT 1 FROM sleep_observations WHERE sleep_observations.episode_id=sleep_episodes.episode_id)"
            )

    def sleep_history(self, days: int = 14) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT e.episode_id,e.started_at,e.ended_at,o.observation_id FROM sleep_episodes e JOIN sleep_observations o ON o.episode_id=e.episode_id ORDER BY e.started_at DESC LIMIT ?",
            (days,),
        ).fetchall()
        return [
            {
                "episode_id": r[0],
                "started_at": r[1],
                "ended_at": r[2],
                "stages": [
                    {"category": s[0], "started_at": s[1], "ended_at": s[2]}
                    for s in self.connection.execute(
                        "SELECT category,started_at,ended_at FROM sleep_stages WHERE observation_id=? ORDER BY started_at",
                        (r[3],),
                    )
                ],
            }
            for r in rows
        ]
