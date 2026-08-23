# Backup, restore, export, and deletion design

Status: **PROPOSED_FOR_INDEPENDENT_REVIEW.**

## Backup and restore

The V10 backup inventory must be derived from the exact V10 schema—not the legacy V1 `_REQUIRED_BACKUP_TABLES`. It includes `schema_migrations`, `vault_config`, all canonical/version/deletion/manifest tables, all `reflection_*` V6–V9 tables, and bootstrap metadata. Backup holds active and historical rows needed for correction/deletion interpretation, is snapshot-consistent (`BEGIN IMMEDIATE`), encrypted/authenticated with `Kbackup`, and binds vault ID, schema version, inventory, sequence, key-wrap version, deletion-state digest and manifest in AAD. No key is embedded in the package.

Restore verifies package/AAD/inventory/counts/checksums, recovery/key access, and migration evidence into a newly created private staging directory and a non-active DB path. It runs integrity/foreign-key/search-rebuild checks and a reopen before atomic activation. A failure before activation removes or quarantines only staging output and preserves the active vault. Corrupt backup, wrong key, disk full, and interrupted restore leave the active vault unchanged.

## Export

Personal export is a user-initiated local, encrypted, versioned JSONL + schemas + manifest/checksums + human-readable explanation, using `Kexport`, with explicit audience/purpose and a content-free disclosure receipt. It includes every selected V10 Reflection/canonical/deletion record required to retain meaning, rather than silently dropping workspace tables. Plaintext exports, professional/audience-specific handoff and third-party disclosure are excluded from Personal v1. A verified export is required before V9→V10 migration; its external copy cannot be recalled.

## Deletion closure

Deletion begins with a dry-run root/scope count. For a Reflection session, cascade removes turns, exploration, snapshots, context anchors/refs, questions, formulations/history, action plans/outcomes and any local search projection. For canonical records it retains existing lineage rules: delete exclusive descendants, invalidate mixed descendants, rebuild projections, and record only a non-reconstructive receipt. Afterwards test canonical/session queries, raw SQL scan, rebuilt search and a new export for absence. Existing encrypted backups may still contain deleted data until their declared expiry; the receipt states that limitation, schedules expiry/key retirement, and never claims SSD overwrite or deletion of prior exports.
