# PSYCHE OS — EPIC E07: One Optional Bounded AI Proposal Slice

**Project root:** `C:\Dev\psyche-os`
**Accepted E06 implementation commit:** `e6225c537ff94390abd1953d70d3caaf5b452712`
**Accepted E06 merge:** `39241af393f2f9e2b0851e6d600be7b8b96c123d`
**Canonical branch:** `main`
**Implementation branch:** `codex/e07-bounded-ai-proposal`
**Risk:** `RISK-H`
**Expected final gate:** `FULL`
**Data:** repository-owned fictional synthetic evidence only
**REAL_DATA_GATE:** `CLOSED`
**Acceptance review:** independent focused Codex high-risk review required

## Role and outcome

Deliver one bounded outcome: implement and objectively evaluate an opt-in,
stateless **structured evidence-grounded reflection proposal** over a small set of
explicitly selected synthetic canonical records. The proposal must cite only
supporting record IDs, expose uncertainty, counterevidence and unknowns, and may
offer bounded questions. It is never evidence, diagnosis, treatment,
recommendation, policy, risk decision or canonical personal state.

This epic proves one external-model-shaped trust boundary without depending on a
live vendor. Implement the candidate and its evidence; do not self-accept, merge,
advance E08 or open the real-data gate.

## Read first

Read completely:

- `AGENTS.md`
- `CONSTITUTION.md`
- `docs/development/STATE.yaml`
- `docs/implementation/E06_ACCEPTANCE_REPORT.md`

Then read only these directly relevant sources and sections:

- `docs/development/EPIC_MAP.md` — E07 only
- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` — §§15 and 17 only
- `docs/architecture/PRIVACY_SECURITY_MODEL.md` — PS-01–PS-03,
  PS-10–PS-12, PS-15–PS-16 and PS-23 only
- `docs/architecture/MENTAL_HEALTH_AI_SAFETY.md` — the normative policy for
  this new boundary
- `docs/SCIENTIFIC_GOVERNANCE.md` — §§7, 8.2, 11 and 13 only
- `docs/architecture/SYSTEM_ARCHITECTURE.md` — §§4–5, 8.3, 11–12 and the
  applicable acceptance criteria in §15 only
- `docs/DECISION_LOG.md` — ADR-007, ADR-015 and ADR-020 only
- `docs/future/CONVERSATIONAL_PSYCHOLOGICAL_SUPPORT_NORTH_STAR.md` — E07
  compatibility constraints only; it is not implementation authority
- `src/psyche_os/policy/engine.py`, `src/psyche_os/provenance/provenance.py`,
  `src/psyche_os/domain/entities.py`, `src/psyche_os/domain/ids.py`, and
  `src/psyche_os/application/ports.py` — accepted interfaces to reuse
- `src/psyche_os/application/e03_archive.py` and
  `src/psyche_os/storage/e03_schema.py` — accepted canonical record/version read
  boundary only
- `src/psyche_os/domain/experiments.py` — accepted claim/action ceiling types
  only where they are directly reusable without changing E06 semantics

Inspect additional files only when directly imported by a touched path. Do not
load historical v1 documents, the original research prompt, the full dossier or
source registry, unrelated architecture, prior repair prompts or E08+ scope.

## Frozen entry decisions

### Narrow task

The sole AI task is a structured evidence-grounded reflection proposal. Given an
explicit purpose and a small selected synthetic evidence set, the provider may
propose:

- concise reflection statements, each with supporting evidence IDs;
- explicit uncertainty for each statement;
- typed material contradiction/counterevidence references;
- typed unknowns and bounded useful questions tied to those unknowns.

The task does not infer a personality, recover memory, explain causes, diagnose,
treat, triage, recommend an intervention or create a conversational relationship.
It must remain independently useful as a one-call proposal even if every future
conversational capability is never built.

### Provider and data profile

Implement one narrow stateless provider port and one repository-owned scripted
offline evaluation adapter. The adapter exercises the same request/response
boundary as a future cloud adapter, but the mandatory gate must not require a
network, vendor SDK, account, credential or mutable provider documentation.

Every request identifies an approved provider, model snapshot and exact config
snapshot. Unknown or unapproved identities fail before context construction.
The provider receives one self-contained request and returns one structured
response. It receives no vault handle, tools or network capability from domain
text and uses no hosted conversation, thread, file, vector store, cache or
long-term personal memory. Do not add a production vendor adapter in this epic.

Only repository-owned fictional synthetic records may cross the provider port.
The existence of the port does not authorize disclosure of personal records;
production enablement stays unavailable while `REAL_DATA_GATE` is `CLOSED`.

### Risk and review

Keep `RISK-H / FULL`. A separate focused Codex review is mandatory after the
implementation report and candidate commits exist. Use
`docs/prompts/codex/HIGH_RISK_EPIC_REVIEW_TEMPLATE.md`; focus it on disclosure
and context construction, canonical-write authority, provider statelessness and
removal, prompt injection, evidence/proposal validity, mental-health safety, and
the bounded North Star compatibility contract. Implementation validation is not
acceptance. Human clinical, privacy and locale governance are not replaced by
that review.

## In scope

### Typed interaction and context contract

Implement only the smallest fields needed for this task:

- an `AIInteractionEnvelope`-compatible request identity with
  `interaction_id`, explicit purpose, context-manifest reference,
  provider/model/config snapshot, policy snapshot, knowledge/safety identity,
  applicable claim/action ceilings, disclosure-receipt reference, structured
  proposal reference and retention semantics;
- optional `session_id` and `turn_id` fields that accept `null` and have no
  session behavior;
- a versioned bounded `ContextManifest` identity containing purpose, explicitly
  selected canonical synthetic IDs, their source versions and cutoff, typed
  supporting/counterevidence/unknown roles, policy decision, provider/model/config
  identity and context-builder version;
- one versioned structured proposal schema whose reflection statements cite
  selected supporting IDs and whose counterevidence and unknown/question fields
  remain typed rather than flattened into anonymous prompt text.

Do not implement the final E09 retrieval engine. Context selection is explicit;
there is no similarity search, graph traversal, hidden expansion or request for
additional records.

Resolve selected IDs and exact versions through the accepted canonical read
boundary. Package fixtures may seed the existing authorized synthetic workflow,
but the context builder must not regenerate or substitute fixture content after
selection. A controlled canonical version/content change must change the manifest
and request or fail the stale authorization; it cannot be hidden by fixture data.

### Externalized policy and disclosure

Resolve policy and lineage before rendering provider context or calling the
adapter. Fail closed for `NEVER_CLOUD`, reconstructive `NEVER_CLOUD` lineage,
missing/contradictory policy, expired purpose/capability, unapproved provider or
model, stale selected version, or any requested ID not in the explicit
selection. Imported evidence text and provider output are data and cannot change
purpose, policy, selected IDs, ceilings, tools or adapter configuration.

Produce a local preview that names purpose, provider/model/config, selected
record IDs/categories, transformations and retention. Require a typed opt-in
authorization scoped to that exact preview. Produce a content-free receipt with
opaque interaction identity and disclosed IDs/categories/counts, versions,
policy/config identity, time and outcome; never copy prompt, output or synthetic
content into ordinary logs or receipts.

### Proposal authority and lifecycle

Provider output begins and remains `PROPOSED`. Deterministic post-validation must
reject malformed output, unknown/invented IDs, citations outside the selected
manifest, missing statement uncertainty, omitted material counterevidence,
questions without a selected unknown, claim/action ceiling violations, and
prohibited diagnosis, treatment, therapy, triage, medical or autonomous-action
content for the bounded evaluation vocabulary.

Expose explicit typed `accept`, `edit`, `reject` and `discard` evaluation actions
if useful, but keep their state bounded and synthetic. Acceptance does not turn
the proposal into evidence, a source report, accepted claim, canonical personal
state, policy or risk decision. E07 must not add a canonical-write path or a new
storage migration for provider output.

### Safety and degraded mode

Keep safety resolution deterministic and outside the provider. The chosen task
may return an allowed proposal, a typed validation rejection, a bounded
safety-limited response state, or provider-unavailable/disabled state. It may
not diagnose, prescribe, conduct therapy, perform triage, promise monitoring or
rescue, affirm implausible premises, conduct recovered-memory work or execute an
external action.

Provider timeout, malformed output, registry removal, policy revocation or model
retirement leaves canonical state byte-for-byte unchanged. Removing the provider
adapter disables only this optional proposal task; capture, query, correction,
export, deletion, restore and accepted E00–E06 behavior remain usable.

## Out of scope

- The future conversational psychologist, multi-turn `Session` engine, guided
  interviewing, `WorkingFormulation`, `SupportSkillRegistry`, recommendation
  lifecycle, proactive follow-up, voice or clinician round trip.
- Hosted memory, conversations/threads, files, vector stores, embeddings,
  retrieval, provider-owned state or model fine-tuning on personal archives.
- Live production provider credentials, vendor SDK coupling, mandatory network
  evaluation, multiple production providers or a provider selection UI.
- Diagnosis, treatment, therapy, clinical decision support, triage, crisis
  detection/monitoring, rescue, intervention selection or autonomous tools.
- Canonical writes from model output, schema migration, desktop/CLI product
  surface, arbitrary vault disclosure, import work, E08 or E09 implementation.
- Real personal or sensitive data while `REAL_DATA_GATE = CLOSED`.
- Changes to accepted E00–E06 behavior, unrelated refactoring, speculative
  abstractions or empty future-only architecture.

## Invariants to protect

- C-01–C-02: preserve human agency and proposal-only model authority.
- C-04–C-08: memory is testimony; no diagnosis/causal overclaim; uncertainty,
  contradiction and unknowns remain first-class.
- C-10–C-12: the core remains local/provider-independent; lineage and least
  disclosure resolve before the provider boundary.
- C-15–C-18: imported/model content is untrusted; relationship, safety,
  scientific and rights policy remains outside the model.
- C-20: only synthetic fixtures; the real-data gate remains closed.

## Failure-driven implementation tests

Add the smallest unit/integration/property and evaluation cases that close these
named failures for the exact slice:

1. Prompt-injection text inside selected evidence cannot change purpose, policy,
   provider configuration, selected IDs, ceilings or tools.
2. Imported/provider text asking for more records cannot expand the manifest or
   cause a second call.
3. Raw or reconstructive `NEVER_CLOUD` lineage blocks context construction
   before the provider adapter is invoked.
4. Missing, unknown, retired or unapproved provider/model/config/policy identity
   fails closed before disclosure.
5. A changed model snapshot or config cannot inherit approval/evaluation from an
   older identity; the pinned scripted regression corpus reruns for the new exact
   identity before it can be enabled.
6. Preview/authorization mismatch, stale source version or expired capability
   prevents the call; the receipt and log remain content-free.
7. Canonical content/version changes alter the manifest/request or invalidate the
   authorization; fixture regeneration cannot conceal canonical state.
8. Invented, unselected or wrongly typed evidence IDs reject the entire proposal.
9. Missing per-statement uncertainty, material counterevidence, required unknown
   or typed question linkage rejects the proposal.
10. Diagnosis, treatment, therapy, triage, medication/medical direction,
   unsupported causal claim, relationship claim, rescue promise or autonomous
   recommendation fails deterministic validation for every named adversarial
   case.
11. Malformed schema, oversize fields, duplicate IDs and unexpected fields fail
   closed; raw provider output is not persisted or logged.
12. Provider timeout/failure, malformed output, registry removal and model
    retirement do not mutate canonical state and leave the local core usable.
13. `accept`, `edit`, `reject` and `discard` cannot relabel output as evidence,
    source report, accepted claim, canonical personal state, policy or risk
    decision.
14. Optional null `session_id`/`turn_id` round-trip without creating session
    semantics; their absence does not change the one-call task.

Use a fixed fictional case with designated supporting records, at least one
material counterevidence record and at least one unknown. The deterministic
evaluation oracle must prove:

- every emitted statement has one or more selected supporting IDs and explicit
  uncertainty;
- every designated material counterevidence ID is surfaced and every emitted ID
  belongs to the manifest;
- unknowns/questions remain linked and non-directive;
- prohibited-authority count and unpreviewed-disclosure count are zero;
- the valid scripted proposal passes while each named invalid/adversarial variant
  is rejected with the expected typed reason.
- each provider/model/config regression artifact is tied to its exact identity;
  alias/snapshot/config drift cannot reuse an earlier pass.

This is the objective value gate for the fixed task: one valid proposal preserves
the fixture's support, contradiction and unknown structure while disclosing no
more than the exact previewed selection. Keep deterministic policy/schema/
evidence/safety tests separate from any optional future live-model regression.
Do not use “looks good,” model self-grading, majority vote or an arbitrary
coverage percentage as acceptance evidence.

## Data, migration, security and privacy

- Reuse accepted IDs, provenance, policy and claim/action types where they fit;
  do not change their semantics to accommodate model output.
- Prefer pure domain values and injected ports. Domain/application code must not
  import a vendor SDK or let the provider own policy, evidence validation or
  safety decisions.
- Keep the new slice in focused E07 modules and the two exact E07 test files named
  in the validation commands; do not turn the provider port into a generic agent
  or tool-execution framework.
- Keep request/response retention `ephemeral` for the E07 profile. A validated
  proposal may exist only in bounded evaluation/application state; receipts and
  regression identities are non-reconstructive.
- No schema migration is expected. If implementation unexpectedly requires a
  canonical schema or accepted-interface change, stop that portion and use the
  architecture-deviation process rather than silently expanding E07.
- Use only clearly fictional repository-owned synthetic fixtures not derived
  from conversations or real persons. Do not place keys, tokens, prompts,
  responses or content in ordinary logs, crash output or committed artifacts.

## Validation

Run the smallest affected tests while implementing. Before reporting completion,
run this final gate once from the repository root:

```powershell
uv sync --frozen
uv run pytest -q tests/unit/test_e07_bounded_ai_proposal.py tests/integration/test_e07_bounded_ai_proposal.py tests/unit/test_policy.py tests/unit/test_provenance.py tests/unit/test_e06_n_of_1_protocols.py
uv run pytest -q
uv run python scripts/validate_f0_scope.py
uv run python scripts/dev/validate_orchestration.py
uv run ruff check src/psyche_os/domain/ai_proposal.py src/psyche_os/application/e07_bounded_ai.py src/psyche_os/adapters/e07_provider.py tests/unit/test_e07_bounded_ai_proposal.py tests/integration/test_e07_bounded_ai_proposal.py
uv run mypy src/psyche_os/domain/ai_proposal.py src/psyche_os/application/e07_bounded_ai.py src/psyche_os/adapters/e07_provider.py
```

The first pytest command is the authoritative targeted E07 and adjacent-regression
set; preserve the exact new test paths. The full pytest command is the required
`FULL` repository gate and runs once after targeted evidence is ready. Do not run
Security Workbench. Desktop/native gates are out of scope because E07 must not
touch desktop files.

Static analysis is a no-new-diagnostics ratchet against exact preparation
baseline `32ea55114a9285057602ef2b88b11a2edcadf58b`. In addition to the clean
touched-file commands above, run `uv run ruff check src/psyche_os` and
`uv run mypy src/psyche_os` on both that isolated committed baseline and the
candidate with the same Ruff/mypy versions. Compare normalized diagnostic
identity by repository-relative file, rule/error code and normalized message;
count-only comparison is insufficient. E07 must introduce zero new Ruff and
zero new mypy diagnostics. An unchanged diagnostic in an accepted untouched
E00–E06 file is known accepted static-analysis baseline debt, not an E07 pass or
blocker. Any diagnostic in an E07-touched Python file remains blocking. Do not
add suppressions, weaken configuration or modify accepted files merely to make
the repository-wide commands return zero.

Record deterministic results separately from any optional provider/model
regression. A skipped mandatory policy, privacy, safety, provider-removal or
canonical-state test is not a pass. Do not add tests for counts, duplicate an
equivalent assertion or impose an arbitrary coverage target.

## Acceptance criteria

- [ ] One opt-in structured evidence-grounded reflection proposal passes the
  fixed synthetic evaluation with exact evidence, counterevidence, uncertainty,
  unknown/question and disclosure invariants.
- [ ] Policy/lineage, preview/capability, provider identity, schema/evidence and
  safety validation occur outside the provider and fail before or after the call
  at the correct boundary.
- [ ] Model output remains `PROPOSED`; no provider output becomes evidence,
  source report, accepted claim, canonical personal state, policy or risk
  decision, and no canonical write/migration is added.
- [ ] The provider is stateless and replaceable; failure/removal leaves canonical
  state unchanged and all non-AI core workflows usable.
- [ ] The interaction/context identities preserve the listed E07 North Star
  extension points without sessions or other future capabilities.
- [ ] Every mandatory named failure has objective evidence, with no unresolved
  `SEV-A` or `SEV-B` defect for this exact synthetic profile.
- [ ] Targeted and final validation results are recorded exactly.
- [ ] `REAL_DATA_GATE` remains `CLOSED` and production personal-data disclosure
  remains unavailable.

## Work and stop rules

- Inspect before editing; preserve unrelated changes and keep scope controlled.
- Implement only on `codex/e07-bounded-ai-proposal` created from synchronized
  `main`; do not perform E07 implementation on `main`.
- Do not duplicate the specification in code comments/docs and do not create
  future-session or E09 retrieval scaffolding.
- Fix in-scope failures before stopping. Do not commit, push, open a PR, merge or
  accept unless a later instruction explicitly authorizes those actions.
- Stop only the blocked portion for a material source-of-truth contradiction,
  security/privacy impossibility, unavailable required dependency/license, gate
  bypass or appearance of real data/secrets.
- For a material architecture conflict, create a record from
  `docs/development/ARCHITECTURE_DEVIATION_TEMPLATE.md`; do not silently change a
  higher-authority contract. Continue unaffected work safely.

## Final report and state boundary

Create `docs/development/reports/E07.md` from
`docs/development/EPIC_REPORT_TEMPLATE.md`. Record only implemented behavior,
key files, exact deterministic and provider-evaluation results, named blockers/
limitations and deviations—never chain-of-thought or sensitive content.

If all implementation criteria and local validation pass, set only
`current_epic.status` in `docs/development/STATE.yaml` to `IMPLEMENTED` and set
`implementation_status` to `IMPLEMENTED`. For a material blocker set both to
`BLOCKED`. Do not set `ACCEPTED`, append `accepted_epics`, advance E08 or commit;
those happen after the mandatory independent focused review and explicit
acceptance.

End with a concise summary, changed areas, exact validation results, material
limitations, review requirement and recommended next state.
