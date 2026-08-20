"""Focused unit tests for the AI Dev OS v2 performance canary tooling.

The tests build a small synthetic repository in a temp dir (never real app data) and
exercise the pure index/impact/context/verify-selection logic in `scripts/ai_dev_perf.py`.
Subprocess-dependent paths (lexical/structural search) are stubbed where a test only
targets the deterministic index logic.
"""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_perf  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(root: Path, rel: str, text: str) -> None:
    path = root.joinpath(*rel.split("/"))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@pytest.fixture
def fake_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A synthetic package with a small dependency chain and mapped tests."""
    root = tmp_path / "fake"
    files = {
        "src/psyche_os/__init__.py": "",
        "src/psyche_os/domain/__init__.py": "",
        "src/psyche_os/domain/ids.py": (
            '"""Opaque identities."""\n\n'
            "from __future__ import annotations\n\n"
            'VAULT_PREFIX = "v"\n\n'
            "def generate_id() -> str:\n"
            '    """Generate a new opaque id."""\n'
            "    return 'id-123'\n\n"
            "class OpaqueId:\n"
            "    def __init__(self, value: str) -> None:\n"
            "        self.value = value\n"
            "    def __str__(self) -> str:\n"
            "        return self.value\n"
        ),
        "src/psyche_os/domain/entities.py": (
            "from .ids import OpaqueId\n\n"
            "class Subject:\n"
            "    def __init__(self, oid: OpaqueId) -> None:\n"
            "        self.oid = oid\n"
        ),
        "src/psyche_os/app/__init__.py": "",
        "src/psyche_os/app/leaf.py": (
            "def helper(x: int) -> int:\n"
            "    return x + 1\n"
        ),
        "src/psyche_os/app/service.py": (
            "from ..domain.entities import Subject\n"
            "from ..domain.ids import OpaqueId\n\n"
            "class Service:\n"
            "    def create(self) -> Subject:\n"
            "        return Subject(OpaqueId('x'))\n"
        ),
        "src/psyche_os/interfaces/__init__.py": "",
        "src/psyche_os/interfaces/cli.py": (
            "from ..app.service import Service\n\n"
            "class Cli:\n"
            "    def __init__(self) -> None:\n"
            "        self.service = Service()\n"
        ),
        "src/psyche_os/crypto/__init__.py": "",
        "src/psyche_os/crypto/box.py": (
            "def seal(payload: bytes) -> bytes:\n"
            "    return b'sealed:' + payload\n"
        ),
        "tests/test_ids.py": (
            "from psyche_os.domain.ids import OpaqueId, generate_id\n\n"
            "def test_generate() -> None:\n"
            "    assert generate_id() == 'id-123'\n\n"
            "def test_oid() -> None:\n"
            "    assert str(OpaqueId('x')) == 'x'\n"
        ),
        "tests/test_service.py": (
            "from psyche_os.app.service import Service\n\n"
            "def test_create() -> None:\n"
            "    assert Service() is not None\n"
        ),
        "tests/test_cli.py": (
            "from psyche_os.interfaces.cli import Cli\n\n"
            "def test_cli() -> None:\n"
            "    assert Cli() is not None\n"
        ),
    }
    for rel, text in files.items():
        _write(root, rel, text)
    monkeypatch.setattr(ai_dev_perf, "REPO", root)
    return root


def make_config(root: Path) -> dict:
    return {
        "src_roots": ["src/psyche_os"],
        "test_root": "tests",
        "context_token_target": 20000,
        "chars_per_token": 4.0,
        "lexical_merge_gap": 4,
        "index_cache": ".ai-dev/evidence/performance/index.json",
        "runs_dir": ".ai-dev/evidence/performance/runs",
    }


# --------------------------------------------------------------------------- estimate


class TestEstimate:
    def test_tokens_positive_and_monotonic(self) -> None:
        assert ai_dev_perf.estimate_tokens("") == 1
        short = ai_dev_perf.estimate_tokens("hello world")
        longer = ai_dev_perf.estimate_tokens("hello world " * 100)
        assert short >= 1
        assert longer > short

    def test_token_volume_from_chars(self) -> None:
        assert ai_dev_perf.estimate_token_volume(8) == 2
        assert ai_dev_perf.estimate_token_volume(0) == 1


# --------------------------------------------------------------------------- index


class TestIndex:
    def test_symbols_have_exact_ranges(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        ids = index.modules["domain/ids.py"]
        names = {s.name: s for s in ids.symbols}
        assert names["generate_id"].start == 7  # 1-based def line
        assert names["OpaqueId"].kind == "class"
        assert "VAULT_PREFIX" in names  # module-level variable binding

    def test_relative_import_edges(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        assert "domain/ids.py" in index.modules["domain/entities.py"].imports
        assert "domain/entities.py" in index.modules["app/service.py"].imports
        assert "app/service.py" in index.modules["interfaces/cli.py"].imports
        # reverse[dep] = importers: ids is imported by entities, entities by service.
        assert "domain/entities.py" in index.reverse["domain/ids.py"]
        assert "app/service.py" in index.reverse["domain/entities.py"]

    def test_test_map_import_based(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        assert "domain/ids.py" in index.test_map["tests/test_ids.py"]
        assert "app/service.py" in index.test_map["tests/test_service.py"]
        assert "interfaces/cli.py" in index.test_map["tests/test_cli.py"]

    def test_key_for_path(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        abs_path = str(fake_repo / "src/psyche_os/domain/ids.py")
        assert index.key_for_path(abs_path) == "domain/ids.py"
        assert index.key_for_path("src/psyche_os/domain/ids.py") == "domain/ids.py"
        assert index.key_for_path("src/psyche_os/nope.py") is None

    def test_cache_hit_and_roundtrip(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index1, hit1 = ai_dev_perf.get_index(config, use_cache=True)
        assert hit1 is False
        index2, hit2 = ai_dev_perf.get_index(config, use_cache=True)
        assert hit2 is True
        assert index1.modules == index2.modules
        assert index1.test_map == index2.test_map

    def test_cache_invalidated_on_change(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = make_config(fake_repo)
        ai_dev_perf.get_index(config, use_cache=True)
        _write(fake_repo, "src/psyche_os/domain/ids.py", "def changed() -> None:\n    pass\n")
        index, hit = ai_dev_perf.get_index(config, use_cache=True)
        assert hit is False
        assert "changed" in {s.name for s in index.modules["domain/ids.py"].symbols}


# --------------------------------------------------------------------------- impact


class TestImpact:
    def test_reverse_dependency_closure(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/domain/ids.py"])
        assert set(surface["changed"]) == {"domain/ids.py"}
        assert surface["affected_modules"] == sorted(
            {"domain/ids.py", "domain/entities.py", "app/service.py", "interfaces/cli.py"}
        )
        assert set(surface["affected_tests"]) == {"tests/test_ids.py", "tests/test_service.py", "tests/test_cli.py"}

    def test_leaf_module_small_surface(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/app/leaf.py"])
        assert surface["closure_size"] == 1
        assert surface["affected_tests"] == []

    def test_classify_high_risk_boundary(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/crypto/box.py"])
        assert ai_dev_perf.classify_impact(index, surface)["level"] == "high"

    def test_classify_cross_module_medium(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/domain/ids.py"])
        assert ai_dev_perf.classify_impact(index, surface)["level"] == "medium"

    def test_classify_single_module_low(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        # An isolated non-boundary module with no importers and no interface reach.
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/app/leaf.py"])
        assert surface["closure_size"] == 1
        assert ai_dev_perf.classify_impact(index, surface)["level"] == "low"


# --------------------------------------------------------------------------- context


class TestContext:
    def test_symbol_context_is_exact_range(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        monkeypatch.setattr(ai_dev_perf, "check_tools", lambda need: {"rg": "rg", "ast-grep": "sg"})
        monkeypatch.setattr(ai_dev_perf, "_lexical_items", lambda *a, **k: [])
        bundle = ai_dev_perf.assemble_context(index, ["OpaqueId"], target=10000)
        items = [i for i in bundle["items"] if i["source"] == "index-symbol" and i["reason"].startswith("symbol 'OpaqueId'")]
        assert items
        item = items[0]
        # The range must be inside the module, not the whole file.
        full_chars = len(ai_dev_perf.read_text(fake_repo / "src/psyche_os/domain/ids.py"))
        assert item["end"] - item["start"] + 1 < 6
        assert len(item["text"]) < full_chars
        assert item["tokens"] < ai_dev_perf.estimate_tokens(ai_dev_perf.extract_range("src/psyche_os/domain/ids.py", 1, 30))

    def test_context_obeys_token_target(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        monkeypatch.setattr(ai_dev_perf, "check_tools", lambda need: {"rg": "rg", "ast-grep": "sg"})
        monkeypatch.setattr(ai_dev_perf, "_lexical_items", lambda *a, **k: [])
        bundle = ai_dev_perf.assemble_context(index, ["OpaqueId", "Subject", "Service"], target=50)
        assert bundle["total_tokens"] <= 50
        assert bundle["truncated"] is True  # more candidates than the tiny target


# --------------------------------------------------------------------------- verify


class TestVerify:
    def test_plan_selects_mapped_tests(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/domain/ids.py"])
        test_paths = ai_dev_perf.select_test_paths(index, surface["affected_modules"])
        plan = ai_dev_perf.verify_plan(index, test_paths, full=False)
        assert plan["command"] is not None
        joined = " ".join(plan["command"])
        assert "pytest" in joined
        for t in ("tests/test_ids.py", "tests/test_service.py"):
            assert t in joined
        assert plan["gate"] == "V1/V2 targeted"

    def test_plan_full_gate(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        plan = ai_dev_perf.verify_plan(index, [], full=True)
        assert plan["command"] == ["uv", "run", "pytest", "-q"]
        assert plan["gate"] == "V3 final gate"

    def test_plan_no_mapped_tests(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        plan = ai_dev_perf.verify_plan(index, [], full=False)
        assert plan["command"] is None
        assert plan["gate"] == "no mapped tests"


# --------------------------------------------------------------------------- prompt


class TestPrompt:
    def test_prompt_packet_is_self_contained(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        monkeypatch.setattr(ai_dev_perf, "check_tools", lambda need: {"rg": "rg", "ast-grep": "sg"})
        monkeypatch.setattr(ai_dev_perf, "_lexical_items", lambda *a, **k: [])
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/domain/ids.py"])
        impact = {**surface, "level": ai_dev_perf.classify_impact(index, surface)["level"]}
        test_paths = ai_dev_perf.select_test_paths(index, surface["affected_modules"])
        verify = ai_dev_perf.verify_plan(index, test_paths, full=False)
        context = ai_dev_perf.assemble_context(index, ["OpaqueId"], target=10000)
        markdown = ai_dev_perf.assemble_prompt("Fix OpaqueId", context, impact, verify)
        assert "## Task" in markdown
        assert "Fix OpaqueId" in markdown
        assert "domain/ids.py" in markdown
        assert "uv run pytest" in markdown
        assert "classification: medium" in markdown


# --------------------------------------------------------------------------- CLI wiring


class TestCli:
    def test_map_json_is_valid(self, fake_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        config = make_config(fake_repo)
        args = argparse_namespace(command="map", json=True, no_cache=True)
        rc = ai_dev_perf.cmd_map(args, config)
        assert rc == 0
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert parsed["stats"]["modules"] == 11

    def test_impact_json_surface(self, fake_repo: Path, capsys: pytest.CaptureFixture[str]) -> None:
        config = make_config(fake_repo)
        args = argparse_namespace(command="impact", json=True, paths=["src/psyche_os/domain/ids.py"], symbols=[], git_diff=False, base="HEAD")
        rc = ai_dev_perf.cmd_impact(args, config)
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        assert "domain/ids.py" in parsed["surface"]["affected_modules"]


def argparse_namespace(**kwargs) -> object:
    from types import SimpleNamespace

    return SimpleNamespace(**kwargs)


# --------------------------------------------------------------------------- F4 cache invalidation (test files + config)


class TestCacheInvalidationTestFiles:
    def test_cache_invalidated_on_test_import_change(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        ai_dev_perf.get_index(config, use_cache=True)
        index1, _ = ai_dev_perf.get_index(config, use_cache=True)
        assert "app/service.py" in index1.test_map["tests/test_service.py"]
        assert "app/leaf.py" not in index1.test_map["tests/test_service.py"]
        # A changed test import changes the test map; the cache must invalidate.
        _write(
            fake_repo,
            "tests/test_service.py",
            "from psyche_os.app.leaf import helper\n\ndef test_helper() -> None:\n    assert helper(1) == 2\n",
        )
        index2, hit = ai_dev_perf.get_index(config, use_cache=True)
        assert hit is False
        assert "app/leaf.py" in index2.test_map["tests/test_service.py"]

    def test_cache_invalidated_on_test_root_config_change(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        ai_dev_perf.get_index(config, use_cache=True)
        config2 = {**config, "test_root": "other_tests"}
        _write(
            fake_repo,
            "other_tests/test_leaf.py",
            "from psyche_os.app.leaf import helper\n\ndef test_helper() -> None:\n    assert helper(1) == 2\n",
        )
        index, hit = ai_dev_perf.get_index(config2, use_cache=True)
        assert hit is False
        assert "other_tests/test_leaf.py" in index.test_map
        assert "app/leaf.py" in index.test_map["other_tests/test_leaf.py"]

    def test_index_shaping_config_keys_invalidate(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        ai_dev_perf.get_index(config, use_cache=True)
        # src_roots is an index-shaping key: changing it must miss.
        config2 = {**config, "src_roots": ["src/psyche_os"]}
        _write(fake_repo, "src/psyche_os/extra.py", "def extra() -> None:\n    pass\n")
        _, hit = ai_dev_perf.get_index(config2, use_cache=True)
        assert hit is False


# --------------------------------------------------------------------------- A4 content-fingerprint cache invalidation


class TestContentFingerprintCache:
    def test_same_size_restored_mtime_edit_invalidates_cache(self, fake_repo: Path) -> None:
        import os

        config = make_config(fake_repo)
        _, hit1 = ai_dev_perf.get_index(config, use_cache=True)
        assert hit1 is False
        _, hit2 = ai_dev_perf.get_index(config, use_cache=True)
        assert hit2 is True  # unchanged content hits

        path = fake_repo / "src/psyche_os/domain/ids.py"
        original = path.read_text(encoding="utf-8")
        # Same byte-length content edit: rename the class, keep every other byte.
        edited = original.replace("class OpaqueId:", "class OpaqueIo:")
        assert len(edited) == len(original) and edited != original
        st = path.stat()
        path.write_text(edited, encoding="utf-8")
        os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns))  # restore the prior mtime

        index, hit = ai_dev_perf.get_index(config, use_cache=True)
        assert hit is False  # content changed -> cache MISS / rebuild
        symbols = {s.name for s in index.modules["domain/ids.py"].symbols}
        assert "OpaqueIo" in symbols and "OpaqueId" not in symbols  # updated mapping

        # Unchanged content still benefits from the cache.
        _, hit_again = ai_dev_perf.get_index(config, use_cache=True)
        assert hit_again is True

    def test_digest_is_deterministic_and_content_dependent(self, fake_repo: Path) -> None:
        d1 = ai_dev_perf._current_digest(make_config(fake_repo))
        d2 = ai_dev_perf._current_digest(make_config(fake_repo))
        assert d1["files"] == d2["files"]
        # A same-size edit changes the digest even when mtime is restored.
        path = fake_repo / "src/psyche_os/domain/ids.py"
        original = path.read_text(encoding="utf-8")
        path.write_text(original.replace("class OpaqueId:", "class OpaqueIo:"), encoding="utf-8")
        d3 = ai_dev_perf._current_digest(make_config(fake_repo))
        assert d1["files"] != d3["files"]


# --------------------------------------------------------------------------- F3 verification fail-closed


class TestVerifyFailClosed:
    def test_pytest_nonzero_rc_is_fail(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        fake = subprocess.CompletedProcess(
            ["uv", "run", "pytest", "x", "-q"], returncode=1, stdout="1 failed, 9 passed", stderr=""
        )
        monkeypatch.setattr(ai_dev_perf, "run_cmd", lambda *a, **k: fake)
        result = ai_dev_perf.run_pytest(index, ["tests/test_ids.py"], raw_dir=tmp_path, source_changed=True)
        assert result["rc"] == 1
        assert result["status"] == "FAIL"
        assert result["status"] != "PASS"

    def test_pytest_nonzero_rc_with_zero_parsed_failures_is_unknown(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
        """Collection/config/infra errors must never be inferred as PASS from counters."""
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        fake = subprocess.CompletedProcess(
            ["uv", "run", "pytest", "x", "-q"], returncode=2, stdout="error: pytest: error: unrecognized arguments", stderr=""
        )
        monkeypatch.setattr(ai_dev_perf, "run_cmd", lambda *a, **k: fake)
        result = ai_dev_perf.run_pytest(index, ["tests/test_ids.py"], raw_dir=tmp_path, source_changed=True)
        assert result["rc"] == 2
        assert result["status"] == "UNKNOWN"
        assert result["status"] != "PASS"

    def test_source_change_with_no_mapped_tests_is_full_required(self, fake_repo: Path, tmp_path: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        surface = ai_dev_perf.affected_surface(index, ["src/psyche_os/app/leaf.py"])
        assert surface["affected_tests"] == []
        plan = ai_dev_perf.verify_plan(index, [], full=False, source_changed=bool(surface["changed"]))
        assert plan["state"] == "FULL_REQUIRED"
        result = ai_dev_perf.run_pytest(index, [], raw_dir=tmp_path, source_changed=True)
        assert result["status"] == "FULL_REQUIRED"
        assert result["rc"] is None
        assert result["status"] != "PASS"

    def test_no_code_change_is_not_full_required(self, fake_repo: Path) -> None:
        config = make_config(fake_repo)
        index = ai_dev_perf.build_index(config)
        plan = ai_dev_perf.verify_plan(index, [], full=False, source_changed=False)
        assert plan["state"] == "NO_CODE_CHANGE"


# --------------------------------------------------------------------------- F5 prompt accounting


class TestPromptAccounting:
    def test_prompt_does_not_double_count_context(self, fake_repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
        config = make_config(fake_repo)
        ai_dev_perf.build_index(config)
        monkeypatch.setattr(ai_dev_perf, "check_tools", lambda need: {"rg": "rg", "ast-grep": "sg"})
        monkeypatch.setattr(ai_dev_perf, "_lexical_items", lambda *a, **k: [])
        monkeypatch.setattr(ai_dev_perf, "RUNS_DIR", tmp_path / "runs")
        args = argparse_namespace(
            task="Fix OpaqueId",
            paths=["src/psyche_os/domain/ids.py"],
            symbols=[],
            terms=["OpaqueId"],
            target=10000,
            out=str(tmp_path / "packet.md"),
            json=True,
            no_cache=False,
        )
        rc = ai_dev_perf.cmd_prompt(args, config)
        assert rc == 0
        parsed = json.loads(capsys.readouterr().out)
        # The total is the estimate of the final rendered prompt ONLY.
        markdown = (tmp_path / "packet.md").read_text(encoding="utf-8")
        assert parsed["prompt_total_estimate"] == ai_dev_perf.estimate_tokens(markdown)
        # Context is embedded in the prompt, never added on top.
        assert parsed["reconciles"] is True
        assert parsed["prompt_total_estimate"] == parsed["context_embedded_estimate"] + parsed["instructions_overhead_estimate"]
        assert parsed["context_embedded_estimate"] == 0 or parsed["prompt_total_estimate"] >= parsed["context_embedded_estimate"]


# --------------------------------------------------------------------------- frozen benchmark tasks + V1/V2 accounting


class TestBenchmarkFrozen:
    def test_frozen_tasks_file_is_valid(self, fake_repo: Path) -> None:
        tasks = ai_dev_perf.load_bench_tasks()
        assert len(tasks) >= 3
        for t in tasks:
            assert t["class"] in ("localized", "cross-module", "verification-heavy", "docs")
            assert t["base_sha"] and t["result_sha"]
            assert all(isinstance(x, list) for x in (t["terms"], t["changed_sources"], t["changed_tests"]))
            assert isinstance(t["description"], str) and t["description"]

    def test_frozen_ground_truth_matches_git_diff(self, fake_repo: Path) -> None:
        """The freeze proof: changed_sources/tests in tasks.yaml must equal git diff."""
        tasks = ai_dev_perf.load_bench_tasks()
        for t in tasks:
            proc = ai_dev_perf.run_cmd(["git", "diff", "--name-only", t["base_sha"], t["result_sha"]], cwd=REPO_ROOT)
            changed = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
            srcs = sorted(p for p in changed if p.startswith("src/psyche_os/"))
            tests = sorted(p for p in changed if p.startswith("tests/"))
            assert srcs == sorted(t["changed_sources"]), t["task_id"]
            assert tests == sorted(t["changed_tests"]), t["task_id"]


class TestV1V2Accounting:
    def test_score_recall_precision(self) -> None:
        recall, precision, hits = ai_dev_perf._score_recall({"a.py", "b.py"}, ["a.py", "c.py"])
        assert (recall, precision, hits) == (0.5, 0.5, 1)
        # No ground truth -> not computable, not zero.
        assert ai_dev_perf._score_recall(set(), []) == (None, None, 0)

    def test_merge_line_ranges_is_deterministic(self) -> None:
        ranges = ai_dev_perf._merge_line_ranges([10, 11, 40, 41], 4)
        assert ranges == [[10, 11], [40, 41]]
        assert ai_dev_perf._merge_line_ranges([1, 5], 4) == [[1, 5]]
        assert ai_dev_perf._merge_line_ranges([5, 1], 4) == [[1, 5]]

    def test_medians_exclude_docs_tasks(self) -> None:
        rows = [
            {"docs_only": False, "v1": {"context_tokens_estimate": 100, "docs_only": False}, "v2": {"context_tokens_estimate": 80, "docs_only": False}},
            {"docs_only": False, "v1": {"context_tokens_estimate": 200, "docs_only": False}, "v2": {"context_tokens_estimate": 120, "docs_only": False}},
            {"docs_only": True, "v1": {"context_tokens_estimate": 0, "docs_only": True}, "v2": {"context_tokens_estimate": 0, "docs_only": True}},
        ]
        med = ai_dev_perf._compute_medians(rows)
        assert med["code_tasks"] == 2
        assert med["docs_tasks"] == 1
        assert med["v1_context_tokens_estimate"] == 150
        assert med["v2_context_tokens_estimate"] == 100


# --------------------------------------------------------------------------- Wave 1 Component D: context-model guard


class TestContextModelGuard:
    def test_module_surface_is_experimental_and_rejected(self) -> None:
        """The ~8x-larger V2 module-surface context model must never silently
        become the default on the context/prompt path."""
        with pytest.raises(ai_dev_perf.PerfError):
            ai_dev_perf._check_context_model({"context_model": "module-surface"})

    def test_exact_range_is_the_only_default(self) -> None:
        ai_dev_perf._check_context_model({"context_model": "exact-range"})
        ai_dev_perf._check_context_model({})  # baked-in default
