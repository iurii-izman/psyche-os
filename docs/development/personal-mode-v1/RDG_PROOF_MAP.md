# RDG proof map for physically isolated Personal v1

Every proof is synthetic, exact-candidate/build/profile bound, and current. A failed applicable proof blocks opening.

| RDG | Required deterministic proof | Required review |
|---|---|---|
| 01 | Personal root is physically separate; SQLCipher DB/WAL cannot open without key; `data_mode` enforced. | independent crypto/key, privacy/deletion |
| 02 | Bounded crash-safe rotation plus DPAPI-loss independent recovery; non-circular bootstrap. | independent crypto/key/recovery |
| 03 | Only bundle + recovery secret restores through isolated staging; wrong/swap header/payload fails. | independent recovery, privacy/deletion |
| 04 | Personal-only cascade/delete/search/export absence and declared backup expiry. | independent privacy/deletion |
| 05 | 0→10 and V9→10 generalized rebuild, preconditions/faults/idempotency; V10 export round trip. | independent privacy/deletion, recovery |
| 06 | Sentinel scan DB/WAL/SHM/staging/logs/package/export and outer bootstrap proves no plaintext Personal content/key. | desktop/IPC, privacy/deletion |
| 07 | Synthetic process cannot open Personal root; Personal has no provider credential, adapter or transport. | technical security, qualified privacy/safety |
| 08 | Personal package modulegraph/command/artifact inventory excludes importer/parser/render. | technical security, independent import/parser |
| 09 | lock/SBOM/license/provenance/hashes/secret scan. | independent technical |
| 10 | exact SHA/build/profile independent review resolves all Critical/High. | crypto, recovery, privacy/deletion, desktop/IPC |
| 11 | exact qualified human packets below, always applicable. | human reviewers |
| 12 | CLOSED Personal request creates no Personal directory/DB/envelope; OPEN synthetic acceptance/recovery/delete/export faults. | usability and owner decision |

Self-falsification includes: unfiltered Synthetic `session.list` has no Personal DB; forgotten Personal AI/action commands absent/denied; recovery-only-new-device succeeds; another-vault and mixed bootstrap/payload fail; the old V9 rename cascades descendants while selected procedure preserves them; Personal CLOSED writes nothing; Synthetic cannot locate Personal after records exist; expired attestation locks on next privileged operation.
