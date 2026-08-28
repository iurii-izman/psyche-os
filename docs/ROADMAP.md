# PSYCHE OS product roadmap

**Product reorientation:** 2026-08-28
**Planning unit:** evidence gates, not calendar promises  
**Current state:** E00–E11 foundation work and Personal Mode v1 are accepted and merged; `REAL_DATA_GATE = CLOSED` and no real data is admitted.

## Current product center

PSYCHE OS is becoming an **AI-led Personal Inquiry & Evidence System**. The local Evidence OS remains the trusted memory, provenance and epistemic-control layer beneath that experience. It must remain useful for capture, evidence inspection, correction, search, export, deletion, recovery and local analysis without an AI or provider.

The future Daily Use loop is: open PSYCHE → identify a worthwhile inquiry → start or continue an AI interview → one primary question at a time → evidence-informed exploration and revision → hypotheses, contradictions, unknowns, coverage and inquiry backlog evolve → later, bounded low-risk experiment/recommendation and observed outcome refine the model.

AI may lead the **inquiry process**, but never determines truth about the owner, changes policy, or turns derived output into evidence. The owner can answer, skip, decline, change direction, correct, challenge, continue or stop at any time.

## Current product verticals

1. **AI Interview V1 — next implementation boundary.** PSYCHE leads a consented, evidence-grounded, one-question-at-a-time personal inquiry with inspectable rationale, disclosure and continuity. Its architecture contract is `docs/architecture/AI_INTERVIEW_V1.md`.
2. **Personal Model V1.** “Картина” becomes an inspectable, correctable view of support, hypotheses, competing explanations, contradictions, unknowns, contexts, temporal relevance and next inquiry directions.
3. **Inquiry → Change V1.** Supported understanding can later yield bounded, low-risk behavior/observation experiments and outcome tracking; existing causal and safety gates remain controlling.
4. **Connected Evidence V1.** Owner-enabled local sources such as sleep, calendar, tasks or habits may later inform inquiry only through separately justified, local evidence boundaries.
5. **Proactive PSYCHE V1.** Local between-session logic may later surface a useful reason to return; cloud AI still requires an explicit session launch and never runs in the background.

Quick Capture, manual Reflection, History, Search, Context Pack, direct evidence inspection, privacy/recovery/export and the current one-shot Working Formulation remain useful supporting capabilities. They are not being removed.

## Explicitly deferred

Do not implement now: AI-generated microtests, governed standardized questionnaires, richer clinical/scientific reference integration, richer third-party relationship modeling, automatic broad temporal re-evaluation, advanced intervention/evaluation, cloud background AI, generic autonomous agents, or whole-vault cloud retrieval.

## Roadmap principles

- A phase starts only when its entry evidence exists and ends only when exit tests pass.
- Real personal data is not a convenient way to test the vault.
- Provider, UI and integration features do not outrun canonical data, privacy, recovery and deletion.
- A new trust boundary—cloud, sync, sharing, clinician, mobile, public distribution—requires a new threat-model/gate decision.
- Research questions remain research questions; implementation volume is not evidence.

## Phase R — Research foundation (complete)

**Outcome:** v1 audited; independent rebuild and three architecture comparison complete; scientific, measurement, safety, privacy/security, regulatory, UX and lifetime evidence synthesized; constitutional/data/security contracts frozen for the next implementation step.

**Exit evidence:** all required research artifacts exist and validate, 153 unique serious sources are registered, four adversarial passes are documented, and the F0 prompt is exact. `RESEARCH_CONVERGED = true` does not open the data gate.

## Completed foundation

The E00–E11 sequence is complete and retained below as historical product strategy and capability context, not an active implementation queue. Material Personal/infrastructure debt is closed. The control plane is stable and exception-only.

## Product development now

The next bounded product increment is **AI Interview V1**. Define its implementation Task Contract from the current master successor and architecture contract, use the product-default delivery lane, and keep `REAL_DATA_GATE = CLOSED`.

## Historical foundation and conditional capability map

### Phase 1 — Minimal irreversible secure core

**Purpose:** prove the semantics that are impossible or costly to retrofit before sensitive bytes exist.

**Build only:**

- Python 3.12+ local domain/storage CLI with no network listener;
- opaque IDs, version rows and multi-clock/fuzzy temporal values;
- raw/verbatim versus normalized/derived records;
- provenance/derivation, claims/evidence/uncertainty/contradiction/unknown;
- orthogonal data policy and `NEVER_CLOUD` lineage engine;
- fail-closed encrypted database/key envelope profile with OS wrap and independent recovery wrap;
- content-free audit, hard deletion dependency traversal;
- minimal transactional schema migrations and open logical export manifests;
- package-owned synthetic-fixture loading with ordinary storage writes denied;
- explicit unavailable states for deferred backup/restore, blob writes and affected filesystem mutation;
- synthetic fixtures and adversarial/failure tests.

**Explicit exclusions:** LLM/provider calls, desktop/web UI, real data, assessment item content, clinical diagnosis, graph/vector engine, wearables/messages/calendar, FHIR, interventions, sync/sharing.

**Exit gate:** the six frozen invariants and four-command gate in
`docs/development/E00_REBASELINE_DECISION.md` pass. An unresolved High in a
disabled future capability does not block this synthetic profile, but that
capability must be unavailable and remains a blocker for its owning profile and
the real-data gate. The gate remains closed through Phase 2 and until a later
explicit signed decision.

## Phase 2 — Synthetic assurance and recovery proof

**Purpose:** attack the foundation before trusting it.

**Activities:**

- complete and then independently attack authenticated backup inventory and
  clean atomic isolated restore;
- complete or continue to exclude the vault-bound blob lifecycle for the exact
  candidate profile;
- close Windows handle/reparse/TOCTOU filesystem mutation on the exact supported
  profile before enabling affected file operations;
- fault injection: full disk, interrupted commit/migration/rotation/deletion;
- hostile import skeleton tests without broad format support;
- arbitrary derivation-policy DAG property tests;
- plaintext scans across database, WAL/temp, blobs, projections, logs and packages;
- old-schema migration and export round trips;
- clean-device recovery with only the independent recovery materials;
- backup corruption/rollback/poisoning exercises;
- synthetic 1/5/20/40-year archive growth/migration simulations;
- independent threat-model, cryptographic integration and privacy/deletion review;
- recovery and deletion usability test using synthetic content.

**Exit gate:** all E01-assigned `PRE_REAL_DATA` findings are fixed or the affected
profile remains disabled; evidence names exact build, platform, tests, reviewers
and residual risks. E01 cannot open `REAL_DATA_GATE`; E11 prepares the only
planned explicit profile-specific decision package.

## Phase 3 — Evidence-centered local experience

**Purpose:** make the safe core usable without creating a chat dependency.

**Deliverables:** typed desktop IPC/shell after separate webview review; capture/inbox; timeline with fuzzy dates; evidence/claim/contradiction/unknown explorers; model-snapshot diffs; privacy center; correction/deletion; backup health/recovery wizard; human-readable export. No cloud or LLM required.

**Evaluation:** representative synthetic tasks must let users find a source, distinguish report from interpretation, correct a claim, understand uncertainty, delete a source and derivatives, recover from backup, and leave for months without penalty. Accessibility/localization and no-dark-pattern review are exit criteria.

## Phase 4 — Governed measurement and local analysis

**Purpose:** add scientifically controlled functions that can remain deterministic/local.

**Deliverables:** assessment registry and rights gate; one or a very small number of legally usable instruments; known-answer scoring; version/language/mode/norm/measurement-error display; sampling/burden protocol; sleep source separation; descriptive longitudinal analysis with missingness/reactivity; preregistered N-of-1 protocol builder for low-risk behavioral questions only.

**Exclusions until evidenced:** universal battery, automatic adaptive testing, unlicensed translations/items, diagnosis, causal “insights,” treatment selection, medication or high-risk interventions.

**Exit gate:** instrument-specific rights and validation; deterministic scoring tests; repeated-measurement and burden evaluation; statistical simulation/calibration; clinical/safety review of interpretation language.

## Phase 5 — Optional bounded AI proposals

**Purpose:** test whether a replaceable model adds value without becoming evidence, authority or relationship.

**Entry:** local product is useful without AI; provider registry/policy snapshot exists; data gate is profile-specific; safety suite and cloud privacy review approved.

**Deliverables:** one narrow opt-in task such as proposing tags/questions from user-selected cloud-eligible synthetic/local records; per-call disclosure preview/receipt; structured proposal schema; evidence-ID validation; no hosted memory/files/vector store; provider/model regression harness; relationship/crisis/delusion/reassurance/false-memory/adversarial tests.

**Exit gate:** value exceeds privacy/safety cost in blinded task evaluation; `NEVER_CLOUD` property tests and prompt-injection impact controls pass; provider removal leaves all canonical functions intact. Failure disables the adapter without blocking the roadmap.

## Phase 6 — Selective imports and projections

**Purpose:** expand retrieval only where maintenance and privacy cost are justified.

Each importer (for example Markdown/PDF/image export) is a separate release unit with format rights, quarantine/parser sandbox, fuzz corpus, resource limits, provenance mapping, redaction and deletion closure. Graph/vector/full-text/columnar engines remain projections with build manifests and deterministic invalidation.

Messages, email, calendar, browsers, wearables and continuous passive sensing stay deferred until a decision-specific benefit, consent/third-party model, importer maintenance owner and security evidence exist. Ambient audio, keystroke collection, covert location, credential harvesting and broad surveillance are rejected.

## Phase 7 — Interoperability and professional collaboration (conditional)

**Purpose:** support a user-controlled, redacted clinician report or open archival interchange—not autonomous clinical decision support.

Potential scope: audience-specific report; source/evidence drill-down; optional FHIR mapping; export provenance; clinician annotations imported as attributed sources. Required first: intended-use and medical-device/privacy/legal qualification, third-party/clinician access model, localized safety resources, professional governance, liability and human-factors review.

No clinician portal, shared vault or diagnostic recommendation inherits local-profile approval. If the evidence/cost is unfavorable, this phase is not built.

## Phase 8 — Lifetime maintenance, not feature accumulation

Recurring work:

- quarterly during active development: provider/model/safety/current-law watch;
- at every release: schema/export/migration/deletion/restore and dependency/SBOM gates;
- annually: preservation formats, recovery drill, ontology/instrument/license and threat-model review;
- on source correction/retraction: knowledge impact and explicit reanalysis proposal;
- on platform cryptographic deprecation: staged migration with old-reader/recovery proof;
- on any incident: affected profile gate closes until reviewed.

Success is a smaller trustworthy system that remains interpretable and exit-friendly, not a growing count of integrations or a “complete” ontology.

## Deferred and rejected backlog

### Deferred pending evidence

- rich desktop visualization and graph layout;
- local embeddings and advanced search;
- provider adapters beyond one evaluated narrow use;
- FHIR/clinician exchange;
- additional assessment instruments/translations;
- passive sensing and wearable algorithms;
- higher-risk N-of-1/intervention categories;
- multi-device sync, mobile and sharing.

### Rejected under the current constitution

- autonomous therapist, diagnostician, crisis monitor or treatment recommender;
- relationship/companion persona, exclusivity or engagement optimization;
- recovered-memory generation or leading trauma reconstruction;
- one universal “mental health”, p-factor, flourishing or identity score;
- full event-sourced content log and immutable retention that defeats deletion;
- graph/vector/model/provider as canonical truth;
- public plaintext hashes/content-addressed filenames for sensitive artefacts;
- surveillance by default and shame/streak mechanics;
- real data before gates pass.
