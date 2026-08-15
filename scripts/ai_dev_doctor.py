#!/usr/bin/env python3
"""AI Dev OS doctor — validate the control plane and the development environment.

Exit non-zero ONLY when an actual CORE requirement is broken. Conditional / optional
capabilities surface as [WARN] / [MANUAL] / [DEFER] and do not fail the run.

Run: python scripts/ai_dev_doctor.py   (or: uv run python scripts/ai_dev_doctor.py)
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AI_DEV = os.path.join(REPO, ".ai-dev")

CORE_TOOLS = ["git", "python", "rg", "ast-grep"]
PROJECT_TOOLS = ["uv", "node", "cargo", "claude"]
CONDITIONAL_TOOLS = ["gitleaks", "osv-scanner", "semgrep"]

CORE_FILES = [
    "policy/risk.yaml",
    "policy/protected-paths.yaml",
    "policy/approvals.yaml",
    "policy/capabilities.yaml",
    "profiles/balanced.yaml",
    "verification/commands.yaml",
    "verification/gates.yaml",
    "capabilities/registry.yaml",
    "telemetry/schema.json",
    "hooks/dispatcher.py",
]


def find_tool(name: str):
    p = shutil.which(name)
    if p:
        return p
    if name == "ast-grep":
        p = shutil.which("sg")
        if p:
            return p
    # Fall back to winget user-package dir (PATH refresh may not have propagated).
    hits = glob.glob(f"C:/Users/*/AppData/Local/Microsoft/WinGet/Packages/*/{name}.exe")
    return hits[0] if hits else None


def emit(status: str, name: str, detail: str = "") -> None:
    suffix = f" — {detail}" if detail else ""
    print(f"[{status}] {name}{suffix}")


def check_tool(name: str, core: bool) -> bool:
    p = find_tool(name)
    if p:
        emit("OK", name, p)
        return True
    if core:
        emit("FAIL", name, "CORE requirement missing")
    else:
        emit("WARN", name, "not found")
    return False


def yaml_ok(path: str) -> bool:
    try:
        import yaml  # type: ignore

        yaml.safe_load(open(path, encoding="utf-8"))
        return True
    except Exception:
        return False


def main() -> int:
    core_fail = 0

    print("== AI Dev OS doctor ==")
    print(f"repo: {REPO}")

    # 1. Control plane presence
    if not os.path.isdir(AI_DEV):
        emit("FAIL", ".ai-dev/ control plane", "missing — run AI Dev OS bootstrap")
        return 1
    emit("OK", ".ai-dev/ control plane")

    missing = [f for f in CORE_FILES if not os.path.isfile(os.path.join(AI_DEV, f))]
    if missing:
        for f in missing:
            emit("FAIL", f"missing control-plane file: {f}")
        core_fail += len(missing)
    else:
        emit("OK", "control-plane files", f"{len(CORE_FILES)} core files present")

    # 2. YAML/JSON validity
    bad = 0
    for f in glob.glob(os.path.join(AI_DEV, "**", "*.yaml"), recursive=True):
        if not yaml_ok(f):
            emit("FAIL", f"YAML parse: {os.path.relpath(f, REPO)}")
            bad += 1
    for f in glob.glob(os.path.join(AI_DEV, "**", "*.json"), recursive=True):
        if "data" in f.split(os.sep):
            continue
        try:
            json.load(open(f, encoding="utf-8"))
        except Exception:
            emit("FAIL", f"JSON parse: {os.path.relpath(f, REPO)}")
            bad += 1
    if bad == 0:
        emit("OK", "control-plane YAML/JSON valid")
    else:
        core_fail += bad

    # 3. Git
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True).stdout.strip()
        branch = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True).stdout.strip()
        if os.path.abspath(top) == os.path.abspath(REPO):
            emit("OK", "git", f"branch={branch}")
        else:
            emit("WARN", "git", f"repo top mismatch: {top}")
    except Exception:
        emit("FAIL", "git", "not available")
        core_fail += 1

    # 4. Core tools
    for t in CORE_TOOLS:
        if not check_tool(t, core=True):
            core_fail += 1

    # 5. Project toolchains
    for t in PROJECT_TOOLS:
        check_tool(t, core=False)

    # 6. Provider presence (names only, never values)
    env = os.environ
    provider = []
    if "DEEPSEEK_API_KEY" in env:
        provider.append("deepseek-api-key")
    if "ANTHROPIC_BASE_URL" in env:
        provider.append("anthropic-base-url")
    if os.path.isdir(os.path.expanduser("~/.cc-switch")):
        provider.append("cc-switch")
    if provider:
        emit("OK", "provider config presence", ", ".join(provider))
    else:
        emit("WARN", "provider config presence", "no provider env vars / cc-switch detected")

    # 7. Security tools (conditional)
    for t in CONDITIONAL_TOOLS:
        check_tool(t, core=False)

    # 8. Telemetry writable
    tdir = os.path.join(AI_DEV, "telemetry")
    if os.path.isdir(tdir):
        try:
            d = os.path.join(tdir, "data")
            os.makedirs(d, exist_ok=True)
            emit("OK", "telemetry", "writable")
        except Exception:
            emit("FAIL", "telemetry", "not writable")
            core_fail += 1
    else:
        emit("FAIL", "telemetry", "missing telemetry dir")
        core_fail += 1

    # 9. Hook integration
    dispatcher = os.path.join(AI_DEV, "hooks", "dispatcher.py")
    settings = os.path.join(REPO, ".claude", "settings.json")
    if os.path.isfile(dispatcher):
        emit("OK", "hook dispatcher", "present")
    else:
        emit("FAIL", "hook dispatcher", "missing")
        core_fail += 1
    if os.path.isfile(settings):
        try:
            cfg = json.load(open(settings, encoding="utf-8"))
            hooks = cfg.get("hooks", {})
            emit("OK", "hook integration", f"{len(hooks)} event(s) configured")
        except Exception:
            emit("WARN", "hook integration", "settings.json present but invalid JSON")
    else:
        emit("WARN", "hook integration", "no .claude/settings.json (dispatcher not active)")

    # 10. Capability registry
    reg = os.path.join(AI_DEV, "capabilities", "registry.yaml")
    if os.path.isfile(reg) and yaml_ok(reg):
        emit("OK", "capability registry", "valid")
    else:
        emit("FAIL", "capability registry", "missing or invalid")
        core_fail += 1

    # 11. Verification registry
    for f in ("commands.yaml", "gates.yaml"):
        p = os.path.join(AI_DEV, "verification", f)
        if os.path.isfile(p) and yaml_ok(p):
            emit("OK", f"verification/{f}")
        else:
            emit("FAIL", f"verification/{f}", "missing or invalid")
            core_fail += 1

    # 12. Manual blockers
    ma = os.path.join(REPO, "docs", "AI_DEV_OS_MANUAL_ACTIONS.md")
    if os.path.isfile(ma):
        emit("MANUAL", "manual actions", "see docs/AI_DEV_OS_MANUAL_ACTIONS.md")
    else:
        emit("OK", "manual actions", "none documented")

    # Deferred (by design)
    emit("DEFER", "LAB capabilities (Pathfinder, SymLens, projectmem, Reasonix, …)")

    print("")
    if core_fail:
        print(f"RESULT: FAIL ({core_fail} CORE issue(s))")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
