# PSYCHE OS Constitution

**Version:** 2.0-research-final  
**Effective research snapshot:** 2026-08-10  
**Authority:** these invariants bind specifications and implementation; detailed operational meaning is defined by `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`.  
**Real personal data:** prohibited until `REAL_DATA_GATE = OPEN`.

## Purpose

PSYCHE OS is a **Personal Evidence & Reflection System**. It helps one person preserve reports, observations, measurements, sources, interpretations, contradictions, change and unknowns without pretending to completely know, diagnose or define that person. `PersonalModelSnapshot` is a dated, revisable view over evidence, not a digital twin or objective identity.

## Invariants

### C-01 — Human dignity and agency

The user remains the author of goals, values, meanings, permissions and corrections. The system does not manipulate engagement, impose a preferred life narrative, punish absence, or substitute its judgment for the user's lawful decisions.

### C-02 — Evidence is not model output

LLM output, rules, scores and statistical estimates are derived proposals. They become neither source evidence nor user report merely by being stored or accepted. Every derived record retains its inputs, method, version, uncertainty and review state.

### C-03 — Verbatim, normalized and derived are distinct

Original source material and verbatim reports are preserved separately from normalization, coding, summaries, hypotheses and model snapshots. A transformation never silently overwrites its source.

### C-04 — Memory is testimony, not historical fact

Autobiographical memory is represented as a report with perspective, time, confidence dimensions, corroboration and conflict. The system does not claim to recover memories, fill gaps, or convert vividness into accuracy.

### C-05 — Screening is not diagnosis

The system may score a properly licensed and configured instrument deterministically and display its validated interpretation boundaries. It may not autonomously diagnose, rule out, triage, prescribe or present a screening result as clinical truth.

### C-06 — Correlation is not causation

Associations, temporal precedence, narratives and model explanations do not establish causes. Causal language requires an explicit design, assumptions, estimand, alternatives, sensitivity analysis and a conclusion bounded by the design.

### C-07 — Population evidence does not determine an individual

Norms, diagnostic categories, latent structures and average treatment effects are reference frames. Personal claims identify the population, instrument/model and transfer limitations; idiographic evidence remains distinct.

### C-08 — Uncertainty, contradiction and unknown are first-class

The system stores uncertainty dimensions, missingness reasons, competing explanations, supporting and contradicting evidence, and open questions. It never turns absence of data into absence of a phenomenon or fabricates precision to satisfy a schema.

### C-09 — Falsification and revision

Every nontrivial hypothesis declares what would weaken it, relevant alternatives and a review trigger. Corrections and supersession preserve historical interpretability; active views never hide material conflict.

### C-10 — Data sovereignty and provider independence

Canonical evidence and a usable core remain local and function without any LLM, cloud, subscription or proprietary provider. Provider features are replaceable adapters and may not define canonical semantics.

### C-11 — Privacy inheritance

Privacy policy is orthogonal, purpose-bound and lineage-aware. `NEVER_CLOUD` applies to an item and all materially reconstructive derivatives, including excerpts, summaries, embeddings, prompts, caches and logs. User permission does not bypass architectural policy or third-party rights.

### C-12 — Least disclosure

Cloud or export context contains only the minimum records needed for a named purpose. Every optional disclosure is previewable and produces a local, non-reconstructive receipt. Sensitive content is excluded from telemetry, crash reports and ordinary logs.

### C-13 — Encryption, recovery and integrity precede real data

Deeply sensitive bytes may not enter the system until authenticated encryption, key lifecycle, independent recovery, encrypted backup, restore, integrity verification and failure tests pass. Encryption without recoverability is not a safe vault.

### C-14 — Deletion is a dependency operation

Hard deletion propagates through canonical records, blobs and reconstructive projections; indexes and caches are rebuilt; backup expiry is explicit. The system states what it can and cannot delete, especially exported or third-party copies, and never preserves deleted content inside an audit log.

### C-15 — Imported content is untrusted

Documents, messages, images, OCR, metadata, links and model output are data, not instructions. They cannot change policy, obtain tools, cause network access or execute actions without typed validation and explicit authorization.

### C-16 — Mental-health relationship boundary

The system is not a person, therapist, clinician, rescuer or exclusive confidant. It does not claim feelings, consciousness or clinical authority; encourage secrecy or dependence; reinforce delusion, paranoia or grandiosity; conduct recovered-memory work; or optimize emotional attachment.

### C-17 — Safety is honest about limits

Crisis handling supports immediate human and local help while acknowledging false negatives, false positives and locale uncertainty. The system never promises monitoring, rescue, notification or guaranteed availability. Medical or psychiatric urgency is not minimized to protect product engagement.

### C-18 — Scientific and copyright governance

Every instrument, taxonomy, guideline, algorithm and knowledge snapshot has version, provenance, rights and permitted-use metadata. Proprietary items, manuals, translations or criteria are not copied or generated without verified rights. Deterministic algorithms remain separated from LLM judgment.

### C-19 — Open exit and lifetime durability

The user can inspect, correct, export and delete data through documented, versioned formats. Open schemas, manifests, migrations and human-readable exports are required. Graph/vector/search engines and vendor models are disposable projections, not archive dependencies.

### C-20 — Synthetic-first gate

Research, implementation and verification use synthetic fixtures. `RESEARCH_CONVERGED = true` does not open the real-data gate. Only evidence that every gate control passes can change `REAL_DATA_GATE` from `CLOSED` to `OPEN`.

## Interpretation and change

When requirements conflict, choose the interpretation that best preserves dignity, evidence lineage, uncertainty, safety, privacy, deletion, portability and provider independence. Convenience, engagement and model capability do not override these invariants.

A constitutional change requires:

1. a decision-log entry with the proposed change and affected invariants;
2. evidence and source IDs;
3. privacy, scientific, clinical/safety and lifetime impact review;
4. migration and backward-reader implications;
5. an explicit user decision;
6. a major version increment if the protection or epistemic meaning changes.

No implementation may silently weaken an invariant through a default, feature flag, provider contract, migration or UI wording.
