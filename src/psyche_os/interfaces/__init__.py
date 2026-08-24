"""Interfaces layer with profile-neutral package initialization."""

from __future__ import annotations

from importlib import import_module
from typing import Any

__all__ = [
    "F0CLI",
    "CliError",
    "CliResult",
    "Command",
    "ExitCode",
    "create_cli",
]


def __getattr__(name: str) -> Any:
    """Keep importing a narrow sidecar from loading the full CLI surface."""
    if name in __all__:
        return getattr(import_module(__name__ + ".cli"), name)
    raise AttributeError(name)
