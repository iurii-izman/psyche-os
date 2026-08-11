# PSYCHE OS — E00 bounded repair prompt

## Role and outcome

Repair the existing E00/F0 implementation in `C:\Dev\psyche-os`. Do not
redesign the product, prepare E01, start a later epic, accept E00, create an
acceptance commit, or open `REAL_DATA_GATE`. The outcome is a synthetic-only E00
candidate that truthfully satisfies the complete frozen E00 contract and is
ready for a new focused high-risk review.

## Read before editing

Read, in authority order:

1. `AGENTS.md` and `CONSTITUTION.md`.
2. `docs/development/STATE.yaml`.
3. `docs/prompts/deepseek/E00_F0_IMPLEMENTATION.md` and
   `docs/prompts/F0_IMPLEMENTATION_PROMPT.md` in full.
4. `docs/implementation/E00_ACCEPTANCE_REPORT.md`.
5. `docs/development/deviations/E00_IMPLEMENTATION_DIVERGES_FROM_FROZEN_CONTRACT.md`.
6. The directly relevant portions of `docs/architecture/DATA_MODEL.md`,
   `docs/architecture/PRIVACY_SECURITY_MODEL.md`, and the accepted decision log.

If implementation and authority conflict, preserve the authority. Record any
new material conflict through the deviation template and stop only the blocked
portion. Use bundled synthetic fixtures only.

## Required repairs

### F01 — Logical export confidentiality and truthfulness

Repair `src/psyche_os/backup_export/operations.py` so a logical export never
writes plaintext while claiming encryption. Use the supplied export envelope
key correctly, authenticate metadata, make the manifest describe the actual
format, and verify the produced export end to end. A plaintext canary must not
be recoverable from the exported files.

### F02 — Backup and restore atomicity

Use one canonical byte representation for backup hashes and verification. A
fresh backup must verify with its own verifier. Restore into an isolated target,
validate schema/version/manifest/checksums before replacement, reject unsafe
dynamic identifiers, never suppress row failures, and leave the existing vault
untouched after any failure.

### F03 — Cryptographic envelope and recovery

Remove duplicate AES-GCM encryption under one key/nonce. Give every encrypted
object an independently wrapped data key and authenticated envelope metadata.
Implement the specified OS/recovery wraps with explicit algorithms, bounded
KDF parameters, versioning, rotation/recovery semantics, and testable failure
behavior. Do not claim memory zeroization that Python cannot guarantee.

### F04 — SQLCipher runtime gate

Reject empty or placeholder license evidence, malformed/failed integrity
results, and unproved backup/restore capability. Bind every vault-create/open
path to a fresh passing gate result. Gate output must distinguish unavailable,
failed, and verified capabilities without treating exception text as evidence.

### F05 — Irreversible storage core

Implement the frozen schema, real ordered migrations, and constraints for
canonical IDs, closed version intervals, subtype preservation, foreign keys,
audit reason codes, temporal/provenance references, and deletion closure.
Provide an atomic unit of work. Enforce blob stage → authenticate/verify →
commit, prevent stored-state claims for absent blobs, and make recovery and
garbage collection crash-safe.

### F06 — Policy lineage

Combine a node's own policy with all ancestors. No child may weaken
`NEVER_CLOUD`. Correct material third-party ordering and preserve every required
axis, including retention and audience, in the effective decision. Add monotonic
property tests for lineage, derivative records, exports, logs, and indexes.

### F07 — Synthetic capability and exact CLI

Implement a deny-by-default, non-forgeable synthetic-fixture capability. Direct
writes and arbitrary capture/import paths must fail without it. Implement the
exact CLI and JSON/error contracts required by E00, including `doctor`, gate,
vault lifecycle, migrations, integrity, backup/verify/restore, logical export,
deletion verification, and audit verification. Remove or finish stubs.

### F08 — Reproducible artifacts and honest evidence

Create and lock `uv.lock`; add real migration files, required JSON Schemas,
property/fault/fixture suites, threat-test matrix, license/crypto review, SBOM,
and machine-readable test evidence required by the original prompt. Validators
must validate behavior and artifact contents, not create directories, scan for
substrings, or pass on declarations alone. Update
`docs/implementation/F0_IMPLEMENTATION_REPORT.md` and create
`docs/development/reports/E00.md` only from fresh command results.

### F09 — Filesystem, temporal, and provenance semantics

Resolve paths and use component-aware containment; reject a sibling such as
`vault2` when the root is `vault`. Preserve unknown time as unknown rather than
fabricating a point interval. Enforce canonical, existing provenance endpoints,
valid edge kinds, deterministic canonical configuration digests, contradiction,
correction, and supersession rules.

## Mandatory regression proofs

Add named tests that prove all of the following realistic failures are blocked:

- an export containing a unique plaintext canary;
- a newly created backup that cannot verify or a failed restore that changes
  the current vault;
- `vault/../vault2` path escape;
- closing a subtype version while losing subtype fields;
- any inherited-policy downgrade, including `NEVER_CLOUD` and material
  third-party scope;
- conversion of unknown time to a known point;
- invalid license, integrity, or backup evidence producing an available gate;
- a direct write performed without the bundled synthetic-fixture capability;
- dangling/noncanonical provenance and interrupted blob/deletion/migration
  operations.

All original E00 acceptance criteria remain binding even if not repeated here.

## Validation sequence

Iterate with targeted tests. Then run the risk-appropriate final gate once:

```powershell
Set-Location 'C:\Dev\psyche-os'
uv sync --frozen --all-groups
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run coverage erase
uv run coverage run -m pytest
uv run coverage report --show-missing
uv run python scripts/validate_f0_scope.py
uv run python scripts/validate_f0_artifacts.py
uv run python -m psyche_os doctor --json
uv run python -m psyche_os gate status --json
uv run python scripts/dev/validate_orchestration.py
uv run python scripts/validate_research_foundation.py
git diff --check
git status --short
```

Do not substitute a smaller passing suite for these commands. Do not use an
arbitrary coverage target; every test must cover a named contract or realistic
failure.

## State and handoff

If and only if every required repair and command passes truthfully:

- keep `current_epic.status: IMPLEMENTED`;
- set `current_epic.review_verdict: REVIEW_REQUIRED`;
- retain the acceptance report as historical evidence and replace no finding
  without a regression proof;
- set `next_action.prompt` to
  `docs/prompts/codex/HIGH_RISK_EPIC_REVIEW_TEMPLATE.md`;
- keep E01 `PLANNED`, `accepted_epics: []`, `accepted_commit: null`, and
  `REAL_DATA_GATE: CLOSED`.

Do not commit, push, accept E00, or prepare E01. The next action after repair is
an independent focused high-risk review.
