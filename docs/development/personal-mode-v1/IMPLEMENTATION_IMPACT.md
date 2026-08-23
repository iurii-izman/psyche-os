# Implementation impact map (not authorization)

| Workstream | Expected surfaces / tests |
|---|---|
| Migration | new `src/psyche_os/storage/personal_mode_v10_schema.py`; `schema.py`; `migrations.py`; V9 fixture and failure/idempotency tests |
| Key lifecycle | a small Python-owned Personal bootstrap/lifecycle module; reuse `crypto/envelope.py` without algorithm edits; recovery/DPAPI negative tests |
| Reflection | `application/reflection_sessions.py`, storage connection/admission, exploration/action query filtering and deletion/search tests |
| Backup/restore/export | `backup_export/operations.py`, `versioned.py`, schemas/tests to enumerate exact V10 inventory and isolated activation |
| Runtime profile | `application/runtime_profile.py` (new if necessary), `desktop_service.py`, `interfaces/desktop_sidecar.py`, Rust commands and renderer capability UI |
| Packaging | `scripts/build_desktop_sidecar.py`, Tauri/PyInstaller configuration, artifact inventory/SBOM/provenance checks |
| Gate evidence | `release_evidence/**`, `schemas/e11/**`, `scripts/dev/**` only if a frozen contract requires it |
| Tests | schema, migration fault injection, key/recovery, backup/restore/export/delete, IPC/profile/exclusion, sentinel leak, package, and synthetic E11 acceptance |

All listed production paths remain protected until the owner explicitly approves the selected V10 and key-recovery designs after independent architecture review.
