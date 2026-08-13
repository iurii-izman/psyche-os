"""Failure-driven mutation proofs for the read-only E01 evidence validator."""

from __future__ import annotations

import copy
import datetime
import json
from pathlib import Path
from typing import Any, Callable

import pytest

import scripts.validate_e01_assurance as validator


@pytest.fixture
def evidence() -> dict[str, Any]:
    return json.loads(validator.EVIDENCE_INDEX_PATH.read_text(encoding="utf-8"))


def _run_mutation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    evidence: dict[str, Any],
    mutate: Callable[[dict[str, Any]], None],
    check: Callable[[], dict[str, Any]],
) -> None:
    candidate = copy.deepcopy(evidence)
    mutate(candidate)
    path = tmp_path / "mutated-evidence.json"
    path.write_text(json.dumps(candidate), encoding="utf-8")
    before = path.read_bytes()
    monkeypatch.setattr(validator, "EVIDENCE_INDEX_PATH", path)
    result = check()
    assert result["status"] == "FAIL", result
    assert path.read_bytes() == before, "Evidence validator must remain read-only"


def test_rejects_empty_and_wrong_digest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evidence: dict[str, Any]
) -> None:
    first = next(iter(evidence["evidence"].values()))
    artifact = next(iter(first["artifact_digests"]))
    _run_mutation(
        tmp_path, monkeypatch, evidence,
        lambda data: data["evidence"][next(iter(data["evidence"]))][
            "artifact_digests"
        ].__setitem__(artifact, ""),
        validator.check_artifact_digests_not_empty,
    )
    _run_mutation(
        tmp_path, monkeypatch, evidence,
        lambda data: data["evidence"][next(iter(data["evidence"]))][
            "artifact_digests"
        ].__setitem__(artifact, "sha256:" + "0" * 64),
        validator.check_artifact_digests_match_disk,
    )


@pytest.mark.parametrize("case", ["missing", "expired"])
def test_rejects_missing_or_expired_timestamp(
    case: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    evidence: dict[str, Any],
) -> None:
    def mutate(data: dict[str, Any]) -> None:
        if case == "missing":
            data.pop("generated_at", None)
        else:
            data["expiry"] = (
                datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=1)
            ).isoformat()

    _run_mutation(
        tmp_path, monkeypatch, evidence, mutate,
        validator.check_evidence_timestamps_set,
    )


@pytest.mark.parametrize("status", ["PENDING", "BLOCKED"])
def test_rejects_nonpassing_status(
    status: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    evidence: dict[str, Any],
) -> None:
    _run_mutation(
        tmp_path, monkeypatch, evidence,
        lambda data: data["evidence"][next(iter(data["evidence"]))].__setitem__(
            "status", status
        ),
        validator.check_evidence_status_not_forbidden,
    )


def test_rejects_missing_artifact_and_contradictory_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, evidence: dict[str, Any]
) -> None:
    first_key = next(iter(evidence["evidence"]))
    _run_mutation(
        tmp_path, monkeypatch, evidence,
        lambda data: data["evidence"][first_key]["artifact_digests"].__setitem__(
            "missing-artifact.py", "sha256:" + "1" * 64
        ),
        validator.check_artifact_digests_match_disk,
    )
    _run_mutation(
        tmp_path, monkeypatch, evidence,
        lambda data: data.__setitem__("accepted_commit", "deadbeef"),
        validator.check_evidence_state_consistency,
    )
