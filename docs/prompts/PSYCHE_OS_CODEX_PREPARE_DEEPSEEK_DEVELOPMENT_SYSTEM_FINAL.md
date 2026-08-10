# PSYCHE OS — CODEX MASTER PROMPT
## Подготовка полной, экономной и качественной системы разработки через DeepSeek V4 Pro
### Final orchestration prompt — после завершения Research Foundation v2, до начала F0

**Project root:** `C:\Dev\psyche-os`  
**Текущее состояние:** `RESEARCH_CONVERGED = true`  
**Текущий safety state:** `REAL_DATA_GATE = CLOSED`  
**Основной implementation engine после этой задачи:** **DeepSeek V4 Pro** через IDE/API пользователя  
**Роль Codex в этой задаче:** архитектор и координатор разработки, а не основной автор production-кода  
**Главный приоритет:** качество и сохранение всех конституционных гарантий PSYCHE OS  
**Второй приоритет:** экономия токенов, времени и лишних проверок там, где они не дают реального прироста качества

---

# 0. МИССИЯ

Исследовательская фаза PSYCHE OS v2 завершена.

В репозитории уже существует сильная научная, epistemic, privacy/security и architectural foundation. Теперь необходимо **не проводить новое глобальное исследование и не переписывать Master Spec**, а подготовить практическую систему последовательной реализации продукта преимущественно с помощью **DeepSeek V4 Pro**.

Твоя задача:

> **прочитать актуальные артефакты PSYCHE OS v2, критически проверить готовность к реализации, определить оптимальную последовательность эпиков, минимально необходимую систему контроля качества и подготовить все reusable prompts/contracts/state files, чтобы далее основной объём production-кода можно было последовательно и экономно реализовывать DeepSeek V4 Pro.**

Это задача по **development orchestration**.

Не реализуй production F0 в рамках этой задачи, если только существующий F0 prompt не требует небольшой технической проверки формата или paths.

Результатом должна стать такая структура разработки, при которой пользователь после завершения этой задачи сможет:

1. открыть проект в IDE с DeepSeek V4 Pro;
2. передать готовый первый implementation prompt;
3. получить полностью реализованный эпик;
4. проверить его строго настолько, насколько требует риск;
5. зафиксировать результат;
6. взять следующий подготовленный или автоматически генерируемый prompt;
7. продолжать до готовой системы без постоянного перепроектирования процесса.

---

# 1. БАЗОВЫЙ ПРИНЦИП

Наша стратегия:

> **DeepSeek пишет основную массу production-кода. Codex проектирует delivery system, контролирует архитектурно критические точки и вмешивается только там, где дополнительный review действительно оправдан риском.**

Не создавай бюрократический multi-agent pipeline.

Не создавай tests ради количества tests.

Не создавай documentation ради documentation.

Не создавай второй review-pass там, где обычный implementation + targeted validation уже даёт достаточную уверенность.

Не генерируй заранее десятки огромных prompts, которые устареют до момента выполнения.

Создай **минимальную, устойчивую, just-in-time development system**.

---

# 2. ЧТО УЖЕ ИЗВЕСТНО

Исследовательская фаза v2 завершилась со следующими принципиальными решениями:

- PSYCHE OS — локальная `Personal Evidence & Reflection System`, а не digital twin, AI psychiatrist или autonomous therapist;
- `PersonalModelSnapshot` — датированная производная версия, а не истина о личности;
- source, verbatim report, observation, measurement, assertion, claim и derivation разделены;
- uncertainty, contradictions, unknowns, alternatives и falsification являются first-class concepts;
- autobiographical memory является evidence/report, а не автоматически историческим фактом;
- ICD-11, DSM, RDoC, HiTOP, traits, functioning и thriving — независимые layers;
- персональный p-factor и универсальные wellbeing/identity scores запрещены;
- assessment registry требует rights/language/population/scoring gates;
- tracking должен быть burden-bounded, episodic/adaptive, а не engagement-driven;
- EMA, sleep/device epochs, missingness и measurement reactivity имеют строгие контракты;
- causality имеет уровни `C0–C6`;
- N-of-1 имеет evidence/design levels `D0–D4`;
- interventions имеют risk `R0–R3`;
- canonical architecture — hybrid bitemporal relational;
- graph/vector/search являются производными projections/indexes;
- privacy lineage-aware;
- `NEVER_CLOUD` распространяется на производные;
- encryption/recovery/backup/delete должны быть фундаментальными;
- imports и model output считаются untrusted;
- F0 должен быть минимальным secure core;
- production code и реальные персональные данные пока отсутствуют;
- `REAL_DATA_GATE = CLOSED`.

Не считай этот summary заменой документации. Используй его только как orientation.

---

# 3. СНАЧАЛА ПРОЧИТАЙ SOURCE OF TRUTH

Работай в:

`C:\Dev\psyche-os`

Сначала осмотри repository и Git state.

Прочитай **актуальные документы v2**, а не только исторический v1.

Обязательный минимум:

1. `AGENTS.md` — если существует.
2. `CONSTITUTION.md`
3. `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`
4. `docs/ROADMAP.md`
5. `docs/DECISION_LOG.md`
6. `docs/FINAL_RESEARCH_REPORT.md`
7. `docs/architecture/SYSTEM_ARCHITECTURE.md`
8. `docs/architecture/DATA_MODEL.md`
9. `docs/architecture/PRIVACY_SECURITY_MODEL.md`
10. `docs/architecture/MENTAL_HEALTH_AI_SAFETY.md`
11. `docs/architecture/THREAT_MODEL.md`
12. `docs/architecture/REAL_DATA_GATE.yaml`
13. `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`
14. `docs/SCIENTIFIC_GOVERNANCE.md`

Не перечитывай Research Dossier целиком без необходимости.

Используй его и Source Registry **только если конкретное implementation decision требует возврата к research evidence**.

Это важное правило экономии контекста.

---

# 4. НЕ ПРОВОДИ НОВОЕ ГЛОБАЛЬНОЕ ИССЛЕДОВАНИЕ

`RESEARCH_CONVERGED = true`.

Следовательно:

- не повторяй 155-source research;
- не перепроверяй весь DSM/ICD/EMA/AI Act;
- не переписывай Master Spec v2;
- не запускай новый red-team всей концепции;
- не создавай Master Spec v3.

Research разрешён только **точечно**, если во время подготовки реализации обнаружена конкретная незакрытая техническая неопределённость.

Пример:

> Master Spec требует envelope encryption, но конкретная production library ещё не выбрана.

Тогда можно исследовать 2–4 реальных варианта и принять ADR.

Не исследуй снова вопрос:

> “Нужна ли вообще encryption?”

Он уже закрыт.

---

# 5. ГЛАВНЫЙ РЕЗУЛЬТАТ ЭТОЙ ЗАДАЧИ

Создай **Lean DeepSeek Development System**.

Она должна включать:

1. окончательную карту implementation epics;
2. dependency order;
3. risk classification каждого эпика;
4. правила выбора объёма тестирования;
5. правила Codex checkpoint review;
6. компактный universal DeepSeek implementation contract;
7. готовый prompt для первого F0;
8. mechanism для генерации следующего epic prompt just-in-time;
9. compact project state;
10. implementation report format;
11. architecture deviation protocol;
12. acceptance rules;
13. token/context efficiency rules;
14. Git workflow;
15. `REAL_DATA_GATE` progression rules.

После этой задачи пользователю **не должна требоваться новая мета-архитектурная сессия перед каждым эпиком**.

---

# 6. НЕ ПЕРЕУСЛОЖНЯЙ DELIVERY PROCESS

Запрещён default pipeline вида:

```text
Implementer
→ reviewer 1
→ reviewer 2
→ reviewer 3
→ full tests
→ full security scan
→ full architecture audit
→ second implementation
```

для каждого эпика.

Вместо этого используй risk-based validation.

Главный принцип:

> **Каждая дополнительная проверка должна закрывать конкретный реалистичный failure mode.**

Если не можешь назвать failure mode — проверка, скорее всего, не нужна.

---

# 7. COST / TOKEN EFFICIENCY CONSTITUTION

Создай и закрепи следующие правила.

## 7.1. Не дублировать Master Spec в prompts

Epic prompt должен **ссылаться на repository files**, а не копировать десятки страниц specification.

## 7.2. Читать релевантный контекст

Каждый Epic Prompt содержит `READ FIRST`:

- обязательные общие файлы;
- 2–6 релевантных документов/sections;
- предыдущий implementation state/report.

Не требовать полного Research Dossier.

## 7.3. Just-in-time prompts

Не писать подробные prompts для 15 будущих эпиков заранее.

Заранее создать:

- полный Epic Map;
- universal template;
- F0 prompt;
- **максимум один следующий fully materialized prompt**, если его scope уже стабилен.

После acceptance эпика следующий prompt создаётся из актуального state + roadmap/template.

Это уменьшает spec drift.

## 7.4. Не повторять уже проверенное

Если invariant покрыт существующим тестом и изменяемый код его не затрагивает — не писать ещё пять эквивалентных тестов.

## 7.5. Targeted tests during development

Во время итерации запускать тесты только затронутого модуля / соседних контрактов.

## 7.6. Final gate once

Полный разумный project gate запускается **один раз в конце эпика**, а не после каждой мелкой правки.

Если full suite со временем станет дорогим, определить fast gate и release/full gate.

## 7.7. Нет arbitrary coverage target

Не требовать `90%`, `95%` или `100%` coverage.

Coverage — diagnostic signal, не KPI.

Тестировать behavior, invariants, failure modes.

## 7.8. Нет forced second model

Отдельный adversarial AI review запускается только если риск эпика это оправдывает.

## 7.9. Документировать decisions, не процесс мышления

Implementation report должен быть компактным.

Не сохранять длинный рассказ о каждом шаге модели.

## 7.10. Не создавать абстракции “на будущее”

Создавать reusable abstraction только если:

- она уже нужна минимум двум реальным paths; или
- защищает constitutional invariant; или
- существенно снижает future migration/security cost.

---

# 8. RISK-BASED EPIC CLASSIFICATION

Спроектируй простой risk classification.

Предпочтительно 3 уровня, если Master Spec не требует другого.

Например:

## `RISK-L` — Low

Типичные изменения:

- non-sensitive UI;
- read-only visualization;
- documentation;
- simple domain screens;
- styling;
- deterministic formatting.

Default validation:

- relevant formatter/lint/typecheck;
- targeted tests only if behavior changed;
- manual smoke if UI;
- no separate Codex review.

---

## `RISK-M` — Medium

Типичные изменения:

- domain services;
- CRUD with invariants;
- API contracts;
- assessment metadata;
- interview orchestration;
- longitudinal calculations without clinical inference;
- export formatting.

Default validation:

- targeted unit/integration tests for changed behavior;
- lint/typecheck;
- migration test if schema changed;
- focused self-review;
- final project fast gate;
- no second-model review unless anomaly/deviation.

---

## `RISK-H` — High / Constitutional

Типичные изменения:

- encryption/key management;
- privacy/`NEVER_CLOUD`;
- deletion/lineage invalidation;
- backups/restore;
- canonical temporal model;
- migrations affecting sensitive data;
- source/evidence lineage;
- claim promotion rules;
- LLM canonical-write boundary;
- mental-health safety boundary;
- statistical causal inference;
- opening `REAL_DATA_GATE`.

Default validation:

- targeted tests;
- relevant integration/adversarial tests;
- lint/typecheck;
- migration/recovery test when applicable;
- explicit constitutional check;
- **Codex checkpoint review required**;
- full project gate before acceptance.

Do not automatically introduce more levels unless they materially improve decisions.

---

# 9. TEST POLICY — QUALITY WITHOUT TEST THEATER

Create a repository-wide testing policy.

## Test when:

- behavior can regress invisibly;
- constitutional invariant is involved;
- data may be lost/corrupted;
- migration changes schema;
- privacy boundary changes;
- deterministic scientific/psychometric logic changes;
- bug existed and needs regression protection;
- edge case is realistic and consequential.

## Usually do not add a new test when:

- changing prose;
- changing CSS;
- renaming an internal symbol already covered by compiler/typecheck;
- changing trivial glue with no meaningful branching;
- another existing test already verifies exactly the invariant;
- a test merely reasserts framework/library behavior.

## Prefer:

- small high-value unit tests;
- boundary/integration tests;
- a few constitutional tests;
- deterministic synthetic fixtures.

## Avoid:

- giant snapshot suites;
- brittle implementation-detail tests;
- dozens of near-duplicate validation tests;
- test generation solely to increase count/coverage.

---

# 10. REVIEW POLICY

Remove the assumption that every epic needs an independent second AI reviewer.

Use:

## Standard epic

DeepSeek implementation
→ targeted validation
→ DeepSeek concise self-check
→ final gate
→ accept if all criteria pass.

## High-risk epic

DeepSeek implementation
→ targeted validation
→ concise implementation report
→ Codex focused review of the risky boundary
→ fixes if needed
→ final gate
→ accept.

## Architecture deviation

Always escalate to Codex before silently changing Master Spec architecture.

## Severe unexplained failure

Escalate only when DeepSeek cannot resolve it after a reasonable bounded attempt.

Do not create infinite “review → review the reviewer” loops.

---

# 11. MODEL RESPONSIBILITIES

Define clear roles.

## DeepSeek V4 Pro

Primary implementation engine.

Expected responsibilities:

- inspect relevant code/docs;
- implement scoped epic;
- create migrations;
- write necessary tests;
- run targeted validation;
- fix failures;
- update concise state/report;
- keep scope controlled.

## Codex / GPT-5.6 Sol

Use selectively for:

- initial delivery-system design — this task;
- high-risk architecture/security/privacy review;
- unresolved design deviation;
- difficult cross-module failure;
- checkpoint after several medium-risk epics if architecture drift is suspected;
- final `REAL_DATA_GATE` review.

Do not spend Codex on routine CRUD/style work unless needed.

---

# 12. EPIC DESIGN PRINCIPLES

Create epics from actual v2 Roadmap and dependencies.

Do not blindly reuse the following example order, but compare against it:

1. Secure Foundation / F0
2. Life Archive Core
3. Evidence & Epistemic Core
4. Assessment / Psychometrics Infrastructure
5. Capture & Interview Core
6. Initial Desktop UX
7. LLM Infrastructure
8. Adaptive Interview Intelligence
9. Longitudinal / EMA
10. Sleep OS
11. Pattern / Personal Science Analytics
12. N-of-1
13. Intervention Registry/System
14. Personal Model / Evidence Explorer
15. Import Pipelines
16. Reports / Clinician Mode
17. Lifetime Hardening / Gate Review

**Use the research-derived Roadmap as source of truth.**

The final map can have fewer or more epics.

Optimization goals:

- clear dependency boundaries;
- vertical user-visible or architectural capability where possible;
- no mega-epic;
- no micro-epics consisting of trivial tasks;
- minimize repeated context loading;
- allow useful intermediate states;
- protect irreversible foundations early.

---

# 13. VERTICAL SLICE PREFERENCE

After foundation work, prefer vertical capabilities over horizontal bulk construction.

Bad:

> “Create every database model for all future modules.”

Better:

> “Implement Life Event capture end-to-end: domain → persistence → API/service → validation → minimal UI if UI exists → export → focused tests.”

Exceptions:

- truly foundational cross-cutting layers;
- encryption;
- privacy;
- canonical provenance;
- migrations;
- audit.

---

# 14. EPIC MAP FORMAT

Create:

`docs/development/EPIC_MAP.md`

Each epic should contain only useful fields:

```text
ID
Name
Goal
Why now
Dependencies
Major deliverables
Out of scope
Risk level
Constitutional invariants touched
Primary source documents
Acceptance criteria
Validation level
Codex review required? yes/no
REAL_DATA_GATE impact
Estimated implementation complexity: S/M/L/XL
```

Do **not** estimate developer hours.

Token/cost estimation may be coarse:

`LOW / MEDIUM / HIGH`

only if it helps model selection/context decisions.

---

# 15. CURRENT STATE FILE

Create a compact machine/human-readable state file:

`docs/development/STATE.yaml`

Recommended structure:

```yaml
project: psyche-os

research:
  converged: true

real_data_gate:
  state: CLOSED

current_epic:
  id: E00
  status: READY

accepted_epics: []

architecture:
  master_spec: docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md
  constitution: CONSTITUTION.md

git:
  branch:
  accepted_commit:

next_action:
  prompt: docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md
```

Keep it small.

Update it **only at epic boundaries**, not after every commit.

---

# 16. EPIC STATUS MODEL

Use a small lifecycle.

Suggested:

```text
PLANNED
READY
IN_PROGRESS
BLOCKED
IMPLEMENTED
ACCEPTED
```

Definitions:

### `IMPLEMENTED`

DeepSeek claims implementation is complete and mandatory local validation passes.

### `ACCEPTED`

All acceptance criteria pass and any required Codex review has completed.

No separate approval ceremony for low/medium-risk epics if objective gates pass.

---

# 17. GIT WORKFLOW — MINIMAL OVERHEAD

Prefer a simple workflow.

Unless repo policy says otherwise:

- stay on a dedicated development branch;
- one clean logical commit per accepted epic, or a small number if an epic is genuinely large;
- do not create branch-per-tiny-task;
- commit only after validation;
- do not push automatically;
- do not rewrite unrelated history.

Before an epic:

- ensure working tree is understood;
- preserve unrelated changes.

After acceptance:

- commit;
- record commit in `STATE.yaml`;
- advance next epic.

For a high-risk spike, temporary branch is acceptable.

---

# 18. IMPLEMENTATION REPORT — COMPACT

Create template:

`docs/development/EPIC_REPORT_TEMPLATE.md`

Each accepted epic report should ideally fit in roughly 1–3 pages, not become another specification.

Fields:

```text
# Epic E__

Status:
Commit:

## Implemented
- ...

## Key files
- ...

## Migrations / data impact
- ...

## Validation
- commands + results

## Constitutional / security notes
- only if relevant

## Deviations
- none / link

## Known limitations
- only material items

## Next dependency
- ...
```

Do not record model chain-of-thought.

---

# 19. ARCHITECTURE DEVIATION PROTOCOL

Create:

`docs/development/ARCHITECTURE_DEVIATION_TEMPLATE.md`

Use only when implementation discovers that source-of-truth architecture is materially impractical or unsafe.

Fields:

```text
Problem
Affected decision
Why current design fails
Minimal evidence
Options
Proposed change
Compatibility/migration impact
Security/privacy impact
Can implementation continue safely without decision?
```

DeepSeek must not silently rewrite constitutional architecture.

Minor implementation detail decisions do **not** require deviation documents.

---

# 20. UNIVERSAL DEEPSEEK EPIC CONTRACT

Create:

`docs/prompts/deepseek/EPIC_IMPLEMENTATION_TEMPLATE.md`

Keep it powerful but lean.

The template should be approximately structured as:

```text
# PSYCHE OS — EPIC {ID}: {NAME}

PROJECT ROOT
C:\Dev\psyche-os

ROLE
You are the primary implementation engineer for this epic.

READ FIRST
- AGENTS.md
- CONSTITUTION.md
- docs/development/STATE.yaml
- exact relevant source-of-truth files
- previous epic report if directly relevant

OBJECTIVE
One concise outcome.

IN SCOPE
...

OUT OF SCOPE
...

CONSTITUTIONAL INVARIANTS TO PROTECT
Only the ones touched by this epic.

IMPLEMENTATION REQUIREMENTS
...

DATA/MIGRATION REQUIREMENTS
Only if relevant.

SECURITY/PRIVACY REQUIREMENTS
Only if relevant.

TEST / VALIDATION REQUIREMENTS
Risk-based and exact.

ACCEPTANCE CRITERIA
Objective checklist.

WORK RULES
- inspect before editing
- keep scope controlled
- do not duplicate architecture
- do not add speculative abstractions
- use synthetic data only while gate closed
- run targeted validation while iterating
- run required final gate once
- fix failures before stopping

DEVIATION RULE
If implementation requires material contradiction with Master Spec/Constitution,
do not silently change architecture. Produce deviation proposal and stop only the
blocked portion.

FINAL OUTPUT
- concise implementation summary
- changed areas
- validation results
- material limitations
- recommended next state
```

Do not fill every possible heading when irrelevant.

Prompt compactness is a design goal.

---

# 21. DEEPSEEK FIX PROMPT

Create a small reusable:

`docs/prompts/deepseek/FIX_FINDINGS_TEMPLATE.md`

For post-review fixes.

It should require DeepSeek to:

- read only the findings;
- inspect affected code;
- fix validated issues;
- add regression tests only where useful;
- rerun affected tests;
- avoid unrelated refactoring;
- report exact resolution.

Do not re-feed the entire original epic prompt unless necessary.

---

# 22. OPTIONAL CODEX CHECKPOINT REVIEW TEMPLATE

Create:

`docs/prompts/codex/HIGH_RISK_EPIC_REVIEW_TEMPLATE.md`

Use only for `RISK-H`.

Review should be focused:

- inspect diff;
- inspect relevant constitution/spec sections;
- identify only actionable high-impact issues;
- verify relevant tests;
- avoid broad repository re-audit;
- do not propose unrelated cleanup.

Output:

```text
ACCEPT
```

or

```text
FIX_REQUIRED
```

with severity-ranked findings.

No stylistic bikeshedding.

---

# 23. FIRST IMPLEMENTATION PROMPT — F0

The repository already contains:

`docs/prompts/F0_IMPLEMENTATION_PROMPT.md`

Do not discard its research-derived content.

Audit it specifically for use with DeepSeek V4 Pro.

Questions:

1. Does it reference the correct current files?
2. Does it accidentally ask for redundant global research?
3. Does it contain unnecessary repeated context?
4. Are validation requirements proportional to F0's high risk?
5. Does it clearly forbid real data?
6. Does it correctly preserve `REAL_DATA_GATE = CLOSED`?
7. Does it ask for unsupported infrastructure?
8. Does it have clear acceptance criteria?
9. Can DeepSeek execute it autonomously in one primary pass?
10. Is there any ambiguity likely to waste tokens?

Then produce:

`docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`

Rules:

- preserve all substantive research-derived requirements;
- remove duplication;
- adapt wording for DeepSeek implementation;
- reference repository docs instead of pasting them;
- include exact targeted validation;
- include final gate;
- include compact report/state update requirements.

F0 is **high risk** because it establishes the sensitive-data foundation.

Therefore a Codex checkpoint review after implementation is justified.

---

# 24. PREPARE THE NEXT PROMPT ONLY IF STABLE

After creating E00, inspect dependencies.

If the immediate next epic has a stable scope independent of F0 implementation details, materialize:

`docs/prompts/deepseek/E01_<NAME>.md`

Otherwise create only:

`E01_PROMPT_DRAFT.md`

or rely on the JIT generator/template.

Do not create E02–E17 full prompts now unless a particular prompt is both small and essentially immutable.

This is deliberate cost/spec-drift control.

---

# 25. JIT NEXT-EPIC MECHANISM

Create a concise coordinator prompt:

`docs/prompts/codex/PREPARE_NEXT_EPIC.md`

Its job after each accepted epic:

1. read `STATE.yaml`;
2. read `EPIC_MAP.md`;
3. read previous report;
4. inspect only relevant changed architecture;
5. verify next epic scope still valid;
6. instantiate `EPIC_IMPLEMENTATION_TEMPLATE`;
7. output the next DeepSeek prompt;
8. update `STATE.yaml` from `PLANNED` to `READY`.

No new global research.

No new project-wide red-team.

No rewriting Master Spec.

If no material architecture drift occurred, this should be a short/cheap Codex task.

---

# 26. OPTIONAL AUTOMATED HELPERS

Assess whether 1–3 tiny scripts would save repeated token/tool work.

Only create them if clearly useful.

Possible examples:

## `scripts/dev/validate_state.py`

Validate:

- `STATE.yaml`;
- referenced prompt exists;
- epic exists;
- gate state valid.

## `scripts/dev/epic_gate.py`

Run a configured set of project checks for current epic.

## `scripts/dev/check_no_real_data.py`

Only if a suitable guard does not already exist.

Do not build a framework for these scripts.

If existing v2 research already created validation scripts that solve these problems, reuse them instead.

---

# 27. VALIDATION COMMAND STRATEGY

Determine actual project language/tooling from repo.

Prepare three conceptual gates, implemented only if useful:

### `FAST`

Changed module:

- unit tests;
- lint/typecheck relevant scope.

### `EPIC`

At epic completion:

- relevant integration tests;
- project lint/typecheck;
- migration checks if touched.

### `FULL / RELEASE`

Reserved for:

- high-risk epic acceptance;
- milestone;
- REAL_DATA_GATE;
- release.

Do not run `FULL` after every medium/low epic if it is materially expensive and `EPIC` provides enough confidence.

If the entire suite is tiny/fast, one full run is fine — do not overengineer gate selection.

---

# 28. WHEN TO USE CODEX REVIEW

Create an explicit matrix.

Default `Codex review = YES` for:

- F0 secure foundation;
- encryption/key management;
- backup/restore affecting real-data readiness;
- hard deletion and lineage invalidation;
- canonical temporal/provenance model changes;
- cloud privacy/`NEVER_CLOUD`;
- LLM canonical-write boundary;
- mental-health safety engine;
- statistical/causal inference core;
- `REAL_DATA_GATE` opening;
- material architecture deviation.

Default `NO` for:

- ordinary domain CRUD;
- simple deterministic services;
- noncritical UI;
- report formatting;
- read-only visualization;
- small import adapters after the untrusted-import core is already accepted;
- docs.

Codex review remains available when a specific anomaly justifies it.

---

# 29. WHEN TO USE DEEPSEEK SELF-REVIEW

Always require a **short self-check**, not a second giant reasoning pass.

At epic end DeepSeek checks only:

- did I meet acceptance criteria?
- did I change out-of-scope areas?
- did I leave TODOs/blockers?
- did I violate Constitution?
- did validation pass?
- did I create speculative abstractions?

This should be concise.

---

# 30. NO “PERFECT BEFORE PROGRESS” LOOP

Do not block implementation for:

- theoretical future scalability with millions of users;
- microservices;
- multi-tenant concerns;
- mobile sync;
- enterprise observability;
- hypothetical cloud orchestration;

unless current v2 explicitly requires them.

Current product is local-first and primarily single-user.

Quality means:

> correct foundations + maintainable code + tested real risks.

Not:

> enterprise infrastructure everywhere.

---

# 31. REAL_DATA_GATE STRATEGY

Read:

`docs/architecture/REAL_DATA_GATE.yaml`

Do not invent a second gate.

In `EPIC_MAP.md` mark which gate conditions each epic can satisfy.

`REAL_DATA_GATE` stays `CLOSED` until the existing machine-readable requirements pass.

No DeepSeek prompt may instruct use of actual user psychological data while gate is closed.

All fixtures:

- synthetic;
- clearly fictional;
- non-derived from user conversations.

Before any future gate-open decision:

- require Codex high-risk review;
- run full relevant gate;
- verify encryption;
- verify backup/restore;
- verify deletion;
- verify export;
- verify privacy controls;
- verify no sensitive logging;
- verify Git leakage protection.

Do not open gate merely because “app works”.

---

# 32. AGENTS.MD

Inspect existing `AGENTS.md`.

Only modify if the new delivery system needs durable repository rules.

Keep it concise.

It may contain:

- source-of-truth hierarchy;
- current real-data prohibition;
- common commands;
- epic state location;
- implementation prompt location;
- deviation rule;
- targeted-test principle.

Do not paste Master Spec into it.

Do not store detailed epic content there.

---

# 33. SOURCE-OF-TRUTH HIERARCHY

Make this explicit.

Recommended hierarchy, subject to existing repo rules:

```text
1. CONSTITUTION.md
2. PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md
3. accepted ADR / DECISION_LOG
4. ROADMAP / EPIC_MAP
5. current Epic Prompt
6. implementation detail
```

If Epic Prompt conflicts with Constitution:

`Constitution wins`.

If Master Spec conflicts with later explicitly accepted ADR:

follow documented supersession rules.

Do not silently resolve material conflicts.

---

# 34. CONTEXT PACKING RULES FOR DEEPSEEK

The DeepSeek prompt must not assume the model needs the whole repo pasted into context.

Provide exact file paths.

For each epic produce a `READ FIRST` list with:

### Always

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`

### Usually

- relevant Master Spec section/file;
- relevant architecture doc;
- previous epic report only if dependency exists.

### Only when needed

- Scientific Governance;
- Research Dossier;
- Source Registry;
- Threat Model;
- Safety doc.

### Avoid by default

- historical v1 spec;
- original giant research master prompt;
- every old epic report;
- unrelated source files.

This is a major token-saving measure.

---

# 35. DO NOT OVER-SPECIFY DEEPSEEK

DeepSeek is an implementation model, not a deterministic script.

Epic prompts should provide:

- goal;
- hard constraints;
- relevant architecture;
- acceptance criteria;
- validation.

Do not prescribe every file/function/class unless architecture requires exact names.

Let the model inspect existing code and make local implementation decisions.

This reduces prompt length and brittle planning.

---

# 36. STOP / ESCALATION CONDITIONS FOR DEEPSEEK

DeepSeek should continue autonomously through normal implementation problems.

It should stop only the blocked portion and report when:

- required architectural choice materially contradicts source of truth;
- destructive migration may lose data;
- security requirement cannot be satisfied with current architecture;
- a required external dependency/license is unavailable;
- tests reveal fundamental spec inconsistency;
- REAL_DATA_GATE would need to be bypassed;
- user secret/real data unexpectedly appears.

Do not stop for trivial decisions the implementation engineer can safely make.

---

# 37. DEPENDENCY MANAGEMENT

Do not add dependency merely because it simplifies ten lines of code.

For new runtime dependency consider:

- maintenance;
- security;
- license;
- platform support;
- lock-in;
- lifetime migration cost.

Document only significant dependency decisions.

No separate ADR for every library.

---

# 38. DOCUMENTATION POLICY

Documentation is required when it preserves knowledge that code/tests do not make obvious.

Document:

- architectural decisions;
- data semantics;
- security invariants;
- public/internal API contracts where needed;
- migration implications;
- operational/recovery procedures.

Do not document:

- obvious functions;
- every implementation step;
- model reasoning narrative;
- duplicated requirements.

---

# 39. CHECK EXISTING F0 BEFORE “IMPROVING” IT

Because `F0_IMPLEMENTATION_PROMPT.md` was produced by the completed v2 research process, treat it as high-value.

Your task is **adaptation and orchestration**, not creative rewriting.

If it already satisfies a requirement, retain it.

Only change where:

- DeepSeek-specific clarity improves execution;
- duplication wastes context;
- paths are stale;
- validation is excessive or insufficient;
- report/state integration is missing.

Create a short diff rationale in the final orchestration report.

---

# 40. EPIC BOUNDARIES MUST COME FROM REAL REPO ARTIFACTS

My earlier conceptual epic list is not authoritative.

Read `docs/ROADMAP.md`.

If research v2 already defines better phases, use them.

You may restructure into implementation epics if the roadmap is too high-level, but preserve research dependencies and rationale.

Do not create epics solely to match an arbitrary number.

---

# 41. PREFERRED SIZE OF AN EPIC

An epic should generally be large enough that:

- it creates a coherent capability;
- context loaded for it is reused meaningfully.

But small enough that:

- DeepSeek can understand and implement it in one sustained session;
- acceptance criteria remain clear;
- failure is debuggable;
- diff is reviewable.

If an epic would touch most of the future application at once, split it.

If two proposed epics merely create adjacent trivial CRUD, merge them.

---

# 42. MILESTONES

Create a small milestone map above epics.

Example conceptually:

```text
M0 Secure Core
M1 Evidence Archive
M2 Structured Self-Knowledge
M3 Intelligent Capture
M4 Longitudinal Personal Science
M5 Guided Interventions
M6 Lifetime Product
```

Use actual v2 architecture.

Milestones help decide when a broader Codex audit is worthwhile.

Do not review every epic independently if several low/medium epics form one coherent milestone.

---

# 43. CHECKPOINT REVIEW STRATEGY

Recommend the **minimum useful Codex checkpoints**.

For example:

- after F0;
- before/after first real-data eligibility;
- after epistemic/evidence core;
- after cloud/LLM boundary;
- after statistical causal engine;
- before intervention/safety layer;
- before lifetime/release milestone.

Do not assume all are necessary.

Use actual epic map.

Output a checkpoint table:

```text
Checkpoint
Why
Risk protected
Required inputs
Expected review scope
```

---

# 44. BUDGET / TOKEN AWARENESS WITHOUT DEGRADING QUALITY

Do not attempt precise token-price forecasting unless the IDE exposes reliable usage.

Instead classify prompts:

- `SMALL`
- `MEDIUM`
- `LARGE`

and note why.

Optimize by:

- narrow context manifests;
- no duplicated specs;
- JIT prompts;
- one implementation pass;
- targeted tests;
- selective reviews;
- compact reports.

Never save tokens by:

- skipping encryption verification;
- skipping migration safety;
- skipping provenance;
- skipping evidence invariants;
- weakening privacy;
- omitting necessary regression tests.

---

# 45. WHAT TO CREATE IN THIS TASK

Create or update the following structure, adapting if equivalent files already exist:

```text
docs/
  development/
    DEVELOPMENT_STRATEGY.md
    EPIC_MAP.md
    STATE.yaml
    EPIC_REPORT_TEMPLATE.md
    ARCHITECTURE_DEVIATION_TEMPLATE.md
    ORCHESTRATION_REPORT.md

  prompts/
    deepseek/
      EPIC_IMPLEMENTATION_TEMPLATE.md
      FIX_FINDINGS_TEMPLATE.md
      E00_F0_IMPLEMENTATION.md
      E01_<NEXT_EPIC>.md            # only if stable enough

    codex/
      PREPARE_NEXT_EPIC.md
      HIGH_RISK_EPIC_REVIEW_TEMPLATE.md
```

If a cleaner existing repo structure exists, integrate with it instead of duplicating files.

Do not create empty placeholder files merely to match this tree.

---

# 46. DEVELOPMENT_STRATEGY.MD

This should become the practical operating manual for implementation.

Keep it concise enough to actually be read.

Required sections:

1. model roles;
2. source-of-truth hierarchy;
3. epic lifecycle;
4. risk levels;
5. test policy;
6. review policy;
7. Git policy;
8. context/token policy;
9. architecture deviation;
10. REAL_DATA_GATE;
11. next-epic generation.

Avoid restating Master Spec.

---

# 47. ORCHESTRATION REPORT

Create:

`docs/development/ORCHESTRATION_REPORT.md`

It should summarize:

- what was prepared;
- final epic count;
- major milestones;
- risk distribution;
- Codex checkpoint count;
- what was deliberately **not** automated;
- how the F0 prompt changed from research version;
- whether E01 was materialized;
- commands/steps for starting DeepSeek;
- current Git state;
- exact next action.

---

# 48. VALIDATE YOUR OWN ORCHESTRATION ARTIFACTS

This task itself does not need heavy code testing.

Validation should be proportional.

Required:

- YAML parse for `STATE.yaml`;
- links/paths referenced by prompts exist where expected;
- Epic IDs unique;
- E00 exists;
- E00 matches current state;
- `REAL_DATA_GATE = CLOSED`;
- no prompt asks for real data;
- no prompt contradicts Constitution in obvious ways;
- Git diff reviewed;
- Markdown structurally sane.

Do not create a test framework just to validate documentation.

A short script is acceptable if the repo already has one or it clearly saves work.

---

# 49. FINAL SELF-CHECK

Before finishing ask:

1. Can the user start F0 in DeepSeek immediately?
2. Is the prompt shorter/cleaner than copying the full v2 spec?
3. Does DeepSeek know exactly what files to read?
4. Are acceptance criteria objective?
5. Are tests risk-based rather than quantity-based?
6. Are expensive reviews limited to high-risk boundaries?
7. Can the next epic be prepared without another global planning session?
8. Is project state recoverable if chat history disappears?
9. Does no file permit real personal data yet?
10. Does the process preserve quality where failure would be costly?

If any answer is no, fix the orchestration system.

---

# 50. FINAL RESPONSE

Do not paste all created prompts.

Return a concise execution summary:

## Ready?
`YES / NO`

## Epic plan
Number of milestones and epics.

## First implementation
Exact path to:

`docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`

## Next epic
Whether E01 is ready or JIT.

## Review strategy
How many mandatory Codex checkpoints and why.

## Cost-control
3–7 main mechanisms used to reduce unnecessary tokens/work.

## Validation
What you actually validated.

## Git
Branch / commits / dirty state.

## REAL_DATA_GATE
Must remain:

`CLOSED`

unless this task unexpectedly discovers that v2 already explicitly authorizes otherwise — but **do not open it in this orchestration task**.

## User next action
Give exact practical action, ideally one command/path to open/copy the DeepSeek E00 prompt.

---

# 51. SUCCESS CONDITION

The task is complete when:

> **PSYCHE OS has a repository-native, lean, risk-based delivery system where DeepSeek V4 Pro can implement the project epic by epic with enough context and validation to preserve quality, but without repeatedly loading the entire research corpus, generating redundant tests, running unnecessary multi-agent reviews, or forcing the user to redesign the workflow after every step.**

The next user action after this Codex task should be **implementation**, not another planning session.

---

# START NOW

1. Inspect `C:\Dev\psyche-os`.
2. Read the v2 source-of-truth files listed above.
3. Inspect existing Roadmap, F0 prompt, gate, validation scripts and Git state.
4. Derive the lean epic/milestone plan from actual v2 artifacts.
5. Design the risk-based implementation/review/testing policy.
6. Create the development orchestration artifacts.
7. Adapt the research-derived F0 prompt into the ready-to-run DeepSeek E00 prompt.
8. Materialize E01 only if its scope is already stable.
9. Create JIT next-epic preparation mechanism.
10. Perform only proportionate documentation/state validation.
11. Review the final diff.
12. Leave `REAL_DATA_GATE = CLOSED`.
13. Return the exact next action for starting F0 with DeepSeek V4 Pro.

**Do not implement production F0 in this task.**
**Do not ingest real personal data.**
**Do not reopen the completed global research phase.**
