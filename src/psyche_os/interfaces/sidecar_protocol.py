"""Shared, profile-neutral length-framed sidecar protocol."""

from __future__ import annotations

import json
import struct
from typing import Any, BinaryIO, Protocol

PROTOCOL_VERSION = "1.0"
MAX_FRAME_BYTES = 65_536
REQUEST_FIELDS = frozenset({"version", "command", "correlation_id", "session_token", "payload"})


class FrameError(Exception):
    pass


class DispatchService(Protocol):
    def dispatch(
        self, command: str, payload: dict[str, Any], session_token: str | None
    ) -> dict[str, Any]: ...

    def close(self) -> None: ...


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


def _oversized_response(correlation_id: str) -> dict[str, Any]:
    return {
        "version": PROTOCOL_VERSION,
        "correlation_id": correlation_id,
        "status": "error",
        "error": {"code": "RESPONSE_TOO_LARGE"},
    }


def handle_request(service: DispatchService, request: dict[str, Any]) -> dict[str, Any]:
    correlation = request.get("correlation_id")
    if set(request) != REQUEST_FIELDS:
        raise FrameError("INVALID_REQUEST")
    if request["version"] != PROTOCOL_VERSION:
        raise FrameError("VERSION_UNSUPPORTED")
    if not isinstance(correlation, str) or not correlation or len(correlation) > 128:
        raise FrameError("INVALID_REQUEST")
    if not isinstance(request["command"], str):
        raise FrameError("INVALID_REQUEST")
    token = request["session_token"]
    if token is not None and (not isinstance(token, str) or len(token) > 128):
        raise FrameError("INVALID_REQUEST")
    return {
        "version": PROTOCOL_VERSION,
        "correlation_id": correlation,
        "status": "ok",
        "data": service.dispatch(request["command"], request["payload"], token),
    }


def run(stdin: BinaryIO, stdout: BinaryIO, service: DispatchService) -> int:
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
            except Exception as exc:
                code = getattr(exc, "code", None)
                if not isinstance(code, str):
                    code = "INTERNAL_ERROR"
                response = {
                    "version": PROTOCOL_VERSION,
                    "correlation_id": correlation,
                    "status": "error",
                    "error": {"code": code},
                }
            try:
                write_frame(stdout, response)
            except FrameError as exc:
                if str(exc) != "RESPONSE_TOO_LARGE":
                    return 2
                write_frame(stdout, _oversized_response(correlation))
    finally:
        service.close()
