# Personal byte map

| Class | Durable Personal location | Boundary/lifecycle | Exposure |
|---|---|---|---|
| VMK wraps, four salts, IDs, recovery header | Personal key envelope and backup outer bootstrap | ACL; no plaintext VMK; RecoveryWrapper then manifest binding | status only |
| Session/turn/exploration/formulation/correction | Personal V10 SQLCipher DB | `real_personal`; backup/recovery/export/delete | typed local IPC while unlocked |
| Search results and Quick Capture draft | memory only until explicit save | regenerated/discarded; no browser storage | bounded IPC only |
| backup/export manifests and packages | Personal backups/exports only | distinct backup/export domain keys; owner-only export | metadata/receipt only |
| WAL/SHM/staging | Personal root private paths | scanned, private, removed/quarantined on failure | never IPC/logged |
| logs/crash/telemetry | content-free diagnostics only | Personal process has no telemetry/provider | no Personal bytes |
| actions/outcomes, archive, AI, imports, attachments, assessment, longitudinal, handoff | none | package/command denied | denial only |

Any additional Personal byte requires an explicit map row with encryption, recovery, backup, export, deletion, projection and exposure semantics.
