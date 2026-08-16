"""Focused unit tests for the Wave 1 JIT Capability Launcher.

Covers: known/unknown capability handling, DISABLED/QUARANTINED refusal, LAB
explicit-only invocation, and subprocess exit-code propagation. Real-tool smoke
tests (difftastic doctor/run) are guarded by skipif so the suite stays hermetic.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ai_dev_capability  # noqa: E402


def _registry(**overrides) -> dict:
    base = {
        "fake-tool": {
            "state": "conditional",
            "type": "probe",
            "version": "9.9.9",
            "command": 'python -c "import sys; print(\'fake ok\'); sys.exit(0)"',
            "installed": True,
        },
        "exit-tool": {
            "state": "conditional",
            "type": "probe",
            "command": 'python -c "import sys; sys.exit(3)"',
            "installed": True,
        },
        "turned-off": {
            "state": "disabled",
            "type": "probe",
            "command": 'python -c "print(\'should not run\')"',
            "installed": True,
        },
        "quarantined-tool": {
            "state": "quarantined",
            "type": "probe",
            "command": 'python -c "print(\'should not run\')"',
            "installed": True,
        },
        "lab-tool": {
            "state": "lab",
            "type": "probe",
            "command": 'python -c "print(\'lab ran\')"',
            "installed": True,
        },
        "uninstalled-lab": {
            "state": "lab",
            "type": "probe",
            "installed": False,
        },
    }
    base.update(overrides)
    return base


@pytest.fixture
def fake_registry(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict:
    reg = _registry()
    monkeypatch.setattr(ai_dev_capability, "load_registry", lambda *a, **k: reg)
    monkeypatch.setattr(ai_dev_capability, "RUNS_DIR", tmp_path / "runs")
    return reg


class TestLauncher:
    def test_known_capability_run(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("fake-tool"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "fake ok" in out
        assert "exit_code: 0" in out

    def test_unknown_capability_run(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("no-such-tool"))
        assert rc == 1
        assert "unknown capability" in capsys.readouterr().err

    def test_unknown_capability_info(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_info(_args("no-such-tool"))
        assert rc == 1
        assert "unknown capability" in capsys.readouterr().err

    def test_disabled_refusal(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("turned-off"))
        assert rc == 2
        assert "refused" in capsys.readouterr().err

    def test_quarantined_refusal(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("quarantined-tool"))
        assert rc == 2
        assert "QUARANTINED" in capsys.readouterr().err

    def test_lab_runs_only_on_explicit_invocation(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("lab-tool"))
        captured = capsys.readouterr()
        assert rc == 0
        assert "lab ran" in captured.out
        assert "LAB" in captured.err

    def test_uninstalled_lab_is_clearly_reported(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("uninstalled-lab"))
        assert rc == 1
        assert "not installed" in capsys.readouterr().err

    def test_subprocess_exit_code_propagation(self, fake_registry) -> None:
        rc = ai_dev_capability.cmd_run(_args("exit-tool"))
        assert rc == 3

    def test_list_output(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_list(_args(None, as_json=True))
        assert rc == 0
        out = capsys.readouterr().out
        assert "fake-tool" in out
        assert "turned-off" in out

    def test_info_record(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_info(_args("fake-tool"))
        assert rc == 0
        assert "fake-tool" in capsys.readouterr().out

    def test_doctor_ok(self, fake_registry, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_doctor(_args("fake-tool"))
        out = capsys.readouterr().out
        assert rc == 0
        assert "[OK]" in out


# Real-tool smoke tests (guarded — installed user-local via winget).
@pytest.mark.skipif(
    ai_dev_capability.find_exe("difft") is None,
    reason="difftastic binary not found (winget user-local)",
)
class TestDifftasticSmoke:
    def test_doctor_reports_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_doctor(_args("difftastic"))
        assert rc == 0
        assert "Difftastic" in capsys.readouterr().out

    def test_run_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        rc = ai_dev_capability.cmd_run(_args("difftastic", extra=["--version"]))
        assert rc == 0
        assert "Difftastic" in capsys.readouterr().out


def _args(name, *, extra=None, as_json=False):
    a = argparse.Namespace()
    a.name = name
    a.extra = list(extra or [])
    a.timeout = 120
    a.preview = 2000
    a.json = as_json
    return a
