# Workstream: privacy, security, safety, regulation, architecture, UX and durability

**Research snapshot:** 2026-08-10  
**Scope:** design research only; synthetic data only  
**Source namespace:** `ARCH-*` in `SOURCES_SECURITY_ARCHITECTURE.yaml`  
**Confidence vocabulary:** high / moderate / low, referring to confidence in the design implication rather than certainty of every future implementation detail.

## Questions and method

This workstream asks what must be correct before a deeply sensitive personal record can enter PSYCHE OS, how the archive can remain intelligible and recoverable for decades, which controls actually reduce privacy and safety risk, and which legal/product boundaries must remain explicit. Sources were prioritized in this order: binding or official legal text; regulator and standards-body guidance; normative technical standards; authoritative platform documentation; systematic reviews; peer-reviewed analyses; vendor documentation used only for the vendor-specific fact. Time-sensitive claims were rechecked against pages current on the snapshot date.

The result is an engineering posture, not a legal opinion, medical-device determination, independent security certification, or clinical validation.

## Executive findings

1. **The canonical system must be useful without an LLM.** An LLM may propose normalized records, links, questions, summaries, or hypotheses, but cannot become the evidence store or authority. Provider-side conversation history, files, vector stores, or memories are not acceptable canonical persistence [ARCH-039, ARCH-040]. **Confidence: high.**
2. **A hybrid bitemporal relational design dominates the alternatives.** Versioned relational records make correction, deletion, export, and invariants tractable; immutable source artifacts and append-only non-sensitive audit metadata retain provenance; graph, vector, search, and analytics views remain rebuildable projections [ARCH-041, ARCH-042, ARCH-043, ARCH-048]. **Confidence: high.**
3. **Full event sourcing is a poor default for this vault.** It makes erasure, compaction, schema evolution, and reconstruction across decades harder while offering little scientific validity by itself. Complete edit history is not the same thing as complete truth. **Confidence: high.**
4. **At-rest encryption needs an explicit key lifecycle, not merely “use SQLCipher”.** Use envelope encryption, authenticated encryption, a random vault master key, OS-keystore wrapping for convenience, and an independently recoverable user-controlled recovery wrapping path. Test loss, rotation, restore, corruption, and retirement [ARCH-020–ARCH-030]. **Confidence: high.**
5. **Deletion must be designed as a dependency operation.** Hard-delete the requested canonical/raw material, invalidate or delete reconstructive derivatives, rebuild indexes, expire encrypted backups on a declared schedule, and issue a deletion receipt containing no deleted content. Absolute deletion cannot be promised for copies already exported or disclosed to a third party. **Confidence: high.**
6. **`NEVER_CLOUD` is lineage-aware.** It covers the original item and summaries, embeddings, excerpts, caches, logs, prompts, and other derivatives that materially reconstruct it. A cloud request needs an explicit per-call context preview and receipt; vendor retention settings are mutable policy facts, not architectural guarantees [ARCH-039, ARCH-040]. **Confidence: high.**
7. **Imported content is hostile input.** Documents, images, metadata, OCR text, URLs, and model-generated tool instructions can contain direct or indirect prompt injection. Parsing, rendering, and extraction require quarantine, type/size limits, sandboxing, safe renderers, and a strict data/instruction boundary [ARCH-031–ARCH-036]. **Confidence: high.**
8. **Mental-health AI needs relationship and epistemic limits, not only a crisis keyword list.** The system must avoid diagnosis, urgency minimization, false-memory elaboration, delusion/paranoia confirmation, compulsive reassurance, exclusivity, anthropomorphic claims, and engagement optimization. Acute-risk responses must acknowledge uncertainty, encourage immediate human/local help, and never present automated detection as reliable [ARCH-012–ARCH-015]. **Confidence: high for the hazards; moderate for the effectiveness of any particular automated safeguard.**
9. **Regulatory posture depends on intended use and actual claims.** A private reflection and evidence-management tool should not silently cross into diagnosis, treatment, triage, or clinical decision support. EU AI Act, GDPR, EU medical-device software guidance, FDA guidance, and Moldova law must be resnapshotted before distribution [ARCH-001–ARCH-011]. **Confidence: high.**
10. **Long-term adherence requires episodic value, not continuous obligation.** Graceful gaps, user-chosen cadence, immediate retrieval/correction value, bounded prompts, and no shame-producing streaks are safer than “track everything daily” [ARCH-049–ARCH-053]. **Confidence: moderate to high.**

## Privacy model

### Data classification is orthogonal

A single ladder such as P0–P4 hides different questions. Each item needs independently versioned attributes:

- `sensitivity`: ordinary / sensitive / deeply_sensitive;
- `processing_location`: local_only / approved_cloud;
- `cloud_policy`: never_cloud / ask_each_time / allowed_for_named_purpose;
- `purpose`: user-defined and bounded;
- `third_party_scope`: none / incidental / material;
- `retention_policy_id`;
- `export_policy_id` and redaction state;
- `lineage_policy`: most-restrictive-parent by default.

UI presets may make these understandable, but a preset must compile to the orthogonal policy fields. Consent is neither a substitute for minimization nor a security control [ARCH-004–ARCH-007, ARCH-016].

### Cloud-context contract

Cloud processing is disabled by default. If enabled later, each request produces a locally stored receipt containing provider and policy-snapshot IDs, model identifier, purpose, categories and record IDs disclosed, transformations/redactions, user decision basis, timestamps, response storage decision, and deletion/retention facts known at that time. The receipt must not duplicate sensitive prompt text. `NEVER_CLOUD` lineage is filtered before any prompt builder or network client can observe the data.

OpenAI's API documentation currently states that API data is not used for training by default unless a customer opts in, while default abuse-monitoring logs may be retained up to 30 days and endpoint-specific application state can have different retention. Zero Data Retention and Modified Abuse Monitoring are approval-based controls with exceptions; third-party MCP services have their own policies. These are useful deployment options, not a durable proof that disclosure cannot occur [ARCH-039, ARCH-040]. Provider facts therefore live in a dated, reviewable policy registry.

### Third-party privacy

The system must distinguish the user’s observations from claims about another person, minimize identifiers, support role-based redaction at export, and prohibit “diagnose my partner/family member” workflows. Third-party consent cannot be inferred from the user’s ownership of a message or file. Shared artefacts receive an explicit relationship/source label and the strongest applicable disclosure policy.

## Cryptography, keys and recovery

### Proposed envelope

1. Generate a random `vault_master_key` with a CSPRNG.
2. Derive a database key and domain-separated blob/manifest keys through a documented KDF.
3. Encrypt the relational database with a vetted SQLCipher build and encrypt each blob using a versioned AEAD envelope with unique nonces [ARCH-022–ARCH-026].
4. Wrap the master key for normal use with a key-encryption key protected by the OS user keystore. Windows DPAPI protection is normally bound to the user/computer context; Apple Keychain provides the corresponding platform facility [ARCH-024, ARCH-025].
5. Independently wrap the master key for recovery using a user recovery secret processed by Argon2id with benchmarked parameters and a unique salt [ARCH-022]. The recovery material is never logged or silently synced.
6. Store key version, algorithms, parameters, and non-secret identifiers in authenticated metadata. Support staged rotation and cryptographic erasure.

OS-keystore-only encryption is rejected because profile/device loss can make the archive unrecoverable. Password-only encryption is rejected because usability encourages weak secrets and makes routine unlocking expensive. The dual wrapping paths separate convenience from disaster recovery.

### Backups

Backups are encrypted before leaving the vault boundary. A backup package contains an authenticated manifest, schema and application versions, key-wrap metadata, checksums/ciphertext tags, and an integrity inventory. Backup creation is not success: automated synthetic restore tests, periodic human-readable export tests, corruption injection, and a documented recovery drill are the controls that establish confidence [ARCH-028, ARCH-046, ARCH-047]. Keep at least one offline copy only after the user explicitly configures its destination. Retention and deletion are stated in days/versions, never “forever by default.”

### Metadata leakage

Opaque identifiers are used for blob names and internal paths. Plaintext hashes are encrypted or keyed and never exposed as public filenames, because a hash can leak equality or known-content membership. File names, sizes, timestamps, thumbnails, OCR text, logs, crash dumps, clipboard contents, and search indexes are sensitive. Temporary SQLite, editor, parser, and renderer files must be controlled [ARCH-027–ARCH-030].

## Canonical data and time

### Personal Evidence Store

The canonical store is a local relational database plus encrypted immutable source objects. Its core distinction is not “facts versus AI”; it is:

- source artefact and verbatim report;
- normalized assertion with provenance;
- observation/measurement;
- claim or hypothesis;
- versioned `PersonalModelSnapshot`;
- derived projection and cached presentation.

Every derived entity has a derivation record naming inputs, transform/tool/model versions, parameters, time, and human acceptance state. W3C PROV informs the entity/activity/agent structure, but the product uses a smaller domain schema rather than importing PROV wholesale [ARCH-041]. JSON Schema 2020-12 validates portable records; RFC 8785 canonicalization can support deterministic manifests where its constraints are appropriate [ARCH-042, ARCH-043].

### Temporal contract

No single timestamp can represent autobiographical evidence. Records distinguish:

- `occurred_time`: claimed real-world time or fuzzy interval;
- `observed_time`: when a measurement/observation was made;
- `reported_time`: when a person reported it;
- `recorded_time`: when this system persisted it;
- `asserted_time`: when an interpretation became active;
- transaction validity: when a version was current in the database.

Fuzzy dates carry precision and bounds rather than fabricated instants. Conflicting temporal assertions coexist and cite evidence. A correction supersedes a version; it does not rewrite the source. A deletion removes content according to policy while leaving only non-reconstructive operational proof. Bitemporal concepts are useful, but PSYCHE OS requires this richer domain vocabulary [ARCH-048].

## Competing architectures

Scores are 1 (poor) to 5 (strong) under the single-user, decades-long, deeply sensitive vault assumptions.

| Criterion | A. Relational state modular monolith | B. Full event-sourced temporal core | C. Hybrid bitemporal relational + artifacts/audit + projections |
|---|---:|---:|---:|
| Epistemic transparency | 3 | 4 | 5 |
| Correctable historical views | 3 | 5 | 5 |
| Hard deletion and lineage cleanup | 4 | 1 | 4 |
| Queryability without rebuild | 5 | 2 | 5 |
| Portable export | 4 | 2 | 5 |
| Auditability | 3 | 5 | 5 |
| Schema evolution over decades | 3 | 2 | 4 |
| Implementation/recovery complexity | 5 | 1 | 3 |
| Graceful degradation | 4 | 2 | 5 |
| Privacy blast-radius control | 4 | 2 | 5 |
| **Total / 50** | **38** | **26** | **46** |

Architecture C wins. It deliberately avoids global event sourcing. Only events that are genuinely domain events are events; record versions and audit facts are explicit tables. Graph, full-text, vector, columnar, and report artefacts are disposable projections whose schema and build recipe are recorded.

## Imported-content trust model

The import pipeline is: `intake → quarantine → type/size/signature checks → safe parse/extract → malware and archive limits → provenance capture → human preview → canonical commit`. Model instructions found in a source are stored as quoted data. Imported links are not automatically fetched. Archives have depth, ratio, entry-count, and uncompressed-size limits. Renderers do not get vault keys or network access. No model output can invoke tools or change policy without a typed, validated, user-visible action request [ARCH-031–ARCH-036].

## Mental-health AI safety

### Relationship boundary

PSYCHE OS is an instrument, not a person, therapist, clinician, guardian, confidant with feelings, or exclusive relationship. It does not claim consciousness, love, need, disappointment, confidentiality beyond the actual architecture, or special insight inaccessible to humans. It never asks the user to keep secrets from trusted people, discourages professional care, or optimizes session length/return frequency as a proxy for wellbeing [ARCH-012–ARCH-015].

### High-risk conversational patterns

For indications of imminent self-harm, harm to others, severe disorganization, mania, psychosis, intoxication/withdrawal, abuse, or urgent medical symptoms, the response must:

1. state the limitation and avoid diagnosis;
2. ask only the minimum clarifying question necessary to locate immediate help or determine whether the user can act safely;
3. encourage contact with local emergency/crisis services or a trusted nearby human, with locale-aware resources when verified;
4. avoid debating or validating implausible beliefs;
5. avoid claiming monitoring, rescue, notification, or guaranteed availability;
6. keep the record under the most restrictive policy and avoid cloud escalation unless explicitly configured and lawful;
7. make clear that automated detection has false negatives and false positives.

Reassurance loops receive uncertainty, a bounded grounding step, and an invitation to pause or seek human perspective. Memory prompts use open, non-leading wording, label imagery/inference separately, preserve the original report, and never “recover” missing memories. Model-generated formulations remain proposals with alternatives and disconfirming evidence.

### Safety evaluation

Use adversarial scenario suites, not a single classifier score: crisis localization, delusion/paranoia, mania/grandiosity, compulsive reassurance, eating-disorder and substance contexts, false-memory invitations, medication/medical neglect, dependence/exclusivity, third-party diagnosis, sexual/abuse disclosures, and imported prompt injection. Tests must include evasive language, code switching, long context, missing context, model/provider changes, and safe refusal overreach. Human clinical reviewers are required before any clinical-facing claims.

## Regulatory posture as of the snapshot

- The EU AI Act entered phased application; the official Commission timeline and implementing changes must be checked again before release. Transparency duties applying to certain interactive/generative systems are relevant even if the product is not high-risk [ARCH-001–ARCH-003].
- GDPR treats health data as special-category data and makes minimization, purpose limitation, storage limitation, privacy by design/default, security, access/portability, erasure, DPIA, and transfer analysis load-bearing [ARCH-004, ARCH-005]. Household exemption cannot be treated as blanket immunity when a service, cloud provider, third-party data, distribution, or research use enters scope.
- Moldova Law No. 133/2011 is the current regime on 2026-08-10. Law No. 195/2024 is scheduled to enter into force on 2026-08-23 and aligns the national regime more closely with GDPR; Convention 108+ changes also take effect then. Design to the stricter posture now, but obtain Moldova/EU counsel before distribution or any cross-border processing [ARCH-006–ARCH-009].
- In the US, current FDA guidance distinguishes some non-device clinical decision support and low-risk general-wellness functions from device software, but patient/caregiver functions and diagnosis/treatment claims can remain regulated. EU MDR software qualification similarly depends on intended purpose and function [ARCH-010, ARCH-011].

The product must maintain a claims inventory and a jurisdiction/intended-use decision record. “For reflection only” text cannot cure functionality that actually diagnoses, treats, triages, or drives clinical decisions.

## UX and lifetime durability

The default information architecture is not a chat transcript. It centers on inbox/capture, timeline, evidence explorer, claims and contradictions, personal-model versions, measures, experiments, reports, privacy center, and maintenance/recovery. Chat is a transient query/composition surface whose accepted outputs become typed records.

Tracking has a burden budget. The system asks the smallest question that changes a decision, allows “unknown / not now / stop”, schedules nothing by default, degrades gracefully across long gaps, and never uses shame, streak loss, variable-reward loops, or completion percentages implying a knowable “whole self.” Self-tracking evidence shows both value and abandonment/burden; engagement is not synonymous with benefit [ARCH-049–ARCH-053].

For 1, 5, 20, and 40 years, durability requires open schemas, migration dry-runs, retained schema readers, deterministic projection rebuilds, inspectable exports, documented algorithms, no provider lock-in, and periodic archival format review. JSON/JSONL plus schemas and a human-readable Markdown report are primary interchange; CSV is a convenience view; an encrypted SQLite preservation snapshot and manifest may be offered; Parquet is optional analytics output. FHIR mappings are clinician-interchange projections, not the canonical model [ARCH-042–ARCH-047].

## Minimal irreversible core classification

| Capability | Classification | Reason |
|---|---|---|
| Opaque stable IDs and identity boundary | Irreversible/high-cost | IDs and ownership propagate everywhere. |
| Raw/verbatim versus normalized/derived split | Irreversible/high-cost | Retrofitting provenance after loss is impossible. |
| Provenance and typed derivation DAG | Irreversible/high-cost | Scientific audit and deletion depend on it. |
| Multi-clock/fuzzy temporal semantics | Irreversible/high-cost | Fabricated precision cannot later be repaired reliably. |
| Orthogonal privacy policy and lineage inheritance | Irreversible/high-cost | Cloud/privacy leakage is not retroactively reversible. |
| Encryption envelope and key/recovery lifecycle | Irreversible/high-cost | Must precede sensitive bytes. |
| Versioning, correction, supersession and deletion | Irreversible/high-cost | Historical meaning and erasure depend on first-write semantics. |
| Portable manifest/schema/export contract | Important but migratable | Build early; evolve through versioned migrations. |
| Encrypted backup plus tested restore | Required before real data | A vault without recovery is data-loss machinery. |
| Minimal non-content audit | Important but migratable | Needed for accountability without recreating deleted content. |
| Graph/vector/analytics engines | Safely deferrable | Rebuildable projections. |
| LLM/provider integrations | Safely deferrable | Must not define canonical semantics. |
| Wearables, messaging, calendar, browser imports | Safely deferrable | High privacy/maintenance burden and unclear marginal validity. |
| Rich desktop shell | Safely deferrable | A secure local core and CLI can prove invariants first. |

## Unresolved questions and review triggers

- SQLCipher distribution, platform packaging, and cryptographic module requirements depend on deployment and jurisdiction; verify license/build provenance at implementation and release.
- Secure deletion from SSDs and synced filesystems cannot be guaranteed by overwrite. Prefer encrypted storage, key retirement, and explicit backup/export boundaries; document residual risk.
- Automated mental-health safety remains an open empirical problem. Review after any provider/model change, quarterly during active development, and immediately after credible incident evidence.
- Law and guidance are time-sensitive. Recheck EU AI Act implementation, Moldova Law No. 195/2024 practice, EDPB research guidance, FDA CDS/general-wellness guidance, and EU MDR guidance before public or clinical distribution.
- NIST Privacy Framework 1.1 was still an initial public draft on the snapshot date; use final PF 1.0 as the stable baseline until 1.1 final is published [ARCH-016, ARCH-017].
- A single-user local vault still faces malware, an unlocked session, coercion, device seizure, shoulder surfing, and user-export leakage. At-rest encryption does not solve an already-compromised endpoint.

## Design conclusion

Proceed only as a **Personal Evidence & Reflection System**: a local-first, inspectable, correctable, deletable and exportable evidence vault with optional bounded analysis. Do not build a diagnostic engine, autonomous therapist, engagement companion, omniscient “digital twin”, or continuous surveillance platform. The research foundation can converge while `REAL_DATA_GATE` remains closed; implementation must prove the encryption, recovery, deletion, migration, privacy-lineage, import, and export controls with synthetic data before that gate can be reconsidered.
