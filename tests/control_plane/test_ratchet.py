"""Versioned diagnostic baseline ratchet tests (component B).

Uses synthetic findings/baselines so no tool needs to run; the pure comparison
logic is the behavior under test.
"""
from __future__ import annotations

from pathlib import Path
import subprocess

import ai_dev_v2 as v2
import pytest

VERSION = "0.0.0"
FINGERPRINT = "abc123"


def _digest(ids: list[str]) -> str:
    return v2._sha256("\n".join(ids))


def baseline(ids: list[str], **overrides) -> dict:
    data = {
        "tool": "ruff",
        "tool_version": VERSION,
        "config_fingerprint": FINGERPRINT,
        "baseline_commit": "ceb3031",
        "finding_count": len(ids),
        "finding_identities": ids,
        "finding_identity_digest": _digest(ids),
        "captured_at": "2026-08-15T00:00:00+00:00",
    }
    data.update(overrides)
    return data


def current(ids: list[str], **overrides) -> dict:
    data = {
        "tool": "ruff",
        "tool_version": VERSION,
        "config_fingerprint": FINGERPRINT,
        "baseline_commit": "ceb3031",
        "finding_count": len(ids),
        "finding_identities": ids,
        "finding_identity_digest": _digest(ids),
        "captured_at": "2026-08-15T00:00:00+00:00",
    }
    data.update(overrides)
    return data


class TestRatchetComparison:
    def test_identical_baseline_passes(self) -> None:
        result = v2.ratchet_compare(baseline(["a", "b"]), current(["a", "b"]))
        assert result["status"] == "PASS"

    def test_new_finding_fails(self) -> None:
        result = v2.ratchet_compare(baseline(["a"]), current(["a", "b"]))
        assert result["status"] == "FAIL"
        assert result["new_findings"] == ["b"]

    def test_same_count_changed_identity_fails(self) -> None:
        # 1 old finding disappeared, 1 new appeared — count-only would miss this.
        result = v2.ratchet_compare(baseline(["a"]), current(["b"]))
        assert result["status"] == "FAIL"
        assert result["new_findings"] == ["b"]
        assert result["removed_findings"] == ["a"]

    def test_removed_only_is_improvement(self) -> None:
        result = v2.ratchet_compare(baseline(["a", "b"]), current(["a"]))
        assert result["status"] == "PASS"
        assert result["removed_findings"] == ["b"]


class TestBaselineCompatibility:
    def test_tool_version_change_is_incompatible(self) -> None:
        result = v2.ratchet_compare(
            baseline(["a"], tool_version="0.0.0"),
            current(["a", "b"], tool_version="0.0.1"),
        )
        assert result["status"] == "BASELINE_INCOMPATIBLE"

    def test_config_change_is_incompatible(self) -> None:
        result = v2.ratchet_compare(
            baseline(["a"], config_fingerprint="old"),
            current(["a", "b"], config_fingerprint="new"),
        )
        assert result["status"] == "BASELINE_INCOMPATIBLE"

    def test_incompatible_is_not_called_regression(self) -> None:
        result = v2.ratchet_compare(
            baseline(["a"], tool_version="0.0.0"),
            current(["a", "b"], tool_version="0.0.1"),
        )
        assert result["status"] != "FAIL"
        assert "regression" not in str(result).lower()


class TestMalformedBaseline:
    def test_malformed_baseline_fails_explicitly(self) -> None:
        result = v2.ratchet_compare({"tool": "ruff"}, current(["a"]))
        assert result["status"] == "FAIL"
        assert "malformed" in result["detail"]


class TestNoAutomaticRebaseline:
    def test_compare_does_not_mutate_baseline(self) -> None:
        base = baseline(["a"])
        snapshot = dict(base)
        snapshot["finding_identities"] = list(base["finding_identities"])
        v2.ratchet_compare(base, current(["a", "b"]))
        assert base == snapshot

    def test_compare_is_side_effect_free(self, monkeypatch) -> None:
        calls: list[str] = []

        def _noop(*args, **kwargs) -> None:
            calls.append("write")

        monkeypatch.setattr(v2, "write_proposal", _noop)
        monkeypatch.setattr(v2, "promote_proposal", _noop)
        v2.ratchet_compare(baseline(["a"]), current(["a", "b"]))
        assert calls == []


class TestToolIdentity:
    def test_wrong_baseline_tool_fails(self) -> None:
        result = v2.ratchet_compare(baseline(["a"], tool="mypy"), current(["a"], tool="ruff"))
        assert result["status"] == "FAIL"
        assert "tool mismatch" in result["detail"]

    def test_missing_baseline_commit_fails(self) -> None:
        base = baseline(["a"])
        del base["baseline_commit"]
        result = v2.ratchet_compare(base, current(["a"]))
        assert result["status"] == "FAIL"


class TestBaselineIntegrity:
    def test_tampered_digest_fails_closed(self) -> None:
        base = baseline(["a", "b"])
        base["finding_identity_digest"] = _digest(["forged"])
        result = v2.ratchet_compare(base, current(["a", "b"]))
        assert result["status"] == "FAIL"
        assert "digest" in result["detail"]

    def test_count_mismatch_fails_closed(self) -> None:
        base = baseline(["a", "b"])
        base["finding_count"] = 3
        result = v2.ratchet_compare(base, current(["a", "b"]))
        assert result["status"] == "FAIL"
        assert "count" in result["detail"]

    def test_non_list_identities_fails_closed(self) -> None:
        base = baseline(["a"])
        base["finding_identities"] = "not-a-list"
        result = v2.ratchet_compare(base, current(["a"]))
        assert result["status"] == "FAIL"

    def test_missing_digest_field_fails_closed(self) -> None:
        base = baseline(["a"])
        del base["finding_identity_digest"]
        result = v2.ratchet_compare(base, current(["a"]))
        assert result["status"] == "FAIL"


@pytest.fixture
def git_repo(tmp_path: Path) -> dict:
    repo = tmp_path / "repo"
    repo.mkdir()

    def g(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, text=True
        ).stdout.strip()

    g("init", "-q")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    (repo / "f.txt").write_text("a", encoding="utf-8")
    g("add", "f.txt")
    g("commit", "-q", "-m", "base")
    base = g("rev-parse", "HEAD")
    g("checkout", "-q", "-b", "side")
    (repo / "s.txt").write_text("s", encoding="utf-8")
    g("add", "s.txt")
    g("commit", "-q", "-m", "side")
    side = g("rev-parse", "HEAD")
    g("checkout", "-q", "-")
    (repo / "g.txt").write_text("g", encoding="utf-8")
    g("add", "g.txt")
    g("commit", "-q", "-m", "child")
    head = g("rev-parse", "HEAD")
    return {"repo": repo, "base": base, "side": side, "head": head}


class TestGitAncestry:
    def test_nonexistent_commit_fails(self, git_repo: dict) -> None:
        ok, why = v2.verify_baseline_git(
            baseline(["a"], baseline_commit="deadbeef" * 10), "ruff", git_repo["repo"], git_repo["head"]
        )
        assert not ok
        assert "not a valid git commit" in why

    def test_non_ancestor_commit_fails(self, git_repo: dict) -> None:
        ok, why = v2.verify_baseline_git(
            baseline(["a"], baseline_commit=git_repo["side"]), "ruff", git_repo["repo"], git_repo["head"]
        )
        assert not ok
        assert "ancestor" in why

    def test_valid_older_ancestor_allowed(self, git_repo: dict) -> None:
        ok, why = v2.verify_baseline_git(
            baseline(["a"], baseline_commit=git_repo["base"]), "ruff", git_repo["repo"], git_repo["head"]
        )
        assert ok, why


class TestProposePromote:
    def _write_canonical(self, repo: Path, tool: str, ids: list[str]) -> None:
        p = v2.canonical_baseline_path(tool, repo)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(v2._yaml_dump(baseline(ids)), encoding="utf-8")

    def test_propose_does_not_alter_canonical(self, tmp_path: Path) -> None:
        self._write_canonical(tmp_path, "ruff", ["a"])
        before = v2.canonical_baseline_path("ruff", tmp_path).read_text(encoding="utf-8")
        v2.write_proposal("ruff", tmp_path, baseline(["a", "b"]), "add b")
        after = v2.canonical_baseline_path("ruff", tmp_path).read_text(encoding="utf-8")
        assert before == after
        assert v2.proposal_path("ruff", tmp_path).is_file()

    def test_compare_after_proposal_still_fails(self, tmp_path: Path) -> None:
        self._write_canonical(tmp_path, "ruff", ["a"])
        v2.write_proposal("ruff", tmp_path, baseline(["a", "b"]), "add b")
        canonical = v2._yaml_load(v2.canonical_baseline_path("ruff", tmp_path))
        result = v2.ratchet_compare(canonical, baseline(["a", "b"]))
        assert result["status"] == "FAIL"
        assert result["new_findings"] == ["b"]

    def test_promote_without_evidence_rejected(self, tmp_path: Path) -> None:
        v2.write_proposal("ruff", tmp_path, baseline(["a", "b"]), "add b")
        with pytest.raises(ValueError):
            v2.promote_proposal("ruff", tmp_path, "add b", "")

    def test_promote_with_evidence_changes_canonical(self, tmp_path: Path) -> None:
        self._write_canonical(tmp_path, "ruff", ["a"])
        v2.write_proposal("ruff", tmp_path, baseline(["a", "b"]), "add b")
        v2.promote_proposal("ruff", tmp_path, "add b", "evidence:decision-X")
        canonical = v2._yaml_load(v2.canonical_baseline_path("ruff", tmp_path))
        assert canonical["finding_count"] == 2
        assert canonical["finding_identities"] == ["a", "b"]

    def test_subsequent_compare_uses_promoted_baseline(self, tmp_path: Path) -> None:
        self._write_canonical(tmp_path, "ruff", ["a"])
        v2.write_proposal("ruff", tmp_path, baseline(["a", "b"]), "add b")
        v2.promote_proposal("ruff", tmp_path, "add b", "evidence:decision-X")
        canonical = v2._yaml_load(v2.canonical_baseline_path("ruff", tmp_path))
        result = v2.ratchet_compare(canonical, baseline(["a", "b"]))
        assert result["status"] == "PASS"

    def test_history_preserves_old_baseline_identity(self, tmp_path: Path) -> None:
        self._write_canonical(tmp_path, "ruff", ["a"])
        old_digest = _digest(["a"])
        v2.write_proposal("ruff", tmp_path, baseline(["a", "b"]), "add b")
        v2.promote_proposal("ruff", tmp_path, "add b", "evidence:decision-X")
        history = v2.baseline_history_path(tmp_path).read_text(encoding="utf-8")
        assert old_digest in history
        assert "promote" in history
