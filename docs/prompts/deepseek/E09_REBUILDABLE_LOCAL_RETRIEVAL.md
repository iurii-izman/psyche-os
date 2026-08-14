# PSYCHE OS — E09 Rebuildable Projections and Local Retrieval

**Project root:** `C:\Dev\psyche-os`
**Branch:** `codex/e09-local-retrieval`
**Prepared from:** E08 accepted `1e6dcd86dd226bc84ef728d643fd21db4ecc1fb9`
**Risk:** `RISK-M` — no independent Codex review unless an escalation trigger appears.

## Objective

Add one local, deterministic, rebuildable lexical retrieval capability over
synthetic canonical records. Given a bounded local text query, return
deterministically ranked canonical record/version IDs by lexical matching while
preserving exact provenance/policy identity and exposing existing canonical
counterevidence/contradiction/unknown relations.

No psychological interpretation. No AI. No semantic embeddings. No cloud.
No new runtime dependency. No canonical schema migration.

## Frozen decisions

- **Engine:** application-owned deterministic lexical inverted index in pure
  Python, process-local and disposable. Not FTS5, not a vector/graph/columnar
  engine.
- **Projection authority:** canonical V5 (and its V2 semantic tables) is the
  sole authority. The projection is never evidence, source, report, assertion,
  claim, policy or canonical state; it can be deleted and rebuilt at any time.
- **Indexed canonical tables:** active `source_artifacts`, `reports`,
  `observations`, `assertions`, `claims`, `unknowns` (`semantic_version=2` where
  that column exists). E08 imported text is already projected into
  `reports`/`assertions`, so `e08_import_nodes` is not indexed separately.
- **Retrieval semantics:** NFKC normalization + case fold + `\w+` tokenization
  (punctuation dropped, no stemming/stopwords). Score = total occurrence count
  of matched query tokens. Order = (score desc, matched_terms desc, record_id
  asc). `max_results` configurable, default 20.
- **Invalidation:** a projection is `STALE` when canonical input identity
  (digest over active record/version set) or policy identity (digest over active
  `data_policies` rows) differs from its manifest. Rebuild is explicit.
- **Policy:** projection is `BLOCKED` (serves nothing) if any active policy is
  not `local_only`/`never_cloud` — fail closed, cannot bypass privacy.
- **Fallback:** typed `RETRIEVAL_PROJECTION_UNAVAILABLE` when no projection or
  when it is stale/corrupt/blocked; canonical archive remains accessible.

## Deliverables

- `src/psyche_os/projections/e09_lexical.py` — builder, tokenizer, identities,
  deterministic `retrieve`, relation expansion, `ProjectionManifest`.
- `src/psyche_os/application/e09_retrieval.py` — `E09RetrievalService`,
  `RetrievalManifest`, `RetrievalOutcome`, staleness/corruption checks.
- `tests/unit/test_e09_retrieval.py`, `tests/integration/test_e09_retrieval.py`.

## Failure-driven tests

1. known-answer lexical retrieval;
2. deterministic ranking/ties;
3. deterministic rebuild/digest;
4. correction marks stale;
5. deletion marks stale;
6. E08 imported deletion marks stale;
7. policy change marks stale;
8. rebuild removes deleted/ineligible content;
9. corrupt/stale projection rejected;
10. projection deletion does not damage canonical data;
11. no-projection fallback/unavailable state;
12. retrieval manifest references canonical IDs/versions only;
13. canonical counterevidence/contradiction/unknown relations preserved;
14. instruction-shaped imported text remains inert;
15. no AI/network/provider authority.

## Acceptance criteria

- Projection can be deleted/rebuilt deterministically from canonical records.
- Stale/deleted/policy-blocked content disappears deterministically.
- Manifest names all inputs/config/builder; no raw record content in manifest/logs.
- Retrieval never becomes evidence or canonical truth.
- E09/touched Ruff and strict mypy PASS; zero new repo-wide identities.
- Full pytest, `validate_f0_scope.py`, `validate_orchestration.py` PASS.
- `REAL_DATA_GATE` stays `CLOSED`.

## Escalation trigger

Stop with `E09_DEFERRED_FOR_CODEX` only if embeddings, vector DB, external
service, LLM/neural ranking, new provider, canonical semantic change,
non-additive schema change, or a new external trust boundary becomes required.

## Report

`docs/implementation/E09_ACCEPTANCE_REPORT.md`; `docs/development/reports/E09.md`;
update `docs/development/STATE.yaml`. Do not implement E10.
