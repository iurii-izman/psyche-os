# Personal lifecycle: backup, restore, export, deletion

Personal backup reads only `%LOCALAPPDATA%\\PSYCHE OS\\Personal\\vault.sqlite` and its WAL/SHM, V10 inventory, Personal bootstrap and Personal manifests; it never enumerates the Synthetic root, AI fixtures, credentials, or unrelated state. Its encrypted payload uses `Kbackup`; outer bootstrap is as specified in [PERSONAL_KEY_RECOVERY_DESIGN.md](PERSONAL_KEY_RECOVERY_DESIGN.md). A Synthetic backup has the inverse root boundary.

Restore accepts only a Personal bundle into `%LOCALAPPDATA%\\PSYCHE OS\\Personal\\staging\\<random>` with private ACL. It performs outer bounds/VMK/payload binding verification, decrypts, opens with derived DB key, verifies inventory/schema, `integrity_check`, `foreign_key_check`, semantic `real_personal` values, search rebuild and reopen. Only then, with explicit activation, does an atomic no-replace swap publish the store and new DPAPI wrap. Failure quarantines/removes staging and leaves active Personal store unchanged.

Personal export is encrypted, local and backend-enforced `audience=OWNER_ONLY`; no reviewer/professional/third-party value is accepted. It uses `Kexport`, includes selected Personal V10 meaning-preserving rows and a content-free receipt, and does not include Synthetic bytes. Previous exports/backup copies have the explicit expiry limitation.

Deletion receives a session ID only from the active profile service. Personal deletion runs only in Personal root and cascades its session turns/exploration/formulations/history/search values; Synthetic deletion runs only in Synthetic root. No projection contains both roots. Post-delete raw Personal DB queries, search, and a new Personal export must not return content; encrypted old backup expiry remains disclosed.
