# Personal Mode foundation — bounded context pack

**Base:** `44129765e05cb6f6c69c115a3718e09efc1a58e2`
**Branch:** `codex/personal-mode-foundation`
**Risk:** `CRITICAL`
**Gate at orientation:** `CLOSED`

This pack records the architecture confirmation required before implementation.
It contains no personal data and does not authorize Personal writes or an
`OPEN` decision.

## Authority and exact profile

Authority is resolved as Constitution → v2 master specification → accepted
ADRs → stable gate/profile → current state → task contract → implementation and
candidate evidence. The load-bearing decisions are ADR-003/004/005/007 through
010, ADR-018 through ADR-023, Master Spec sections 16 and 19 through 25, and
Constitution C-02, C-10 through C-14, and C-18 through C-20.

`local_personal_evidence_reflection_windows_v1` enables only:

- canonical encrypted storage with OS convenience wrap and independent
  recovery;
- encrypted backup, isolated restore, and scoped Windows filesystem access;
- the desktop renderer, typed IPC, and local sidecar;
- local archive and disposable deterministic retrieval.

It excludes attachments/blobs, import/parser/rendering, provider/model/network,
assessment/scoring, longitudinal/N-of-1/intervention, and professional/external
handoff. Owner-only open portability export is not the excluded professional or
audience-specific handoff boundary.

## Current byte lifecycle

All durable Reflection bytes currently live in one non-canonical SQLCipher v9
database at `reflection-workspace.db`; its only persisted key material is a
direct DPAPI wrap at `reflection-workspace.key.dpapi`.

| Record class | Current store/copies | Current lifecycle result |
| --- | --- | --- |
| Session title/state/time | `reflection_sessions`; renderer/IPC while open | SQLCipher + DPAPI only; no independent recovery/backup/export |
| User turns | `reflection_turns`; renderer/IPC/DOM | Same gap |
| Exploration answers | turns, context items, source links, snapshot context | Reconstructive duplication; cascade delete only |
| Formulations/corrections | formulation history and snapshot references | History is explicit; not in portable/recoverable package |
| Action plans/outcomes | action plan/outcome tables | No backup/export/recovery or persisted deletion receipt |
| Search | live SELECT and transient excerpt | No on-disk index; plaintext exists in process/IPC/DOM |
| Review/Return/Longitudinal views | process/DOM projections | Current Review/Dynamics are longitudinal and excluded in Personal |
| Evidence notebook | absent; E03 desktop archive is in-memory synthetic state | Deferred |
| Deletion receipt | response only | Not persisted; no backup-expiry state |
| Backup/recovery/export UI | separate temporary V1 synthetic vault | Does not cover Reflection bytes |

No current Reflection path has a RecoveryWrapper header, VMK-derived database/
backup/export keys, tested isolated restore, open export round trip, key
rotation, candidate-bound plaintext scan, or backup-expiry record.

## Confirmed defects and gaps

1. The product reports offline/cloud-disabled while an explicitly configured
   SYNTHETIC_LAB provider can make an outbound OpenAI call.
2. The launcher expects `psyche-os.exe`, while the release binary is
   `psyche-os-desktop.exe`.
3. Native smoke relies on a stale Home marker.
4. The desktop flattens E07 structured proposal semantics and renders unknown
   uncertainty twice.
5. Search can match after character 200 while displaying only the first 200
   characters.
6. Reflection backup/recovery/export buttons operate on a disposable V1 vault,
   not the durable Reflection database.
7. ExportBuilder may swallow unsupported-table query failures and produce a
   verified empty export; this cannot prove portability.
8. First-start Reflection key publication is an `exists` then `write_bytes`
   race; concurrent starts can orphan the database key.
9. E11 allows always-applicable RDG-09 through RDG-12 to be classified as
   excluded; the accepted RDG-11 test demonstrates the gap.
10. E11 review entries are declarations inside the evaluation and are not yet
    bound to a separately validated human-result artifact.
11. `reflection_exploration.get` is content-bearing but currently bypasses the
    unlock/session-required set.
12. Search/AI Rust handlers are absent from the native build/capability ACL,
    and nested AI selection casing disagrees between TypeScript and Rust.
13. Rust length checks count UTF-8 bytes while the Python/TypeScript contract
    counts Unicode characters.
14. `get_session` is unbounded; a response beyond the 65,536-byte sidecar frame
    can terminate the process because response writing occurs outside request
    exception mapping.
15. Sidecar packaging lacks a deterministic composition manifest and explicit
    excluded-module proof.
16. Candidate/build evidence does not yet distinguish candidate, merged
    product tree, and later evidence commits; binary hashes must cover raw
    bytes rather than text-normalized content.

## Architecture answers

### Recovery and portability

Adding an independent recovery wrap around a single vault VMK and deriving
database/backup/export keys can reuse accepted primitives without changing
algorithms or Argon2 parameters. Supporting the complete v9 Reflection
inventory can likewise extend accepted backup/export mechanics while
preserving V1 readers. Neither exists today.

Crash-safe VMK/database-key rotation does not have an accepted executable
primitive. The current code has only lifecycle enum values. A resumable rekey,
old-read-key retention, failure recovery, and atomic envelope transition need a
focused accepted architecture before implementation.

### Schema and Personal data mode

Both canonical and Reflection schemas constrain `data_mode` to
`synthetic_only`; the Reflection writer also hardcodes it. A truthful
`real_personal` store therefore needs versioned schema evolution. The attached
prompt simultaneously required `real_personal` and forbade/stopped on
migration. This conflict blocks Personal writes under the current contract.

The accepted E11 evaluator uses `requested_data_class: SYNTHETIC_ONLY` for
candidate proof execution. That does not define an accepted authority
transition to `REAL_PERSONAL`; production admission remains closed until the
validation-fixture class and admitted-data class are represented and accepted
as distinct semantics.

The existing canonical entity model already has Report, Observation,
Assertion, Unknown, provenance, policy, versioning, and deletion concepts, but
a Personal Notebook still needs an authorized non-fixture write path and the
same complete lifecycle proof. It is deferred rather than emulated with a
mislabelled record.

### Route classification

- Search and session list/open/resume may be simple deterministic retrieval.
- Current Review Hub, Dynamics, Return, and Follow-up are excluded because the
  renderer assembles them from cross-session generic reads. A future narrow
  Return/Follow-up facade would need its own below-renderer capability proof.
- A free-text user-authored next step/outcome can remain reflection; schedules,
  protocols, comparisons, recommendations, or effectiveness inference cross
  into the excluded intervention boundary.

### Exclusion and gate semantics

An excluded boundary that is reachable or unproved does not become applicable
inside this stable profile. It invalidates the candidate. RDG-09 through
RDG-12 are always applicable and can never be made N/A through exclusions.
RDG-10 and RDG-11 require legitimate human review; machine output may only be
labelled non-authoritative pre-review.

The exact enabled-boundary review matrix comprises each stable-profile
declared class for canonical store/key recovery, backup/restore/filesystem,
desktop/IPC, and local projection, plus a mandatory substantive RDG-11
intended-use/privacy/legal/regulatory deployment review. Excluded feature
boundaries require exclusion proofs, not substitute reviews.

Human authorship, qualification, and independence are procedural owner/reviewer
claims. Intake tooling can validate structure, binding, digest, timestamps and
declared provenance but cannot prove that a human authored a result.

## Safe implementation boundary for this contract

Proceed with the product-truth fixes, Reflection first-start race repair,
fail-closed runtime profile/capability foundation, Rust credential omission,
E11 applicability/review-integrity repairs, launchers, tests, and an improved
prompt. Keep Personal storage unopened and every content command disabled when
LOCAL_PERSONAL is requested.

Do not implement Personal writes, evidence Notebook writes, v9 Personal
backup/restore/export claims, or VMK rotation until a focused decision
explicitly authorizes the compatibility-preserving migration and accepts the
rotation/lifecycle architecture. `REAL_DATA_GATE` remains `CLOSED`.
