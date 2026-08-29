from __future__ import annotations

import hashlib
import json
import sqlite3

import pytest

from psyche_os.personal_mode.external_evidence import ExternalEvidenceError, ExternalEvidenceService
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
        "hash": "a" * 64,
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
    manifest = {
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
        "logicalChecksumSha256": "b" * 64,
        "manifestChecksumSha256": "c" * 64,
        "artifactChecksumSha256": None,
    }
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
