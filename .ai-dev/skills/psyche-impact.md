# psyche-impact

WHEN TO USE: before a multi-module change, to bound the affected surface.

INPUTS: the candidate change (files/symbols), risk level.

STEPS:
1. `rg` for references to the symbols you intend to change.
2. `ast-grep` for structural call sites (e.g. `$NAME(...)` / imports).
3. Map affected tests using `rg` over `tests/` for the touched module names.
4. Classify impact: single-module (low) vs cross-module/contract (medium/high).

OUTPUT: an affected-surface list (files + tests) and an impact classification that
drives risk/profile selection.

STOP CONDITIONS: change reaches a HIGH/CRITICAL boundary (crypto, storage, policy,
backup, Tauri IPC) → escalate profile to quality and flag review.

ALLOWED TOOLS: Read, Grep, rg, ast-grep, git (read-only).

FORBIDDEN SIDE EFFECTS: no edits, no "while I'm here" fixes.
