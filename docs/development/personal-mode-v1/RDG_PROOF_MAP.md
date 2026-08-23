# RDG proof map for Personal Mode v1

All evidence is synthetic, current, exact-candidate/build/profile bound, and expires. A failed applicable proof blocks opening.

| RDG | Deterministic proof | Required review |
|---|---|---|
| 01 | separate root, SQLCipher/WAL wrong-key rejection, `data_mode` enforcement | `independent_crypto_key_recovery`, `independent_privacy_deletion` |
| 02 | separate proofs: independent recovery; N→N+1 active rotation; faulted/interrupted rotation restart; N backup restore after rotation; retained-key destruction only after expiry | `independent_crypto_key_recovery`, `independent_recovery` |
| 03 | bundle+secret isolated restore, N and N+1 restore, no active-N+1 corruption, bootstrap tamper/swap rejection | `independent_recovery`, `independent_privacy_deletion` |
| 04–07 | deletion/projection/backup expiry, migration/export, plaintext scan, root/provider isolation | exact classes in profile |
| 08–12 | package exclusion, provenance/secret gates, independent security, always-applicable RDG-11, synthetic usability/fault suite | exact classes in profile |

RDG-02 fault matrix injects after pending envelope, journal publication, during encrypted export, after candidate DB, before/after candidate verification, before/after active-envelope promotion, and before journal cleanup. After every restart it asserts the expected N/N+1 database/key state, exactly readable synthetic rows, absence of data loss, and no retained-key active write. It additionally tests corrupt/missing journal/envelopes, both/neither key opening, stale journal, DPAPI loss, wrong recovery secret, disk-full, file-lock activation, retention expiry, and attempted premature destruction. RDG-03 proves backup N → active N+1 → isolated restore N and independently restores N+1.
