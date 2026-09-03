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
    assert "AIInterview" in build
    assert "local_personal_ai_interview_openai_windows_v1" in build
    assert (ROOT / "docs" / "architecture" / "REAL_DATA_GATE_PROFILE_AI_INTERVIEW_OPENAI.yaml").is_file()


def test_personal_release_binding_is_explicit_and_cache_safe() -> None:
    build_rs = (ROOT / "desktop" / "src-tauri" / "build.rs").read_text(encoding="utf-8")
    product = (ROOT / "desktop" / "src-tauri" / "src" / "personal_product.rs").read_text(encoding="utf-8")
    for name in ("PSYCHE_OS_PERSONAL_BUILD_ID", "PSYCHE_OS_PERSONAL_PROFILE_DIGEST"):
        assert name in build_rs
    assert "cargo:rerun-if-env-changed={BUILD_ID}" in build_rs
    assert "cargo:rerun-if-env-changed={PROFILE_DIGEST}" in build_rs
    assert "cargo:rustc-env=PSYCHE_OS_PERSONAL_BUILD_ID=" in build_rs
    assert "cargo:rustc-env=PSYCHE_OS_PERSONAL_PROFILE_DIGEST=" in build_rs
    assert "Personal release builds require valid" in build_rs
    assert 'personal_openai_command_manifest::SHIPPED_COMMANDS' in build_rs
    assert '#[path = "src/personal_openai_command_manifest.rs"]\nmod personal_openai_command_manifest;' in build_rs
    assert 'env!("PSYCHE_OS_PERSONAL_BUILD_ID")' in product
    assert 'env!("PSYCHE_OS_PERSONAL_PROFILE_DIGEST")' in product
    assert "option_env!(\"PSYCHE_OS_PERSONAL_" not in product
