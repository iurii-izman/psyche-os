"""Personal-profile Python sidecar entrypoint, packaged without Synthetic code."""

from __future__ import annotations

import os
import sys

from sqlcipher3 import dbapi2 as _sqlcipher

from psyche_os.interfaces.sidecar_protocol import run
from psyche_os.personal_mode.desktop_service import PersonalDesktopApplicationService
from psyche_os.personal_mode.runtime_profile import personal_runtime_paths


def verify_sqlcipher_runtime() -> bool:
    connection = _sqlcipher.connect(":memory:")
    try:
        row = connection.execute("PRAGMA cipher_version").fetchone()
        return bool(row and isinstance(row[0], str) and row[0])
    finally:
        connection.close()


def main() -> int:
    if not verify_sqlcipher_runtime() or len(sys.argv) != 1:
        return 2
    local_app_data = os.environ.get("PSYCHE_OS_LOCAL_APP_DATA")
    if not local_app_data:
        return 2
    return run(
        sys.stdin.buffer,
        sys.stdout.buffer,
        PersonalDesktopApplicationService(personal_runtime_paths(local_app_data=local_app_data)),
    )


if __name__ == "__main__":
    raise SystemExit(main())
