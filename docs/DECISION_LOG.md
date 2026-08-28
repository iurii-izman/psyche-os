# PSYCHE OS v2 decision log

**Snapshot:** 2026-08-11
**Status:** research convergence and implementation-governance record
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

### ADR-021 — Minimal E00 boundary and pre-real-data staging

- **Decision:** Rebaseline E00 to the irreversible synthetic-only foundation in `docs/development/E00_REBASELINE_DECISION.md`. Keep canonical version semantics, minimal transactional migrations, storage-enforced bundled-fixture-only writes and truthful acceptance validation in E00. Preserve the High severity of incomplete backup/restore, blob lifecycle and Windows filesystem mutation, disable those surfaces, and assign their completion to E01 before real-data eligibility. Assign release-grade SBOM reconciliation to E11. `REAL_DATA_GATE` stays `CLOSED`.
- **Question:** Which controls must be correct before any later synthetic epic, rather than before the first real sensitive record or release?
- **Evidence:** Master Spec §24.1 distinguishes irreversible/high-cost semantics from §24.2 migratable real-data-gate controls; §25 and Constitution C-13/C-20 still require all security/recovery evidence before real data. The concrete remaining defects are recorded in `docs/implementation/E00_ACCEPTANCE_REPORT.md`; E01 already owns independent recovery, fault and exact-profile assurance.
- **Alternatives:** continue repairing every F0 control inside E00; downgrade remaining findings; accept unsafe features with documentation only; create another epic.
- **Rationale:** The chosen boundary prevents later code from depending on incorrect canonical/migration/write semantics or false acceptance while avoiding production hardening of capabilities that can be made unavailable during synthetic development. Severity is not reduced and no real-data requirement is removed.
- **Uncertainty:** E01 may find that a disabled capability requires API adjustment before E02; the stable deferred typed error limits that coupling. Exact Windows runtime feasibility remains unverified.
- **Review trigger:** evidence of a frozen E00 invariant violation; any attempt to enable backup/restore, blobs or affected filesystem mutation; E01 entry review; any `REAL_DATA_GATE` decision.
- **Supersedes:** ADR-020 only as to epic scheduling of F0 recovery/backup/migration/export evidence. ADR-020's closed-gate rule and required evidence remain fully in force.
- **Confidence:** high for the staging boundary; moderate for exact E01 implementation effort.

### ADR-022 — E02 secure desktop shell and typed Python boundary

- **Decision:** Implement E02 as a Tauri 2 desktop shell using the Windows Microsoft Edge WebView2 renderer, a minimal local TypeScript/Vite frontend, Rust-owned allowlisted commands, and one fixed PSYCHE OS Python sidecar reached only through length-bounded, versioned JSON messages over inherited stdin/stdout pipes. The renderer is an untrusted presentation adapter. Rust owns window/webview policy, session/origin checks, request validation, sidecar lifecycle and content-free error mapping. The Python process remains the authoritative application/domain/policy/storage/crypto/backup/export core. Rust does not reimplement E00/E01 semantics, and neither renderer nor Rust command handlers write SQL directly.
- **Question:** Which reviewed Windows desktop boundary best preserves the accepted no-listener Python core while minimizing renderer privilege and enabling typed E02 workflows?
- **Evidence:** Accepted architecture requires a later typed desktop adapter with restrictive CSP and no direct webview vault/key access [ARCH-026, ARCH-036]. Current official Tauri documentation confirms Windows WebView2 and MSVC prerequisites [ARCH-056], per-window/webview capability control and local-origin runtime authority [ARCH-057, ARCH-058], configurable CSP [ARCH-059], fixed external binaries with stdin/stdout support [ARCH-060], and Windows MSI/NSIS packaging [ARCH-061]. The minimum Tauri core line is `2.11.1` because its official release notes include origin/ACL security fixes [ARCH-062]. Package metadata probed on 2026-08-13 reported `tauri` 2.11.5, `@tauri-apps/cli` 2.11.4 and `@tauri-apps/api` 2.11.1, each Apache-2.0 OR MIT.
- **Renderer and origin model:** Only packaged local application assets are loaded. No remote URL, remote capability, webview plugin, popup or arbitrary navigation is allowed. Production CSP defaults to self-only content, with Tauri's internal IPC transport sources added only as required by the generated runtime; those `.localhost` URLs are WebView2 custom-protocol origins, not an HTTP server or TCP listener. Devtools are disabled in production. Dynamic content uses text-safe DOM APIs, never raw HTML.
- **Typed privileged boundary:** The only renderer authority is an explicit Tauri capability for named Rust commands. Every request has a protocol version, command-specific strict schema/limits, opaque correlation ID and, where state-changing, current session authority and explicit confirmation. Unknown commands, fields, origins, sessions and states fail closed before Python is called. Rust launches only the configured sidecar with fixed arguments; the renderer receives no shell plugin, filesystem plugin, SQL, CLI dispatcher, vault path, process handle or sidecar transport. Rust↔Python messages use bounded framing over stdin/stdout, never TCP, HTTP or a local socket.
- **Toolchain:** Target Tauri major version is `2.x`; implementation must resolve current stable compatible releases into committed npm and Cargo lockfiles, with `tauri >=2.11.1,<3` and no older origin/ACL behavior. The 2026-08-13 reference set is core 2.11.5 / CLI 2.11.4 / API 2.11.1, Vite 8.2.1 and TypeScript 7.0.2. Use npm with committed `package-lock.json`, Cargo with committed `Cargo.lock`, Python 3.12 with existing `uv.lock`, and a fixed Python-sidecar build specification. Local probes found Python 3.12.10, uv 0.9.30, Node 24.18.0, npm 11.16.0, Rust/Cargo 1.94.1 on `stable-x86_64-pc-windows-msvc`, and WebView2 151.0.4129.78. Microsoft C++ Build Tools with “Desktop development with C++” is required but was not installed; install it before the first E02 build. Release signing and release-grade packaging remain E11.
- **Expected implementation commands:** `uv sync --frozen`; `uv run pytest -q tests/<E02-targeted-paths>`; `npm --prefix desktop ci`; `npm --prefix desktop run typecheck`; `npm --prefix desktop run lint`; `npm --prefix desktop run test:unit`; `cargo fmt --check --manifest-path desktop/src-tauri/Cargo.toml`; `cargo clippy --manifest-path desktop/src-tauri/Cargo.toml --all-targets -- -D warnings`; `cargo test --manifest-path desktop/src-tauri/Cargo.toml`; `npm --prefix desktop run test:desktop`; `npm --prefix desktop run build`; and `npm --prefix desktop run tauri:build -- --debug`. E02 must define these npm scripts without weakening the named checks. The repository FULL gate remains additional and is run once after targeted E02 evidence is ready.
- **Alternatives:** Electron with a sandboxed/context-isolated renderer, per-message preload bridge and Python child over stdio is viable [ARCH-063, ARCH-064] but rejected because its trusted Node/Chromium main/preload surface and bundled Chromium dependency are broader than needed. PySide6/Qt WebEngine with a narrowly published `QWebChannel` object is also viable [ARCH-065, ARCH-066] and integrates directly with Python, but is rejected because published QObject surface discipline is less explicit than Tauri capabilities, the WebEngine deployment is heavier, and LGPL/GPL/commercial plus Chromium notice obligations require additional release review [ARCH-067, ARCH-068]. A browser/localhost Python service is non-viable because it violates the frozen no-listener boundary.
- **Rationale:** Tauri best satisfies the ordered criteria: no listener, least renderer privilege, explicit typed command ACL, preservation of the Python core, current Windows/WebView2 support, auditable security configuration, plausible packaging, and a smaller bundled runtime than Electron. The extra Rust-to-Python pipe is deliberate defense in depth and keeps storage/key authority out of the webview host contract.
- **License:** Tauri framework and JavaScript API/CLI packages are Apache-2.0 OR MIT. WebView2 redistributable terms and all resolved Rust/npm/Python transitive licenses must be captured in the E02 dependency evidence and reconciled for release in E11; this ADR does not claim release clearance.
- **Uncertainty:** The actual Windows desktop tests must prove WebView2 CSP/navigation/origin behavior, sidecar framing/backpressure/crash handling, secret-free renderer surfaces, and packaging of SQLCipher plus the Python sidecar. The absent local C++ Build Tools prerequisite must be installed before those proofs. WebView2 and framework security updates can change runtime behavior.
- **Review trigger:** Any need for TCP/HTTP/local sockets, remote origins/capabilities, renderer shell/filesystem access, a generic Python/CLI dispatcher, direct non-Python domain/storage logic, Tauri below the security floor, incompatible sidecar/SQLCipher packaging, a new webview/window, or failure of mandatory Windows E02 tests requires the architecture-deviation procedure and focused review.
- **Supersedes:** Only ADR-003's deferred desktop-choice uncertainty. It does not supersede ADR-003's no-listener core boundary, authorize network/cloud, authorize real data, change E00/E01 semantics, or open `REAL_DATA_GATE`.
- **Confidence:** high for the boundary pattern; moderate until the actual Windows packaging and adversarial IPC/renderer tests pass.

### ADR-023 — Profile-specific real-data gate evaluation

- **Decision:** Adopt Option B: a stable `REAL_DATA_GATE` policy, a separate stable versioned profile definition, and an exact candidate evaluation/decision instance. The first accepted definition is `local_personal_evidence_reflection_windows_v1` for a local/offline Windows envelope. It is a scope definition to be evaluated, not a statement that current code is ready for real data; accepted or implemented epics do not enable any capability by implication.
- **Question:** How can the closed real-data gate remain stable while a future release is evaluated for one exact profile, build, platform, evidence package, and human decision?
- **Alternatives:** Keep policy, profile, candidate evidence, and live decision in one mutable gate file (rejected: mismatched lifecycles and stale operational truth); introduce a registry/service/PKI attestation platform (rejected: disproportionate new trust and operational boundary for local deployment).
- **Rationale:** Stable policy, a reusable scope definition, and a candidate-specific evaluation change at different rates. `docs/architecture/REAL_DATA_GATE.yaml` owns the fail-closed default and RDG-01--RDG-12 policy; `docs/architecture/REAL_DATA_GATE_PROFILE.yaml` owns the versioned intended scope; `artifacts/e11/gate-evaluations/<evaluation-id>.yaml` will own exact build/profile/evidence/review status and decision data. No valid exact evaluation defaults to `CLOSED`.
- **RDG semantics:** An evaluation binds profile path, ID, version, SHA-256 of the exact profile-file bytes, source commit, source/build/platform, lock/SBOM/artifact identities, evidence, and reviews. Statuses are `PROVED_FOR_CANDIDATE`, `NOT_PROVED`, `NOT_APPLICABLE_EXCLUDED`, `STALE_OR_EXPIRED`, and `UNKNOWN_OR_INCOMPLETE`. Applicability/currentness fail closed; expiry, failed reproduction, regression, incident, or unresolved Critical/High finding invalidates the affected candidate.
- **Lifecycle and human authority:** `DRAFT` is mutable for evidence collection and can never support `OPEN`; deterministic final validation produces immutable `SEALED` content. A future human decision must bind the exact sealed evaluation digest. The sole gate-decider role is `REPOSITORY_OWNER`, using `local_human_attestation_v1`, a version-controlled local human attestation. Coding models cannot provide that human decision. No PKI, service, daemon, or invented signer identity is added; a higher authority requiring stronger cryptographic signing stops the process fail closed rather than silently substituting another method.
- **Gate effect:** `REAL_DATA_GATE` remains `CLOSED`. This acceptance neither proves an RDG control nor creates an evaluation, a human attestation, or an `OPEN` decision. ADR-020 and ADR-021 closed-gate requirements remain in force; this entry refines their profile-specific evaluation mechanics without erasing history.
- **Review trigger:** Any enabled-boundary, platform, source/build, dependency/lock/SBOM/license, intended-use/jurisdiction, provider/network, crypto/storage/recovery/deletion, evidence/review/attestation expiry, incident, or Critical/High finding change requires a new exact evaluation or successor record and current required reviews.
- **Supersedes:** No prior ADR. It operationalizes, and does not weaken, ADR-020 and ADR-021.
- **Confidence:** high for the local policy/evidence ownership boundary; candidate enforcement and any real-data decision remain unproved pending E11 evidence and human review.

### ADR-024 — Solo product-development control-plane simplification

- **Decision:** For local synthetic-only solo development, LOW/MEDIUM product work uses the current capable coding agent, autonomous in-scope repair, targeted verification, and one final gate. Relevant exact-SHA PR CI may supply that final gate; normal topic-branch push and draft PR are pre-authorized. HIGH/CRITICAL are reserved for a material change to crypto/key lifecycle, storage/recovery integrity, irreversible migration, permissions/network exposure, a real privacy/trust boundary, real-data admission, or material security architecture. Independent review is trigger-based only.
- **Rationale:** Accepted storage, IPC, filesystem, security, and permission mechanisms are not new boundaries by themselves. Requiring model-switch rituals, duplicate full suites, or routine review for ordinary work slows Daily Use progress without adding discriminating assurance.
- **Safety floor:** `REAL_DATA_GATE` remains `CLOSED`; synthetic-only, `NEVER_CLOUD`, provenance, deletion/recovery/crypto invariants, valid-test integrity, and action-based approval for protected actions remain unchanged.
- **Rollback:** Revert this entry's control-plane commit to restore the prior routing and verification defaults; no product behavior or real-data state is changed.
- **Review trigger:** Any material protected-boundary change, or concrete evidence that an independent review or additional proof can alter readiness.
- **Confidence:** high for workflow simplification; safety invariants are unchanged.

### ADR-025 — AI-led personal inquiry product reorientation

- **Decision:** Reorient PSYCHE OS from a primarily local reflection/evidence-analysis product with bounded AI on top to an **AI-led Personal Inquiry & Evidence System**. The local Evidence OS remains the canonical, provider-independent memory, provenance and epistemic-control layer. Personal AI Interview V1 is the next implementation vertical; its justified boundary is frozen in `docs/architecture/AI_INTERVIEW_V1.md`.
- **Question:** How can PSYCHE make long-term, evidence-grounded inquiry the primary Daily Use experience without turning an AI interpretation into truth, weakening owner agency, or eroding the local Evidence OS?
- **Evidence:** The accepted product-direction Task Contract dated 2026-08-28; the accepted v2 foundation's provenance, source/derived, privacy, local ownership, correction/deletion, temporal, safety and provider-independence architecture; completed Personal Mode v1 capabilities.
- **Alternatives:** retain archive/control-panel-first navigation with only one-shot optional AI proposals; rewrite the foundation around opaque provider memory; frame the AI as therapist/companion; introduce a generic autonomous agent.
- **Rationale:** The existing foundation supplies the safeguards necessary for a meaningful long-term inquiry system. Process-leading AI can improve continuity and information value only when it remains evidence-bounded, defeasible, consented, inspectable, stateless at the provider, and unable to claim authority over the person.
- **Frozen consequences:** AI may choose inquiry direction and question sequencing inside a foreground session, but not truth, permissions, policy, diagnosis, causal fact, or canonical evidence. USER answers persist as source before provider work; all AI outputs are derived; bounded local retrieval, explicit outbound eligibility, memory-only runtime consent, stateless foreground calls, local validation, atomic derived-state commits, idempotent USER submission, content-minimizing disclosure receipts, and correction/deletion compatibility are required. Provider memory, `previous_response_id`, hosted files/vector stores/tools/web, whole-vault cloud RAG, background AI, hidden profiles and generic agent loops are excluded.
- **Uncertainty:** V1 context bounds, scoring/selection heuristics, evaluation corpus and exact internal state/schema names require a later bounded implementation contract and synthetic evidence. This decision does not authorize implementation or real/provider data disclosure.
- **Review trigger:** any new or materially changed network/provider/privacy/consent boundary, background autonomy, provider-hosted memory/tooling, canonical semantic change, migration, real-data admission, clinical/recommendation expansion, or evidence that the boundary cannot preserve correction/deletion/provenance semantics.
- **Supersedes:** ADR-001 only as to current product identity, and ADR-018 only as to primary UI priority. Their evidence-preserving, anti-dependency and nonclinical rationale remains in force. No constitutional invariant, real-data gate, crypto/key, storage, recovery or deletion decision is superseded.
- **Confidence:** high for product direction and retained safeguards; implementation/evaluation readiness remains unproved.

## Supersession

ADR-021 partially supersedes ADR-020 only for epic allocation; it does not alter
any constitutional or real-data opening requirement. Future entries must state
`supersedes`, preserve the earlier record, name migrations and identify whether
constitutional or real-data gates are affected.

ADR-022 supersedes only ADR-003's deferred desktop-choice uncertainty. ADR-003's
no-listener Python core and every constitutional, network and real-data boundary
remain in force.

ADR-025 supersedes ADR-001's product-category framing and ADR-018's
archive-first UI priority only. It does not alter their underlying evidence, local
ownership, nonclinical or anti-dependency constraints, and it does not authorize a
provider, network, real-data or canonical-semantics change.
