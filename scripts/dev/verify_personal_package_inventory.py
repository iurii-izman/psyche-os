"""Fail closed on the emitted Personal product inventory (P1 package proof)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
OFFLINE_PROFILE = "local_personal_evidence_reflection_windows_v1"
BOUNDED_OPENAI_PROFILE = "local_personal_bounded_openai_reflection_windows_v1"
INTERVIEW_PROFILE = "local_personal_ai_interview_openai_windows_v1"
FORBIDDEN_RENDERER = ("desktop_archive_", "desktop_action_", "archive.operate")
FORBIDDEN_MODULES = (
    "psyche_os.application.action_planning",
    "psyche_os.backup_export",
    "psyche_os.interfaces.cli",
    "psyche_os.storage.migrations",
    "psyche_os.domain.assessments",
    "psyche_os.storage.v3a3_action_schema",
)
OPENAI_PROFILES = {BOUNDED_OPENAI_PROFILE, INTERVIEW_PROFILE}


def fail(message: str) -> None:
    raise RuntimeError(message)


def _permission_set(path: Path) -> set[str]:
    value = json.loads(path.read_text(encoding="utf-8"))
    permissions = value.get("permissions")
    if not isinstance(permissions, list) or not all(isinstance(item, str) for item in permissions):
        fail(f"invalid capability permissions: {path.name}")
    return set(permissions)


def _manifest_permissions(path: Path) -> set[str]:
    command_table = path.read_text(encoding="utf-8")
    return {
        f"allow-{line.replace('_', '-')}"
        for line in command_table.split('"')
        if line.startswith("desktop_")
    }


def _profile_contract(profile: str) -> tuple[str, str, tuple[str, ...]]:
    if profile == OFFLINE_PROFILE:
        return (
            "tauri.personal.conf.json",
            "personal-local.json",
            ("personal_command_manifest.rs",),
        )
    return (
        "tauri.personal.openai.conf.json",
        "personal-openai.json",
        ("personal_command_manifest.rs", "personal_openai_command_manifest.rs"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", required=True, type=Path)
    parser.add_argument(
        "--profile",
        required=True,
        choices=(OFFLINE_PROFILE, BOUNDED_OPENAI_PROFILE, INTERVIEW_PROFILE),
    )
    arguments = parser.parse_args()
    installer = arguments.installer.resolve()
    if not installer.is_file():
        fail("emitted installer does not exist")

    renderer = ROOT / "desktop" / "dist-personal"
    assets = sorted((renderer / "assets").glob("*.js"))
    if not assets:
        fail("Personal emitted renderer assets are missing")
    asset_text = "\n".join(path.read_text(encoding="utf-8") for path in assets)
    if any(token in asset_text.lower() for token in FORBIDDEN_RENDERER):
        fail("Personal emitted renderer contains a forbidden product surface")

    config_name, capability_name, manifest_names = _profile_contract(arguments.profile)
    tauri_root = ROOT / "desktop" / "src-tauri"
    config_value = json.loads((tauri_root / config_name).read_text(encoding="utf-8"))
    external_bin = config_value.get("bundle", {}).get("externalBin")
    if external_bin != ["binaries/psyche-os-personal-sidecar"]:
        fail(f"{config_name} does not have the exact Personal sidecar inventory")
    expected_capability = capability_name.removesuffix(".json")
    active_capabilities = config_value.get("app", {}).get("security", {}).get("capabilities")
    if active_capabilities != [expected_capability]:
        fail(f"{config_name} does not select exactly {expected_capability}")

    manifest_paths = [tauri_root / "src" / name for name in manifest_names]
    command_tables = [path.read_text(encoding="utf-8") for path in manifest_paths]
    manifest_commands = set().union(*(_manifest_permissions(path) for path in manifest_paths))
    actual_permissions = _permission_set(tauri_root / "capabilities" / capability_name)
    if actual_permissions != manifest_commands:
        fail(f"{capability_name} does not match the complete profile command inventory")
    command_table = "\n".join(command_tables)
    if any(token in command_table for token in ("desktop_archive_", "desktop_action_")):
        fail("Personal command table contains a forbidden command")

    has_ai = "desktop_ai_" in command_table
    if arguments.profile == OFFLINE_PROFILE and (
        has_ai or "desktop_ai_" in asset_text or "personal-browser-preview" in asset_text
    ):
        fail("Offline Personal package contains provider or preview capability")

    provider_commands = (
        "desktop_ai_provider_status",
        "desktop_ai_provider_configure",
        "desktop_ai_provider_delete",
    )
    formulation_commands = (
        "desktop_ai_formulation_prepare",
        "desktop_ai_formulation_execute",
    )
    interview_commands = (
        "desktop_ai_interview_status",
        "desktop_ai_interview_policy",
        "desktop_ai_interview_external_policy",
        "desktop_ai_interview_source_policy",
        "desktop_ai_interview_start",
        "desktop_ai_interview_list",
        "desktop_ai_interview_grant_consent",
        "desktop_ai_interview_revoke_consent",
        "desktop_ai_interview_first_question",
        "desktop_ai_interview_submit",
        "desktop_ai_interview_retry",
        "desktop_ai_interview_control",
        "desktop_ai_interview_get",
        "desktop_ai_interview_disclosure",
        "desktop_ai_model_list",
        "desktop_ai_model_correct",
        "desktop_ai_change_list",
        "desktop_ai_change_control",
        "desktop_ai_change_observe",
        "desktop_ai_change_allow_observations",
        "desktop_ai_change_start_review",
    )
    if arguments.profile in OPENAI_PROFILES:
        if any(command not in command_table for command in provider_commands):
            fail("OpenAI provider command inventory is incomplete")
        provider = (ROOT / "src" / "psyche_os" / "adapters" / "e07_provider.py").read_text(
            encoding="utf-8"
        )
        required_provider_invariants = (
            'endpoint = "https://api.openai.com/v1/responses"',
            "request.ProxyHandler({})",
            "class _RejectRedirects",
            '"store": False',
            '"model": "gpt-5.6-luna"',
            '"reasoning": {"effort": "low"}',
        )
        if any(item not in provider for item in required_provider_invariants):
            fail("Bounded OpenAI provider invariant missing")
    if arguments.profile == BOUNDED_OPENAI_PROFILE and any(
        command not in command_table for command in formulation_commands
    ):
        fail("Bounded OpenAI formulation command inventory is incomplete")
    if arguments.profile == INTERVIEW_PROFILE and any(
        command not in command_table for command in interview_commands
    ):
        fail("AI Interview command inventory is incomplete")

    seven_zip = Path("C:/Program Files/7-Zip/7z.exe")
    if not seven_zip.is_file():
        discovered = shutil.which("7z")
        if discovered is None:
            fail("7-Zip is unavailable for installer inspection")
        seven_zip = Path(discovered)
    listed = subprocess.run(
        [str(seven_zip), "l", str(installer)],
        capture_output=True,
        text=True,
        check=False,
    )
    if listed.returncode != 0:
        fail("unable to inspect emitted installer")
    if (
        "psyche-os-personal-sidecar.exe" not in listed.stdout
        or "psyche-os-sidecar.exe" in listed.stdout
    ):
        fail("Personal installer sidecar inventory is not exact")

    sidecar = (
        tauri_root
        / "binaries"
        / "psyche-os-personal-sidecar-x86_64-pc-windows-msvc.exe"
    )
    if not sidecar.is_file():
        fail("Personal frozen sidecar is missing")
    graph = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller.utils.cliutils.archive_viewer",
            "-r",
            "-b",
            str(sidecar),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    names = {name.strip() for name in graph.stdout.splitlines()}
    if graph.returncode != 0 or any(
        name == forbidden or name.startswith(f"{forbidden}.")
        for name in names
        for forbidden in FORBIDDEN_MODULES
    ):
        fail("Personal frozen sidecar modulegraph contains a forbidden module")
    adapters = {
        name
        for name in names
        if name == "psyche_os.adapters" or name.startswith("psyche_os.adapters.")
    }
    allowed_adapters = {
        "psyche_os.adapters",
        "psyche_os.adapters.adapters",
        "psyche_os.adapters.e07_provider",
    }
    if arguments.profile == OFFLINE_PROFILE and adapters:
        fail("Offline Personal sidecar contains an adapter module")
    if arguments.profile in OPENAI_PROFILES and adapters != allowed_adapters:
        fail("OpenAI Personal sidecar adapter inventory is not exact")
    if (
        arguments.profile == INTERVIEW_PROFILE
        and "psyche_os.personal_mode.ai_interview" not in names
    ):
        fail("AI Interview frozen sidecar module is missing")

    print(
        f"PASS personal package ({arguments.profile}): config, renderer, command table, "
        "installer sidecars, and frozen modulegraph"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, json.JSONDecodeError) as error:
        print(f"FAIL {error}", file=sys.stderr)
        raise SystemExit(1) from error
