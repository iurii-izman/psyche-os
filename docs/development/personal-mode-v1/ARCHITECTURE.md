# Personal Mode v1 admission architecture

Status: **ACCEPTED**. Accepted architecture candidate: `79bf063902ab4c1106fdfb420edcf905dfa42f43`. Architecture merge: `e8bfb83211fb424d09fa9a272066d5c6232cc0dd`. Independent review verdict: **ACCEPT**. Accepted/recorded: 2026-08-24. Implementation authorization: [IMPLEMENTATION_AUTHORIZATION.md](IMPLEMENTATION_AUTHORIZATION.md). `REAL_DATA_GATE` remains **CLOSED** and `LOCAL_PERSONAL` remains **NOT_ADMITTED**.

`SYNTHETIC_LAB` owns only the existing Synthetic root. `LOCAL_PERSONAL` owns only `%LOCALAPPDATA%\\PSYCHE OS\\Personal\\vault.sqlite` and fixed siblings for envelopes, rotation staging, backups, and exports. A Synthetic process has no Personal path; a Personal process has no Synthetic path. `data_mode` is an integrity invariant, not the security boundary. V10 supports `synthetic_only` and `real_personal` without changing existing Synthetic rows; its selected generalized rebuild remains `PMV1-V10-SQLITE-GENERALIZED-REBUILD`.

After legitimate OPEN only, Personal permits unlock/lock, explicit Quick Capture, reflection sessions/USER turns, bounded local search, session-scoped exploration, revisable working formulation, correction/history, session deletion, encrypted backup, independent recovery, OWNER_ONLY encrypted export, and restart persistence. Provider/model/network, telemetry/sync, AI Lab, actions/outcomes, longitudinal/intervention, Review/Return/Follow-up, importer/parser/rendering, scoring, professional handoff, blobs/attachments, and Evidence Notebook are excluded and absent/denied in both Rust allowlist and Python dispatcher.

## PERSONAL_ADMISSION_GUARD

`PERSONAL_ADMISSION_GUARD` is the sole authorization boundary before every operation able to read, write, derive, search, export, back up, restore/activate, recover, or delete Personal bytes. It runs before opening the Personal store, envelope, backup payload, staging DB, or returning any Personal content. It covers session create/add/list/get, search, exploration get/writes, formulation reads/writes, history/correction, delete, backup, restore, recovery, export, unlock, and every future Personal privileged command. Content-free status, lock, admission error, build/product information, and explicit Synthetic navigation may run without admission.

At admission the trusted Rust launch context gives an admission-only sidecar the fixed repository root and no vault root. It evaluates the exact SEALED E11 record, its human owner attestation, profile digest, candidate source/build/platform identity, and expiry. It records in memory only evaluation ID/digest, attestation digest, profile digest, candidate/build identity, expiry, and file identity evidence (canonical path, volume/file identifier, length, mtime). It initializes neither Personal directory, DB, envelope, provider nor credential while closed. A closed request returns only content-free `NOT_ADMITTED`, with no Synthetic fallback.

On every guarded operation, the guard first requires current time strictly before expiry and unchanged file identity evidence for gate/profile/evaluation/attestation. Any identity, mtime, length, path, or replacement ambiguity triggers full digest re-evaluation before Personal access. A safely undetectable replacement requires digest revalidation. Expiry or failed re-evaluation locks the session, best-effort clears in-memory Personal key material, returns `NOT_ADMITTED`, and retrieves no new Personal bytes. This includes reads (`session.list`, `session.get`, search, exploration get, formulation/history reads) as well as writes. Previously displayed pixels are not retroactively erased.

Recovery/restore may inspect only bounded, encrypted, content-free package headers before OPEN, solely to report format/eligibility. It must pass the guard before accepting a recovery secret, unwrapping a VMK, decrypting payload, opening a staging DB, or exposing/activating any Personal content. Rotation is Personal-only and guarded. This preserves the rule that plaintext Personal content is never exposed without current OPEN.

Keys, bootstrap, backup, rotation, pending-state handling, and recovery are exactly `PERSONAL_KEY_RECOVERY_DESIGN.md`; lifecycle and byte ownership are its companion documents. Human classes use exact profile machine IDs in `HUMAN_GATE_PLAN.md`. `UNRESOLVED_CRITICAL_ARCHITECTURE_QUESTIONS = 0`.

## Implementation authorization

The exact active `HUMAN_REPOSITORY_OWNER` approvals are recorded in
[IMPLEMENTATION_AUTHORIZATION.md](IMPLEMENTATION_AUTHORIZATION.md). Historical
prompt templates are not themselves authority.
