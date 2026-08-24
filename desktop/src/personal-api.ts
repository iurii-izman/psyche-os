import { invoke } from "@tauri-apps/api/core";

export interface PersonalStatus { data_mode: "LOCAL_PERSONAL"; real_data_gate: "CLOSED"; local_personal: "NOT_ADMITTED" | "ADMISSION_AVAILABLE" | "ADMITTED"; locked: boolean; }
export interface ReflectionTurn { turn_id: string; session_id: string; sequence: number; actor: "USER"; created_at: string; content: string; }
export interface ReflectionSession { session_id: string; title: string; state: "ACTIVE" | "CLOSED"; turn_count: number; created_at?: string; updated_at?: string; closed_at?: string | null; turns?: ReflectionTurn[]; }
export interface SearchResult { session_id: string; session_title: string; session_state: "ACTIVE" | "CLOSED"; turn_id: string | null; turn_sequence: number | null; excerpt: string; }
export interface SearchView { query: string; state: "ALL" | "ACTIVE" | "CLOSED"; total_matches: number; returned_count: number; offset: number; limit: number; truncated: boolean; has_more: boolean; results: SearchResult[]; }
export interface ExplorationView { context: { context_item_id: string; kind: "KNOWN" | "UNKNOWN" | "CONTRADICTION"; text: string; state: string }[]; hypotheses: { hypothesis_id: string; proposal_text: string; uncertainty_text: string; discriminator_text: string }[]; next_question: { question_id: string; text: string } | null; snapshots: unknown[]; formulations: { formulation_id: string; version: number; status: "PROPOSED" | "CURRENT" | "REJECTED" | "SUPERSEDED"; summary: string; correction_text: string | null }[]; }

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
  formulationReject: (formulationId: string) => call("desktop_formulation_reject", { formulationId })
};
export type PersonalApi = typeof personalApi;
