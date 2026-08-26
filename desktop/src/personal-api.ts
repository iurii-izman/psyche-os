import { invoke } from "@tauri-apps/api/core";

export interface PersonalStatus {
  build_id?: string | null;
  runtime_profile: "LOCAL_PERSONAL" | "LOCAL_PERSONAL_BOUNDED_OPENAI";
  local_personal: "NOT_ADMITTED" | "ADMISSION_AVAILABLE" | "ADMITTED";
  real_data_gate: "CLOSED" | "OPEN";
  admission_expires_at?: string | null;
  locked: boolean;
  setup_required?: boolean;
  inbound_listener: "NONE";
  outbound_provider: "NOT_CONFIGURED" | "OPENAI_EXPLICIT_OPT_IN";
  network: "OFFLINE_NO_LISTENER" | "OPENAI_EXPLICIT_ONE_CALL_ONLY";
  privacy: { core_processing_location: "LOCAL"; cloud_storage: "DISABLED"; cloud_disclosure: "NEVER_CLOUD" | "EXPLICIT_OPT_IN_OPENAI_ONLY"; telemetry: "OFF" };
}
export interface ReflectionTurn { turn_id: string; session_id: string; sequence: number; actor: "USER"; created_at: string; content: string; }
export interface ReflectionSession { session_id: string; title: string; state: "ACTIVE" | "CLOSED"; turn_count: number; created_at?: string; updated_at?: string; closed_at?: string | null; turns?: ReflectionTurn[]; }
export interface SearchResult { session_id: string; session_title: string; session_state: "ACTIVE" | "CLOSED"; turn_id: string | null; turn_sequence: number | null; excerpt: string; }
export interface SearchView { query: string; state: "ALL" | "ACTIVE" | "CLOSED"; total_matches: number; returned_count: number; offset: number; limit: number; truncated: boolean; has_more: boolean; results: SearchResult[]; }
export interface ExplorationView {
  context: { context_item_id: string; kind: "KNOWN" | "UNKNOWN" | "CONTRADICTION"; text: string; state: string; source_turn_ids?: string[]; created_at?: string }[];
  hypotheses: { hypothesis_id: string; proposal_text: string; uncertainty_text: string; discriminator_text: string; context_refs?: { context_item_id: string; relation: string; source_turn_ids: string[] }[]; created_at?: string }[];
  next_question: { question_id: string; text: string } | null;
  snapshots: unknown[];
  formulations: { formulation_id: string; version: number; status: "PROPOSED" | "CURRENT" | "REJECTED" | "SUPERSEDED"; summary: string; correction_text: string | null; supporting_turn_ids?: string[]; ai_provenance?: { origin: "AI"; provider: string; actual_model: string }; created_at?: string; updated_at?: string }[];
}

let sessionToken: string | null = null;
const call = <T>(command: string, args: Record<string, unknown> = {}) => invoke<T>(command, { request: { ...args, sessionToken } });

export const personalApi = {
  status: () => invoke<PersonalStatus>("desktop_status"),
  async unlock(secret: string) { const value = await invoke<{ session_token: string }>("desktop_unlock", { request: { secret } }); sessionToken = value.session_token; return value; },
  async lock() { const value = await call<Record<string, unknown>>("desktop_lock"); sessionToken = null; return value; },
  reflectionCreate: (title: string) => call<ReflectionSession>("desktop_reflection_create", { title }),
  reflectionList: () => call<{ sessions: ReflectionSession[] }>("desktop_reflection_list"),
  reflectionGet: (sessionId: string) => call<ReflectionSession>("desktop_reflection_get", { sessionId }),
  reflectionAddTurn: (sessionId: string, content: string) => call<ReflectionTurn>("desktop_reflection_add_turn", { sessionId, content }),
  reflectionClose: (sessionId: string) => call("desktop_reflection_close", { sessionId }),
  reflectionDelete: (sessionId: string) => call("desktop_reflection_delete", { sessionId, confirmation: "DELETE REFLECTION SESSION" }),
  reflectionSearch: (query: string, state: "ALL" | "ACTIVE" | "CLOSED", limit = 20, offset = 0) => call<SearchView>("desktop_reflection_search", { query, state, limit, offset }),
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
  personalRecoveryStatus: () => call("desktop_personal_recovery_status")
  ,aiProviderStatus: () => call<{ provider: "OpenAI"; configured: boolean; model: string; config_id: string }>("desktop_ai_provider_status")
  ,aiProviderConfigure: (apiKey: string) => call("desktop_ai_provider_configure", { apiKey })
  ,aiProviderDelete: () => call("desktop_ai_provider_delete")
  ,aiFormulationPrepare: (sessionId: string, selectedTurnIds: string[]) => call<{ interaction_id: string; preview_id: string; turns: { turn_id: string; sequence: number; content: string }[]; expires_at: string }>("desktop_ai_formulation_prepare", { sessionId, selectedTurnIds })
  ,aiFormulationExecute: (interactionId: string, previewId: string) => call("desktop_ai_formulation_execute", { interactionId, previewId })
};
export type PersonalApi = typeof personalApi;
