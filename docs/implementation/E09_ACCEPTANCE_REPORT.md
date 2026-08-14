# E09 RISK-M bounded acceptance report

**Review date:** 2026-08-14
**Verdict:** `ACCEPTED`
**Base:** `0fa1547761b3d2abdb4767775f0a5e05062139f6` (E08 merge)
**Implementation commit:** `27c536fa8af784a7dc69a3ac99fc1cecd831d906`
**Risk:** `RISK-M` (no independent Codex review required; no escalation trigger)
**REAL_DATA_GATE:** `CLOSED`

## Scope

One local, deterministic, rebuildable lexical retrieval capability over synthetic
canonical records. No psychological interpretation, no AI, no embeddings, no cloud,
no new runtime dependency, no canonical schema migration.

## Frozen decisions (implemented)

- **Engine:** application-owned deterministic lexical inverted index in pure Python;
  process-local and disposable. Not FTS5, vector, graph or columnar.
- **Authority:** canonical V5 (and V2 semantic tables) remains sole authority; the
  projection is never evidence, source, report, assertion, claim, policy or
  canonical state and can be deleted/rebuild at any time.
- **Indexed tables:** active `source_artifacts`, `reports`, `observations`,
  `assertions`, `claims`, `unknowns` (`semantic_version=2` where present).
- **Semantics:** NFKC + case fold + `\w+` tokenization; score = total matched-token
  occurrence count; order = (score desc, matched_terms desc, record_id asc);
  `max_results` configurable.
- **Invalidation:** projection is `STALE` when canonical input identity or policy
  identity differs from its manifest; rebuild is explicit.
- **Policy:** fail-closed `BLOCKED` (serves nothing) if any active policy is not
  `local_only`/`never_cloud`.
- **Fallback:** typed `RETRIEVAL_PROJECTION_UNAVAILABLE` when absent/stale/corrupt/
  blocked; canonical archive remains accessible.

## Deliverables

- `src/psyche_os/projections/e09_lexical.py` — builder, tokenizer, identities,
  deterministic `retrieve`, relation expansion, `ProjectionManifest`.
- `src/psyche_os/application/e09_retrieval.py` — `E09RetrievalService`,
  `RetrievalManifest`, `RetrievalOutcome`, staleness/corruption checks.
- `tests/unit/test_e09_retrieval.py`, `tests/integration/test_e09_retrieval.py`.

## Evidence

- Targeted E09 tests: `20 passed` (unit + integration), no skips.
- Full suite: `589 passed, 1 skipped` — the one skip is the unchanged,
  unrelated administrator-only symlink test.
- `uv sync --frozen`: PASS.
- `scripts/validate_f0_scope.py`: PASS.
- `scripts/dev/validate_orchestration.py`: `114 passed, 0 failed`.
- Touched Ruff: PASS; touched strict mypy: PASS.
- Repository-wide static ratchet versus `0fa1547`: zero new Ruff identities and
  zero new mypy identities (Ruff baseline 0/0, mypy baseline 6/6).
- `REAL_DATA_GATE` remains `CLOSED`; E10 remains `PLANNED` and unimplemented.

## Self-review findings

No concrete local defect found. Verified: stale/deleted content cannot be
retrieved (correction, E03 deletion, E08 imported deletion, policy change all
mark stale and rebuild removes content); the projection cannot become sole
authority or bypass policy (fail-closed block); untrusted imported text stays
inert searchable data; rebuild is deterministic; manifests name exact
inputs/config/builder; retrieval references canonical record/version IDs only;
projection removal leaves canonical access intact.

## Decision

E09 meets its frozen acceptance criteria at implementation commit
`27c536fa8af784a7dc69a3ac99fc1cecd831d906` and is accepted for merge preserving
history. No escalation trigger appeared.
