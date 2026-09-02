import type { ChangePlan, ExplorationView, InterviewView, ModelItem, PersonalApi, PersonalModelView, PersonalStatus, ReflectionSession, ReflectionTurn, SearchResult, SearchView, SleepEpisode, SleepSourceStatus } from "./personal-api";

export type PreviewScenario = "ACTIVE" | "CLOSED" | "EMPTY" | "SEARCH_MANY" | "SLEEP_EMPTY" | "SLEEP_LAST_NIGHT" | "SLEEP_PARTIAL_STAGES" | "SLEEP_UPDATED_AFTER_RESYNC" | "SLEEP_14_DAY_HISTORY" | "SLEEP_IMPORT_ERROR" | "SLEEP_SOURCE_DETAILS" | "SLEEP_RICH_30_DAYS" | "INTERVIEW_ONBOARDING" | "INTERVIEW_ACTIVE" | "INTERVIEW_WITH_HISTORY" | "INTERVIEW_END_RECOMMENDED" | "INTERVIEW_RETRYABLE_FAILURE" | "INTERVIEW_PAUSED_RECONSENT" | "INTERVIEW_DISCLOSURE" | "INTERVIEW_SLEEP_DISABLED" | "INTERVIEW_WITH_SLEEP_EVIDENCE" | "INTERVIEW_SLEEP_PARTIAL" | "INTERVIEW_SLEEP_COUNTEREVIDENCE" | "INTERVIEW_SLEEP_DISCLOSURE" | "PERSONAL_MODEL_EARLY" | "PERSONAL_MODEL_KNOWN_USER" | "PERSONAL_MODEL_COMPETING_HYPOTHESES" | "PERSONAL_MODEL_COUNTEREVIDENCE" | "PERSONAL_MODEL_REVISION" | "PERSONAL_MODEL_OWNER_CORRECTION" | "PERSONAL_MODEL_CURRENT_VS_HISTORICAL" | "PERSONAL_MODEL_CONTRADICTION" | "PERSONAL_MODEL_SOURCE_DELETED" | "PERSONAL_MODEL_WITH_EXTERNAL_SUPPORT" | "PERSONAL_MODEL_RICH_20_SESSIONS" | "CHANGE_NONE" | "CHANGE_OBSERVE_PROPOSED" | "CHANGE_EXPERIMENT_PROPOSED" | "CHANGE_ACTIVE_OBSERVE" | "CHANGE_ACTIVE_EXPERIMENT_DAY_1" | "CHANGE_ACTIVE_EXPERIMENT_DAY_5" | "CHANGE_WITH_OBSERVATIONS" | "CHANGE_OBSERVATIONS_NOT_AI_ELIGIBLE" | "CHANGE_REVIEW_SUPPORTED" | "CHANGE_REVIEW_WEAKENED" | "CHANGE_REVIEW_INCONCLUSIVE" | "CHANGE_REVIEW_CONTEXT_DEPENDENT" | "CHANGE_STOPPED_BY_OWNER" | "CHANGE_EXPERIMENT_CHANGED_MODEL" | "CHANGE_RICH_HISTORY_10_PLANS";

type PreviewState = {
  sessions: ReflectionSession[];
  explorations: Map<string, ExplorationView>;
  locked: boolean;
  scenario: PreviewScenario;
  interview: InterviewView | null;
  model: PersonalModelView | null;
  changes: ChangePlan[];
};

const at = (day: number) => `2026-08-${String(day).padStart(2, "0")}T10:00:00Z`;
const status = (locked: boolean, interview = false): PersonalStatus => ({
  build_id: "browser-preview-synthetic",
  runtime_profile: interview ? "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI" : "LOCAL_PERSONAL",
  local_personal: "ADMITTED",
  real_data_gate: "CLOSED",
  locked,
  inbound_listener: "NONE",
  outbound_provider: interview ? "OPENAI_EXPLICIT_OPT_IN" : "NOT_CONFIGURED",
  network: interview ? "OPENAI_FOREGROUND_BOUNDED" : "OFFLINE_NO_LISTENER",
  privacy: { core_processing_location: "LOCAL", cloud_storage: "DISABLED", cloud_disclosure: interview ? "EXPLICIT_SESSION_CONSENT_OPENAI_ONLY" : "NEVER_CLOUD", telemetry: "OFF" },
  capabilities: {
    provider: interview,
    working_formulation: false,
    interview,
  },
});

const previewInterview = (scenario: PreviewScenario): InterviewView | null => {
  if (!scenario.startsWith("INTERVIEW_")) return null;
  const end = scenario === "INTERVIEW_END_RECOMMENDED";
  const active = scenario === "INTERVIEW_ACTIVE" || scenario === "INTERVIEW_WITH_HISTORY" || scenario === "INTERVIEW_DISCLOSURE" || scenario === "INTERVIEW_WITH_SLEEP_EVIDENCE" || scenario === "INTERVIEW_SLEEP_PARTIAL" || scenario === "INTERVIEW_SLEEP_COUNTEREVIDENCE" || scenario === "INTERVIEW_SLEEP_DISCLOSURE";
  const failure = scenario === "INTERVIEW_RETRYABLE_FAILURE";
  const hasSleepEvidence = scenario === "INTERVIEW_WITH_SLEEP_EVIDENCE" || scenario === "INTERVIEW_SLEEP_PARTIAL" || scenario === "INTERVIEW_SLEEP_COUNTEREVIDENCE" || scenario === "INTERVIEW_SLEEP_DISCLOSURE";
  const question = scenario === "INTERVIEW_WITH_HISTORY"
    ? "В каком конкретном эпизоде после встречи вы заметили, что переключиться на отдых трудно?"
    : scenario === "INTERVIEW_SLEEP_PARTIAL"
      ? "Какие детали следующего дня стоит учитывать, если за ночь доступна только частичная сводка сна?"
      : scenario === "INTERVIEW_SLEEP_COUNTEREVIDENCE"
        ? "Что в том дне могло повлиять на самочувствие, хотя данные сна не подтверждают короткую ночь?"
        : "Что в последнем похожем эпизоде произошло до того, как стало трудно остановиться?";
  const rationale = scenario === "INTERVIEW_SLEEP_COUNTEREVIDENCE"
    ? "Данные сна — только наблюдение: они не подтверждают эту версию и не объясняют психологическое состояние."
    : scenario === "INTERVIEW_SLEEP_PARTIAL"
      ? "Сводка сна неполна; вопрос не заполняет отсутствующие физиологические данные."
      : "Чтобы отделить общее объяснение от наблюдаемого эпизода.";
  return { interview_session_id: "synthetic-interview", state: end ? "END_RECOMMENDED" : scenario === "INTERVIEW_PAUSED_RECONSENT" ? "PAUSED" : "ACTIVE", owner_topic: null, summary: end ? "Сейчас полезно остановиться: новая информация почти не меняет рабочие версии." : null, next_direction: end ? "Вернуться к одному конкретному эпизоду, когда будет уместно." : null, consent: active ? "ACTIVE_IN_MEMORY" : "ABSENT", source_session_id: "active", current_question: active ? { question_id: "synthetic-question", question, rationale, decision: "ASK", basis_aliases: scenario === "INTERVIEW_WITH_HISTORY" ? ["S1"] : hasSleepEvidence ? ["E1"] : [], attempt_id: "synthetic-question-attempt" } : null, attempts: failure ? [{ attempt_id: "synthetic-failed", state: "OUTCOME_UNKNOWN", answer_turn_id: "synthetic-answer", error_code: "PROVIDER_OUTCOME_UNKNOWN" }] : scenario === "INTERVIEW_DISCLOSURE" || scenario === "INTERVIEW_SLEEP_DISCLOSURE" ? [{ attempt_id: "synthetic-question-attempt", state: "SUCCEEDED", answer_turn_id: "synthetic-answer", error_code: null }] : [] };
};

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
  hypotheses: [{ hypothesis_id: "active-hypothesis", proposal_text: "Короткая пауза может быть полезным переходом после насыщенной встречи.", uncertainty_text: "Пока неясно, работает ли это и в дни без встреч.", discriminator_text: "Сравнить несколько дней с паузой и без неё.", context_refs: [{ context_item_id: "active-unknown", relation: "RELATES_TO", source_turn_ids: ["active-turn-2"] }], created_at: at(5) }, { hypothesis_id: "active-hypothesis-open", proposal_text: "Привычка отвечать сразу может мешать сделать паузу.", uncertainty_text: "Неизвестно, насколько это устойчивая закономерность.", discriminator_text: "Заметить в моменте, когда пауза не состоялась и почему.", context_refs: [{ context_item_id: "active-unknown", relation: "MENTIONS", source_turn_ids: [] }], created_at: at(5) }],
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

const manyTurns: ReflectionTurn[] = Array.from({ length: 45 }, (_, index) => ({ turn_id: `many-turn-${index + 1}`, session_id: "many", sequence: index + 1, actor: "USER" as const, created_at: at(3), content: `Синтетическая запись ${index + 1} о маршруте: утренний маршрут занимает разное время.` }));

// Synthetic Personal Model fixtures: every support/counterevidence excerpt
// points at synthetic USER turns so basis views stay inspectable.
type ModelFixtureInput = {
  id: string;
  kind: ModelItem["kind"];
  state: ModelItem["state"];
  text: string;
  scope: string;
  uncertainty?: string;
  support?: string[];
  counterevidence?: string[];
  challenges?: string[];
  history?: { text: string; reason: string; day: number; status?: ModelItem["history"][number]["status"] }[];
  created?: number;
  updated?: number;
};

const modelFixture = (inputs: ModelFixtureInput[]): PersonalModelView => ({
  items: inputs.map((input) => {
    const created = at(input.created ?? 1);
    const updated = at(input.updated ?? 10);
    const history = [
      ...(input.history ?? []).map((revision, index) => ({ ordinal: index + 1, kind: input.kind, text: revision.text, temporal_scope: input.scope, revision_reason: revision.reason, status: revision.status ?? ("SUPERSEDED" as const), created_at: at(revision.day) })),
      { ordinal: (input.history?.length ?? 0) + 1, kind: input.kind, text: input.text, temporal_scope: input.scope, revision_reason: input.history?.length ? "Версия пересмотрена с учётом новых данных." : null, status: "CURRENT" as const, created_at: updated }
    ];
    const invalidated = input.state === "INVALIDATED";
    return {
      item_id: input.id,
      kind: input.kind,
      state: input.state,
      created_at: created,
      updated_at: updated,
      current: invalidated
        ? null
        : {
            revision_id: `${input.id}-current`,
            text: input.text,
            temporal_scope: input.scope,
            uncertainty: input.uncertainty ?? null,
            created_at: updated,
            support: (input.support ?? []).map((turnId, index) => ({ turn_id: turnId, content: `Синтетическая запись-основание ${index + 1}: ${turnId === "active-turn-1" ? "Встреча дала энергию, но после неё сложно переключиться на отдых." : "Помогает короткая прогулка без телефона, хотя не всегда удаётся её сделать."}`, created_at: at(4), session_id: "active" })),
            counterevidence: (input.counterevidence ?? []).map((turnId, index) => ({ turn_id: turnId, content: `Синтетический контрпример ${index + 1}: в этот раз пауза не потребовалась и всё прошло спокойно.`, created_at: at(6), session_id: "active" }))
          },
      challenges: (input.challenges ?? []).map((text, index) => ({ text, created_at: at(9 + index) })),
      history
    };
  })
});

const previewModel = (scenario: PreviewScenario): PersonalModelView | null => {
  if (!scenario.startsWith("PERSONAL_MODEL_")) return null;
  if (scenario === "PERSONAL_MODEL_WITH_EXTERNAL_SUPPORT") {
    const value = modelFixture([{ id: "sleep-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Одна рабочая версия: трудное утро могло совпасть с короткими ночами.", scope: "UNCLEAR", support: ["active-turn-1"] }]);
    value.items[0]!.current!.external_support = [{ kind: "SLEEP_EPISODE", label: "Health.md → Health Connect", started_at: at(4), ended_at: at(5), snapshot_status: "PARTIAL", classification: "VENDOR_DERIVED" }];
    return value;
  }
  if (scenario === "PERSONAL_MODEL_EARLY")
    return modelFixture([
      { id: "early-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Возможно, после насыщенных встреч трудно переключаться на отдых.", scope: "UNCLEAR", uncertainty: "Пока один эпизод; недостаточно данных.", support: ["active-turn-1"] },
      { id: "early-h2", kind: "HYPOTHESIS", state: "ACTIVE", text: "Одна из версий: короткая прогулка помогает сделать переход.", scope: "UNCLEAR", support: ["active-turn-2"] },
      { id: "early-u1", kind: "UNKNOWN", state: "ACTIVE", text: "Неясно, зависит ли это от дня недели или усталости.", scope: "UNCLEAR", support: ["active-turn-1"] }
    ]);
  if (scenario === "PERSONAL_MODEL_KNOWN_USER")
    return modelFixture([
      { id: "known-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Возможно, контроль становится особенно значимым, когда результат зависит от других людей.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-1", "active-turn-2"] },
      { id: "known-p1", kind: "PATTERN", state: "ACTIVE", text: "Короткая пауза после встреч повторяется как то, что помогает восстановиться.", scope: "CROSS_PERIOD_PATTERN", support: ["active-turn-1", "active-turn-2"] },
      { id: "known-u1", kind: "UNKNOWN", state: "ACTIVE", text: "Пока неясно, работает ли это в дни без встреч.", scope: "UNCLEAR", support: ["active-turn-2"] }
    ]);
  if (scenario === "PERSONAL_MODEL_COMPETING_HYPOTHESES")
    return modelFixture([
      { id: "competing-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Версия А: трудности с паузой связаны с привычкой отвечать сразу.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-1"] },
      { id: "competing-h2", kind: "HYPOTHESIS", state: "ACTIVE", text: "Версия Б: трудности с паузой связаны с остаточным возбуждением после встреч.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-2"] }
    ]);
  if (scenario === "PERSONAL_MODEL_COUNTEREVIDENCE")
    return modelFixture([
      { id: "counter-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Возможно, вы избегаете конфликтов.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-1"], counterevidence: ["active-turn-2"], uncertainty: "Есть контрпример; версия сузилась." }
    ]);
  if (scenario === "PERSONAL_MODEL_REVISION")
    return modelFixture([
      { id: "revision-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Общее избегание конфликтов не подтверждается; паттерн может быть специфичен для ситуаций, где от другого человека зависит значимый результат.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-1", "active-turn-2"], history: [{ text: "Возможно, вы избегаете конфликтов.", reason: "Первичная рабочая версия.", day: 2 }] }
    ]);
  if (scenario === "PERSONAL_MODEL_OWNER_CORRECTION")
    return modelFixture([
      { id: "correction-h1", kind: "HYPOTHESIS", state: "CONTESTED", text: "Возможно, вам важно всё доводить до конца самостоятельно.", scope: "UNCLEAR", support: ["active-turn-1"], challenges: ["Это было верно только для 2021–2022, сейчас я чаще прошу о помощи."] }
    ]);
  if (scenario === "PERSONAL_MODEL_CURRENT_VS_HISTORICAL")
    return modelFixture([
      { id: "historical-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Возможно, это описывало вас раньше, но уже не описывает сейчас: ночные рабочие сессии.", scope: "HISTORICAL_CHANGED", support: ["active-turn-1"], history: [{ text: "Возможно, ночные рабочие сессии — ваша норма.", reason: "Появились данные о недавних изменениях.", day: 2 }] }
    ]);
  if (scenario === "PERSONAL_MODEL_CONTRADICTION")
    return modelFixture([
      { id: "contradiction-c1", kind: "CONTRADICTION", state: "ACTIVE", text: "Записи не сходятся: общение одновременно даёт энергию и затрудняет восстановление.", scope: "UNCLEAR", support: ["active-turn-1", "active-turn-2"] }
    ]);
  if (scenario === "PERSONAL_MODEL_SOURCE_DELETED")
    return modelFixture([
      { id: "deleted-h1", kind: "HYPOTHESIS", state: "INVALIDATED", text: "Эта версия больше не подтверждается: исходная запись удалена.", scope: "UNCLEAR", history: [{ text: "Возможно, утренние маршруты всегда занимают одинаковое время.", reason: "Первая версия.", day: 2 }] }
    ]);
  // PERSONAL_MODEL_RICH_20_SESSIONS: a mature, still readable model.
  return modelFixture([
    { id: "rich-p1", kind: "PATTERN", state: "ACTIVE", text: "Пауза после насыщенных встреч повторяется как то, что помогает восстановиться.", scope: "CROSS_PERIOD_PATTERN", support: ["active-turn-1", "active-turn-2"], created: 1, updated: 10 },
    { id: "rich-h1", kind: "HYPOTHESIS", state: "ACTIVE", text: "Возможно, контроль особенно значим, когда результат зависит от других.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-1"], created: 2, updated: 9 },
    { id: "rich-h2", kind: "HYPOTHESIS", state: "CONTESTED", text: "Возможно, вам важно всё доводить до конца самостоятельно.", scope: "UNCLEAR", support: ["active-turn-2"], challenges: ["Это было верно только для 2021–2022."], created: 3, updated: 8 },
    { id: "rich-c1", kind: "CONTRADICTION", state: "ACTIVE", text: "Общение даёт энергию и одновременно затрудняет восстановление.", scope: "UNCLEAR", support: ["active-turn-1", "active-turn-2"], created: 4, updated: 10 },
    { id: "rich-u1", kind: "UNKNOWN", state: "ACTIVE", text: "Неясно, зависит ли паттерн паузы от дня недели.", scope: "UNCLEAR", support: ["active-turn-2"], created: 5, updated: 7 },
    { id: "rich-h3", kind: "HYPOTHESIS", state: "ACTIVE", text: "Избегание конфликтов, возможно, специфично для рабочих ситуаций.", scope: "CONTEXTUAL_PATTERN", support: ["active-turn-1"], counterevidence: ["active-turn-2"], history: [{ text: "Возможно, вы избегаете конфликтов.", reason: "Первичная версия.", day: 3 }], created: 3, updated: 9 },
    { id: "rich-h4", kind: "HYPOTHESIS", state: "ACTIVE", text: "Ночные рабочие сессии, возможно, остались в прошлом.", scope: "HISTORICAL_CHANGED", support: ["active-turn-1"], history: [{ text: "Возможно, ночные сессии — ваша норма.", reason: "Данные о недавних изменениях.", day: 2 }], created: 2, updated: 8 }
  ]);
};

const previewChanges = (scenario: PreviewScenario): ChangePlan[] => {
  if (!scenario.startsWith("CHANGE_") || scenario === "CHANGE_NONE") return [];
  const observe = scenario.includes("OBSERVE");
  const active = scenario.includes("ACTIVE") || scenario === "CHANGE_WITH_OBSERVATIONS" || scenario === "CHANGE_OBSERVATIONS_NOT_AI_ELIGIBLE";
  const stopped = scenario === "CHANGE_STOPPED_BY_OWNER";
  const reviewed = scenario.startsWith("CHANGE_REVIEW_") || scenario === "CHANGE_EXPERIMENT_CHANGED_MODEL";
  const state: ChangePlan["state"] = stopped ? "STOPPED" : reviewed ? "COMPLETED" : active ? "ACTIVE" : "PROPOSED";
  const review = reviewed ? { practical_effect: scenario === "CHANGE_REVIEW_SUPPORTED" ? "HELPED" : scenario === "CHANGE_REVIEW_WEAKENED" ? "NO_CLEAR_EFFECT" : "MIXED", epistemic_outcome: scenario === "CHANGE_REVIEW_SUPPORTED" ? "SUPPORTED" : scenario === "CHANGE_REVIEW_WEAKENED" || scenario === "CHANGE_EXPERIMENT_CHANGED_MODEL" ? "WEAKENED" : scenario === "CHANGE_REVIEW_CONTEXT_DEPENDENT" ? "CONTEXT_DEPENDENT" : "INCONCLUSIVE", summary: "Синтетический итог реальной проверки.", understanding: "Результат уточняет рабочую версию, а не описывает человека как неизменного.", recommended_next: "COMPLETE", created_at: at(3) } : null;
  const base: ChangePlan = { plan_id: "synthetic-change", kind: observe ? "OBSERVE" : "EXPERIMENT", state, title: observe ? "Наблюдать переход после встреч" : "Короткая пауза после встречи", reason: "Проверить синтетическую рабочую версию.", instructions: observe ? "В нескольких подходящих случаях заметить контекст и трудность перехода." : "После подходящей встречи оставить короткую паузу без новой информации.", observation_prompt: "Что произошло?", expected_signal: "Переключаться немного легче.", counter_signal: "Разницы нет или трудность остаётся.", duration_days: scenario.includes("DAY_5") ? 7 : 5, stop_conditions: "Остановить в любой момент.", created_at: at(3), activated_at: active ? at(4) : null, ended_at: stopped || reviewed ? at(8) : null, targets: [{ item_id: "synthetic-model", revision_id: "synthetic-revision", text: "Возможно, пауза влияет на переключение.", kind: "HYPOTHESIS" }], observations: scenario === "CHANGE_WITH_OBSERVATIONS" || scenario === "CHANGE_OBSERVATIONS_NOT_AI_ELIGIBLE" || reviewed ? [{ turn_id: "synthetic-observation", content: "После паузы переключение заметно не изменилось.", signal: "SAME", created_at: at(6), ai_eligible: scenario !== "CHANGE_OBSERVATIONS_NOT_AI_ELIGIBLE" }] : [], review };
  if (scenario !== "CHANGE_RICH_HISTORY_10_PLANS") return [base];
  return Array.from({ length: 10 }, (_, index) => ({ ...base, plan_id: `synthetic-change-${index + 1}`, title: `Синтетическая проверка ${index + 1}`, state: index === 0 ? "ACTIVE" : index % 2 ? "COMPLETED" : "STOPPED", review: index === 0 ? null : review }));
};

const clone = <T>(value: T): T => structuredClone(value);
const session = (sessionId: string, title: string, state: "ACTIVE" | "CLOSED", turns: ReflectionTurn[], day: number): ReflectionSession => ({ session_id: sessionId, title, state, turn_count: turns.length, turns, created_at: at(day), updated_at: at(day), closed_at: state === "CLOSED" ? at(day) : null });

const scenarioState = (scenario: PreviewScenario): PreviewState => {
  if (scenario === "EMPTY") return { sessions: [], explorations: new Map(), locked: false, scenario, interview: null, model: null, changes: previewChanges(scenario) };
  if (scenario === "SEARCH_MANY") { const many = session("many", "Синтетический сценарий пагинации", "ACTIVE", clone(manyTurns), 3); return { sessions: [many], explorations: new Map([[many.session_id, { context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] }]]), locked: false, scenario, interview: null, model: null, changes: previewChanges(scenario) }; }
  const active = session("active", "Активное размышление", "ACTIVE", clone(activeTurns), 5);
  const closed = session("closed", "Завершённое размышление", "CLOSED", clone(closedTurns), 2);
  if (scenario === "CLOSED") return { sessions: [closed], explorations: new Map([[closed.session_id, closedExploration()]]), locked: false, scenario, interview: null, model: null, changes: previewChanges(scenario) };
  return { sessions: [active, closed], explorations: new Map([[active.session_id, activeExploration()], [closed.session_id, closedExploration()]]), locked: false, scenario, interview: previewInterview(scenario), model: previewModel(scenario), changes: previewChanges(scenario) };
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
    status: async () => status(state.locked, state.interview !== null || state.model !== null || state.changes.length > 0),
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
    aiFormulationExecute: async () => ({}),
    aiInterviewStatus: async () => ({ configured: true, policy_enabled: true, profile_id: "synthetic-no-network", eligible_source_count: 2, sleep_evidence: { enabled: scenario !== "INTERVIEW_SLEEP_DISABLED" } }),
    aiInterviewPolicy: async () => ({}),
    aiInterviewExternalPolicy: async () => ({}),
    aiInterviewSourcePolicy: async () => ({}),
    aiInterviewStart: async () => { state.interview = previewInterview("INTERVIEW_ONBOARDING")!; return clone(state.interview); },
    aiInterviewList: async () => ({ sessions: state.interview ? [clone(state.interview)] : [] }),
    aiInterviewGrantConsent: async () => ({}),
    aiInterviewRevokeConsent: async () => ({}),
    aiInterviewFirstQuestion: async () => { state.interview = { ...(state.interview ?? previewInterview("INTERVIEW_ACTIVE")!), consent: "ACTIVE_IN_MEMORY", current_question: previewInterview("INTERVIEW_ACTIVE")!.current_question }; return clone(state.interview); },
    aiInterviewSubmit: async () => { state.interview = { ...(state.interview ?? previewInterview("INTERVIEW_ACTIVE")!), state: "ACTIVE", consent: "ACTIVE_IN_MEMORY", current_question: previewInterview("INTERVIEW_WITH_HISTORY")!.current_question }; return clone(state.interview); },
    aiInterviewRetry: async () => clone(state.interview ?? previewInterview("INTERVIEW_RETRYABLE_FAILURE")!),
    aiInterviewControl: async (_id, action, topic) => { if (!state.interview) throw new Error("SYNTHETIC_INTERVIEW_NOT_FOUND"); state.interview.state = action === "END" ? "COMPLETED" : action === "STOP" ? "PAUSED" : "ACTIVE"; if (action === "STOP" || action === "END") state.interview.consent = "ABSENT"; if (action === "CHANGE_TOPIC" && topic) state.interview.owner_topic = topic; return clone(state.interview); },
    aiInterviewGet: async () => clone(state.interview ?? previewInterview("INTERVIEW_ONBOARDING")!),
    aiInterviewDisclosure: async (attemptId) => attemptId === "synthetic-question-attempt"
      ? { state: "SUCCEEDED", items: [{ alias: "S1", content: "Синтетическая локальная запись из более раннего размышления для визуальной проверки оснований; сеть не используется.", turn_id: "closed-turn-1", created_at: at(2), session_id: "closed", session_title: "Синтетическое прошлое размышление" }], external_evidence: scenario.includes("SLEEP") || scenario === "INTERVIEW_WITH_SLEEP_EVIDENCE" ? [{ alias: "E1", source_label: "Health.md → Health Connect", raw_not_sent: true, physiology_not_sent: true, content: { start: at(4), end: at(5), duration_minutes: 420, stage_minutes: (scenario === "INTERVIEW_SLEEP_PARTIAL" ? { LIGHT: 230 } : { LIGHT: 230, DEEP: 85, REM: 90 }) as Record<string, number>, snapshot_status: scenario === "INTERVIEW_SLEEP_PARTIAL" ? "PARTIAL" : "COMPLETE" } }] : [], model_items: state.model ? state.model.items.filter((item) => item.current && item.state === "ACTIVE").slice(0, 2).map((item, index) => ({ alias: `M${index + 1}`, kind: item.kind, text: item.current!.text, temporal_scope: item.current!.temporal_scope, uncertainty: item.current!.uncertainty, state: item.state })) : [] }
      : { state: "SUCCEEDED", items: [{ alias: "S1", content: "Синтетическая локальная запись для визуальной проверки; сеть не используется.", turn_id: "active-turn-1", created_at: at(4), session_id: "active", session_title: "Активное синтетическое размышление" }] },
    aiChangeList: async () => ({ plans: clone(state.changes) }),
    aiChangeControl: async (planId, action) => { const plan = state.changes.find((item) => item.plan_id === planId); if (plan) plan.state = action === "ACTIVATE" ? "ACTIVE" : action === "STOP" ? "STOPPED" : "DISMISSED"; return { plans: clone(state.changes) }; },
    aiChangeObserve: async (planId) => ({ turn_id: "synthetic-change-observation", plan_id: planId, source: "USER" as const }),
    aiChangeAllowObservations: async () => ({ plans: [] }),
    aiChangeStartReview: async () => clone(state.interview ?? previewInterview("INTERVIEW_ACTIVE")!),
    aiModelList: async () => clone(state.model ?? { items: [] }),
    aiModelCorrect: async (itemId, content) => {
      const target = state.model?.items.find((item) => item.item_id === itemId);
      if (!target) throw new Error("MODEL_ITEM_NOT_FOUND");
      target.state = "CONTESTED";
      target.challenges = [...target.challenges, { text: content, created_at: at(11) }];
      return clone(state.model!);
    },
    sleepSourceStatus: async () => clone(previewSleepSource(scenario)),
    sleepConfigureInbox: async (inboxPath) => ({ ...previewSleepSource(scenario), configured: true, state: "ACTIVE", inbox_path: inboxPath }),
    sleepScan: async () => ({ records: previewSleepEpisodes(scenario).length * 5, versions: scenario === "SLEEP_UPDATED_AFTER_RESYNC" ? 1 : 0 }),
    sleepHistory: async (days = 14) => ({ episodes: clone(previewSleepEpisodes(scenario).slice(0, days)) }),
    sleepDeleteRecord: async () => ({ deleted: true })
  };
};

const previewSleepEpisodes = (scenario: PreviewScenario): SleepEpisode[] => {
  if (scenario === "SLEEP_EMPTY" || scenario === "SLEEP_IMPORT_ERROR" || scenario === "SLEEP_SOURCE_DETAILS") return [];
  const count = scenario === "SLEEP_RICH_30_DAYS" ? 30 : scenario === "SLEEP_14_DAY_HISTORY" ? 14 : 1;
  return Array.from({ length: count }, (_, index) => {
    const night = new Date(Date.UTC(2026, 7, 29 - index, 22, 45));
    const stamp = (minutes: number) => new Date(night.getTime() + minutes * 60_000).toISOString();
    const startedAt = stamp(0);
    const endedAt = stamp(465);
    const partial = scenario === "SLEEP_PARTIAL_STAGES";
    const updated = scenario === "SLEEP_UPDATED_AFTER_RESYNC";
    return {
      episode_id: `synthetic-sleep-${index + 1}`,
      started_at: startedAt,
      ended_at: endedAt,
      stages: partial ? [] : [
        { category: "LIGHT", started_at: startedAt, ended_at: stamp(145) },
        { category: updated ? "DEEP" : "REM", started_at: stamp(145), ended_at: stamp(260) },
        { category: "LIGHT", started_at: stamp(260), ended_at: endedAt },
      ],
      samples: index === 0 ? [
        { metric: "HEART_RATE", observed_at: stamp(85), value: 52, unit: "bpm" },
        { metric: "RESTING_HEART_RATE", observed_at: stamp(90), value: 48, unit: "bpm" },
        { metric: "SPO2", observed_at: stamp(95), value: 97, unit: "%" },
        { metric: "RESPIRATORY_RATE", observed_at: stamp(100), value: 14, unit: "breaths/min" },
      ] : [],
    };
  });
};

const previewSleepSource = (scenario: PreviewScenario): SleepSourceStatus => ({
  configured: scenario !== "SLEEP_EMPTY",
  label: "Синтетический Health.md / Health Connect",
  state: scenario === "SLEEP_IMPORT_ERROR" ? "ERROR" : scenario === "SLEEP_EMPTY" ? "DISABLED" : "ACTIVE",
  inbox_path: scenario === "SLEEP_EMPTY" ? null : "C:\\Synthetic\\Health",
  last_imported_at: scenario === "SLEEP_IMPORT_ERROR" ? null : at(29),
  snapshot_status: scenario === "SLEEP_PARTIAL_STAGES" ? "PARTIAL" : "COMPLETE",
  issue_count: scenario === "SLEEP_PARTIAL_STAGES" ? 2 : 0,
  nights: previewSleepEpisodes(scenario).length,
});
