"""Focused privacy and schema checks for optional AI Dev OS telemetry."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WRITER_PATH = ROOT / ".ai-dev" / "telemetry" / "writer.py"
SPEC = importlib.util.spec_from_file_location("telemetry_writer", WRITER_PATH)
assert SPEC is not None and SPEC.loader is not None
writer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(writer)


def _valid_event(**changes: object) -> dict[str, object]:
    event: dict[str, object] = {
        "event_type": "session_meta",
        "task_id": "SYNTHETIC-TELEMETRY-TEST",
        "risk": "low",
        "profile": "balanced",
    }
    event.update(changes)
    return event


def _events(telemetry_dir: Path) -> list[dict[str, object]]:
    path = telemetry_dir / "data" / "events.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_tel_01_valid_session_meta_appends(tmp_path: Path) -> None:
    result = writer.run(str(tmp_path), _valid_event())

    assert result["path"] == str(tmp_path / "data" / "events.jsonl")
    assert len(_events(tmp_path)) == 1


def test_tel_02_unknown_event_type_is_rejected_before_append(tmp_path: Path) -> None:
    with pytest.raises(writer.TelemetryValidationError):
        writer.run(str(tmp_path), _valid_event(event_type="unknown_event"))

    assert _events(tmp_path) == []


def test_tel_03_missing_event_type_is_rejected_before_append(tmp_path: Path) -> None:
    event = _valid_event()
    event.pop("event_type")

    with pytest.raises(writer.TelemetryValidationError):
        writer.run(str(tmp_path), event)

    assert _events(tmp_path) == []


@pytest.mark.parametrize("field, value", [("risk", "unsafe"), ("profile", "invalid")])
def test_tel_04_invalid_risk_or_profile_is_rejected(tmp_path: Path, field: str, value: str) -> None:
    with pytest.raises(writer.TelemetryValidationError):
        writer.run(str(tmp_path), _valid_event(**{field: value}))

    assert _events(tmp_path) == []


def test_tel_05_and_06_redacts_secrets_and_drops_private_content(tmp_path: Path) -> None:
    writer.run(
        str(tmp_path),
        _valid_event(
            api_key="SYNTHETIC-CANARY-NOT-A-SECRET",
            raw_prompt="synthetic prompt",
            tool_output="synthetic tool output",
        ),
    )

    persisted = _events(tmp_path)[0]
    assert persisted["api_key"] == writer.REDACT
    assert "raw_prompt" not in persisted
    assert "tool_output" not in persisted


def test_tel_07_invalid_event_does_not_change_existing_jsonl(tmp_path: Path) -> None:
    writer.run(str(tmp_path), _valid_event(task_id="first"))
    path = tmp_path / "data" / "events.jsonl"
    before = path.read_bytes()

    with pytest.raises(writer.TelemetryValidationError):
        writer.run(str(tmp_path), _valid_event(event_type="not-allowed"))

    assert path.read_bytes() == before


def test_tel_08_valid_events_append_in_order(tmp_path: Path) -> None:
    writer.run(str(tmp_path), _valid_event(task_id="first"))
    writer.run(str(tmp_path), _valid_event(task_id="second"))

    assert [event["task_id"] for event in _events(tmp_path)] == ["first", "second"]
