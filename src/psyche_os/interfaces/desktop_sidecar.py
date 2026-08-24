"""Synthetic-profile Python sidecar entrypoint.

This executable is intentionally separate from the Personal sidecar package.
"""

from __future__ import annotations

import sys
from typing import BinaryIO

from sqlcipher3 import dbapi2 as _sqlcipher

from psyche_os.application.desktop_service import DesktopApplicationService
from psyche_os.interfaces.sidecar_protocol import (
    run as _run,
)


def run(stdin: BinaryIO, stdout: BinaryIO) -> int:
    return _run(stdin, stdout, DesktopApplicationService())


def verify_sqlcipher_runtime() -> bool:
    connection = _sqlcipher.connect(":memory:")
    try:
        row = connection.execute("PRAGMA cipher_version").fetchone()
        return bool(row and isinstance(row[0], str) and row[0])
    finally:
        connection.close()


def main() -> int:
    if not verify_sqlcipher_runtime():
        return 3
    if len(sys.argv) != 1:
        return 2
    return run(sys.stdin.buffer, sys.stdout.buffer)


if __name__ == "__main__":
    raise SystemExit(main())
