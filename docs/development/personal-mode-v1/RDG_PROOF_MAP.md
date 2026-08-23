# RDG-01…RDG-12 proof map

Every row is candidate/build/profile-bound synthetic evidence. `NOT_APPLICABLE_EXCLUDED` is allowed only when the complete control predicate is proven unreachable; RDG-09–12 always apply.

| RDG | Machine proof | Independent/qualified requirement |
|---|---|---|
| 01 encryption | SQLCipher/open-without-key denial; encrypted DB/WAL inventory; V10 bootstrap and no blob-write reachability | crypto/key recovery and privacy/deletion review |
| 02 recovery | DPAPI loss, wrong/corrupt recovery secret/header, recovery rewrap, key-state/rotation tests | independent crypto/key/recovery review |
| 03 backup/restore | authenticated encrypted package; corrupt/wrong-key denial; clean isolated restore and no activation on fault | independent recovery and privacy/deletion review |
| 04 deletion | session/canonical lineage closure, projection rebuild, search/export absence and backup-expiry lifecycle | independent privacy/deletion review |
| 05 migration/export | V9→V10 fixture, checksums/precondition denials, faults/idempotency, open export round trip | independent privacy/deletion and recovery review |
| 06 leaks | synthetic sentinel scan of DB/WAL/SHM/staging/logs/sidecar/backups/exports/projections/package; content-free errors | desktop/IPC and privacy/deletion review |
| 07 NEVER_CLOUD | provider construction, credentials, transport, telemetry and sync all unreachable under Personal process tests | technical security plus qualified privacy/safety review |
| 08 package boundaries | exact Personal installer/sidecar command/module inventory proves importer/parser/render path absent/unreachable | independent technical security and import/parser class as required by profile |
| 09 supply chain | lock, SBOM, license, provenance, reproducibility, executable/sidecar/installer hash, secret scan | independent technical review |
| 10 technical reviews | review artifacts bind candidate SHA/build/profile and resolve all Critical/High | independent crypto, recovery, privacy/deletion, desktop/IPC reviewers |
| 11 human review | intended-use/privacy/legal/regulatory packet and qualified review, no boundary N/A | qualified privacy, safety, legal/regulatory and rights/scientific reviewers required by profile |
| 12 field acceptance | synthetic TEST-admission setup/create/restart/search/correct/backup/restore/recover/delete/export/fault flows plus CLOSED denial/exclusion tests | usability/qualified human review and owner decision |

Failure of any load-bearing proof blocks opening; a coding-model review is pre-review only and cannot satisfy RDG-10 or RDG-11.
