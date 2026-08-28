"""Test-only admitted Personal sidecar; it is never a package entrypoint."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import os
import sys
from typing import cast

from psyche_os.interfaces.sidecar_protocol import run  # type: ignore[import-untyped]
from psyche_os.personal_mode.admission import AdmissionDecision  # type: ignore[import-untyped]
from psyche_os.personal_mode.desktop_service import (  # type: ignore[import-untyped]
    PersonalDesktopApplicationService,
)
from psyche_os.personal_mode.runtime import PersonalRuntime  # type: ignore[import-untyped]
from psyche_os.personal_mode.runtime_profile import (  # type: ignore[import-untyped]
    personal_runtime_paths,
)


class _SyntheticDpapi:
    available = True

    def protect(self, value: bytes, description: str) -> bytes:
        return b"synthetic-dpapi:" + value

    def unprotect(self, blob: bytes) -> bytes:
        prefix = b"synthetic-dpapi:"
        if not blob.startswith(prefix):
            raise ValueError("invalid synthetic DPAPI blob")
        return blob[len(prefix) :]


def main() -> int:
    local_app_data = os.environ["PSYCHE_OS_LOCAL_APP_DATA"]
    now = datetime.now(UTC)
    decision = AdmissionDecision(True, "synthetic-test", "digest", "attestation", "profile", "candidate", now + timedelta(minutes=5))
    service = PersonalDesktopApplicationService(
        personal_runtime_paths(local_app_data=local_app_data),
        evaluator=lambda: decision,
        clock=lambda: now,
        runtime_factory=lambda paths, guard: PersonalRuntime(paths, guard, os_wrapper_factory=_SyntheticDpapi),
    )
    return cast(int, run(sys.stdin.buffer, sys.stdout.buffer, service))


if __name__ == "__main__":
    raise SystemExit(main())
