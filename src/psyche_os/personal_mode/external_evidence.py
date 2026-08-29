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
    "SPO2": ("%", "SPO2"),
    "OXYGEN_SATURATION": ("%", "SPO2"),
    "RESPIRATORY_RATE": ("breaths/min", "RESPIRATORY_RATE"),
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


def health_md_checksums(
    header: dict[str, Any], records: list[dict[str, Any]], issues: list[dict[str, Any]], manifest: dict[str, Any]
) -> tuple[list[str], str, str]:
    """Return the normative v1 semantic checksums for a decoded snapshot.

    A record hash covers the exact record object except its self-referential
    ``hash`` member.  The logical checksum covers the decoded framing and
    records (and is therefore format-independent); the manifest checksum
    covers its own complete semantic payload except its self-reference.
    """
    record_hashes = [_hash({key: value for key, value in record.items() if key != "hash"}) for record in records]
    logical = _hash({"header": header, "records": records, "issues": issues})
    manifest_payload = {key: value for key, value in manifest.items() if key != "manifestChecksumSha256"}
    return record_hashes, logical, _hash(manifest_payload)


def _id(prefix: str, *values: str) -> str:
    return f"{prefix}_{hashlib.sha256('|'.join(values).encode()).hexdigest()[:32]}"


def _first(value: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in value and value[key] is not None:
            return value[key]
    return None


def _timestamp(value: Any) -> str | None:
    """Read the normative full-resolution Health.md instant object."""
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"epochSecond", "nano", "epochSecondExact"}:
        raise ExternalEvidenceError("INVALID_INSTANT")
    second, nano, exact = value["epochSecond"], value["nano"], value["epochSecondExact"]
    if (
        not isinstance(second, int)
        or isinstance(second, bool)
        or not isinstance(nano, int)
        or isinstance(nano, bool)
        or not isinstance(exact, str)
        or str(second) != exact
        or not 0 <= nano <= 999_999_999
    ):
        raise ExternalEvidenceError("INVALID_INSTANT")
    try:
        stamp = datetime.fromtimestamp(second, UTC).strftime("%Y-%m-%dT%H:%M:%S")
    except (OverflowError, OSError, ValueError) as exc:
        raise ExternalEvidenceError("INVALID_INSTANT") from exc
    return f"{stamp}.{nano:09d}Z"


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _validate_header(header: Any) -> None:
    required = {"schema", "version", "snapshotId", "createdAt", "request", "capabilities"}
    if (
        not isinstance(header, dict)
        or set(header) != required
        or header["schema"] != "healthmd.raw-snapshot"
        or header["version"] != 1
        or not isinstance(header["snapshotId"], str)
        or not header["snapshotId"]
    ):
        raise ExternalEvidenceError("INVALID_SNAPSHOT_HEADER")
    _timestamp(header["createdAt"])
    request, capabilities = header["request"], header["capabilities"]
    if (
        not isinstance(request, dict)
        or not {
            "format",
            "scope",
            "startTime",
            "endTime",
            "selectedMetricIds",
            "pageSize",
            "includeExerciseRoutes",
        }.issubset(request)
        or request.get("format") not in {"JSON", "NDJSON"}
        or request.get("scope") not in {"SELECTED_RECORD_TYPES", "ALL_AUTHORIZED_SUPPORTED_DATA"}
        or not isinstance(request.get("pageSize"), int)
        or not 1 <= request["pageSize"] <= 5000
        or not isinstance(request.get("selectedMetricIds"), list)
        or not isinstance(request.get("includeExerciseRoutes"), bool)
    ):
        raise ExternalEvidenceError("INVALID_SNAPSHOT_HEADER")
    start, end = _timestamp(request["startTime"]), _timestamp(request["endTime"])
    if (
        start is None
        or end is None
        or start >= end
        or not isinstance(capabilities, dict)
        or capabilities.get("nonTransactional") is not True
    ):
        raise ExternalEvidenceError("INVALID_SNAPSHOT_HEADER")


def _validate_manifest(
    manifest: Any,
    header: dict[str, Any],
    records: list[dict[str, Any]],
    issues: list[dict[str, Any]],
) -> None:
    required = {
        "schema",
        "version",
        "snapshotId",
        "status",
        "completedAt",
        "recordCount",
        "issueCount",
        "duplicateCount",
        "identityCollisionCount",
        "typeCounts",
        "typeReports",
        "logicalChecksumSha256",
        "manifestChecksumSha256",
        "artifactChecksumSha256",
    }
    if (
        not isinstance(manifest, dict)
        or set(manifest) != required
        or manifest["schema"] != "healthmd.raw-snapshot.manifest"
        or manifest["version"] != 1
        or manifest["snapshotId"] != header["snapshotId"]
        or manifest["status"] not in {"COMPLETE", "PARTIAL", "FAILED"}
        or manifest["recordCount"] != len(records)
        or manifest["issueCount"] != len(issues)
        or any(
            not isinstance(manifest[name], int) or manifest[name] < 0
            for name in ("duplicateCount", "identityCollisionCount")
        )
        or not isinstance(manifest["typeCounts"], list)
        or not isinstance(manifest["typeReports"], list)
        or not _valid_sha(manifest["logicalChecksumSha256"])
        or not _valid_sha(manifest["manifestChecksumSha256"])
        or (
            manifest["artifactChecksumSha256"] is not None
            and not _valid_sha(manifest["artifactChecksumSha256"])
        )
    ):
        raise ExternalEvidenceError("INVALID_SNAPSHOT_MANIFEST")
    _timestamp(manifest["completedAt"])
    if manifest["status"] == "FAILED":
        raise ExternalEvidenceError("FAILED_SNAPSHOT")
    _, logical, manifest_checksum = health_md_checksums(header, records, issues, manifest)
    if (
        manifest["logicalChecksumSha256"] != logical
        or manifest["manifestChecksumSha256"] != manifest_checksum
    ):
        raise ExternalEvidenceError("SNAPSHOT_CHECKSUM_MISMATCH")


def _validate_issue(issue: Any) -> None:
    if (
        not isinstance(issue, dict)
        or set(issue) != {"code", "message", "severity", "recordType", "retryable"}
        or not isinstance(issue["code"], str)
        or not isinstance(issue["message"], str)
        or issue["severity"] not in {"INFO", "WARNING", "ERROR"}
        or (issue["recordType"] is not None and not isinstance(issue["recordType"], str))
        or not isinstance(issue["retryable"], bool)
    ):
        raise ExternalEvidenceError("INVALID_SNAPSHOT_ISSUE")


def _validate_record(record: Any) -> dict[str, Any]:
    required = {
        "wireType",
        "nativeIdentity",
        "recordKind",
        "source",
        "startTime",
        "endTime",
        "startZoneOffsetSeconds",
        "endZoneOffsetSeconds",
        "metadata",
        "fields",
        "providerPayload",
        "hash",
    }
    if (
        not isinstance(record, dict)
        or set(record) != required
        or not isinstance(record["wireType"], str)
        or not record["wireType"]
        or not isinstance(record["nativeIdentity"], str)
        or not record["nativeIdentity"]
        or record["recordKind"] != "health_connect_record"
        or not isinstance(record["source"], dict)
        or record["source"].get("providerId") != "health_connect"
        or record["source"].get("fidelityLevel") != "health_connect_api_projected"
        or not isinstance(record["fields"], dict)
        or record["providerPayload"] is not None
        or not _valid_sha(record["hash"])
    ):
        raise ExternalEvidenceError("INVALID_RAW_RECORD")
    if record["hash"] != _hash({key: value for key, value in record.items() if key != "hash"}):
        raise ExternalEvidenceError("RECORD_CHECKSUM_MISMATCH")
    start, end = _timestamp(record["startTime"]), _timestamp(record["endTime"])
    if record["wireType"] == "sleep_session" and (start is None or end is None or end <= start):
        raise ExternalEvidenceError("INVALID_RAW_RECORD")
    return record


def parse_health_md(raw: bytes) -> tuple[list[dict[str, Any]], str]:
    """Validate only the normative ``healthmd.raw-snapshot`` v1 formats."""
    if not raw or len(raw) > 32 * 1024 * 1024:
        raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from exc
    try:
        parsed = json.loads(decoded)
        if (
            not isinstance(parsed, dict)
            or set(parsed) != {"header", "records", "issues", "manifest"}
            or not isinstance(parsed["records"], list)
            or not isinstance(parsed["issues"], list)
        ):
            raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from None
        header, records, issues, manifest = (
            parsed["header"],
            parsed["records"],
            parsed["issues"],
            parsed["manifest"],
        )
        _validate_header(header)
        if header["request"]["format"] != "JSON":
            raise ExternalEvidenceError("SNAPSHOT_FORMAT_MISMATCH")
        for issue in issues:
            _validate_issue(issue)
        records = [_validate_record(record) for record in records]
        _validate_manifest(manifest, header, records, issues)
        return records, str(manifest["status"])
    except json.JSONDecodeError:
        try:
            lines = decoded.splitlines()
            if not lines or any(not line.strip() for line in lines):
                raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from None
            envelopes = [json.loads(line) for line in lines]
        except json.JSONDecodeError as exc:
            raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from exc
        if (
            not isinstance(envelopes[0], dict)
            or set(envelopes[0]) != {"kind", "header"}
            or envelopes[0]["kind"] != "header"
            or not isinstance(envelopes[-1], dict)
            or set(envelopes[-1]) != {"kind", "manifest"}
            or envelopes[-1]["kind"] != "manifest"
        ):
            raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from None
        header, manifest, records, issues = (
            envelopes[0]["header"],
            envelopes[-1]["manifest"],
            [],
            [],
        )
        _validate_header(header)
        if header["request"]["format"] != "NDJSON":
            raise ExternalEvidenceError("SNAPSHOT_FORMAT_MISMATCH") from None
        for envelope in envelopes[1:-1]:
            if (
                not isinstance(envelope, dict)
                or envelope.get("kind") not in {"record", "issue"}
                or set(envelope)
                != ({"kind", "record"} if envelope.get("kind") == "record" else {"kind", "issue"})
            ):
                raise ExternalEvidenceError("UNSUPPORTED_ARTIFACT") from None
            if envelope["kind"] == "record":
                records.append(_validate_record(envelope["record"]))
            else:
                _validate_issue(envelope["issue"])
                issues.append(envelope["issue"])
        _validate_manifest(manifest, header, records, issues)
        return records, str(manifest["status"])


def _record_identity(
    record: dict[str, Any],
) -> tuple[str, str, str, str | None, str | None, str, str | None, str | None]:
    record_type = str(record["wireType"]).upper()
    metadata = record["metadata"] if isinstance(record["metadata"], dict) else {}
    native_id = record["nativeIdentity"]
    start = _timestamp(record["startTime"])
    end = _timestamp(record["endTime"])
    if record_type == "SLEEP_SESSION" and (start is None or end is None or end <= start):
        raise ExternalEvidenceError("INVALID_SLEEP_SESSION")
    origin = {"source": record["source"], "metadata": metadata}
    modified = _timestamp(metadata.get("lastModifiedTime")) if metadata else None
    source_version = metadata.get("clientRecordVersionExact") if metadata else None
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
    stages = record["fields"].get("stages") or []
    if not isinstance(stages, list):
        raise ExternalEvidenceError("INVALID_STAGES")
    for stage in stages:
        if not isinstance(stage, dict):
            raise ExternalEvidenceError("INVALID_STAGES")
        category = (
            str((stage.get("stage") or {}).get("label") or "UNKNOWN").upper().replace(" ", "_")
        )
        if category not in _STAGES:
            category = "UNKNOWN"
        start = _timestamp(stage.get("startTime"))
        end = _timestamp(stage.get("endTime"))
        if start is None or end is None or end <= start:
            raise ExternalEvidenceError("INVALID_STAGES")
        yield category, start, end


def _sample(record: dict[str, Any], record_type: str) -> tuple[str, str, float, str] | None:
    metric_info = _METRICS.get(record_type)
    if metric_info is None:
        return None
    fields = record["fields"]
    if record_type == "HEART_RATE":
        return None
    observed = _timestamp(record["startTime"])
    value = (
        fields.get("beatsPerMinute")
        if record_type == "RESTING_HEART_RATE"
        else (fields.get("percentage") or {}).get("number")
        if record_type == "OXYGEN_SATURATION"
        else (fields.get("rate") or {}).get("number")
    )
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
                "INSERT INTO external_sources(source_id,source_kind,label,state,processing_policy,inbox_path,created_at,updated_at) VALUES(?,?,?,'ACTIVE','LOCAL_ONLY',?,?,?) ON CONFLICT(source_id) DO UPDATE SET label=excluded.label,inbox_path=COALESCE(excluded.inbox_path,external_sources.inbox_path),updated_at=excluded.updated_at",
                (SOURCE_ID, SOURCE_KIND, label, inbox_path, now, now),
            )

    def import_artifact(
        self, raw: bytes, *, artifact_name: str = "health-md.json"
    ) -> dict[str, int]:
        records, _snapshot_status = parse_health_md(raw)  # validate fully before changing state
        artifact_hash = hashlib.sha256(raw).hexdigest()
        now = _now()
        try:
            self.connection.execute("BEGIN IMMEDIATE")
            # Import is allowed before a UI configuration, but creation of the
            # default source is part of this same transaction.  In particular,
            # an artifact can never erase an owner-selected inbox path.
            self.connection.execute(
                "INSERT INTO external_sources(source_id,source_kind,label,state,processing_policy,inbox_path,created_at,updated_at) VALUES(?,?,?,'ACTIVE','LOCAL_ONLY',NULL,?,?) ON CONFLICT(source_id) DO NOTHING",
                (SOURCE_ID, SOURCE_KIND, "Amazfit / Zepp через Health Connect", now, now),
            )
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
        if record_type == "HEART_RATE":
            self.connection.execute(
                "DELETE FROM physiological_samples WHERE external_record_id=?", (record_id,)
            )
            samples = record["fields"].get("samples")
            if not isinstance(samples, list):
                raise ExternalEvidenceError("INVALID_SAMPLE")
            for index, sample in enumerate(samples):
                observed, value = (
                    _timestamp(sample.get("time")) if isinstance(sample, dict) else None,
                    sample.get("beatsPerMinute") if isinstance(sample, dict) else None,
                )
                if observed is None or not isinstance(value, int) or isinstance(value, bool):
                    raise ExternalEvidenceError("INVALID_SAMPLE")
                self.connection.execute(
                    "INSERT INTO physiological_samples(sample_id,external_record_id,source_version_id,metric,classification,observed_at,value,unit) VALUES(?,?,?,?,?,?,?,?)",
                    (
                        _id("sample", version_id, str(index)),
                        record_id,
                        version_id,
                        "HEART_RATE",
                        "MEASUREMENT",
                        observed,
                        value,
                        "bpm",
                    ),
                )
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
            sidecar = path.with_name(f"{path.name}.sha256")
            if sidecar.exists():
                try:
                    declared, spacing, filename = (
                        sidecar.read_text(encoding="utf-8").rstrip("\n").partition("  ")
                    )
                    if (
                        spacing != "  "
                        or filename != path.name
                        or declared != hashlib.sha256(raw).hexdigest()
                    ):
                        raise ExternalEvidenceError("SIDECAR_CHECKSUM_MISMATCH")
                except UnicodeDecodeError as exc:
                    raise ExternalEvidenceError("SIDECAR_CHECKSUM_MISMATCH") from exc
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
