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

---

# Acceleration Wave 1 (2026-08-17)

One implementation wave for the PR #11 performance branch. Installed and evaluated
three high-ROI local tools, integrated them with the proven subset, and kept the
module-surface context model off the default path. Wave 1 is **removable**: no
component is required for the V1 workflow or for the plain `ai_dev_perf.py` path.

Status: **`WAVE_1_COMPLETE`** · base `ceb3031` · branch `ai-dev/v2-performance-canary`

## A. Difftastic — syntax-aware diff review

| item | value |
|---|---|
| version | 0.70.0 (2026-08-07 release; verified from GitHub releases, not memory) |
| install | user-local via winget `Wilfred.difftastic` (no daemon, no service) |
| executable | `…\WinGet\Packages\Wilfred.difftastic_…\difft.exe` (winget user-package dir; PATH link not created — the launcher resolves it via glob) |
| license | MIT (`github.com/Wilfred/difftastic`) |
| rollback | `winget uninstall --id Wilfred.difftastic --exact` |

Repository-native invocation (JIT, via the Wave 1 launcher):

```bash
uv run python scripts/ai_dev_capability.py run difftastic -- --git <base> <head> [paths...]
# one ref = diff vs working tree; trailing paths bound the comparison
```

Measurement on real historical diffs (frozen benchmark tasks):

| case | output bytes | wall ms | notes |
|---|---|---|---|
| whole-tree, `e08` cross-module (9 files) | 160 308 | 7 008 | "No changes." fast-path per unchanged file; full side-by-side for changed files |
| single file, `e10` small change | 3 203 | 1 040 | git-archive + tar dominate; pure `difft` ~15 ms |
| unchanged file | 52 | 958 | structural fast-path |

Observations: startup/runtime is negligible for the binary; the git-tree adapter's
materialization dominates. Output volume is bounded by scope — whole-tree diffs are
large, per-file diffs are small. Structural changes (moved blocks, re-indented code,
whitespace-insensitive edits) are materially easier to spot in side-by-side mode than
in unified diff. Output is suitable for bounded human/AI review when scoped to the
changed paths.

**Decision: `PROMOTE_CONDITIONAL`** — a review capability for structural/refactor-heavy
changes and targeted diffs. It is **not** a replacement for git diff and is **not**
configured as an always-on external diff.

## B. pytest-reportlog + deterministic parser

| item | value |
|---|---|
| version | pytest-reportlog 1.0.0 (pinned, dev-only), parser `scripts/ai_dev_reportlog.py` 0.1.0 |
| install | dev dependency `[dependency-groups].dev` (verified MIT, pytest-dev org, active) |
| rollback | remove the pin and re-lock; plain stdout parsing is the untouched fallback |

Integration: `ai_dev_perf.py verify --reportlog` (or config `verify_reportlog: true`)
runs the targeted pytest with `--report-log <artifact>`, parses the JSONL with the
deterministic local parser, and prints a bounded failure packet. The raw artifact and
raw pytest console are always preserved under `.ai-dev/evidence/performance/runs/`.

Output-reduction benchmark (measured, not modeled):

| case | raw console B | artifact B | parsed summary B | reduction vs console |
|---|---|---|---|---|
| successful targeted (16 tests, PASS) | 101 | 29 677 | 288 | −185% (pass console is already minimal; packet adds structure) |
| deliberate failure (4 tests, 2 fail) | 1 095 | 10 068 | 895 | 18% |
| many failures (30 tests) | 10 720 | 89 958 | 2 432 | **77%** |
| collection errors (2) | — | 2 359 | 1 478 | — |

Runtime overhead: **~0 ms** (median 994 ms with vs without `--report-log`, 3 runs each).

Failure evidence quality: the packet deterministically carries failing nodeid, phase
(setup/call/teardown/collection), error type, message, and a bounded traceback excerpt
plus explicit exit code and raw-artifact path — evidence the old bounded-stderr path
did not provide in-band at all.

Fail-closed semantics (unchanged, unit-proven): `PASS` requires pytest rc 0 **and** a
clean SessionFinish; a truncated/malformed log is `UNKNOWN`; non-zero rc with parsed
failures is `FAIL`; collection/config errors are `UNKNOWN`; no mapped tests is
`FULL_REQUIRED`. If the plugin/artifact is unavailable, `verify` degrades to the plain
stdout parse automatically.

**Decision: `PROMOTE_CONDITIONAL`.** Deterministic, no false-green, ~0 ms overhead,
trivial fallback — all promotion criteria met. The honest caveat: the pass-case packet
is larger than the already-minimal `-q` console, and the current verify path already
bounds its in-band output, so the >50% reduction is real for failure-heavy runs (77%)
but not for passes. Promoting to CORE is a one-line config flip (`verify_reportlog:
true`) justified once the failure-evidence benefit is observed on real failing runs.
Kept opt-in rather than silently defaulted.

## C. JIT Capability Launcher

```bash
uv run python scripts/ai_dev_capability.py list | info <name> | doctor <name> | run <name> [-- args]
```

- Reuses `.ai-dev/capabilities/registry.yaml` (no second registry). Four Wave 1 records
  added: `difftastic`, `pytest-reportlog`, `reportlog-parser`, `capability-launcher`.
- States honored: `DISABLED`/`QUARANTINED` refuse (exit 2); `LAB` runs only by explicit
  invocation; there is no automatic LAB→CORE transition.
- JIT: invoke → capture bounded evidence → exit. No daemon, no always-on process, no
  new telemetry system (evidence JSONL under `…/runs/capability-runs/`, gitignored).
- Startup overhead: single-digit ms of launcher overhead over the subprocess itself
  (a `difft --version` invocation completed in ~14 ms end-to-end).
- Failure propagation: subprocess exit codes propagate (verified rc=2, rc=3); unknown
  capability → 1; refused state → 2; not-invocable/not-installed → 1 with a clear message.
- difftastic `--git <base> <head> [paths...]` adapter materializes trees and diff
  directories (difftastic takes paths, not refs); one-ref form diffs vs the working tree.

**Decision: `PROMOTE_CONDITIONAL`.** Retained as the standard JIT path for external
tools; its registry state is `core` (the mechanism itself), but the wave's *tools* are
conditional, so the wave-level class is CONDITIONAL until a CORE workflow routes
through it.

## D. PR #11 consolidation

- **RETAIN (proven):** code map/index, exact-range symbol retrieval, impact analysis,
  import-based test mapping, selective verification, benchmark harness + frozen tasks,
  prompt assembler, PREPARE E11 dry-run helper. All exercised unchanged.
- **EXPERIMENTAL / OFF-BY-DEFAULT:** the module-definition-surface V2 context model
  (the ~8×-larger context). It now has an explicit guard: `config.yaml` declares
  `context_model: exact-range` (the only implemented default), and `context`/`prompt`
  reject any other model with a clear error. The model survives only as
  `benchmark-v1v2` evidence. It cannot silently become default.
- Dev-toolchain normalization: the test toolchain (pytest, pytest-cov, pytest-timeout,
  pytest-xdist, ruff, mypy, coverage, hypothesis) moved from the legacy optional
  `dev` extra into `[dependency-groups].dev` so a plain `uv sync`/`uv run` reproduces
  the full dev environment (previously relied on a stale `--extra dev` venv). The only
  **new** dependency is `pytest-reportlog==1.0.0`. No production/runtime dependency
  changed; `src/psyche_os/**` and `desktop/**` untouched.

## Verification (Wave 1)

| check | result |
|---|---|
| focused tests (reportlog parser, fail-closed integration, launcher, context guard) | 62 passed (reportlog 13, launcher 13, perf 36; incl. 2 real difftastic smokes) |
| ruff on changed Python | pass |
| reportlog PASS smoke | pass (146-test targeted run → bounded packet) |
| reportlog FAIL/ERROR smoke | pass (synthetic fixture: 2 failed + collection errors parsed correctly) |
| capability launcher smoke | pass (list/info/doctor/run, refusal, exit-code propagation) |
| difftastic smoke | pass (doctor version, run, `--git` two-ref + working-tree) |
| AI Dev OS doctor | **PASS** |
| orchestration validator | 113/114 pass; the branch-match check fails — **pre-existing** on the canary branch (branch is neither `main` nor the current E10 epic candidate; reproduced identically at base `b35db65`) |
| FULL pytest | **706 passed, 2 skipped** (54 s; skips are pre-existing Windows symlink/platform limits) |
| application-source diff | **0** (`src/psyche_os/**`, `desktop/**` untouched) |
| dependency diff | reviewed; dev-only; `pytest-reportlog==1.0.0` is the only new package |

## Complexity (Wave 1)

| item | value |
|---|---|
| new files | `scripts/ai_dev_capability.py` (454 LOC), `scripts/ai_dev_reportlog.py` (264 LOC), 2 test files (420 LOC) |
| changed files | `ai_dev_perf.py` (+130/−13 reportlog integration + context-model guard), registry, evidence ledger, perf config, README, skill, pyproject, uv.lock |
| new dev dependencies | 1 (`pytest-reportlog==1.0.0`; dev group consolidated) |
| installed external binaries | 1 (`difft` 0.70.0, winget user-local) |
| new framework | none (one launcher + one parser; no daemon, no telemetry system) |

## Wave 1 decisions

| component | decision |
|---|---|
| Difftastic | **PROMOTE_CONDITIONAL** |
| pytest-reportlog + parser | **PROMOTE_CONDITIONAL** (CORE = one config flip once failure-evidence win is observed) |
| JIT Capability Launcher | **PROMOTE_CONDITIONAL** |
| PR #11 performance subset | **RETAIN_PROVEN_SUBSET** (module-surface context explicit OFF-BY-DEFAULT) |

## Next

**`READY_FOR_WAVE_2_PATHFINDER_AND_TESTMON`.** Pathfinder and pytest-testmon are
already registered LAB candidates (`installed: false`); the JIT launcher + registry +
reportlog verify path give both a drop-in A/B mechanism: install → register → `run` /
`verify` → measure against the frozen tasks. Reasonix remains Wave 3.
