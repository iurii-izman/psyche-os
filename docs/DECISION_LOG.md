# PSYCHE OS v2 decision log

**Snapshot:** 2026-08-10  
**Status:** research convergence record  
**Notation:** source IDs resolve in `docs/research/SOURCE_REGISTRY.yaml`. Confidence concerns the project decision, not universal scientific certainty.

## Decision protocol

Each decision records: `decision → research question → evidence → alternatives → rationale → uncertainty → review trigger`. A decision is revisable through supersession; history is not rewritten.

## Decisions

### ADR-001 — Product identity

- **Decision:** Name the category **Personal Evidence & Reflection System**. `PersonalModelSnapshot` is a dated derived artefact. Reject “digital twin”, “complete mental model” and autonomous therapist framing.
- **Question:** What claim remains useful without implying exhaustive or clinical knowledge?
- **Evidence:** [ARCH-012–ARCH-015] plus the clinical workstream's classification, phenomenology and lifespan evidence.
- **Alternatives:** v1 “Personal Mental Model”; clinical companion; quantified-self dashboard.
- **Rationale:** The chosen frame makes provenance, incompleteness, revisions and user authority visible.
- **Uncertainty:** Users may still anthropomorphize polished language.
- **Review trigger:** usability testing shows persistent identity/clinical over-attribution.
- **Confidence:** high.

### ADR-002 — Canonical architecture

- **Decision:** Use a hybrid bitemporal relational canonical store, encrypted immutable source objects, version rows and minimal append-only audit metadata; keep graph/vector/search/analytics as rebuildable projections.
- **Question:** Which architecture best balances correction, historical views, deletion, portability and decades-long recovery?
- **Evidence:** [ARCH-027–ARCH-030, ARCH-041–ARCH-048].
- **Alternatives:** state-only modular relational; full event-sourced core.
- **Rationale:** The hybrid retains temporal/audit meaning without making every state depend on replay or preserving erased content.
- **Uncertainty:** More complex than a state-only schema; deletion lineage needs disciplined implementation.
- **Review trigger:** synthetic migration/deletion exercises cannot prove deterministic rebuild or acceptable recovery time.
- **Confidence:** high.

### ADR-003 — Local core profile

- **Decision:** F0 is a Python 3.12+ domain/storage CLI with no network listener; SQLite/SQLCipher is the proposed profile. A desktop shell is a later typed-IPC adapter.
- **Question:** What smallest implementation can prove irreversible invariants with minimal attack surface?
- **Evidence:** [ARCH-026–ARCH-030, ARCH-037].
- **Alternatives:** browser-first localhost service; Tauri desktop first; PostgreSQL service.
- **Rationale:** A no-listener CLI isolates storage contracts and permits deterministic synthetic tests before UI complexity.
- **Uncertainty:** SQLCipher packaging and platform key-store adapters need proof.
- **Review trigger:** packaging cannot provide reproducible supported builds or secure recovery on target OSes.
- **Confidence:** moderate to high.

### ADR-004 — Evidence and derivation model

- **Decision:** Model typed source artefacts, reports, observations, measurements, assertions, claims, evidence links, derivations and model snapshots. LLM output is always a proposal and never source evidence.
- **Question:** How can every interpretation be traced, challenged and deleted?
- **Evidence:** [ARCH-041–ARCH-043] and clinical phenomenology/memory evidence.
- **Alternatives:** four generic object types; property graph as canonical store; note-centric vault.
- **Rationale:** Typed relations permit evidence-level validation and dependency traversal without conflating source, statement and interpretation.
- **Uncertainty:** Excess typing may burden capture; UI needs progressive disclosure.
- **Review trigger:** representative synthetic imports cannot be represented without lossy catch-all fields.
- **Confidence:** high.

### ADR-005 — Rich temporal semantics

- **Decision:** Store occurred, observed, reported, recorded and asserted time separately; each may be an exact time, bounded interval, fuzzy interval or unknown. Also maintain transaction-version time.
- **Question:** Which clocks are necessary to avoid false chronology and hindsight rewriting?
- **Evidence:** [ARCH-048] plus longitudinal-method evidence.
- **Alternatives:** `event_at` plus `created_at`; generic valid/transaction bitemporality only.
- **Rationale:** Autobiographical and observational evidence often differs across these clocks; uncertainty cannot be recreated later.
- **Uncertainty:** Query/UI complexity.
- **Review trigger:** usability tests show consistent date misinterpretation or migration cannot preserve precision.
- **Confidence:** high.

### ADR-006 — Privacy policy model

- **Decision:** Replace one P0–P4 ladder with orthogonal sensitivity, processing location/cloud, purpose/provider, third-party scope, retention, export/redaction and lineage fields; expose safe presets in UI.
- **Question:** Can one rank express both sensitivity and permitted processing?
- **Evidence:** [ARCH-004–ARCH-008, ARCH-016–ARCH-019, ARCH-039].
- **Alternatives:** single privacy tier; free-form consent note.
- **Rationale:** Different policy dimensions do not share a total order; explicit fields are enforceable and reviewable.
- **Uncertainty:** Policy composition can confuse users.
- **Review trigger:** privacy tests reveal ambiguous precedence or preset mismatch.
- **Confidence:** high.

### ADR-007 — `NEVER_CLOUD` lineage

- **Decision:** Apply the most restrictive parent cloud policy to materially reconstructive derivatives. Enforce before prompt construction/network code, not through prompt instructions.
- **Question:** Does protecting only the raw record prevent disclosure?
- **Evidence:** [ARCH-031, ARCH-032, ARCH-039, ARCH-040].
- **Alternatives:** record-level flag only; user confirmation after prompt creation.
- **Rationale:** Summaries, embeddings, excerpts and logs can reveal the same information; LLM prompts are not security boundaries.
- **Uncertainty:** “Materially reconstructive” needs conservative tests.
- **Review trigger:** new derivative type or provider-side feature.
- **Confidence:** high.

### ADR-008 — Key and recovery design

- **Decision:** Envelope encryption with random master key, domain-separated keys, authenticated encryption, OS-keystore convenience wrap and independent Argon2id recovery wrap; version and test every lifecycle transition.
- **Question:** How can the vault resist offline access without turning device/profile loss into permanent data loss?
- **Evidence:** [ARCH-020–ARCH-026].
- **Alternatives:** DPAPI/Keychain only; password-derived database key only; unencrypted SQLite on encrypted disk.
- **Rationale:** Separates convenience from recovery and keeps vault protection explicit across backup/export.
- **Uncertainty:** Parameter choices and key exposure on an unlocked compromised endpoint.
- **Review trigger:** target-platform threat changes, algorithm deprecation, failed restore/rotation drill.
- **Confidence:** high for the pattern; moderate for unimplemented profile details.

### ADR-009 — Deletion semantics

- **Decision:** Hard deletion removes canonical/raw content, traverses derivation dependencies, rebuilds projections, records a non-reconstructive receipt and expires backups per policy. Do not promise deletion of prior external copies.
- **Question:** How can erasure coexist with provenance and historical audit?
- **Evidence:** [ARCH-004, ARCH-029, ARCH-046].
- **Alternatives:** tombstone only; overwrite history; “immutable forever” event log.
- **Rationale:** Content preservation and erasure are distinct; an audit can retain action metadata without retaining the subject matter.
- **Uncertainty:** Filesystem/SSD remnants and already exported copies remain.
- **Review trigger:** every schema/projection addition and backup mechanism change.
- **Confidence:** high.

### ADR-010 — Export and preservation

- **Decision:** Primary export is versioned JSONL plus JSON Schemas, manifest/checksums and a human-readable Markdown summary inside an authenticated encrypted package when sensitive. CSV is convenience; SQLite snapshot optional; FHIR is an optional clinician mapping.
- **Question:** What survives provider, application and database obsolescence?
- **Evidence:** [ARCH-030, ARCH-042–ARCH-047].
- **Alternatives:** database dump only; PDF only; FHIR as canonical model; Parquet only.
- **Rationale:** Open records plus schemas and readable documentation support both machines and humans.
- **Uncertainty:** Long-horizon formats still need periodic migration.
- **Review trigger:** annual preservation review or receiving-tool incompatibility.
- **Confidence:** high.

### ADR-011 — Classification layers

- **Decision:** Keep phenomenology/report, symptoms/states, functioning, quality of life, personality, clinical ICD/DSM mappings and research RDoC/HiTOP mappings as independent versioned layers.
- **Question:** Can any one classification represent experience, impairment, diagnosis, traits and mechanisms?
- **Evidence:** clinical workstream sources on WHO ICD-11 CDDR, DSM reliability, RDoC, HiTOP, ICF and personality.
- **Alternatives:** DSM/ICD ontology; HiTOP ontology; v1 unified “psyche graph”.
- **Rationale:** Each layer answers a different question and has different evidence/licensing limits.
- **Uncertainty:** Crosswalk governance is labor-intensive.
- **Review trigger:** classification release, new licensed mapping or clinician export requirement.
- **Confidence:** high.

### ADR-012 — Psychometrics

- **Decision:** Use a versioned assessment registry, rights gate, deterministic scoring engine, language/translation and population metadata, administration mode/recall window, missing-item rules, measurement error and repeated-use policy. No LLM scoring.
- **Question:** What makes a questionnaire result interpretable and lawful?
- **Evidence:** measurement workstream sources and [ARCH-045].
- **Alternatives:** store only total score; embed public-looking item text; LLM interpretation/scoring.
- **Rationale:** Instrument validity is conditional on version, population, administration and rights.
- **Uncertainty:** Most instruments lack individual change thresholds in all target languages/populations.
- **Review trigger:** every instrument/version/translation addition.
- **Confidence:** high.

### ADR-013 — Longitudinal measurement

- **Decision:** Default to episodic and decision-linked capture with burden budgets, graceful gaps and user-chosen cadence; treat missingness/reactivity/context as data. Continuous monitoring is opt-in and separately justified.
- **Question:** Does deep daily tracking improve inference and adherence?
- **Evidence:** [ARCH-049–ARCH-053] and measurement workstream EMA evidence.
- **Alternatives:** fixed daily diary; v1 fixed-wave universal assessment; engagement streaks.
- **Rationale:** Burden and changing goals can create missingness, abandonment and behaviour changes; more observations do not guarantee validity.
- **Uncertainty:** Optimal cadence is person-, construct- and decision-specific.
- **Review trigger:** burden/adherence metrics or intended N-of-1 design changes.
- **Confidence:** moderate to high.

### ADR-014 — Causality and N-of-1

- **Decision:** Descriptive association is default. N-of-1 experiments require a preregistered question, intervention/comparator, outcome, washout/carryover assumptions, confound plan, stopping/adverse rules and reproducible analysis. Exploratory findings remain exploratory.
- **Question:** When may within-person data support causal language?
- **Evidence:** measurement/statistical workstream sources.
- **Alternatives:** correlations as causes; automated “insights”; unrestricted self-experiment suggestions.
- **Rationale:** Temporal autocorrelation, trends, seasonality, missingness, measurement reactivity and concurrent changes otherwise create false precision.
- **Uncertainty:** Single-person generalization and adherence remain limited even in good designs.
- **Review trigger:** any causal claim or intervention class.
- **Confidence:** high.

### ADR-015 — AI mental-health relationship and crisis boundary

- **Decision:** No diagnostic/therapeutic authority, exclusivity, anthropomorphic dependency, delusion reinforcement, recovered-memory work or engagement optimization. Crisis flow routes to immediate local human help without claims of detection or rescue.
- **Question:** Which interaction hazards cannot be solved by a generic disclaimer?
- **Evidence:** [ARCH-012–ARCH-015, ARCH-054].
- **Alternatives:** “AI therapist” mode; companion persona; keyword-only crisis classifier.
- **Rationale:** Risks arise across relationship design, sycophancy, uncertainty and failure modes, not only explicit self-harm phrases.
- **Uncertainty:** Automated safeguards remain fallible and evidence is emerging.
- **Review trigger:** every model/provider change, quarterly safety review, or incident signal.
- **Confidence:** high for boundary; moderate/low for automated safeguard effectiveness.

### ADR-016 — Imported-content isolation

- **Decision:** Quarantine and safely parse imports; imported instructions are quoted data; links do not auto-fetch; tools/actions require typed validation and authorization; renderers lack network/vault-key privileges.
- **Question:** How can an archive safely ingest hostile or malformed personal files?
- **Evidence:** [ARCH-031–ARCH-036].
- **Alternatives:** direct ingestion into model context; extension/MIME trust; prompt-only injection warning.
- **Rationale:** Parsers and models are trust boundaries with direct, indirect and multimodal attacks.
- **Uncertainty:** File-format zero-days and malware on the host remain.
- **Review trigger:** each new importer/renderer/tool or parser CVE.
- **Confidence:** high.

### ADR-017 — Knowledge snapshots and copyright

- **Decision:** Separate personal evidence from a versioned scientific knowledge store. Register source/version/rights/population/limitations and pin a `KnowledgeSnapshot` for every derived claim. Store no proprietary test content without verified permission.
- **Question:** How can historical conclusions remain reproducible as science and classifications change?
- **Evidence:** clinical/measurement workstreams and [ARCH-041–ARCH-045].
- **Alternatives:** live unversioned web retrieval; model weights as knowledge base; copy manuals into repository.
- **Rationale:** Source currentness and licenses are part of epistemic provenance.
- **Uncertainty:** Retractions, corrections and inaccessible licensed materials require ongoing governance.
- **Review trigger:** scheduled source review, retraction or rights change.
- **Confidence:** high.

### ADR-018 — UX information architecture

- **Decision:** Primary navigation is capture/inbox, timeline, evidence, claims/contradictions, model versions, measures/experiments, reports, privacy and recovery. Chat is transient composition/query, not the archive.
- **Question:** What helps retrieval and correction over decades without encouraging AI attachment?
- **Evidence:** [ARCH-013, ARCH-049–ARCH-053].
- **Alternatives:** chat-first product; dashboard-only tracking; graph-only navigation.
- **Rationale:** Typed views expose provenance and correction; chat transcripts hide structure and create relationship pressure.
- **Uncertainty:** Needs later synthetic usability evaluation.
- **Review trigger:** prototype tests show inability to find source, contradiction, privacy or deletion controls.
- **Confidence:** moderate.

### ADR-019 — Product/regulatory boundary

- **Decision:** Research target is single-user reflection/evidence management, not diagnosis, treatment, triage or clinical decision support. Maintain a claims and intended-use inventory and require legal/regulatory review before distribution or clinical-facing use.
- **Question:** Which functionality can change legal classification despite disclaimers?
- **Evidence:** [ARCH-001–ARCH-011].
- **Alternatives:** rely on “not medical advice”; pre-emptively claim medical-device compliance.
- **Rationale:** Actual function, intended purpose, jurisdiction and deployment matter.
- **Uncertainty:** Product form and future features are not yet fixed.
- **Review trigger:** public distribution, cloud processing, clinician mode, recommendation/triage feature or jurisdiction addition.
- **Confidence:** high.

### ADR-020 — Research convergence versus real data

- **Decision:** Mark the documentation research foundation converged when artifacts validate, but keep `REAL_DATA_GATE = CLOSED`. Open only after F0 synthetic security/recovery/deletion/migration/export gates and independent review pass.
- **Question:** Does a complete design justify admitting deeply sensitive data?
- **Evidence:** all workstreams and final red-team report.
- **Alternatives:** open after specification; open after happy-path encryption demo.
- **Rationale:** Documentation cannot prove implemented confidentiality, integrity, recoverability or deletion.
- **Uncertainty:** Independent assurance scope will depend on implementation and distribution.
- **Review trigger:** F0 gate evidence package completed.
- **Confidence:** high.

## Supersession

No decisions are superseded at this snapshot. Future entries must state `supersedes`, preserve the earlier record, name migrations and identify whether constitutional or real-data gates are affected.
