from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from psyche_os.personal_mode.external_evidence import (
    ExternalEvidenceError,
    ExternalEvidenceService,
    health_md_checksums,
)
from psyche_os.personal_mode.package_format import create_personal_package, restore_personal_package
from psyche_os.personal_mode.schema import initialize_personal_v14, initialize_personal_v15


def instant(second: int) -> dict[str, int | str]:
    return {"epochSecond": second, "nano": 0, "epochSecondExact": str(second)}


def raw_record(
    wire_type: str, identity: str, start: int | None, end: int | None, fields: dict[str, object]
) -> dict[str, object]:
    return {
        "wireType": wire_type,
        "nativeIdentity": identity,
        "recordKind": "health_connect_record",
        "source": {
            "providerId": "health_connect",
            "fidelityLevel": "health_connect_api_projected",
            "endpointKey": None,
        },
        "startTime": instant(start) if start is not None else None,
        "endTime": instant(end) if end is not None else None,
        "startZoneOffsetSeconds": None,
        "endZoneOffsetSeconds": None,
        "metadata": {
            "id": identity.removeprefix("hc:"),
            "clientRecordId": None,
            "clientRecordVersion": 1,
            "clientRecordVersionExact": "1",
            "lastModifiedTime": instant(1_755_700_000),
            "dataOriginPackageName": "synthetic.zepp",
            "recordingMethod": {"raw": 2, "label": "automatically_recorded"},
            "device": None,
        },
        "fields": fields,
        "providerPayload": None,
        "hash": "",
    }


def snapshot(records: list[dict[str, object]], *, ndjson: bool = False) -> bytes:
    header = {
        "schema": "healthmd.raw-snapshot",
        "version": 1,
        "snapshotId": "synthetic-snapshot",
        "createdAt": instant(1_755_700_000),
        "request": {
            "format": "NDJSON" if ndjson else "JSON",
            "scope": "SELECTED_RECORD_TYPES",
            "startTime": instant(1_755_600_000),
            "endTime": instant(1_755_800_000),
            "selectedMetricIds": [],
            "pageSize": 100,
            "includeExerciseRoutes": False,
        },
        "capabilities": {
            "sdkVersion": "synthetic",
            "available": True,
            "grantedPermissions": [],
            "availableFeatures": [],
            "historicalReadGranted": True,
            "nonTransactional": True,
            "preservesSourceUnits": False,
            "preservesUnknownSdkFields": False,
        },
    }
    for record in records:
        record["hash"] = hashlib.sha256(
            json.dumps(
                {key: value for key, value in record.items() if key != "hash"},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
    manifest: dict[str, object] = {
        "schema": "healthmd.raw-snapshot.manifest",
        "version": 1,
        "snapshotId": "synthetic-snapshot",
        "status": "COMPLETE",
        "completedAt": instant(1_755_700_100),
        "recordCount": len(records),
        "issueCount": 0,
        "duplicateCount": 0,
        "identityCollisionCount": 0,
        "typeCounts": [],
        "typeReports": [],
        "logicalChecksumSha256": "",
        "manifestChecksumSha256": "",
        "artifactChecksumSha256": None,
    }
    _, logical, _ = health_md_checksums(header, records, [], manifest)
    manifest["logicalChecksumSha256"] = logical
    _, _, manifest_checksum = health_md_checksums(header, records, [], manifest)
    manifest["manifestChecksumSha256"] = manifest_checksum
    if ndjson:
        return (
            "\n".join(
                [
                    json.dumps({"kind": "header", "header": header}),
                    *(json.dumps({"kind": "record", "record": record}) for record in records),
                    json.dumps({"kind": "manifest", "manifest": manifest}),
                ]
            )
            + "\n"
        ).encode()
    return json.dumps(
        {"header": header, "records": records, "issues": [], "manifest": manifest}
    ).encode()


def artifact(stage: str = "light", *, ndjson: bool = False) -> bytes:
    return snapshot(
        [
            raw_record(
                "sleep_session",
                "hc:sleep-1",
                1_755_600_000,
                1_755_627_840,
                {
                    "title": None,
                    "notes": None,
                    "stages": [
                        {
                            "startTime": instant(1_755_600_000),
                            "endTime": instant(1_755_627_840),
                            "stage": {"raw": 2, "label": stage},
                        }
                    ],
                },
            ),
            raw_record(
                "heart_rate",
                "hc:hr-1",
                1_755_611_000,
                None,
                {
                    "samples": [
                        {"time": instant(1_755_611_000), "beatsPerMinute": 52},
                        {"time": instant(1_755_611_060), "beatsPerMinute": 53},
                    ]
                },
            ),
            raw_record(
                "oxygen_saturation",
                "hc:spo2-1",
                1_755_611_120,
                None,
                {
                    "percentage": {
                        "number": 97.0,
                        "decimal": "97",
                        "type": "Percentage",
                        "unit": "%",
                    }
                },
            ),
            raw_record(
                "respiratory_rate",
                "hc:rr-1",
                1_755_611_180,
                None,
                {"rate": {"number": 14.0, "decimal": "14", "unit": "breaths/min"}},
            ),
            raw_record(
                "resting_heart_rate", "hc:rhr-1", 1_755_611_240, None, {"beatsPerMinute": 49}
            ),
        ],
        ndjson=ndjson,
    )


def connection() -> sqlite3.Connection:
    db = sqlite3.connect(":memory:")
    db.execute("PRAGMA foreign_keys=ON")
    initialize_personal_v15(db)
    return db


def test_v14_migrates_additively_to_v15_and_package_round_trips() -> None:
    old = sqlite3.connect(":memory:")
    old.execute("PRAGMA foreign_keys=ON")
    initialize_personal_v14(old)
    initialize_personal_v15(old)
    assert [v[0] for v in old.execute("SELECT version FROM schema_migrations")] == [
        10,
        11,
        12,
        13,
        14,
        15,
    ]
    service = ExternalEvidenceService(old)
    service.import_artifact(artifact())
    package = create_personal_package(old)
    assert package["schema_version"] == 15 and package["format_version"] == 8
    restored = connection()
    restored.close()
    restored = sqlite3.connect(":memory:")
    restored.execute("PRAGMA foreign_keys=ON")
    restore_personal_package(package, restored)
    assert create_personal_package(restored)["package_checksum"] == package["package_checksum"]


def test_idempotent_versioned_import_and_projection_update() -> None:
    db = connection()
    service = ExternalEvidenceService(db)
    assert service.import_artifact(artifact()) == {"records": 5, "versions": 5}
    assert service.import_artifact(artifact()) == {"records": 0, "versions": 0}
    equivalent = json.dumps(json.loads(artifact()), indent=2).encode()
    assert service.import_artifact(equivalent)["versions"] == 0
    assert service.import_artifact(artifact("DEEP"))["versions"] == 1
    assert (
        db.execute(
            "SELECT count(*) FROM external_record_versions WHERE external_record_id=(SELECT external_record_id FROM external_records WHERE native_id='hc:sleep-1')"
        ).fetchone()[0]
        == 2
    )
    assert db.execute("SELECT count(*) FROM sleep_episodes").fetchone()[0] == 1
    assert db.execute("SELECT category FROM sleep_stages").fetchone()[0] == "DEEP"
    assert db.execute("SELECT count(*) FROM physiological_samples").fetchone()[0] == 5
    episode = service.sleep_history()[0]
    assert {sample["metric"] for sample in episode["samples"]} == {
        "HEART_RATE",
        "RESTING_HEART_RATE",
        "SPO2",
        "RESPIRATORY_RATE",
    }
    assert all({"metric", "observed_at", "value", "unit"} == set(sample) for sample in episode["samples"])


def test_partial_snapshot_truth_is_persisted_with_issue_count() -> None:
    decoded = json.loads(artifact())
    decoded["issues"] = [
        {
            "code": "SYNTHETIC_PARTIAL",
            "message": "Synthetic incomplete page for regression coverage.",
            "severity": "WARNING",
            "recordType": "sleep_session",
            "retryable": True,
        }
    ]
    decoded["manifest"]["status"] = "PARTIAL"
    decoded["manifest"]["issueCount"] = 1
    _, logical, _ = health_md_checksums(decoded["header"], decoded["records"], decoded["issues"], decoded["manifest"])
    decoded["manifest"]["logicalChecksumSha256"] = logical
    _, _, manifest_checksum = health_md_checksums(decoded["header"], decoded["records"], decoded["issues"], decoded["manifest"])
    decoded["manifest"]["manifestChecksumSha256"] = manifest_checksum
    db = connection()
    ExternalEvidenceService(db).import_artifact(json.dumps(decoded).encode())
    assert db.execute(
        "SELECT snapshot_status,issue_count FROM external_import_batches"
    ).fetchone() == ("PARTIAL", 1)


def test_invalid_artifact_is_atomic_and_owner_deletion_closes_projections() -> None:
    db = connection()
    service = ExternalEvidenceService(db)
    service.import_artifact(artifact())
    before = db.execute("SELECT count(*) FROM external_records").fetchone()[0]
    with pytest.raises(ExternalEvidenceError):
        service.import_artifact(b'{"records": [')
    assert db.execute("SELECT count(*) FROM external_records").fetchone()[0] == before
    record_id = db.execute(
        "SELECT external_record_id FROM external_records WHERE native_id='hc:sleep-1'"
    ).fetchone()[0]
    service.delete_external_record(record_id)
    assert db.execute("SELECT count(*) FROM sleep_observations").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM sleep_episodes").fetchone()[0] == 0


def test_normative_ndjson_is_equivalent_and_missing_manifest_is_atomic() -> None:
    json_db, ndjson_db = connection(), connection()
    json_service, ndjson_service = (
        ExternalEvidenceService(json_db),
        ExternalEvidenceService(ndjson_db),
    )
    json_service.import_artifact(artifact())
    ndjson_service.import_artifact(artifact(ndjson=True))
    assert json_service.sleep_history() == ndjson_service.sleep_history()
    before = ndjson_db.execute("SELECT count(*) FROM external_records").fetchone()[0]
    with pytest.raises(ExternalEvidenceError):
        ndjson_service.import_artifact(artifact(ndjson=True).rsplit(b"\n", 3)[0] + b"\n")
    assert ndjson_db.execute("SELECT count(*) FROM external_records").fetchone()[0] == before


def test_sidecar_checksum_is_honored(tmp_path) -> None:
    raw = artifact()
    path = tmp_path / "synthetic.json"
    path.write_bytes(raw)
    path.with_name("synthetic.json.sha256").write_text(
        f"{hashlib.sha256(raw).hexdigest()}  synthetic.json\n", encoding="utf-8"
    )
    service = ExternalEvidenceService(connection())
    assert service.scan_inbox(path.parent)["records"] == 5
    path.with_name("synthetic.json.sha256").write_text(
        "0" * 64 + "  synthetic.json\n", encoding="utf-8"
    )
    with pytest.raises(ExternalEvidenceError):
        service.scan_inbox(path.parent)


def test_configured_inbox_survives_import_second_scan_and_restart(tmp_path) -> None:
    path = tmp_path / "snapshot.json"
    path.write_bytes(artifact())
    db = connection()
    service = ExternalEvidenceService(db)
    service.configure_source(inbox_path=str(tmp_path))
    assert service.scan_inbox(tmp_path)["records"] == 5
    assert db.execute("SELECT inbox_path FROM external_sources").fetchone()[0] == str(tmp_path)
    assert service.scan_inbox(tmp_path) == {"records": 0, "versions": 0}
    # The same initialized persistent connection models a lock/restart cycle:
    # only service objects are process-local; source configuration is storage.
    restarted = ExternalEvidenceService(db)
    assert restarted.scan_inbox(tmp_path) == {"records": 0, "versions": 0}
    assert db.execute("SELECT inbox_path FROM external_sources").fetchone()[0] == str(tmp_path)


def test_record_and_manifest_checksum_fail_before_any_mutation() -> None:
    db = connection()
    service = ExternalEvidenceService(db)
    decoded = json.loads(artifact())
    decoded["records"][0]["fields"]["stages"][0]["stage"]["label"] = "DEEP"
    with pytest.raises(ExternalEvidenceError, match="RECORD_CHECKSUM_MISMATCH"):
        service.import_artifact(json.dumps(decoded).encode())
    assert db.execute("SELECT count(*) FROM external_sources").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM external_import_batches").fetchone()[0] == 0

    decoded = json.loads(artifact())
    decoded["manifest"]["logicalChecksumSha256"] = "0" * 64
    with pytest.raises(ExternalEvidenceError, match="SNAPSHOT_CHECKSUM_MISMATCH"):
        service.import_artifact(json.dumps(decoded).encode())
    assert db.execute("SELECT count(*) FROM external_records").fetchone()[0] == 0


def test_projection_failure_rolls_back_source_batch_and_records(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    db = connection()
    service = ExternalEvidenceService(db)
    original = service._project_sleep

    def fail_after_projection(*args: object) -> None:
        original(*args)  # type: ignore[arg-type]
        raise ExternalEvidenceError("SYNTHETIC_PROJECTION_FAILURE")

    monkeypatch.setattr(service, "_project_sleep", fail_after_projection)
    with pytest.raises(ExternalEvidenceError, match="SYNTHETIC_PROJECTION_FAILURE"):
        service.import_artifact(artifact())
    for table in ("external_sources", "external_import_batches", "external_records", "external_record_versions", "sleep_episodes", "sleep_stages"):
        assert db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] == 0


def test_failed_and_wrong_format_snapshots_reject() -> None:
    decoded = json.loads(artifact())
    decoded["manifest"]["status"] = "FAILED"
    _, logical, _ = health_md_checksums(decoded["header"], decoded["records"], decoded["issues"], decoded["manifest"])
    decoded["manifest"]["logicalChecksumSha256"] = logical
    _, _, checksum = health_md_checksums(decoded["header"], decoded["records"], decoded["issues"], decoded["manifest"])
    decoded["manifest"]["manifestChecksumSha256"] = checksum
    with pytest.raises(ExternalEvidenceError, match="FAILED_SNAPSHOT"):
        ExternalEvidenceService(connection()).import_artifact(json.dumps(decoded).encode())
    decoded = json.loads(artifact())
    decoded["header"]["request"]["format"] = "NDJSON"
    with pytest.raises(ExternalEvidenceError, match="SNAPSHOT_FORMAT_MISMATCH"):
        ExternalEvidenceService(connection()).import_artifact(json.dumps(decoded).encode())
