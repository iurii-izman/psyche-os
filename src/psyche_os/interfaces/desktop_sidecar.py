"""Length-framed, content-free E02 Python sidecar protocol."""

from __future__ import annotations

import json
import struct
import sys
from typing import Any, BinaryIO

from sqlcipher3 import dbapi2 as _sqlcipher

from psyche_os.application.desktop_service import (
    DesktopApplicationService,
    DesktopServiceError,
    PROTOCOL_VERSION,
)


MAX_FRAME_BYTES = 65_536
REQUEST_FIELDS = frozenset({"version", "command", "correlation_id", "session_token", "payload"})


class FrameError(Exception):
    pass


def read_frame(stream: BinaryIO) -> dict[str, Any] | None:
    header = stream.read(4)
    if not header:
        return None
    if len(header) != 4:
        raise FrameError("INVALID_FRAME")
    length = struct.unpack(">I", header)[0]
    if length == 0 or length > MAX_FRAME_BYTES:
        raise FrameError("INVALID_FRAME")
    body = stream.read(length)
    if len(body) != length:
        raise FrameError("INVALID_FRAME")
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FrameError("INVALID_FRAME") from exc
    if not isinstance(value, dict):
        raise FrameError("INVALID_FRAME")
    return value


def write_frame(stream: BinaryIO, value: dict[str, Any]) -> None:
    body = json.dumps(value, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    if len(body) > MAX_FRAME_BYTES:
        raise FrameError("RESPONSE_TOO_LARGE")
    stream.write(struct.pack(">I", len(body)))
    stream.write(body)
    stream.flush()


def handle_request(service: DesktopApplicationService, request: dict[str, Any]) -> dict[str, Any]:
    correlation = request.get("correlation_id")
    if set(request) != REQUEST_FIELDS:
        raise DesktopServiceError("INVALID_REQUEST")
    if request["version"] != PROTOCOL_VERSION:
        raise DesktopServiceError("VERSION_UNSUPPORTED")
    if not isinstance(correlation, str) or not correlation or len(correlation) > 128:
        raise DesktopServiceError("INVALID_REQUEST")
    if not isinstance(request["command"], str):
        raise DesktopServiceError("INVALID_REQUEST")
    token = request["session_token"]
    if token is not None and (not isinstance(token, str) or len(token) > 128):
        raise DesktopServiceError("INVALID_REQUEST")
    data = service.dispatch(request["command"], request["payload"], token)
    return {
        "version": PROTOCOL_VERSION,
        "correlation_id": correlation,
        "status": "ok",
        "data": data,
    }


def run(stdin: BinaryIO, stdout: BinaryIO) -> int:
    service = DesktopApplicationService()
    try:
        while True:
            try:
                request = read_frame(stdin)
            except FrameError:
                return 2
            if request is None:
                return 0
            correlation = request.get("correlation_id", "invalid")
            if not isinstance(correlation, str) or len(correlation) > 128:
                correlation = "invalid"
            try:
                response = handle_request(service, request)
            except DesktopServiceError as exc:
                response = {
                    "version": PROTOCOL_VERSION,
                    "correlation_id": correlation,
                    "status": "error",
                    "error": {"code": exc.code},
                }
            except Exception:
                response = {
                    "version": PROTOCOL_VERSION,
                    "correlation_id": correlation,
                    "status": "error",
                    "error": {"code": "INTERNAL_ERROR"},
                }
            write_frame(stdout, response)
    finally:
        service.close()


def verify_sqlcipher_runtime() -> bool:
    """Prove the packaged sidecar contains the accepted SQLCipher runtime."""
    connection = _sqlcipher.connect(":memory:")
    try:
        row = connection.execute("PRAGMA cipher_version").fetchone()
        return bool(row and isinstance(row[0], str) and row[0])
    finally:
        connection.close()


def main() -> int:
    if not verify_sqlcipher_runtime():
        return 3
    return run(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
