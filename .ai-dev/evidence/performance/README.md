# Performance canary evidence

This directory holds **generated** evidence from `scripts/ai_dev_perf.py`. The raw runs
and the index cache are gitignored (local only); this README is kept so the directory
has a committed explanation.

| Entry | Kind | Content |
|---|---|---|
| `index.json` | cache | Deterministic symbol/import/test index, invalidated by file mtime+size |
| `runs/` | generated | Per-run raw rg output, pytest output, and `benchmark.json` |
| `runs/baseline-full.json` | generated | One full-suite baseline reused by `benchmark --skip-full` |

The distilled numbers land in `docs/AI_DEV_OS_V2_PERFORMANCE_CANARY_REPORT.md`
(via `ai_dev_perf.py report`). Nothing here is application data; synthetic and
metadata-first only.
