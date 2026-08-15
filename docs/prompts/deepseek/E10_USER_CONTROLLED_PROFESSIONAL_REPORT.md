# PSYCHE OS — E10 User-Controlled Professional Report and Interchange

**Project root:** `C:\Dev\psyche-os`
**Implementation branch:** `codex/e10-professional-handoff`
**Prepared from:** E09 accepted `27c536fa8af784a7dc69a3ac99fc1cecd831d906`
**Risk:** `RISK-H` — independent Codex review is required before acceptance.

## Objective

Implement the smallest deterministic professional handoff slice: one frozen
profile for an adult owner manually providing selected synthetic records to a
mental-health professional as a personal informational consultation handoff.

Explicit record selection → local preview → optional exclusion/redaction →
exact single-use authorization → deterministic handoff report (Markdown/plain
text) + deterministic JSON manifest → content-free disclosure receipt.

No diagnosis, no clinical decision support, no treatment guidance, no shared
vault, no background sharing, no AI/model call, no network, no real data.

## Read first

- `AGENTS.md`, `CONSTITUTION.md`, `docs/development/STATE.yaml`.
- `src/psyche_os/storage/schema.py` and `src/psyche_os/storage/e03_schema.py`
  (canonical V2 semantic tables and relations).
- `src/psyche_os/projections/e09_lexical.py` (canonical access, relation
  expansion, digest pattern — reuse, do not duplicate).
- `src/psyche_os/application/e09_retrieval.py` (service/manifest pattern).
- `src/psyche_os/adapters/e08_filesystem.py` (outer filesystem boundary style).
- `tests/integration/test_e09_retrieval.py` and
  `src/psyche_os/application/e03_archive.py` (fixture records for tests).

Do not load historical v1 prompts, the research dossier, or unrelated
architecture. The North Star is forward-compatibility only: E10 adds no
conversational capability.

## Frozen decisions

- **Profile:** `personal_informational_consultation_handoff`; audience
  `mental_health_professional`; purpose `professional_consultation_handoff`.
  The report is a derived informational copy, never canonical truth, a medical
  record, diagnosis, clinical decision support, treatment guidance, or
  synchronized professional access.
- **Selection:** final membership comes only from explicitly selected canonical
  `(record_id, version_id)` pairs. E09 may assist discovery only; it is never
  selection authority.
- **Output:** deterministic UTF-8 Markdown report + deterministic JSON
  manifest. Manifest carries report identity and per-record provenance/status
  metadata, never content excerpts.
- **Policy gate:** report generation fails closed unless every active
  `data_policies` row is `local_only`/`never_cloud` with
  `export_rule IN ('allow','redact')` and `export_audience` empty or
  `mental_health_professional`.
- **Counterevidence:** selected records with directly linked canonical
  contradiction/counterevidence (contradiction-set membership or
  `contradicts`-family evidence links) automatically include the linked
  material marked as counterevidence; only accepted canonical relations are
  used, no new interpretation.
- **Redaction/exclusion:** report transformations only, bound to exact
  canonical `(record_id, version_id)` and previewed before authorization;
  canonical data is never mutated.
- **Authorization:** service-minted, exact-preview-bound, single-use,
  non-transferable across service instances; fabricated/replayed/reused
  capabilities are rejected.
- **TOCTOU:** immediately before generation, revalidate record existence/
  version, policy, audience/purpose eligibility, transformations, preview and
  builder/config identity; any material change invalidates the authorization
  (no silent reuse).
- **Filesystem:** narrow outer adapter only; validated destination, no
  traversal, no silent overwrite, atomic write. No upload/network.
- **Receipt/logging:** content-free disclosure receipt; no report text,
  excerpts, secrets, sensitive paths, unredacted values, or plaintext stable
  content hashes in receipts, logs, or `repr`.

## In scope

- Report profile + intended-use boundary (unresolved approvals recorded as
  `PENDING_QUALIFIED_REVIEW`, never invented).
- Report model/builder, deterministic Markdown + JSON manifest, report
  identity/digest, provenance/status rendering, linked counterevidence,
  redaction/exclusion, preview + authorization + TOCTOU revalidation, content-
  free receipt, narrow filesystem adapter, focused tests.

## Out of scope

- Clinician portal/shared vault, automatic/background sharing, FHIR/EHR,
  PDF/DOCX, professional account/access model, clinician synchronization,
  AI-written narrative, diagnosis, treatment recommendations, medication
  advice, clinical triage, WorkingFormulation, conversational features, new
  importers, E11, real data.
- Broad audit, refactoring, speculative architecture, Security Workbench.

## Invariants to protect

- Canonical V2 tables and relations are read-only for E10 (no schema change).
- `NEVER_CLOUD` and `local_only` semantics; hostile imported content stays
  inert DATA.
- Receipts/logs/repr stay content-free; `REAL_DATA_GATE` stays `CLOSED`.

## Failure-driven tests

1. only explicitly selected records enter the report;
2. audience/purpose exact and visible in preview/report;
3. provenance/epistemic status (source/verbatim/observation/assertion/claim/
   unknown) survives rendering;
4. material linked counterevidence not silently hidden;
5. redaction/exclusion cannot mutate canonical content and is previewed;
6. hostile HTML/Markdown/URL content stays inert literal text;
7. fabricated/replayed/cross-service authorization rejected;
8. source-version and policy TOCTOU invalidates authorization;
9. deleted/superseded record rejection;
10. deterministic report + JSON manifest;
11. content-free receipt/repr/logs (no excerpts, paths, content hashes);
12. external-copy limitation truthful and visible;
13. filesystem overwrite/path safety (if file output used);
14. provider/network absence (bare sqlite works).

## Acceptance criteria

- All 14 failure-driven invariants above pass with named failure coverage.
- No AI/network/background-sharing authority; canonical workflows independent
  of report files.
- E10/touched Ruff and strict mypy PASS; zero new repo-wide identities vs the
  E10 preparation baseline (compare stable identities mechanically).
- `uv run pytest -q`, `uv run python scripts/validate_f0_scope.py`,
  `uv run python scripts/dev/validate_orchestration.py` PASS.
- `REAL_DATA_GATE` stays `CLOSED`; E11 stays `PLANNED`; E10 ends
  `IMPLEMENTED / PENDING_REVIEW`.

## Escalation trigger

Stop with `E10_ARCHITECTURE_DEVIATION_REQUIRED` if E10 requires semantic
modification of accepted canonical contracts, new major persistence/trust
architecture, FHIR/portal/cloud service, cryptographic sharing, AI-generated
clinical capability, real data, or an unresolved authority conflict.

## Report

`docs/development/reports/E10.md`; review packet
`docs/development/reviews/E10_CODEX_REVIEW_PACKET.md`; update
`docs/development/STATE.yaml`. Do not accept or merge E10. Do not implement E11.
