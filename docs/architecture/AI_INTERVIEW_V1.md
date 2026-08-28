# Personal AI Interview V1 — Architecture Contract

**Status:** accepted product-architecture boundary; implementation is not authorized by this document
**Authority:** `CONSTITUTION.md` → `docs/PSYCHE_OS_MASTER_SPEC_v2.1_PRODUCT_REORIENTATION.md` → ADR-025 → this contract
**REAL_DATA_GATE:** `CLOSED`; synthetic-only development and evaluation
**Scope:** the next bounded implementation vertical, not a production/provider enablement

## 1. Purpose and boundary

Personal AI Interview V1 is a dedicated application/service boundary that leads a personal inquiry from the Personal UI. It reuses immutable USER reflection turns as canonical USER source where appropriate and reuses existing canonical hypothesis, contradiction, provenance, temporal, Unknown and privacy concepts. Dedicated interview state exists only for genuinely session-specific meaning.

The interview is a foreground, owner-controlled process. It asks one primary question at a time and can adapt after every answer: deepen, request specificity, revisit evidence, flag a contradiction, challenge an interpretation, switch direction, explore a useful coverage gap, or recommend ending a line. It is not a generic autonomous agent, therapist, diagnostician, hidden profile, or provider-owned conversation.

## 2. Consent and outbound eligibility

- Starting a Personal AI Interview requires explicit, session-scoped disclosure and consent.
- Consent creates a memory-only runtime outbound capability. It is not durable state, a standing authorization or a policy override.
- Local unfinished interview state may persist, but `STOP`, accepted end, process exit or restart destroys the outbound capability. A later personal-data provider call after restart requires new consent.
- Every provider call independently checks purpose, current consent capability, provider profile, data-policy/lineage eligibility, `NEVER_CLOUD`, third-party restrictions and the bounded selected local inputs.
- The owner can stop, change topic, decline, correct, challenge, or continue after `END_RECOMMENDED` at any time. No background call, automatic resend, or follow-up provider work is authorized.

## 3. Local state and semantic ownership

PSYCHE owns all durable inquiry meaning. The minimum long-term inquiry state can represent active/recurring themes, underexplored areas, unresolved contradictions, hypotheses worth testing, revisit questions/reasons, priority, temporal relevance, evidence links and continuation between sessions. It is primarily AI-managed but inspectable, correctable and dismissible by the owner.

The canonical distinction is mandatory:

- a USER answer/reflection is a durable USER source before provider work begins;
- observations/assertions preserve their source-near/provenance-aware role;
- model questions, rationales, summaries, hypotheses, contradiction/Unknown suggestions, backlog updates and next-session directions are **DERIVED**;
- recommendations and later outcomes remain distinct from sources and derived interpretations.

No provider response is source evidence, canonical truth, policy, consent, permission, diagnosis, causal conclusion or durable hidden persona memory. No chain-of-thought is persisted. “Why this question?” is a bounded user-facing rationale, not hidden reasoning.

## 4. Retrieval, disclosure and provider isolation

Local selection is autonomous only within this bounded interview process: it may use current session state, eligible local evidence/history, support and counterevidence, contradictions, Unknowns, inquiry state, temporal relevance and owner priority. It does not disclose the whole vault and does not rely on similarity-only confirmation.

The provider profile is isolated and explicitly owns context budget/config, model/schema identity, allowed endpoint behavior and retention controls. Context-budget limits are evaluated configuration, not eternal Working Formulation constants.

Each call is one foreground, stateless request. The implementation must not use provider conversation memory, `previous_response_id`, hosted files/vector stores/tools/web, provider retrieval, hosted profile memory, background calls or generic tool loops. Disclosure receipts reference exact local inputs and transformations without storing a second plaintext copy where content-free receipt metadata is sufficient. The owner can inspect the per-call disclosure and the stated basis for a question.

## 5. Turn and commit protocol

1. The application receives a USER answer under a local idempotency identity and validates/persists it as canonical USER source.
2. It selects a bounded, policy-eligible local context and creates the runtime outbound capability check and content-free disclosure receipt.
3. One stateless provider request runs in the foreground.
4. The response undergoes strict schema, business, evidence-reference, privacy, contradiction, safety and relationship-boundary validation locally.
5. Only after validation does one local transaction atomically commit permitted **DERIVED** interview state: the next primary question/rationale, session summary or status, and any validated hypothesis/contradiction/Unknown/backlog suggestions or updates.

Provider/model/schema failures never partially mutate derived knowledge. Retrying never duplicates the USER source. An ambiguous network outcome never automatically resends the request; the owner must explicitly choose a safe next action. The provider response may be discarded while the persisted USER source remains intact.

## 6. Session experience and lifecycle

V1 supports accelerated onboarding where coverage is thin, preference for current/repeating meaningful themes when evidence warrants it, and exploration of long-term gaps when useful. Direction is selected from current context, evidence, open inquiry state, owner priority and expected information value—not a fixed turn cadence.

The interview ends only by the owner, `STOP`, process lifecycle, or an AI `END_RECOMMENDED` state that the owner may override. A normal end stores a short derived summary, open questions, the next-session direction and the local continuation state. The next session continues the investigation rather than starting from zero, subject to new consent before any outbound personal-data call.

## 7. Compatibility, correction and deletion

All derived interview records retain typed provenance: local input references, derivation/provider/profile/schema/policy identity, time and validation/review state. Correction, supersession, invalidation and deletion traverse those derived links under existing rules. Deleting or correcting a source must leave no unsupported active derived meaning; affected inquiry state, summaries and projections are invalidated, rebuilt or removed as their lineage requires.

The local Evidence OS—capture, inspection, query, correction, export, deletion, recovery and its local Personal Model views—remains operational without a provider.

## 8. Safety and explicit non-goals

The interview follows the existing mental-health, clinical, third-party, false-memory, causality, recommendation and dependency boundaries. Strong process leadership never means clinical authority or ownership of the person's truth. AI may challenge an explanation with inspectable evidence, and must revise when better evidence defeats it.

This contract does not authorize: real data; production OpenAI/provider configuration or secrets; a database migration; new dependency; external service; background networking; voice; microtests; standardized questionnaires; connected evidence sources; advanced experiments; broad temporal re-evaluation; third-party relationship modeling; diagnosis/therapy/triage; or notification/proactivity implementation.
