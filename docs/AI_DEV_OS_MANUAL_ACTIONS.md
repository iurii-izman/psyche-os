# AI Dev OS v1 — Manual Actions

One residual verification step is BLOCKING for full VERIFIED acceptance; two are
OPTIONAL. No credentials are involved. Acceptance status: PARTIAL (see
`docs/AI_DEV_OS_IMPLEMENTATION_REPORT.md`).

## M-001 — Verify Claude Code starts cleanly with the hook dispatcher active

- **Priority:** BLOCKING (for VERIFIED acceptance)
- **Acceptance note (2026-08-15):** the final acceptance pass could not complete this
  item because its session was launched in a worktree at the BASE commit
  (`practical-blackwell-2a40fc` @ `256057c`), which has no `.claude/settings.json`,
  rather than this implementation worktree. A headless `claude -p` retry was not
  possible (standalone CLI reports "Not logged in"). Dispatcher remains
  standalone-tested (10/10) and the hook config is valid, but live hook firing has
  not yet been observed in a real session.
- **Why agent cannot do it:** Hook activation is read at Claude Code startup. The
  dispatcher is implemented, standalone-tested (10/10 cases), and wired into
  `.claude/settings.json`, but a non-interactive session cannot restart Claude Code
  to confirm the hooks register and the session still starts.
- **Exact user action:** Start a fresh `claude` session in the `sad-chebyshev-784466`
  worktree (branch `claude/sad-chebyshev-784466` @ `77b3ac8`+), then run `/hooks`
  (or `/doctor`) to confirm `PreToolUse` and `Stop` are registered. Confirm
  the session starts normally and ordinary edits/tests still run.
- **Expected result:** Hooks are listed; normal tool use is unaffected; an edit to a
  protected path (e.g. `.ai-dev/policy/risk.yaml`) is blocked with the dispatcher
  message; `git push --force` is blocked.
- **How to verify:** `/hooks` shows the two events; a normal `uv run pytest -q` run
  is unaffected.
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
