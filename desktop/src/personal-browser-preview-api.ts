import type { ExplorationView, PersonalApi, PersonalStatus, ReflectionSession, ReflectionTurn, SearchResult, SearchView } from "./personal-api";

export type PreviewScenario = "ACTIVE" | "CLOSED" | "EMPTY";

type PreviewState = {
  sessions: ReflectionSession[];
  explorations: Map<string, ExplorationView>;
  locked: boolean;
};

const at = (day: number) => `2026-08-${String(day).padStart(2, "0")}T10:00:00Z`;
const status = (locked: boolean): PersonalStatus => ({
  build_id: "browser-preview-synthetic",
  runtime_profile: "LOCAL_PERSONAL",
  local_personal: "ADMITTED",
  real_data_gate: "CLOSED",
  locked,
  inbound_listener: "NONE",
  outbound_provider: "NOT_CONFIGURED",
  network: "OFFLINE_NO_LISTENER",
  privacy: { core_processing_location: "LOCAL", cloud_storage: "DISABLED", cloud_disclosure: "NEVER_CLOUD", telemetry: "OFF" }
});

const activeTurns: ReflectionTurn[] = [
  { turn_id: "active-turn-1", session_id: "active", sequence: 1, actor: "USER", created_at: at(4), content: "Встреча дала энергию, но после неё сложно переключиться на отдых." },
  { turn_id: "active-turn-2", session_id: "active", sequence: 2, actor: "USER", created_at: at(5), content: "Помогает короткая прогулка без телефона, хотя не всегда удаётся её сделать." }
];

const closedTurns: ReflectionTurn[] = [
  { turn_id: "closed-turn-1", session_id: "closed", sequence: 1, actor: "USER", created_at: at(1), content: "После длинного дня хотелось больше тишины, чем планов." },
  { turn_id: "closed-turn-2", session_id: "closed", sequence: 2, actor: "USER", created_at: at(2), content: "Небольшая пауза перед ответом помогла не торопиться." }
];

const activeExploration = (): ExplorationView => ({
  context: [
    { context_item_id: "active-unknown", dimension: "context", kind: "UNKNOWN", text: "Неясно, что чаще мешает сделать паузу: время или привычка отвечать сразу.", state: "OPEN", source_turn_ids: ["active-turn-2"], created_at: at(5) },
    { context_item_id: "active-contradiction", dimension: "context", kind: "CONTRADICTION", text: "Контакт с людьми одновременно даёт энергию и затрудняет восстановление.", state: "UNRESOLVED", source_turn_ids: ["active-turn-1", "active-turn-2"], created_at: at(5) }
  ],
  hypotheses: [{ hypothesis_id: "active-hypothesis", proposal_text: "Короткая пауза может быть полезным переходом после насыщенной встречи.", uncertainty_text: "Это рабочее предположение, а не факт.", discriminator_text: "Проверить на нескольких разных днях.", created_at: at(5) }],
  next_question: { question_id: "active-question", text: "Что помогает заметить момент, когда нужна короткая пауза?" },
  snapshots: [{ snapshot_id: "active-snapshot", version: 1, created_at: at(5) }],
  formulations: [
    { formulation_id: "active-current", version: 3, parent_formulation_id: "active-superseded", status: "CURRENT", origin: "DETERMINISTIC", summary: "Сейчас полезно оставлять короткий переход после встреч, если есть возможность.", correction_text: null, supporting_turn_ids: ["active-turn-1", "active-turn-2"], created_at: at(5), updated_at: at(5) },
    { formulation_id: "active-proposed", version: 4, parent_formulation_id: "active-current", status: "PROPOSED", origin: "AI", summary: "Синтетическое AI-предложение: заранее обозначить себе время для короткой прогулки.", correction_text: null, uncertainty_text: "Предложение требует вашей проверки.", supporting_turn_ids: ["active-turn-2"], ai_provenance: { origin: "AI", provider: "Synthetic preview", actual_model: "no-network" }, created_at: at(5), updated_at: at(5) },
    { formulation_id: "active-superseded", version: 2, parent_formulation_id: null, status: "SUPERSEDED", origin: "DETERMINISTIC", summary: "Старый вариант: после встреч всегда нужен отдых.", correction_text: "Уточнено: это зависит от дня и контекста.", supporting_turn_ids: ["active-turn-1"], created_at: at(4), updated_at: at(5) }
  ]
});

const closedExploration = (): ExplorationView => ({
  context: [{ context_item_id: "closed-unknown", dimension: "context", kind: "UNKNOWN", text: "Остаётся открытым: какая пауза действительно восстанавливает в конце дня.", state: "OPEN", source_turn_ids: ["closed-turn-1"], created_at: at(2) }],
  hypotheses: [],
  next_question: { question_id: "closed-question", text: "Что из этого опыта хочется сохранить на будущее?" },
  snapshots: [{ snapshot_id: "closed-snapshot", version: 1, created_at: at(2) }],
  formulations: [{ formulation_id: "closed-current", version: 1, parent_formulation_id: null, status: "CURRENT", origin: "DETERMINISTIC", summary: "Перед ответом иногда полезна короткая спокойная пауза.", correction_text: null, supporting_turn_ids: ["closed-turn-2"], created_at: at(2), updated_at: at(2) }]
});

const clone = <T>(value: T): T => structuredClone(value);
const session = (sessionId: string, title: string, state: "ACTIVE" | "CLOSED", turns: ReflectionTurn[], day: number): ReflectionSession => ({ session_id: sessionId, title, state, turn_count: turns.length, turns, created_at: at(day), updated_at: at(day), closed_at: state === "CLOSED" ? at(day) : null });

const scenarioState = (scenario: PreviewScenario): PreviewState => {
  if (scenario === "EMPTY") return { sessions: [], explorations: new Map(), locked: false };
  const active = session("active", "Активное размышление", "ACTIVE", clone(activeTurns), 5);
  const closed = session("closed", "Завершённое размышление", "CLOSED", clone(closedTurns), 2);
  if (scenario === "CLOSED") return { sessions: [closed], explorations: new Map([[closed.session_id, closedExploration()]]), locked: false };
  return { sessions: [active, closed], explorations: new Map([[active.session_id, activeExploration()], [closed.session_id, closedExploration()]]), locked: false };
};

const findSession = (state: PreviewState, sessionId: string) => {
  const value = state.sessions.find((item) => item.session_id === sessionId);
  if (!value) throw new Error("SYNTHETIC_SESSION_NOT_FOUND");
  return value;
};

const explorationFor = (state: PreviewState, sessionId: string) => {
  const existing = state.explorations.get(sessionId);
  if (existing) return existing;
  const value: ExplorationView = { context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] };
  state.explorations.set(sessionId, value);
  return value;
};

const searchResults = (state: PreviewState, query: string): SearchResult[] => state.sessions.flatMap((item) => {
  const exploration = explorationFor(state, item.session_id);
  const turns = item.turns ?? [];
  const source = turns[0] ?? null;
  const results: SearchResult[] = [
    ...turns.map((turn) => ({ result_id: `turn:${turn.turn_id}`, result_type: "USER_SOURCE" as const, session_id: item.session_id, session_title: item.title, session_state: item.state, at: turn.created_at, text: turn.content, excerpt: turn.content, turn_id: turn.turn_id, turn_sequence: turn.sequence, status: null, source_turns: [turn], why_here: "Синтетическая запись пользователя.", parent_result_id: null, ai_provenance: null, correction_text: null, related_context: [] })),
    ...exploration.context.map((context) => ({ result_id: `context:${context.context_item_id}`, result_type: context.kind === "UNKNOWN" ? "UNKNOWN" as const : "CONTRADICTION" as const, session_id: item.session_id, session_title: item.title, session_state: item.state, at: context.created_at ?? item.created_at ?? "", text: context.text, excerpt: context.text, turn_id: null, turn_sequence: null, status: context.state, source_turns: turns.filter((turn) => context.source_turn_ids?.includes(turn.turn_id)), why_here: "Синтетический связанный контекст.", parent_result_id: null, ai_provenance: null, correction_text: null, related_context: source ? [{ label: "Запись пользователя", why_related: "Источник этого контекста.", result_id: `turn:${source.turn_id}`, result_type: "USER_SOURCE" as const, session_id: item.session_id, session_title: item.title, turn_id: source.turn_id, turn_sequence: source.sequence, text: source.content }] : [] })),
    ...exploration.formulations.map((formulation) => ({ result_id: `formulation:${formulation.formulation_id}`, result_type: formulation.origin === "AI" ? "AI_PROPOSAL" as const : "FORMULATION" as const, session_id: item.session_id, session_title: item.title, session_state: item.state, at: formulation.updated_at ?? formulation.created_at ?? item.created_at ?? "", text: formulation.summary, excerpt: formulation.summary, turn_id: null, turn_sequence: null, status: formulation.status, source_turns: turns.filter((turn) => formulation.supporting_turn_ids?.includes(turn.turn_id)), why_here: "Синтетическая рабочая формулировка.", parent_result_id: formulation.parent_formulation_id ?? null, ai_provenance: formulation.ai_provenance ? { provider: formulation.ai_provenance.provider, actual_model: formulation.ai_provenance.actual_model } : null, correction_text: formulation.correction_text, related_context: [] }))
  ];
  const needle = query.trim().toLocaleLowerCase();
  return needle ? results.filter((result) => result.text.toLocaleLowerCase().includes(needle)) : results;
});

export const createPersonalBrowserPreviewApi = (scenario: PreviewScenario): PersonalApi => {
  const state = scenarioState(scenario);
  const getExploration = (sessionId: string) => clone(explorationFor(state, sessionId));
  return {
    status: async () => status(state.locked),
    unlock: async () => { state.locked = false; return { session_token: "synthetic-preview-only" }; },
    lock: async () => { state.locked = true; return {}; },
    reflectionCreate: async (title) => { const sessionId = `preview-${state.sessions.length + 1}`; const created = session(sessionId, title, "ACTIVE", [], 6); state.sessions.unshift(created); state.explorations.set(sessionId, { context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] }); return clone(created); },
    reflectionList: async () => ({ sessions: clone(state.sessions) }),
    reflectionGet: async (sessionId) => clone(findSession(state, sessionId)),
    reflectionAddTurn: async (sessionId, content) => { const current = findSession(state, sessionId); if (current.state === "CLOSED") throw new Error("SESSION_CLOSED"); const turn: ReflectionTurn = { turn_id: `${sessionId}-turn-${current.turn_count + 1}`, session_id: sessionId, sequence: current.turn_count + 1, actor: "USER", created_at: at(6), content }; current.turns = [...(current.turns ?? []), turn]; current.turn_count = current.turns.length; current.updated_at = turn.created_at; return clone(turn); },
    reflectionClose: async (sessionId) => { const current = findSession(state, sessionId); current.state = "CLOSED"; current.closed_at = at(6); current.updated_at = at(6); return {}; },
    reflectionDelete: async (sessionId) => { state.sessions = state.sessions.filter((item) => item.session_id !== sessionId); state.explorations.delete(sessionId); return {}; },
    reflectionSearch: async (query, filters, limit = 20, offset = 0) => { const filtered = searchResults(state, query).filter((result) => (filters.state === "ALL" || result.session_state === filters.state) && (filters.content === "ALL" || (filters.content === "SOURCE" && result.result_type === "USER_SOURCE") || (filters.content === "UNKNOWN" && result.result_type === "UNKNOWN") || (filters.content === "CONTRADICTION" && result.result_type === "CONTRADICTION") || (filters.content === "FORMULATION" && ["FORMULATION", "AI_PROPOSAL"].includes(result.result_type)))); const results = filtered.slice(offset, offset + limit); return { query, state: filters.state, content: filters.content, period: filters.period, formulation_status: filters.formulationStatus, total_matches: filtered.length, returned_count: results.length, offset, limit, truncated: offset + results.length < filtered.length, has_more: offset + results.length < filtered.length, results: clone(results) } as SearchView; },
    explorationStart: async (sessionId) => getExploration(sessionId),
    explorationGet: async (sessionId) => getExploration(sessionId),
    explorationAnswer: async (questionId, answerText) => { for (const exploration of state.explorations.values()) if (exploration.next_question?.question_id === questionId) { exploration.context.push({ context_item_id: `answer-${questionId}`, dimension: "context", kind: "KNOWN", text: answerText, state: "RECORDED", created_at: at(6) }); exploration.next_question = null; return clone(exploration); } throw new Error("SYNTHETIC_QUESTION_NOT_FOUND"); },
    explorationSkip: async (questionId) => { for (const exploration of state.explorations.values()) if (exploration.next_question?.question_id === questionId) { exploration.next_question = null; return clone(exploration); } throw new Error("SYNTHETIC_QUESTION_NOT_FOUND"); },
    formulationPropose: async (sessionId) => { const exploration = explorationFor(state, sessionId); exploration.formulations.push({ formulation_id: `proposal-${exploration.formulations.length + 1}`, version: exploration.formulations.length + 1, parent_formulation_id: null, status: "PROPOSED", origin: "DETERMINISTIC", summary: "Новая синтетическая рабочая формулировка для проверки интерфейса.", correction_text: null, created_at: at(6), updated_at: at(6) }); return {}; },
    formulationCorrect: async (formulationId, correctionText) => { for (const exploration of state.explorations.values()) { const current = exploration.formulations.find((item) => item.formulation_id === formulationId); if (current) { current.status = "SUPERSEDED"; exploration.formulations.push({ ...current, formulation_id: `${formulationId}-correction`, version: current.version + 1, parent_formulation_id: formulationId, status: "CURRENT", summary: correctionText, correction_text: correctionText, updated_at: at(6) }); return {}; } } throw new Error("SYNTHETIC_FORMULATION_NOT_FOUND"); },
    formulationAccept: async (formulationId) => { for (const exploration of state.explorations.values()) { const proposed = exploration.formulations.find((item) => item.formulation_id === formulationId); if (proposed) { exploration.formulations.forEach((item) => { if (item.status === "CURRENT") item.status = "SUPERSEDED"; }); proposed.status = "CURRENT"; return {}; } } throw new Error("SYNTHETIC_FORMULATION_NOT_FOUND"); },
    formulationReject: async (formulationId) => { for (const exploration of state.explorations.values()) { const proposed = exploration.formulations.find((item) => item.formulation_id === formulationId); if (proposed) { proposed.status = "REJECTED"; return {}; } } throw new Error("SYNTHETIC_FORMULATION_NOT_FOUND"); },
    personalBackup: async () => ({ backup_id: "synthetic-browser-backup", created_at: at(6) }),
    personalRestoreIsolated: async () => ({ candidate_id: "synthetic-browser-candidate", freshness: "SYNTHETIC", created_at: at(6) }),
    personalExportOwner: async () => ({ export_id: "synthetic-browser-export", audience: "OWNER_ONLY" }),
    personalRotate: async () => ({}),
    personalRecoveryStatus: async () => ({ local_personal: "ADMITTED", rotation: "SYNTHETIC" }),
    aiProviderStatus: async () => ({ provider: "OpenAI" as const, configured: false, model: "no-network", config_id: "synthetic-preview" }),
    aiProviderConfigure: async () => ({}),
    aiProviderDelete: async () => ({}),
    aiFormulationPrepare: async (_sessionId, selectedTurnIds) => ({ interaction_id: "synthetic-preview", preview_id: "synthetic-preview", turns: state.sessions.flatMap((item) => item.turns ?? []).filter((turn) => selectedTurnIds.includes(turn.turn_id)), expires_at: at(6) }),
    aiFormulationExecute: async () => ({})
  };
};
