"""Shared setup for V2 control-plane tests.

Puts the repository-native control-plane modules on the import path the same
way the hook dispatcher does (`sys.path.insert(0, .ai-dev/hooks)`), plus the
`scripts/` directory for `ai_dev_v2`.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]

for extra in (
    str(ROOT / "scripts"),
    str(ROOT / ".ai-dev" / "hooks"),
    str(ROOT / ".ai-dev" / "telemetry"),
):
    if extra not in sys.path:
        sys.path.insert(0, extra)
