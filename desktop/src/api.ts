import { invoke } from "@tauri-apps/api/core";

export interface StatusView {
  locked: boolean;
  data_mode: string;
  real_data_gate: string;
  network: string;
  privacy: { processing_location: string; cloud: string; telemetry: string };
}

let sessionToken: string | null = null;

async function call<T>(command: string, args: Record<string, unknown> = {}): Promise<T> {
  return invoke<T>(command, { request: { ...args, sessionToken } });
}

export const desktopApi = {
  status: (): Promise<StatusView> => invoke<StatusView>("desktop_status"),
  async unlock(secret: string): Promise<Record<string, unknown>> {
    const result = await invoke<{ session_token: string }>("desktop_unlock", { request: { secret } });
    sessionToken = result.session_token;
    return result;
  },
  async lock(): Promise<Record<string, unknown>> {
    const result = await call<Record<string, unknown>>("desktop_lock");
    sessionToken = null;
    return result;
  },
  correct: (replacement: string, reason: string): Promise<Record<string, unknown>> =>
    call("desktop_correct", { recordId: "synthetic-observation-1", replacement, reason }),
  planDeletion: (): Promise<Record<string, unknown>> =>
    call("desktop_plan_deletion", { recordId: "synthetic-observation-1" }),
  executeDeletion: (planId: string, confirmation: string): Promise<Record<string, unknown>> =>
    call("desktop_execute_deletion", { planId, confirmation }),
  backupStatus: (): Promise<Record<string, unknown>> => call("desktop_backup_status"),
  verifyBackup: (): Promise<Record<string, unknown>> => call("desktop_verify_backup"),
  validateRecovery: (): Promise<Record<string, unknown>> => call("desktop_validate_recovery"),
  activateRecovery: (candidateId: string, confirmation: string): Promise<Record<string, unknown>> =>
    call("desktop_activate_recovery", { candidateId, confirmation }),
  previewExport: (input: Record<string, unknown>): Promise<Record<string, unknown>> =>
    call("desktop_preview_export", input),
  executeExport: (previewId: string, confirmation: string): Promise<Record<string, unknown>> =>
    call("desktop_execute_export", { previewId, confirmation }),
  archiveOperate: (operation: string, choice: string, idempotencyKey: string): Promise<Record<string, unknown>> =>
    call("desktop_archive_operate", { operation, choice, idempotencyKey }),
  archiveTimeline: (temporalRole: string): Promise<Record<string, unknown>> =>
    call("desktop_archive_timeline", { temporalRole }),
  archiveExplorer: (): Promise<Record<string, unknown>> => call("desktop_archive_explorer"),
  archiveSnapshotDiff: (): Promise<Record<string, unknown>> => call("desktop_archive_snapshot_diff"),
  archiveExecuteDeletion: (planId: string, confirmation: string): Promise<Record<string, unknown>> =>
    call("desktop_archive_execute_deletion", { planId, confirmation })
};

export type DesktopApi = typeof desktopApi;
