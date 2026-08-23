"""E02 T2/T3 real Python-sidecar framing and confidentiality tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import struct
import subprocess
import sys
from typing import Any, BinaryIO

import pytest


def _write(stream: BinaryIO, value: dict[str, Any]) -> None:
    body = json.dumps(value).encode()
    stream.write(struct.pack(">I", len(body)) + body)
    stream.flush()


def _read(stream: BinaryIO) -> dict[str, Any]:
    size = struct.unpack(">I", stream.read(4))[0]
    return json.loads(stream.read(size))


@pytest.fixture
def sidecar(tmp_path: Path) -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment["PSYCHE_OS_APP_DATA"] = str(tmp_path / "sidecar-app-data")
    process = subprocess.Popen(
        [sys.executable, "-m", "psyche_os.interfaces.desktop_sidecar"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).resolve().parents[2],
        env=environment,
    )
    yield process
    process.terminate()
    process.wait(timeout=10)


def _request(
    command: str,
    payload: dict[str, Any],
    token: str | None = None,
    correlation_id: str = "opaque-test-1",
) -> dict[str, Any]:
    return {
        "version": "1.0",
        "command": command,
        "correlation_id": correlation_id,
        "session_token": token,
        "payload": payload,
    }


def test_t2_actual_sidecar_rejects_unregistered_command(sidecar: subprocess.Popen[bytes]) -> None:
    assert sidecar.stdin and sidecar.stdout
    _write(sidecar.stdin, _request("filesystem.read", {"path": "C:/vault"}))
    response = _read(sidecar.stdout)
    assert response["status"] == "error"
    assert response["error"] == {"code": "UNKNOWN_COMMAND"}


def test_t2_oversized_frame_terminates_without_dispatch(sidecar: subprocess.Popen[bytes]) -> None:
    assert sidecar.stdin
    sidecar.stdin.write(struct.pack(">I", 65_537))
    sidecar.stdin.flush()
    assert sidecar.wait(timeout=10) == 2


def test_t2_oversized_response_returns_error_and_sidecar_continues(
    sidecar: subprocess.Popen[bytes],
) -> None:
    assert sidecar.stdin and sidecar.stdout
    _write(
        sidecar.stdin, _request("session.unlock", {"secret": "synthetic-demo"}, correlation_id="A")
    )
    token = _read(sidecar.stdout)["data"]["session_token"]
    _write(sidecar.stdin, _request("reflection_session.create", {"title": "overflow"}, token, "B"))
    session_id = _read(sidecar.stdout)["data"]["session_id"]
    oversized_content = "SYNTHETIC-OVERSIZE-CANARY-" + ("x" * 11_970)
    for sequence in range(6):
        _write(
            sidecar.stdin,
            _request(
                "reflection_session.add_turn",
                {"session_id": session_id, "content": oversized_content},
                token,
                f"turn-{sequence}",
            ),
        )
        assert _read(sidecar.stdout)["status"] == "ok"

    _write(
        sidecar.stdin,
        _request("reflection_session.get", {"session_id": session_id}, token, "oversized"),
    )
    overflow = _read(sidecar.stdout)
    assert overflow == {
        "version": "1.0",
        "correlation_id": "oversized",
        "status": "error",
        "error": {"code": "RESPONSE_TOO_LARGE"},
    }
    assert oversized_content not in json.dumps(overflow)

    _write(sidecar.stdin, _request("status.get", {}, token, "after-overflow"))
    recovered = _read(sidecar.stdout)
    assert recovered["correlation_id"] == "after-overflow"
    assert recovered["status"] == "ok"
    assert sidecar.poll() is None


def test_t3_secret_and_path_never_echo_to_response_or_stderr(
    sidecar: subprocess.Popen[bytes],
) -> None:
    assert sidecar.stdin and sidecar.stdout and sidecar.stderr
    canary = "SYNTHETIC-SECRET-CANARY-C:/vault/private.db"
    _write(sidecar.stdin, _request("session.unlock", {"secret": canary}))
    response = _read(sidecar.stdout)
    assert response["status"] == "ok"
    serialized = json.dumps(response)
    assert canary not in serialized
    assert "private.db" not in serialized
    sidecar.terminate()
    sidecar.wait(timeout=10)
    assert canary.encode() not in sidecar.stderr.read()
