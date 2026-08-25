from __future__ import annotations

import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def canonical_profile_digest(content: bytes) -> str:
    """The Personal launcher must use E11's LF-normalized UTF-8 identity."""
    return hashlib.sha256(content.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")).hexdigest()


def test_personal_profile_digest_is_checkout_representation_independent() -> None:
    lf = (ROOT / "docs" / "architecture" / "REAL_DATA_GATE_PROFILE.yaml").read_bytes().replace(b"\r\n", b"\n")
    crlf = lf.replace(b"\n", b"\r\n")
    assert canonical_profile_digest(lf) == canonical_profile_digest(crlf)
    assert canonical_profile_digest(lf) == "50f8f9b684b4db14df482ef8f461c8c95bf99ba3ec35842059fa56d08859d1f7"


def test_personal_build_uses_the_canonical_profile_representation() -> None:
    build = (ROOT / "desktop" / "scripts" / "build-personal.ps1").read_text(encoding="utf-8")
    assert '$profileText.Replace("`r`n", "`n").Replace("`r", "`n")' in build
    assert "ReadAllBytes" not in build
