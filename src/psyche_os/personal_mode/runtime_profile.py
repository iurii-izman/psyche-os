"""Trusted physical-root selection for the two runtime profiles."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import os
from pathlib import Path


class RuntimeProfile(StrEnum):
    SYNTHETIC_LAB = "SYNTHETIC_LAB"
    LOCAL_PERSONAL = "LOCAL_PERSONAL"


@dataclass(frozen=True, slots=True)
class PersonalRuntimePaths:
    """Fixed Personal paths; callers cannot provide individual file paths."""

    root: Path

    @property
    def vault(self) -> Path:
        return self.root / "vault.sqlite"

    @property
    def envelope(self) -> Path:
        return self.root / "key-envelope.pmv1.json"

    @property
    def backups(self) -> Path:
        return self.root / "backups"

    @property
    def staging(self) -> Path:
        return self.root / "staging"

    @property
    def exports(self) -> Path:
        return self.root / "exports"

    @property
    def retained_keys(self) -> Path:
        return self.root / "retained-keys"

    @property
    def rotation_journal(self) -> Path:
        return self.root / "rotation.pmv1.json"


def personal_runtime_paths(*, local_app_data: str | Path | None = None) -> PersonalRuntimePaths:
    """Return the one fixed Personal root without creating it.

    ``local_app_data`` is a trusted composition dependency for tests and the
    Rust launcher; it is never accepted from IPC or renderer payloads.
    """
    base = Path(local_app_data) if local_app_data is not None else Path(os.environ["LOCALAPPDATA"])
    return PersonalRuntimePaths(base / "PSYCHE OS" / "Personal")
