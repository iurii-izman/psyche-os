# PSYCHE OS research dossier 2026

**Evidence snapshot:** 2026-08-10  
**Scope:** scientific, clinical-boundary, measurement, safety, privacy/security, regulation, architecture, UX and lifetime durability research  
**Registry:** 155 stable records / 153 unique sources in `SOURCE_REGISTRY.yaml`  
**Data used:** public research/official sources and synthetic design examples only; no personal archive data

## 1. Method, epistemic posture and coverage

The dossier treats v1 as a hypothesis rather than a requirements source. Three workstreams were researched independently enough to expose different failure modes:

- 50 clinical/lifespan/personality/memory/functioning sources (`CLIN-*`);
- 50 psychometric/EMA/sleep/sensing/statistical/N-of-1/intervention sources (`MEAS-*`);
- 55 privacy/security/regulatory/architecture/AI-safety/UX/preservation sources (`ARCH-*`).

Priority was given to current official classifications, laws, regulator/guideline and standards-body documents; then systematic reviews/meta-analyses/methodological consensus; then relevant primary/field evidence. Vendor documentation is used only for vendor-specific behavior. Each source has currentness, design implication, limitation, rights note and review date. Evidence tiers from different workstreams are not collapsed into a universal score.

For every design implication, the relevant question is not merely “is there a source?” but:

- Is it the right construct and intended use?
- Is evidence direct or an analogy?
- Does the population, language, context and timescale match?
- Are observations independent and measurements valid?
- Does it establish description, prediction or causation?
- Is it current, licensed and reproducible?
- What alternative explanation or harm remains?

Confidence labels below concern the design implication. They do not turn contested constructs into facts.

## 2. Product problem and scientific north star

**Research question.** Can a system integrate a lifetime of heterogeneous psychological evidence without claiming a complete/clinical model of a person?

**Key findings and consensus.** Phenomena, reports, diagnoses, research dimensions, traits, functioning, quality of life, goals and narratives answer different questions. Model output and statistical factors are not evidence by themselves. Autobiographical sources are temporally and epistemically uncertain. A useful design therefore preserves layers, provenance, contradictions, unknowns and model history rather than converging to one identity profile [CLIN-001–CLIN-018, ARCH-041–ARCH-048].

**Controversies.** There is no accepted complete ontology of “the psyche”; dimensional and categorical systems each have uses and limits. A coherent personal formulation may be useful without being uniquely true.

**Limitations.** No longitudinal trial validates PSYCHE OS as a product; all architecture implications are a synthesis requiring later user/safety evaluation.

**Project implication.** Build a **Personal Evidence & Reflection System**. Treat `PersonalModelSnapshot` as a dated revisable derivative, never a digital twin, objective identity or clinician.

**Confidence:** high for the layered/evidence-preserving boundary; low that any one generated formulation is complete.

## 3. Psychiatric phenomenology and clinical classification

**Research question.** What may the system represent about symptoms and classification without autonomous diagnosis?

**Key findings.** A psychiatric phenomenon is context-sensitive: verbatim expression, form/content, course, distress, insight/conviction, context and functioning matter [CLIN-001]. ICD-11 CDDR is the appropriate primary international clinical terminology reference but is designed for trained clinical judgment [CLIN-002–CLIN-004]. DSM-5-TR is a proprietary, evolving US reference/crosswalk with diagnosis-specific reliability and rights constraints [CLIN-005]. Reliability varies and does not prove validity or etiology.

RDoC is a research framework, not diagnostic guidance [CLIN-006]. HiTOP has meaningful structural evidence for dimensional/hierarchical covariance but does not establish causal ontology or personal treatment utility [CLIN-007, CLIN-008]. The p-factor can summarize covariance in a specified population/model; critical literature warns against reification, unstable meaning and validity-by-fit [CLIN-009, CLIN-010].

**Consensus.** Preserve report/phenomenology separately from clinical mapping. Keep supporting/contradicting evidence and source/version. Diagnosis requires qualified professional context; screen results do not substitute.

**Controversies and limitations.** Classification boundaries, reliability, culture and revision continue to change. Structural dimensions do not eliminate clinical judgment. Proprietary text cannot be copied simply because a model can reproduce it.

**Project implication.** ICD-11 primary and DSM secondary versioned crosswalk; RDoC/HiTOP optional research tags; no p-score, self-diagnosis probability or causal category. Store no protected criteria/items without rights.

**Confidence:** high for layer separation and diagnostic boundary; moderate for any individual crosswalk; low for causal interpretation of latent dimensions.

## 4. Personality, state–trait and lifespan development

**Research question.** How should stable patterns and developmental change be represented?

**Key findings.** Big Five-compatible domains are a useful broad descriptive crosswalk, while facets often carry more information; HEXACO is a justified alternative whose Honesty–Humility/Emotionality/Agreeableness are not losslessly converted to Big Five [CLIN-011–CLIN-015]. Cross-cultural structure and percentile meaning are not universally invariant [CLIN-012]. Experience sampling supports wide within-person state variability alongside stable distributions [CLIN-013]. Traits are relatively stable and also change across life; long intervals, age, method and facets alter stability [CLIN-014, CLIN-015].

Lifespan development is multidirectional, plastic and shaped by cohort/context, with concurrent gains and losses [CLIN-016]. Equifinality and multifinality prohibit deterministic childhood-to-adult rules [CLIN-017]. Goals and narrative identity change; narrative coherence is meaning, not accuracy [CLIN-018].

**Controversies.** No trait model is a complete personality ontology. Mean-level population trends do not predict an individual trajectory. “Life stages” can guide questions but easily become cultural norm enforcement.

**Limitations.** Much personality evidence uses self-report and specific cultures/cohorts. Instrument versions/translations and measurement invariance matter.

**Project implication.** Separate state/behavior-in-context from trait estimates. Every trait has instrument/model, population, time window, age/context and uncertainty. Retain source-native HEXACO/Big Five facets and mark crosswalks lossy. Developmental links are hypotheses with alternatives; goals/narratives are versioned.

**Confidence:** high for state–trait/time separation; moderate for Big Five as primary interoperability lens; low for universal stage/trajectory inference.

## 5. Attachment and relationships

**Research question.** Can attachment science support a personal model without fixed “types” or partner diagnosis?

**Key findings.** Attachment research supports relationship-specific expectations, regulation and history, but early-to-adult stability is not determinism and depends on method/context [CLIN-019]. Popular fixed style labels overstate categorical stability. A user’s report about another person is evidence of the report/relationship perspective, not a diagnosis of that person.

**Controversies and limitations.** Attachment instruments and constructs differ; self-report and interview methods are not interchangeable. Cultural and relationship context matter.

**Project implication.** Model relationship episodes, expectations/behaviors, context, roles, change and sources; optional dimensional tags remain hypothesis-level. Prohibit “diagnose my partner/family” and protect third-party identifiers/content.

**Confidence:** moderate for relationship-specific dimensional patterns; low for a permanent personal attachment type.

## 6. Trauma, dissociation, grief, resilience and moral injury

**Research question.** How can adverse experience be represented without overdiagnosis, etiological certainty or suggestion?

**Key findings.** Exposure, current account, acute response, symptom phenomena, course, impairment, classification and recovery are distinct [CLIN-020]. Adversity/distress/dissociation does not entail PTSD. CPTSD and prolonged grief need system/version, duration, culture and functioning context [CLIN-002, CLIN-004, CLIN-020]. Moral injury is a potentially useful formulation concept with unsettled boundaries, not a diagnosis or proof of the event [CLIN-021]. Dissociation is heterogeneous; suggestibility evidence reinforces caution around hypnosis/guided imagery/recovery techniques [CLIN-023]. Post-adversity trajectories vary; resilience is common in some analyses but model/sample-dependent and not a moral obligation [CLIN-022].

**Controversies.** “Recovered/repressed memory,” moral injury boundaries and trajectory classes remain disputed. Trauma-focused treatment evidence does not authorize a software product to conduct therapy.

**Limitations.** Many data are retrospective, heterogeneous and culturally/contextually bounded. The system cannot determine whether an event happened or why symptoms arose.

**Project implication.** Keep exposure/report/phenomenology/impairment/classification separate; preserve alternatives/medical/substance/sleep context; never search for hidden trauma, use hypnosis/guided imagery, mandate disclosure, pathologize grief or promise post-traumatic growth.

**Confidence:** high for anti-deterministic/suggestion-safe boundaries; moderate for construct-specific mappings.

## 7. Autobiographical memory and biography reconstruction

**Research question.** What may be inferred from remembered events and conflicting sources?

**Key findings.** Memory is reconstructive and vulnerable to source-monitoring error [CLIN-024, CLIN-025]. Prospective and retrospective adversity records may agree weakly; neither is automatically the sole truth [CLIN-027]. Forensic interviewing research favors open free recall before specific prompts, but PSYCHE OS is not a forensic interviewer [CLIN-026]. Vividness, detail, repetition, emotion and confidence do not prove accuracy; uncertainty/fragmentation/change do not prove falsity.

**Consensus.** Preserve verbatim account, report time, claimed event interval, perspective and independent corroboration/conflict. Use non-leading prompts and an explicit “I do not know / prefer not to answer” path.

**Controversies and limitations.** Individual historical accuracy often cannot be resolved. Documentary sources may also be wrong, incomplete or coercive.

**Project implication.** `MemoryReport` carries separate belief, vividness, temporal precision, source clarity, corroboration, conflict and suggestion-risk dimensions—not one accuracy confidence. Biography is a set of source-linked event candidates and temporal assertions, not an authoritative reconstructed timeline.

**Confidence:** high for provenance/anti-suggestion rules; intrinsically low for uncorroborated historical truth.

## 8. Cognition, neuropsychology and neurodevelopment

**Research question.** Can subjective complaints, tests and screeners be combined safely?

**Key findings.** Subjective complaint, informant rating and performance task can reflect different levels and correlate weakly [CLIN-028]. ADHD assessment requires developmental/psychiatric history, impairment and multiple settings; rating scales alone are insufficient, and retrospective childhood recall can be inaccurate [CLIN-029, CLIN-030]. Adult autism assessment similarly uses developmental, observational, functioning and differential information; one screener can have poor predictive validity in a referral sample, while masking research is relevant but heterogeneous/self-report-heavy [CLIN-031–CLIN-033].

**Controversies and limitations.** Ecological validity, practice effects, digital tasks, adult retrospective onset and cultural/sex/gender presentation complicate inference. Proprietary neuropsychological tests have rights and qualified-use constraints.

**Project implication.** Keep complaint/informant/performance/device evidence separate; no ADHD/autism/neurocognitive diagnosis from a score or chat. Record method, conditions, validity flags, development, context, functional impact and alternative medical/sleep/substance explanations.

**Confidence:** high for multi-method/non-diagnostic boundary; variable for particular instruments and populations.

## 9. Emotion, behavior and regulation

**Research question.** Which emotion/behavior patterns are interpretable without moralizing strategies?

**Key findings.** Regulation strategies show transdiagnostic associations, but much evidence is self-report/associational and context/culture moderate effects [CLIN-034, CLIN-035]. Reappraisal or suppression is not universally good/bad. Behavioral activation has treatment evidence, but mostly short-term low-to-moderate certainty and does not make every activity–mood correlation causal [CLIN-036].

**Controversies and limitations.** Strategy definitions, timing, goal and controllability vary; population treatment evidence does not identify the mechanism for one person.

**Project implication.** Store goal, context, timing, feasibility, immediate/delayed outcome and alternatives. Use rumination/avoidance/suppression as revisable process hypotheses, not identities. Do not autonomously prescribe treatment.

**Confidence:** moderate for descriptive patterns; low for individual causal mechanisms without design.

## 10. Functioning, quality of life, strengths, values and thriving

**Research question.** How should impairment and positive functioning coexist with symptom evidence?

**Key findings.** ICF treats functioning as interaction among health, activity/participation and environment [CLIN-037]. WHODAS measures generic disability in distinct domains but is not diagnosis or quality of life [CLIN-038]. WHOQOL is subjective and culture/value/goal situated [CLIN-039]. Mental illness and positive mental health are related but distinct dimensions [CLIN-040]. Strength interventions show limited small-to-moderate pooled behavioral effects, not a universal replacement for symptom-focused care [CLIN-041].

**Controversies.** Flourishing/strength taxonomies and cut-offs vary. Values are authored and change; no algorithm can infer a final “true value hierarchy.”

**Limitations.** Response shift, adaptation, environment and culture affect all measures. High functioning can mask distress; low wellbeing is not diagnosis.

**Project implication.** Separate symptoms, functioning, QoL and thriving. Record strengths as demonstrated capacities/resources/person×context patterns with outcomes. Values/goals are user-authored, versioned and never optimized into one wellness score.

**Confidence:** high for separate layers; moderate for particular constructs; low for universal flourishing score.

## 11. Substances, behavioral addictions and medical confounders

**Research question.** What contextual health information reduces false psychological inference without practicing medicine?

**Key findings.** Structured substance risk instruments can support screening but carry rights/training and diagnostic-boundary constraints [CLIN-042]. Gambling has recognized severe harms and safeguarding needs [CLIN-043], while broad electronic “addiction” literature has inconsistent definitions/measures [CLIN-044]. Psychiatric evaluation should consider medicines, sleep, pain, substances, neurologic/endocrine/infectious and other contributors [CLIN-045].

**Controversies and limitations.** Exposure units, prescribed/nonmedical use, withdrawal, culture and self-report accuracy vary. The system cannot diagnose a medical condition or infer a substance-use disorder from a pattern alone.

**Project implication.** Record substance/category, amount/unit, route, frequency, timing, context, control/harms and source without moral labels. Medical candidates have states `not_assessed`, `possible_confound`, `clinician_documented`, `user_reported`, never `AI_diagnosed`. Urgent symptoms route to human care; no medication/test advice.

**Confidence:** high for confound/safety boundary; variable for screening instruments.

## 12. Psychometrics, licensing, language and adaptive assessment

**Research question.** What makes a score interpretable, comparable and legally usable?

**Key findings.** Validity supports a specified score interpretation/use, not a test “in general”; reliability, content/structural validity, measurement error, criterion/construct evidence and responsiveness are distinct [MEAS-001–MEAS-003]. CTT, IRT and CAT each impose assumptions; none bypasses content validity [MEAS-007, MEAS-008]. Longitudinal/group comparison needs measurement invariance appropriate to the inference [MEAS-009]. Translation requires forward/independent review/cognitive debriefing/validation and rights; an unvalidated Russian translation cannot support norms, cut-offs or standardized claims [MEAS-004–MEAS-006, MEAS-011].

**Consensus.** Score deterministically from the registered version, language, mode, recall window and missing-item rule. Preserve items/responses only if licensed. LLMs may explain bounded registered results but never score or invent interpretation.

**Controversies and limitations.** Cronbach alpha is often overused; cut-offs and minimally important change may not transfer. CAT/adaptive interviewing can reduce burden but introduces item-bank, IRT, exposure and comparability requirements.

**Project implication.** Create an assessment registry and hard rights/validation gate. “Publicly visible online” is not a license. Store reference population and uncertainty; screening remains non-diagnostic. Defer CAT until a licensed calibrated bank and equivalence evidence exist.

**Confidence:** high for the measurement contract; instrument-specific confidence varies.

## 13. Repeated measurement and EMA/ESM

**Research question.** How can the system learn over time without burden, reactivity or misleading missing-data assumptions?

**Key findings.** Signal-, event- and interval-contingent sampling answer different questions; frequency must match process timescale, not a universal prompt count [MEAS-022, MEAS-023, MEAS-025]. Adherence definitions vary and burden is often undermeasured [MEAS-023, MEAS-027]. Measurement can change behavior/experience, while many EMA studies do not test reactivity [MEAS-023, MEAS-024]. Adaptive EMA may reduce items but adds poorly standardized decision rules [MEAS-026]. Technical loss, deliberate skip, unavailable context, recall and non-applicability are different missingness states; LOCF/complete-case are not universal defaults [MEAS-036].

**Controversies.** Optimal density, incentives, reactivity and adaptive policy are person/construct/design specific. High response rate is not proof of low harm or validity.

**Limitations.** Studies are heterogeneous and often short. Users who disengage may be systematically different.

**Project implication.** Default to episodic/value-driven capture; use a protocol with burden ceiling, pause/stop, timezone and missingness rules. No guilt/streaks. Store protocol version and measurement change. Adaptive prompts require a predeclared algorithm and validation.

**Confidence:** high for no-universal-cadence/missingness transparency; moderate for any specific burden threshold.

## 14. Sleep OS and physical context

**Research question.** Which sleep observations can be useful without treating consumer devices as clinical truth?

**Key findings.** Clinical classification remains professional; sleep diaries provide subjective reports and deterministic derived metrics [MEAS-012–MEAS-014]. Actigraphy has conditional task-specific uses; PSG remains a standard for relevant diagnostic contexts and home testing is clinically bounded [MEAS-015, MEAS-016]. Consumer trackers differ from PSG and are heterogeneous; proprietary metrics/algorithm updates can drift silently [MEAS-017–MEAS-020]. CBT-I has guideline support for chronic insomnia, but sleep hygiene alone is not sufficient and aggressive restriction/medication change is unsafe for autonomous software [MEAS-013]. Orthosomnia warns that fixation on tracker scores can be harmful [MEAS-021].

**Controversies and limitations.** Device validation is model/firmware/algorithm/population-specific; sleep-stage labels may invite false precision.

**Project implication.** Separate diary, actigraphy, consumer, clinical and inferred records; pin device/algorithm epoch. Use trends cautiously, never diagnose OSA/parasomnia/circadian disorder. Route red flags, mania/psychosis worsening and dangerous sleepiness to human care.

**Confidence:** high for source separation and clinical boundary; low-to-moderate for individual consumer-derived sleep stages.

## 15. Passive sensing and digital phenotyping

**Research question.** Does passive smartphone/wearable data justify continuous psychological inference?

**Key findings.** Some studies show predictive signal, but small samples, bias, complex missingness, device/platform drift, lack of standardization/external validation and unclear clinical utility remain [MEAS-028–MEAS-031]. Sensor automation does not validate the construct or consent of third parties.

**Controversies.** Accuracy can look useful in cross-validation and fail across people/devices/time. Continuous collection changes autonomy and creates a much larger breach/maintenance surface.

**Limitations.** Evidence is rapidly evolving, often correlational and platform-specific.

**Project implication.** Reject ambient audio, keystrokes, covert location and surveillance. Defer most passive sensing. Any later feature requires decision-specific validity, minimal raw retention, on-device processing, explicit purpose/expiry, drift monitoring, missingness and deletion proof.

**Confidence:** high for deferral/minimization; low for clinical/personal inference from current passive data.

## 16. Longitudinal statistics, causality and N-of-1

**Research question.** What claims can one person's time series support?

**Key findings.** Between-person relationships do not automatically describe within-person dynamics [MEAS-032, MEAS-033]. Baseline is a time distribution with trend/cycle/context, not one point. Autocorrelation, nonstationarity, irregular spacing, missingness, regression to the mean, concurrent changes and multiplicity can create convincing false patterns [MEAS-034–MEAS-037]. Causal inference requires an estimand/diagram and assumptions; interrupted time series requires adequate pre/post observations and trend/seasonality/autocorrelation/concurrent-event checks [MEAS-038, MEAS-039]. CENT/SPENT/SCRIBE/AHRQ guidance supports prespecified transparent N-of-1/single-case protocol and analysis [MEAS-040–MEAS-043].

**Consensus.** Default claim is descriptive (`C0`) or association (`C1/C2`), not causal. Exploratory analyses stay labeled. N-of-1 requires preregistration, comparator/design, outcome, washout/carryover, confounds, missingness, analysis, stopping/adverse rules and reproducibility.

**Controversies and limitations.** Individual causal identification remains assumption-dependent; good N-of-1 evidence may not generalize beyond that person/time/context. Sophisticated models can amplify researcher degrees of freedom.

**Project implication.** Implement a causality ladder and design/risk gates. No automatic causal “insights”. High-risk medical/psychiatric/substance/sleep interventions remain outside self-experiment automation.

**Confidence:** high for analytic guardrails; design-specific for any causal result.

## 17. Intervention evidence and computational psychiatry

**Research question.** Can the product recommend actions or computational mechanisms safely?

**Key findings.** Evidence requirement should scale with function/risk; interventions need reproducible TIDieR description, certainty separate from magnitude, systematic harms and contextual guideline boundaries [MEAS-044–MEAS-048]. Computational models can formalize latent/dynamic hypotheses but psychiatric prediction models often show bias, weak external validation and uncertain clinical utility [MEAS-049, MEAS-050].

**Controversies and limitations.** Digital delivery, mechanism, person-level effect and harms often lack strong external evidence. Model fit/prediction does not equal actionable causal understanding.

**Project implication.** Maintain a versioned intervention registry with intended population, contraindications, harms, evidence and rights. Initially allow only information and low-risk user-authored actions; no treatment selection. Computational psychiatry remains research-only until external validation and clinical utility exist.

**Confidence:** high for registry/risk gate; low for automated personalized treatment.

## 18. Mental-health AI safety and relationship design

**Research question.** Which harms arise when generative models discuss mental health and life history?

**Key findings.** WHO calls for defined intended use, governance, transparency, evaluation, privacy and protection against false/biased health output [CLIN-046, ARCH-012, ARCH-054]. APA warns general-purpose GenAI/wellness apps are not established mental-health care and recommends reducing anthropomorphic/continuous-relationship cues [CLIN-047, ARCH-013]. Evaluations show stigma, inappropriate responses, delusion reinforcement, crisis inconsistency and sycophantic advice/dependence risk [CLIN-048–CLIN-050]. Prompt injection remains unsolved as a general class [ARCH-031, ARCH-032].

**Consensus.** Model output is proposal; no clinical authority, exclusivity, sentience/feeling claim, recovered-memory work or autonomous action. Acute-risk flow points to immediate local human help and states detection/rescue limitations.

**Controversies and limitations.** Incidence and causal contribution to severe harm are emerging and hard to estimate. Safety behavior changes by model, language, context and deployment. Keyword/classifier systems have false positives/negatives.

**Project implication.** Keep core useful without AI. Optional per-call context with policy preview; no provider memory. Version safety policies and adversarially test crisis, delusion/paranoia, mania, reassurance/OCD, trauma/suggestion, eating/substance/medical urgency, dependency, third-party diagnosis and prompt injection.

**Confidence:** high for precautionary relationship/authority boundaries; moderate-to-low for automated safeguard effectiveness.

## 19. Privacy, security and third-party data

**Research question.** What protection is required before deeply sensitive content exists?

**Key findings.** GDPR and privacy-by-design guidance make minimization, purpose, restrictive defaults, security, erasure/portability, DPIA-style assessment and transfer governance load-bearing [ARCH-004, ARCH-005]. A one-dimensional privacy tier cannot represent sensitivity, location, purpose, third-party scope, retention/export and derivative lineage. Encryption requires a complete key/recovery lifecycle [ARCH-020–ARCH-026]. SQLite temporary/deletion/backup behavior and metadata leakage require explicit control [ARCH-027–ARCH-030]. Imports and model context are attacker surfaces [ARCH-031–ARCH-036].

**Consensus.** Local canonical store, authenticated envelope encryption, OS convenience wrapping plus independent recovery, encrypted/restored backups, no content logs, opaque blob paths, least disclosure, lineage-aware `NEVER_CLOUD`, quarantine/parsers without network/keys and dependency/release provenance.

**Controversies and limitations.** At-rest encryption cannot stop same-user malware/coercion. SSD overwrite, external exports/provider copies and lost recovery material prevent absolute guarantees.

**Project implication.** F0 proves encryption/recovery/deletion/migration/export with synthetic data and no network listener. `REAL_DATA_GATE` remains closed until independent security review and failure testing.

**Confidence:** high for architecture/control classes; implementation assurance nonexistent until built/tested.

## 20. Regulatory posture

**Research question.** Which current boundaries affect a local reflection/evidence product?

**Key findings.** EU AI Act application is phased and current implementation/guidance must be resnapshotted; transparency duties may apply even outside high-risk classification [ARCH-001–ARCH-003]. GDPR applicability/roles depend on household/service/research/cloud facts [ARCH-004, ARCH-005]. Moldova Law No. 133/2011 remains current on 2026-08-10; Law No. 195/2024 and Convention 108+ changes are scheduled for 2026-08-23 [ARCH-006–ARCH-009]. FDA CDS/general-wellness and EU MDR software guidance make intended purpose/function—not a disclaimer alone—central [ARCH-010, ARCH-011].

**Controversies and limitations.** Final product, jurisdiction, controller/processor role and clinical functionality are not fixed. This research is not legal advice or device qualification.

**Project implication.** Keep a versioned claims/intended-use inventory. The current target excludes diagnosis, treatment, triage and clinical decisions. Obtain Moldova/EU/target-market legal review before distribution, cloud/research/clinician use; recheck time-sensitive law/guidance.

**Confidence:** high that review is mandatory; no final classification asserted.

## 21. Data, time, provenance, deletion and lifetime preservation

**Research question.** What representation remains correct, deletable and understandable for 40 years?

**Key findings.** Provenance standards support explicit entities/activities/agents; JSON Schema and canonicalization support versioned portable validation/manifests [ARCH-041–ARCH-043]. FHIR is a useful optional clinical export mapping, not a personal canonical ontology [ARCH-044, ARCH-045]. BagIt-like inventories and preservation guidance support packaged integrity/open formats but do not create confidentiality/authenticity alone [ARCH-046, ARCH-047]. Bitemporal database principles are necessary but autobiographical evidence also needs occurred/observed/reported/recorded/asserted and fuzzy intervals [ARCH-048].

**Consensus.** Use relational canonical versions plus encrypted source objects and typed derivation DAG. Graph/vector/search/analytics are projections. Hard deletion propagates to reconstructive descendants and declares backup/external limitations. Primary interchange is JSONL + schemas + manifest + Markdown; encrypted for sensitive content.

**Controversies and limitations.** No format guarantees 40-year readability without stewardship. Full event sourcing increases erasure/replay/migration risk; state-only rows underrepresent “as known then.”

**Project implication.** Choose hybrid bitemporal relational architecture. Maintain old-schema fixtures/readers, deterministic projection rebuild, migrations and restore/export drills.

**Confidence:** high for hybrid/projection/open-export direction; moderate for exact SQLCipher/package profile until implementation proof.

## 22. UX, burden and long-term adherence

**Research question.** What interface remains useful without compulsive tracking or AI attachment?

**Key findings.** Self-tracking can help and can fail/produce burden; abandonment reflects changing goals, usability, data value and context [ARCH-049, ARCH-050]. EMA burden/adherence depends on protocol and population [ARCH-051]. Digital mental-health acceptance depends on utility, trust, privacy, usability and human context [ARCH-052]; chatbot attrition/engagement measures are heterogeneous and engagement is not outcome [ARCH-053].

**Consensus.** Capture should be episodic and purpose-linked, allow unknown/decline/pause, deliver retrieval/correction value and handle long gaps. No guilt, streak loss, variable rewards or “percent of self known.” Chat is a temporary interaction surface, not canonical archive.

**Controversies and limitations.** Evidence comes from heterogeneous short-lived technologies; PSYCHE OS needs its own synthetic/prospective usability evaluation.

**Project implication.** Primary IA: capture/inbox, timeline, evidence, claims/contradictions/unknowns, model versions, measures/experiments, reports, privacy and recovery. Progressive disclosure prevents schema complexity from becoming user burden.

**Confidence:** moderate-to-high for anti-burden/no-engagement-optimization principles; low for final UI before testing.

## 23. Architecture convergence

**Research question.** Which architecture best satisfies evidence, privacy, deletion and lifetime constraints?

Three materially different designs were compared:

1. conventional state-oriented relational modular monolith;
2. full event-sourced temporal core;
3. hybrid bitemporal relational canonical store with encrypted artefacts, version/audit metadata and rebuildable projections.

The hybrid wins on traceable historical views, direct query/export, deletion and graceful projection/provider failure. Full event sourcing preserves change but makes content erasure, replay compatibility and migration/compaction disproportionately hazardous. State-only design is simpler but too easily loses derivation and “as-known-then” meaning. Selection is detailed in `docs/architecture/SYSTEM_ARCHITECTURE.md` and the independent rebuild.

**Confidence:** high for the selected pattern under a single-user local deeply sensitive vault; revisit for multi-user sync/distributed profiles.

## 24. Design decisions by confidence

| Decision | Confidence | Main uncertainty / review trigger |
|---|---|---|
| Evidence-preserving, non-clinical product identity | High | User anthropomorphism/clinical over-attribution in usability tests |
| Raw/normalized/derived and provenance split | High | Capture burden/UI progressive disclosure |
| Hybrid bitemporal relational canonical store | High | Implementation/migration/deletion property tests |
| Orthogonal privacy + lineage-aware `NEVER_CLOUD` | High | Novel derivative/policy composition |
| Dual-wrap key/recovery pattern | High pattern / Moderate profile | Platform/build/parameter independent review |
| ICD primary / DSM secondary mapping layers | High | Version/rights/jurisdiction updates |
| Big Five-compatible descriptive crosswalk | Moderate | Cross-cultural/translation/invariance evidence |
| No p-factor/personal wellness master score | High | None absent a new validated, bounded use |
| Episodic burden-bounded capture | Moderate–High | Construct/person-specific cadence |
| Consumer sleep trends only | Moderate | Exact device/algorithm validation |
| Defer passive sensing | High | New externally validated decision-specific evidence |
| Prespecified low-risk N-of-1 only | High | Design-specific identification/adherence |
| Optional proposal-only LLM | High boundary / Low variable benefit | Provider/model/safety/value evaluation |
| Open JSONL/schema/Markdown export | High | Periodic preservation migration |
| Real data remains prohibited | High | Only implemented independent gate evidence can change it |

## 25. Open research questions

1. Which minimal capture/evidence views users can understand without collapsing epistemic distinctions?
2. Which Russian-language instruments have verified rights, translation quality, invariance and repeated-use evidence for the exact intended purpose?
3. How should qualitative uncertainty be displayed without either false precision or unusable vagueness?
4. What bounded local-only analysis produces sustained value after long tracking gaps?
5. Which safety interventions actually reduce sycophancy, dependency, delusion and reassurance harms across languages/models without unsafe refusal overreach?
6. How can third-party narrative material be redacted while preserving evidentiary meaning?
7. Which preservation/container profile best combines independent recovery, cryptographic agility and accessible 20–40-year migration?
8. What evidence would justify any passive sensor/importer relative to breach/maintenance/validity cost?
9. What legal role and requirements apply to the actual distribution/deployment/intended use after Moldova Law No. 195/2024 commences?
10. What independent-review scope is proportionate before opening the local-only real-data profile?

## 26. Research verdict

PSYCHE OS should proceed only in the constrained form defined here: a local, evidence-preserving, correctable, deletable and exportable reflection system that remains useful without AI. The scientific foundation is strong enough to specify the secure core and explicit non-goals, not to validate a clinical product or an objective model of a person. Research documents may state `RESEARCH_CONVERGED = true`; implemented protection evidence does not yet exist, so `REAL_DATA_GATE = CLOSED`.
