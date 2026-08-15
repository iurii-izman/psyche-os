# E10 RISK-H acceptance report

**Review date:** 2026-08-15
**Verdict:** `ACCEPTED`
**Base:** `78ff17784474b89c9138bf4db39d9b479e836d70` (main before the E10 merge)
**Accepted implementation commit:** `6c2ccf75637ef85db42bc62caf206c1c0e736d21`
**F10 fix commit:** `dd97c0f`
**Risk:** `RISK-H`
**REAL_DATA_GATE:** `CLOSED`

## Review

The original E10 Task Contract required a fresh independent Codex review. Codex
was unavailable (credits exhausted). Before the review, the architect/user
**explicitly authorized a temporary substitution**: a fresh strong independent
reviewer in place of Codex. The review ran in a fresh session and reported its
observable runtime model as `claude-opus-5[1m]`. DeepSeek V4 Pro was
requested/configured but was **not observably confirmed**. The original
Codex-review requirement remains a recorded historical contract fact; the
substitution is accepted for E10 closure. Codex did **not** review E10, and
DeepSeek V4 Pro is **not** claimed as the observed reviewer.

## Scope

Smallest deterministic professional handoff slice for the frozen profile
`personal_informational_consultation_handoff` (audience
`mental_health_professional`, purpose `professional_consultation_handoff`):
explicit record selection → local preview → optional exclusion/redaction →
exact single-use authorization → deterministic Markdown report + JSON manifest
→ content-free disclosure receipt. No psychological interpretation, no AI/model/
provider/network authority, no cloud, no new runtime dependency, no canonical
schema migration, no canonical writes.

## Deliverables

- `src/psyche_os/reports/e10_professional.py` — report model, canonical
  extractor, linked-counterevidence gathering, redaction/exclusion, Markdown +
  JSON serialization, report identity/digest.
- `src/psyche_os/application/e10_professional_handoff.py` — service: preview,
  authorization, TOCTOU revalidation, transitive policy-lineage resolution,
  generation, content-free receipt.
- `src/psyche_os/adapters/e10_filesystem.py` — narrow outer file writer.
- `tests/unit/test_e10_professional.py`,
  `tests/integration/test_e10_professional_handoff.py`.

## Evidence

- Targeted E10 (F1–F10): `55 passed, 1 skipped` (real-symlink creation
  unavailable on Windows without privilege; deterministic link-rejection
  coverage provided).
- Full suite `uv run pytest -q`: `644 passed, 2 skipped` (both Windows
  symlink/admin skips).
- `scripts/validate_f0_scope.py`: PASS.
- `scripts/dev/validate_orchestration.py`: `112 passed, 0 failed; gate CLOSED`.
- Touched Ruff: clean; touched strict mypy: clean.
- No-new-diagnostic ratchet (current tool versions): Ruff 215→215 (0 new),
  mypy 40→40 (0 new).
- `REAL_DATA_GATE` remains `CLOSED`; E11 remains `PLANNED`.

## Review findings and residuals

- **G-2 (blocking, strong review):** E10 policy resolution originally composed
  only direct `policy_lineage` parents. **Fixed by F10** (`dd97c0f`): the
  effective export policy is the most-restrictive meet of the record's own
  policy and its **complete transitive** `policy_lineage` ancestor set; a
  restrictive grandparent or deeper ancestor can never be omitted or weakened;
  lineage cycle, dangling/missing or ambiguous ancestor reference, and
  composition failures fail closed; ancestors are deduplicated deterministically;
  counterevidence uses the same transitive resolution. Failure-driven lineage
  tests A–F added.
- **Filesystem no-clobber race (LOW, accepted residual):**
  `ReportFileWriter.write()` performs `exists()` → concurrent creation →
  `os.replace()`. A concurrently created target can be clobbered in the window
  between the check and the replace. Accepted under the single-user threat
  model; no absolute race-free no-clobber behavior is claimed.
- **E07 inherited debt (documented, non-blocking):** the E07 canonical reader
  retains its direct-parent `policy_lineage` reader for the E07 LLM-disclosure
  path; it is not part of the E10 disclosure gate.
- **Unresolved qualified items (truthfully unresolved, non-blocking):**
  professional/legal/privacy/clinical-safety/human-factors approvals remain
  `PENDING_QUALIFIED_REVIEW` and are recorded as such, never invented or waived.

## Carry-forward (not E10 blockers)

1. Verify/fix policy-lineage persistence/FK/version semantics before any
   real-data gate opening.
2. Optional atomic filesystem no-clobber hardening.
3. AI Dev OS M-002 effective-model/provider attestation.

## Decision

E10 meets its frozen acceptance criteria at implementation commit
`6c2ccf75637ef85db42bc62caf206c1c0e736d21` and is accepted for merge preserving
history, under the explicit architect/user-authorised reviewer substitution
recorded above. `REAL_DATA_GATE` remains `CLOSED`; E11 remains `PLANNED`.
