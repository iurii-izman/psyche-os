import { invoke } from "@tauri-apps/api/core";

export interface PersonalStatus { data_mode: "LOCAL_PERSONAL"; real_data_gate: "CLOSED"; local_personal: "NOT_ADMITTED" | "ADMISSION_AVAILABLE" | "ADMITTED"; locked: boolean; }
export interface ReflectionSession { session_id: string; title: string; state: "ACTIVE" | "CLOSED"; turn_count: number; }
let sessionToken: string | null = null;
const call = <T>(command: string, args: Record<string, unknown> = {}) => invoke<T>(command, { request: { ...args, sessionToken } });

export const personalApi = {
  status: () => invoke<PersonalStatus>("desktop_status"),
  async unlock(secret: string) { const value = await invoke<{ session_token: string }>("desktop_unlock", { request: { secret } }); sessionToken = value.session_token; return value; },
  async lock() { const value = await call<Record<string, unknown>>("desktop_lock"); sessionToken = null; return value; },
  reflectionCreate: (title: string) => call<ReflectionSession>("desktop_reflection_create", { title }),
  reflectionList: () => call<{ sessions: ReflectionSession[] }>("desktop_reflection_list"),
  reflectionGet: (sessionId: string) => call<ReflectionSession>("desktop_reflection_get", { sessionId }),
  reflectionAddTurn: (sessionId: string, content: string) => call("desktop_reflection_add_turn", { sessionId, content }),
  reflectionClose: (sessionId: string) => call("desktop_reflection_close", { sessionId }),
  reflectionDelete: (sessionId: string) => call("desktop_reflection_delete", { sessionId, confirmation: "DELETE REFLECTION SESSION" }),
  reflectionSearch: (query: string) => call("desktop_reflection_search", { query, state: "ALL", limit: 20, offset: 0 }),
  explorationStart: (sessionId: string) => call("desktop_exploration_start", { sessionId }),
  explorationGet: (sessionId: string) => call("desktop_exploration_get", { sessionId }),
  explorationAnswer: (questionId: string, answerText: string) => call("desktop_exploration_answer", { questionId, answerText }),
  explorationSkip: (questionId: string) => call("desktop_exploration_skip", { questionId }),
  formulationPropose: (sessionId: string) => call("desktop_formulation_propose", { sessionId }),
  formulationCorrect: (formulationId: string, correctionText: string) => call("desktop_formulation_correct", { formulationId, correctionText }),
  formulationAccept: (formulationId: string) => call("desktop_formulation_accept", { formulationId }),
  formulationReject: (formulationId: string) => call("desktop_formulation_reject", { formulationId }),
  personalBackup: (secret: string) => call("desktop_personal_backup", { secret }),
  personalRestoreIsolated: (backupId: string, secret: string) => call("desktop_personal_restore_isolated", { backupId, secret }),
  personalExportOwner: (secret: string) => call("desktop_personal_export_owner", { secret }),
  personalRotate: (secret: string) => call("desktop_personal_rotate", { secret }),
  personalRecoveryStatus: () => call("desktop_personal_recovery_status")
};
