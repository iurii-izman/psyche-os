"""Versioned diagnostic baseline ratchet tests (component B).

Uses synthetic findings/baselines so no tool needs to run; the pure comparison
logic is the behavior under test.
"""
from __future__ import annotations

import ai_dev_v2 as v2

VERSION = "0.0.0"
FINGERPRINT = "abc123"


def baseline(ids: list[str], **overrides) -> dict:
    data = {
        "tool": "ruff",
        "tool_version": VERSION,
        "config_fingerprint": FINGERPRINT,
        "baseline_commit": "ceb3031",
        "finding_count": len(ids),
        "finding_identities": ids,
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

        monkeypatch.setattr(v2, "_write_baseline", _noop)
        v2.ratchet_compare(baseline(["a"]), current(["a", "b"]))
        assert calls == []
