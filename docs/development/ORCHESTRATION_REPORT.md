# PSYCHE OS DeepSeek development-system preparation report

**Prepared:** 2026-08-10
**Ready for implementation:** yes
**Branch:** `codex/deepseek-development-system`
**Prepared from:** `eff1a97` (`docs: finalize v2 master spec and F0 contract`)
**REAL_DATA_GATE:** `CLOSED`

## What was prepared

- A concise implementation operating manual with authority, lifecycle, risk, test, review, Git, context, deviation, and gate rules.
- A compact machine-readable state whose current action survives chat loss.
- A Roadmap-derived 7-milestone / 12-epic capability map with dependencies, exclusions, objective gates, and gate impact.
- Lean reusable DeepSeek implementation/fix prompts and focused Codex next-epic/high-risk-review prompts.
- A ready-to-run DeepSeek E00 wrapper around the frozen research-derived F0 contract.
- Compact report/deviation templates and one documentation-state validator.
- Concise durable delivery rules in `AGENTS.md`.

No production F0 code, real data, provider integration, UI, import parser, scoring content, or gate-open action was created.

## Plan and milestones

The final plan has **7 milestones and 12 epics (E00–E11)**:

1. Secure synthetic foundation — E00–E01.
2. Evidence-centered local experience — E02–E03.
3. Governed measurement and personal science — E04–E06.
4. Optional bounded AI — E07.
5. Selective imports and retrieval — E08–E09.
6. Conditional professional interchange — E10.
7. Lifetime operations and gate decision — E11.

The risk distribution is **8 `RISK-H`, 4 `RISK-M`, 0 `RISK-L`**. There are no low-risk epics because documentation/mechanical work stays inside the implementation epics instead of becoming artificial micro-epics.

## Codex checkpoints

There are **8 mandatory focused Codex checkpoints**, one for each `RISK-H` epic:

- E00 secure semantic/cryptographic/deletion/recovery core;
- E01 independent assurance and recovery evidence;
- E02 desktop webview/typed IPC trust boundary;
- E06 causal/N-of-1 and intervention limits;
- E07 provider/`NEVER_CLOUD`/LLM-write/mental-safety boundary;
- E08 hostile importer/parser core;
- E10 professional interchange and intended-use expansion;
- E11 release evidence and explicit real-data decision.

E03, E04, E05, and E09 use DeepSeek self-review and objective gates without a second model by default. A material deviation or actual high-risk boundary crossing escalates. Codex review never substitutes for a qualified independent clinical, cryptographic, legal, privacy, rights, psychometric, or lived-experience reviewer required by the normative contracts.

## Deliberately not automated

- No multi-agent pipeline, standing council, branch-per-task workflow, or automatic second-model review.
- No pre-generated E01–E11 prompts; they are prepared just in time from accepted code and reports.
- No automatic architecture/roadmap rewrite, research rerun, or project-wide red team after each epic.
- No automatic Git commit/push/PR and no automatic `REAL_DATA_GATE` transition.
- No invented `FAST/EPIC/FULL` scripts before E00 establishes the actual locked Python toolchain.
- No arbitrary coverage threshold, test-count KPI, or generated test matrix detached from named failures.
- No gate approval, clinical/safety/legal/rights decision, or independent review impersonated by code or a model.

One helper, `scripts/dev/validate_orchestration.py`, was justified because the same compact state/path/epic/gate/fence checks run at every epic boundary. It is not a test framework.

## F0 prompt audit and adaptation

The research F0 prompt was preserved unchanged and remains the detailed binding control catalog. The new `docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`:

- adds the current state, risk, report, review, and boundary-transition contract;
- gives a targeted source read list and explicitly avoids unrelated historical/research/safety context;
- groups repeated requirements by executable boundary while referencing the original exact sections;
- preserves synthetic capability, typed canonical semantics, `NEVER_CLOUD`, SQLCipher/OS/recovery fail-closed behavior, blob atomicity, deletion, migration, backup/restore/export, threat/fault evidence, restricted CLI, exact deliverables, and honest partial/blocker states;
- sequences targeted checks and one final full gate;
- removes `coverage >= 90%` as an arbitrary acceptance number while retaining coverage inspection and every named high-risk proof;
- forbids DeepSeek from self-accepting, committing, claiming independent review, expanding scope, or opening the gate.

This is a delivery simplification, not a reduction in F0 assurance.

## E01 materialization decision

E01 is **JIT, not materialized**. Its purpose is stable, but its exact target build, platform, toolchain commands, failure evidence, independent-review scope, and long-horizon fixtures depend on the accepted E00 implementation. Generating it now would either duplicate E00 or invent stale checks. `STATE.yaml` keeps E01 `PLANNED`, and `PREPARE_NEXT_EPIC.md` turns it into `READY` only after E00 is accepted.

## Starting DeepSeek

1. Open the repository at `C:\Dev\psyche-os` in DeepSeek V4 Pro.
2. Give it the complete contents or exact accessible path of `docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`.
3. Let DeepSeek implement through `IMPLEMENTED`/`BLOCKED`; do not let it mark `ACCEPTED` or commit.
4. If implemented, run the focused Codex review template before acceptance and fixes.

PowerShell convenience command to copy the prompt:

```powershell
Get-Content -Raw C:\Dev\psyche-os\docs\prompts\deepseek\E00_F0_IMPLEMENTATION.md | Set-Clipboard
```

## Validation

The orchestration task validates proportionally:

- `STATE.yaml` and authoritative gate YAML parse;
- required source/artifact paths exist;
- E00–E11 IDs are unique/sequential and E00 matches `STATE.yaml`;
- both state and authoritative gate are `CLOSED`, with automatic opening forbidden;
- current prompts contain no real-data authorization pattern and E00 is explicitly synthetic-only;
- Markdown titles/fences are structurally sane;
- current Git branch matches state;
- frozen research foundation remains valid;
- Git whitespace/diff/status and the user-provided orchestration prompt checksum are reviewed.

Completed results:

- `python scripts/dev/validate_orchestration.py`: **113 passed, 0 failed**, 12 epics, gate `CLOSED`.
- Epic field audit: 12/12 sections contain every required field; 8 `RISK-H`, 4 `RISK-M`, 8 required Codex reviews.
- `python scripts/validate_research_foundation.py`: **0 errors**; three duplicate-heading warnings are confined to preserved input/historical prompts/specification.
- `python -m py_compile scripts/dev/validate_orchestration.py`: passed.
- `git diff --cached --check` for all new delivery artifacts: passed. The separately preserved user master prompt retains its intentional Markdown hard-break whitespace; its SHA-256 remains `cc7dc528d26ca16de7d1dace3fedebd95ce02ab12a674f85b3712bedb6d31083`.
- Manual prompt scan found only prohibitions/review references to real data, never authorization.

## Git state and exact next action

This development system was prepared on `codex/deepseek-development-system` from `eff1a97`. `STATE.yaml.git.accepted_commit` is intentionally `null`: no implementation epic is accepted. The orchestration commit/dirty state is reported in the final handoff; no push occurs.

**Exact next action:** run DeepSeek V4 Pro with `C:\Dev\psyche-os\docs\prompts\deepseek\E00_F0_IMPLEMENTATION.md`. The next task is implementation, not another planning session.
