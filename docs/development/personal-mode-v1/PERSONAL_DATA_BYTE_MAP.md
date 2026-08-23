# Personal byte map

| Durable bytes | Location | Secret/encrypted/ACL | Backup/export/deletion/crash rule | Owner |
|---|---|---|---|---|
| active protected VMK, salts, IDs, recovery header | `key-envelope.pmv1.json` | secret-bearing wraps; ACL; no plaintext VMK | backup bootstrap copy; never export plaintext; atomic replacement/reopen | Personal |
| pending protected N+1 envelope and transition metadata | `rotation-journal.pmv1.json` | AES-GCM under Kmanifest(N), ACL, no plaintext keys | journal is not a backup/export item; parsed at crash and retired only deterministically | Personal |
| retained protected historical envelope | `retained-keys\key-envelope-v<N>.pmv1.json` | secret-bearing wraps, immutable ACL; published/reopened before active N+1 promotion | supports only old backup restore; no active writes | Personal |
| retained lifecycle metadata | `retained-keys\key-v<N>.pmv1.metadata.json` | content-free, AES-GCM authenticated under Kmanifest(N), ACL | `prepared_for_retention` before promotion; `retained_for_read` after actual retirement; destruction receipt after expiry | Personal |
| active/candidate/previous encrypted DB plus WAL/SHM | `vault.sqlite`, `staging\rotation-*` | SQLCipher, private ACL | backup includes validated active store; staging never exports; cleanup after durable state recovery | Personal |
| bootstrap, encrypted payload, manifests | `backups\` | bootstrap is authenticated after recovery unwrap; payload encrypted | retained under recorded key version and expiry | Personal |
| encrypted OWNER_ONLY export | `exports\` | Kexport/current key, ACL | external copies have declared deletion limitation | Personal |
| session/turn/exploration/formulation/history/search | SQLCipher DB | encrypted, no logs/telemetry | backup/export/delete according to lifecycle | Personal |
| logs, crash diagnostics, UI drafts | content-free / memory only | no Personal content or keys | no backup/export; discard on lock/crash | process memory |
| actions, archive, AI, imports, attachments, scoring, longitudinal, handoff | none | command/package denied | none | none |

No durable Personal bytes may be added without a row defining encryption, ACL, owner, backup/export/deletion, and crash-remnant behavior.
