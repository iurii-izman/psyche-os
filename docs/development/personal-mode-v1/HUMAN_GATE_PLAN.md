# Human gate plan

Machine identifiers below are exact values from `REAL_DATA_GATE_PROFILE.yaml`; friendly names are not identifiers. Every packet binds candidate SHA, build ID/platform, profile digest, sealed evaluation digest, deterministic evidence, reviewer identity/qualification, findings, and expiry. Critical/High or stale/absent evidence blocks opening. `RDG-11` is always applicable. A coding model is `NON_AUTHORITATIVE_PROPOSAL_ONLY`; only `HUMAN_REPOSITORY_OWNER` may provide the local attestation gate decision.

| Exact review class ID | Trigger and packet | Output |
|---|---|---|
| `independent_crypto_key_recovery` | enabled canonical encrypted store; envelope, rotation, bootstrap, retention and wrong/swap proofs | independent technical review bound to candidate/profile, expiring |
| `independent_privacy_deletion` | enabled canonical store/backup and local projection boundaries | independent privacy/deletion review, expiring |
| `independent_recovery` | enabled backup/restore boundary; bundle-only restore and activation fault packet | independent recovery review, expiring |
| `independent_technical_security` | enabled desktop/typed IPC; command/package/root evidence | independent technical-security review, expiring |
| `independent_import_parser` | excluded importer/parser/render boundary; reachability exclusion proof | independent exclusion review, expiring |
| `qualified_privacy` | excluded provider/network boundary and intended local processing | qualified review, expiring |
| `qualified_safety` | excluded provider/intervention/diagnostic relationship boundary | qualified review, expiring |
| `qualified_rights_scientific_psychometric` | excluded assessment/scoring boundary | qualified review, expiring |
| `qualified_scientific_clinical` | excluded longitudinal/N-of-1/intervention boundary | qualified review, expiring |
| `qualified_legal_privacy_clinical_human_factors` | excluded professional/handoff boundary and OWNER_ONLY export limits | qualified review, expiring |

The E11 evaluator requires boundary-specific review records carrying these exact IDs; the evidence packet/review candidate, build, and platform bindings must match the SEALED evaluation. The owner attestation binds its exact sealed digest and expiry after qualified/independent reviews; it is not a substitute for them.
