# Human review and gate plan

The lifecycle is: exact source candidate → exact build → deterministic evidence → independent technical reviews → qualified reviews → DRAFT evaluation → pre-seal validation → immutable SEALED evaluation → `sealed_evaluation_sha256` → `local_human_attestation_v1` by `HUMAN_REPOSITORY_OWNER` → deterministic `evaluate_evaluation()` → OPEN. There is no code/evidence/profile/build byte change after seal; any change creates a successor evaluation.

Pre-seal requires the source SHA, Windows build and profile digest frozen; current deterministic RDG evidence; reproducibility; every required review bound to that same candidate/build/platform; no unresolved Critical/High; and no expired evidence/review. `schemas/e11/gate_evaluation.schema.json` defines DRAFT/SEALED binding and `schemas/e11/human_attestation.schema.json` requires evaluation ID, exact sealed digest, human owner, decision, date and expiry. An agent must never create a live OPEN attestation.

| Packet / reviewer | Candidate-bound contents and questions | Validity / blocks |
|---|---|---|
| Crypto/key/recovery — independent technical cryptography reviewer | VMK/bootstrap/DPAPI/Argon2id/KDF design, exact diff, negative tests; can loss/corruption expose or permanently lose data? | expires on crypto/key/build change; Critical/High blocks |
| Backup/restore — independent recovery reviewer | inventory, package/AAD, isolated activation, fault evidence; can corrupt/partial restore change active vault? | expires on lifecycle/schema/build change; blocks |
| Privacy/deletion — independent privacy/deletion reviewer | byte map, lineage/backup expiry, sentinel scans, export limitations; do reconstructive copies survive unexpectedly? | expires on data/projection/export change; blocks |
| Desktop/IPC/package — independent security reviewer | allowlists, profile propagation, command/module/artifact inventory; can renderer bypass profile or reach excluded paths? | expires on desktop/package/dependency change; blocks |
| Intended use/privacy/legal/regulatory — qualified human reviewers | profile, intended-use language, exclusions, limitations, jurisdiction assumptions; are claims/communications lawful and non-clinical? | expires on scope/jurisdiction/content change; blocks |

Each packet contains candidate SHA, build ID, profile digest, scoped diff, architecture summary, raw deterministic evidence, falsification questions, residual risks and a finding template (severity, evidence, state, expiry). The repository owner performs the only final gate decision and must choose CLOSED where a review is missing, stale, mismatched, or has unresolved High/Critical findings.
