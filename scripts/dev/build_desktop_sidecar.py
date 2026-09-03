"""Build and probe the fixed E02/E03 Python/SQLCipher sidecar executable."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / "desktop"
OUTPUT = DESKTOP / "src-tauri" / "binaries"
BUILD = DESKTOP / "build" / "sidecar"
NAME = "psyche-os-sidecar-x86_64-pc-windows-msvc"
PERSONAL_NAME = "psyche-os-personal-sidecar-x86_64-pc-windows-msvc"
PERSONAL_FORBIDDEN_MODULES = (
    "psyche_os.application.action_planning",
    "psyche_os.backup_export",
    "psyche_os.interfaces.cli",
    "psyche_os.storage.migrations",
    "psyche_os.domain.assessments",
    "psyche_os.storage.v3a3_action_schema",
)
OFFLINE_PROFILE = "local_personal_evidence_reflection_windows_v1"
BOUNDED_OPENAI_PROFILE = "local_personal_bounded_openai_reflection_windows_v1"
INTERVIEW_PROFILE = "local_personal_ai_interview_openai_windows_v1"
BOUNDED_OPENAI_ADAPTERS = {
    "psyche_os.adapters",
    "psyche_os.adapters.adapters",
    "psyche_os.adapters.e07_provider",
}
INTERVIEW_HIDDEN_IMPORTS = (
    "psyche_os.adapters.e07_provider",
    "psyche_os.personal_mode.ai_interview",
)
SYNTHETIC_FIXTURE = "psyche_os/fixtures/e03_orchid_station_v1.json"


def _build(name: str, entrypoint: Path, *, synthetic: bool, hidden_imports: tuple[str, ...] = ()) -> Path:
    executable = OUTPUT / f"{name}.exe"
    if executable.exists():
        executable.unlink()
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--console",
        "--name",
        name,
        "--distpath",
        str(OUTPUT),
        "--workpath",
        str(BUILD / name / "work"),
        "--specpath",
        str(BUILD / name),
        "--paths",
        str(ROOT / "src"),
        "--hidden-import",
        "sqlcipher3",
        str(entrypoint),
    ]
    if synthetic:
        command[-1:-1] = [
            "--hidden-import",
            "psyche_os.storage.migrations",
            "--add-data",
            f"{ROOT / 'src' / 'psyche_os' / 'fixtures' / 'e03_orchid_station_v1.json'}"
            f"{os.pathsep}psyche_os/fixtures",
        ]
    if hidden_imports:
        command[-1:-1] = [item for module in hidden_imports for item in ("--hidden-import", module)]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0 or not executable.is_file():
        raise RuntimeError(name)
    return executable


def _personal_profile() -> str:
    """Return the explicit package profile, defaulting fail-closed to Offline."""
    profile = os.environ.get("PSYCHE_OS_PERSONAL_PROFILE_ID", OFFLINE_PROFILE)
    if profile not in {OFFLINE_PROFILE, BOUNDED_OPENAI_PROFILE, INTERVIEW_PROFILE}:
        raise RuntimeError("unknown-personal-profile")
    return profile


def _verify_personal_inventory(executable: Path, profile: str) -> None:
    """Inspect the emitted module graph against the exact active profile."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller.utils.cliutils.archive_viewer",
            "-r",
            "-b",
            str(executable),
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    modules = {name.strip() for name in result.stdout.splitlines()}
    if result.returncode != 0 or any(
        name.strip() == forbidden or name.strip().startswith(f"{forbidden}.")
        for name in modules
        for forbidden in PERSONAL_FORBIDDEN_MODULES
    ):
        raise RuntimeError("personal-modulegraph")
    adapters = {name for name in modules if name == "psyche_os.adapters" or name.startswith("psyche_os.adapters.")}
    if profile == OFFLINE_PROFILE and adapters:
        raise RuntimeError("offline-personal-adapter-leakage")
    if profile in {BOUNDED_OPENAI_PROFILE, INTERVIEW_PROFILE} and not BOUNDED_OPENAI_ADAPTERS.issubset(adapters):
        raise RuntimeError("bounded-openai-adapter-inventory")
    actual = {path.name for path in OUTPUT.glob("psyche-os*sidecar*.exe")}
    expected = {f"{NAME}.exe", f"{PERSONAL_NAME}.exe"}
    if actual != expected:
        raise RuntimeError("sidecar-executable-inventory")


def _verify_synthetic_resource(executable: Path) -> None:
    """Fail if the frozen Synthetic sidecar lacks its owned E03 fixture."""
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller.utils.cliutils.archive_viewer",
            "-r",
            "-b",
            str(executable),
        ],
        cwd=ROOT,
        capture_output=True,
        check=False,
        text=True,
    )
    normalized = result.stdout.replace("\\", "/")
    if result.returncode != 0 or SYNTHETIC_FIXTURE not in normalized:
        raise RuntimeError("synthetic-fixture-resource")


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    try:
        executable = _build(
            NAME,
            ROOT / "src" / "psyche_os" / "interfaces" / "desktop_sidecar.py",
            synthetic=True,
        )
        profile = _personal_profile()
        personal = _build(
            PERSONAL_NAME,
            ROOT / "src" / "psyche_os" / "interfaces" / "personal_desktop_sidecar.py",
            synthetic=False,
            hidden_imports=(
                tuple(sorted(BOUNDED_OPENAI_ADAPTERS))
                if profile == BOUNDED_OPENAI_PROFILE
                else INTERVIEW_HIDDEN_IMPORTS
                if profile == INTERVIEW_PROFILE
                else ()
            ),
        )
        _verify_personal_inventory(personal, profile)
        _verify_synthetic_resource(executable)
    except RuntimeError as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1

    request = {
        "version": "1.0",
        "command": "status.get",
        "correlation_id": "packaging-probe",
        "session_token": None,
        "payload": {},
    }
    body = json.dumps(request).encode("utf-8")
    probe = subprocess.run(
        [str(executable)],
        input=struct.pack(">I", len(body)) + body,
        capture_output=True,
        check=False,
        timeout=30,
    )
    if probe.returncode != 0 or len(probe.stdout) < 4:
        return 2
    length = struct.unpack(">I", probe.stdout[:4])[0]
    response = json.loads(probe.stdout[4 : 4 + length])
    if (
        response.get("status") != "ok"
        or response.get("data", {}).get("real_data_gate") != "CLOSED"
        or response.get("data", {}).get("inbound_listener") != "NONE"
    ):
        return 3
    # PyInstaller specs are generated inputs, not durable source files.
    shutil.rmtree(BUILD, ignore_errors=True)
    print(
        f"PASS: profile-specific Python/SQLCipher sidecars built and synthetic probe passed: {executable}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
