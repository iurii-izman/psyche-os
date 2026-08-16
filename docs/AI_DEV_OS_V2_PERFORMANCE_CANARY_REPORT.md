# AI Dev OS v2 — Performance & Token Efficiency Canary Report

_Regenerated from local evidence by `scripts/ai_dev_perf.py report` (2026-08-16T20:10:35.934479+00:00)._

## Question

> Does local code intelligence + deterministic context selection + impact-based
> verification materially improve real Psyche OS development vs the V1 workflow?

## Index (map)

- Index build: **801.7 ms** for 60 modules, 1117 symbols, 20864 LOC.
- The whole index is cached on disk; only changed files invalidate it.

## Context selection

- A single exact-range symbol lookup reads a median of **2%** of its whole file (1117 lookups sampled; est. 5668 tokens saved per lookup).
- Range selection follows the Context Broker waterfall: rg -> ast-grep -> exact ranges; provenance and token estimates are attached to every item.

## Test selection

- 42 test files indexed; a representative 3-module change selects a union of **18** test files.

  - `backup_export/operations.py` (1805 LOC) -> 7 affected modules, 11 mapped tests
  - `interfaces/cli.py` (1524 LOC) -> 3 affected modules, 4 mapped tests
  - `application/e08_imports.py` (1193 LOC) -> 1 affected modules, 7 mapped tests

## Verification

- Full suite: 667 collected, 56.5s.
- Targeted union: 290 collected, 36.1s.
- Test-count ratio **0.435**; wall-time ratio **0.64** (fresh run).
- Inner loop runs targeted subsets; the full suite runs once at the final risk gate.

## Interpretation

- Token volume: an exact-range lookup reads a small fraction of its file (median 2%); the deterministic index removes repeated searches and whole-file reads.
- Wall time: impact-based verification cuts the suite to ~two-thirds for hub modules (see measured ratios above) and is far smaller for leaf/mid changes — e.g. a change to `adapters/e08_filesystem.py` selects 7 of 42 test files. When a change's reverse-dependency closure approaches the full suite, that is the signal to run the final gate directly.
- Caveats: token estimates use a ~4 chars/token heuristic (relative comparisons only); test mapping is import-based with a lexical fallback, so edge cases can over- or under-select. Evidence: raw rg and pytest output stay local under `.ai-dev/evidence/performance/runs/`.
