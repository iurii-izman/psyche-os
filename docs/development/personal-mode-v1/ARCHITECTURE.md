# Personal Mode v1 admission architecture

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW**. Architecture candidate base: `166832da18d913f591c3956346e41b7b5e742a5a`. `REAL_DATA_GATE` remains **CLOSED**. This is a selected design, not implementation authority.

## Selected topology and invariant

There is one repository-owned V10 schema and one Python service implementation, instantiated in physically separate roots:

| Profile | Owned root and database | Other owned locations |
|---|---|---|
| `SYNTHETIC_LAB` | Existing accepted Synthetic workspace and its existing database path remain supported without movement. | Its existing sibling staging, backup and export locations remain Synthetic-only. |
| `LOCAL_PERSONAL` | `%LOCALAPPDATA%\\PSYCHE OS\\Personal\\vault.sqlite` | `%LOCALAPPDATA%\\PSYCHE OS\\Personal\\key-envelope.pmv1.json`; `staging\\`; `backups\\`; `exports\\` beneath that same Personal root. |

The Personal root is new, fixed by trusted Rust/Python code, private to the current Windows user, and has never contained Synthetic data. The renderer supplies none of these paths. A Synthetic process is constructed without a Personal-root path and must not open, enumerate, or fall back to it; a Personal process is constructed without the Synthetic workspace path. `data_mode` remains a row-integrity invariant, not the isolation boundary.

## Personal v1 scope

Allowed only after a legitimate Personal admission: unlock/lock; explicit-save Quick Capture; Reflection sessions and USER turns; local bounded search; session-scoped Guided Exploration and Working Formulation as revisable proposals; correction/history; session deletion; encrypted backup, independent recovery, owner-only encrypted export; and restart persistence.

Excluded: provider/model/network/telemetry/sync; Action Planning and Outcomes; Longitudinal/N-of-1 and intervention workflows; Review Hub, Return and Follow-up; import/parser/untrusted rendering; assessments; professional/external handoff; arbitrary blobs/attachments; Evidence Notebook. A Personal action command is absent/denied at the Rust allowlist and Python dispatcher. Existing Synthetic behavior, including actions, remains unchanged.

## V10 and migration policy

V10 adds `synthetic_only | real_personal` to `reflection_sessions`. A newly admitted Personal vault is created directly at V10 and writes `real_personal` solely from the effective admitted Personal profile. Existing Synthetic V9 workspaces can remain V9; their conversion is not a Personal-admission prerequisite. The 0→10 and V9→10 chains remain supported, but V10 never changes an existing `synthetic_only` row and roots never merge automatically. The rejected and selected procedures, exact probes, and Migrator ownership change are in [MIGRATION_V10_DESIGN.md](MIGRATION_V10_DESIGN.md).

## Keys, recovery, backup and export

`PMV1-KEY-ENVELOPE-V1` uses existing `RecoveryWrapper`, `OSKeyWrapper`, and `derive_domain_key` unchanged. It specifies the Personal envelope and a portable outer recovery bootstrap; the recovery package plus recovery secret suffices on a different Windows profile. See [PERSONAL_KEY_RECOVERY_DESIGN.md](PERSONAL_KEY_RECOVERY_DESIGN.md). Backup is Personal-root-only and includes only Personal V10 store, Personal bootstrap and Personal manifests; Synthetic backup never contains Personal bytes. Export is encrypted and `OWNER_ONLY` enforced in the backend. Restore decrypts into Personal staging, verifies before activation, and never mutates an active vault. [LIFECYCLE_DESIGN.md](LIFECYCLE_DESIGN.md) defines this lifecycle.

## Admission and runtime gate

Personal v1 is deliberately repository-bound. The trusted launch context supplies a fixed build-time repository root; Rust passes it to an admission-only sidecar, never the renderer. That root contains `docs/architecture/REAL_DATA_GATE.yaml`, `docs/architecture/REAL_DATA_GATE_PROFILE.yaml`, `artifacts/e11/gate-evaluations/<evaluation-id>.yaml`, `artifacts/e11/human-attestations/<evaluation-id>.yaml`, and the source/build identity required by `evaluate_evaluation()`. The selected sealed evaluation must bind the exact profile bytes, source commit, build identity, platform, evidence and current owner attestation. Missing/moved/tampered evidence, digest mismatch, expiry or a non-OPEN result is CLOSED.

Startup states are `REQUESTED_SYNTHETIC → SYNTHETIC_ACTIVE`, or `REQUESTED_PERSONAL → PERSONAL_ADMISSION_CHECKING → PERSONAL_NOT_ADMITTED | PERSONAL_ADMITTED → PERSONAL_ACTIVE`. The admission-only process initializes no Reflection service, archive, provider, Personal DB, key envelope, directory, or credential. CLOSED returns only a content-free `NOT_ADMITTED` capability/status DTO and has no Synthetic fallback. OPEN selects the fixed Personal root, publishes/verifies the key envelope, opens the V10 Personal store, then initializes only allowed services. Personal never receives `OPENAI_API_KEY`; only Synthetic may receive it when configured.

Attestation expiry while stopped closes the next Personal startup. While unlocked, expiry closes the session at the next privileged operation (write, search, backup, export, delete, or unlock renewal); it locks and returns `NOT_ADMITTED`, avoiding continued privileged use under an expired decision.

## Evidence and review

[PERSONAL_DATA_BYTE_MAP.md](PERSONAL_DATA_BYTE_MAP.md), [RUNTIME_PROFILE_PACKAGE_ISOLATION.md](RUNTIME_PROFILE_PACKAGE_ISOLATION.md), and [RDG_PROOF_MAP.md](RDG_PROOF_MAP.md) are load-bearing. The current authority requires rotation before initial opening: `REAL_DATA_GATE.yaml` RDG-02 says `key_rotation_and_independent_recovery_verified`, and the master spec requires versioned generation/rotation/retirement/destruction. The bounded rotation design is in the key document.

All required review classes are listed in [HUMAN_GATE_PLAN.md](HUMAN_GATE_PLAN.md). No coding-model output satisfies them. The implementation contract remains DRAFT and unauthorized.

## Approval text after independent review

> I explicitly approve V10 migration PMV1-V10-SQLITE-GENERALIZED-REBUILD as described in docs/development/personal-mode-v1/ARCHITECTURE.md, with foreign_keys disabled only outside the migration transaction, no destructive migration, no crypto-algorithm change and no REAL_DATA_GATE opening.

> I explicitly approve Personal key-envelope, bootstrap recovery, and bounded key rotation PMV1-KEY-ENVELOPE-V1 as described in docs/development/personal-mode-v1/ARCHITECTURE.md, with no crypto-algorithm change and no REAL_DATA_GATE opening.
