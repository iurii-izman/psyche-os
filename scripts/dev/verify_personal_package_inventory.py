"""Fail closed on the emitted Personal product inventory (P1 package proof)."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OFFLINE_PROFILE = "local_personal_evidence_reflection_windows_v1"
BOUNDED_OPENAI_PROFILE = "local_personal_bounded_openai_reflection_windows_v1"
FORBIDDEN_RENDERER = ("desktop_archive_", "desktop_action_", "archive.operate", "ai.")
FORBIDDEN_MODULES = (
    "psyche_os.application.action_planning", "psyche_os.backup_export",
    "psyche_os.interfaces.cli", "psyche_os.storage.migrations", "psyche_os.domain.assessments",
    "psyche_os.storage.v3a3_action_schema",
)


def fail(message: str) -> None:
    raise RuntimeError(message)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument("--profile", required=True, choices=(OFFLINE_PROFILE, BOUNDED_OPENAI_PROFILE))
    arguments = parser.parse_args()
    installer = arguments.installer.resolve()
    renderer = ROOT / "desktop" / "dist-personal"
    config = (ROOT / "desktop" / "src-tauri" / "tauri.personal.conf.json").read_text(encoding="utf-8")
    if '"binaries/psyche-os-personal-sidecar"' not in config or '"binaries/psyche-os-sidecar"' in config:
        fail("Personal Tauri config does not have the exact sidecar inventory")
    asset_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted((renderer / "assets").glob("*.js")))
    if any(token in asset_text.lower() for token in FORBIDDEN_RENDERER):
        fail("Personal emitted renderer contains a forbidden product surface")
    command_table = (ROOT / "desktop" / "src-tauri" / "src" / "personal_command_manifest.rs").read_text(encoding="utf-8")
    if any(token in command_table for token in ("desktop_archive_", "desktop_action_")):
        fail("Personal command table contains a forbidden command")
    has_ai = "desktop_ai_" in command_table
    if arguments.profile == OFFLINE_PROFILE and (has_ai or "openai" in asset_text.lower()):
        fail("Offline Personal package contains bounded OpenAI capability")
    if arguments.profile == BOUNDED_OPENAI_PROFILE:
        required_commands = (
            "desktop_ai_provider_status", "desktop_ai_provider_configure", "desktop_ai_provider_delete",
            "desktop_ai_formulation_prepare", "desktop_ai_formulation_execute",
        )
        if any(command not in command_table for command in required_commands):
            fail("Bounded OpenAI command inventory is incomplete")
        provider = (ROOT / "src" / "psyche_os" / "adapters" / "e07_provider.py").read_text(encoding="utf-8")
        required_provider_invariants = (
            'endpoint = "https://api.openai.com/v1/responses"', "request.ProxyHandler({})",
            "class _RejectRedirects", '"store": False', '"model": "gpt-5.6-luna"',
            '"reasoning": {"effort": "low"}',
        )
        if any(item not in provider for item in required_provider_invariants):
            fail("Bounded OpenAI provider invariant missing")
    seven_zip = Path("C:/Program Files/7-Zip/7z.exe")
    listed = subprocess.run([str(seven_zip), "l", str(installer)], capture_output=True, text=True, check=False)
    if listed.returncode != 0:
        fail("unable to inspect emitted installer")
    if "psyche-os-personal-sidecar.exe" not in listed.stdout or "psyche-os-sidecar.exe" in listed.stdout:
        fail("Personal installer sidecar inventory is not exact")
    sidecar = ROOT / "desktop" / "src-tauri" / "binaries" / "psyche-os-personal-sidecar-x86_64-pc-windows-msvc.exe"
    graph = subprocess.run([sys.executable, "-m", "PyInstaller.utils.cliutils.archive_viewer", "-r", "-b", str(sidecar)], cwd=ROOT, capture_output=True, text=True, check=False)
    names = {name.strip() for name in graph.stdout.splitlines()}
    if graph.returncode != 0 or any(name == forbidden or name.startswith(f"{forbidden}.") for name in names for forbidden in FORBIDDEN_MODULES):
        fail("Personal frozen sidecar modulegraph contains a forbidden module")
    adapters = {name for name in names if name == "psyche_os.adapters" or name.startswith("psyche_os.adapters.")}
    allowed_adapters = {
        "psyche_os.adapters", "psyche_os.adapters.adapters", "psyche_os.adapters.e07_provider",
    }
    if arguments.profile == OFFLINE_PROFILE and adapters:
        fail("Offline Personal sidecar contains an adapter module")
    if arguments.profile == BOUNDED_OPENAI_PROFILE and adapters != allowed_adapters:
        fail("Bounded OpenAI Personal sidecar adapter inventory is not exact")
    print(f"PASS personal package ({arguments.profile}): config, renderer, command table, installer sidecars, and frozen modulegraph")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error
