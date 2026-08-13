"""E02 T2/T3 real Python-sidecar framing and confidentiality tests."""

from __future__ import annotations

import json
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
def sidecar() -> subprocess.Popen[bytes]:
    process = subprocess.Popen(
        [sys.executable, "-m", "psyche_os.interfaces.desktop_sidecar"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).resolve().parents[2],
    )
    yield process
    process.terminate()
    process.wait(timeout=10)


def _request(command: str, payload: dict[str, Any], token: str | None = None) -> dict[str, Any]:
    return {
        "version": "1.0",
        "command": command,
        "correlation_id": "opaque-test-1",
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
