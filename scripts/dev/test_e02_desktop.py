"""Exercise the packaged E02 Windows app through the native UIA boundary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import time
from typing import Any

import psutil
from pywinauto import Desktop


WINDOW_TITLE = "PSYCHE OS — Local vault controls"
SECRET_CANARY = "E02-SECRET-CANARY-8ca4c3"
MARKUP_CANARY = '<img src=x onerror="alert(1)"><script>bad()</script>'


def wait_for_text(window: Any, needle: str, timeout: float = 12.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        text = "\n".join(control.window_text() for control in window.descendants())
        if needle in text:
            return
        time.sleep(0.2)
    raise AssertionError(f"Timed out waiting for UI state: {needle}")


def edit(window: Any, title: str, value: str) -> None:
    control = window.child_window(title=title, control_type="Edit").wait("ready", 8)
    control.set_edit_text(value)


def click(window: Any, title: str) -> None:
    window.child_window(title=title, control_type="Button").wait("enabled", 8).invoke()


def process_evidence(root_pid: int) -> dict[str, Any]:
    root = psutil.Process(root_pid)
    descendants = root.children(recursive=True)
    names = sorted({process.name().lower() for process in descendants if process.is_running()})
    if not any("msedgewebview2" in name for name in names):
        raise AssertionError(f"WebView2 child process was not observed: {names}")
    if not any("psyche-os-sidecar" in name for name in names):
        raise AssertionError(f"Packaged fixed sidecar process was not observed: {names}")

    owned_pids = {root_pid, *(process.pid for process in descendants)}
    listeners: list[dict[str, Any]] = []
    application_connections: list[dict[str, Any]] = []
    webview_background_connections: list[dict[str, Any]] = []
    for connection in psutil.net_connections(kind="inet"):
        if connection.pid in owned_pids:
            try:
                process_name = psutil.Process(connection.pid).name().lower()
            except psutil.Error:
                process_name = "unavailable"
            detail = {
                "pid": connection.pid,
                "process_name": process_name,
                "local_address": str(connection.laddr),
                "remote_address": str(connection.raddr),
                "status": connection.status,
            }
            if connection.status == psutil.CONN_LISTEN:
                listeners.append(detail)
            elif "msedgewebview2" in process_name:
                webview_background_connections.append(detail)
            else:
                application_connections.append(detail)
    if listeners:
        raise AssertionError(f"Desktop process tree opened a listener: {listeners}")
    if application_connections:
        raise AssertionError(
            "Desktop or fixed sidecar used an INET connection: "
            f"{application_connections}"
        )
    return {
        "process_names": names,
        "listeners": listeners,
        "application_connections": application_connections,
        "webview_background_connections": webview_background_connections,
        "offline_workflows_completed": True,
    }


def terminate_tree(process: subprocess.Popen[bytes]) -> None:
    try:
        root = psutil.Process(process.pid)
        children = root.children(recursive=True)
        for child in children:
            child.terminate()
        root.terminate()
        _, alive = psutil.wait_procs([*children, root], timeout=5)
        for survivor in alive:
            survivor.kill()
    except psutil.Error:
        pass


def run(executable: Path) -> dict[str, Any]:
    if not executable.is_file():
        raise SystemExit(f"Desktop executable does not exist: {executable}")
    process = subprocess.Popen(
        [str(executable)],
        cwd=executable.parent,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        window = Desktop(backend="uia").window(title=WINDOW_TITLE)
        window.wait("visible", timeout=20)

        edit(window, "Local session secret", SECRET_CANARY)
        click(window, "Unlock locally")
        wait_for_text(window, "Your local control center")
        visible_text = "\n".join(control.window_text() for control in window.descendants())
        if SECRET_CANARY in visible_text:
            raise AssertionError("Unlock secret leaked into the native accessibility surface")
        for required in ("SYNTHETIC_ONLY", "CLOSED", "OFFLINE_NO_LISTENER", "DISABLED"):
            if required not in visible_text:
                raise AssertionError(f"Missing privacy/runtime status: {required}")

        edit(window, "Corrected synthetic observation", MARKUP_CANARY)
        edit(window, "Reason for correction", "Synthetic UIA safety check")
        click(window, "Preserve history and correct")
        wait_for_text(window, "Correction applied to this synthetic session; earlier session version preserved.")
        if len(Desktop(backend="uia").windows(title=WINDOW_TITLE)) != 1:
            raise AssertionError("Untrusted markup changed the native window surface")

        click(window, "Preview deletion scope")
        wait_for_text(window, "Deletion dry-run only; nothing deleted.")
        click(window, "Confirm deletion")
        wait_for_text(window, "Synthetic-session deletion applied with stated limitations; no canonical record was changed.")

        click(window, "Verify backup")
        wait_for_text(window, "Backup verified without content disclosure.")
        click(window, "Validate isolated recovery")
        wait_for_text(window, "Candidate validated; active vault unchanged.")
        click(window, "Activate validated candidate")
        wait_for_text(window, "Validated candidate activated separately.")

        edit(window, "Purpose", "portability")
        edit(window, "Audience", "owner")
        edit(window, "Scope", "synthetic minimum")
        click(window, "Preview export")
        wait_for_text(window, "Export preview; nothing written yet.")
        click(window, "Confirm synthetic export")
        wait_for_text(window, "Export completed. This is not a backup.")

        evidence = process_evidence(process.pid)
        evidence.update(
            {
                "native_window": True,
                "uia_workflows": [
                    "unlock",
                    "correction",
                    "deletion",
                    "backup_verify",
                    "recovery_validate_activate",
                    "export_preview_execute",
                ],
                "secret_surface_clean": True,
                "malicious_markup_inert": True,
            }
        )
        return evidence
    finally:
        terminate_tree(process)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", required=True, type=Path)
    args = parser.parse_args()
    evidence = run(args.executable.resolve())
    print(json.dumps(evidence, indent=2, sort_keys=True))
    print("E02_NATIVE_DESKTOP_UIA: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
