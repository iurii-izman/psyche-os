# Bounded implementation impact (not authorization)

| Workstream | Exact expected surfaces |
|---|---|
| V10 | `src/psyche_os/storage/migrations.py`, new `personal_mode_v10_schema.py`, reflection schema tests |
| Personal roots/envelope | new focused `src/psyche_os/personal_mode/` package, storage connection factory, envelope/recovery tests |
| backup/export | `src/psyche_os/backup_export/operations.py`, `versioned.py`, focused lifecycle tests |
| profile/admission | `src/psyche_os/application/desktop_service.py`, `interfaces/desktop_sidecar.py`, `release_evidence/e11_gate.py`, `desktop/src-tauri/src/**` |
| package | `scripts/build_desktop_sidecar.py`, desktop packaging config, package inventory test |
| Personal UI | only profile capability/status and allowed routes under `desktop/src/**` |

No production path is authorized until a separately ACTIVE contract exists after independent review and owner approval.
