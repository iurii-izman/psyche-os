# AI Dev OS v2 — Performance & Token Efficiency Canary Report

_One report, updated in place. Measured sections are regenerable from local
evidence by `scripts/ai_dev_perf.py report`; the narrative sections are maintained
here. Evidence: `.ai-dev/evidence/performance/v1v2-benchmark.json`,
`.ai-dev/evidence/performance/prepare-e11.json`, and raw runs under
`.ai-dev/evidence/performance/runs/` (local, gitignored)._

## Question

> Does local code intelligence + deterministic context selection + impact-based
> verification materially improve real Psyche OS development vs the V1 workflow —
> saving context/tokens/time without weakening verification?

## What changed

This iteration (canary fix pass) closed five failures and added the real-work dry run:

1. **Fair V1-vs-V2 benchmark** (F1). The old benchmark compared exact ranges vs whole
   files, which V1 already achieves. It is replaced by `benchmark-v1v2`, which runs
   the same frozen task definitions through two faithful workflows on the **same**
   historical base trees and the **same** token target:
   - **V1**: authority-style rg over src + tests, exact match-line ranges merged into
     clusters, V1-style lexical test discovery. No persistent index.
   - **V2**: local cached index → symbol/module resolution → exact definition ranges,
     index test map; rg only as fallback for unresolved terms.
2. **Frozen real historical tasks** (F2). Five accepted Psyche OS tasks were frozen in
   `.ai-dev/performance/benchmarks/tasks.yaml` **before** any tuning, with ground truth
   copied verbatim from `git diff --name-only <base> <result>`. A unit test re-derives
   that ground truth from git to prevent drift.
3. **Pytest fail-closed** (F3). Exit code 0 is now required for `PASS`. A non-zero rc
   becomes `FAIL` when parsed failures exist and `UNKNOWN` otherwise (collection/config/
   infra errors) — never a silent green. A real source change with no mapped tests now
   returns `FULL_REQUIRED`; docs-only changes return the light `NO_CODE_CHANGE` path.
4. **Cache invalidation complete** (F4). The cache digest now covers indexed source
   files **and** indexed test files **and** the index-shaping config (src_roots,
   test_root, schema version). A changed test import invalidates the cached test map.
5. **Honest token accounting** (F5). The prompt total is the estimate of the **final
   rendered prompt only**; the embedded context is reported separately and the two
   reconcile (`total = context_embedded + overhead`). No double counting.
6. **PREPARE E11 dry run** (`prepare-e11`). A read-only next-epic preparation on the
   current tree produces the bounded `PREPARE_E11_PERF_CONTEXT_PACK` plus a V1-vs-V2
   metrics artifact. **E11 is not implemented** and `REAL_DATA_GATE` stays `CLOSED`.

No application source changed; no new dependency; V1 remains usable independently.

## Historical benchmark tasks

Frozen at `.ai-dev/performance/benchmarks/tasks.yaml` (ground truth = git diff).

| task_id | class | base | result | changed src | changed tests |
|---|---|---|---|---|---|
| `e10-hardening-f1f5` | localized | `331ea4f` | `853e6a6` | 3 | 2 |
| `e08-durable-storage-integration` | cross-module | `eef04e1` | `1e6dcd8` | 9 | 5 |
| `e07-disclosure-enforcement` | verification-heavy | `976d383` | `7d6c040` | 2 | 2 |
| `e06-bounded-review-semantics` | cross-module | `0534d26` | `e6225c5` | 3 | 3 |
| `repo-consolidation-report` | docs | `129b34b` | `24c9bae` | 0 | 0 |

The docs task has no source/test ground truth; it measures that both variants
correctly select nothing (doc-only path).

## V1 vs V2

Same terms, same token target (20 000), same ground truth. Recall = retrieved
ground-truth source files / all changed source files (new-at-base files are counted
in the denominator — neither variant can retrieve a file that did not exist at base).

| task | class | variant | ctx tok (est) | tool out B | tool calls | ranges | wall ms | src recall | src prec | test recall |
|---|---|---|---|---|---|---|---|---|---|---|
| e10-hardening-f1f5 | localized | v1 | 612 | 16 755 | 8 | 33 | 552.7 | 0.667 | 0.400 | 1.0 |
| e10-hardening-f1f5 | localized | v2 | 10 863 | 13 331 | 1 | 87 | 56.8 | 1.0 | 0.500 | 1.0 |
| e08-durable-storage-integration | cross-module | v1 | 3 462 | 61 844 | 10 | 96 | 537.1 | 0.556 | 0.294 | 0.6 |
| e08-durable-storage-integration | cross-module | v2 | 13 348 | 59 848 | 3 | 117 | 110.8 | 0.667 | 0.333 | 0.6 |
| e07-disclosure-enforcement | verification-heavy | v1 | 310 | 12 056 | 8 | 19 | 437.7 | 1.0 | 0.667 | 1.0 |
| e07-disclosure-enforcement | verification-heavy | v2 | 7 558 | 6 959 | 1 | 61 | 42.2 | 1.0 | 1.0 | 1.0 |
| e06-bounded-review-semantics | cross-module | v1 | 1 989 | 41 626 | 8 | 76 | 430.8 | 1.0 | 0.167 | 1.0 |
| e06-bounded-review-semantics | cross-module | v2 | 10 885 | 37 504 | 1 | 118 | 52.4 | 1.0 | 0.167 | 1.0 |
| repo-consolidation-report | docs | v1 | 1 | 0 | 0 | 0 | 0.0 | — | — | — |
| repo-consolidation-report | docs | v2 | 1 | 0 | 0 | 0 | 0.0 | — | — | — |

| median (code tasks) | V1 | V2 |
|---|---|---|
| context tokens (est, natural) | 1 300.5 | 10 874.0 |
| targeted context tokens (est) | 1 300.5 | 10 874.0 |
| raw tool output bytes | 29 190.5 | 25 417.5 |
| bytes searched (rg scan volume) | 2 973 258 | 743 315 |
| local tool calls | 8.0 | 1.0 |
| retrieval wall ms (warm) | 487.4 | 54.6 |
| source recall | 0.834 | 1.0 |
| source precision | 0.347 | 0.416 |
| test recall | 1.0 | 1.0 |

- V2 one-time index build per base tree: 632.9–921.6 ms, amortized over repeated tasks
  (the warm per-task retrieval is what the table reports).
- Tool-output / context token estimates use the ~4 chars/token heuristic (ESTIMATES).

**Reading.** V2 wins decisively on retrieval efficiency: **8× fewer tool calls**, **9×
faster warm retrieval**, **4× less bytes scanned**, **better source recall** (1.0 vs
0.834 — module-name terms resolve from the index even when rg never hits the module's
own content), and equal test recall. V1 wins on **context volume**: its match-line
clusters are much smaller than V2's module definition surfaces (10.9K vs 1.3K median
tokens). That trade-off is the crux: V1's small context is thin — it misses 17% of the
relevant files, and an implementer would still open the modules to see their
definitions (full-file reads the metric does not count). V2's context is self-contained
but larger. Reported together (context reduction **+** recall), neither variant is a
clean win on the primary "reduce context" goal.

## PREPARE E11 dry run

Read-only, on the current tree, following the JIT next-epic workflow
(`docs/prompts/codex/PREPARE_NEXT_EPIC.md`). Artifacts:
`.ai-dev/evidence/performance/PREPARE_E11_PERF_CONTEXT_PACK.md` and
`.ai-dev/evidence/performance/prepare-e11.json`.

Terms (E11 implementation surface): `e09_retrieval`, `e08_filesystem`,
`e10_professional_handoff`, `storage/schema`, `migrations`.

| metric | V1 | V2 |
|---|---|---|
| selected context bytes | 3 169 | 74 676 |
| estimated context tokens | 792 | 18 669 |
| raw tool-output bytes | 21 534 | 0 |
| bytes searched (rg scan volume) | 4 164 755 | 0 |
| local tool calls | 10 | 0 |
| exact ranges selected | 41 | 71 |
| files selected | 13 | 5 |
| full-file inclusions | 0 | 0 |
| retrieval wall ms (warm) | 413.2 | 29.5 |

- **V2** resolves all 5 terms from the index (5 files: the exact modules E11 builds on)
  with **zero** subprocess calls. **V1** scans the tree 10× and returns 13 noisier files
  (importers of `migrations`/`schema`).
- Deterministic impact: 18 affected modules (reverse-dep closure), **HIGH** (storage
  boundary), 30 mapped test files; full gate stays `uv run pytest -q` +
  `validate_orchestration` + `validate_research_foundation`.
- The bounded pack (7 authority ranges + up to 8 exact code ranges) renders to
  **~3 579 tokens est** — a compact self-contained PREPARE packet.

Confirmed: **`E11 NOT IMPLEMENTED`** and **`REAL_DATA_GATE CLOSED`**.

## Safety

- **Pytest fail-closed**: exit code 0 is the only route to `PASS`. Non-zero rc →
  `FAIL` (parsed failures) or `UNKNOWN` (collection/config/timeout/infra errors) —
  never a green from `failed == 0 && errors == 0`. Exact command, rc, bounded
  stdout/stderr summaries and a raw-evidence path are preserved.
- **No mapped tests**: a source change with no mapped tests returns `FULL_REQUIRED`
  (broader verification required) — it can no longer become a successful no-op. Only
  docs/non-code changes take the light `NO_CODE_CHANGE` path.
- **Cache correctness**: the digest covers source + test files + index-shaping config
  (mtime_ns + size). A changed test import invalidates the cached test map (unit-proven).
- **Token accounting**: `prompt_total = estimate(rendered prompt)`; embedded context
  reported separately; `total = context + overhead` reconciles; tokens are labeled
  ESTIMATES unless observable from provider telemetry (`UNKNOWN` here).

## Complexity

| item | value |
|---|---|
| `scripts/ai_dev_perf.py` | 2 199 LOC (one CLI, stdlib + rg/ast-grep/git/uv) |
| `tests/unit/test_ai_dev_perf.py` | 514 LOC (34 focused tests) |
| `.ai-dev/performance/**` | config (19), README (48), `benchmarks/tasks.yaml` (132) |
| `.ai-dev/skills/psyche-perf.md` | 36 LOC |
| new dependencies | **0** |
| app-source diff | **0** |
| `uv.lock` / dependency diff | **0** |

## Decision

**`PERF_CANARY_NOT_PROVEN`.**

V2 is not a net win over V1 on the primary goal (reduce LLM context/tokens): the
historical median context is ~8× larger, and the E11 dry run shows the same pattern
(18.7K vs 0.8K est. tokens). The wins — 8× fewer tool calls, 9× faster warm retrieval,
4× less scanning, full recall, useful selective verification (targeted 290/667 tests,
7/42 files for a leaf change) — are real, but they do not offset an 8× context
regression in a system whose stated purpose is context reduction, and the context
comparison is confounded: V1's tiny packet misses files (recall 0.834) and counts none
of the follow-up reads an implementer would make. A **context-competitive** V2 (ranked,
relevance-limited module context rather than full definition surfaces) could change
this verdict; that is the single highest-value refinement. V1 already produces exact
ranges, so the benchmark correctly did not reward "exact vs whole file".

## Recommended retained components

Keep the pieces that independently measured value; withhold the unproven context model:

- **Deterministic code map / index** — retain. Sub-second build, powers module
  resolution, recall 1.0, warm repeatability; the caching digest is now correct.
- **Exact-range symbol retrieval** — retain. Median 2% of whole-file bytes per lookup;
  exact definition ranges beat raw match lines for real implementation work.
- **Impact analysis + test selection** — retain. Reverse-dep closure and index test map
  give test recall 1.0 and meaningful targeted verification (0.435 count ratio, 0.64
  wall-time ratio). Note: the lexical test fallback can over-select (e.g. test files
  that merely mention a module path); prefer import-based mapping.
- **Prompt assembler** — retain. Bounded self-contained packets; the PREPARE E11 pack
  renders to ~3.6K tokens.
- **Benchmark harness (`benchmark-v1v2`, frozen `tasks.yaml`)** — retain. It produced
  the honest V1-vs-V2 trade-off and is reusable for the next measured bottleneck.
- **Module definition-surface context** (the V2 context model) — **not retained as-is**.
  It must become ranked and relevance-limited before it can claim context reduction.
- **`prepare-e11` dry run** — retain as a read-only PREPARE helper; it is the intended
  real use of the proven components.
