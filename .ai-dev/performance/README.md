# AI Dev OS v2 — Performance & Token Efficiency Canary

A small local-first canary that answers:

> Does local code intelligence + deterministic context selection + impact-based
> verification materially improve real Psyche OS development vs the V1 workflow?

The PC does the mechanical work (index, search, parse, rank, dependency traversal,
range selection, test mapping, bounded verification, output compression, metrics) and
preserves raw evidence locally. The LLM reasons over exact ranges instead of whole files.

This is an **extension/automation of the V1 Context Broker** (`.ai-dev/context-broker.md`
and `docs/AI_DEV_OS_V1.md` §25–27), not a parallel competing workflow: the waterfall
`authority → rg → ast-grep → exact source ranges` is preserved, just made deterministic
and reusable.

## Layout

| Path | Purpose |
|---|---|
| `config.yaml` | Optional overrides for index/context thresholds |
| `../evidence/performance/` | Generated runs + index cache (gitignored); README kept |
| `scripts/ai_dev_perf.py` | The one CLI (stdlib + rg/ast-grep/git/uv) |
| `tests/unit/test_ai_dev_perf.py` | Focused synthetic-repo tests (no real data) |
| `.ai-dev/skills/psyche-perf.md` | Skill that routes a session to the CLI |
| `docs/AI_DEV_OS_V2_PERFORMANCE_CANARY_REPORT.md` | One concise evidence report |

## Commands

```bash
uv run python scripts/ai_dev_perf.py map                                  # build/read the index
uv run python scripts/ai_dev_perf.py context <term>...                    # exact-range context
uv run python scripts/ai_dev_perf.py impact --paths <file>...             # affected surface
uv run python scripts/ai_dev_perf.py verify --paths <file>...             # targeted pytest (fail-closed)
uv run python scripts/ai_dev_perf.py prompt --task "..." --symbols <s>... # self-contained packet
uv run python scripts/ai_dev_perf.py benchmark                            # micro cost measurements
uv run python scripts/ai_dev_perf.py benchmark-v1v2                       # fair V1 vs V2 over frozen tasks
uv run python scripts/ai_dev_perf.py prepare-e11                          # read-only PREPARE E11 dry run
uv run python scripts/ai_dev_perf.py report                               # regenerate measured report sections
```

## Fair V1 vs V2 benchmark

`benchmark-v1v2` runs the frozen real historical tasks in
`benchmarks/tasks.yaml` against their base trees through two faithful workflows:

- **V1**: rg over src + tests, exact match-line ranges, V1-style lexical test discovery
  (no persistent index).
- **V2**: local cached index → symbol/module resolution → exact definition ranges,
  index test map; rg only as fallback.

Both use the same terms and token target; ground truth is the git diff of each accepted
commit (recall/precision). Evidence: `.ai-dev/evidence/performance/v1v2-benchmark.json`
(committed), raw runs local under `../evidence/performance/runs/`.

`prepare-e11` is a read-only next-epic preparation that emits the bounded
`PREPARE_E11_PERF_CONTEXT_PACK` plus a V1-vs-V2 metrics artifact. It never implements
E11 and never opens `REAL_DATA_GATE`.

## Scope discipline

- No new production dependency, no network, no daemon, no database.
- Application source (`src/psyche_os/`, `desktop/`) is **never modified**.
- Protected control-plane paths (`.ai-dev/policy`, `verification`, `hooks`, telemetry
  schema, `state.yaml`) are untouched; `gates.yaml` is only read to name the gate level.
- Evidence is metadata-first and redacted by convention; raw tool output stays local.

See `docs/AI_DEV_OS_V2_PERFORMANCE_CANARY_REPORT.md` for measured results.
