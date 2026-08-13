# Post-E11 Conversational Psychological Support North Star

**Status:** forward-compatibility contract; documentation only  
**Horizon:** after E11 and only through separately authorized capability work  
**Owner profile:** one adult owner of one personal vault  
**REAL_DATA_GATE:** `CLOSED`

## Authority and boundary

This document preserves extension points for a future **Personal Psychological Intelligence System**. It does not authorize implementation, real data, clinical use, a therapist persona, or expansion of E07–E11. Authority remains, in order, with `CONSTITUTION.md`, the v2 master specification, accepted decisions and architecture (including `MENTAL_HEALTH_AI_SAFETY.md`), accepted E00–E06 contracts, and the bounded current epic. Where this North Star conflicts with them, they win.

The intended experience is approximately **70% analytical and structured personal intelligence / 30% conversational support and bounded-session experience**. It may eventually combine evidence-grounded sessions, guided interviewing, structured extraction, revisable formulations, longitudinal analysis, governed support skills, risk-bounded recommendation candidates and outcome tracking, user-authorized follow-up, optional cloud AI and voice, professional round trips, and rebuildable analytical views. None is enabled here.

## Frozen future contracts

### 1. Sessions and interaction envelope

Conversation is organized as bounded `Session` / `Turn` state, not one endless transcript. A future session can carry purpose, mode, agenda, context, questions, proposals, recommendations, accepted actions, summary, and follow-up.

AI surfaces should remain compatible with a generic typed `AIInteractionEnvelope` that can reference `interaction_id`, `session_id`, `turn_id`, purpose, skill, `ContextManifest`, provider/model snapshot, policy and knowledge snapshots, claim and action ceilings, disclosure receipt, structured proposal, safety result, and retention policy. An epic may use only the subset it needs, but must not force a later incompatible provider architecture.

### 2. Stateless providers and reproducible context

Provider/model memory is never canonical personal or session memory. PSYCHE OS owns state and selects policy-eligible context for every call; provider replacement must not erase canonical/session meaning.

A versioned `ContextManifest` should be reproducible from relevant evidence, supporting and contradicting evidence, unknowns, model snapshot, measurements, experiments, prior recommendation outcomes, knowledge and policy snapshots, retriever/builder version, and cutoff. Retrieval must remain counterevidence-, contradiction-, and unknown-aware rather than becoming similarity-only confirmation machinery.

### 3. Canonical state, transcript retention, and semantic intake

Raw transcripts are not canonical truth. Future retention modes are `ephemeral`, `selective`, and `full_encrypted`; the preferred default is that an accepted structured result may survive while the raw transcript can be deleted. Structured extraction remains proposal-only until accepted through typed user authority.

Semantic intake maps ordinary language only into existing versioned construct/domain/context/source/time/uncertainty semantics. A model cannot invent canonical ontology fields. Unsupported mappings become `unclassified` / `needs_review`, and verbatim user report stays separate from structured interpretation.

### 4. Working formulations and governed support skills

Reserve a proposal-level, versioned `WorkingFormulation` for one problem: problem, observations, hypotheses, supporting evidence, counterevidence, unknowns, alternatives, protective/context factors, goals, next useful information, and review triggers. It is neither diagnosis, personality truth, nor source evidence, and is not to be persisted or implemented in E07–E11 absent separate authorization.

A future `SupportSkillRegistry` may govern reflection, clarification, summary, alternative exploration, question planning, goal clarification, problem decomposition, decision support, observation proposals, low-risk recommendations, N-of-1 proposals, and professional-question preparation. Each skill may pin intended use, evidence, version, risk, required context, contraindications, claim/action ceiling, and output schema. Architecture must not assume unrestricted LLM-selected psychological techniques. The registry is not implemented now.

### 5. Recommendations, guided self-help, and proactivity

Recommendations are provenance- and risk-bearing candidates, not disposable chat sentences. Preserve compatibility with `candidate` → `accepted` / `rejected` → `tried` → outcome → `useful` / `unclear` / `harmful` / `abandoned` → review. E06 action-risk gates remain authoritative.

Guided self-help is a separate capability profile. Future low-risk nonclinical support requires its own evidence/risk contract; symptom-targeting or clinically directed skills require separate governance and receive no implied authorization from conversation.

Proactivity is user-controlled: the owner explicitly authorizes a follow-up, review, or schedule, and PSYCHE OS later offers that agreed review. Potential triggers include scheduled follow-up, experiment completion, new evidence for a tracked hypothesis, material contradiction, planned periodic review, or knowledge reevaluation. Proactivity never implies attachment, continuous monitoring, crisis detection or rescue, punishment for absence, or engagement optimization.

### 6. Style and relationship boundary

The default future ordering is analytical first, supportive second, Socratic/questioning third, and direct/challenging fourth. Style and presets are configuration, never a relationship or persona claim. Anthropomorphic dependency mechanics remain prohibited.

### 7. Professional round trip and visual analytics

Preserve compatibility with `PSYCHE OS → bounded versioned report → psychologist → attributed comment → safe import → PSYCHE OS`. A professional comment remains an attributed external source, not canonical truth. No clinician portal is implied.

Timelines, heatmaps, context/construct and hypothesis/evidence matrices, contradiction maps, experiment views, snapshot diffs, coverage maps, 2D graphs, and optional experimental 3D maps remain rebuildable projections. They cannot become canonical truth or introduce unsupported personality/health scores.

### 8. Voice and model personalization

Voice is an interface capability by default: speech-to-text and text-to-speech. Inferring psychological state from voice, face, or passive behavior requires a separate scientific/privacy capability profile.

Canonical personal memory must not depend on fine-tuning model weights on the owner's archive. Prefer a replaceable base model plus interaction configuration, knowledge snapshot, retrieved personal context, and PSYCHE-owned session state. Any future fine-tuning is limited to generic skills/style under separate evaluation.

### 9. Evaluation compatibility

Future multi-turn synthetic evaluation must be able to test memory contamination, leading questions, suggestion/false-memory pressure, confirmation bias, counterevidence handling, unsupported claim escalation, unsafe recommendations, dependency/manipulation behavior, provider/model-change regression, and longitudinal consistency. No harness is implemented here; AI calls must preserve enough model/provider/policy/context identity for later replay and evaluation.

### 10. Independent capability gates

E11 and later architecture must permit independent decisions for core real data, cloud AI disclosure, conversational support, proactive follow-up, guided self-help, voice/cloud transcription, and professional interchange. Opening one capability cannot open the others. This requirement does not change `REAL_DATA_GATE` semantics or status.

## E07–E11 forward-compatibility only

| Epic | Compatibility to preserve without expanding scope |
| --- | --- |
| E07 | A typed AI interaction envelope; stateless provider; explicit purpose and context reference; provider/model/policy identity; optional future session/turn identifiers. |
| E08 | Strong source/segment provenance and untrusted-content state sufficient for later attributed professional-comment import and AI-context eligibility. |
| E09 | Reproducible, counterevidence/contradiction/unknown-aware context manifests; projection manifests that do not preclude later rebuildable visual analytics. |
| E10 | Stable report identity, version, audience, and purpose so a future attributed external comment can reference one exact report. |
| E11 | Independent capability/profile decisions plus provider/model/policy regression triggers; no bundled gate opening. |

These are compatibility constraints, not deliverables. Each epic remains bounded by its accepted map, prompt, dependencies, risk, gates, exclusions, and review.
