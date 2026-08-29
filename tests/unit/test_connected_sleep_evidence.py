from __future__ import annotations

import json
import sqlite3

import pytest

from psyche_os.personal_mode.external_evidence import ExternalEvidenceError, ExternalEvidenceService
from psyche_os.personal_mode.package_format import create_personal_package, restore_personal_package
from psyche_os.personal_mode.schema import initialize_personal_v14, initialize_personal_v15


def artifact(stage: str = "LIGHT") -> bytes:
    return json.dumps(
        {
            "records": [
                {
                    "recordType": "SleepSession",
                    "id": "sleep-1",
                    "dataOrigin": {"packageName": "synthetic.zepp"},
                    "startTime": "2026-08-20T23:48:00Z",
                    "endTime": "2026-08-21T07:32:00Z",
                    "lastModifiedTime": "2026-08-21T08:01:00Z",
                    "stages": [
                        {
                            "stage": stage,
                            "startTime": "2026-08-20T23:48:00Z",
                            "endTime": "2026-08-21T07:32:00Z",
                        }
                    ],
                },
                {
                    "recordType": "HeartRate",
                    "id": "hr-1",
                    "time": "2026-08-21T03:00:00Z",
                    "value": 52,
                    "dataOrigin": {"packageName": "synthetic.zepp"},
                },
                {
                    "recordType": "OxygenSaturation",
                    "id": "spo2-1",
                    "time": "2026-08-21T03:01:00Z",
                    "value": 97.0,
                    "dataOrigin": {"packageName": "synthetic.zepp"},
                },
                {
                    "recordType": "RespiratoryRate",
                    "id": "rr-1",
                    "time": "2026-08-21T03:02:00Z",
                    "value": 14.0,
                    "dataOrigin": {"packageName": "synthetic.zepp"},
                },
            ]
        }
    ).encode()


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
    assert service.import_artifact(artifact()) == {"records": 4, "versions": 4}
    assert service.import_artifact(artifact()) == {"records": 0, "versions": 0}
    equivalent = json.dumps(json.loads(artifact()), indent=2).encode()
    assert service.import_artifact(equivalent)["versions"] == 0
    assert service.import_artifact(artifact("DEEP"))["versions"] == 1
    assert (
        db.execute(
            "SELECT count(*) FROM external_record_versions WHERE external_record_id=(SELECT external_record_id FROM external_records WHERE native_id='sleep-1')"
        ).fetchone()[0]
        == 2
    )
    assert db.execute("SELECT count(*) FROM sleep_episodes").fetchone()[0] == 1
    assert db.execute("SELECT category FROM sleep_stages").fetchone()[0] == "DEEP"
    assert db.execute("SELECT count(*) FROM physiological_samples").fetchone()[0] == 3


def test_invalid_artifact_is_atomic_and_owner_deletion_closes_projections() -> None:
    db = connection()
    service = ExternalEvidenceService(db)
    service.import_artifact(artifact())
    before = db.execute("SELECT count(*) FROM external_records").fetchone()[0]
    with pytest.raises(ExternalEvidenceError):
        service.import_artifact(b'{"records": [')
    assert db.execute("SELECT count(*) FROM external_records").fetchone()[0] == before
    record_id = db.execute(
        "SELECT external_record_id FROM external_records WHERE native_id='sleep-1'"
    ).fetchone()[0]
    service.delete_external_record(record_id)
    assert db.execute("SELECT count(*) FROM sleep_observations").fetchone()[0] == 0
    assert db.execute("SELECT count(*) FROM sleep_episodes").fetchone()[0] == 0
