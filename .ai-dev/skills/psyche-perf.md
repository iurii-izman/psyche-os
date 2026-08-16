# psyche-perf

WHEN TO USE: any task where context volume, repeated reading, or verification wall-time
matters; before a multi-module change; when a fresh session needs a self-contained
context packet.

INPUTS: task goal, the files/symbols to be touched, risk level (from
`.ai-dev/policy/risk.yaml`).

STEPS:
1. `uv run python scripts/ai_dev_perf.py map` — build/read the deterministic index
   (symbols, imports, reverse deps, test map). It caches on disk; no re-parse on repeat.
2. `uv run python scripts/ai_dev_perf.py context <symbols/terms>...` — get exact source
   ranges with provenance and token estimates (rg → ast-grep → ranges, per
   `.ai-dev/context-broker.md`). Read only those ranges.
3. `uv run python scripts/ai_dev_perf.py impact --paths <files>` — affected modules +
   tests and a LOW/MEDIUM/HIGH classification (high-risk boundaries from
   `.ai-dev/policy/protected-paths.yaml`).
4. `uv run python scripts/ai_dev_perf.py verify --paths <files>` — run the targeted
   pytest subset (bounded output, raw evidence preserved). The full suite runs once at
   the final risk gate only.
5. `uv run python scripts/ai_dev_perf.py prompt --task "..." --symbols <s>...` — emit a
   self-contained prompt packet (instructions + exact ranges + impact + verification
   plan) for a fresh session.

OUTPUT: exact ranges + affected surface + targeted verify command (or the prompt packet)
with token estimates attached.

STOP CONDITIONS: never open whole files when an exact range suffices; never run the full
suite after every edit; do not weaken a gate to go faster.

ALLOWED TOOLS: the `ai_dev_perf.py` CLI, Read (exact ranges), rg, ast-grep, git
(read-only), targeted pytest.

FORBIDDEN SIDE EFFECTS: no edits, no dependency changes, no modifications to
`.ai-dev/policy/**`, `.ai-dev/verification/**`, `.ai-dev/hooks/**`, or application source.
