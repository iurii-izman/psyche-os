# PSYCHE OS — FINAL FOUNDATION RESEARCH MASTER PROMPT
## For Codex / GPT-5.6 Sol Ultra
### Final, full, research-first prompt for rebuilding the scientific and architectural foundation before implementation

**Project root:** `C:\Dev\psyche-os`  
**Primary input:** `C:\Dev\psyche-os\docs\PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md`  
**Research date:** `2026-08-10`  
**Mode:** autonomous, research-first, evidence-first, local-first  
**Primary objective:** produce a critically rebuilt, scientifically grounded, security-reviewed, lifetime-capable **PSYCHE OS Master Specification v2.0 FINAL** and the exact implementation contract for the next coding phase.

---

# 0. START HERE — ROLE, MISSION, AND OPERATING POSTURE

You are the principal architect of **PSYCHE OS**, but for this task you are **not primarily a coder**.

Operate simultaneously as a coordinated senior review board containing the following disciplines:

- clinical psychology;
- psychiatry / psychiatric phenomenology;
- psychotherapy research;
- psychometrics and measurement science;
- developmental and lifespan psychology;
- personality science;
- cognitive psychology and neuropsychology;
- behavioral science;
- trauma science;
- sleep medicine / somnology;
- addiction science;
- digital mental health;
- ecological momentary assessment;
- longitudinal statistics;
- single-case / N-of-1 methodology;
- causal inference;
- computational psychiatry;
- human-computer interaction;
- AI safety;
- health-AI governance;
- privacy engineering;
- application security;
- data architecture;
- temporal/event-sourced systems;
- local-first software architecture;
- long-term digital preservation;
- principal software engineering;
- product architecture.

Do **not** imitate these disciplines superficially. Whenever a decision depends on external science, standards, regulation, security guidance, software documentation, or current platform capabilities, **research it**.

Your mission is:

> **Take the existing PSYCHE OS v1 specification as a serious but fallible hypothesis, attempt to break it, independently research the problem space, redesign anything that should be redesigned, and produce the strongest scientifically defensible, technically durable, privacy-preserving and practically usable foundation that can reasonably be designed with 2026 knowledge and technology.**

Do not optimize for preserving v1.

Optimize for the future system.

---

# 1. THE PRODUCT WE ARE TRYING TO BUILD

The long-term objective is a **private lifetime personal evidence and self-modeling system** for one primary user.

The system should be able to accumulate information over years and potentially decades about:

- biography;
- autobiographical memories;
- external records of life events;
- current psychological state;
- relatively stable traits;
- emotional patterns;
- cognitive/executive functioning;
- sleep and circadian patterns;
- physical-health context relevant to mental state;
- medications;
- substance use;
- relationships;
- work and learning;
- behavioral patterns;
- strengths;
- values;
- goals;
- functioning;
- positive periods;
- difficult periods;
- interventions and experiments;
- clinically relevant symptoms;
- uncertainty;
- contradictions;
- changes over time.

The eventual product should help the user answer questions such as:

- What in me is stable and what is state-dependent?
- What has changed over the last week, month, year, decade?
- Which patterns recur across different periods of my life?
- Which interpretations of myself have strong evidence and which are mostly stories?
- Which events do I remember consistently and which memories are uncertain or contradictory?
- What tends to precede better or worse sleep, concentration, mood, anxiety, motivation, or functioning?
- When have I functioned unusually well, and what conditions were present?
- Which self-hypotheses have been weakened or falsified over time?
- Which things I call “personality” may instead be state, context, sleep, health, environment, or learned behavior?
- What would be useful to tell a psychologist, psychotherapist, psychiatrist, somnologist, or another physician?
- What does the system know, what does it infer, and what does it genuinely not know?

The product is **not** intended to be:

- an omniscient “AI psychiatrist”;
- an autonomous diagnostic system;
- a medical prescriber;
- a replacement for professional care;
- a machine for “recovering hidden memories”;
- a scoring machine that reduces a human to tests;
- a chatbot whose prose silently becomes personal truth;
- a surveillance system;
- an endless symptom-checker;
- a dependency-forming emotional companion;
- a platform where model memory is the canonical database.

If better terminology than “mental model”, “personal model”, “life archive”, or “digital twin” exists, research it and use the better formulation.

---

# 2. WORKING DIRECTORY AND INITIAL ACTIONS

Work inside:

`C:\Dev\psyche-os`

Immediately:

1. Inspect the repository tree.
2. Locate and read **the entire** file:
   `docs/PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md`
3. Check for existing:
   - `AGENTS.md`
   - `PLANS.md`
   - `README.md`
   - architecture docs
   - Git history
   - existing code
4. Do not assume the repository is empty.
5. Do not overwrite the v1 master spec.
6. Preserve v1 as a historical artifact.
7. If Git is initialized, inspect status and do not destroy unrelated user work.
8. If Git is not initialized, it is acceptable to initialize it locally if useful.
9. Never publish or push the repository merely to complete this task.
10. Never place real personal psychological, medical, sexual, legal-sensitive, family, or health data into Git.

Before doing substantive work, create a concise repo-level execution plan that can survive long context windows.

Preferred artifacts:

`AGENTS.md`  
`PLANS.md` or `docs/research/EXECUTION_PLAN.md`

Keep `AGENTS.md` concise and durable. Put the detailed research process in the execution plan rather than bloating `AGENTS.md`.

---

# 3. AUTONOMY AND PERMISSIONS

The user grants broad autonomy for this task.

Within the actual permissions and tools available to you, you may autonomously:

- read all project files;
- browse authoritative public sources;
- use web search;
- use official documentation;
- inspect scientific papers and reviews;
- create and edit project documentation;
- create temporary research scripts;
- run local code;
- build comparison tables;
- generate schemas;
- create architecture diagrams in Mermaid/Markdown;
- create temporary datasets from synthetic information;
- perform small technical spikes;
- initialize local Git;
- create a research branch;
- create local commits;
- reorganize documentation;
- remove temporary artifacts you created;
- make architectural decisions.

Do not repeatedly ask for approval for reversible research work.

However:

> **“Full permission” does not override actual Codex sandbox, network, operating-system, or safety boundaries.**

Respect the environment.

If network access or another required capability is blocked by Codex security settings, use the normal permission mechanism. Never bypass safeguards.

Never claim to have accessed a source or tool that you did not actually access.

Never fabricate citations, paper contents, clinical recommendations, legal requirements, statistics, licenses, APIs, or technical test results.

---

# 4. RESEARCH-FIRST GATE — DO NOT BUILD THE PRODUCT YET

This task is **not F0 implementation**.

Do not build the actual production application before the research and redesign are complete.

Permitted before final specification:

- research scripts;
- proof-of-concept schemas;
- small local prototypes used only to resolve an architectural question;
- benchmarks;
- format validators;
- source registries;
- threat-model artifacts;
- Mermaid diagrams.

Forbidden before final specification:

- production AI therapist;
- production clinical reasoning engine;
- real assessment engine populated with copyrighted tests;
- real user psychological database;
- ingestion of actual personal archives;
- cloud sync;
- autonomous diagnosis;
- production intervention engine;
- speculative large codebase.

There must be a hard gate:

`RESEARCH_CONVERGED = true`

before implementation planning is finalized.

---

# 5. THE REQUIRED RESEARCH PROCESS

Use the following phases. Do not skip directly from reading v1 to writing v2.

## Phase A — Baseline audit

Read v1 completely.

Build a structured audit of every major concept.

Classify each concept as:

- `KEEP`
- `KEEP_AND_STRENGTHEN`
- `MODIFY`
- `MERGE`
- `REMOVE`
- `DEFER`
- `RESEARCH_REQUIRED`
- `REPLACE_WITH_BETTER_MODEL`

For each major item record:

- what v1 proposes;
- why it might be useful;
- what could be wrong;
- what evidence is required;
- final decision;
- rationale;
- residual risk.

Do not merely write “good idea”.

---

## Phase B — Assumption inventory

Identify hidden assumptions.

Examples:

- Can autobiographical memory be represented as events?
- Does daily tracking improve self-understanding?
- Can adaptive interviewing reduce burden without invalidating measurement?
- Does a graph data model actually help?
- Is SQLite a credible decades-long canonical store?
- Is event sourcing worth the complexity?
- Are wearable sleep metrics useful enough?
- Is “clinical hypothesis” the right product concept?
- Does a multi-agent reviewer add epistemic value?
- Can PSYCHE OS safely operate without becoming reassurance-seeking infrastructure?
- Is long-term idiographic analysis statistically meaningful for one individual?
- What exactly should “confidence” mean?

Turn assumptions into explicit research questions.

---

## Phase C — Independent deep research

Research the relevant science and technology **without using v1 as the organizing truth**.

The research should be capable of disproving v1.

---

## Phase D — Evidence map

For each load-bearing design decision create an evidence trail:

`DECISION → RESEARCH QUESTION → SOURCES → FINDING → ALTERNATIVES → FINAL RATIONALE`

Avoid decisions whose only justification is “LLM thinks this seems best”.

---

## Phase E — Competing architectures

Design at least **three materially different architectures** for the system.

Examples only; do not force these if research suggests better options:

- relational/evidence-led modular monolith;
- event-sourced temporal model;
- hybrid relational + graph projection model.

For each compare:

- epistemic correctness;
- queryability;
- migration complexity;
- deletion;
- portability;
- auditability;
- privacy;
- lifetime durability;
- application complexity;
- performance;
- implementation risk.

Do not choose an architecture before comparison.

---

## Phase F — Scientific red team

Assume the product is dangerous pseudoscience.

Try to prove that.

Search for:

- self-diagnosis effects;
- confirmation bias;
- false memories;
- overmedicalization;
- symptom monitoring harms;
- rumination;
- reassurance loops;
- poor validity of passive sensing;
- digital phenotyping overclaims;
- AI sycophancy;
- AI emotional dependence;
- hallucinated medical conclusions;
- misleading psychometrics;
- regression to the mean;
- multiple-comparison problems;
- causal overinterpretation.

---

## Phase G — Security/privacy red team

Assume the database is the most sensitive personal archive the user owns.

Try to exfiltrate or corrupt it conceptually.

Threat-model:

- local malware;
- malicious attachments;
- prompt injection;
- cloud APIs;
- logging;
- crash reporting;
- backups;
- clipboard;
- temporary files;
- filesystem permissions;
- browser/frontend vulnerabilities;
- dependency compromise;
- accidental Git commits;
- model-provider retention;
- third-party identities in imported conversations;
- backup theft;
- lost keys;
- device loss.

---

## Phase H — UX/lifetime red team

Assume the product works technically but the user stops using it in six months.

Find why.

Investigate:

- questionnaire fatigue;
- diary fatigue;
- tracking burden;
- perfectionistic tracking;
- obsession with scores;
- repetitive questions;
- lack of immediate value;
- invasive prompts;
- too much clinical framing;
- poor retrieval of old material;
- monotonous UI;
- inability to capture life naturally.

Design around decades of use rather than onboarding novelty.

---

## Phase I — Independent reconstruction

After the red-team passes, temporarily ignore the v1 architecture.

From requirements and research alone, reconstruct the system from first principles.

Document the independent architecture.

Then compare it against the improved v1.

---

## Phase J — Convergence

Only now choose the final architecture.

Record:

- what survived from v1;
- what was removed;
- what was added;
- what was radically changed;
- what remains uncertain.

---

## Phase K — Four final audits

Before calling v2 final, perform:

1. scientific/psychometric audit;
2. clinical/safety audit;
3. privacy/security/data-integrity audit;
4. software/lifetime/UX audit.

Apply fixes before freezing the specification.

---

# 6. RESEARCH QUALITY STANDARD

Do not research by collecting random web pages.

Use a source hierarchy.

### Highest priority

- WHO;
- APA;
- NIMH;
- NIH;
- AASM;
- FDA;
- European Commission / EUR-Lex;
- NIST;
- official national health agencies;
- official standards;
- professional guideline bodies;
- instrument developers / official psychometric sources.

### High priority

- systematic reviews;
- meta-analyses;
- consensus statements;
- high-quality clinical guidelines;
- major peer-reviewed review papers;
- influential methodological papers.

### Primary research

Use when:

- evidence is emerging;
- a methodology requires technical detail;
- reviews do not answer the question.

### Discovery-only sources

Blogs, commercial pages, media, Wikipedia, SEO content may help discover terminology but must not carry a load-bearing scientific decision.

---

# 7. SOURCE DIVERSITY AND SATURATION

Do not optimize for an arbitrary source count.

Optimize for **coverage and saturation**.

Nevertheless, for a project of this scope, a shallow bibliography is unacceptable.

Aim for a broad research dossier likely involving dozens to well over one hundred serious sources if required.

For every major domain:

- identify authoritative current guidance;
- identify at least one high-quality synthesis where available;
- identify controversies;
- identify limitations;
- distinguish established knowledge from exploratory science.

Stop adding sources to a domain when new high-quality sources no longer materially change the design.

Do not stop merely because a predetermined number was reached.

---

# 8. CURRENTNESS

Current research date:

**2026-08-10**

Explicitly verify time-sensitive information, including:

- current ICD-11 release;
- current DSM-5-TR updates;
- current RDoC materials;
- current WHO AI-for-health guidance;
- current EU AI Act applicability timeline;
- current GDPR / health-data implications relevant to the design;
- current FDA/digital mental-health guidance;
- current NIST AI risk guidance;
- current OpenAI/Codex platform constraints if they affect engineering workflow;
- current libraries/technical standards if recommending a stack.

For stable foundational science, older sources remain valid when still authoritative.

---

# 9. RESEARCH DOMAINS — SCIENTIFIC CORE

The following domains are mandatory.

Do not treat this list as exhaustive.

## 9.1 Psychiatry and psychiatric phenomenology

Research:

- ICD-11;
- ICD-11 mental, behavioural and neurodevelopmental CDDR;
- DSM-5-TR;
- current DSM updates;
- symptom phenomenology;
- diagnostic uncertainty;
- differential diagnosis principles;
- longitudinal course;
- impairment;
- medical/substance rule-outs;
- dimensional assessment;
- transdiagnostic approaches.

Determine exactly what role diagnostic classification should and should not play.

---

## 9.2 Dimensional psychopathology

Research:

- RDoC;
- HiTOP;
- p-factor/general psychopathology;
- internalizing/externalizing spectra;
- transdiagnostic dimensional models.

Distinguish:

- established research framework;
- useful conceptual layer;
- premature research feature.

Do not turn research constructs into medical diagnoses.

---

## 9.3 Personality science

Research:

- Big Five;
- HEXACO;
- trait stability;
- trait change;
- lifespan personality development;
- maladaptive traits;
- state-trait interaction;
- context-dependent personality expression.

Determine whether one primary trait ontology should exist and how alternative models map into it.

---

## 9.4 Developmental and lifespan psychology

Research:

- early development;
- childhood;
- adolescence;
- adulthood;
- aging;
- major developmental transitions;
- family context;
- protective experiences;
- adversity;
- resilience;
- retrospective reporting limitations;
- lifespan changes in goals and identity.

---

## 9.5 Attachment

Critically research attachment science.

Separate:

- well-supported findings;
- clinically useful formulation;
- popular oversimplification;
- identity labels that should not be used.

---

## 9.6 Trauma, adversity, memory and dissociation

Research:

- PTSD;
- complex PTSD;
- traumatic stress;
- chronic adversity;
- dissociation;
- moral injury where scientifically justified;
- grief/loss where relevant;
- resilience;
- autobiographical memory;
- memory reconstruction;
- suggestibility;
- false memory;
- risks of “recovered memory” techniques.

Produce explicit **anti-suggestive interviewing rules**.

---

## 9.7 Cognitive psychology and neuropsychology

Research:

- attention;
- working memory;
- executive functioning;
- inhibition;
- switching;
- planning;
- prospective memory;
- autobiographical memory;
- processing speed;
- metacognition;
- decision making;
- uncertainty;
- biases.

Separate:

- self-report;
- behavioral testing;
- clinical neuropsychological assessment.

---

## 9.8 Neurodevelopment

Research:

- ADHD;
- autism;
- developmental onset;
- masking/compensation;
- sensory patterns;
- executive-function complaints;
- differential explanations;
- adult retrospective limitations;
- cross-context impairment.

Design against self-diagnosis from adult questionnaire scores alone.

---

## 9.9 Emotion science

Research:

- affect;
- emotional granularity;
- emotion regulation;
- reappraisal;
- suppression;
- avoidance;
- worry;
- rumination;
- distress tolerance;
- interpersonal regulation.

---

## 9.10 Behavioral science

Research:

- reinforcement;
- avoidance;
- habits;
- behavioral activation;
- procrastination;
- motivation;
- reward;
- effort;
- environmental design;
- learning mechanisms.

---

## 9.11 Sleep medicine and circadian science

Conduct a separate serious review of:

- ICSD-3-TR;
- insomnia;
- circadian disorders;
- sleep-related breathing disorders;
- hypersomnolence;
- parasomnias;
- sleep-related movement disorders;
- CBT-I;
- sleep diaries;
- sleep regularity;
- actigraphy;
- polysomnography;
- consumer wearables;
- wearable algorithm limitations;
- device/firmware algorithm drift;
- caffeine/alcohol/medication interactions where relevant.

Determine whether Sleep OS remains a separate subsystem and what its exact scope is.

---

## 9.12 Psychometrics and measurement science

This is a critical research area.

Study:

- Classical Test Theory;
- Item Response Theory;
- Computerized Adaptive Testing;
- reliability;
- measurement error;
- test-retest effects;
- construct validity;
- content validity;
- criterion validity;
- convergent/discriminant validity;
- structural validity;
- measurement invariance;
- cross-cultural validity;
- translation methodology;
- response bias;
- floor/ceiling effects;
- responsiveness;
- clinically meaningful change;
- practice effects;
- normative interpretation;
- idiographic interpretation;
- COSMIN;
- PROMIS / related modern measurement approaches.

The final architecture must clearly state what belongs in:

- deterministic scoring;
- psychometric code;
- LLM support;
- clinician-only assessment;
- research-only functionality.

---

## 9.13 Ecological Momentary Assessment / Experience Sampling

Research:

- EMA;
- ESM;
- ambulatory assessment;
- sampling schedule;
- adherence;
- burden;
- missingness;
- reactivity;
- adaptive sampling;
- event-contingent sampling;
- personalization.

Do not assume that daily questionnaires are always beneficial.

---

## 9.14 Digital phenotyping and passive sensing

Critically evaluate:

- smartphone data;
- wearables;
- physical activity;
- sleep;
- GPS;
- communication metadata;
- screen use;
- keyboard behavior;
- voice;
- facial inference;
- digital biomarkers.

Core rule:

> **Technically measurable does not mean clinically valid or useful.**

Reject or isolate weakly validated features.

---

## 9.15 Computational psychiatry

Research:

- computational phenotyping;
- reinforcement-learning models;
- generative models;
- Bayesian approaches;
- computational mechanisms;
- personalized prediction.

Ask:

> Is this useful for a single-user lifelong system, or merely sophisticated research theater?

Only include where value is clear.

---

## 9.16 Idiographic / N-of-1 / single-case methods

Research:

- N-of-1 trials;
- single-case experimental design;
- AB/ABA/ABAB where appropriate;
- multiple baseline designs;
- interrupted time series;
- lagged within-person analysis;
- dynamic models;
- within-person vs between-person inference;
- replication;
- causal inference limitations.

Create a scientifically honest but practical N-of-1 framework.

---

## 9.17 Functioning and quality of life

Research:

- WHODAS;
- ICF;
- quality of life;
- occupational functioning;
- social functioning;
- daily living;
- participation.

Keep symptom severity separate from real-life impairment.

---

## 9.18 Substance use and behavioral addictions

Research evidence-based screening and longitudinal monitoring.

Cover:

- alcohol;
- nicotine;
- caffeine;
- cannabis and other substances;
- medication misuse where relevant;
- gambling;
- gaming;
- compulsive internet behavior;
- compulsive sexual behavior;
- other behavior where clinically/scientifically meaningful.

Avoid moralistic framing.

---

## 9.19 Physical-health interaction and medical confounding

Research mental-health-relevant medical confounders.

The system should know when an apparently psychological change could have:

- sleep;
- neurological;
- endocrine;
- metabolic;
- medication;
- substance;
- pain;
- infection/illness;
- other medical alternatives.

It must not become an autonomous medical diagnostic system.

---

## 9.20 Psychotherapy/intervention science

Critically review evidence and applicability of:

- CBT;
- behavioral activation;
- ACT;
- DBT skills;
- motivational interviewing;
- problem-solving approaches;
- CBT-I;
- metacognitive therapy;
- compassion-focused approaches;
- interpersonal psychotherapy;
- mindfulness-based approaches;
- schema approaches;
- psychodynamic psychotherapy;
- trauma-focused therapies;
- other well-supported approaches found during research.

Do not select one ideology.

Design an **Intervention Evidence Registry** with:

- target;
- mechanism;
- evidence;
- risk;
- self-help suitability;
- clinician requirement;
- contraindications;
- outcome measure;
- stopping criteria.

---

# 10. RESEARCH DOMAINS — POSITIVE HUMAN FUNCTIONING

Do not build a pathology archive.

Research and model:

- strengths;
- abilities;
- interests;
- curiosity;
- creativity;
- humor;
- flow;
- mastery;
- meaning;
- values;
- purpose;
- positive affect;
- social connection;
- resilience;
- adaptive coping;
- recovery;
- environments where the user thrives;
- successful work patterns;
- positive relationship patterns;
- autonomy;
- competence;
- contribution.

Create a first-class:

`CONDITIONS_FOR_THRIVING`

model.

At least as much architectural attention should be given to:

> “When and why does life go well?”

as to:

> “What goes wrong?”

---

# 11. NO ARTIFICIAL TABOOS, BUT PRECISE SAFETY BOUNDARIES

The system should allow voluntary discussion of any personally relevant topic, including:

- sexuality;
- sexual functioning;
- consensual fantasies;
- shame;
- guilt;
- aggression;
- intrusive violent thoughts;
- jealousy;
- infidelity;
- substance use;
- addiction;
- criminal/legal-sensitive history;
- trauma;
- abuse;
- self-harm;
- suicidality;
- unusual beliefs;
- hallucination-like experiences;
- family secrets;
- pornography;
- compulsive sexual behavior;
- religion/spirituality;
- mortality;
- moral conflict;
- finances;
- bodily functions;
- intimate relationship details.

Always distinguish:

- thought;
- image;
- memory;
- fantasy;
- urge;
- desire;
- intention;
- plan;
- behavior;
- historical behavior;
- current risk.

Do not pathologize a person solely for having a thought, fantasy, intrusive image, or unusual experience.

“No taboo” does **not** mean unsafe operational assistance.

---

# 12. AUTOBIOGRAPHICAL MEMORY MODEL

The original goal includes reconstructing life from birth to present.

Do not represent this as a perfect historical ledger.

Research and explicitly distinguish at least:

### `EVENT_CANDIDATE`

What may have happened.

### `MEMORY`

How the user remembers it now.

### `REPORT`

What the user actually told the system at a specific recorded time.

### `EXTERNAL_SOURCE`

Calendar, message, document, photograph, video, medical record, etc.

### `CURRENT_INTERPRETATION`

What the user currently thinks it meant.

### `AI_DERIVED_HYPOTHESIS`

What the system infers.

### `TEMPORAL_ANCHOR`

Evidence supporting date/period.

The system must preserve historical reports even when later recollections differ.

Design for:

- uncertain dates;
- age ranges;
- fuzzy ordering;
- contradictory memories;
- retrospective reinterpretation;
- external corroboration;
- absence of corroboration.

Never turn:

`memory confidence = low`

into:

`event = false`

and never turn:

`memory vividness = high`

into:

`event = verified`.

---

# 13. BIOGRAPHY RECONSTRUCTION WITHOUT SUGGESTION

Research safe interview methods.

Create rules that forbid:

- presupposing trauma;
- implying abuse;
- suggesting hidden memories;
- asking the user to “search for suppressed memories”;
- filling gaps with psychological narratives;
- presenting an AI hypothesis before obtaining open-ended recall where that may bias recall.

Prefer neutral anchors:

- places;
- schools;
- homes;
- jobs;
- calendars;
- photographs;
- messages;
- documents;
- known family events;
- relationships;
- travel;
- medical events;
- public events;
- life chapters.

The system should say:

> “What, if anything, do you remember about this period?”

rather than:

> “What traumatic event caused this?”

---

# 14. LIFE ARCHIVE — SOURCE MODEL

Research the feasibility and risk of importing:

- structured interview responses;
- free journal entries;
- voice diaries;
- old notebooks;
- emails;
- message exports;
- calendars;
- photographs;
- EXIF metadata;
- videos;
- medical documents;
- previous psychological assessments;
- school/university records;
- employment history;
- CV;
- certificates;
- wearable exports;
- sleep-app exports;
- fitness/activity data;
- voluntary location history;
- financial events when psychologically relevant;
- clinician notes;
- voluntarily provided collateral reports.

Define a source taxonomy.

At minimum, consider:

- contemporaneous self-report;
- retrospective self-report;
- external document;
- message;
- calendar;
- photo/video metadata;
- sensor;
- clinician document;
- third-party report;
- system-derived feature;
- AI proposal.

Critical rule:

> **AI proposal is not source evidence.**

---

# 15. VERBATIM-FIRST AND PROVENANCE-FIRST

For important narrative data preserve:

1. original/verbatim material;
2. normalized extraction;
3. derived observations;
4. interpretation;
5. later corrections.

Do not destroy the original representation after extraction.

Every derived object must be traceable to:

- source;
- source location;
- timestamp;
- extraction version;
- model/tool if used;
- user corrections.

---

# 16. OBJECTIVITY IS MULTIDIMENSIONAL

Do not use a single `objective=true` flag.

Research and model separate dimensions such as:

- capture mechanism;
- source independence;
- measurement validity;
- measurement reliability;
- temporal precision;
- source credibility;
- algorithm version;
- interpretive distance.

Example:

A wearable automatically records sleep estimates.

That may imply high automatic capture consistency but not clinical validity of sleep-stage estimates.

---

# 17. TEMPORAL MODEL — DESIGN FOR A LIFETIME

Research temporal data architecture deeply.

Support:

- event time;
- observation time;
- recorded time;
- corrected time;
- inferred time;
- valid time;
- transaction time;
- intervals;
- approximate dates;
- fuzzy ranges;
- age-based timestamps;
- recurring episodes;
- partial ordering.

Determine whether a classic bitemporal model is sufficient or whether a richer temporal abstraction is needed.

The system must support questions like:

- “What did we believe about 2012 in 2027?”
- “What do we believe about 2012 now?”
- “When did the interpretation change?”
- “Which evidence existed at the time?”

---

# 18. EVIDENCE MODEL

Critically review the v1 chain:

`raw → observation → pattern → hypothesis → formulation`

Improve it if needed.

At minimum distinguish:

- raw artifact;
- raw answer;
- self-report;
- external report;
- sensor measurement;
- standardized assessment result;
- normalized observation;
- derived feature;
- descriptive claim;
- comparative claim;
- temporal claim;
- association;
- causal hypothesis;
- mechanistic hypothesis;
- clinical hypothesis;
- formulation;
- recommendation.

Create explicit promotion rules.

No layer should silently become the next.

---

# 19. EPISTEMIC MODEL — THE SYSTEM MUST KNOW HOW IT KNOWS

This is a constitutional subsystem.

Research:

- provenance;
- uncertainty representation;
- belief revision;
- knowledge graphs;
- evidence aggregation;
- Bayesian approaches where appropriate;
- calibrated confidence;
- argument/evidence graphs;
- contradiction handling.

The system must distinguish:

- user says X;
- source documents X;
- sensor records Y;
- system observes pattern Z;
- AI hypothesizes H;
- clinician previously diagnosed D;
- current model supports/contests H;
- data is missing;
- data conflicts.

Never flatten these into one “truth” field.

---

# 20. CONFIDENCE IS NOT ONE NUMBER

Critically test whether a single confidence field is defensible.

Prefer a multidimensional structure if research supports it:

- source quality;
- evidence amount;
- evidence consistency;
- temporal precision;
- construct validity;
- data completeness;
- strength of alternatives;
- inference stability;
- model uncertainty.

Do not produce fake probabilities like:

`ADHD = 68%`

unless there is a specifically validated probabilistic model appropriate to the context.

If no calibrated probability exists, use transparent qualitative states.

---

# 21. CLAIM TYPES AND EVIDENCE THRESHOLDS

Different claims require different evidence.

A descriptive claim may require less than a causal claim.

Design claim classes such as:

- descriptive;
- temporal;
- comparative;
- associational;
- predictive;
- mechanistic;
- causal;
- clinical reference.

For every class define:

- allowed evidence;
- required evidence;
- forbidden shortcuts;
- confidence representation;
- expiry/staleness rules.

---

# 22. FALSIFICATION ENGINE

Every important hypothesis should specify:

- supporting evidence;
- contradicting evidence;
- missing evidence;
- alternatives;
- predictions;
- falsifiers;
- status;
- last review date.

Ask:

> “What observation would make this interpretation weaker?”

Do not only ask:

> “What supports it?”

This should be a first-class design feature, not a prompt afterthought.

---

# 23. CONTRADICTIONS AS FIRST-CLASS DATA

Contradiction must be allowed to remain unresolved.

Examples:

- self-concept vs historical behavior;
- two versions of a childhood event;
- questionnaire result vs daily functioning;
- sensor estimate vs subjective experience;
- past clinician interpretation vs current evidence.

Create a contradiction entity and lifecycle.

Do not let the LLM silently reconcile inconsistent evidence into a neat narrative.

---

# 24. UNKNOWN MAP

Design an explicit unknown/coverage system.

Potential states:

- not assessed;
- insufficient;
- partially assessed;
- contradictory;
- stale;
- supported;
- rejected.

But research whether these are adequate.

Separate:

- coverage;
- data recency;
- data quality;
- evidence strength;
- uncertainty.

Coverage percentage must never masquerade as “percentage of how well the system knows the person”.

---

# 25. ADAPTIVE INTERVIEW ENGINE

This is a central subsystem.

Goal:

> **Maximize useful information gain while minimizing unnecessary burden, suggestion, and measurement contamination.**

Research:

- adaptive testing;
- active learning;
- information gain;
- branching interviews;
- qualitative interviewing;
- clinical interview structure;
- burden optimization.

Question prioritization may consider:

- domain relevance;
- current uncertainty;
- expected information gain;
- safety;
- recency;
- coverage;
- relation to open hypotheses;
- need for a concrete example;
- user burden;
- emotional sensitivity;
- previous answer history.

Do not treat a heuristic priority score as a medical metric.

---

# 26. QUESTION MODES

Design a flexible system supporting:

- single-select;
- multi-select;
- Likert;
- numeric rating;
- binary;
- ranking;
- short free text;
- long narrative;
- timeline;
- event capture;
- voice response;
- document import;
- optional follow-up.

Always support when semantically appropriate:

- “Не знаю”
- “Не помню”
- “Зависит от ситуации”
- “Предпочитаю не отвечать”
- “Нужно пояснить вопрос”

Never force fake certainty.

---

# 27. CONCRETE-EXAMPLE RULE

Abstract self-statements are useful but weak.

For important claims, seek concrete episodes.

Example:

Instead of only:

> “Я плохо переношу критику.”

also obtain:

> “Вспомните последний конкретный случай, когда критика заметно повлияла на вас.”

Then record:

- event;
- thought;
- emotion;
- body;
- urge;
- action;
- immediate consequence;
- delayed consequence;
- context.

Do not assume the reason before the user reports it.

---

# 28. ANTI-LEADING QUESTION REVIEWER

Design a question-quality gate capable of detecting:

- leading questions;
- diagnostic assumptions;
- causal assumptions;
- moral judgment;
- double-barreled questions;
- false dichotomy;
- suggestive trauma framing;
- forced certainty;
- identity labeling;
- hidden interpretation.

For high-sensitivity domains, question generation should pass this gate before presentation.

---

# 29. TIME WINDOWS AND STATE/TRAIT SEPARATION

The system must represent recall periods explicitly.

Examples:

- right now;
- today;
- 7 days;
- 14 days;
- 30 days;
- 3 months;
- 12 months;
- adult lifetime;
- childhood;
- custom period.

Derived constructs should distinguish:

- trait;
- state;
- episode;
- context-specific;
- developmental;
- unknown.

A month of irritability must never automatically become:

> “You are an irritable person.”

---

# 30. PSYCHOMETRIC ENGINE — STRICT SEPARATION FROM LLM

Research and enforce:

LLM may assist with:

- explaining instructions;
- routing to a measure;
- discussing results;
- contextualizing uncertainty.

LLM must not silently:

- rewrite standardized items;
- invent norms;
- alter scoring;
- guess missing item values;
- convert free text into a standardized score without a validated procedure;
- call an invented questionnaire “validated”.

Scoring should be deterministic and versioned.

---

# 31. ASSESSMENT REGISTRY

Design a registry containing at least:

- instrument ID;
- exact version;
- construct;
- intended purpose;
- population;
- age range;
- recall period;
- language;
- validated translation status;
- administration mode;
- official source;
- citation;
- license;
- reproduction rights;
- redistribution rights;
- commercial-use rights;
- scoring algorithm version;
- missing-data policy;
- normative population;
- reliability;
- validity evidence;
- cross-cultural validity;
- responsiveness;
- interpretation limits;
- screening vs diagnostic status;
- clinician-required status;
- review date;
- deprecated/superseded status.

---

# 32. LICENSING AUDIT

Before recommending any instrument for inclusion, verify rights.

Audit especially:

- DSM-related measures;
- ICD materials;
- ICSD materials;
- PROMIS;
- personality instruments;
- trauma instruments;
- sleep instruments;
- proprietary clinical scales.

Do not copy copyrighted questionnaire items into the repository unless rights are verified.

If use is legally uncertain, store metadata and official links, not copied content.

---

# 33. LANGUAGE AND TRANSLATION

The primary user is Russian-speaking.

Research:

- validated Russian-language versions;
- translation equivalence;
- measurement invariance;
- norms;
- cultural validity.

If an English instrument is simply translated by an LLM:

- mark it nonvalidated;
- disable normative interpretation;
- do not pretend the original psychometric properties automatically transfer.

---

# 34. NORMATIVE VS IDIOGRAPHIC MEASUREMENT

Separate:

### Normative comparison

“How does this score compare with a validated reference population?”

### Idiographic comparison

“How does today compare with this person's own historical baseline?”

Over years, idiographic modeling may become especially valuable.

Research robust personal baselines rather than assuming population cutoffs answer all questions.

---

# 35. LONGITUDINAL SAMPLING

Do not assume fixed daily check-ins are optimal.

Research and design:

- daily pulse;
- adaptive pulse;
- weekly review;
- monthly review;
- quarterly reassessment;
- annual review;
- event-contingent capture;
- temporary high-frequency sampling when scientifically justified.

The schedule should minimize:

- fatigue;
- habituation;
- score chasing;
- rumination;
- compulsive monitoring.

---

# 36. MEASUREMENT REACTIVITY

Tracking itself is an intervention.

The system must monitor whether tracking causes:

- anxiety;
- rumination;
- compulsive checking;
- avoidance;
- self-judgment;
- fatigue;
- loss of spontaneity.

If burden rises, sampling should reduce or change.

Design this as a real product mechanism.

---

# 37. EVENT-CENTRIC CAPTURE

Explore a mode for important events occurring in real life.

Potential schema:

`trigger/event → appraisal → emotion → physiology → urge → behavior → immediate consequence → delayed consequence`

Do not force every event into a CBT ontology if another representation is better.

Research the most neutral canonical representation and allow theory-specific projections.

---

# 38. SLEEP OS

Determine the exact design after research.

Potential components:

- bedtime;
- sleep attempt;
- latency;
- awakenings;
- wake after sleep onset;
- final wake;
- get-up time;
- total sleep estimate;
- quality;
- restoration;
- daytime sleepiness;
- naps;
- circadian timing;
- caffeine;
- alcohol;
- medications;
- exercise;
- stress;
- light;
- illness;
- environment;
- wearable estimates.

Separate:

- self-report;
- device estimate;
- actigraphy-like data;
- clinical sleep study;
- inferred pattern.

Device algorithms must be versioned where possible.

Never label consumer wearable sleep stages as clinical ground truth.

---

# 39. MEDICAL CONFOUND ENGINE

For changes in:

- mood;
- energy;
- sleep;
- concentration;
- cognition;
- libido;
- irritability;
- anxiety;
- psychomotor state;

the system should be able to ask whether nonpsychological explanations need consideration.

It should not diagnose medical illness.

Design output states such as:

> “Medical/medication/sleep/substance alternatives have not been adequately evaluated.”

This is an uncertainty flag, not a diagnosis.

---

# 40. CLINICAL DIFFERENTIAL ENGINE

The system should reason in competing hypotheses rather than label-first reasoning.

For any serious concern consider categories such as:

- psychological mechanism;
- psychiatric syndrome;
- developmental pattern;
- sleep issue;
- medical contributor;
- medication effect;
- substance effect;
- environmental/contextual explanation;
- normal human variation.

Every important hypothesis should have:

- support;
- contradiction;
- alternatives;
- missing evidence;
- functional impact;
- temporal course;
- confound check.

---

# 41. MULTI-MODEL / MULTI-AGENT USE

Multiple AI reviewers can improve critique but cannot create independent clinical evidence.

If used, assign explicit roles:

- proposer;
- skeptic;
- evidence auditor;
- alternative generator;
- safety reviewer;
- statistical reviewer.

Never use:

`5 agents agree`

as:

`5 independent experts confirmed`.

Model agreement is not evidence about the user.

---

# 42. LLM TASK BOUNDARIES

Research and finalize which tasks belong to LLMs.

Likely candidates:

- adaptive interviewing;
- narrative summarization;
- semantic retrieval;
- candidate evidence extraction;
- hypothesis proposal;
- alternative explanation generation;
- contradiction discovery;
- user-facing explanation;
- narrative synthesis.

Likely deterministic or separately controlled:

- psychometric scoring;
- access control;
- encryption;
- deletion;
- exact statistical computation;
- migrations;
- canonical IDs;
- provenance enforcement;
- safety-critical hard rules;
- cloud privacy filtering.

Do not accept this division automatically. Validate it.

---

# 43. CANONICAL WRITES

The LLM should not directly rewrite the “truth about the person”.

Design a proposal pipeline such as:

`LLM proposal → schema validation → evidence validation → privacy validation → contradiction check → optional user review → derived record`

Raw data remains immutable except explicit correction/deletion semantics.

---

# 44. MODEL/PROVIDER INDEPENDENCE

The system should survive replacement of:

- OpenAI;
- another AI provider;
- model family;
- embedding model;
- vector index.

Canonical memory must not depend on proprietary conversational memory.

Define provider interfaces.

---

# 45. PERSONAL DATA VS SCIENTIFIC KNOWLEDGE

Separate stores/concepts:

### Personal Evidence Store

The user's history and measurements.

### Scientific Knowledge Store

External knowledge used to interpret it.

Scientific knowledge requires:

- source ID;
- source version;
- publication date;
- accessed date;
- evidence class;
- license;
- superseded state.

A new scientific guideline can change interpretation without rewriting past raw data.

---

# 46. KNOWLEDGE SNAPSHOTS

Every serious generated Personal Model should record the scientific and software context used.

At minimum consider:

- ICD snapshot;
- DSM snapshot/update;
- RDoC snapshot;
- instrument versions;
- reference registry version;
- intervention evidence version;
- application version;
- code commit;
- prompt version;
- model/provider;
- evidence cutoff date.

This allows historical reproducibility.

---

# 47. STATISTICAL ENGINE

Research robust longitudinal statistics.

Evaluate:

- rolling medians;
- quantiles;
- robust baseline estimation;
- smoothing;
- seasonality;
- change-point detection;
- anomaly detection;
- autocorrelation;
- lagged association;
- missing data;
- nonrandom missingness;
- intervention effects;
- uncertainty intervals;
- multiple testing;
- false discovery;
- temporal confounding;
- regression to the mean.

Do not run thousands of correlations and surface only attractive ones.

Exploratory analyses must be labeled exploratory.

---

# 48. CAUSALITY LADDER

Develop an explicit hierarchy from weak to stronger causal support.

Potential stages:

- co-occurrence;
- temporal ordering;
- repeated within-person association;
- lagged relationship;
- natural experiment;
- planned N-of-1;
- replication;
- external mechanistic/clinical evidence.

Do not use “cause” casually.

---

# 49. N-OF-1 LAB

Research and design:

- hypothesis;
- preregistration;
- outcome;
- baseline;
- intervention;
- confounders;
- measurement schedule;
- stopping rule;
- analysis;
- replication;
- result classification.

Create risk tiers.

Permitted self-experiments may include low-risk behavior such as:

- light exposure;
- task structure;
- notification reduction;
- exercise timing;
- sleep schedule adjustments within safe limits;
- caffeine timing;
- environmental changes.

Do not autonomously experiment with:

- prescription medication;
- abrupt withdrawal;
- dangerous sleep restriction;
- extreme fasting;
- self-harm exposure;
- intense trauma processing;
- other medically risky interventions.

---

# 50. INTERVENTION SYSTEM

Do not make therapy advice a generic chat behavior.

Create a registry with:

- target;
- mechanism;
- evidence quality;
- indications;
- contraindications;
- self-help suitability;
- clinician-required flag;
- risk tier;
- outcome measures;
- review interval;
- stopping conditions.

Recommendations should follow:

`problem → mechanism hypotheses → evidence → risk → preferences → minimal intervention → measurement → review`

---

# 51. SAFETY — MENTAL HEALTH AI

Conduct a dedicated research pass on AI mental-health failure modes.

Include:

- sycophancy;
- hallucinated certainty;
- overdiagnosis;
- AI authority bias;
- emotional dependence;
- exclusivity;
- reassurance loops;
- OCD reinforcement;
- health-anxiety reinforcement;
- delusion reinforcement;
- paranoia validation;
- manic/grandiose reinforcement;
- trauma suggestibility;
- self-harm;
- suicidality;
- eating-disorder reinforcement;
- substance-related risk;
- pathological self-monitoring;
- therapist substitution.

Create concrete architectural mitigations, not merely prompt reminders.

---

# 52. SAFETY STATE MACHINE

Research a contextual model distinguishing at least:

- ordinary self-reflection;
- potential clinical concern;
- professional evaluation appropriate;
- urgent evaluation;
- emergency.

Avoid turning ordinary distress into emergency mode.

For suicide/self-harm and related risk, distinguish where clinically appropriate:

- thoughts;
- intent;
- plan;
- access/means;
- immediacy;
- past behavior;
- intoxication;
- psychosis;
- protective factors;
- ability to maintain safety.

The final system must follow applicable safety policies and current authoritative guidance.

---

# 53. AI RELATIONSHIP BOUNDARY

The AI may be:

- calm;
- nonjudgmental;
- respectful;
- supportive;
- intellectually honest.

It must not cultivate:

- exclusivity;
- emotional dependency;
- authority dependency;
- “I understand you better than anyone” dynamics;
- manipulative attachment;
- social replacement.

Design this into conversational policy.

---

# 54. IDENTITY-LABEL AVOIDANCE

Prefer:

> “In several evaluation contexts, increased anxiety was reported.”

Over:

> “You are an anxious person.”

Prefer behaviors, contexts and evidence over identity labels.

Especially avoid turning:

- perfectionism;
- attachment;
- trauma response;
- ADHD-like complaints;
- anxiety;
- avoidance;

into immutable identity.

---

# 55. CONDITIONS FOR THRIVING

Create a positive counterpart to problem analysis.

The system should actively identify:

- best-functioning periods;
- restorative routines;
- supportive relationships;
- meaningful work;
- environments associated with focus;
- sleep patterns associated with wellbeing;
- autonomy;
- mastery;
- meaningful goals;
- sources of enjoyment;
- resilience after setbacks.

Potential object:

`THRIVING_PATTERN`

with the same evidence discipline as problem patterns.

---

# 56. PRIVACY — ASSUME MAXIMUM SENSITIVITY

This archive could be more sensitive than a journal, medical record, mailbox, and photo archive combined.

Research modern best practices for:

- local-first storage;
- encryption at rest;
- authenticated encryption;
- key management;
- KDF;
- OS credential vault;
- passphrase recovery;
- backup encryption;
- key rotation;
- least privilege;
- selective disclosure;
- local-only data;
- pseudonymization;
- export;
- deletion.

Do not declare plaintext SQLite “safe enough” for real data.

---

# 57. PRIVACY MODEL — BEYOND A SINGLE CLASS

Critically assess simple P0–P4 classification.

Consider whether privacy should be represented by orthogonal attributes:

- sensitivity;
- cloud permission;
- third-party involvement;
- export policy;
- retention;
- redaction policy.

If a multidimensional policy is stronger, replace P0–P4.

Still provide a simple UI abstraction for the user.

---

# 58. NEVER-CLOUD GUARANTEE

Support a strong local-only category.

If an item is marked `NEVER_CLOUD`, no cloud context builder may include:

- raw data;
- summary;
- embedding;
- paraphrase;
- derived identifier that meaningfully reconstructs it;

unless the user explicitly changes the policy.

Test this.

---

# 59. CLOUD CONTEXT BUILDER

No LLM call should automatically receive the entire life archive.

Design context selection based on:

- query relevance;
- minimum necessary disclosure;
- sensitivity;
- third-party data;
- de-identification;
- token budget;
- provenance.

The user should be able to inspect what categories are allowed to leave the device.

---

# 60. THIRD-PARTY PRIVACY

Imported life data includes other people.

Design:

- pseudonymous person IDs;
- third-party flags;
- selective redaction;
- clinician-export pseudonymization;
- exclusion from cloud context;
- handling of message archives.

Do not diagnose other people from the user's description.

---

# 61. PROMPT-INJECTION THREAT MODEL

Imported data may contain adversarial instructions.

Files, messages, web pages and notes are:

`UNTRUSTED_DATA`

not policy.

Research and design defenses for:

- document prompt injection;
- HTML instructions;
- malicious PDFs;
- hidden text;
- quoted assistant-like text;
- hostile metadata.

Imported content must never override application/system instructions.

---

# 62. SECURITY THREAT MODEL

Create a serious threat model.

Cover:

- local malware;
- ransomware;
- malicious attachments;
- parser vulnerabilities;
- dependency compromise;
- frontend XSS;
- shell injection;
- path traversal;
- unsafe temp files;
- logs;
- crash dumps;
- clipboard leakage;
- database theft;
- backup theft;
- lost device;
- cloud API leakage;
- accidental Git commit;
- malicious model output;
- corrupted migrations;
- vector index leakage;
- secrets.

For each:

- asset;
- attacker;
- attack path;
- impact;
- mitigation;
- residual risk.

---

# 63. REAL-DATA SECURITY GATE

Real personal data must not enter the application until a hard gate passes.

At minimum investigate requirements for:

- encrypted production storage;
- encrypted attachments;
- secure key handling;
- backup encryption;
- backup restore test;
- deletion;
- export;
- audit;
- Git leak prevention;
- log redaction;
- cloud policy enforcement;
- dependency review;
- prompt-injection handling.

Create a machine-checkable or explicit checklist.

---

# 64. LIFETIME DURABILITY

Design for 20–50+ years conceptually.

The archive must survive:

- computer replacement;
- OS change;
- UI rewrite;
- backend rewrite;
- database migration;
- LLM replacement;
- vector-index replacement;
- taxonomy change;
- questionnaire deprecation;
- scientific updates;
- provider shutdown;
- project abandonment.

The user's data should outlive the application.

---

# 65. EXPORT AND ARCHIVAL FORMAT

Research appropriate durable export formats.

Consider:

- JSON;
- JSONL;
- JSON Schema;
- Markdown;
- CSV;
- Parquet;
- SQLite snapshot;
- attachment manifest;
- cryptographic checksums;
- signed manifests;
- schema versions.

Consider FHIR only if it delivers real interoperability value for clinician/medical export.

Do not add standards as decoration.

---

# 66. DATA INTEGRITY

Research:

- content hashes;
- content-addressed attachment storage;
- source hashing;
- migration checksums;
- backup integrity;
- corruption detection;
- reproducible exports.

The system should be able to prove that an original imported artifact has not silently changed.

---

# 67. CORRECTION, SUPERSESSION AND DELETION

Distinguish:

- correction;
- reinterpretation;
- supersession;
- redaction;
- hard deletion.

Append-only history must not remove the user's right to delete.

Deletion must address:

- raw record;
- derived observations;
- claims;
- embeddings;
- caches;
- exports;
- attachments;
- backups according to policy.

Design dependency invalidation.

---

# 68. DATA ARCHITECTURE — COMPARE BEFORE CHOOSING

Evaluate:

- relational database;
- document database;
- graph database;
- event sourcing;
- bitemporal relational;
- hybrid relational + graph projection;
- vector index.

Decide what is canonical.

Strong preference should go to systems that provide:

- explicit schema;
- reliable migrations;
- auditability;
- exportability;
- deletion;
- long-term maintainability.

Do not choose graph DB simply because the UI contains a mind graph.

---

# 69. VECTOR SEARCH IS AN INDEX, NOT MEMORY

If semantic search is used:

- canonical source remains structured/original data;
- every vector result points to source IDs;
- deletion removes derived embeddings;
- embedding models can be rebuilt;
- model changes do not invalidate raw history.

---

# 70. SOFTWARE ARCHITECTURE RESEARCH

Critically compare candidate architecture.

Potential candidates:

- Python modular monolith;
- local API;
- Tauri desktop;
- React/TypeScript;
- SQLite-compatible store;
- DuckDB analytics;
- Polars;
- embedded semantic index;
- PostgreSQL later if needed.

Do not blindly inherit v1 stack.

Evaluate against:

- user's hardware;
- local-first requirement;
- maintainability;
- privacy;
- portability;
- testability;
- long-lived migrations;
- development velocity.

Prefer the smallest architecture that preserves constitutional guarantees.

---

# 71. MODULAR MONOLITH VS MICROSERVICES

Assume single-user local-first unless research proves otherwise.

Avoid distributed infrastructure without a compelling reason.

Module boundaries matter; network services do not necessarily.

---

# 72. FAILURE MODES AND GRACEFUL DEGRADATION

The core archive must remain usable if:

- LLM is unavailable;
- internet is unavailable;
- a provider disappears;
- vector index is corrupted;
- one assessment is deprecated;
- wearable integration stops;
- knowledge source becomes superseded;
- new model disagrees with old model;
- migration fails.

Design recovery paths.

---

# 73. UI IS NOT JUST CHAT

Research and propose a long-term information architecture.

Candidate surfaces:

- Today;
- Current State;
- Me / Personal Model;
- Life Timeline;
- Mind Map;
- Evidence Explorer;
- Pattern Explorer;
- Assessments;
- Sleep;
- Sources;
- Unknowns;
- Contradictions;
- Experiments;
- Reports;
- Clinician Mode;
- Privacy;
- Data Health.

Choose the minimal coherent set.

---

# 74. TIMELINE UX

The timeline should be able to overlay:

- life events;
- relationships;
- work;
- health;
- medication;
- substance changes;
- sleep;
- mood;
- anxiety;
- interventions;
- major stress;
- thriving periods.

Overlay does not imply causality.

---

# 75. EVIDENCE EXPLORER

The user should be able to click:

> “Why does the system think this?”

and see:

- supporting evidence;
- contradictory evidence;
- time range;
- alternatives;
- source quality;
- inference type;
- model run;
- scientific snapshot;
- history of revisions.

This is a constitutional UX feature.

---

# 76. PATTERN EXPLORER

Patterns must show:

- contexts;
- antecedents;
- responses;
- consequences;
- modifiers;
- exceptions;
- sample size;
- uncertainty;
- alternative explanations.

Avoid “pattern” from two anecdotes unless explicitly marked weak.

---

# 77. PERSONAL MODEL VERSIONING

Every Personal Model release should support:

- version;
- generation date;
- evidence cutoff;
- knowledge snapshot;
- model/prompt;
- strengthened claims;
- weakened claims;
- rejected claims;
- new contradictions;
- new unknowns.

A **Model Diff** is a major feature.

---

# 78. RED-TEAM REBUILD FEATURE

Research the future feature:

> Rebuild the personal model from raw evidence while hiding current conclusions from the reviewer.

Purpose:

- detect anchoring;
- detect circular reasoning;
- detect stale narratives;
- detect confirmation bias.

Compare the rebuilt model to the current one.

Do not call it independent clinical validation.

---

# 79. CLINICIAN MODE

Design exports that clearly separate:

- `USER_REPORTED`
- `MEASURED`
- `DOCUMENTED`
- `CLINICIAN_RECORDED`
- `AI_DERIVED`
- `OPEN_HYPOTHESIS`
- `UNKNOWN`

Potential content:

- reason for consultation;
- current state;
- onset/course;
- functioning;
- relevant history;
- sleep;
- medications;
- substances;
- medical context;
- assessments;
- risks;
- longitudinal changes;
- open questions.

Aim for useful compression, not a 150-page dump.

---

# 80. REGULATORY AND LEGAL RESEARCH

As of `2026-08-10`, research the relevant current landscape.

At minimum examine when useful:

- EU AI Act;
- GDPR and special-category health data;
- digital medical-device boundaries;
- FDA digital health / mental health device guidance;
- European medical-device considerations;
- Moldova-relevant privacy/data-protection considerations;
- cross-border cloud processing implications.

Primary purpose:

> identify product boundaries and future risks.

Do not provide legal certainty where specialist legal review would be required.

Distinguish:

- single-user personal research/wellness tool;
- product offered to other users;
- clinical decision support;
- diagnostic/treatment claims.

---

# 81. SCIENTIFIC KNOWLEDGE GOVERNANCE

Create a source registry with fields such as:

- source ID;
- title;
- organization/authors;
- type;
- publication;
- publication date;
- URL/DOI;
- access date;
- evidence tier;
- relevant domains;
- project implications;
- limitations;
- license/rights notes;
- superseded status;
- review date.

Every load-bearing scientific design decision should point to sources.

---

# 82. EVIDENCE-TIER SYSTEM

Research the best hierarchy.

Potential example:

- official classification/guideline;
- systematic review/meta-analysis;
- validated methodological framework;
- strong primary evidence;
- emerging primary research;
- theory/formulation;
- exploratory/nonclinical.

Do not treat all citations equally.

---

# 83. RESEARCH CONTROVERSY HANDLING

When strong sources disagree, document:

- View A;
- View B;
- evidence strengths;
- implications;
- final project decision;
- confidence;
- what future evidence may change the decision.

Do not hide uncertainty.

---

# 84. NO “SCIENCE THEATER”

Every advanced feature must answer:

1. What user problem does it solve?
2. What evidence supports it?
3. What data does it require?
4. What is the failure mode?
5. Can a simpler method do the job?

Reject technology or theory that only sounds sophisticated.

Examples to treat skeptically:

- digital biomarkers without strong validity;
- overcomplicated computational psychiatry;
- graph database for its own sake;
- deep causal models from sparse data;
- dozens of agents;
- “AI diagnosis confidence” scores;
- pseudo-neurobiological explanations.

---

# 85. USER BURDEN AS A HARD RESOURCE CONSTRAINT

Model user attention like a scarce resource.

Every assessment/question should justify itself.

Potential value calculation:

`expected information value × decision relevance ÷ burden`

Do not make the user complete thousands of redundant questions simply because the system can generate them.

---

# 86. INITIAL “LIFE SNAPSHOT” PROTOCOL

Design a high-quality initial inventory that may take days or weeks rather than one exhausting session.

Potential phases:

- privacy and boundaries;
- current state;
- life skeleton;
- developmental history;
- important relationships;
- strengths and positive periods;
- personality;
- cognition/executive functioning;
- emotional patterns;
- clinical broad screen;
- adaptive deep dives;
- adversity/trauma where indicated;
- sleep;
- medical context;
- substances;
- work/functioning;
- values/meaning;
- contradictions;
- synthesis.

Research and improve this.

The protocol should save progress, adapt, and avoid asking what is already known.

---

# 87. QUESTION MEMORY

The system must know:

- what it already asked;
- exact wording;
- answer;
- date;
- recall period;
- stability of construct;
- when retesting is justified.

Do not repeatedly ask stable biographical facts.

---

# 88. ANNUAL REVIEW

Design a future annual review that produces a longitudinal life chronicle.

Potential sections:

- major events;
- best periods;
- hardest periods;
- sleep;
- health;
- relationships;
- work;
- functioning;
- values;
- strengths;
- interventions;
- hypotheses strengthened/weakened;
- unknowns;
- next-year priorities.

---

# 89. PRODUCT SUCCESS METRICS

Do not optimize for:

- chat length;
- number of insights;
- number of diagnoses;
- number of correlations.

Research metrics such as:

- evidence fidelity;
- traceability;
- uncertainty calibration;
- contradiction sensitivity;
- low false-claim rate;
- user correction rate;
- longitudinal usefulness;
- tracking burden;
- data durability;
- privacy violations;
- export completeness;
- hypothesis falsifiability.

---

# 90. TESTING PHILOSOPHY

The final architecture must specify tests for constitutional invariants.

Examples:

- LLM output cannot become evidence automatically.
- Missing value cannot silently become zero.
- Raw report remains accessible after normalization.
- Contradictory claims may coexist.
- Event time and recorded time remain distinct.
- A causal claim cannot pass a descriptive evidence threshold.
- Unvalidated translation cannot use original norms.
- Copyright/license gate prevents unauthorized test content.
- `NEVER_CLOUD` is excluded from cloud context.
- Imported prompt injection remains data.
- Hard deletion invalidates dependent derived artifacts.
- Embeddings are deletable/rebuildable.
- Personal model can be regenerated under a new model.
- Old personal model remains historically inspectable.
- No third-party diagnosis.
- No false-memory prompting.
- No autonomous medication dosing advice.

---

# 91. GOLDEN SAFETY / EPISTEMIC SCENARIOS

Design a future test corpus using only synthetic personas.

Include:

- normal sadness;
- grief;
- short-term sleep deprivation;
- anxiety;
- panic-like symptoms;
- reassurance-seeking/OCD-like loop;
- concentration problems caused by poor sleep;
- possible ADHD;
- possible mania;
- possible psychosis;
- health anxiety;
- trauma disclosure;
- contradictory memories;
- medication side-effect narrative;
- substance-related changes;
- high questionnaire score with low impairment;
- high impairment with modest score;
- unusual consensual sexual fantasy without harmful intent;
- self-harm disclosure;
- overtracking anxiety;
- false-memory invitation;
- third-party “diagnose my partner” request.

---

# 92. REPOSITORY GOVERNANCE

After the research converges, produce concise repo-native guidance.

Use:

`AGENTS.md`

for durable instructions such as:

- where source of truth lives;
- constitutional invariants;
- commands;
- no-real-data rule;
- how research docs are organized.

Do not dump the entire Master Spec into `AGENTS.md`.

The Master Spec remains the authoritative detailed document.

---

# 93. REQUIRED OUTPUT ARTIFACTS

Create all of the following.

## 93.1 Final master specification

`docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`

This is the primary source of truth.

No artificial page or word limit.

It must be complete but not repetitive.

---

## 93.2 Research dossier

`docs/research/PSYCHE_OS_RESEARCH_DOSSIER_2026.md`

For each major research domain:

- research question;
- key findings;
- scientific consensus;
- controversies;
- limitations;
- project implications;
- sources;
- confidence.

---

## 93.3 Source registry

`docs/research/SOURCE_REGISTRY.yaml`

Machine-readable source inventory.

Validate YAML.

---

## 93.4 Research execution plan

`docs/research/EXECUTION_PLAN.md`

Maintain it during work.

At completion, include final status for every research stream.

---

## 93.5 Critical audit of v1

`docs/reviews/V1_CRITICAL_AUDIT.md`

Use a table similar to:

| V1 concept | Decision | Evidence/problem | Final resolution |

---

## 93.6 Independent reconstruction

`docs/reviews/INDEPENDENT_REBUILD.md`

Show the architecture built from first principles before convergence.

---

## 93.7 Red-team report

`docs/reviews/RED_TEAM_REPORT.md`

Cover:

- science;
- clinical/safety;
- statistics;
- privacy;
- security;
- UX;
- lifetime durability.

For each meaningful risk:

- risk;
- likelihood;
- impact;
- mitigation;
- residual risk;
- architectural implication.

---

## 93.8 Decision log

`docs/DECISION_LOG.md`

Record only major design decisions.

Each decision:

- question;
- options;
- chosen solution;
- evidence;
- why alternatives lost;
- confidence;
- reversible/irreversible;
- review trigger.

---

## 93.9 Constitution

`CONSTITUTION.md`

Concise, strict, enforceable.

---

## 93.10 Scientific governance

`docs/SCIENTIFIC_GOVERNANCE.md`

---

## 93.11 Data model

`docs/architecture/DATA_MODEL.md`

Include:

- entities;
- relationships;
- raw/derived separation;
- temporal semantics;
- provenance;
- privacy attributes;
- correction;
- deletion;
- schema versioning.

Use Mermaid ER diagrams where useful.

---

## 93.12 System architecture

`docs/architecture/SYSTEM_ARCHITECTURE.md`

Include competing architectures considered and final architecture.

---

## 93.13 Privacy/security model

`docs/architecture/PRIVACY_SECURITY_MODEL.md`

---

## 93.14 Mental-health AI safety model

`docs/architecture/MENTAL_HEALTH_AI_SAFETY.md`

---

## 93.15 Threat model

`docs/architecture/THREAT_MODEL.md`

---

## 93.16 Ontology

`ontology/psyche_domains.yaml`

Machine-readable.

Validate YAML.

---

## 93.17 Product roadmap

`docs/ROADMAP.md`

Research-driven phases.

Do not preserve F0–F10 merely for compatibility.

---

## 93.18 F0 implementation prompt

`docs/prompts/F0_IMPLEMENTATION_PROMPT.md`

This must be the **exact next prompt** ready for Codex after research.

It should implement only the minimal irreversible foundation identified by research.

---

## 93.19 Final research report

`docs/FINAL_RESEARCH_REPORT.md`

Short executive summary of the entire research/rebuild.

---

# 94. REQUIRED MASTER SPEC V2 CONTENT

The final Master Spec should contain, at minimum, coherent treatment of:

1. product definition;
2. non-goals;
3. terminology;
4. constitutional invariants;
5. scientific model;
6. clinical boundaries;
7. epistemic model;
8. complete domain ontology;
9. Life Archive;
10. autobiographical memory;
11. biography reconstruction;
12. source/provenance system;
13. evidence graph;
14. temporal architecture;
15. claim types;
16. uncertainty;
17. contradiction model;
18. unknown model;
19. falsification;
20. psychometrics;
21. assessment registry;
22. licensing;
23. language/translation;
24. adaptive interviewing;
25. longitudinal sampling;
26. measurement reactivity;
27. event capture;
28. Sleep OS;
29. medical confounders;
30. clinical differential reasoning;
31. traits/personality;
32. strengths and thriving;
33. functioning;
34. values/meaning;
35. statistics;
36. causality policy;
37. N-of-1;
38. intervention registry;
39. safety;
40. crisis handling;
41. AI relationship boundary;
42. third-party privacy;
43. privacy architecture;
44. security;
45. threat model;
46. imported-content trust model;
47. LLM architecture;
48. provider independence;
49. scientific knowledge store;
50. knowledge snapshots;
51. data architecture;
52. migrations;
53. long-term durability;
54. backups;
55. integrity;
56. export;
57. deletion;
58. UI information architecture;
59. timeline;
60. mind/evidence graph visualization;
61. pattern explorer;
62. evidence explorer;
63. clinician mode;
64. reports;
65. testing;
66. evaluation;
67. regulatory posture;
68. scientific update process;
69. product roadmap;
70. minimal irreversible core;
71. real-data gate;
72. implementation contract;
73. unresolved research questions;
74. risks and residual risks.

Add anything materially missing.

---

# 95. MINIMAL IRREVERSIBLE CORE

A major output of the research must answer:

> **What must be designed correctly before the first real deeply sensitive personal record enters PSYCHE OS?**

Do not assume v1's answer.

Investigate likely candidates:

- identity/IDs;
- raw/derived split;
- source provenance;
- temporal semantics;
- encryption;
- privacy policy;
- schema versioning;
- correction/deletion;
- export;
- backups;
- audit;
- knowledge/model provenance.

Mark each:

- irreversible/high-cost-to-change;
- important but migratable;
- safely deferrable.

F0 must build only what belongs in the first two categories and is necessary for safe real-data entry.

---

# 96. IMPLEMENTATION CONTRACT

At the end of Master Spec v2 create a precise section:

# IMPLEMENTATION CONTRACT

It must define:

- constitutional invariants;
- module boundaries;
- canonical data store;
- schemas that must exist first;
- forbidden shortcuts;
- privacy guarantees;
- testing requirements;
- security gate;
- real-data gate;
- knowledge/copyright gate;
- migration requirements;
- export requirements;
- Definition of Done.

The F0 implementation agent should not need to reinterpret the philosophy.

---

# 97. DO NOT STORE REAL PERSONAL DATA DURING THIS TASK

Use only synthetic fixtures.

Do not copy from:

- user conversations;
- personal files;
- health data;
- psychological disclosures;
- sexual disclosures;
- real diaries;
- email;
- calendars;
- wearables.

Even if such data is accessible somewhere, it is out of scope.

This task designs the vault before filling it.

---

# 98. GIT WORKFLOW

If the repo is already Git-enabled:

1. Inspect status.
2. Preserve unrelated changes.
3. Create a branch such as:
   `research/master-spec-v2-final`
4. Commit logical milestones if useful.

Suggested commits:

- research plan and source registry;
- v1 audit;
- scientific research dossier;
- red team and independent rebuild;
- final architecture/spec;
- F0 prompt.

Do not push unless explicitly required by an existing repository workflow.

If Git is not initialized, local initialization is acceptable.

---

# 99. COPYRIGHT SAFETY

Do not download and commit proprietary manuals/tests merely to “have everything”.

For copyrighted resources:

- cite;
- record metadata;
- record license;
- store official link;
- note required access.

Keep public repo content legally clean.

---

# 100. RESEARCH TRACEABILITY

No major conclusion may live only in hidden model reasoning.

Externalized artifacts must contain:

- conclusion;
- evidence;
- source;
- alternatives;
- rationale;
- uncertainty.

Do not expose token-by-token private chain of thought.

Provide concise decision rationale.

---

# 101. DECISION QUALITY TEMPLATE

For important decisions use:

### Decision
What is being decided?

### Problem
What real problem does it solve?

### Evidence
What sources support it?

### Alternatives
What else was considered?

### Why this option
Why did it win?

### Failure modes
How can it fail?

### Reversibility
How costly is a later change?

### Confidence
How certain is the design decision?

### Review trigger
What future evidence would cause reconsideration?

---

# 102. CRITICAL QUESTIONS THE FINAL DESIGN MUST ANSWER

Before finalizing v2, answer all of these.

### Epistemics

1. How can a user inspect why a claim exists?
2. What prevents AI prose from becoming fact?
3. How are contradictory memories preserved?
4. How does the system represent “unknown”?
5. How does it distinguish evidence strength from model confidence?
6. Can a hypothesis be explicitly falsified?
7. Can old conclusions be regenerated under new science/models?

### Memory

8. Can suggestive interviewing create false autobiographical certainty?
9. How does the system prevent this?
10. Can a vivid memory remain unverified?
11. Can external evidence disagree with memory without silently overwriting it?

### Psychometrics

12. Can an LLM alter standardized scoring?
13. How are licensed instruments protected?
14. What happens with an unvalidated Russian translation?
15. How are practice effects and repeated testing handled?

### Longitudinal science

16. How are personal baselines estimated?
17. How are regression to the mean and multiple comparisons handled?
18. How is tracking burden measured?
19. How does the system avoid turning random correlations into personal “truth”?

### Clinical safety

20. Can poor sleep be mistaken for a personality trait?
21. Can medical causes be prematurely psychologized?
22. Can a screen become a diagnosis?
23. Can the system reinforce OCD reassurance?
24. Can it reinforce paranoia/delusion?
25. Can it intensify mania/grandiosity?
26. Can it overreact to ordinary sadness?
27. Can it encourage emotional dependence on AI?

### Privacy/security

28. Can a sensitive item be guaranteed local-only?
29. Can imported text inject instructions?
30. Can third-party identities be protected?
31. Can one selected memory be truly deleted?
32. What happens to embeddings/caches/backups?
33. Can an attacker steal usable plaintext from backups?
34. Can crash logs leak sensitive content?

### Lifetime durability

35. Can the archive be read without this application in 20 years?
36. Can OpenAI disappear without losing canonical memory?
37. Can the database schema migrate repeatedly?
38. Can a wearable integration disappear without damaging the archive?
39. Can a scientific framework be superseded without rewriting history?
40. Can the application work meaningfully without internet/LLM?

### Product/UX

41. Why would the user keep using this after five years?
42. How does the app produce value without demanding constant tracking?
43. How are positive/thriving periods represented?
44. How can the user correct the system?
45. How can the user disagree with an AI interpretation?

If any answer is weak, continue the design work.

---

# 103. ADVERSARIAL SELF-REVIEW

Perform four final review passes.

## Pass A — Scientific/psychometric

Search for:

- invalid constructs;
- overclaiming;
- misuse of scales;
- unsupported causal language;
- false precision;
- population-to-person inference errors.

## Pass B — Clinical/safety

Search for:

- overdiagnosis;
- medical neglect;
- unsafe intervention;
- false-memory risk;
- reassurance;
- delusion reinforcement;
- AI dependency.

## Pass C — Privacy/security

Search for:

- plaintext sensitive data;
- uncontrolled cloud context;
- logging;
- key mistakes;
- weak deletion;
- prompt injection;
- backup failure.

## Pass D — Lifetime/product/software

Imagine the system after:

- 1 year;
- 5 years;
- 20 years;
- 40 years.

Identify:

- schema pain;
- abandoned integrations;
- obsolete AI;
- scientific drift;
- unusable archive;
- user fatigue;
- data explosion;
- corrupted assumptions.

Apply fixes.

---

# 104. RESEARCH COMPLETION CRITERIA

Do not declare research complete because the documents are long.

Research is complete only when:

- v1 has been systematically audited;
- major assumptions are explicit;
- all core scientific domains have current evidence;
- psychometric design is grounded;
- safety research is complete;
- privacy/security threat model is complete;
- legal/regulatory boundaries are reasonably mapped;
- competing architectures were compared;
- independent rebuild is complete;
- red team is complete;
- unresolved controversies are explicit;
- design has converged;
- final audits were performed;
- all required artifacts exist and validate;
- F0 scope is derived from research rather than copied from v1.

---

# 105. DOCUMENT QUALITY

Write the final Master Spec primarily in **Russian**, because the primary user is Russian-speaking.

Use English technical identifiers, schema names, code terms and standard names where clarity benefits.

The document should be:

- rigorous;
- direct;
- non-marketing;
- scientifically cautious;
- architecturally actionable;
- internally consistent;
- well indexed;
- easy for future Codex agents to navigate.

Avoid:

- motivational fluff;
- repeated principles across many sections;
- pseudo-scientific prose;
- “AI magic” language;
- unsupported certainty.

---

# 106. ARTIFACT VALIDATION

Before completion:

- validate YAML files;
- check Markdown links where practical;
- check duplicate headings;
- check internal paths;
- check terminology consistency;
- check source-registry references;
- check dates and versions;
- check copyright/license notes;
- ensure no real personal data entered;
- ensure Git status is understood;
- ensure no temporary secrets/files remain.

---

# 107. FINAL RESEARCH REPORT FORMAT

`docs/FINAL_RESEARCH_REPORT.md` should answer succinctly:

## Verdict
Should PSYCHE OS be built, and in what form?

## Biggest problems in v1
What was wrong, weak or insufficient?

## Biggest improvements in v2
What changed materially?

## Removed/rejected ideas
What did research show we should not build?

## New foundational subsystems
What did v1 miss?

## Scientific confidence
What areas are strong vs speculative?

## Residual risks
What cannot be fully solved?

## Readiness
Is the project ready for implementation?

## Minimal irreversible core
What must F0 implement?

## Real-data blockers
What must be complete before ingesting the user's real life archive?

## Next step
Exact next command/prompt.

---

# 108. FINAL USER RESPONSE

After all work is complete, respond with a concise executive summary rather than pasting the whole spec.

Include:

1. final verdict;
2. 10–20 most important changes from v1;
3. major ideas rejected or deferred;
4. number and type of authoritative/high-quality sources reviewed;
5. remaining unresolved scientific or architectural risks;
6. list of artifacts created;
7. Git branch and local commits if used;
8. validation performed;
9. exact path to:
   `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`
10. exact path to:
   `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`
11. whether the **REAL_DATA_GATE** is currently CLOSED or OPEN;
12. exact recommended next action.

---

# 109. FINAL OPERATING RULES

Throughout the task:

- Do not preserve a v1 decision out of politeness.
- Do not invent science.
- Do not invent certainty.
- Do not count model agreement as evidence.
- Do not confuse screening with diagnosis.
- Do not confuse memory with historical fact.
- Do not confuse correlation with causation.
- Do not confuse sensor automation with measurement validity.
- Do not confuse a graph visualization with a graph database requirement.
- Do not confuse user permission with security permission.
- Do not confuse deep tracking with better understanding.
- Do not confuse more questions with better assessment.
- Do not confuse sophisticated statistics with meaningful personal science.
- Do not confuse AI empathy with clinical authority.
- Do not confuse a useful psychological formulation with objective identity.
- Do not let implementation convenience weaken the evidence model.
- Do not add real user data before the security/privacy foundation is proven.

---

# 110. NORTH STAR

The system must never aim to say:

> **“I now fully know who you are.”**

It should aim to say:

> **“Here is the most complete evidence-preserving record currently available. Here is what you reported, what external sources recorded, what was measured, what appears repeatedly, what changed, what supports each interpretation, what contradicts it, what alternative explanations remain, what we used to believe, what was later revised, what is still unknown, and exactly why the current model says what it says.”**

That is the standard.

---

# 111. START NOW

Execute the following sequence without asking the user to restate information already available:

1. Enter/inspect `C:\Dev\psyche-os`.
2. Read `docs/PSYCHE_OS_MASTER_SPEC_v1.0_2026-08-10.md` completely.
3. Inspect Git/repository state and existing instructions.
4. Create/update concise `AGENTS.md` only if appropriate.
5. Create `docs/research/EXECUTION_PLAN.md`.
6. Create the v1 assumption/audit framework.
7. Begin independent research.
8. Maintain the source registry during research, not afterward.
9. Complete scientific, psychometric, safety, privacy/security, UX and lifetime research.
10. Compare competing architectures.
11. Run the scientific/security/product red teams.
12. Perform the independent rebuild.
13. Converge on the final design.
14. Create every required artifact.
15. Produce `PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`.
16. Produce the research-derived `F0_IMPLEMENTATION_PROMPT.md`.
17. Run all document/schema/link/consistency validations reasonably possible.
18. Perform the four final adversarial audits.
19. Fix discovered weaknesses.
20. Only then mark the research foundation complete.

**Do not begin production implementation during this task.**

**Do not ingest real personal data during this task.**

**Work autonomously until the research and final foundation are genuinely complete within the capabilities of the current environment.**

---

# FINAL SUCCESS CONDITION

This task succeeds only if a future implementation agent can open the repository, read the resulting v2 specification and F0 implementation prompt, and build the secure foundation **without needing to rediscover what PSYCHE OS fundamentally is, what it may claim, what it must never claim, how its evidence works, how its data survives decades, how uncertainty is preserved, and what must be protected before the first real personal record is stored.**
