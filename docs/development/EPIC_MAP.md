# PSYCHE OS implementation epic map

**Planning basis:** `docs/ROADMAP.md`, snapshot 2026-08-10
**Plan:** 7 milestones, 12 epics
**Risk distribution:** 8 × `RISK-H`, 4 × `RISK-M`, 0 × `RISK-L`
**Mandatory Codex checkpoints:** 8, one for each `RISK-H` epic
**Current:** `E00 IMPLEMENTED / FIX_REQUIRED` under the approved minimal rebaseline; all later epics are `PLANNED` and prepared just in time

This is a capability map, not a release calendar. A later epic can be narrowed, deferred, or rejected when its entry evidence is unfavorable. No epic authorizes real data while `docs/architecture/REAL_DATA_GATE.yaml` is `CLOSED`.

## Milestone map

| Milestone | Roadmap basis | Epics | Exit outcome |
|---|---|---|---|
| M0 — Secure synthetic foundation | Phases 1–2 | E00–E01 | Irreversible semantics accepted in E00; deferred recovery/file controls completed and independently attacked in E01 |
| M1 — Evidence-centered local experience | Phase 3 | E02–E03 | Safe desktop boundary and usable evidence/archive workflows without cloud or LLM |
| M2 — Governed measurement and personal science | Phase 4 | E04–E06 | Rights-gated measurement, honest descriptive analysis, and bounded low-risk N-of-1 |
| M3 — Optional bounded AI | Phase 5 | E07 | One replaceable proposal-only AI task proves value without canonical authority or relationship |
| M4 — Selective imports and retrieval | Phase 6 | E08–E09 | One hostile-content-safe importer and disposable local projections |
| M5 — Conditional professional interchange | Phase 7 | E10 | User-controlled, audience-bounded report/export only if governance evidence supports it |
| M6 — Lifetime operations and gate decision | Phase 8 | E11 | Repeatable preservation/release process and explicit profile-specific gate decision package |

## Review matrix

| Boundary | Epic | Why Codex is mandatory |
|---|---|---|
| Secure core, keys, deletion, time/provenance | E00 | A retrofit failure could corrupt meaning or expose every future record |
| Independent recovery/assurance evidence | E01 | A green self-test is not independent recovery/security evidence |
| Desktop webview/typed IPC trust boundary | E02 | It adds a renderer/process boundary adjacent to vault paths and keys |
| Causal/N-of-1 and intervention limits | E06 | Statistical overclaim or unsafe action selection has consequential impact |
| Provider, `NEVER_CLOUD`, LLM write, safety | E07 | It adds a network/model boundary and mental-health interaction risk |
| Untrusted importer/parser boundary | E08 | Hostile content can attack parsers, policy, provenance, and deletion |
| Professional/clinician interchange | E10 | Intended use, disclosure, and regulatory interpretation materially change |
| Lifetime release and real-data decision | E11 | Gate evidence and residual risks require a focused final challenge |

E03, E04, E05, and E09 use objective `EPIC` gates and DeepSeek self-review without a second model by default. Any material architecture deviation or actual crossing into a high-risk boundary escalates before acceptance.

## E00 — Minimal Irreversible Secure Core

**Goal:** Implement the smallest local Python/CLI synthetic-only core whose canonical semantics, minimal migrations, write isolation and acceptance truthfulness are unsafe or expensive to retrofit.
**Why now:** Later features depend on trustworthy canonical meaning and a storage boundary that cannot admit arbitrary content while the gate is closed; production recovery and filesystem capabilities can remain disabled until E01.
**Dependencies:** Research convergence; frozen v2 documents; `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`; target OS/dependency feasibility.
**Major deliverables:** Locked Python package/toolchain; pure domain/temporal/provenance/policy layers; SQLCipher-gated encrypted store and key wraps; canonical versioning/deletion; minimal transactional migrations; open logical export; package-owned bundled-fixture loader with direct writes denied; truthful scoped validators; explicit unavailable states for deferred backup/restore, blob writes and affected filesystem mutations.
**Out of scope:** Real/arbitrary user input, UI/server/network/LLM/imports, assessments/scoring, analytics, interventions, FHIR, graph/vector engines, sync or sharing.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-02–C-15, C-18–C-20.
**Primary source documents:** Constitution; Master Spec §§6, 9, 16, 19–20 and IC-1–IC-8; Data Model; System Architecture; Privacy/Security Model; Threat Model; ADR-002–ADR-010, ADR-017, ADR-020; original F0 contract.
**Acceptance criteria:** Every invariant and command in `docs/development/E00_REBASELINE_DECISION.md` passes; F01/F03/F04/F06 and corrected versioning do not regress; minimal migrations are atomic; only the verified bundled-fixture path can mutate content; validators cannot certify fake evidence; deferred features are unavailable and explicitly `DEFERRED/NOT_READY`; no real/arbitrary input or production-readiness claim; gate still `CLOSED`.
**Validation level:** Targeted tests during construction, then the single bounded four-command rebaselined E00 gate. Deferred feature readiness, broad audit and unrelated static-analysis cleanup are excluded.
**Codex review required:** yes, focused only on the frozen E00 invariants, feature unavailability and evidence honesty.
**REAL_DATA_GATE impact:** Produces synthetic foundation evidence only. Backup/restore, blobs, Windows mutation and release-grade SBOM evidence remain unsatisfied and prevent gate opening.
**Estimated implementation complexity:** `XL`; prompt/context cost `HIGH`.

## E01 — Synthetic Assurance and Independent Recovery Proof

**Goal:** Complete the named pre-real-data recovery/file controls, attack the exact E00 build, and assemble reproducible independent evidence for recovery, deletion, privacy, and long-horizon durability.
**Why now:** A foundation implementer cannot independently validate its own key/recovery/deletion design; feature work must not outrun Phase 2 assurance.
**Dependencies:** E00 `ACCEPTED`; exact build/profile, F0 report, threat matrix, frozen lock/SBOM, stable executable commands.
**Major deliverables:** Correct authenticated backup inventory and atomic isolated restore; completed or still-disabled vault-bound blob lifecycle; handle-bound Windows mutation with runtime evidence; independent threat/crypto integration/privacy-deletion reviews; clean-device recovery drill; hostile backup/rollback/corruption and failure campaigns; 1/5/20/40-year synthetic migration/archive simulations; synthetic recovery/deletion usability evidence; consolidated gate evidence package.
**Out of scope:** New product features, real data, weakening F0 controls to make tests pass, automatic gate opening.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-10–C-14, C-19–C-20.
**Primary source documents:** Roadmap Phase 2; Privacy/Security Model PS-17–PS-26; Threat Model; Real Data Gate; F0 report and accepted E00 diff.
**Acceptance criteria:** F02 and F09 are closed on the exact enabled profile; blob I/O is either closed or remains excluded from that profile; clean recovery works with independent material; deletion/rebuild and plaintext scans pass; fault/migration/archive exercises are reproducible; residual risks and failures are explicit; independent roles are genuine; no Critical/High remains unresolved for an enabled reviewed capability.
**Validation level:** `FULL`, independent reruns and adversarial/fault suites.
**Codex review required:** yes, to validate evidence coverage and prevent unsupported security/gate claims; it does not replace required human expertise.
**REAL_DATA_GATE impact:** May satisfy RDG-01–RDG-07, RDG-09, RDG-10, and RDG-12 for one exact profile if their evidence requirements truly pass; RDG-11 and signed opening remain separate, so status stays `CLOSED` absent an explicit decision.
**Estimated implementation complexity:** `L`; prompt/context cost `HIGH`.

## E02 — Secure Desktop Shell and Vault Operations UX

**Goal:** Deliver a local, accessible desktop vertical slice for unlock, privacy status, correction/deletion, backup health, isolated recovery, and export through a narrow typed IPC boundary.
**Why now:** After secure-core assurance, the highest-value user step is making recovery and control usable before adding content-heavy features.
**Dependencies:** E01 `ACCEPTED`; accepted IPC/webview choice or explicit deviation decision; stable application ports and CLI/domain contracts.
**Major deliverables:** Restrictive local shell; typed allowlisted IPC/view models; no direct renderer vault/key access; privacy center; deletion plan/receipt flow; backup/recovery wizard; accessible synthetic UX tests and security configuration.
**Out of scope:** Chat persona, cloud/network, broad capture, model/AI, analytics, import parsers, real data.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-01, C-10–C-14, C-17, C-19–C-20.
**Primary source documents:** System Architecture §§4–6, 8–9, 11–12; Privacy/Security Model; Threat Model future webview/IPC boundary; Master Spec §§16, 20–22; ADR-003, ADR-009, ADR-010, ADR-018.
**Acceptance criteria:** Renderer cannot read vault paths/keys or invoke untyped commands; restrictive CSP/encoding and dependency review pass; all state-changing flows go through application/policy ports; synthetic users can delete, export, and recover without misleading promises; core remains usable without a network.
**Validation level:** `FULL` for IPC/renderer and recovery/deletion paths, plus focused accessibility/usability tests.
**Codex review required:** yes, focused on the new trust boundary and preservation of core controls.
**REAL_DATA_GATE impact:** Can provide part of RDG-08 and RDG-12 evidence; adding a webview is a regression trigger and does not open the gate.
**Estimated implementation complexity:** `L`; prompt/context cost `HIGH`.

## E03 — Evidence Archive, Timeline, and Epistemic Explorer

**Goal:** Let a user create synthetic evidence through typed capture, navigate fuzzy/multi-clock time, and distinguish sources, reports, claims, uncertainty, contradictions, unknowns, and model-snapshot changes.
**Why now:** This is the product's core non-chat value and reuses accepted canonical semantics without adding a new external trust boundary.
**Dependencies:** E02 `ACCEPTED`; stable capture/application APIs and desktop shell.
**Major deliverables:** Synthetic capture/inbox; source locator/view; fuzzy timeline; evidence/claim/contradiction/unknown explorers; snapshot diff; correction and dependency-aware deletion UX; no-dark-pattern/accessibility behavior.
**Out of scope:** AI-generated interpretation, diagnosis, causal insights, real imports, measurement instruments, cloud or real data.
**Risk level:** `RISK-M`; escalate if canonical temporal/provenance/deletion semantics change.
**Constitutional invariants touched:** C-01–C-04, C-08–C-09, C-14, C-17, C-20.
**Primary source documents:** Master Spec §§6, 8–9, 19, 21; Data Model §§3–7, 12–13; System Architecture capture/correction/deletion workflows; ADR-004, ADR-005, ADR-009, ADR-018.
**Acceptance criteria:** Representative synthetic tasks preserve source/derived separation, fuzzy time, uncertainty, contradictions, correction history, and deletion closure; UI never labels proposal as evidence/fact; months-away return has no penalty/engagement pressure.
**Validation level:** `EPIC`: targeted domain/view-model and integration tests, synthetic task suite, lint/typecheck, migration check if schema changes.
**Codex review required:** no by default.
**REAL_DATA_GATE impact:** May strengthen RDG-04/RDG-12 usability evidence but cannot change gate status.
**Estimated implementation complexity:** `L`; prompt/context cost `MEDIUM`.

## E04 — Rights-Gated Assessment Vertical Slice

**Goal:** Implement the deny-by-default assessment registry and at most one legally usable, scientifically approved deterministic instrument vertical slice.
**Why now:** Measurement must enter through rights/version/validity gates, not an uncontrolled universal battery.
**Dependencies:** E03 `ACCEPTED`; exact instrument/version/language/mode rights and governance decision available; otherwise deliver metadata-only/blocked registry behavior.
**Major deliverables:** P0–P7 registry states; rights matrix; versioned administration/response/score records; deterministic scorer with known-answer vectors only when all gates pass; display of mode/norm/error/interpretation limits.
**Out of scope:** Proprietary content without rights, LLM scoring/translation, diagnosis/treatment, universal battery, automatic adaptive testing, invented norms/cutoffs.
**Risk level:** `RISK-M`; a clinical/rights expansion or unsafe interpretation escalates.
**Constitutional invariants touched:** C-02, C-05, C-08, C-18, C-20.
**Primary source documents:** Scientific Governance §§2, 6, 8–9, 12–13; Master Spec §10; Data Model §8; ADR-012; ontology registry.
**Acceptance criteria:** Unresolved rights/version/language evidence fails closed; no protected test text enters Git/log/prompt; scoring is exact, deterministic, version-pinned, and independently rerunnable; output clearly separates score, error, norm/cutoff status, screening, and diagnosis.
**Validation level:** `EPIC`: rights-denial tests, known-answer/edge/missing-data tests, integration and migration checks.
**Codex review required:** no by default; mandatory qualified rights/scientific/psychometric review is not delegated to a second coding model.
**REAL_DATA_GATE impact:** No direct opening condition; may contribute to RDG-09/RDG-11 evidence for this optional capability and never authorizes real responses while closed.
**Estimated implementation complexity:** `L`; prompt/context cost `MEDIUM`.

## E05 — Longitudinal, EMA, Sleep, and Descriptive Analysis

**Goal:** Add bounded repeated measurement and local descriptive analysis that exposes coverage, missingness, reactivity, source type, and uncertainty without causal or clinical claims.
**Why now:** Repeated measurement is useful only after governed definitions and an evidence-centered UX exist.
**Dependencies:** E04 `ACCEPTED`; accepted sampling/measurement schemas; no need for E04 scoring to be enabled if rights remain blocked.
**Major deliverables:** Sampling/burden protocol and stop rules; EMA capture; separate sleep diary/actigraphy/consumer/clinical/inferred source types; confound context; descriptive trends/associations with missingness/reactivity/algorithm-version display.
**Out of scope:** Passive surveillance by default, diagnostic sleep/substance conclusions, causal insight, treatment selection, adaptive battery, N-of-1 intervention execution.
**Risk level:** `RISK-M`.
**Constitutional invariants touched:** C-05–C-08, C-11–C-12, C-17–C-18, C-20.
**Primary source documents:** Master Spec §§11–14.2; Data Model §§4.7, 9; Scientific Governance §§3, 7.3, 8; ADR-013; measurement workstream through the source registry.
**Acceptance criteria:** Cadence/burden/decline/missing states are explicit; sleep and context sources never collapse into clinical facts; outputs disclose window/coverage/missingness/reactivity and stay at C0–C3 language; version changes do not silently compare incomparable series.
**Validation level:** `EPIC`: deterministic simulation/known-answer tests, missingness/reactivity edge cases, integration and migration checks.
**Codex review required:** no by default.
**REAL_DATA_GATE impact:** No direct opening condition; only synthetic fixtures while closed.
**Estimated implementation complexity:** `L`; prompt/context cost `MEDIUM`.

## E06 — Bounded N-of-1 and Intervention Protocols

**Goal:** Implement preregistered low-risk N-of-1 protocols and an allowlisted intervention registry with enforceable causal-language and action-risk ceilings.
**Why now:** It builds on honest longitudinal data and is the first point where an analysis might influence action.
**Dependencies:** E05 `ACCEPTED`; approved scientific method and intervention records; qualified review for any R2 scope.
**Major deliverables:** D0–D4 design and R0–R3 action gates; preregistration/estimand/assumptions; randomization and carryover/missingness handling; stop/adverse-event rules; C0–C6 claim resolver; low-risk protocol builder and reproducible report.
**Out of scope:** Medication/dose/substance changes, dangerous sleep/food restriction, trauma exposure, self-harm, autonomous R2/R3 recommendations, universal causal life stories.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-02, C-05–C-09, C-17–C-18, C-20.
**Primary source documents:** Scientific Governance §§7–9, 13; Master Spec §14; Mental Health AI Safety intervention/medical boundaries; ADR-014; measurement research sources.
**Acceptance criteria:** Risk tier cannot be downgraded by model/user text; prohibited actions fail closed; claim language never exceeds design/measurement ceiling; simulation/calibration/sensitivity and stop-rule tests pass; output remains scope/time/person specific and reproducible.
**Validation level:** `FULL`: targeted statistical tests, simulations, property/invariant tests, adverse/stop cases, reproducibility and safety integration.
**Codex review required:** yes, focused on identification assumptions, claim ceiling, action gates, and dangerous edge cases; qualified scientific/clinical reviewers remain required.
**REAL_DATA_GATE impact:** Does not open the gate; adds intended-use evidence obligations under RDG-11 before any future non-synthetic use.
**Estimated implementation complexity:** `XL`; prompt/context cost `HIGH`.

## E07 — One Optional Bounded AI Proposal Slice

**Goal:** Evaluate one narrow opt-in AI task whose structured output remains a replaceable proposal, with per-call disclosure, `NEVER_CLOUD`, provider, prompt-injection, and mental-health safety controls enforced outside the model.
**Why now:** AI is admissible only after the local product is useful without it and deterministic evidence/scientific boundaries exist.
**Dependencies:** E06 `ACCEPTED`; the local product is useful without AI; approved provider/model/config/resource/safety snapshots; a synthetic-evaluation disclosure profile; evidence that the narrow task has evaluable value. Production use with real records remains deferred until a separate exact profile gate decision. If these conditions do not exist, defer E07.
**Major deliverables:** Provider registry/policy snapshot; local disclosure preview/receipt; selected-record context builder; structured proposal schema; evidence-ID and prohibited-claim validation; deterministic safety resolver/response states; provider regression/removal path; one narrow task and adversarial evaluation.
**Out of scope:** Hosted memory/files/vector stores, canonical model writes, autonomous tools/actions, diagnosis/therapy/triage, relationship persona, safety monitoring/rescue claims, arbitrary vault disclosure.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-01–C-02, C-04–C-08, C-10–C-12, C-15–C-18, C-20.
**Primary source documents:** Master Spec §§15, 17; Privacy/Security Model PS-01–PS-03, PS-10–PS-12, PS-15–PS-16, PS-23; Mental Health AI Safety; Scientific Governance claim/LLM contracts; System Architecture optional LLM workflow; ADR-007, ADR-015, ADR-020.
**Acceptance criteria:** No model output becomes evidence/canonical state without explicit typed human action; policy blocks `NEVER_CLOUD` and unknown lineage before context construction; the synthetic evaluation provider sees only previewed allowed fixtures; injection cannot change policy/tools; mandatory safety/adversarial families for the exact profile pass with no unresolved SEV-A/B; provider removal leaves canonical workflows intact; measured synthetic-task value exceeds stated privacy/safety cost. Production enablement stays blocked while the gate is closed.
**Validation level:** `FULL`: privacy lineage properties, provider boundary tests, schema/adversarial/stochastic/model-change regression, safety suite, removal/degraded-mode test.
**Codex review required:** yes, focused on disclosure and canonical-write boundaries, externalized policy, safety behavior, and evidence claims; human clinical/privacy/locale governance remains required.
**REAL_DATA_GATE impact:** A provider/model is a regression trigger. Synthetic implementation can produce candidate evidence for RDG-07, RDG-09, and RDG-11, but no real disclosure is allowed unless a later separate exact profile gate decision authorizes it.
**Estimated implementation complexity:** `XL`; prompt/context cost `HIGH`.

## E08 — Untrusted Import Core and First Bounded Importer

**Goal:** Establish quarantine/parser/provenance/deletion contracts and ship at most one decision-justified bounded format importer using only hostile/synthetic fixtures.
**Why now:** Integrations are deferred until canonical deletion and projection semantics are proven; the first importer establishes the reusable security boundary.
**Dependencies:** E03 `ACCEPTED`; E01 assurance; exact format benefit/owner/rights decision; E07 is not required.
**Major deliverables:** Quarantine/sniffing/resource limits; isolated parser; preview/consent; untrusted-content handling; typed source/provenance mapping; fuzz corpus; redaction and deletion closure; one bounded importer.
**Out of scope:** Automatic URL fetch, credential harvesting, broad email/message/calendar/wearable access, imported instructions as authority, multiple convenience adapters, real files while gate closed.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-03, C-10–C-15, C-18–C-20.
**Primary source documents:** Master Spec §§16.4, 19–20; System Architecture import workflow/module; Privacy/Security Model PS-13–PS-16; Threat Model; ADR-016; Roadmap Phase 6.
**Acceptance criteria:** Hostile content cannot change policy or execute tools; parser failures/timeouts/oversize inputs contain damage and content-free logs; provenance and exact source locator survive; correction/deletion closes all imported derivatives; fuzz and malformed-package cases pass; format rights and maintenance owner are documented.
**Validation level:** `FULL`: sandbox/resource/fuzz/adversarial, provenance, deletion, migration and leakage tests.
**Codex review required:** yes for the import core and first parser boundary; later small adapters default to `RISK-M` if they reuse it unchanged.
**REAL_DATA_GATE impact:** Can satisfy/revalidate RDG-08 and affected RDG-04/RDG-06/RDG-09 for the exact enabled importer; importer addition is a regression trigger and does not open the gate.
**Estimated implementation complexity:** `L`; prompt/context cost `HIGH`.

## E09 — Rebuildable Projections and Local Retrieval

**Goal:** Add only the local retrieval/projection capability justified by synthetic user tasks, with deterministic manifests, invalidation, rebuild, and no canonical authority.
**Why now:** Search/graph/analytics acceleration is safe only after canonical semantics and importer invalidation are proven.
**Dependencies:** E08 `ACCEPTED`; measured retrieval need; accepted canonical query baseline.
**Major deliverables:** Projection manifest/version/digest; deterministic build/rebuild; invalidation on correction/deletion/policy change; one minimal local retrieval surface; graceful no-projection fallback.
**Out of scope:** Graph/vector/full-text/columnar engines without measured need, embeddings sent to cloud, projection-only facts, opaque provider memory.
**Risk level:** `RISK-M`; escalate if adding embeddings, external service, or canonical semantics.
**Constitutional invariants touched:** C-02–C-03, C-08–C-14, C-19–C-20.
**Primary source documents:** Master Spec §§9.2, 19–20; Data Model §13; System Architecture projection boundary; Privacy/Security Model lineage/deletion; ADR-002, ADR-004, ADR-009.
**Acceptance criteria:** Projection can be deleted/rebuilt from canonical records; stale/deleted/policy-blocked content disappears deterministically; manifest names all inputs/code/config; failure does not prevent canonical access/export; no projection becomes evidence or canonical truth.
**Validation level:** `EPIC`: known-answer build/rebuild, invalidation/deletion, migration and degraded-mode integration tests.
**Codex review required:** no by default.
**REAL_DATA_GATE impact:** Can strengthen RDG-04/RDG-06 evidence for the exact projection; does not change status.
**Estimated implementation complexity:** `M`; prompt/context cost `MEDIUM`.

## E10 — User-Controlled Professional Report and Interchange

**Goal:** Conditionally deliver an audience-specific, redacted, provenance-rich report/export without autonomous clinical decision support or shared-vault authority.
**Why now:** Professional collaboration changes intended use and is admissible only after evidence, privacy, export, and user-control workflows are mature.
**Dependencies:** E09 `ACCEPTED`; explicit intended-use, legal/regulatory, privacy, rights, clinical-safety, liability, and human-factors decisions. If unfavorable, reject/defer this epic.
**Major deliverables:** Audience/purpose policy; user-selected evidence and redaction preview; report with source/uncertainty/contradiction drill-down; disclosure receipt; optional bounded mapping only if separately approved; clinician annotations as attributed imports if supported.
**Out of scope:** Clinician portal/shared vault, diagnosis/treatment recommendation, background sharing, automatic FHIR/EHR integration, professional access inherited from local approval.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-01–C-12, C-14–C-20.
**Primary source documents:** Master Spec §§15, 21.1, 23; Roadmap Phase 7; Privacy/Security Model disclosure/import/export controls; Mental Health AI Safety intended-use/human-governance sections; Scientific Governance; ADR-010, ADR-015, ADR-019.
**Acceptance criteria:** User explicitly chooses audience/purpose/records and previews redaction; report preserves provenance/time/uncertainty and no diagnostic authority; receipt/deletion/external-copy limits are clear; no background access; required professional/legal/privacy/rights evidence is recorded for the exact profile.
**Validation level:** `FULL`: disclosure-policy properties, redaction/leakage, export round-trip, deletion/receipt, accessibility/human-factors and hostile annotation tests as applicable.
**Codex review required:** yes, focused on intended-use expansion, disclosure, clinical-claim boundary, and external-copy semantics; required human approvals are separate.
**REAL_DATA_GATE impact:** May contribute to RDG-05, RDG-08, and RDG-11 for a separately reviewed professional profile; clinician workflow is a regression trigger and never inherits another profile's opening.
**Estimated implementation complexity:** `L`; prompt/context cost `HIGH`.

## E11 — Lifetime Operations, Release Evidence, and Gate Decision

**Goal:** Make release, migration, preservation, dependency/currentness review, incident closure, and profile-specific real-data decisions repeatable over 1/5/20/40-year horizons.
**Why now:** Lifetime reliability is recurring work, but the first complete release/gate package must integrate evidence from every enabled boundary.
**Dependencies:** All capabilities intended for the candidate profile `ACCEPTED`; exact build/SBOM/evidence; independent reviews; no unresolved Critical/High. Optional rejected/deferred epics need not be implemented.
**Major deliverables:** Release manifest and reproducible gates; exact dependency/SBOM/license/build-provenance reconciliation including negative evidence cases; preservation/migration/recovery drill; source/license/security currentness checks; incident disable/rollback evidence; residual-risk/expiry register; machine-readable gate evidence and explicit signed decision package.
**Out of scope:** Automatic gate opening, marketing security/clinical claims, feature accumulation, hiding failed/expired evidence, real-data ingestion inside the gate-review task.
**Risk level:** `RISK-H`.
**Constitutional invariants touched:** C-01–C-20.
**Primary source documents:** Roadmap Phase 8; Real Data Gate; Master Spec §§20, 22–25; Privacy/Security Model PS-22–PS-26; Threat Model; Scientific Governance update/review; Mental Health AI Safety release/incident sections; Decision Log.
**Acceptance criteria:** Exact build/profile and all enabled trust boundaries are named; required RDG evidence is current and independently reviewed; expiry/regression triggers and rollback/disable paths work; residual risks are explicit; decision record is signed by authorized roles. If any requirement fails, status remains `CLOSED` without workaround.
**Validation level:** `FULL / RELEASE`, including a clean independent rerun of all affected gates and evidence-path validation.
**Codex review required:** yes, focused final review of evidence completeness, contradictions, claims, and gate logic; Codex cannot sign for required independent human authorities.
**REAL_DATA_GATE impact:** This is the only planned epic that may prepare an explicit profile-specific open/keep-closed decision. Opening is never automatic and is not authorized by this map.
**Estimated implementation complexity:** `L`; prompt/context cost `HIGH`.

## Just-in-time rule

Only E00 has a materialized implementation prompt. E01 is deliberately `PLANNED`: its exact commands, target profile, independent review inputs, and evidence gaps depend on the accepted E00 implementation. Prepare it after E00 acceptance with `docs/prompts/codex/PREPARE_NEXT_EPIC.md`. Apply the same rule to E02–E11 so prompts describe the actual accepted code rather than a stale imagined repository.
