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
4. `uv run python scripts/ai_dev_perf.py verify --paths <files> [--reportlog]` — run the
   targeted pytest subset (bounded output, raw evidence preserved). Fail-closed:
   `PASS` requires pytest exit code 0; a source change with no mapped tests reports
   `FULL_REQUIRED` (run the full suite) and never becomes a silent green.
   `--reportlog` emits a deterministic failure packet (nodeid/phase/error/traceback)
   parsed from a machine-readable `--report-log` artifact instead of the console.
5. `uv run python scripts/ai_dev_perf.py prompt --task "..." --symbols <s>...` — emit a
   self-contained prompt packet (instructions + exact ranges + impact + verification
   plan) for a fresh session. The token total is the rendered prompt only (no double count).

WAVE 1 JIT CAPABILITIES:
- `uv run python scripts/ai_dev_capability.py run difftastic -- --git <base> <head> [paths...]`
  — syntax-aware structural diff review (two refs, or one ref vs working tree). Use for
  refactor-heavy changes; bound scope to the changed paths (whole-tree diffs are large).
- `uv run python scripts/ai_dev_reportlog.py <report-log>.jsonl` — deterministic
  failure packet from a pytest report-log artifact (standalone CLI).
- `uv run python scripts/ai_dev_capability.py doctor difftastic` — verify availability/version.

BENCHMARK / PREPARE:
- `uv run python scripts/ai_dev_perf.py benchmark-v1v2` — fair V1 vs V2 over the frozen
  real historical tasks in `.ai-dev/performance/benchmarks/tasks.yaml`.
- `uv run python scripts/ai_dev_perf.py prepare-e11` — read-only PREPARE E11 dry run
  that emits `PREPARE_E11_PERF_CONTEXT_PACK` + V1-vs-V2 metrics; never implements E11.

OUTPUT: exact ranges + affected surface + targeted verify command (or the prompt packet)
with token estimates attached.

STOP CONDITIONS: never open whole files when an exact range suffices; never run the full
suite after every edit; do not weaken a gate to go faster; the module-surface context model
is EXPERIMENTAL/OFF-BY-DEFAULT and cannot be selected on the context/prompt path.

ALLOWED TOOLS: the `ai_dev_perf.py` CLI, the `ai_dev_capability.py` JIT launcher, Read
(exact ranges), rg, ast-grep, git (read-only), targeted pytest (+reportlog).

FORBIDDEN SIDE EFFECTS: no edits, no dependency changes, no modifications to
`.ai-dev/policy/**`, `.ai-dev/verification/**`, `.ai-dev/hooks/**`, or application source.

