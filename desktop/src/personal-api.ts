import { invoke } from "@tauri-apps/api/core";

export interface PersonalStatus {
  build_id?: string | null;
  runtime_profile:
    | "LOCAL_PERSONAL"
    | "LOCAL_PERSONAL_BOUNDED_OPENAI"
    | "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI";
  local_personal: "NOT_ADMITTED" | "ADMISSION_AVAILABLE" | "ADMITTED";
  real_data_gate: "CLOSED" | "OPEN";
  admission_expires_at?: string | null;
  locked: boolean;
  setup_required?: boolean;
  inbound_listener: "NONE";
  outbound_provider: "NOT_CONFIGURED" | "OPENAI_EXPLICIT_OPT_IN";
  network:
    | "OFFLINE_NO_LISTENER"
    | "OPENAI_EXPLICIT_ONE_CALL_ONLY"
    | "OPENAI_FOREGROUND_BOUNDED";
  privacy: {
    core_processing_location: "LOCAL";
    cloud_storage: "DISABLED";
    cloud_disclosure:
      | "NEVER_CLOUD"
      | "EXPLICIT_OPT_IN_OPENAI_ONLY"
      | "EXPLICIT_SESSION_CONSENT_OPENAI_ONLY";
    telemetry: "OFF";
  };
}
export interface ReflectionTurn {
  turn_id: string;
  session_id: string;
  sequence: number;
  actor: "USER";
  created_at: string;
  content: string;
}
export interface ReflectionSession {
  session_id: string;
  title: string;
  state: "ACTIVE" | "CLOSED";
  turn_count: number;
  created_at?: string;
  updated_at?: string;
  closed_at?: string | null;
  turns?: ReflectionTurn[];
}
export type SearchContent =
  "ALL" | "SOURCE" | "UNKNOWN" | "CONTRADICTION" | "FORMULATION";
export type SearchPeriod = "7D" | "30D" | "ALL";
export type FormulationStatusFilter =
  "ALL" | "CURRENT" | "PROPOSED" | "REJECTED" | "SUPERSEDED";
export type SearchResultType =
  | "REFLECTION"
  | "USER_SOURCE"
  | "UNKNOWN"
  | "CONTRADICTION"
  | "FORMULATION"
  | "AI_PROPOSAL";
export interface SearchSourceTurn {
  turn_id: string;
  sequence: number;
  created_at: string;
  content: string;
}
export interface RelatedContext {
  label: string;
  why_related: string;
  result_id: string;
  result_type: SearchResultType;
  session_id: string;
  session_title: string;
  turn_id: string | null;
  turn_sequence: number | null;
  text: string;
}
export interface SearchResult {
  result_id: string;
  result_type: SearchResultType;
  session_id: string;
  session_title: string;
  session_state: "ACTIVE" | "CLOSED";
  at: string;
  text: string;
  excerpt: string;
  turn_id: string | null;
  turn_sequence: number | null;
  status: string | null;
  source_turns: SearchSourceTurn[];
  why_here: string;
  parent_result_id: string | null;
  ai_provenance: { provider: string; actual_model: string } | null;
  correction_text: string | null;
  related_context: RelatedContext[];
}
export interface SearchView {
  query: string;
  state: "ALL" | "ACTIVE" | "CLOSED";
  content: SearchContent;
  period: SearchPeriod;
  formulation_status: FormulationStatusFilter;
  total_matches: number;
  returned_count: number;
  offset: number;
  limit: number;
  truncated: boolean;
  has_more: boolean;
  results: SearchResult[];
}
export interface ExplorationView {
  context: {
    context_item_id: string;
    dimension: string;
    kind: "KNOWN" | "UNKNOWN" | "CONTRADICTION";
    text: string;
    state: string;
    source_turn_ids?: string[];
    created_at?: string;
  }[];
  hypotheses: {
    hypothesis_id: string;
    proposal_text: string;
    uncertainty_text: string;
    discriminator_text: string;
    context_refs?: {
      context_item_id: string;
      relation: string;
      source_turn_ids: string[];
    }[];
    created_at?: string;
  }[];
  next_question: { question_id: string; text: string } | null;
  snapshots: unknown[];
  formulations: {
    formulation_id: string;
    version: number;
    parent_formulation_id?: string | null;
    snapshot_id?: string;
    status: "PROPOSED" | "CURRENT" | "REJECTED" | "SUPERSEDED";
    origin?: "DETERMINISTIC" | "AI";
    summary: string;
    correction_text: string | null;
    uncertainty_text?: string | null;
    supporting_turn_ids?: string[];
    ai_provenance?: {
      origin: "AI";
      provider: string;
      actual_model: string;
      config_digest?: string;
      context_manifest_id?: string;
      disclosure_receipt_id?: string;
    };
    created_at?: string;
    updated_at?: string;
  }[];
}
export interface ModelRevision {
  ordinal: number;
  kind: string;
  text: string;
  temporal_scope: string;
  revision_reason: string | null;
  status: "CURRENT" | "SUPERSEDED" | "INVALIDATED";
  created_at: string;
}
export interface ModelSourceExcerpt {
  turn_id: string;
  content: string;
  created_at: string;
  session_id?: string;
}
export interface ModelItem {
  item_id: string;
  kind: "HYPOTHESIS" | "PATTERN" | "CONTRADICTION" | "UNKNOWN";
  state: "ACTIVE" | "CONTESTED" | "RESOLVED" | "INVALIDATED";
  created_at: string;
  updated_at: string;
  current: {
    revision_id: string;
    text: string;
    temporal_scope: string;
    uncertainty: string | null;
    created_at: string;
    support: ModelSourceExcerpt[];
    counterevidence: ModelSourceExcerpt[];
    external_support?: { kind: string; label: string; started_at: string; ended_at: string; snapshot_status: string; classification: string }[];
    external_counterevidence?: { kind: string; label: string; started_at: string; ended_at: string; snapshot_status: string; classification: string }[];
  } | null;
  challenges: { text: string; created_at: string }[];
  history: ModelRevision[];
}
export interface PersonalModelView {
  items: ModelItem[];
}
export interface ChangePlan { plan_id: string; kind: "OBSERVE" | "EXPERIMENT"; state: "PROPOSED" | "ACTIVE" | "COMPLETED" | "STOPPED" | "DISMISSED" | "INVALIDATED"; title: string; reason: string; instructions: string; observation_prompt: string; expected_signal: string; counter_signal: string; duration_days: number | null; stop_conditions: string; created_at: string; activated_at: string | null; ended_at: string | null; targets?: { item_id: string; revision_id: string; text: string; kind: string }[]; observations?: { turn_id: string; content: string; signal: string | null; created_at: string; ai_eligible: boolean }[]; review?: { practical_effect: string; epistemic_outcome: string; summary: string; understanding: string; recommended_next: string; created_at: string } | null; }
export interface InterviewQuestion {
  question_id: string;
  question: string;
  rationale: string;
  decision: "ASK" | "END_RECOMMENDED";
  basis_aliases: string[];
  attempt_id?: string | null;
}
export interface InterviewView {
  interview_session_id: string;
  state: "ACTIVE" | "END_RECOMMENDED" | "PAUSED" | "COMPLETED";
  owner_topic: string | null;
  summary: string | null;
  next_direction: string | null;
  consent: "ABSENT" | "ACTIVE_IN_MEMORY";
  source_session_id?: string | null;
  current_question: InterviewQuestion | null;
  attempts: {
    attempt_id: string;
    state: string;
    answer_turn_id: string | null;
    error_code: string | null;
  }[];
  session_trail?: { actor: "PSYCHE" | "YOU"; text: string; created_at: string }[];
  derived_items?: { item_id: string; kind: string; text: string; priority: number; created_at: string }[];
}
export interface SleepStage { category: string; started_at: string; ended_at: string; }
export interface SleepSample { metric: "HEART_RATE" | "RESTING_HEART_RATE" | "SPO2" | "RESPIRATORY_RATE"; observed_at: string; value: number; unit: string; }
export interface SleepEpisode { episode_id: string; started_at: string; ended_at: string; stages: SleepStage[]; samples: SleepSample[]; }
export interface SleepSourceStatus { configured: boolean; label: string | null; state: string; inbox_path: string | null; last_imported_at: string | null; snapshot_status?: "COMPLETE" | "PARTIAL" | null; issue_count?: number | null; nights: number; }

let sessionToken: string | null = null;
const call = <T>(command: string, args: Record<string, unknown> = {}) =>
  invoke<T>(command, { request: { ...args, sessionToken } });

export const personalApi = {
  status: () => invoke<PersonalStatus>("desktop_status"),
  async unlock(secret: string) {
    const value = await invoke<{ session_token: string }>("desktop_unlock", {
      request: { secret },
    });
    sessionToken = value.session_token;
    return value;
  },
  async lock() {
    const value = await call<Record<string, unknown>>("desktop_lock");
    sessionToken = null;
    return value;
  },
  reflectionCreate: (title: string) =>
    call<ReflectionSession>("desktop_reflection_create", { title }),
  reflectionList: () =>
    call<{ sessions: ReflectionSession[] }>("desktop_reflection_list"),
  reflectionGet: (sessionId: string) =>
    call<ReflectionSession>("desktop_reflection_get", { sessionId }),
  reflectionAddTurn: (sessionId: string, content: string) =>
    call<ReflectionTurn>("desktop_reflection_add_turn", { sessionId, content }),
  reflectionClose: (sessionId: string) =>
    call("desktop_reflection_close", { sessionId }),
  reflectionDelete: (sessionId: string) =>
    call("desktop_reflection_delete", {
      sessionId,
      confirmation: "DELETE REFLECTION SESSION",
    }),
  reflectionSearch: (
    query: string,
    filters: {
      state: "ALL" | "ACTIVE" | "CLOSED";
      content: SearchContent;
      period: SearchPeriod;
      formulationStatus: FormulationStatusFilter;
    },
    limit = 20,
    offset = 0,
  ) =>
    call<SearchView>("desktop_reflection_search", {
      query,
      state: filters.state,
      content: filters.content,
      period: filters.period,
      formulationStatus: filters.formulationStatus,
      limit,
      offset,
    }),
  explorationStart: (sessionId: string) =>
    call<ExplorationView>("desktop_exploration_start", { sessionId }),
  explorationGet: (sessionId: string) =>
    call<ExplorationView>("desktop_exploration_get", { sessionId }),
  explorationAnswer: (questionId: string, answerText: string) =>
    call<ExplorationView>("desktop_exploration_answer", {
      questionId,
      answerText,
    }),
  explorationSkip: (questionId: string) =>
    call<ExplorationView>("desktop_exploration_skip", { questionId }),
  formulationPropose: (sessionId: string) =>
    call("desktop_formulation_propose", { sessionId }),
  formulationCorrect: (formulationId: string, correctionText: string) =>
    call("desktop_formulation_correct", { formulationId, correctionText }),
  formulationAccept: (formulationId: string) =>
    call("desktop_formulation_accept", { formulationId }),
  formulationReject: (formulationId: string) =>
    call("desktop_formulation_reject", { formulationId }),
  personalBackup: (secret: string) =>
    call("desktop_personal_backup", { secret }),
  personalRestoreIsolated: (backupId: string, secret: string) =>
    call("desktop_personal_restore_isolated", { backupId, secret }),
  personalExportOwner: (secret: string) =>
    call("desktop_personal_export_owner", { secret }),
  personalRotate: (secret: string) =>
    call("desktop_personal_rotate", { secret }),
  personalRecoveryStatus: () => call("desktop_personal_recovery_status"),
  aiProviderStatus: () =>
    call<{
      provider: "OpenAI";
      configured: boolean;
      model: string;
      config_id: string;
    }>("desktop_ai_provider_status"),
  aiProviderConfigure: (apiKey: string) =>
    call("desktop_ai_provider_configure", { apiKey }),
  aiProviderDelete: () => call("desktop_ai_provider_delete"),
  aiFormulationPrepare: (sessionId: string, selectedTurnIds: string[]) =>
    call<{
      interaction_id: string;
      preview_id: string;
      turns: { turn_id: string; sequence: number; content: string }[];
      expires_at: string;
    }>("desktop_ai_formulation_prepare", { sessionId, selectedTurnIds }),
  aiFormulationExecute: (interactionId: string, previewId: string) =>
    call("desktop_ai_formulation_execute", { interactionId, previewId }),
  aiInterviewStatus: () =>
    call<{ configured: boolean; policy_enabled: boolean; profile_id: string; eligible_source_count: number }>(
      "desktop_ai_interview_status",
    ),
  aiInterviewPolicy: (enabled: boolean) =>
    call("desktop_ai_interview_policy", { enabled }),
  aiInterviewSourcePolicy: (turnIds: string[], enabled: boolean) =>
    call("desktop_ai_interview_source_policy", { turnIds, enabled }),
  aiInterviewStart: (ownerTopic: string | null = null) =>
    call<InterviewView>("desktop_ai_interview_start", { ownerTopic }),
  aiInterviewList: () =>
    call<{ sessions: InterviewView[] }>("desktop_ai_interview_list"),
  aiInterviewExternalPolicy: (enabled: boolean) => call("desktop_ai_interview_external_policy", { enabled }),
  aiInterviewGrantConsent: (interviewSessionId: string, includeSleep = false) =>
    call("desktop_ai_interview_grant_consent", { interviewSessionId, includeSleep }),
  aiInterviewRevokeConsent: (interviewSessionId: string) =>
    call("desktop_ai_interview_revoke_consent", { interviewSessionId }),
  aiInterviewFirstQuestion: (interviewSessionId: string) =>
    call<InterviewView>("desktop_ai_interview_first_question", {
      interviewSessionId,
    }),
  aiInterviewSubmit: (
    interviewSessionId: string,
    clientSubmissionId: string,
    content: string,
  ) =>
    call<InterviewView>("desktop_ai_interview_submit", {
      interviewSessionId,
      clientSubmissionId,
      content,
    }),
  aiInterviewRetry: (interviewSessionId: string, answerTurnId: string) =>
    call<InterviewView>("desktop_ai_interview_retry", { interviewSessionId, answerTurnId }),
  aiInterviewControl: (
    interviewSessionId: string,
    action: string,
    topic: string | null = null,
  ) =>
    call<InterviewView>("desktop_ai_interview_control", {
      interviewSessionId,
      action,
      topic,
    }),
  aiChangeList: () => call<{ plans: ChangePlan[] }>("desktop_ai_change_list"),
  aiChangeControl: (planId: string, action: "ACTIVATE" | "DISMISS" | "STOP") => call<{ plans: ChangePlan[] }>("desktop_ai_change_control", { planId, action }),
  aiChangeObserve: (planId: string, content: string, signal: string | null) => call<{ turn_id: string; plan_id: string; source: "USER" }>("desktop_ai_change_observe", { planId, content, signal }),
  aiChangeAllowObservations: (planId: string, enabled: boolean) => call<{ plans: ChangePlan[] }>("desktop_ai_change_allow_observations", { planId, enabled }),
  aiChangeStartReview: (planId: string) => call<InterviewView>("desktop_ai_change_start_review", { planId }),
  aiInterviewGet: (interviewSessionId: string) =>
    call<InterviewView>("desktop_ai_interview_get", { interviewSessionId }),
  aiInterviewDisclosure: (attemptId: string) =>
    call<{
      state: string;
      items: {
        alias: string;
        content: string;
        turn_id?: string;
        created_at?: string;
        session_id?: string;
        session_title?: string;
      }[];
      model_items?: {
        alias: string;
        kind: string;
        text: string;
        temporal_scope: string;
        uncertainty: string | null;
        state: string;
      }[];
      external_evidence?: { alias: string; content: { start: string; end: string; duration_minutes: number; stage_minutes: Record<string, number>; snapshot_status: string }; source_label: string; raw_not_sent: boolean; physiology_not_sent: boolean }[];
    }>(
      "desktop_ai_interview_disclosure",
      { attemptId },
    ),
  aiModelList: () => call<PersonalModelView>("desktop_ai_model_list"),
  aiModelCorrect: (itemId: string, content: string) =>
    call<PersonalModelView>("desktop_ai_model_correct", { itemId, content }),
  sleepSourceStatus: () => call<SleepSourceStatus>("desktop_sleep_source_status"),
  sleepConfigureInbox: (inboxPath: string) =>
    call<SleepSourceStatus>("desktop_sleep_configure_inbox", { inboxPath }),
  sleepScan: () => call<{ records: number; versions: number }>("desktop_sleep_scan"),
  sleepHistory: (days = 14) =>
    call<{ episodes: SleepEpisode[] }>("desktop_sleep_history", { days }),
  sleepDeleteRecord: (externalRecordId: string) =>
    call<{ deleted: boolean }>("desktop_sleep_delete_record", { externalRecordId }),
};
export type PersonalApi = typeof personalApi;
