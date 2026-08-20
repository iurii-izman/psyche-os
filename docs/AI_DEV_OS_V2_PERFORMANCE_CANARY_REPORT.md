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

## Final Targeted Fix R1 (2026-08-21)

An independent Codex acceptance review found eight defects (A1–A8) in the retained V2
tooling and in this report's claims. This pass repairs them with minimal local changes to
the six AI Dev OS scripts, focused tests, and this report. **No application source changed;
no production dependency added; V1 remains independently operable; `E11 NOT IMPLEMENTED`;
`REAL_DATA_GATE CLOSED`; PR #11 remains DRAFT / NOT MERGED.**

| finding | status | change | evidence |
|---|---|---|---|
| A1 machine truth not truncated | FIXED | `parse_reportlog` adds complete `failure_nodeids` + `failure_records_count` (uncapped); test-select reads `failure_nodeids`, never the bounded `failures` list | unit tests with 20–25 failing identities: machine IDs complete, presentation ≤ 10 |
| A2 test selection fail-closed | FIXED | explicit status semantics `PASS/TEST_FAILURE/INFRA_ERROR/NO_TESTS/INCOMPLETE`; infra rc (2/3/4) and missing/malformed reportlog can never establish detection; unavailable selectors → `SKIPPED_UNAVAILABLE`; detection requires complete-detector intersection | focused tests; revalidation below |
| A3 harness fail-closed | FIXED | `overall_status` — timeout / non-zero harness rc / setup failure / recorded errors can never be PASS; single-run CLI exit 0 only on PASS; bounded psutil process-tree termination on timeout | focused tests incl. synthetic sleeper, no survivor |
| A4 content-based cache invalidation | FIXED | index cache digest now uses a sha256 content fingerprint (path + bytes), not mtime/size | same-size + restored-mtime edit → cache MISS + updated mapping; unchanged → HIT |
| A5 one capability state enforcement | FIXED | shared `execution_allowed` primitive (case-insensitive, fail-closed) used by launcher AND tournament; DISABLED/QUARANTINED refuse regardless of caller | launcher + tournament tests incl. case variants |
| A6 reportlog schema + redaction | FIXED | non-object JSON events are malformed (never a crash/green); deterministic secret redaction before any AI-facing render (message/traceback/command) | non-object JSON tests; synthetic `sk-proj-…`/bearer/api-key redaction tests |
| A7 minimal harness environment | FIXED | harness env built from an explicit allowlist + only the exact provider credential (DeepSeek-derived for Claude/opencode; none extra for reasonix/codex) | unrelated parent secret absent from every harness env |
| A8 claims match executable reality | FIXED | this report corrected: `code-review-graph` is LAB/conditional (not the default); selector claim gated on revalidation; testmon claim invalidated; Task-A causation downgraded; freeze/reboot caveat added; PREPARE figures explained (not double counting) | see "Invalidated claims" and "Selector revalidation" below |

### Invalidated historical claims

- **Wave 2 test-selection recall** (PR11 1.0, testmon 0.8, testmon hub-schema false negative,
  impacted 1.0): invalidated by A1/A2 — the detector ground truth was the bounded (≤10)
  presentation list. §5/§6 above mark them superseded. The revalidation below is the fresh,
  repaired evidence.
- **`code-review-graph` as the preferred/default code-intelligence path**: corrected. It is a
  LAB / conditional field challenger; the executable default is the deterministic local index
  (`ai_dev_perf context|prompt`). The architecture was NOT changed to make it the default.
- **Wave 3 Task-A "model-capability signal, not a harness difference"**: downgraded to
  "model causation is plausible but not established" (all three CHEAP harness runs shared the
  same failure under the same requested model class).
- **Pre-run task-freeze chronology and the discarded reboot attempt**: asserted, not
  independently retained; no retry evidence was kept. `HARNESS_NO_WINNER` remains accepted
  without over-claiming those chronology details.

### Selector revalidation (A1/A2-repaired)

`ai_dev_tournament.py test-select --revalidate` reruns the **five frozen mutation scenarios**
with **FULL truth + the retained current selector only** (no external selectors; testmon /
impacted are `SKIPPED_UNAVAILABLE`). Compact aggregate:
`.ai-dev/evidence/performance/tournament/test-select/revalidation.json`.

| scenario | class | FULL status | detector count | current status | selected tests | current detected |
|---|---|---|---|---|---|---|
| leaf-temporal-validity | leaf | TEST_FAILURE | 2 | TEST_FAILURE | 130 | ✅ |
| mid-crypto-vmk-length | mid | TEST_FAILURE | 3 | TEST_FAILURE | 277 | ✅ |
| cross-domain-version-isactive | cross-module | TEST_FAILURE | 4 | TEST_FAILURE | 161 | ✅ |
| storage-filesystem-regular | storage | TEST_FAILURE | 77 | TEST_FAILURE | 122 | ✅ |
| hub-schema-primary-key | hub | TEST_FAILURE | 239 | TEST_FAILURE | 482 | ✅ |

**Retained selector result: PASS (5/5 repaired bounded mutation probes detected).** The hub
scenario's detector count (239) is the same 239-failure scenario the review flagged: with A1's
complete machine accounting, all 239 detector identities are used — the old capped-to-10
presentation can no longer corrupt detection. Five probes are bounded, not universal proof;
FULL pytest remains the final truth gate.

### Remaining UNKNOWNs / residuals

- **pytest-testmon previous false-negative claim: INVALIDATED / UNRESOLVED.** Not re-proven;
  not reinstalled; selection remains unresolved / not selected.
- **Selector status:** five probes are bounded, not universal proof. FULL pytest remains the
  final truth gate.
- **A9 (non-blocking, unchanged):** the non-blocking context defect (module-like query such as
  `e09_retrieval` returning zero candidates with success; exact-symbol context can include a
  contained duplicate `rg` line) was **left alone** unless a trivial fix fell out of an already
  required change — it did not, so A9 remains OPTIONAL / NON-BLOCKING.

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
  using a **sha256 content fingerprint** (not mtime/size), so a same-size edit with a
  restored mtime still invalidates the cached index/test map (R1/A4). A changed test
  import invalidates the cached test map (unit-proven).
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

---

# Acceleration Wave 2 — Intelligence Tournament (2026-08-17)

A LARGE experimental LAB wave. Installed a local arsenal for two expensive AI
activities — **code intelligence** and **test selection** — and ran every external
challenger against the SAME frozen historical tasks (PR #11 control set). The
goal is not to prove a permanent winner; it is to keep healthy challengers
installed for future real epics while making the honest initial ranking visible.
Wave 1 foundation is untouched; application source is untouched.

Status: **`WAVE_2_COMPLETE`** · base `ceb3031` · branch `ai-dev/v2-performance-canary`

## 1. Installed arsenal

| candidate | category | version | source | license | environment | state |
|---|---|---|---|---|---|---|
| v1 | code-intel control | — | repo V1 (rg + ast-grep) | MIT | repo | core |
| v2 | code-intel control | — | repo PR11 index | MIT | repo | core |
| code-review-graph | code-intel | 2.3.7 | tirth8205/code-review-graph | MIT | uv tool | lab |
| codebase-memory | code-intel | 0.10.5 | DeusData/codebase-memory-mcp | MIT | uv tool | lab |
| pathfinder | code-intel | 0.23.2 | irahardianto/pathfinder (pathfinder-mcp) | MIT | cargo (source build, Windows) | lab |
| symlens | code-intel | 0.12.15 | TtTRz/symlens | MIT | WSL2 (cargo) | lab |
| aider-repo-map | code-intel | 0.86.2 | Aider-AI/aider | Apache-2.0 | uv tool | lab |
| pytest-testmon | test-selection | 2.2.0 | pytest-testmon | MIT | dev dep | lab |
| pytest-impacted | test-selection | 0.28.0 | pytest-impacted | MIT | dev dep | lab |

Every install was primary-source-verified before installation (identity, version,
license, OS support, languages, install path, maintenance). No candidate was
substituted on a name match alone.

## 2. Code-intelligence tournament

All candidates ran on the **5 frozen historical tasks** with the **same terms and
the same token target (20 000)**, scoring against git-diff ground truth. Objective:
**HIGH RECALL with SMALL USEFUL CONTEXT** — a candidate that returns almost nothing
can never win.

| candidate | src recall (mean) | ctx tok (median) | ctx tok (total) | raw output B (median) | dur ms (mean) |
|---|---|---|---|---|---|
| v1 (control) | 0.806 | 1 269 | 10 509 | 29 190 | 414 |
| v2 (control) | 0.917 | 8 403 | 35 211 | 13 331 | 155 |
| **code-review-graph** | **0.945** | **459** | 1 836 | 1 432 | 20 856 |
| codebase-memory | 0.833 | **77** | 380 | 2 840 | 35 761 |
| pathfinder | 0.444 | 158 | 774 | 40 363 | 1 907 |
| aider-repo-map | 0.972 | 19 165 | 95 630 | 81 558 | 13 518 |
| symlens | 0.555 | 45 | 218 | 1 572 | 366 |

**Reading.** The recall/context frontier is the story:

- **code-review-graph** leads on the primary objective: **0.945 recall at 459 median
  context tokens** — the best recall with still-tiny context. Its graph search also
  surfaces the *tests* for each task (test recall 0.6–1.0), which no control does.
- **codebase-memory** is the most economical: 77 median tokens at 0.833 recall. It
  misses ~17% of relevant files — the fewest false negatives of the cheap tools.
- **aider-repo-map** has the highest recall (0.972) but at **41× the context of
  code-review-graph** (19 165 median tokens) — the "giant high-recall dump is not
  automatically useful" case, made explicit. Precision is correspondingly low.
- **pathfinder** (0.444) and **symlens** (0.555) trail on retrieval: their text/symbol
  search misses module-name terms that live only in file paths (not content).
- **v1/v2 controls** confirm the Wave 1 crux: v2 has high recall but an 8×-larger
  context; v1 stays small but thin.

(Full per-task tables: `.ai-dev/evidence/performance/tournament/code-intel/comparison.json`.)

## 3. Per-task results (source-recall / context-tokens)

| task | v1 | v2 | crg | cbm | pathfinder | aider | symlens |
|---|---|---|---|---|---|---|---|
| e10-hardening-f1f5 (localized) | 0.667 / 1269 | 1.0 / 11002 | 1.0 / 371 | 1.0 / 77 | 0.333 / 158 | 1.0 / 19259 | 0.333 / 72 |
| e08-durable-storage (cross-module) | 0.556 / 5187 | 0.667 / 8403 | 0.778 / 519 | 0.333 / 50 | 0.111 / 158 | 0.889 / 19391 | 0.222 / 70 |
| e07-disclosure (verification-heavy) | 1.0 / 679 | 1.0 / 5724 | 1.0 / 459 | 1.0 / 127 | 1.0 / 168 | 1.0 / 19165 | 1.0 / 45 |
| e06-bounded-review (cross-module) | 1.0 / 3373 | 1.0 / 10081 | 1.0 / 486 | 1.0 / 125 | 0.333 / 289 | 1.0 / 18945 | 0.667 / 30 |
| repo-consolidation (docs) | — | — | — | — | — | 78 files | — |

The docs task has no source ground truth; all candidates correctly return nothing
except aider, whose whole-repo map has no docs-only path.

## 4. PREPARE E11 results

Read-only tournament on the current tree; **`E11 NOT IMPLEMENTED`**, **`REAL_DATA_GATE
CLOSED`**. TWO outputs, per the no-context-soup rule: comparison evidence for every
candidate plus ONE agent-facing context pack from a single chosen candidate.

| candidate | files | ctx tok (est) | raw B | duration ms |
|---|---|---|---|---|
| v1 | 13 | 1 543 | 21 570 | 557 |
| v2 | 5 | 13 189 | 0 | 30 |
| **code-review-graph (chosen)** | 23 | 245 | 35 660 | 25 120 |
| codebase-memory | 17 | 171 | 22 576 | 46 888 |
| pathfinder | 33 | 358 | 403 627 | 4 673 |
| aider-repo-map | 83 | 19 060 | 81 558 | 15 322 |
| symlens | 5 | 59 | 15 722 | 487 |

Provisional selection rule (recorded): term-coverage first (all 5 E11 terms matched),
then matched test-file verification value, then context economy. **code-review-graph**
was chosen — it covers all 5 E11 modules plus their tests at 245 tokens, and it won
the historical tournament. The agent-facing pack renders to ~551 tokens est.
(`.ai-dev/evidence/performance/tournament/prepare-e11/agent-context-pack.md`)

Confirmed: **`E11 NOT IMPLEMENTED`**, **`REAL_DATA_GATE CLOSED`**.

## 7. Resource / operational cost

| candidate | index build | index/cache | runtime (mean/task) | service/daemon |
|---|---|---|---|---|
| v1 | none | none | 0.4 s | none |
| v2 | ~1 s cached | on-disk JSON | 0.15 s (warm) | none |
| code-review-graph | ~8 s (full build) | local SQLite graph | 20.9 s | none (CLI; no daemon started) |
| codebase-memory | ~7-15 s (fast mode) | ~/.cache SQLite | 35.8 s | temp daemon per CLI call (auto-shutdown verified) |
| pathfinder | at server start | .pathfinder cache | 1.9 s | none (MCP over stdio, JIT) |
| aider-repo-map | at map build | .aider cache | 13.5 s | none |
| symlens | 0.2-0.5 s | WSL ~/.symlens | 0.4 s | none |
| pytest-testmon | first run (full) | .testmondata | ~2 s selection | none |
| pytest-impacted | at selection | none | ~14 s | none |

No Docker containers were started. No experimental service/daemon is left running
after the wave (verified by process inspection). External-tool indexes on disk are
retained; run-local artifacts (`.code-review-graph/`, `.aider*`, `.pathfinder/`) are
removed after runs on the current tree and are gitignored.

## 8. Provisional winners

- **Code intelligence — `PROVISIONAL_WINNER` (historical, Wave 2 ranking): code-review-graph.**
  Best recall (0.945) at affordable tiny context (459 median tokens) on the frozen benchmark;
  also surfaces tests (verification value). **Its status is LAB / conditional field challenger —
  it is NOT the executable default.** The normal default path is the deterministic local index
  (`ai_dev_perf context|prompt`). R1/A8 corrected the prose to match that executable reality;
  the architecture was not changed to make the challenger the default.
- **Test selection — `PROVISIONAL_WINNER` (pending mutation results): see §5.**

Provisional means provisional: the real decision comes from future E11/E12… real
epics. No candidate is promoted to CORE; nothing that had a false negative on our
mutation set is eligible to become the default selector.

## 9. LABs retained for real-work observation

| candidate | retained because |
|---|---|
| codebase-memory | most economical (77 median tokens); shadow-run during E11 to measure real-world recall |
| aider-repo-map | highest recall when context budget is not a constraint; map-only comparator |
| symlens | cheapest symbol search (45 tokens); WSL path; healthy challenger |
| pathfinder | real source-built Windows binary (contradicts "unsupported"); MCP tools for symbol navigation |
| pytest-testmon | strongest selection reduction so far (see §5-6) |
| pytest-impacted | installed and measured; note the src-layout degradation (§6) |

## 10. Candidates removed / blocked

None removed. Two classification notes:

- **Pathfinder** was expected to be `INSTALL_BLOCKED` (no official Windows binaries;
  Windows "unsupported"). It was instead **source-built successfully** on this
  Windows 11 machine (`cargo install pathfinder-mcp` 0.23.2) — real evidence that
  overrides the documented platform claim. Installed as LAB.
- **SymLens** does not compile on native Windows (Unix-only daemon referenced
  unconditionally). Installed as **WSL2-local LAB tooling** (authorized) instead of
  being marked `INSTALL_BLOCKED`.
- **code-review-graph** was the "attempt additionally" candidate; its canonical
  identity, MIT license, and Windows install path verified cleanly, so it entered
  the tournament and won the initial ranking.

## 11. Wave 3 recommendation

**`READY_FOR_WAVE_3_HARNESS_TOURNAMENT`.**

Wave 3 should test harnesses (Reasonix, Codex CLI, OpenCode, Aider agent mode) —
but the winning code-intelligence context (code-review-graph) and the test-selection
evidence should be wired as the *proposed context/verification providers* behind a
harness-agnostic Task Contract. Recommended initial contestants (do NOT install/run
in this wave): Reasonix, Codex CLI, OpenCode, Aider agent mode. No model calls were
made through any harness in Wave 2; aider was used for repo-map only.

## 5. Test-selection tournament

FIVE synthetic mutation probes in disposable git worktrees (never committed),
one per dependency tier: leaf (temporal), mid (crypto VMK length), cross-module
(versions.is_active), storage/filesystem (e08 regular-file guard), hub (schema
primary key). Ground truth per scenario = FULL pytest's failing nodeids; a
selector's **MUTATION DETECTION RECALL** = did its selected suite fail on a
detector nodeid.

| selector | leaf | mid | cross | storage | hub | recall | selection ratio (median) |
|---|---|---|---|---|---|---|---|
| full (truth) | 2/2 | 3/3 | 4/4 | 10/10 | 10/10 | 1.0 | 1.0 |
| **current (PR11)** | ✅ | ✅ | ✅ | ✅ | ✅ | **1.0** | 0.23 |
| pytest-testmon | ✅ | ✅ | ✅ | ✅ | ❌ | **0.8** | 0.041 |
| pytest-impacted | ✅ | ✅ | ✅ | ✅ | ✅ | 1.0 | 1.0 (no reduction) |

Selection counts (selected / 708 full): current 122-482 tests (17-68%); testmon
4-81 tests (0.6-11%); impacted 708 (100%, full-equivalent).

> **⚠️ INVALIDATED (R1/A1-A2):** this table's detector ground truth was the bounded
> presentation list (capped at 10), so these recall numbers are unsupported. See
> §6 and "Final Targeted Fix R1 → Selector revalidation" for the repaired evidence.

## 6. Mutation detection

> **⚠️ Historical evidence invalidated (R1/A1-A2).** The Wave 2 detector ground truth was
> the parser's bounded `failures` list (capped at 10), so the per-selector recall numbers in
> §5/§6 — including the **pytest-testmon hub-schema false negative** and the **PR11 recall 1.0**
> — were order-dependent and unsupported. They are superseded by the repaired revalidation
> below (§ "Final Targeted Fix R1 → Selector revalidation"). The fresh numbers use complete
> machine-accounting detector identities and deterministic pytest status semantics.

- **current (PR11 index selector)** — see the repaired five-scenario revalidation below; the
  historical "caught all five at 17-68%" claim is invalidated until re-proven.
- **pytest-testmon** — the previous **false-negative claim is INVALIDATED / UNRESOLVED**: it was
  based on truncated detector identities. The claim is not re-established unless fresh valid
  evidence proves it again; pytest-testmon is not reinstalled and remains unselected.
- **pytest-impacted** — caught everything in the old (invalidated) accounting but **degrades to
  the full suite in our `src/` layout**; selection ratio 1.0 = no test reduction (that
  compatibility limitation is unaffected by A1/A2).
- Full pytest remains truth/control; a selected-test system never redefines acceptance.

## Final status

**`WAVE_2_COMPLETE`** · `E11 NOT IMPLEMENTED` · `REAL_DATA_GATE CLOSED` ·
`READY_FOR_WAVE_3_HARNESS_TOURNAMENT`

# Acceleration Wave 3 — Harness Tournament & Final V2 Decision (2026-08-20)

The FINAL experimental wave. Small, evidence-driven harness tournament answering one
practical question: *which harness should be used for normal AI Dev OS work after V2?*
Claude Code (control) vs Reasonix vs OpenCode on the SAME CHEAP DeepSeek model class
(`deepseek-v4-flash`), each on TWO frozen real tasks. No new framework, no new
subsystem; the retained stack is intentionally SMALLER after this wave.

Status: **`WAVE_3_COMPLETE`** · start `9376adc` → final `HEAD` · branch `ai-dev/v2-performance-canary`

## 1. Frozen tasks (written before any run, never tuned)

Derived from accepted main-branch history; contestants start at the base SHA and are
never shown the accepted diff. Deterministic verification = overlay the result-SHA
test files and run them; PASS iff every collected test passes.

| task | class | base → result | expected files | verification (result-SHA tests) | ground truth |
|---|---|---|---|---|---|
| `e07-disclosure-enforcement` | A (small/local) | `976d383` → `7d6c040` | `application/e07_bounded_ai.py`, `domain/ai_proposal.py` | unit + integration `test_e07_bounded_ai_proposal.py` | result 66 ✅ / base 19 ❌ |
| `e06-bounded-review-semantics` | B (medium/cross-module) | `0534d26` → `e6225c5` | `domain/experiments.py`, `application/e06_experiments.py`, `storage/e06_schema.py` | unit + integration `test_e06_n_of_1_protocols.py`, `test_e06_migration.py` | result 38 ✅ / base collection ❌ |

## 2. Contestants (same model class)

| contestant | version | provider | model | effective model | accounting |
|---|---|---|---|---|---|
| Claude Code (control) | 2.1.233 | DeepSeek direct (`api.deepseek.com/anthropic`) | `deepseek-v4-flash` | confirmed `deepseek-v4-flash` | transcript usage (real) |
| Reasonix | 1.31.0 | DeepSeek preset (anthropic kind) | `deepseek-v4-flash` | confirmed `deepseek-flash/deepseek-v4-flash` | `--metrics` (real, DeepSeek table) |
| OpenCode | 1.18.19 | DeepSeek built-in provider | `deepseek/deepseek-v4-flash` | **UNKNOWN** (stream emits no model; cost basis consistent with DeepSeek) | `step_finish` tokens + cost (real) |

## 3. Core tournament — 6 runs

| task | harness | accept | pass/collected | wall | turns | in tok | out tok | cache read | cost (see note) |
|---|---|---|---|---|---|---|---|---|---|
| A | Claude Code | FAIL | 65/66 | 406 s | 45 | 64 500 | 48 751 | 2 934 272 | ~$0.051 |
| A | Reasonix | FAIL | 65/66 | 284 s | 40 | 1 603 701 | 26 188 | 1 536 896 | $0.0427 |
| A | OpenCode | FAIL | 64/66 | 239 s | 23 | 42 113 | 9 104 | 1 091 456 | $0.0162 |
| B | Claude Code | FAIL | 30/38 | 689 s | 64 | 73 613 | 81 876 | 5 515 264 | ~$0.091 |
| B | **Reasonix** | **PASS** | **38/38** | 415 s | 54 | 3 014 050 | 45 986 | 2 914 560 | $0.0726 |
| B | OpenCode | FAIL | 29/38 | 710 s | 66 | 49 634 | 25 678 | 5 895 424 | $0.0452 |

Cost note: Reasonix/OpenCode report their own cost from DeepSeek pricing (off-peak).
Claude Code's reported `total_cost_usd` uses Anthropic default pricing (mispriced for
DeepSeek), so the column shows a **DeepSeek off-peak ESTIMATE** computed from real token
counts. All token counts are real.

## 4. Quality result

- **Task A — all three FAILED on the same single test**
  (`test_one_interaction_id_can_reach_provider_at_most_once`): `prepare()` must
  permanently reserve an interaction id and reject reuse with `INTERACTION_REUSED`.
  OpenCode additionally missed the lookalike-capability rejection (64/66). All three
  harness runs shared the same failure under the same requested CHEAP model class;
  **model causation is plausible but not established** (R1/A8) — the shared miss is a
  harness-independent observation, not a proven model-capability signal.
- **Task B — only Reasonix PASSED (38/38).** Claude Code (30/38) and OpenCode (29/38)
  both failed the same integration cluster: canonical DB-persisted execution,
  stale-digest/assignment-drift fail-closed, arbitrary-payload authority, deletion
  cascades. Reasonix implemented the full cross-module semantics correctly.
- No harness passed BOTH tasks → **no eligible winner**.

## 5. Optional Codex strong reference (separate; NOT same-model)

Codex CLI 0.130.0 (ChatGPT auth) on Task B with `gpt-5.5` (the configured
`gpt-5.6-sol` requires a newer CLI; `gpt-5` is not allowed with ChatGPT auth).
Reference result: **29/38 FAIL** — the same integration cluster Claude Code and
OpenCode missed. input 648 837 (553 301 uncached), output 12 783, wall 274 s;
cost UNKNOWN (codex emits no cost; different provider economics). Excluded from the
same-model winner calculation.

## 6. Winner decision

**`HARNESS_NO_WINNER`** → **retain Claude Code as the harness.**

No contestant passed both frozen tasks, so none is eligible to replace the control.
Reasonix showed a genuine quality advantage on Task B (full pass at the lowest cost of
the passers) but failed Task A on the same guard as everyone else. There is no material
efficiency advantage **without quality loss**, so the existing working control stands.

## 7. Final retained V2 stack (intentionally small)

- **Code intelligence:** deterministic local index + exact-range retrieval remains the
  **executable default** (`task/psyche-perf → ai_dev_perf context|prompt → local index/cache
  → rg exact ranges → affected-surface → test selection → pytest`). `code-review-graph` is a
  **LAB / conditional field challenger**, NOT the executable default (R1/A8); `codebase-memory`
  SHADOW-only; V1 fallback retained.
- **Test intelligence:** PR11 impact/test selector **inner-loop field canary** — "preferred"
  only if the repaired five-scenario revalidation passes (see "Final Targeted Fix R1 → Selector
  revalidation"); FULL final verification gate retained · `pytest-testmon` / `pytest-impacted`
  **NOT_SELECTED** (removed from project dev dependencies and the lockfile — they were
  tournament-only; the old testmon false-negative claim was invalidated by A1/A2).
- **Harness:** Claude Code (control retained) · Reasonix/OpenCode LAB/shadow-eligible.
- **Routing:** unchanged simple principle (local deterministic tooling → bounded context
  → CHEAP harness → targeted verification → STRONG only when evidence requires it). No
  router built.

## 8. PREPARE E11 final field check (read-only, retained V2 path)

Confirmed **`E11 NOT IMPLEMENTED`** · **`REAL_DATA_GATE CLOSED`**. Selected context
V2 = 18 669 tokens est (0 tool calls, 38 ms warm) over 7 authority ranges; impact 18
affected modules / 32 mapped tests (HIGH); agent-facing pack ≈ 3 616 tokens est. No
code-intelligence tournament re-run.

> **Reading the two figures (R1/A8):** ~18.7K tokens is the **broad retrieval candidate
> set / metrics payload**; ~3.6K tokens is the **clamped rendered agent pack** the agent
> actually receives. This is **not** arithmetic double counting. PREPARE uses a **broader
> internal module-surface candidate resolver** than normal context generation; the
> module-surface context model remains **EXPERIMENTAL / OFF-BY-DEFAULT** for the normal
> `context`/`prompt` path.

## 9. Complexity delta & cleanup

- **+1** focused runner `scripts/ai_dev_harness.py` (~560 LOC) reusing the existing
  Wave 1/2 evidence layout.
- **+1** frozen task spec `.ai-dev/performance/harness-tasks.yaml`.
- **+1** compact aggregate `.ai-dev/evidence/performance/harness-comparison.json`.
- **+1** focused test file `tests/unit/test_ai_dev_harness.py` (8 tests).
- **−2** project dev dependencies (pytest-testmon, pytest-impacted) + lockfile update.
- Raw transcripts/logs remain under the gitignored runs path; only aggregates committed.

## 10. Verification

Focused tests 8/8 ✅ · ruff clean ✅ · AI Dev OS doctor PASS ✅ · orchestration validator
113 passed (1 pre-existing failure: the canary branch is not the branch recorded in
STATE.yaml — expected on this branch) · deterministic replay/evidence check for both
frozen tasks ✅ · PREPARE E11 read-only ✅ · app-source diff: **no `src/psyche_os/` or
`desktop/` changes** ✅ · production dependency diff: none ✅ · full pytest final gate
**743 passed, 2 skipped** (skips = Windows symlink-admin, pre-existing) ✅ · PR #11
remains DRAFT / NOT MERGED.

## 11. Remaining limitations

- CHEAP-model-class results only; a stronger model may pass both tasks. Task A's
  interaction-reuse rule was missed by all three harnesses on `deepseek-v4-flash`.
- OpenCode effective model UNKNOWN from its stream (configured `deepseek-v4-flash`,
  cost consistent with DeepSeek).
- Claude Code cost is a DeepSeek off-peak ESTIMATE; its own `total_cost_usd` is
  Anthropic-basis.
- Single-shot sessions, no retries; a harness invocation/setup error was corrected
  once where clearly infrastructure (reboot interruption; codex model requires newer
  CLI). **Caveat (R1/A8):** the pre-run task-freeze chronology and the discarded reboot
  attempt are **asserted, not independently retained** — no retry evidence for the replaced
  attempt was kept. `HARNESS_NO_WINNER` remains accepted; it is not over-claimed as
  machine-verifiable for those chronology details.
- Reasonix large total input volume (1.6–3.0 M tokens) comes from its caching-heavy
  context strategy; cache-hit economics kept real cost lowest-of-the-passers.

## Final status

**`WAVE_3_COMPLETE`** · **`HARNESS_NO_WINNER`** · **`V2_PERFORMANCE_READY_FOR_E11_CANARY`**
· `E11 NOT IMPLEMENTED` · `REAL_DATA_GATE CLOSED` · harness retained = Claude Code ·
PR #11 DRAFT / NOT MERGED
