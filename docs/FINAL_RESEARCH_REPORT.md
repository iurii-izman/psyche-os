# PSYCHE OS v2 — final research report

**Snapshot:** 2026-08-10  
**Evidence:** 155 stable records / 153 unique serious sources  
**RESEARCH_CONVERGED:** `true`  
**REAL_DATA_GATE:** `CLOSED`

## Verdict

PSYCHE OS стоит строить только как **Personal Evidence & Reflection System**: локальное, provider-independent, evidence-preserving хранилище, которое отделяет report/measurement от интерпретации, показывает противоречия и неизвестное, допускает исправление/удаление/экспорт и остаётся полезным без AI.

Не следует строить «полный цифровой двойник», автономного терапевта/диагноста, universal mental-health score, immutable surveillance archive или систему, которая оптимизирует эмоциональную зависимость. Научная основа достаточна для точного F0 secure-foundation contract, но не является клинической валидацией продукта.

## Biggest problems in v1

1. Обещание полного Personal Mental Model провоцировало реификацию и ложную завершённость.
2. Четырёхобъектная модель и linear evidence ladder смешивали source, report, observation, assertion, claim и formulation.
3. Одна evidence/privacy tier скрывала разные оси validity, purpose, location, third-party, retention и rights.
4. Память/событие имели риск превращения искреннего report в исторический факт и приглашения к suggestion.
5. Категории ICD/DSM, dimensions, traits, functioning и wellbeing могли сливаться в одну psyche ontology.
6. Daily/fixed-wave deep tracking недооценивал burden, reactivity, missingness и abandonment.
7. Корреляционные «insights» и population-to-person перенос не имели достаточно строгой causal/statistical лестницы.
8. SQLCipher/local-first формулировались без полного key, independent recovery, temp, backup, deletion и restore lifecycle.
9. Full audit/event-history идея конфликтовала с реальным hard deletion и десятилетиями replay/migration.
10. F0 был слишком широк: UI/AI/integrations могли появиться раньше vault invariants и security proof.

## Biggest improvements in v2

1. Новая честная product identity и неизменяемая Constitution.
2. `PersonalModelSnapshot` — versioned derivative, а не identity/truth.
3. Phenomenology-first независимые clinical/research/trait/functioning/QoL/thriving layers.
4. ICD-11 primary, DSM secondary; RDoC/HiTOP research-only; p-factor personal score запрещён.
5. `SourceArtifact → Report/Observation/Measurement → Assertion/Claim` с typed `DerivationRun` и source locator.
6. Отдельные uncertainty dimensions, `ContradictionSet`, `Unknown`, alternatives и falsification.
7. Multi-clock/fuzzy time: occurred/observed/reported/recorded/asserted + transaction time.
8. `MemoryReport` с anti-suggestive protocol; no recovered-memory/hidden-trauma machinery.
9. Versioned psychometric rights/language/population/mode/scoring gate; LLM scoring запрещён.
10. Burden-bounded episodic EMA, missingness/reactivity contract и graceful gaps.
11. Source-specific Sleep OS and device/firmware/algorithm epochs; passive sensing deferred.
12. Causality `C0–C6`, N-of-1 design `D0–D4` and action risk `R0–R3`.
13. Hybrid bitemporal relational canonical store; graph/vector/search/analytics are rebuildable projections.
14. Orthogonal privacy and lineage-aware `NEVER_CLOUD` before prompt/network construction.
15. Envelope/key design with OS convenience wrap + independent Argon2id recovery; encrypted tested backup.
16. Dependency-graph deletion, mixed-output invalidation, projection rebuild and honest external-copy limits.
17. Quarantine/parser sandbox and imported/model text as untrusted data, never authority.
18. Mental-health AI relationship/crisis policy plus adversarial multilingual/model-change evaluation.
19. Open JSONL/schema/manifest/Markdown export and versioned migrations for lifetime durability.
20. Machine-readable closed real-data gate with twelve unsatisfied runtime/review requirements.

## Removed/rejected ideas

Rejected: digital-twin/complete-self claim; autonomous therapy/diagnosis/triage; personal p-factor/universal wellness score; recovered-memory work; fixed attachment/personality types; causal inference from ordinary correlations; full event-sourced content ledger; graph/vector/provider as canonical truth; public plaintext content hashes; chat as archive; engagement/streak pressure; ambient audio/keystroke/covert-location surveillance; OS-key-only recovery.

Deferred pending evidence: desktop shell, LLM/cloud, assessments/items, wearables/messages/calendar imports, graph/vector/advanced analytics, FHIR/clinician mode, intervention execution, sync/mobile/sharing.

## New foundational subsystems

- constitutional and scientific governance;
- Personal Evidence Store and typed derivation DAG;
- knowledge/source/rights snapshots;
- temporal assertion and contradiction/unknown models;
- assessment registry and deterministic scoring gate;
- privacy-policy compiler and lineage engine;
- cryptographic key/recovery/backup lifecycle;
- deletion dependency traversal and content-free audit;
- hostile import boundary;
- mental-health AI safety state/policy/eval system;
- migration, preservation/export and real-data gate machinery.

## Scientific confidence

| Area | Confidence | Boundary |
|---|---|---|
| Raw/derived, provenance, uncertainty, conflict, time separation | High | Implementation/UI still must prove usability and invariants. |
| Clinical-layer separation; screening ≠ diagnosis | High | No individual diagnosis/clinical validation. |
| Memory reconstruction and anti-suggestion limits | High | Historical truth often remains unknowable. |
| Psychometric/version/rights/translation gate | High | Exact instrument confidence is use/population/language-specific. |
| Longitudinal/statistical/causal guardrails | High | Any causal result remains design/assumption-specific. |
| Big Five as broad crosswalk | Moderate | Culture, facets and HEXACO mapping limit universality. |
| EMA/sleep trend usefulness | Moderate | Protocol/device/person/algorithm-specific. |
| Passive sensing and computational personalized prediction | Low | External validity and clinical utility insufficient. |
| LLM benefit and automated mental-health safeguards | Low–Moderate | Model/language/context drift and severe false negatives/positives remain. |

The evidence registry includes official laws/classifications/regulator and professional guidance, standards, systematic reviews/meta-analyses, methodological consensus, field/primary studies and authoritative technical/provider documentation. Binding EU AI Act text is registered separately from implementation summaries [ARCH-002].

## Residual risks

No architecture fully solves an unlocked compromised endpoint, coercion, screen/clipboard capture, inaccurate sources/science/models, user-authorized oversharing, third-party harms, parser zero-days, SSD/filesystem remnants, copies already exported/disclosed, future cryptographic obsolescence or loss of all recovery material. Mental-health model safety remains an open empirical problem. Legal/device/privacy qualification depends on final intended use and deployment.

## Readiness

Ready only to implement **F0 Minimal Irreversible Secure Core with synthetic fixtures**. Not ready for production, real personal data, cloud, clinician use, public distribution, assessment deployment or therapeutic/diagnostic claims.

The research foundation contains four independent/adversarial audit passes, 70 red-team risks, explicit 1/5/20/40-year failure analysis and a repository-scoped threat model. Documentation controls are not counted as implemented security.

## Minimal irreversible core

F0 must implement opaque IDs, version rows, raw/derived split, provenance/derivation, multi-clock/fuzzy time, claims/evidence/uncertainty/conflict/unknown, orthogonal privacy/lineage, encryption envelope/key/recovery state, content-free audit, hard deletion traversal, schema migrations, encrypted backup/isolated restore and open export—through a Python 3.12+ local CLI with no network listener.

It must not implement AI, real imports/data, rich UI, assessment content/scoring, diagnosis, graph/vector, FHIR, interventions or sync.

## Real-data blockers

All twelve gate requirements remain unsatisfied: verified encrypted DB/blobs; rotation/independent recovery; encrypted clean restore; deletion/projection/backup expiry; migration/export round trip; no plaintext temp/WAL/log/crash/package/projection; `NEVER_CLOUD` properties; enabled import boundaries; dependency/SBOM/license/build/secret gates; independent threat/crypto/privacy/deletion review; intended-use/legal review; synthetic fault/recovery/deletion usability suite.

Therefore `REAL_DATA_GATE = CLOSED`.

## Validation performed

- all 19 required artifacts plus machine gate and research support scripts checked for existence;
- `SOURCE_REGISTRY.yaml`: YAML parse, 155 unique IDs, 153 unique URLs/sources, reciprocal duplicate aliases, required currentness/limitations/rights fields;
- ontology: YAML parse, 44 unique domains, 18 layers, 17 evidence-kind contracts, 24 valid relations, `completeness_claim: false`;
- 155 registered source IDs referenced across the evidence base; unknown citations: 0;
- local Markdown links, required master/threat headings, implementation-contract footer and gate consistency checked;
- forbidden vault/key/database/export file types and common plaintext secret signatures checked: 0;
- Git whitespace/diff check and four final audit passes completed;
- original v1 and master research prompt preserved unchanged.

The repeatable command is:

```powershell
python scripts/validate_research_foundation.py
```

## Next step

Open a new Codex task rooted at `C:\Dev\psyche-os` and pass the **complete, unchanged** contents of `docs/prompts/F0_IMPLEMENTATION_PROMPT.md`. To print that exact prompt:

```powershell
Get-Content -Raw .\docs\prompts\F0_IMPLEMENTATION_PROMPT.md
```

Do not append new scope and do not use real data. F0 completion leads only to synthetic independent assurance; it does not automatically open the gate.
