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
uv run python scripts/ai_dev_perf.py verify --paths <file>...             # targeted pytest
uv run python scripts/ai_dev_perf.py prompt --task "..." --symbols <s>... # self-contained packet
uv run python scripts/ai_dev_perf.py benchmark                            # measured evidence
uv run python scripts/ai_dev_perf.py report                               # regenerate the report
```

## Scope discipline

- No new production dependency, no network, no daemon, no database.
- Application source (`src/psyche_os/`, `desktop/`) is **never modified**.
- Protected control-plane paths (`.ai-dev/policy`, `verification`, `hooks`, telemetry
  schema, `state.yaml`) are untouched; `gates.yaml` is only read to name the gate level.
- Evidence is metadata-first and redacted by convention; raw tool output stays local.

See `docs/AI_DEV_OS_V2_PERFORMANCE_CANARY_REPORT.md` for measured results.
