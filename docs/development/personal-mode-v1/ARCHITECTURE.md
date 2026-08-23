# Personal Mode v1 admission architecture

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW**. Base: `166832da18d913f591c3956346e41b7b5e742a5a`. No production code changed; `REAL_DATA_GATE` is `CLOSED`.

## Problem, authority, and constraints

V9 Reflection physically accepts only `synthetic_only`; its direct DB key plus DPAPI does not prove independent recovery. Personal admission must satisfy Constitution C-10–C-14/C-20, master-spec migration/recovery/deletion/export rules, ADR-008/009/010/022/023, and the exact E11 profile. Imported data, providers/network, diagnosis/scoring, longitudinal activity, professional handoff and blobs remain outside the profile.

## Selected Personal v1 scope

Allowed: unlock/lock; Quick Capture to an explicit user save; Reflection sessions/USER turns; bounded local search; session-scoped Guided Exploration and Working Formulation as revisable proposals; action/outcome; correction/history; deletion; encrypted backup/recovery/export; restart persistence. Excluded: Review Hub, Return, Follow-up, cross-session longitudinal workflow, Longitudinal/N-of-1, AI Lab/provider/network, import/rendering, assessment/scoring, professional handoff, arbitrary attachment/blob writes. The manual Evidence Notebook is **DEFERRED**: existing canonical schema has evidence types, but admitting Personal notebook writes needs a separate explicit data-mode/trust/lifecycle decision and must not delay Reflection.

The byte inventory is [PERSONAL_DATA_BYTE_MAP.md](PERSONAL_DATA_BYTE_MAP.md). Sensitive bytes are canonical encrypted store or interaction workspace; derived UI/search values do not persist. Unknown or uncovered bytes are admission blockers.

## Chosen designs

V10 is `PMV1-V10-REFLECTION-DATA-MODE-REBUILD`, a transactionally rebuilt common `reflection_sessions` table with exact two-value check constraint; it preserves all V9 synthetic rows and requires verified backup/export, recognized inventory/checksum, integrity/FK checks, capacity and exclusive writer. See [MIGRATION_V10_DESIGN.md](MIGRATION_V10_DESIGN.md). Separate personal tables and separate database/schema paths were rejected for duplicated deletion/inventory and compatibility risk.

Key design is `PMV1-VMK-RECOVERY-ENVELOPE-V1`: CSPRNG VMK, DPAPI convenience wrap, Argon2id RecoveryWrapper, and existing domain-separated KDF for DB/backup/export. Bootstrap is Python-owned ACL-scoped metadata; renderer never sees keys. Exact salt compatibility and bootstrap format are review-critical. See [PERSONAL_KEY_RECOVERY_DESIGN.md](PERSONAL_KEY_RECOVERY_DESIGN.md).

Backup enumerates V10 rather than legacy V1 inventory, restores only into isolated staging and activates atomically after verification. Export is encrypted/local/owner-controlled. Deletion closes session and canonical dependencies, rebuilds projections, and declares backup expiry/external-copy limits. See [LIFECYCLE_DESIGN.md](LIFECYCLE_DESIGN.md).

Requested profile is not authority: Rust and typed Python calculate/enforce an effective profile; renderer is untrusted. Denial exists at command, dispatcher, package and artifact boundaries. See [RUNTIME_PROFILE_PACKAGE_ISOLATION.md](RUNTIME_PROFILE_PACKAGE_ISOLATION.md).

## Gate and review strategy

RDG-01 through RDG-12 are candidate-bound synthetic proofs in [RDG_PROOF_MAP.md](RDG_PROOF_MAP.md). Required independent review covers crypto/key/recovery, backup/restore, privacy/deletion and desktop/IPC; qualified review covers intended-use, privacy, legal/regulatory, safety and applicable rights/scientific issues. Seal only after exact source/build/profile proof and clean reviews; only the human repository owner can attest OPEN. See [HUMAN_GATE_PLAN.md](HUMAN_GATE_PLAN.md).

## Self-falsification and residual risks

| Counterexample | Expected safe state / future proof |
|---|---|
| V9 synthetic DB or second V10 run | unchanged synthetic semantics; fixture + idempotency test |
| migration crash, integrity/pending deletion, disk full | pre-V10 valid DB; preflight/fault tests |
| lost DPAPI; wrong/corrupt recovery envelope | fail closed or independently recover/re-wrap; negative lifecycle tests |
| corrupt backup/restore interruption | active vault unchanged; isolated restore tests |
| closed gate or forged renderer profile/AI/import/longitudinal request | denial before write/transport; backend and package tests |
| deletion search/projection/export/old backup residue | no active/query copy; backup expiry explicitly reported and tested |
| evidence/review/attestation mismatches or later code change | evaluator rejects/must create successor; schema/evaluator tests |

Residual risks include endpoint malware, coercion, screen/clipboard exposure, forgotten recovery material, filesystem remnants, old exported/backup copies until expiry, and future cryptographic/platform defects. None is hidden or cured by an OPEN decision.

## Handoff and approvals

Expected work surfaces are in [IMPLEMENTATION_IMPACT.md](IMPLEMENTATION_IMPACT.md); the next-run contract is [.ai-dev/contracts/personal-mode-v1-implementation.DRAFT.yaml](../../../.ai-dev/contracts/personal-mode-v1-implementation.DRAFT.yaml). It is **DRAFT, NOT AUTHORIZED FOR IMPLEMENTATION**. Required owner text after independent review:

> I explicitly approve V10 migration PMV1-V10-REFLECTION-DATA-MODE-REBUILD as described in docs/development/personal-mode-v1/ARCHITECTURE.md, with no destructive migration, no crypto-algorithm change and no REAL_DATA_GATE opening.

> I explicitly approve Personal VMK/recovery integration PMV1-VMK-RECOVERY-ENVELOPE-V1 as described in docs/development/personal-mode-v1/ARCHITECTURE.md, with no destructive migration, no crypto-algorithm change and no REAL_DATA_GATE opening.
