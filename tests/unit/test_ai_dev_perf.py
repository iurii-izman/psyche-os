"""Focused unit tests for the AI Dev OS v2 performance canary tooling.

The tests build a small synthetic repository in a temp dir (never real app data) and
exercise the pure index/impact/context/verify-selection logic in `scripts/ai_dev_perf.py`.
Subprocess-dependent paths (lexical/structural search) are stubbed where a test only
targets the deterministic index logic.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_perf  # noqa: E402


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
