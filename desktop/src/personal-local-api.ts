import { invoke } from "@tauri-apps/api/core";
import type {
  ExplorationView,
  PersonalStatus,
  ReflectionSession,
  ReflectionTurn,
  SearchContent,
  SearchPeriod,
  FormulationStatusFilter,
  SearchView,
  SleepEpisode,
  SleepSourceStatus,
} from "./personal-api";

let sessionToken: string | null = null;
const call = <T>(command: string, args: Record<string, unknown> = {}) =>
  invoke<T>(command, { request: { ...args, sessionToken } });

/** Local-only API surface. It deliberately has no provider command names. */
export const personalLocalApi = {
  status: () => invoke<PersonalStatus>("desktop_status"),
  async unlock(secret: string) {
    const value = await invoke<{ session_token: string }>("desktop_unlock", { request: { secret } });
    sessionToken = value.session_token;
    return value;
  },
  async lock() {
    const value = await call<Record<string, unknown>>("desktop_lock");
    sessionToken = null;
    return value;
  },
  reflectionCreate: (title: string) => call<ReflectionSession>("desktop_reflection_create", { title }),
  reflectionList: () => call<{ sessions: ReflectionSession[] }>("desktop_reflection_list"),
  reflectionGet: (sessionId: string) => call<ReflectionSession>("desktop_reflection_get", { sessionId }),
  reflectionAddTurn: (sessionId: string, content: string) => call<ReflectionTurn>("desktop_reflection_add_turn", { sessionId, content }),
  reflectionClose: (sessionId: string) => call("desktop_reflection_close", { sessionId }),
  reflectionDelete: (sessionId: string) => call("desktop_reflection_delete", { sessionId, confirmation: "DELETE REFLECTION SESSION" }),
  reflectionSearch: (query: string, filters: { state: "ALL" | "ACTIVE" | "CLOSED"; content: SearchContent; period: SearchPeriod; formulationStatus: FormulationStatusFilter }, limit = 20, offset = 0) =>
    call<SearchView>("desktop_reflection_search", { query, state: filters.state, content: filters.content, period: filters.period, formulationStatus: filters.formulationStatus, limit, offset }),
  explorationStart: (sessionId: string) => call<ExplorationView>("desktop_exploration_start", { sessionId }),
  explorationGet: (sessionId: string) => call<ExplorationView>("desktop_exploration_get", { sessionId }),
  explorationAnswer: (questionId: string, answerText: string) => call<ExplorationView>("desktop_exploration_answer", { questionId, answerText }),
  explorationSkip: (questionId: string) => call<ExplorationView>("desktop_exploration_skip", { questionId }),
  formulationPropose: (sessionId: string) => call("desktop_formulation_propose", { sessionId }),
  formulationCorrect: (formulationId: string, correctionText: string) => call("desktop_formulation_correct", { formulationId, correctionText }),
  formulationAccept: (formulationId: string) => call("desktop_formulation_accept", { formulationId }),
  formulationReject: (formulationId: string) => call("desktop_formulation_reject", { formulationId }),
  personalBackup: (secret: string) => call("desktop_personal_backup", { secret }),
  personalRestoreIsolated: (backupId: string, secret: string) => call("desktop_personal_restore_isolated", { backupId, secret }),
  personalExportOwner: (secret: string) => call("desktop_personal_export_owner", { secret }),
  personalRotate: (secret: string) => call("desktop_personal_rotate", { secret }),
  personalRecoveryStatus: () => call("desktop_personal_recovery_status"),
  sleepSourceStatus: () => call<SleepSourceStatus>("desktop_sleep_source_status"),
  sleepConfigureInbox: (inboxPath: string) => call<SleepSourceStatus>("desktop_sleep_configure_inbox", { inboxPath }),
  sleepScan: () => call<{ records: number; versions: number }>("desktop_sleep_scan"),
  sleepHistory: (days = 14) => call<{ episodes: SleepEpisode[] }>("desktop_sleep_history", { days }),
  sleepDeleteRecord: (externalRecordId: string) => call<{ deleted: boolean }>("desktop_sleep_delete_record", { externalRecordId }),
};
