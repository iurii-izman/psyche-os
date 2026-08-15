# AI Dev OS v1 — Manual Actions

M-001 (live Claude Code hook verification) is now CLOSED. Two OPTIONAL actions
remain (M-002 model ids, M-003 WSL migration). No credentials are involved.
Acceptance status: VERIFIED (see `docs/AI_DEV_OS_IMPLEMENTATION_REPORT.md`).

## M-001 — Verify Claude Code starts cleanly with the hook dispatcher active

- **Priority:** BLOCKING (for VERIFIED acceptance)
- **Status:** CLOSED (2026-08-15) — verified in a fresh live session.
- **Evidence:** A fresh Claude Code session at acceptance commit `91fdad0` (with
  `.claude/settings.json` active) observed the `PreToolUse` hook firing
  automatically on real tool calls. Seven genuine telemetry events
  (`event_type: tool_call`, `run_id: 3df8e5cc-57e0-4af2-92e2-2100268a9e5b`) were
  appended to `.ai-dev/telemetry/data/events.jsonl`, each timestamp-correlated to
  the moment of a real Bash invocation (event 4 at `11:05:33.209064Z` matches a
  `date -u` output of `11:05:33Z` to the millisecond, and the file mtime tracks the
  hook write). No event was manually injected. Dispatcher re-run 10/10 PASS; doctor
  PASS (exit 0). A live edit to a protected path (`.ai-dev/state.yaml`) was blocked
  by the dispatcher (exit 2), confirming the guard denies real protected-path edits.
- **Result:** Hooks registered; normal tool use unaffected; dispatcher blocks
  protected-path edits and destructive commands; telemetry is genuine and redacted.
- **What remains blocked:** Nothing. Rollback if it misbehaves: create
  `.ai-dev/hooks/DISABLED` (fail-open kill switch) or delete `.claude/settings.json`.

## M-002 — Confirm DeepSeek model ids for the CHEAP/STRONG roles (optional)

- **Priority:** OPTIONAL
- **Why agent cannot do it:** Model names are version-sensitive (AI_DEV_OS_V1.md §1.1)
  and must be confirmed against the live provider before first heavy use.
- **Exact user action:** Verify the current DeepSeek Anthropic-compatible model ids
  and update `cheap`/`strong` in `.ai-dev/routing/routing.yaml` if they differ from
  `deepseek-v4-flash` / `deepseek-v4-pro`.
- **Expected result:** Routing roles map to real, current model ids.
- **How to verify:** A model call resolves without a routing error.
- **What remains blocked:** Nothing at the control-plane level.

## M-003 — Consider WSL2 Ubuntu as the canonical environment (optional)

- **Priority:** OPTIONAL
- **Why agent cannot do it:** Moving the repository between filesystems is a
  user-only, irreversible-host-adjacent action; the prompt forbids doing it automatically.
- **Exact user action:** Only if Windows-NTFS tooling becomes a bottleneck: move or
  clone the repo to a WSL2-native filesystem (e.g. `~/psyche-os`) with the standard
  `git clone`/`rsync` procedure, preserving `.git`.
- **Expected result:** Repo on ext4; Linux tooling operates at native speed.
- **How to verify:** `uname -a` shows Linux; `uv run pytest -q` passes.
- **What remains blocked:** Nothing — the entire AI Dev OS v1 works on Windows
  natively today.
