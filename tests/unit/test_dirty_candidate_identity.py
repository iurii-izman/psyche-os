from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("dirty_candidate_identity", ROOT / "scripts" / "dev" / "dirty_candidate_identity.py")
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_manifest_is_explicit_lexical_and_rejects_parent_paths(tmp_path: Path) -> None:
    manifest = tmp_path / "owned.txt"
    manifest.write_text("# comment\nz.txt\na.txt\n", encoding="utf-8")
    assert MODULE.read_manifest(manifest) == ["a.txt", "z.txt"]
    manifest.write_text("../outside.txt\n", encoding="utf-8")
    try:
        MODULE.read_manifest(manifest)
    except ValueError as error:
        assert "repository-relative" in str(error)
    else:
        raise AssertionError("parent path was accepted")


def test_detached_receipt_verification_rejects_tampering(tmp_path: Path, monkeypatch) -> None:
    expected = {
        "receipt_version": "PMV1-DIRTY-CANDIDATE-DETACHED-RECEIPT-V1",
        "candidate_algorithm": "PSYCHE-OS-DIRTY-CANDIDATE-v1",
        "head": "head",
        "origin_main": "main",
        "manifest_path": "owned.txt",
        "manifest_sha256": "manifest",
        "task_owned_count": 1,
        "candidate_sha256": "expected",
        "evidence_file_path": "evidence.md",
        "evidence_file_sha256": "evidence",
        "real_data_gate": "CLOSED",
    }
    receipt_path = tmp_path / "receipt.json"
    receipt_path.write_text(json.dumps(expected), encoding="utf-8")
    monkeypatch.setattr(MODULE, "detached_receipt", lambda _root, _manifest: expected)
    MODULE.verify_detached_receipt(tmp_path, tmp_path / "owned.txt", receipt_path)
    expected["candidate_sha256"] = "tampered"
    receipt_path.write_text(json.dumps(expected), encoding="utf-8")
    expected["candidate_sha256"] = "expected"
    try:
        MODULE.verify_detached_receipt(tmp_path, tmp_path / "owned.txt", receipt_path)
    except ValueError as error:
        assert "candidate_sha256" in str(error)
    else:
        raise AssertionError("tampered receipt was accepted")
