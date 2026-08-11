# Architecture deviation — E00 implementation diverges from frozen contract

**Epic:** `E00`
**Status:** `REJECTED`
**Owner:** `E00 focused reviewer`

## Problem

The submitted synthetic-only F0 implementation materially diverges from the
frozen E00 contract and cannot be accepted or used as the base for E01. This
record rejects the implementation divergence; it does not amend the governing
architecture.

## Affected decision

- `CONSTITUTION.md`: C-02, C-03, C-08–C-14, C-19, and C-20.
- `docs/PSYCHE_OS_MASTER_SPEC_v2.0_FINAL.md`: sections 6, 9, 16, 19, and 20.
- `docs/architecture/DATA_MODEL.md` and
  `docs/architecture/PRIVACY_SECURITY_MODEL.md`.
- `docs/prompts/F0_IMPLEMENTATION_PROMPT.md` and
  `docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md`.

## Why the current design fails

The code marks plaintext logical exports as encrypted, cannot verify backups it
creates, permits partial restore, accepts invalid SQLCipher evidence, and does
not enforce the required storage, lineage, synthetic-capability, temporal, and
provenance invariants. Several required commands, migrations, schemas, fault and
property suites, and evidence artifacts are absent. Existing validators and the
implementer report therefore overstate completion.

## Minimal evidence

- Formal Codex Security diff scan of the original E00 snapshot: 10 validated
  findings (`1 Critical`, `6 High`, `3 Medium`), complete 50/50 file coverage.
- Dynamic probes reproduced plaintext in an export whose manifest says
  `encrypted=true`, backup self-verification failure, sibling-directory path
  escape, loss of subtype fields on version close, privacy-policy downgrade,
  and fabrication of unknown time as a point.
- `python -m pytest -q`: 148 tests pass, but the suite does not exercise the
  missing or unsafe required behavior; aggregate coverage is 68% and the
  backup/export module is untested.
- `uv sync --frozen --all-groups`, Ruff, mypy, the F0 validators, and the exact
  `doctor` CLI contract fail. `uv.lock` and multiple required artifacts are
  absent.

## Options

1. Preserve the frozen decisions and repair the implementation.
2. Narrow or defer E00, leaving E01 and all real-data work blocked.
3. Propose an explicit architecture supersession and subject it to focused
   review before implementation.

## Proposed change

Select option 1. Preserve the frozen architecture and rework only the bounded
E00 implementation according to
`docs/prompts/deepseek/E00_FIX_REQUIRED.md`. Re-run the complete E00 acceptance
gate and focused high-risk review after the repair.

## Compatibility / migration impact

No accepted E00 data or schema exists, and only bundled synthetic fixtures are
permitted. The repair may replace the unaccepted schema and implementation, but
must retain canonical semantics, versioning, export verifiability, recovery,
deletion closure, and forward migration guarantees from the frozen contract.

## Security / privacy impact

Acceptance, E01 preparation, and real-data admission remain blocked. The repair
must keep `REAL_DATA_GATE` closed, prevent `NEVER_CLOUD` downgrades, eliminate
plaintext export claims, bind cryptographic and backup evidence to real checks,
and keep imports and synthetic capabilities deny-by-default.

## Can implementation continue safely without a decision?

`YES` — bounded synthetic-only E00 repair and validation may continue.
Acceptance, E01, production use, real-data ingestion, and any gate opening are
blocked. No higher-authority document is changed by this record.
