# E10 — Codex Review Packet

Focused review material for the required fresh independent Codex review of
E10 (User-Controlled Professional Report and Interchange). This packet
deliberately omits project history, full logs, full diagnostics and any
transcript; it exists to minimize future review cost.

## Scope

- **Base SHA:** `78ff17784474b89c9138bf4db39d9b479e836d70` (accepted `main`,
  E09 accepted `27c536fa8af784a7dc69a3ac99fc1cecd831d906`)
- **Candidate HEAD:** `853e6a690bb93bd4ec82a01653f1f387bb61822d`
  (implementation `9ccbfa1` + hardening `853e6a6`; a docs commit may follow)
- **Implementation prompt:** `docs/prompts/deepseek/E10_USER_CONTROLLED_PROFESSIONAL_REPORT.md`
- **Report:** `docs/development/reports/E10.md`

## Pre-review hardening (F1–F5)

- **F1 — frozen profile:** `ReportConfig` now fails closed at construction on
  any non-frozen profile/audience/purpose/output format
  (`UNSUPPORTED_PROFILE`/`UNSUPPORTED_AUDIENCE`/`UNSUPPORTED_PURPOSE`/
  `UNSUPPORTED_OUTPUT_FORMAT`); there is no generic profile framework.
- **F2 — authorization bypass removed:** `force_register_for_test()` is gone;
  there is no callable production path to register an arbitrary authorization.
  Cross-service/non-transferability coverage now uses test-only private-state
  injection.
- **F3 — exclusion validation:** exclusions must be members of the exact
  explicit selection (`INVALID_EXCLUSION` otherwise) and the excluded version
  must exist/be available (`RECORD_UNAVAILABLE`); fabricated/unselected IDs
  cannot appear as excluded metadata. Report-only non-mutation is unchanged.
- **F4 — counterevidence duplication:** materially linked counterevidence
  already explicitly selected is not emitted a second time; contradicts-family
  evidence links are resolved directionally (a source contradicting a selected
  target is its counterevidence; the contradicted target is not the source's),
  via `evidence_links`, not the direction-agnostic relation expansion.
- **F5 — symlink guarantee:** `ReportFileWriter` rejects the destination link
  on the unresolved path before `.resolve()`, so a symlink whose target stays
  inside `base_dir` cannot hide; containment re-check after resolution remains.
  Real-symlink coverage runs only where the OS permits creation; deterministic
  path-validation coverage is provided on all platforms (documented limitation).

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
  transformation identity, report id, content-free manifest, preview digest,
  frozen-profile cannot-be-widened (F1).
- `tests/integration/test_e10_professional_handoff.py` (new) — selection-only
  membership, audience/purpose visibility, provenance preservation, automatic
  counterevidence (contradiction set, contradicts evidence link, claim naming a
  `contradiction_set_id`), no-counterevidence-when-unlinked, redaction
  non-mutation, exclusion as report-only, hostile content inert, fabricated/
  replayed/cross-service authorization, no-production-bypass (F2), source-
  version + policy TOCTOU, deleted/superseded rejection, policy fail-closed,
  determinism, content-free receipt/reprs, external-copy truthfulness,
  filesystem path/overwrite safety, exclusion ⊆ selection + excluded-version
  availability (F3), selected-counterevidence non-duplication with both
  contradiction sides selected (F4), real + deterministic symlink rejection
  (F5), provider/network absence.

## Policy semantics conclusion (authority-backed, no deviation)

- **Empty `data_policies` is intentionally allow-by-absence.** The E09 accepted
  contract's fail-closed rule is universal quantification over *active*
  policies ("any active non-`local_only`/`never_cloud` policy blocks",
  `docs/development/reports/E09.md` and
  `docs/prompts/deepseek/E09_REBUILDABLE_LOCAL_RETRIEVAL.md`); an empty active
  set satisfies it. E10 mirrors this exactly. **Preserved.**
- **`data_policies.purpose` is not an export-gate input.** The accepted privacy
  model defines export as "allow / redact / block / ask, **by audience**"
  (`docs/architecture/PRIVACY_SECURITY_MODEL.md`); `purpose` belongs to the
  local/cloud policy ("named allowed providers/purposes"), the E07
  LLM-disclosure path, not the E10 local export gate. Enforcing it would be
  invented semantics. **Preserved.**

No `E10_ARCHITECTURE_DEVIATION_REQUIRED`.

## Frozen E10 invariants (falsify these)

1. Report membership = explicitly selected canonical `(record_id, version_id)`
   only, minus report-only exclusions; every exclusion is a member of the exact
   explicit selection; E09 is never selection authority. The profile is frozen
   (unsupported profile/audience/purpose/output fails closed).
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
   without the material; already-selected counterevidence is not duplicated.
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
  tests/integration/test_e10_professional_handoff.py -q` → **34 passed,
  1 skipped** (real-symlink creation unavailable on Windows without privilege;
  deterministic link-rejection path-validation coverage is provided).
- FULL: `uv run pytest -q` → **623 passed, 2 skipped** (both are Windows
  symlink/admin skips: the E10 link test and the pre-existing
  `tests/regression/test_regression_proofs.py:263`).
- F0: `uv run python scripts/validate_f0_scope.py` → **PASS**.
- Orchestration: `uv run python scripts/dev/validate_orchestration.py` →
  **112 passed, 0 failed; gate CLOSED**.
- Touched Ruff: clean. Touched strict mypy: clean.
- Ratchet (stable identities vs exact E10 preparation baseline): Ruff 92→92
  (0 new), mypy 13→13 (0 new).

## Known limitations

- Empty `data_policies` is eligible by accepted E09 authority; `purpose` is not
  an export-gate input by accepted privacy-model authority (see Policy
  conclusion).
- Extractor covers the six semantic text tables; E05 measurement and E06
  experiment-result tables are not separately indexed.
- Revalidation is against the current connection; a concurrent writer between
  revalidation and generation is out of scope for the local single-connection
  synthetic profile.
- The file writer is an outer adapter, not an OS access-control policy
  boundary. Real symlink rejection is verified only where the OS permits
  symlink creation; the link-rejection path-validation logic has deterministic
  coverage on all platforms.

## Highest-value adversarial review questions

1. Can any path cause an unselected record's content to appear as selected
   content (selection bypass, relation-expansion confusion, excluded-record
   leak)?
2. Can a selected claim with linked contradiction/counterevidence be exported
   without that material (missing relation kind, broken `contradiction_set_id`,
   deletion timing), or be duplicated when the counterevidence is itself
   selected?
3. Can a redaction be bypassed or used to hide then alter content (TOCTOU
   between preview and generation, regex edge cases)?
4. Can an authorization be fabricated, replayed, or used across service
   instances, or registered through any production callable?
5. Can a stale/blocked/deleted source or policy be exported?
6. Can hostile content in any canonical field break out of escaping, manifest,
   receipt, or `repr` surfaces?
7. Is the report/manifest/identity fully deterministic across reruns, and is
   the manifest free of content excerpts?
8. Does the filesystem adapter permit traversal, overwrite, symlink escape, or
   a symlink whose target stays inside `base_dir`?
9. Is there any hidden AI/model/network/background-sharing authority in the
   E10 code path?
10. Are the `PENDING_QUALIFIED_REVIEW` items recorded truthfully and not
    misrepresented as approvals?
11. Can the frozen profile be widened (arbitrary audience/purpose/output)? Can
    an exclusion name a fabricated or unselected ID?
12. Is the allow-by-absence and audience-only export-gate reading of
    `data_policies` consistent with the cited E09 and privacy-model authority?
