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


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    BUILD.mkdir(parents=True, exist_ok=True)
    executable = OUTPUT / f"{NAME}.exe"
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
        NAME,
        "--distpath",
        str(OUTPUT),
        "--workpath",
        str(BUILD / "work"),
        "--specpath",
        str(BUILD),
        "--paths",
        str(ROOT / "src"),
        "--hidden-import",
        "sqlcipher3",
        "--add-data",
        f"{ROOT / 'src' / 'psyche_os' / 'fixtures' / 'e03_orchid_station_v1.json'}{os.pathsep}psyche_os/fixtures",
        str(ROOT / "src" / "psyche_os" / "interfaces" / "desktop_sidecar.py"),
    ]
    completed = subprocess.run(command, cwd=ROOT, check=False)
    if completed.returncode != 0 or not executable.is_file():
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
        or response.get("data", {}).get("network") != "OFFLINE_NO_LISTENER"
    ):
        return 3
    # PyInstaller spec is a generated build input, not a durable source file.
    spec = BUILD / f"{NAME}.spec"
    if spec.exists():
        spec.unlink()
    shutil.rmtree(BUILD / "work", ignore_errors=True)
    print(f"PASS: fixed Python/SQLCipher sidecar built and probed: {executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
