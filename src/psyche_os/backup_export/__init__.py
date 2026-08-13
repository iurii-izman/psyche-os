"""Backup/restore/export layer — E01 activated (repaired 2026-08-11).

E01 REPAIR: All 7 targets addressed:
  T1: Fail-closed BEGIN IMMEDIATE, ALL rows, BackupPackageStore publication
  T2: restore_backup creates isolated SQLCipher target
  T3: activate_restored_vault performs atomic file-level activation/swap
  T4: Fault injection hooks (4 points) + vault state capture
  T5: Independent Argon2id recovery via recover_and_restore
  T6: Production path uses BackupPackageStore exclusively
  T7: Evidence validator rejects PENDING/BLOCKED/missing
"""

from psyche_os.backup_export.operations import (
    BackupBuilder,
    BackupManifest,
    DeferredFeatureError,
    ExportBuilder,
    ExportManifest,
    HOOK_AFTER_PACKAGE_STAGING,
    HOOK_AFTER_RESTORE_WRITE,
    HOOK_BEFORE_ACTIVATION,
    HOOK_DURING_VALIDATION,
    activate_restored_vault,
    arm_fault_hook,
    capture_semantic_state,
    capture_vault_state,
    clear_fault_hooks,
    recover_and_restore,
    restore_backup,
    verify_backup_file,
    verify_export,
)
from psyche_os.backup_export.package_store import BackupPackageStore

__all__ = [
    "BackupBuilder",
    "BackupManifest",
    "BackupPackageStore",
    "DeferredFeatureError",
    "ExportBuilder",
    "ExportManifest",
    "HOOK_AFTER_PACKAGE_STAGING",
    "HOOK_AFTER_RESTORE_WRITE",
    "HOOK_BEFORE_ACTIVATION",
    "HOOK_DURING_VALIDATION",
    "activate_restored_vault",
    "arm_fault_hook",
    "capture_semantic_state",
    "capture_vault_state",
    "clear_fault_hooks",
    "recover_and_restore",
    "restore_backup",
    "verify_backup_file",
    "verify_export",
]
