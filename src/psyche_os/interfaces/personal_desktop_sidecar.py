"""Personal-profile Python sidecar entrypoint, packaged without Synthetic code."""

from __future__ import annotations

import os
import sys

from sqlcipher3 import dbapi2 as _sqlcipher

from psyche_os.interfaces.sidecar_protocol import run
from psyche_os.personal_mode.admission_token import token_evaluator
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
    admission_root = os.environ.get("PSYCHE_OS_PERSONAL_ADMISSION_ROOT")
    build_identity = os.environ.get("PSYCHE_OS_PERSONAL_BUILD_ID")
    profile_id = os.environ.get("PSYCHE_OS_PERSONAL_PROFILE_ID")
    profile_digest = os.environ.get("PSYCHE_OS_PERSONAL_PROFILE_DIGEST")
    paths = personal_runtime_paths(local_app_data=local_app_data) if local_app_data else None
    if (
        not all((local_app_data, admission_root, build_identity, profile_id, profile_digest))
        or paths is None
        or os.path.normcase(os.path.normpath(admission_root))
        != os.path.normcase(os.path.normpath(str(paths.root)))
    ):
        return 2
    return run(
        sys.stdin.buffer,
        sys.stdout.buffer,
        PersonalDesktopApplicationService(
            paths,
            evaluator=token_evaluator(
                paths.root,
                candidate_identity=build_identity,
                profile_id=profile_id,
                profile_digest=profile_digest,
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
