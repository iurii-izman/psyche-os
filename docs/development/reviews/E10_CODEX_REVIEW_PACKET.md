# E10 — Codex Review Packet

Focused review material for the required fresh independent Codex review of
E10 (User-Controlled Professional Report and Interchange). This packet
deliberately omits project history, full logs, full diagnostics and any
transcript; it exists to minimize future review cost.

## Scope

- **Base SHA:** `78ff17784474b89c9138bf4db39d9b479e836d70` (accepted `main`,
  E09 accepted `27c536fa8af784a7dc69a3ac99fc1cecd831d906`)
- **Implementation SHA:** `9ccbfa1b961399d9309f347fd27bae23125b72d4`
- **Candidate HEAD:** `f0708e018c84dadbe1ba1d4bfaafd75e443b991c`
  (F1–F5 `853e6a6`, F6–F7 `d67f051`, F8–F9 `f0708e0`; docs commit may follow)
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

## Disclosure-policy boundary (F6–F9)

- **F6 — missing policy fails closed:** zero active `data_policies` rows now
  returns `POLICY_MISSING` (never silently permissive). Authority: PS-01
  "Missing or contradictory policy fails closed" and Master Spec §409
  "Missing/ambiguous policy fails closed"; PS-03 requires disclosure only after
  policy resolution. The weaker E09 local-retrieval allow-by-absence precedent
  is explicitly not treated as authority for the disclosure gate.
- **F7 — authorization binds the disclosure transaction:** the exact export
  destination is chosen before authorization, is visible on the preview, and is
  bound into the preview digest (never into report bytes); the preview carries
  truthful export-retention semantics. The single-use `disclose()` capability
  covers the complete action (revalidate → build → write → content-free
  receipt) and is consumed by it; destination substitution after authorization
  and any replay fail closed; sensitive destinations never appear in
  receipt/repr/log/error surfaces.
- **F8 — policy applies to every disclosed record:** for each record actually
  disclosed (effective selection + auto-added counterevidence), the applicable
  policy is resolved per the accepted authority (own policy = active
  `data_policies` row whose `target_record_id` is the record, per the E07
  canonical reader; lineage parents via `policy_lineage`; effective axes =
  most-restrictive meet of own + ancestors via `resolve_with_own_policy` in
  `src/psyche_os/policy/engine.py`). No applicable policy → `POLICY_MISSING`;
  ambiguous/contradictory applicable policy (multiple active policies targeting
  the record, or unresolvable axes) → `POLICY_BLOCKED`; an applicable policy
  must satisfy the frozen local/no-cloud, audience-bounded export rules. An
  unrelated policy never authorizes a record without its own applicable policy.
  No new generic policy engine was introduced.
- **F9 — authorization binds the real file operation:** the service owns one
  immutable filesystem writer; `build_preview` resolves the destination to the
  concrete export target through that writer and binds target + destination
  into the preview digest, so the same relative filename under a different base
  directory is a different authorized target. `disclose()` exposes no writer or
  overwrite parameter; overwrite is frozen to `false`, so an existing target is
  never replaced and overwrite cannot change after authorization. Determinism,
  atomic write, traversal/link protections, content-free surfaces and the
  no-network property are preserved.

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
  missing-policy fail-closed + policy-removed TOCTOU (F6), determinism,
  content-free receipt/reprs, external-copy truthfulness, destination visible
  before authorization, invalid-destination rejection, destination substitution
  after authorization, no second-export replay, report bytes deterministic
  across destinations, destination absent from bounded surfaces (F7),
  filesystem path/overwrite safety, exclusion ⊆ selection + excluded-version
  availability (F3), selected-counterevidence non-duplication (F4), real +
  deterministic symlink rejection (F5), provider/network absence.

## Policy semantics conclusion (authority-backed, no deviation)

- **Applicable policy is per-record, and missing/ambiguous policy fails
  closed.** The accepted per-record resolution (E07 canonical reader: own
  policy = active `data_policies` row whose `target_record_id` is the record;
  `policy_lineage` parents; effective axes via `resolve_with_own_policy`) is
  combined with PS-01 "Missing or contradictory policy fails closed"
  (`docs/architecture/PRIVACY_SECURITY_MODEL.md`) and Master Spec §409
  "Missing/ambiguous policy fails closed". No applicable policy for a disclosed
  record → `POLICY_MISSING`; ambiguous/contradictory applicable policy or
  ineligible axes → `POLICY_BLOCKED`. The earlier E09-precedent allow-by-absence
  reading was explicitly set aside; no "global/all" policy semantic exists in
  the authority. An unrelated permissive policy never authorizes a record
  without its own applicable policy.
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
14. Missing/ambiguous export policy fails closed (`POLICY_MISSING` /
    `POLICY_BLOCKED`); the exact export destination, concrete resolved export
    target and export-retention semantics are visible before authorization and
    bound to the single-use capability, which covers the complete authorized
    disclosure action; destination substitution/replay fails closed;
    destination/target never enters report bytes, the receipt, reprs, logs or
    error text.
15. Every record actually disclosed (effective selection + auto-added
    counterevidence) resolves an applicable, eligible export policy; an
    unrelated policy never authorizes a record without its own applicable
    policy; counterevidence cannot bypass policy resolution.
16. The concrete filesystem target is authorization-bound (service-owned
    immutable writer; target + destination in the preview digest); overwrite is
    frozen to `false` and cannot change after authorization; an existing target
    is never replaced.

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
  tests/integration/test_e10_professional_handoff.py -q` → **49 passed,
  1 skipped** (real-symlink creation unavailable on Windows without privilege;
  deterministic link-rejection path-validation coverage is provided).
- FULL: `uv run pytest -q` → **638 passed, 2 skipped** (both are Windows
  symlink/admin skips: the E10 link test and the pre-existing
  `tests/regression/test_regression_proofs.py:263`).
- F0: `uv run python scripts/validate_f0_scope.py` → **PASS**.
- Orchestration: `uv run python scripts/dev/validate_orchestration.py` →
  **112 passed, 0 failed; gate CLOSED**.
- Touched Ruff: clean. Touched strict mypy: clean.
- Ratchet (stable identities vs exact E10 preparation baseline): Ruff 92→92
  (0 new), mypy 13→13 (0 new).

## Known limitations

- Per-record applicable policy must be present and unambiguous for every
  disclosed record (see Policy conclusion); `data_policies.purpose` is not an
  export-gate input by accepted privacy-model authority (export "by audience").
- Extractor covers the six semantic text tables; E05 measurement and E06
  experiment-result tables are not separately indexed.
- Revalidation is against the current connection immediately before the
  disclosure write; a concurrent writer between revalidation and the write is
  out of scope for the local single-connection synthetic profile.
- The service-owned filesystem writer is an outer adapter, not an OS
  access-control policy boundary. Real symlink rejection is verified only where
  the OS permits symlink creation; the link-rejection path-validation logic has
  deterministic coverage on all platforms.

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
12. Does missing/ambiguous export policy fail closed, and is the 
    audience-only export-gate reading of `data_policies` consistent with the
    cited PS-01 / Master Spec §409 / PS-03 authority?
13. Is the exact export destination visible before authorization and bound to
    the single-use capability? Can the destination be substituted or the
    capability replayed to a second destination? Does the destination leak
    into report bytes, receipt, repr, logs, telemetry or error text?
14. **Per-record policy applicability:** can any disclosed record (selection or
    auto-added counterevidence) be exported without its own applicable,
    eligible policy — e.g. an unrelated permissive policy authorizing a record
    with no applicable policy, ambiguous multi-policy targeting, lineage
    relaxation, or a blocked/`NEVER_CLOUD`-violating applicable policy?
15. **Target/base-dir binding:** can the same relative destination be used
    under a different base directory with the same authorization, or can the
    writer/target be substituted after authorization?
16. **Overwrite/replay semantics:** can an existing target be replaced, or can
    an overwrite/write argument change after authorization; is replay to a
    second export rejected; is the capability consumed by the complete action?
17. **TOCTOU:** can source/version, policy, transformations, preview digest or
    target change between revalidation and the disclosure write without
    invalidating the authorization?
18. **Filesystem link/race behavior:** symlink-destination rejection, symlink
    target inside `base_dir`, parent-symlink escape, atomic-write races.
19. **Content leakage:** can report text, excerpts, destinations, full paths,
    or content hashes appear in the receipt, `repr` surfaces, logs, telemetry
    or error text?
