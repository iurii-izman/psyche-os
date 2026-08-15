"""Versioned diagnostic baseline ratchet tests (component B).

Uses synthetic findings/baselines so no tool needs to run; the pure comparison
logic is the behavior under test. F4b adds the immutable-baseline-source proof:
comparison loads the canonical baseline from an explicit Git commit SHA (via
`git show`), never the mutable working-tree file, and the coding-agent CLI has
no canonical-baseline write path.
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


@pytest.fixture
def ratchet_repo(tmp_path: Path) -> dict:
    """A git repo with a canonical baseline file (findings A) committed at `trusted`."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def g(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=str(repo), capture_output=True, text=True
        ).stdout.strip()

    g("init", "-q")
    g("config", "user.email", "t@example.com")
    g("config", "user.name", "t")
    (repo / "seed.txt").write_text("seed", encoding="utf-8")
    g("add", "seed.txt")
    g("commit", "-q", "-m", "seed")
    seed = g("rev-parse", "HEAD")

    rel = v2.baseline_rel_path("ruff")
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(v2._yaml_dump(baseline(["a"], baseline_commit=seed)), encoding="utf-8")
    g("add", rel)
    g("commit", "-q", "-m", "baseline A")
    trusted = g("rev-parse", "HEAD")

    return {"repo": repo, "seed": seed, "trusted": trusted, "g": g, "rel": rel}


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

    def test_tool_mismatch_fails(self, git_repo: dict) -> None:
        ok, why = v2.verify_baseline_git(
            baseline(["a"], tool="mypy", baseline_commit=git_repo["base"]),
            "ruff",
            git_repo["repo"],
            git_repo["head"],
        )
        assert not ok
        assert "tool" in why

    def test_corrupt_digest_fails(self, git_repo: dict) -> None:
        base = baseline(["a"], baseline_commit=git_repo["base"])
        base["finding_identity_digest"] = _digest(["forged"])
        ok, why = v2.verify_baseline_git(base, "ruff", git_repo["repo"], git_repo["head"])
        assert not ok
        assert "digest" in why


class TestImmutableBaselineSource:
    """A/B/C: comparison must read the trusted Git SHA, not the working-tree file."""

    def test_compare_loads_baseline_from_git_sha_not_working_tree(self, ratchet_repo: dict) -> None:
        repo, trusted, seed = ratchet_repo["repo"], ratchet_repo["trusted"], ratchet_repo["seed"]
        # Overwrite the working-tree baseline with A+B; the trusted SHA still holds A.
        (repo / ratchet_repo["rel"]).write_text(
            v2._yaml_dump(baseline(["a", "b"], baseline_commit=seed)), encoding="utf-8"
        )
        result = v2.ratchet_compare_from_ref("ruff", repo, trusted, trusted, current(["a"]))
        assert result["status"] == "PASS"
        assert result["detail"] == "no new diagnostics"  # read A from SHA, ignored A+B
        assert result["baseline_sha"] == trusted
        assert result["baseline_path"] == v2.baseline_rel_path("ruff")

    def test_working_tree_mutation_does_not_change_result(self, ratchet_repo: dict) -> None:
        repo, trusted, seed = ratchet_repo["repo"], ratchet_repo["trusted"], ratchet_repo["seed"]
        before = v2.ratchet_compare_from_ref("ruff", repo, trusted, trusted, current(["a", "b"]))
        assert before["status"] == "FAIL"
        assert before["new_findings"] == ["b"]
        # Mutate the working-tree baseline after the trusted SHA; result must be unchanged.
        (repo / ratchet_repo["rel"]).write_text(
            v2._yaml_dump(baseline(["a", "b"], baseline_commit=seed)), encoding="utf-8"
        )
        after = v2.ratchet_compare_from_ref("ruff", repo, trusted, trusted, current(["a", "b"]))
        assert after["status"] == "FAIL"
        assert after["new_findings"] == ["b"]

    def test_working_tree_absorbs_new_diagnostic_still_fails(self, ratchet_repo: dict) -> None:
        """Central anti-reward-hacking invariant: absorbing a defect into the working-tree
        baseline must not green a trusted-ref comparison."""
        repo, trusted, seed = ratchet_repo["repo"], ratchet_repo["trusted"], ratchet_repo["seed"]
        (repo / ratchet_repo["rel"]).write_text(
            v2._yaml_dump(baseline(["a", "b"], baseline_commit=seed)), encoding="utf-8"
        )
        result = v2.ratchet_compare_from_ref("ruff", repo, trusted, trusted, current(["a", "b"]))
        assert result["status"] == "FAIL"
        assert result["new_findings"] == ["b"]


class TestBaselineRefResolution:
    def test_nonexistent_baseline_ref_fails(self, ratchet_repo: dict) -> None:
        result = v2.ratchet_compare_from_ref(
            "ruff", ratchet_repo["repo"], "deadbeef" * 10, ratchet_repo["trusted"], current(["a"])
        )
        assert result["status"] == "FAIL"
        assert "resolve" in result["detail"]

    def test_baseline_file_absent_at_ref_fails(self, ratchet_repo: dict) -> None:
        # `seed` predates the baseline file; the file is absent at that ref.
        result = v2.ratchet_compare_from_ref(
            "ruff", ratchet_repo["repo"], ratchet_repo["seed"], ratchet_repo["trusted"], current(["a"])
        )
        assert result["status"] == "FAIL"
        assert "absent" in result["detail"]

    def test_compare_requires_baseline_ref(self, tmp_path: Path, capsys) -> None:
        rc = v2.main(["--repo", str(tmp_path), "ratchet", "compare"])
        assert rc == 2
        assert "baseline-ref" in capsys.readouterr().out


class TestProposeOnly:
    def test_propose_does_not_alter_canonical(self, ratchet_repo: dict) -> None:
        repo, trusted = ratchet_repo["repo"], ratchet_repo["trusted"]
        before = (repo / ratchet_repo["rel"]).read_text(encoding="utf-8")
        v2.write_proposal(
            "ruff", repo, baseline(["a", "b"]), "add b",
            baseline_ref=trusted, baseline_sha=trusted, canonical=baseline(["a"]),
        )
        after = (repo / ratchet_repo["rel"]).read_text(encoding="utf-8")
        assert before == after
        assert v2.proposal_path("ruff", repo).is_file()

    def test_proposal_retains_canonical_digest_and_source_sha(self, ratchet_repo: dict) -> None:
        repo, trusted = ratchet_repo["repo"], ratchet_repo["trusted"]
        canonical = baseline(["a"])
        v2.write_proposal(
            "ruff", repo, baseline(["a", "b"]), "add b",
            baseline_ref=trusted, baseline_sha=trusted, canonical=canonical,
        )
        prop = v2._yaml_load(v2.proposal_path("ruff", repo))
        assert prop["current_canonical_digest"] == canonical["finding_identity_digest"]
        assert prop["baseline_sha"] == trusted
        assert prop["baseline_ref"] == trusted

    def test_propose_after_failure_compare_still_fails(self, ratchet_repo: dict) -> None:
        repo, trusted = ratchet_repo["repo"], ratchet_repo["trusted"]
        v2.write_proposal(
            "ruff", repo, baseline(["a", "b"]), "add b",
            baseline_ref=trusted, baseline_sha=trusted, canonical=baseline(["a"]),
        )
        result = v2.ratchet_compare_from_ref("ruff", repo, trusted, trusted, current(["a", "b"]))
        assert result["status"] == "FAIL"
        assert result["new_findings"] == ["b"]


class TestNoAutonomousPromotion:
    def test_no_autonomous_promotion_function(self) -> None:
        assert not hasattr(v2, "promote_proposal")
        assert not hasattr(v2, "_load_canonical")

    def test_promote_returns_human_gate_required(self, tmp_path: Path, capsys) -> None:
        rc = v2.main(["--repo", str(tmp_path), "ratchet", "promote"])
        assert rc == 1
        assert "HUMAN_GATE_REQUIRED" in capsys.readouterr().out

    def test_promote_performs_no_canonical_write(self, ratchet_repo: dict, capsys) -> None:
        repo = ratchet_repo["repo"]
        before = (repo / ratchet_repo["rel"]).read_text(encoding="utf-8")
        v2.main(["--repo", str(repo), "ratchet", "promote", "--reason", "x"])
        after = (repo / ratchet_repo["rel"]).read_text(encoding="utf-8")
        assert before == after
        assert "HUMAN_GATE_REQUIRED" in capsys.readouterr().out

    def test_compare_and_propose_never_write_canonical(self, ratchet_repo: dict) -> None:
        repo, trusted = ratchet_repo["repo"], ratchet_repo["trusted"]
        before = (repo / ratchet_repo["rel"]).read_text(encoding="utf-8")
        v2.ratchet_compare_from_ref("ruff", repo, trusted, trusted, current(["a", "b"]))
        v2.write_proposal(
            "ruff", repo, baseline(["a", "b"]), "add b",
            baseline_ref=trusted, baseline_sha=trusted, canonical=baseline(["a"]),
        )
        after = (repo / ratchet_repo["rel"]).read_text(encoding="utf-8")
        assert before == after
