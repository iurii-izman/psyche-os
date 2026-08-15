# E10 — Codex Review Packet

Focused review material for the required fresh independent Codex review of
E10 (User-Controlled Professional Report and Interchange). This packet
deliberately omits project history, full logs, full diagnostics and any
transcript; it exists to minimize future review cost.

## Scope

- **Base SHA:** `78ff17784474b89c9138bf4db39d9b479e836d70` (accepted `main`,
  E09 accepted `27c536fa8af784a7dc69a3ac99fc1cecd831d906`)
- **Candidate HEAD:** `9ccbfa1b961399d9309f347fd27bae23125b72d4`
  (docs commit follows; implementation HEAD is this SHA)
- **Implementation prompt:** `docs/prompts/deepseek/E10_USER_CONTROLLED_PROFESSIONAL_REPORT.md`
- **Report:** `docs/development/reports/E10.md`

## Changed production files

- `src/psyche_os/reports/e10_professional.py` (new) — report model, canonical
  extractor, linked-counterevidence gathering, redaction/exclusion,
  Markdown + JSON serialization, report identity/digest.
- `src/psyche_os/reports/__init__.py` (new) — package re-exports.
- `src/psyche_os/application/e10_professional_handoff.py` (new) — service:
  preview, authorization, TOCTOU revalidation, generation, receipt.
- `src/psyche_os/adapters/e10_filesystem.py` (new) — narrow outer file writer
  (validated destination, atomic write, no traversal/silent overwrite).

## Changed test files

- `tests/unit/test_e10_professional.py` (new) — escaping, redaction purity,
  transformation identity, report id, content-free manifest, preview digest.
- `tests/integration/test_e10_professional_handoff.py` (new) — selection-only
  membership, audience/purpose visibility, provenance preservation, automatic
  counterevidence (contradiction set, contradicts evidence link, claim naming a
  `contradiction_set_id`), no-counterevidence-when-unlinked, redaction
  non-mutation, exclusion as report-only, hostile content inert, fabricated/
  replayed/cross-service authorization, source-version + policy TOCTOU,
  deleted/superseded rejection, policy fail-closed, determinism, content-free
  receipt/reprs, external-copy truthfulness, filesystem path/overwrite safety,
  provider/network absence.

## Frozen E10 invariants (falsify these)

1. Report membership = explicitly selected canonical `(record_id, version_id)`
   only, minus report-only exclusions; E09 is never selection authority.
2. Audience `mental_health_professional`, purpose
   `professional_consultation_handoff`, profile
   `personal_informational_consultation_handoff` are exact and visible in
   preview, report and manifest.
3. Canonical provenance/epistemic status (source, verbatim report, observation,
   assertion + modality, claim type/status/origin, unknown) survives rendering;
   no new interpretation or diagnostic authority.
4. Materially linked counterevidence (contradiction-set membership,
   contradicts-family evidence links, claim `contradiction_set_id`) is
   automatically included and marked; a linked derived claim is never presented
   without the material.
5. Redaction/exclusion are previewed report transformations bound to exact
   versions; canonical data is never mutated.
6. Hostile/untrusted content is escaped to inert literal text (no HTML, links,
   or markup semantics); manifest/receipt/log/repr surfaces stay content-free.
7. Authorization is service-minted, exact-preview-bound, single-use and
   non-transferable; fabricated/replayed capabilities are rejected.
8. TOCTOU: generation revalidates source/version, policy, audience/purpose
   eligibility, transformations, preview digest and builder/config identity
   against current canonical state; any material change invalidates the
   authorization (no silent reuse).
9. Report + JSON manifest are deterministic for identical canonical inputs.
10. Receipt and `repr` carry only bounded metadata; no report text, excerpts,
    secrets, sensitive paths, unredacted values, or plaintext stable content
    hashes.
11. External-copy limitation is truthful and visible (corrections/deletions do
    not update external copies).
12. No AI/model/provider/network/background-sharing authority; canonical
    workflows are independent of report files.
13. `REAL_DATA_GATE` stays `CLOSED`; E11 stays `PLANNED`; E10 is not accepted
    or merged.

## Trust-boundary summary

- **Read-only canonical access:** the report extractor only `SELECT`s the six
  semantic tables plus `data_policies`, `record_relations`, `evidence_links`,
  `contradiction_members`. No writes, no migration.
- **Policy gate:** fail closed unless every active policy is
  `local_only`/`never_cloud` with `export_rule IN ('allow','redact')` and
  `export_audience` empty or the frozen audience.
- **Authorization:** per-service-instance registry; preview-digest bound;
  consumed after one generation; cross-instance rejection.
- **Filesystem:** narrow outer adapter; base-directory anchored; no
  traversal, symlink/regular-file checks, no silent overwrite; atomic
  `os.replace`. It is an adapter, not an authorization boundary.
- **No new runtime dependency; no network path.**

## Unresolved PENDING_QUALIFIED_REVIEW items

Recorded truthfully (not invented, not waived) in the report/preview/manifest:

- legal/regulatory approval
- privacy/rights approval
- clinical-safety approval
- human-factors approval

## Verification results (exact)

- Targeted E10: `uv run pytest tests/unit/test_e10_professional.py
  tests/integration/test_e10_professional_handoff.py -q` → **28 passed**.
- FULL: `uv run pytest -q` → **617 passed, 1 skipped**
  (`tests/regression/test_regression_proofs.py:263` — Windows admin/symlink,
  pre-existing).
- F0: `uv run python scripts/validate_f0_scope.py` → **PASS**.
- Orchestration: `uv run python scripts/dev/validate_orchestration.py` →
  **112 passed, 0 failed; gate CLOSED**.
- Touched Ruff: clean. Touched strict mypy: clean.
- Ratchet (stable identities vs exact E10 preparation baseline): Ruff 92→92
  (0 new), mypy 13→13 (0 new).

## Known limitations

- Empty `data_policies` is eligible (matches accepted E09 precedent).
- Extractor covers the six semantic text tables; E05 measurement and E06
  experiment-result tables are not separately indexed.
- Revalidation is against the current connection; a concurrent writer between
  revalidation and generation is out of scope for the local single-connection
  synthetic profile.
- The file writer is an outer adapter, not an OS access-control policy
  boundary.

## Highest-value adversarial review questions

1. Can any path cause an unselected record's content to appear as selected
   content (selection bypass, relation-expansion confusion, excluded-record
   leak)?
2. Can a selected claim with linked contradiction/counterevidence be exported
   without that material (missing relation kind, broken `contradiction_set_id`,
   deletion timing)?
3. Can a redaction be bypassed or used to hide then alter content (TOCTOU
   between preview and generation, regex edge cases)?
4. Can an authorization be fabricated, replayed, or used across service
   instances?
5. Can a stale/blocked/deleted source or policy be exported?
6. Can hostile content in any canonical field break out of escaping, manifest,
   receipt, or `repr` surfaces?
7. Is the report/manifest/identity fully deterministic across reruns, and is
   the manifest free of content excerpts?
8. Does the filesystem adapter permit traversal, overwrite, or symlink escape?
9. Is there any hidden AI/model/network/background-sharing authority in the
   E10 code path?
10. Are the `PENDING_QUALIFIED_REVIEW` items recorded truthfully and not
    misrepresented as approvals?
