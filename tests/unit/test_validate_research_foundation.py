"""Focused regressions for research-validator security hygiene."""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "validate_research_foundation.py"
SPEC = importlib.util.spec_from_file_location("research_foundation_validator", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def test_secret_scanner_does_not_exempt_synthetic_or_neighboring_tokens(tmp_path: Path) -> None:
    fixture = tmp_path / "synthetic-fixture.yaml"
    token = "sk-proj-" + "syntheticsecretvalue0123456789"
    fixture.write_text(f"token: {token}\n", encoding="utf-8")

    allowlist = {"synthetic-fixture.yaml": frozenset({token})}
    assert VALIDATOR.potential_plaintext_secret_matches(tmp_path, [fixture], allowlist) == []

    fixture.write_text(f"token: {token}x\n", encoding="utf-8")
    assert VALIDATOR.potential_plaintext_secret_matches(tmp_path, [fixture], allowlist) == [
        "synthetic-fixture.yaml"
    ]
