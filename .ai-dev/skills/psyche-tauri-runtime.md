# psyche-tauri-runtime  (conditional, NOT enabled by default)

WHEN TO USE: debugging Tauri desktop runtime behavior (UI/IPC/logs/state).

INPUTS: the patch, a Tauri debug build.

STEPS:
1. Build debug: `cd desktop && npm run sidecar:build && npm run tauri -- build --debug`.
2. Use a temporary localhost-only runtime bridge; no production secrets.
3. Capture UI/IPC/logs/state, then run the relevant verifier.

OUTPUT: runtime evidence tied to the change.

STOP CONDITIONS: debug only, localhost only, temporary. Never enable a global Tauri
runtime MCP. No production secrets in the bridge.

ALLOWED TOOLS: tauri build, localhost bridge (temporary).

FORBIDDEN SIDE EFFECTS: no always-on MCP, no secrets, no network exposure.
