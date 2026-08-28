# PSYCHE OS Master Specification v2.1 — Product Reorientation

**Product category:** AI-led Personal Inquiry & Evidence System
**Specification version:** 2.1.0-product-reorientation
**Effective:** 2026-08-28
**Authority:** current product, roadmap and AI-interaction source of truth
**REAL_DATA_GATE:** `CLOSED`
**Development data:** synthetic fixtures only

## 1. Authority and scope

This is the current successor to `PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md` for product center, Daily Use experience, LLM role, UI priority, roadmap and the next implementation boundary. ADR-025 records the decision and `docs/architecture/AI_INTERVIEW_V1.md` freezes the justified architecture for that next boundary.

The v2.0 specification remains the retained foundation for its constitutional, scientific, epistemic, privacy, security, storage, recovery, deletion, temporal, provenance and provider-independence contracts. Nothing in this successor weakens those contracts. On a conflict about product direction or AI Interview, this successor wins; on a conflict about an invariant or foundational semantic, `CONSTITUTION.md` wins.

This document authorizes no feature implementation, database migration, provider integration, network exposure, production dependency, real-data admission or change to cryptographic/key behavior. A later bounded Task Contract must authorize AI Interview V1 implementation.

## 2. Product center

PSYCHE OS is primarily an **AI-led Personal Inquiry & Evidence System**. The AI is intended to lead an inquiry process over months and years; the Evidence OS is the trusted local memory, provenance system and epistemic-control layer beneath it.

The product is not an opaque AI memory/profile blob, generic companion, therapist persona, psychiatrist, diagnostic agent, archive/control panel, or engagement machine. Its owner model stays reconstructable from typed, versioned, provenance-aware local state.

The AI may autonomously lead **process**: select a useful inquiry direction, ask one primary question at a time, request concrete episodes, deepen or switch a line, revisit evidence, notice contradictions, challenge weak explanations, keep competing hypotheses, explore coverage gaps, maintain inquiry continuity/backlog, and recommend an end when information value falls.

The AI has no authority over truth about the owner. Its interpretations are defeasible by new evidence. It may not determine values, permissions, policy, privacy class, clinical truth, diagnosis, cause, or required action; it may not fabricate evidence, silently change canonical truth, or create dependency-oriented behavior. The owner may answer, skip, decline, change direction, correct the record, challenge the AI, continue after an end recommendation, or stop the session.

## 3. Daily Use loop and epistemic model

The intended long-term loop is:

`SOURCE → evidence/provenance → observations/assertions → hypotheses / contradictions / unknowns → long-term inquiry state → bounded local retrieval → AI interview → new USER source → model revision → later recommendation/experiment → observed outcome → model revision`.

The following distinctions remain explicit and reconstructable:

- source is not observation, assertion, interpretation, hypothesis, recommendation or outcome;
- raw/verbatim user material is not normalized or derived material;
- a memory report is testimony rather than historical fact;
- state, context and trait are not interchangeable;
- uncertainty, contradiction, correction, supersession, deletion and Unknown remain first-class;
- a derived interpretation or AI output is never evidence merely because it was produced or retained.

The Personal Model ("Картина") is the inspectable current view of what seems supported, what remains hypothesis, competing explanations, contradictions, unknowns, contexts, historical versus currently relevant patterns, correction/supersession, evidence anchors and next inquiry directions. It is not a static personality profile, label list, diagnosis, percent-understood score or opaque summary.

## 4. Product-experience priority

Primary future surfaces, in order, are:

1. AI Interview / Continue Inquiry;
2. evolving Personal Model / "Картина";
3. long-term inquiry continuity;
4. contradictions, unknowns and competing hypotheses;
5. temporal evolution / "Во времени";
6. later, the inquiry → change → outcome loop.

Quick Capture, manual Reflection, History, Search, Context Pack, direct evidence inspection, privacy/recovery/export and the current one-shot Working Formulation remain useful supporting capabilities. Working Formulation is retained as a secondary/manual bounded capability; it may later be absorbed into the inquiry architecture and is not deleted by this decision.

Home should eventually answer: **what is useful for PSYCHE and the owner to investigate or continue now?** It should not primarily function as an archive or control panel.

## 5. Long-term inquiry state

Long-term inquiry state is a first-class, primarily AI-managed architectural/product concept. It supports at least active and recurring themes; underexplored areas/white spots; unresolved contradictions; hypotheses worth testing; questions worth revisiting; reasons for revisit; priority; temporal relevance; evidence links; and continuation between sessions.

It is not a manual task-manager or checklist product. The owner may inspect, correct or dismiss items, but ordinary Daily Use must not require backlog administration. Existing domain ontology may support broad coverage; V1 must not create a giant new psychological ontology.

## 6. AI Interview V1 — next implementation boundary

The next implementation vertical is **Personal AI Interview V1**: PSYCHE itself leads a bounded inquiry while all durable personal meaning remains locally owned and inspectable.

V1 is expected to provide a Personal-UI session start; explicit session-scoped disclosure and consent; bounded local historical selection; one-question-at-a-time adaptive interviewing; accelerated onboarding for thin coverage; evidence-informed themes and gap exploration; visible “Почему этот вопрос?” and “Показать основания”; per-call disclosure inspection; owner overrides; `END_RECOMMENDED` rather than forced closure; a short session summary; derived updates to hypotheses/contradictions/unknowns/backlog; and a next-session direction.

The implementation contract is `docs/architecture/AI_INTERVIEW_V1.md`. It requires a dedicated Personal AI Interview boundary, memory-only runtime consent capability, stateless foreground provider calls, bounded local retrieval, explicit outbound eligibility, provider-profile isolation, source/derived separation, local validation and atomic derived-state commits. It prohibits hosted provider conversation memory, whole-vault cloud RAG, provider files/vector stores/tools/web, background AI, generic autonomous loops and hidden profile state.

V1 may begin with conservative evaluated bounds, but provider context budget is an explicit, evolvable provider-profile/config contract. It is not inherited from the current Working Formulation's 8-turn/20,000-character limits, and it must not follow arbitrary cadence rules such as exploring a coverage gap every N turns.

## 7. Roadmap

The current roadmap is:

1. **AI Interview V1:** PSYCHE leads the inquiry.
2. **Personal Model V1:** PSYCHE increasingly understands the owner in an inspectable, correctable way.
3. **Inquiry → Change V1:** sufficiently supported understanding can produce bounded low-risk action/observation experiments with outcome tracking.
4. **Connected Evidence V1:** owner-enabled local sources such as sleep, calendar, tasks or habits may inform inquiry through separately justified evidence boundaries.
5. **Proactive PSYCHE V1:** local between-session logic may identify a useful reason to return and notify the owner; cloud AI still requires explicit session launch.

Later—not current implementation—are AI-generated microtests, governed standardized questionnaires, richer scientific/clinical reference integration, richer third-party relationship modeling, automatic broad temporal re-evaluation, and an advanced intervention/evaluation engine.

## 8. Enduring local and safety boundaries

Local evidence capture/query/correction/export/delete/recovery remains useful and provider-independent. `NEVER_CLOUD` and all materially reconstructive derivatives remain outside cloud context. Any future AI disclosure is purpose-bound, least-disclosing, inspectable and receipt-based; provider removal or failure cannot prevent canonical local operations.

PSYCHE may be natural, intelligent, direct and evidence-grounded. It may defend a competing interpretation and must revise it when better evidence defeats it. It remains neither a friend substitute nor a clinician, and it does not use anthropomorphic dependency mechanics, safety-monitoring/rescue claims, recovered-memory work, clinical authority or hidden engagement optimization.

`REAL_DATA_GATE` remains `CLOSED`. Development, evaluation and verification use synthetic fixtures only. This product reorientation neither authorizes personal-data disclosure nor makes any OpenAI/provider capability available.

## 9. Current authority route

1. `CONSTITUTION.md` — binding invariants and current product-purpose pointer;
2. this v2.1 successor — current product center, roadmap, AI role and V1 boundary;
3. retained v2.0 master specification and its referenced architecture documents — foundational operational contracts not superseded here;
4. ADR-025 and other accepted entries in `docs/DECISION_LOG.md` — decision history and stated supersession;
5. `docs/ROADMAP.md`, `docs/development/EPIC_MAP.md` and `docs/development/STATE.yaml` — current planning/status routing;
6. a later bounded AI Interview V1 Task Contract — implementation scope.
