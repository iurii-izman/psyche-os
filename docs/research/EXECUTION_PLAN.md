# PSYCHE OS v2 research execution plan

**Research snapshot date:** 2026-08-10  
**Repository:** `C:\Dev\psyche-os`  
**Status:** complete — research foundation converged
**Production implementation:** prohibited in this plan  
**Real personal data:** prohibited; `REAL_DATA_GATE = CLOSED`

**Completion snapshot:** 2026-08-10
**RESEARCH_CONVERGED:** `true`
**Next authorized scope:** F0 secure foundation with synthetic fixtures only

## Inputs and path resolution

- Master research prompt: `docs/prompts/PSYCHE_OS_FINAL_RESEARCH_MASTER_PROMPT_CODEX_SOL_ULTRA.md`.
- Historical v1 specification: `docs/specs/PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md`.
- The prompt's older references to `docs/PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md` are resolved to the actual `docs/specs/` path. Neither historical input will be overwritten.
- Initial repository state: two documentation files, no code, no pre-existing `AGENTS.md`, `PLANS.md`, `README.md`, `SECURITY.md`, architecture documents, or Git repository.

## Completion gates

Research can converge only when all of the following are evidenced in repository artifacts:

1. v1 concepts and hidden assumptions are audited.
2. Mandatory scientific, psychometric, safety, privacy, security, legal, UX, statistical, and lifetime domains reach evidence saturation appropriate to their design impact.
3. Current, time-sensitive facts are verified as of 2026-08-10.
4. At least three materially different system architectures are compared before selection.
5. Scientific, clinical/safety, statistical, privacy/security, UX, and lifetime red teams are completed.
6. A first-principles reconstruction is documented independently of v1.
7. Major decisions have evidence trails and explicit alternatives.
8. All required artifacts exist and validate.
9. Four final adversarial audits have been applied and weaknesses corrected.
10. The minimal irreversible core, implementation contract, and real-data blockers are explicit.

Only then may the final artifacts state `RESEARCH_CONVERGED = true`. This does not by itself open the real-data gate.

## Workstreams and status

| ID | Workstream | Main questions | Required output | Status |
|---|---|---|---|---|
| A | Baseline audit | What v1 proposes, assumes, gets right, overstates, or leaves unspecified | `docs/reviews/V1_CRITICAL_AUDIT.md` | Completed |
| B | Assumption inventory | Which scientific and architectural assumptions are load-bearing and falsifiable | Audit and dossier sections | Completed |
| C1 | Clinical and dimensional science | Proper role of ICD/DSM, phenomenology, dimensional models, impairment, differential reasoning | Research dossier and v2 scientific model | Completed |
| C2 | Development, personality, memory, trauma | Trait/state/context, lifespan limits, attachment, memory reconstruction, anti-suggestion | Dossier, ontology, safety rules | Completed |
| C3 | Psychometrics and EMA | Validity, licensing, translation, repeated measurement, burden, idiographic inference | Dossier, governance, assessment contract | Completed |
| C4 | Sleep, cognition, substances, physical context | Measurement hierarchy and confound boundaries | Dossier, Sleep OS and confound design | Completed |
| C5 | Longitudinal statistics and N-of-1 | Honest within-person inference, multiplicity, missingness, causal limits | Dossier, statistical and N-of-1 contract | Completed |
| C6 | Positive functioning and interventions | Conditions for thriving, evidence registry, self-help/clinician boundaries | Dossier, ontology, intervention registry contract | Completed |
| D | AI and mental-health safety | Sycophancy, dependence, reassurance, delusion/mania, crisis, false-memory harms | `docs/architecture/MENTAL_HEALTH_AI_SAFETY.md` | Completed |
| E | Privacy and security | Assets, trust boundaries, encryption/key/backup/deletion, prompt injection, third-party data | Privacy/security model and threat model | Completed |
| F | Regulatory and governance | EU AI Act, GDPR, Moldova, FDA/MDR boundary, scientific update lifecycle | Governance and regulatory posture | Completed |
| G | Architecture and lifetime durability | Canonical store, temporal model, migrations, export, deletion, offline/provider failure | Competing architectures and final design | Completed |
| H | UX and lifetime adherence | Burden, long-term value, retrieval, correction, non-chat information architecture | Red team, v2 UX contract | Completed |
| I | Independent reconstruction | What design follows from requirements without inheriting v1 | `docs/reviews/INDEPENDENT_REBUILD.md` | Completed |
| J | Convergence and decisions | Which design wins, what survives, changes, or is rejected | Decision log and final architecture | Completed |
| K | Final audits and validation | Does the complete foundation satisfy science, safety, security, durability, and consistency | Final report and validation record | Completed |

## Evidence workflow

For every load-bearing choice, record:

`DECISION → RESEARCH QUESTION → SOURCE IDS → FINDING → ALTERNATIVES → RATIONALE → UNCERTAINTY → REVIEW TRIGGER`

Source priority is: official classifications/guidelines/standards; systematic reviews and meta-analyses; methodological consensus; relevant primary research; discovery-only material. Every registered source must include currentness, evidence tier, project implication, limitation, rights/licensing note, and access date.

## Architecture comparison protocol

Compare at minimum:

1. state-oriented relational modular monolith;
2. fully event-sourced temporal core;
3. hybrid bitemporal relational canonical store with immutable artifacts/audit events and rebuildable graph/vector/analytics projections.

Score epistemic correctness, queryability, auditability, deletion, portability, privacy, durability, migration burden, implementation complexity, performance, graceful degradation, and failure recovery. Do not select a winner until the independent reconstruction and red teams are complete.

## Required artifacts checklist

- [x] `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`
- [x] `docs/research/PSYCHE_OS_RESEARCH_DOSSIER_2026.md`
- [x] `docs/research/SOURCE_REGISTRY.yaml`
- [x] `docs/research/EXECUTION_PLAN.md`
- [x] `docs/reviews/V1_CRITICAL_AUDIT.md`
- [x] `docs/reviews/INDEPENDENT_REBUILD.md`
- [x] `docs/reviews/RED_TEAM_REPORT.md`
- [x] `docs/DECISION_LOG.md`
- [x] `CONSTITUTION.md`
- [x] `docs/SCIENTIFIC_GOVERNANCE.md`
- [x] `docs/architecture/DATA_MODEL.md`
- [x] `docs/architecture/SYSTEM_ARCHITECTURE.md`
- [x] `docs/architecture/PRIVACY_SECURITY_MODEL.md`
- [x] `docs/architecture/MENTAL_HEALTH_AI_SAFETY.md`
- [x] `docs/architecture/THREAT_MODEL.md`
- [x] `ontology/psyche_domains.yaml`
- [x] `docs/ROADMAP.md`
- [x] `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`
- [x] `docs/FINAL_RESEARCH_REPORT.md`

## Validation checklist

- YAML parses and uses unique stable IDs.
- Required files and internal links resolve.
- Markdown headings and anchors are not ambiguously duplicated where avoidable.
- Source IDs cited by decisions and research sections exist in the registry.
- Current versions/dates are verified and access dates are recorded.
- Copyright and license limitations are explicit.
- Terminology is consistent across ontology, data model, architecture, and master spec.
- No real personal data, credentials, raw secrets, unsafe temporary files, or accidental binary archives exist.
- `RESEARCH_CONVERGED`, `REAL_DATA_GATE`, and implementation readiness agree across all final artifacts.
- Git/workspace status is understood and validation results are recorded.

## Completion evidence

- v1 was treated as a hypothesis; 60+ concepts and 44 hidden assumptions were audited.
- The registry contains 155 stable records representing 153 unique serious sources; every registered ID is cited and no unknown citation remains.
- Independent reconstruction compared four designs; the final system selects a hybrid bitemporal relational canonical store with encrypted source objects and rebuildable projections.
- Scientific, clinical/safety, statistical, privacy/security, deletion, UX, schema and 1/5/20/40-year red teams recorded 70 risks and four final audit passes with applied corrections.
- The ontology validates with 44 unique domains, 18 layer contracts, 17 evidence-kind contracts and no completeness claim.
- `python scripts/validate_research_foundation.py` reports 19/19 artifacts, zero errors, and only two duplicate-heading warnings in preserved historical inputs.
- `git diff --check` passes; no vault/database/key/export artefact or common plaintext secret signature is present.
- Final decision: build the bounded Personal Evidence & Reflection System and only the synthetic F0 foundation next. `REAL_DATA_GATE = CLOSED` with all 12 runtime/review requirements unsatisfied.
