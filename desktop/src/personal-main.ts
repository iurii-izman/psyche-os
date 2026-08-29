import "./personal-styles.css";
import type {
  ExplorationView,
  InterviewView,
  ModelItem,
  ChangePlan,
  PersonalApi,
  PersonalModelView,
  PersonalStatus,
  ReflectionSession,
  SearchResult,
  SearchView,
  SleepEpisode,
  SleepSourceStatus,
} from "./personal-api";
import {
  buildPersonalLongitudinal,
  type LongitudinalPeriod,
} from "./personal-longitudinal";
import { buildContextPack, CONTEXT_PACK_LIMIT } from "./personal-context-pack";

type Route =
  | "home"
  | "interview"
  | "history"
  | "detail"
  | "search"
  | "sensemaking"
  | "longitudinal"
  | "sleep"
  | "privacy"
  | "recovery";
type ExplorationBundle = {
  session: ReflectionSession;
  exploration: ExplorationView | null;
};
const escape = (value: unknown) =>
  String(value ?? "").replace(
    /[&<>"]/g,
    (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c] ?? c,
  );
const errorText = (error: unknown) =>
  error instanceof Error ? error.message : String(error);
const dateLabel = (value?: string | null) => {
  if (!value) return "Дата не указана";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleDateString("ru-RU", {
        day: "numeric",
        month: "long",
        year: "numeric",
      });
};
const statusLabel = (value: string | null | undefined) =>
  (
    ({
      CURRENT: "Текущая",
      PROPOSED: "Предложена",
      SUPERSEDED: "Заменена",
      REJECTED: "Отклонена",
      OPEN: "Открыто",
      UNRESOLVED: "Остаётся открытым",
    }) as Record<string, string>
  )[String(value)] ?? String(value ?? "");

const interviewKindLabel = (kind: string) =>
  (
    ({
      HYPOTHESIS: "РАБОЧЕЕ ПРЕДПОЛОЖЕНИЕ · НЕ ФАКТ",
      CONTRADICTION: "ПРОТИВОРЕЧИЕ",
      UNKNOWN: "ПОКА НЕЯСНО",
      REVISIT: "СТОИТ ВЕРНУТЬСЯ",
      THEME: "ТЕМА ИССЛЕДОВАНИЯ",
      WHITE_SPOT: "МАЛО ДАННЫХ",
    }) as Record<string, string>
  )[kind] ?? "ЗАМЕТКА AI-ИССЛЕДОВАНИЯ · НЕ ФАКТ";

const modelKindLabel = (kind: string) =>
  (
    ({
      HYPOTHESIS: "РАБОЧЕЕ ПРЕДПОЛОЖЕНИЕ · НЕ ФАКТ",
      PATTERN: "ПОВТОРЯЮЩИЙСЯ ПАТТЕРН · ВЫВОД ИЗ ЗАПИСЕЙ",
      CONTRADICTION: "ПРОТИВОРЕЧИЕ · НЕ СХОДЯТСЯ ДАННЫЕ",
      UNKNOWN: "ПОКА НЕЯСНО",
    }) as Record<string, string>
  )[kind] ?? "РАБОЧАЯ ВЕРСИЯ · НЕ ФАКТ";

const temporalLabel = (scope: string) =>
  (
    ({
      CURRENT_STATE: "Похоже на текущее состояние",
      CONTEXTUAL_PATTERN: "Зависит от контекста",
      CROSS_PERIOD_PATTERN: "Повторяется в разных периодах",
      HISTORICAL_CHANGED: "Раньше проявлялось, сейчас могло измениться",
      UNCLEAR: "Пока непонятно, насколько это устойчиво",
    }) as Record<string, string>
  )[scope] ?? "Временная область неясна";

const modelStateLabel = (state: string) =>
  (
    ({
      CONTESTED: "Оспорено вами",
      RESOLVED: "Разрешено",
      INVALIDATED: "Не подтверждается",
    }) as Record<string, string>
  )[state] ?? "";

const modelExcerpt = (excerpt: {
  turn_id: string;
  content: string;
  created_at: string;
  session_id?: string;
}) =>
  `<article class="source-excerpt"><strong>Вы написали</strong><small>${escape(dateLabel(excerpt.created_at))}</small><p>${escape(excerpt.content)}</p>${excerpt.session_id ? `<button class="link-button" data-open-source="${escape(excerpt.session_id)}" data-turn-id="${escape(excerpt.turn_id)}">Открыть источник</button>` : ""}</article>`;

const modelCard = (item: ModelItem) => {
  const current = item.current;
  if (!current) {
    const latest = item.history.at(-1);
    if (!latest) return "";
    return `<article class="hypothesis-card model-card"><p class="hypothesis-label">${escape(modelKindLabel(item.kind))}</p><span class="status-pill">Не подтверждается</span><p class="hypothesis-proposal">${escape(latest.text)}</p><p class="provenance-note">Эта версия больше не активна: значимая опора утрачена или версия разрешена. История сохранена, удалённое содержимое не восстанавливается.</p></article>`;
  }
  const stateBadge = modelStateLabel(item.state)
    ? `<span class="status-pill">${escape(modelStateLabel(item.state))}</span>`
    : "";
  const basis =
    current.support.length || current.counterevidence.length
      ? `<details class="source-evidence"><summary>Почему эта версия · основания ${current.support.length} · не укладывается ${current.counterevidence.length}</summary>${current.support.length ? `<p class="provenance-note">Основания:</p>${current.support.map(modelExcerpt).join("")}` : ""}${current.counterevidence.length ? `<p class="provenance-note">Не укладывается в эту версию:</p>${current.counterevidence.map(modelExcerpt).join("")}` : ""}</details>`
      : "";
  const history = item.history.filter((revision) => revision.status !== "CURRENT");
  const historyMarkup = history.length
    ? `<details><summary>Что изменилось в понимании · ${history.length}</summary>${history.map((revision) => `<article class="history-event"><strong>Предыдущая версия</strong><p>${escape(revision.text)}</p>${revision.revision_reason ? `<small>Причина: ${escape(revision.revision_reason)}</small>` : ""}<small>${escape(dateLabel(revision.created_at))} · исходная версия сохранена.</small></article>`).join("")}</details>`
    : "";
  const challenges = item.challenges.length
    ? item.challenges.map((challenge) => `<article class="history-event"><strong>Ваше исправление</strong><p>${escape(challenge.text)}</p><small>${escape(dateLabel(challenge.created_at))} · сохранено как ваша запись-источник.</small></article>`).join("")
    : "";
  return `<article class="hypothesis-card model-card"><p class="hypothesis-label">${escape(modelKindLabel(item.kind))}</p>${stateBadge}<p class="hypothesis-proposal">${escape(current.text)}</p><p class="provenance-note">${escape(temporalLabel(current.temporal_scope))}</p>${current.uncertainty ? `<p class="hypothesis-field"><strong>Что пока неизвестно</strong><span>${escape(current.uncertainty)}</span></p>` : ""}${challenges}${basis}${historyMarkup}<small>${escape(dateLabel(item.updated_at))}</small><form data-model-challenge="${escape(item.item_id)}"><label>Исправить / оспорить <textarea required maxlength="12000" placeholder="Например: это было верно только для 2021–2022"></textarea></label><button>Сохранить исправление</button></form></article>`;
};

export async function mountPersonal(
  api: PersonalApi,
  host: HTMLDivElement = document.querySelector<HTMLDivElement>("#app")!,
): Promise<void> {
  if (!host) throw new Error("Personal application root is missing");
  let status: PersonalStatus | null = null,
    sessions: ReflectionSession[] = [],
    current: ReflectionSession | null = null,
    exploration: ExplorationView | null = null,
    interview: InterviewView | null = null,
    interviewSessions: InterviewView[] = [],
    model: PersonalModelView | null = null,
    changePlans: ChangePlan[] = [],
    sleepEpisodes: SleepEpisode[] = [],
    sleepSource: SleepSourceStatus | null = null;
  let route: Route = "home",
    notice = "",
    recovery: Record<string, unknown> | null = null,
    search: SearchView | null = null,
    sensemaking: ExplorationBundle[] | null = null,
    longitudinalPeriod: LongitudinalPeriod = "30d",
    busy = false,
    aiConfigured: boolean | null = null,
    interviewEligibility: number | null = null,
    sourceTurnId: string | null = null,
    showContextPack = false;
  type SearchFilters = {
    state: "ALL" | "ACTIVE" | "CLOSED";
    content: SearchView["content"];
    period: SearchView["period"];
    formulationStatus: SearchView["formulation_status"];
  };
  let searchRequest: { query: string; filters: SearchFilters } | null = null;
  const SEARCH_PAGE_LIMIT = 20;
  const mergeSearchPage = (
    previous: SearchView,
    page: SearchView,
  ): SearchView => {
    const seen = new Set(previous.results.map((item) => item.result_id));
    const appended: SearchResult[] = [];
    for (const item of page.results) {
      if (seen.has(item.result_id)) continue;
      seen.add(item.result_id);
      appended.push(item);
    }
    return { ...page, results: [...previous.results, ...appended] };
  };
  const selectedSearch = new Map<string, SearchResult>();
  let aiPreview: {
      interaction_id: string;
      preview_id: string;
      turns: { turn_id: string; sequence: number; content: string }[];
      expires_at: string;
    } | null = null,
    generatedRecoverySecret: string | null = null;
  const generateRecoverySecret = () => {
    const bytes = crypto.getRandomValues(new Uint8Array(24));
    return `PSY-${Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("")}`;
  };
  const ordered = () =>
    [...sessions].sort((a, b) =>
      String(b.updated_at ?? b.created_at ?? "").localeCompare(
        String(a.updated_at ?? a.created_at ?? ""),
      ),
    );
  const refresh = async () => {
    const nextStatus = await api.status();
    status = nextStatus;
    if (!nextStatus.locked && nextStatus.local_personal === "ADMITTED") {
      sessions = (await api.reflectionList()).sessions;
      sleepSource = await api.sleepSourceStatus();
      sleepEpisodes = (await api.sleepHistory(14)).episodes;
      if (nextStatus.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI") {
        const listed = await api.aiInterviewList();
        interviewSessions = listed.sessions;
        model = await api.aiModelList();
        changePlans = api.aiChangeList ? (await api.aiChangeList()).plans : [];
        if (!interview) {
          const selected =
            listed.sessions.find((item) => item.state !== "COMPLETED") ??
            listed.sessions[0] ??
            null;
          interview = selected
            ? await api.aiInterviewGet(selected.interview_session_id)
            : null;
        }
      }
      sensemaking = null;
    }
    return nextStatus;
  };
  const open = async (id: string, turnId: string | null = null) => {
    current = await api.reflectionGet(id);
    exploration = await api.explorationGet(id);
    sourceTurnId = turnId;
    route = "detail";
    render();
  };
  const loadSensemaking = async () => {
    if (sensemaking) return sensemaking;
    sensemaking = await Promise.all(
      ordered().map(async (summary) => {
        try {
          const [session, exploration] = await Promise.all([
            api.reflectionGet(summary.session_id),
            api.explorationGet(summary.session_id),
          ]);
          return { session, exploration };
        } catch {
          return { session: summary, exploration: null };
        }
      }),
    );
    return sensemaking;
  };
  const actionErrorText = (error: unknown) => {
    const message = errorText(error);
    return message.includes("SESSION_CLOSED")
      ? "Размышление завершено. Изменения недоступны."
      : message;
  };
  const act = async (action: () => Promise<void>) => {
    busy = true;
    try {
      await action();
    } catch (error) {
      notice = `Не удалось выполнить действие: ${actionErrorText(error)}`;
    } finally {
      busy = false;
      render();
    }
  };
  const nav = () =>
    `<aside class="personal-sidebar"><div class="personal-brand"><strong>PSYCHE OS</strong><span>Personal</span></div><nav class="product-nav" aria-label="Навигация Personal">${([["home", "Сегодня"], ["sleep", "Сон"], ...(status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI" ? [["interview", "AI-сессия"] as const] : []), ["history", "История"], ["longitudinal", "Во времени"], ["search", "Поиск"], ["sensemaking", "Картина"]] as const).map(([id, label]) => `<button data-route="${id}" class="${route === id ? "active" : ""}"${route === id ? ' aria-current="page"' : ""}>${label}</button>`).join("")}<div class="nav-spacer"></div><button data-route="privacy" class="${route === "privacy" || route === "recovery" ? "active" : ""}"${route === "privacy" || route === "recovery" ? ' aria-current="page"' : ""}>Настройки</button><button id="lock">Заблокировать хранилище</button></nav></aside>`;
  const sessionRow = (item: ReflectionSession) =>
    `<article class="session-row"><div><strong>${escape(item.title)}</strong><small>${escape(dateLabel(item.updated_at ?? item.created_at))} · ${item.turn_count} ${item.turn_count === 1 ? "запись" : "записей"}</small></div><span class="status-pill ${item.state === "ACTIVE" ? "is-active" : ""}">${item.state === "ACTIVE" ? "Активно" : "Завершено"}</span><button data-open="${escape(item.session_id)}">${item.state === "ACTIVE" ? "Продолжить" : "Открыть"}</button></article>`;
  const noticeMarkup = () =>
    `<p class="result" role="status">${escape(busy ? "Сохраняем…" : notice)}</p>`;
  const bindCommon = () => {
    host.querySelectorAll<HTMLButtonElement>("[data-route]").forEach((button) =>
      button.addEventListener(
        "click",
        () =>
          void act(async () => {
            route = button.dataset.route as Route;
            notice = "";
            if (
              route === "sensemaking" ||
              route === "longitudinal" ||
              route === "home"
            )
              await loadSensemaking();
          }),
      ),
    );
    host.querySelector("#lock")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          await api.lock();
          await refresh();
          notice = "Хранилище заблокировано.";
        }),
    );
    host
      .querySelectorAll<HTMLButtonElement>("[data-open]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () => void act(() => open(button.dataset.open!)),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-open-source]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void act(() =>
              open(button.dataset.openSource!, button.dataset.turnId ?? null),
            ),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-search-context]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void act(async () => {
              const query = button.dataset.searchContext?.trim();
              if (!query) return;
              route = "search";
              selectedSearch.clear();
              showContextPack = false;
              searchRequest = {
                query,
                filters: {
                  state: "ALL",
                  content: "ALL",
                  period: "ALL",
                  formulationStatus: "ALL",
                },
              };
              search = await api.reflectionSearch(
                query,
                searchRequest.filters,
                SEARCH_PAGE_LIMIT,
                0,
              );
            }),
        ),
      );
    host
      .querySelectorAll<HTMLFormElement>("[data-model-challenge]")
      .forEach((form) =>
        form.addEventListener("submit", (event) => {
          event.preventDefault();
          const content = form.querySelector("textarea")?.value.trim();
          if (!content) return;
          void act(async () => {
            model = await api.aiModelCorrect(form.dataset.modelChallenge!, content);
            notice =
              "Исправление сохранено как ваша запись-источник; рабочая версия помечена как оспоренная.";
          });
        }),
      );
  };
  const submit = (selector: string, action: () => Promise<void>) =>
    host
      .querySelector<HTMLFormElement>(selector)
      ?.addEventListener("submit", (event) => {
        event.preventDefault();
        void act(action);
      });
  const sourceEvidence = (
    bundle: ExplorationBundle,
    turnIds: string[] = [],
  ) => {
    const turns = (bundle.session.turns ?? []).filter((turn) =>
      turnIds.includes(turn.turn_id),
    );
    if (!turnIds.length)
      return `<p class="provenance-note">На основе структуры исследования; конкретная запись не указана.</p>`;
    if (!turns.length)
      return `<p class="provenance-note">Связанный источник больше не доступен в этом представлении.</p>`;
    return `<details class="source-evidence"><summary>Показать источник · ${turns.length}</summary>${turns.map((turn) => `<article class="source-excerpt"><strong>Вы написали · запись ${turn.sequence}</strong><small>${escape(dateLabel(turn.created_at))} · ${escape(bundle.session.title)}</small><p>${escape(turn.content)}</p><button class="link-button" data-open-source="${escape(bundle.session.session_id)}" data-turn-id="${escape(turn.turn_id)}">Открыть размышление</button></article>`).join("")}</details>`;
  };
  const hypothesisCard = (
    bundle: ExplorationBundle,
    item: ExplorationView["hypotheses"][number],
  ) => {
    const turnIds = [
      ...new Set(
        (item.context_refs ?? []).flatMap((ref) => ref.source_turn_ids ?? []),
      ),
    ];
    const provenance =
      (item.context_refs?.length ?? 0) > 0 && !turnIds.length
        ? `<p class="provenance-note">Связано с открытыми вопросами исследования; конкретная исходная запись не указана.</p>`
        : sourceEvidence(bundle, turnIds);
    return `<article class="hypothesis-card"><p class="hypothesis-label">РАБОЧЕЕ ПРЕДПОЛОЖЕНИЕ · НЕ ФАКТ</p><p class="hypothesis-proposal">${escape(item.proposal_text)}</p>${item.uncertainty_text ? `<p class="hypothesis-field"><strong>Что пока неизвестно</strong><span>${escape(item.uncertainty_text)}</span></p>` : ""}${item.discriminator_text ? `<p class="hypothesis-field"><strong>Что поможет проверить</strong><span>${escape(item.discriminator_text)}</span></p>` : ""}${item.created_at ? `<small>${escape(dateLabel(item.created_at))}</small>` : ""}${provenance}</article>`;
  };
  const derivedCard = (
    bundle: ExplorationBundle,
    text: string,
    options: {
      label: string;
      detail?: string;
      sourceTurnIds?: string[];
      ai?: boolean;
      createdAt?: string;
    },
  ) =>
    `<article class="derived ${options.ai ? "is-ai-proposal" : ""}"><p>${options.ai ? "ПРЕДЛОЖЕНО AI" : "ВЫВОД ИЗ ЗАПИСЕЙ"}</p><h3>${escape(options.label)}</h3><p>${escape(text)}</p>${options.detail ? `<p class="provenance-note">${escape(options.detail)}</p>` : ""}${options.createdAt ? `<small>${escape(dateLabel(options.createdAt))}</small>` : ""}${sourceEvidence(bundle, options.sourceTurnIds)}<button class="link-button" data-search-context="${escape(text)}">Открыть в поиске и контексте</button></article>`;
  const formulationCard = (
    bundle: ExplorationBundle,
    item: ExplorationView["formulations"][number],
    controls = false,
  ) => {
    const statusText = statusLabel(item.status);
    const origin = item.ai_provenance
      ? `AI · ${item.ai_provenance.provider} · ${item.ai_provenance.actual_model}`
      : "Детерминированно из записей";
    const lineage = item.parent_formulation_id
      ? "Есть предыдущая версия; история сохранена."
      : "Первая сохранённая версия.";
    const controlsMarkup =
      controls && (item.status === "PROPOSED" || item.status === "CURRENT")
        ? `${item.status === "PROPOSED" ? `<button data-accept="${escape(item.formulation_id)}" class="primary">Сделать текущей</button><button data-reject="${escape(item.formulation_id)}">Отклонить формулировку</button>` : ""}<form data-correct="${escape(item.formulation_id)}"><label>Исправить, сохранив историю <textarea required maxlength="12000"></textarea></label><button>Сохранить исправление</button></form>`
        : "";
    return `${derivedCard(bundle, item.summary, { label: `Рабочая формулировка · ${statusText}`, detail: `${origin}. ${lineage}${item.uncertainty_text ? ` Неясно: ${item.uncertainty_text}` : ""}`, sourceTurnIds: item.supporting_turn_ids, ai: item.origin === "AI", createdAt: item.updated_at ?? item.created_at })}${controlsMarkup ? `<div class="formulation-controls">${controlsMarkup}</div>` : ""}`;
  };
  const explorationMarkup = () => {
    if (!current || !exploration) return "";
    const bundle = { session: current, exploration },
      readOnly = current.state === "CLOSED";
    const contextLabels = {
        KNOWN: "Зафиксировано",
        UNKNOWN: "Неясно",
        CONTRADICTION: "Противоречие",
      } as const,
      contexts = exploration.context
        .map((item) =>
          derivedCard(bundle, item.text, {
            label: contextLabels[item.kind],
            detail: `Статус: ${statusLabel(item.state)}`,
            sourceTurnIds: item.source_turn_ids,
            createdAt: item.created_at,
          }),
        )
        .join("");
    const hypotheses = exploration.hypotheses
      .map((item) => hypothesisCard(bundle, item))
      .join("");
    const question = exploration.next_question,
      formulations = exploration.formulations
        .map((item) => formulationCard(bundle, item, !readOnly))
        .join("");
    return `<section class="guided-exploration"><h2>Исследование размышления</h2>${readOnly ? '<p class="provenance-note">Размышление завершено. Исследование доступно только для чтения.</p>' : ""}${contexts ? `<section><h3>Сохранённый контекст</h3>${contexts}</section>` : ""}${hypotheses ? `<section class="hypotheses-section"><h3>Рабочие предположения</h3><p class="provenance-note">Локальные варианты для рассмотрения. Это не факты, не диагнозы и не выводы AI.</p>${hypotheses}</section>` : ""}${question ? `<article class="card"><h3>Текущий вопрос</h3><p>${escape(question.text)}</p>${readOnly ? "" : `<form id="answer-question"><label>Ваш ответ <textarea id="question-answer" required maxlength="12000"></textarea></label><button>Ответить</button><button type="button" id="skip-question">Пропустить</button></form>`}</article>` : "<p>Сейчас нет вопроса.</p>"}${readOnly ? "" : `<div><button id="start-exploration">${exploration.snapshots.length ? "Обновить исследование" : "Начать исследование"}</button><button id="propose-formulation">Предложить рабочую формулировку</button></div>`}${formulations}</section>`;
  };
  const detailMarkup = () => {
    if (!current) return "";
    const turns = [...(current.turns ?? [])].sort(
        (a, b) => a.sequence - b.sequence,
      ),
      aiAvailable =
        status?.runtime_profile === "LOCAL_PERSONAL_BOUNDED_OPENAI" &&
        current.state === "ACTIVE" &&
        turns.length;
    const preview = aiPreview
      ? `<section class="card"><p>OPENAI · РАЗОВОЕ РАСКРЫТИЕ</p><h2>Проверьте выбранные записи</h2><p>Эти выбранные тексты покинут устройство один раз. Результат AI — предложение, а не факт.</p>${aiPreview.turns.map((turn) => `<article class="session-turn"><strong>Запись ${turn.sequence}</strong><p>${escape(turn.content)}</p></article>`).join("")}<button id="ai-send" class="primary">Отправить выбранное в OpenAI</button><button id="ai-cancel">Отмена</button></section>`
      : "";
    const selector = aiAvailable
      ? `<section class="card"><h2>Рабочая формулировка с AI</h2><p>Выберите до 8 ваших записей. Ничего не будет отправлено до точного предпросмотра и отдельного подтверждения.</p><form id="ai-selection">${turns.map((turn) => `<label><input type="checkbox" name="ai-turn" value="${escape(turn.turn_id)}" /> Запись ${turn.sequence} · ${turn.content.length} знаков</label>`).join("")}<button>Показать выбранное для проверки</button></form></section>`
      : "";
    const interviewPolicy = status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI" && turns.length
      ? `<section class="card"><h2>Разрешение для AI-исследования</h2><p>Выберите конкретные записи, которые можно передавать только OpenAI для цели «AI-исследование». Невыбранные исторические записи остаются локальными и не передаются.</p><form id="interview-source-policy">${turns.map((turn) => `<label><input type="checkbox" name="interview-source-turn" value="${escape(turn.turn_id)}" /> Запись ${turn.sequence}</label>`).join("")}<button class="primary">Разрешить выбранные записи</button><button type="button" id="interview-source-revoke">Отозвать разрешение</button></form><div class="formulation-controls"><button id="interview-source-allow-all">Разрешить всё размышление для AI</button><button id="interview-source-revoke-all">Отозвать разрешение со всего размышления</button></div><p class="provenance-note">Кнопки выше действуют только на записи этого размышления; разрешение остаётся точным и отдельным для каждой записи.</p></section>`
      : "";
    return `<main class="product-shell">${nav()}<header class="session-header"><p>РАЗМЫШЛЕНИЕ</p><h1>${escape(current.title)}</h1><p>${current.state === "CLOSED" ? "Завершено — только чтение" : "Активно — можно продолжить"}</p><button data-route="history">К истории</button></header><section class="card"><h2>Что вы написали</h2>${turns.length ? turns.map((turn) => `<article class="session-turn ${sourceTurnId === turn.turn_id ? "is-source-highlight" : ""}"><strong>Вы написали · запись ${turn.sequence}</strong><small>${escape(dateLabel(turn.created_at))}</small><p>${escape(turn.content)}</p></article>`).join("") : "<p>Записей пока нет.</p>"}${current.state === "ACTIVE" ? `<form id="add-turn"><label>Продолжить <textarea id="reflection-turn" required maxlength="12000"></textarea></label><button class="primary">Добавить запись</button></form><button id="close-reflection">Завершить размышление</button>` : ""}<button id="delete-reflection" class="danger">Удалить размышление</button></section>${interviewPolicy}${selector}${preview}${explorationMarkup()}${noticeMarkup()}</main>`;
  };
  const sleepMarkup = () => {
    void sleepSource;
    const latest = sleepEpisodes[0];
    const minutes = (start: string, end: string) => Math.max(0, Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60_000));
    const duration = latest ? minutes(latest.started_at, latest.ended_at) : 0;
    const stageSummary = latest ? latest.stages.reduce<Record<string, number>>((all, stage) => {
      all[stage.category] = (all[stage.category] ?? 0) + minutes(stage.started_at, stage.ended_at);
      return all;
    }, {}) : {};
    const row = (episode: SleepEpisode) => `<article class="session-row"><div><strong>${escape(dateLabel(episode.started_at))}</strong><small>${escape(episode.started_at)} → ${escape(episode.ended_at)} · ${minutes(episode.started_at, episode.ended_at)} мин</small></div></article>`;
    return `<main class="product-shell">${nav()}<section class="product-home"><p>LOCAL HEALTH CONNECT</p><h1>Сон</h1><p>Стадии сна — оценки устройства/поставщика, а не медицинский вывод.</p></section>${latest ? `<section class="card"><h2>Последняя ночь · ${duration} мин</h2><p>${escape(latest.started_at)} → ${escape(latest.ended_at)}</p><div class="review-counts">${Object.entries(stageSummary).map(([stage, value]) => `<span>${escape(stage)} · ${value} мин</span>`).join("") || "Стадии недоступны / частичны."}</div><section class="card"><h3>Хронология стадий</h3>${latest.stages.length ? latest.stages.map((stage) => `<p>${escape(stage.category)} · ${escape(stage.started_at)} → ${escape(stage.ended_at)}</p>`).join("") : "Стадии недоступны / частичны."}</section></section>` : `<section class="card calm-empty"><h2>Данных о сне пока нет</h2><p>Выберите локальную папку Health.md в настройках, затем проверьте её. Отсутствующие показатели не заменяются нулями.</p></section>`}<section class="card"><h2>Последние 14 ночей</h2>${sleepEpisodes.length ? sleepEpisodes.map(row).join("") : "Нет импортированных ночей."}</section>${noticeMarkup()}</main>`;
  };
  const homeMarkup = () => {
    const recent = ordered().slice(0, 5),
      bundles = sensemaking ?? [],
      modelReason = (() => {
        const items = (model?.items ?? []).filter((item) => item.current);
        if (items.some((item) => item.kind === "CONTRADICTION" && item.state === "ACTIVE"))
          return "Есть противоречие, которое стоит проверить";
        if (items.some((item) => item.state === "CONTESTED"))
          return "Есть рабочая версия, которую вы оспорили — её стоит перепроверить";
        if (
          items.some(
            (item) =>
              item.kind === "HYPOTHESIS" &&
              item.state === "ACTIVE" &&
              (item.current?.counterevidence.length ?? 0) === 0,
          )
        )
          return "Есть рабочая версия, которой пока не хватает контрпримеров";
        if (items.some((item) => item.kind === "UNKNOWN" && item.state === "ACTIVE"))
          return "Мы пока плохо понимаем, устойчива ли одна важная часть картины";
        return null;
      })(),
      active = ordered().filter((item) => item.state === "ACTIVE"),
      unknowns = bundles.reduce(
        (count, bundle) =>
          count +
          (bundle.exploration?.context.filter(
            (item) => item.kind === "UNKNOWN" && item.state === "OPEN",
          ).length ?? 0),
        0,
      ),
      contradictions = bundles.reduce(
        (count, bundle) =>
          count +
          (bundle.exploration?.context.filter(
            (item) =>
              item.kind === "CONTRADICTION" && item.state === "UNRESOLVED",
          ).length ?? 0),
        0,
      ),
      currentFormulations = bundles.reduce(
        (count, bundle) =>
          count +
          (bundle.exploration?.formulations.filter(
            (item) => item.status === "CURRENT",
          ).length ?? 0),
        0,
      );
    let interviewCard =
        status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI"
          ? `<section class="card daily-review inquiry-primary"><p>AI-ИССЛЕДОВАНИЕ</p><h2>${interview && interview.state !== "COMPLETED" ? "Продолжить исследование" : "Начать исследование"}</h2><p>${interview?.next_direction ? `Полезно вернуться к: ${escape(interview.next_direction)}` : interview?.owner_topic ? `Продолжим выбранную тему: ${escape(interview.owner_topic)}` : "PSYCHE задаёт один вопрос за раз и постепенно проясняет важное — без анкеты и без спешки."}</p>${modelReason ? `<p class="provenance-note">${escape(modelReason)}</p>` : ""}<p class="provenance-note">Ваши ответы сохраняются локально как источники; выводы AI — рабочие предложения.</p><button data-route="interview" class="primary">${interview && interview.state !== "COMPLETED" ? "Продолжить" : "Начать AI-сессию"}</button>${!interview || interview.state === "COMPLETED" ? '<button id="home-start-topic">Есть тема, о которой хочу поговорить</button>' : '<button id="home-new-topic">Начать с другой темы</button>'}</section>`
          : "";
    const activeChange = changePlans.find((plan) => plan.state === "ACTIVE" && plan.kind === "EXPERIMENT") ?? changePlans.find((plan) => plan.state === "ACTIVE");
    const changeCard = activeChange ? `<section class="card daily-review"><p>СЕЙЧАС ПРОВЕРЯЕМ</p><h2>${escape(activeChange.title)}</h2><p>${escape(activeChange.instructions)}</p><form data-change-observation="${escape(activeChange.plan_id)}"><label>Что произошло?<textarea required maxlength="12000"></textarea></label><select><option value="UNCLEAR">Пока неясно</option><option value="BETTER">Стало легче</option><option value="SAME">Без разницы</option><option value="WORSE">Стало хуже</option></select><button class="primary">Записать наблюдение</button></form><button data-change-stop="${escape(activeChange.plan_id)}">Остановить</button><p class="provenance-note">Запись остаётся локальным источником, пока вы отдельно не разрешите AI-разбор.</p></section>` : "";
    const proposedChange = changePlans.find((plan) => plan.state === "PROPOSED");
    const proposalCard = proposedChange ? `<section class="card"><p>ПРЕДЛАГАЮ ПРОВЕРИТЬ · AI-ПРЕДЛОЖЕНИЕ</p><h2>${escape(proposedChange.title)}</h2><p>${escape(proposedChange.reason)}</p><p>${escape(proposedChange.instructions)}</p><p><strong>Ожидаемый сигнал:</strong> ${escape(proposedChange.expected_signal)}</p><p><strong>Что ослабит версию:</strong> ${escape(proposedChange.counter_signal)}</p><button class="primary" data-change-activate="${escape(proposedChange.plan_id)}">${proposedChange.kind === "OBSERVE" ? "Начать наблюдение" : "Попробовать"}</button><button data-change-dismiss="${escape(proposedChange.plan_id)}">Пока не хочу</button></section>` : "";
    const observationCount = activeChange?.observations?.length ?? 0;
    const eligibleObservationCount = activeChange?.observations?.filter((item) => item.ai_eligible).length ?? 0;
    const reviewCard = activeChange && observationCount ? `<section class="card"><p>НАБЛЮДЕНИЯ · ЛОКАЛЬНО ПО УМОЛЧАНИЮ</p><h2>${observationCount} записей</h2><p>Для AI-разбора разрешено: ${eligibleObservationCount}. Будущие наблюдения не будут разрешены автоматически.</p><button data-change-observations-allow="${escape(activeChange.plan_id)}">Разрешить наблюдения для AI-разбора</button>${eligibleObservationCount ? `<button data-change-observations-revoke="${escape(activeChange.plan_id)}">Отозвать разрешение</button><button class="primary" data-change-review="${escape(activeChange.plan_id)}">Разобрать с PSYCHE</button>` : ""}</section>` : "";
    const completedReview = changePlans.find((plan) => plan.review && plan.state === "COMPLETED");
    const effectLabel: Record<string, string> = { HELPED: "стало легче", NO_CLEAR_EFFECT: "ясного эффекта не видно", WORSE: "стало хуже", MIXED: "эффект смешанный", NOT_TESTED: "пока не проверяли" };
    const epistemicLabel: Record<string, string> = { SUPPORTED: "версия согласуется с наблюдениями", WEAKENED: "версия ослаблена", INCONCLUSIVE: "пока недостаточно данных", CONTEXT_DEPENDENT: "результат зависит от контекста" };
    const outcomeCard = completedReview?.review ? `<section class="card"><p>ЧТО УЗНАЛИ В РЕАЛЬНОЙ ЖИЗНИ · AI-ВЫВОД</p><h2>${escape(completedReview.title)}</h2><p>${escape(completedReview.review.summary)}</p><p><strong>О практическом эффекте:</strong> ${effectLabel[completedReview.review.practical_effect] ?? "неясно"}</p><p><strong>О рабочей версии:</strong> ${epistemicLabel[completedReview.review.epistemic_outcome] ?? "неясно"}</p><p>${escape(completedReview.review.understanding)}</p></section>` : "";
    interviewCard = `${changeCard}${proposalCard}${reviewCard}${outcomeCard}${interviewCard}`;
    const homeLead = activeChange ? `Сейчас проверяем: ${activeChange.title}` : status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI" ? "Что сейчас полезно исследовать?" : "Запишите то, к чему хотите вернуться.";
    const latestSleep = sleepEpisodes[0];
    return `<main class="product-shell home-shell">${nav()}<section class="product-home compact-heading"><p>PERSONAL</p><h1>Сегодня</h1><p>${homeLead}</p></section>${latestSleep ? `<section class="card daily-review"><p>СОН · ЛОКАЛЬНЫЙ ИМПОРТ</p><h2>Последняя ночь · ${Math.round((new Date(latestSleep.ended_at).getTime() - new Date(latestSleep.started_at).getTime()) / 60_000)} мин</h2><p>${escape(latestSleep.started_at)} → ${escape(latestSleep.ended_at)}. Стадии — оценки устройства.</p><button data-route="sleep">Подробнее</button></section>` : ""}${interviewCard}<section class="card quick-capture"><p>БЫСТРАЯ ЗАПИСЬ</p><h2>Сохранить мысль</h2><form id="quick-capture-form"><label>Название (необязательно) <input id="quick-capture-title" maxlength="160" placeholder="Короткая заметка" autofocus /></label><label>Текст <textarea id="quick-capture-text" required maxlength="12000" placeholder="Напишите то, что хотите сохранить…"></textarea></label><button class="primary">Сохранить</button></form></section><section class="card daily-review"><div><p>КАРТИНА</p><h2>Ваши записи и выводы</h2></div><div class="review-counts"><span>${active.length} активных размышлений</span><span>${currentFormulations} текущих формулировок</span><span>${unknowns} неясного</span><span>${contradictions} противоречий</span></div><button data-route="sensemaking" class="primary">Открыть картину</button><button data-route="longitudinal">Посмотреть изменения за 30 дней</button></section><section class="card recent-card"><p>НЕДАВНЕЕ</p><h2>Ваши размышления</h2>${recent.length ? recent.map(sessionRow).join("") : "<p>Первая запись появится здесь.</p>"}<button data-route="history">Открыть историю</button></section>${noticeMarkup()}</main>`;
  };

  const interviewMarkup = () => {
    if (!interview)
      return `<main class="product-shell">${nav()}<section class="product-home"><p>AI-ИССЛЕДОВАНИЕ</p><h1>Начать AI-сессию</h1><p>Один вопрос за раз. Перед первой отправкой будет показано согласие на ограниченную передачу в OpenAI.</p><button id="interview-start" class="primary">Начать AI-сессию</button></section>${noticeMarkup()}</main>`;
    const question = interview.current_question;
    const basis = question
      ? question.attempt_id
        ? `<details id="interview-basis" data-attempt="${escape(question.attempt_id)}"><summary>Показать основания</summary><p class="provenance-note" data-basis-body>Загружаем основания…</p></details>`
        : `<details><summary>Показать основания</summary><p>Основание: текущая сессия и выбранное направление.</p></details>`
      : "";
    const disclosure = interview.attempts[0]
      ? `<button data-disclosure="${escape(interview.attempts[0].attempt_id)}">Что было передано</button>`
      : "";
    const consent =
      interview.consent === "ACTIVE_IN_MEMORY"
        ? "Согласие активно только в памяти этого запуска."
        : "Передача выключена до явного согласия.";
    const trail = interview.session_trail?.length
      ? `<details class="card session-trail"><summary>Ход этой сессии · ${interview.session_trail.length}</summary>${interview.session_trail.map((item) => `<article class="session-turn ${item.actor === "PSYCHE" ? "derived" : ""}"><strong>${item.actor === "PSYCHE" ? "PSYCHE спросил" : "ВЫ ответили"}</strong><p>${escape(item.text)}</p></article>`).join("")}</details>`
      : "";
    const main = question
      ? `<section class="card interview-focus"><p>PSYCHE · ОДИН ВОПРОС</p><h1>${escape(question.question)}</h1><details><summary>Почему этот вопрос?</summary><p>${escape(question.rationale)}</p></details>${basis}<form id="interview-answer"><label>Ваш ответ <textarea id="interview-answer-text" required maxlength="12000"></textarea></label><button class="primary">Ответить</button></form><div class="formulation-controls"><button data-interview-control="SKIP">Пропустить</button><button data-interview-control="DECLINE">Не хочу обсуждать</button><button data-interview-control="CHANGE_TOPIC">Сменить тему</button><button data-interview-control="STOP" class="danger">Остановить</button></div></section>`
      : `<section class="card"><p>${escape(consent)}</p><button id="${interview.consent === "ACTIVE_IN_MEMORY" ? "interview-next" : "interview-consent"}" class="primary">${interview.consent === "ACTIVE_IN_MEMORY" ? "Продолжить исследование" : "Показать согласие и продолжить"}</button></section>`;
    const end =
      interview.state === "END_RECOMMENDED"
        ? `<section class="card interview-result"><p>РЕКОМЕНДАЦИЯ AI · НЕ РЕШЕНИЕ ЗА ВАС</p><h2>Что стало яснее</h2><p>${escape(interview.summary ?? "Можно завершить эту линию на сейчас.")}</p><h3>Что вы рассказали</h3><p>Ваши ответы остаются отдельными локальными источниками — их можно увидеть в ходе сессии.</p><h3>Рабочие предположения · НЕ ФАКТ</h3>${(interview.derived_items ?? []).filter((item) => item.kind === "HYPOTHESIS").map((item) => `<p>${escape(item.text)}</p>`).join("") || "<p>Новых рабочих предположений не сохранено.</p>"}<h3>Противоречия / неизвестное</h3>${(interview.derived_items ?? []).filter((item) => item.kind === "CONTRADICTION" || item.kind === "UNKNOWN").map((item) => `<p>${escape(item.text)}</p>`).join("") || "<p>Новых открытых пунктов не сохранено.</p>"}<h3>К чему вернуться</h3><p>${escape(interview.next_direction ?? "Следующее направление сохранено локально.")}</p><button data-interview-control="END" class="primary">Завершить</button><button data-interview-control="CONTINUE">Продолжить</button></section>`
        : "";
    return `<main class="product-shell">${nav()}<section class="product-home"><p>AI-ИССЛЕДОВАНИЕ</p><h1>Исследование</h1><p>${escape(consent)} Всё хранилище не передаётся; фоновых вызовов нет.</p></section>${end}${main}${trail}${disclosure ? `<section class="card">${disclosure}<div id="interview-disclosure"></div></section>` : ""}${noticeMarkup()}</main>`;
  };
  const historyMarkup = () =>
    `<main class="product-shell">${nav()}<section class="product-home"><p>ЛИЧНЫЕ ЗАПИСИ</p><h1>История</h1><p>Недавние записи — в начале списка.</p></section><section class="card sessions-card">${ordered().length ? ordered().map(sessionRow).join("") : "<p>История пока пуста. Начните с быстрой записи.</p>"}</section>${noticeMarkup()}</main>`;
  const normaliseSearchResult = (item: SearchResult): SearchResult => ({
    ...item,
    result_id:
      item.result_id ??
      `legacy:${item.session_id}:${item.turn_id ?? "reflection"}`,
    result_type:
      item.result_type ?? (item.turn_id ? "USER_SOURCE" : "REFLECTION"),
    at: item.at ?? "",
    text: item.text ?? item.excerpt,
    status: item.status ?? null,
    source_turns: item.source_turns ?? [],
    why_here:
      item.why_here ??
      (item.turn_id
        ? "Это точный текст вашей записи."
        : "Это название размышления."),
    parent_result_id: item.parent_result_id ?? null,
    ai_provenance: item.ai_provenance ?? null,
    correction_text: item.correction_text ?? null,
    related_context: item.related_context ?? [],
  });
  const resultTypeLabel = (item: SearchResult) =>
    (
      ({
        REFLECTION: "Размышление",
        USER_SOURCE: "Вы написали",
        UNKNOWN: "Неясно",
        CONTRADICTION: "Противоречие",
        FORMULATION: "Рабочая формулировка",
        AI_PROPOSAL: "Предложено AI",
      }) as const
    )[item.result_type];
  const searchMarkup = () => {
    const selected = [...selectedSearch.values()];
    const pack = showContextPack ? buildContextPack(selected) : null;
    const option = (
      value: string,
      label: string,
      selectedValue: string | undefined,
    ) =>
      `<option value="${value}"${value === selectedValue ? " selected" : ""}>${label}</option>`;
    const related = (item: SearchResult) =>
      item.related_context.length
        ? `<details class="related-context"><summary>Связанный контекст · ${item.related_context.length}</summary>${item.related_context.map((relation) => `<article><strong>${escape(relation.label)}</strong><small>${escape(relation.why_related)}</small><p>${escape(relation.text)}</p><button class="link-button" ${relation.turn_id ? `data-open-source="${escape(relation.session_id)}" data-turn-id="${escape(relation.turn_id)}"` : `data-open="${escape(relation.session_id)}"`}>Открыть источник</button></article>`).join("")}</details>`
        : `<p class="provenance-note">Связанного контекста по сохранённым связям нет.</p>`;
    const results = search?.results
      .map(normaliseSearchResult)
      .map(
        (item) =>
          `<article class="search-result search-result-${item.result_type.toLocaleLowerCase()}"><div><p class="result-type">${escape(resultTypeLabel(item))}</p><strong>${escape(item.session_title)}</strong><span class="status-pill ${item.session_state === "ACTIVE" ? "is-active" : ""}">${item.session_state === "ACTIVE" ? "Активно" : "Завершено"}</span>${item.status ? `<span class="status-pill">${escape(statusLabel(item.status))}</span>` : ""}<small>${escape(dateLabel(item.at))}${item.ai_provenance ? ` · AI: ${escape(item.ai_provenance.provider)} · ${escape(item.ai_provenance.actual_model)}` : ""}</small><p>${escape(item.excerpt)}</p>${item.correction_text ? `<p><strong>Уточнение:</strong> ${escape(item.correction_text)}</p>` : ""}<p class="provenance-note">Почему это здесь? ${escape(item.why_here)}</p>${item.source_turns.length ? `<details class="source-evidence"><summary>Показать источник · ${item.source_turns.length}</summary>${item.source_turns.map((turn) => `<article class="source-excerpt"><strong>Вы написали · запись ${turn.sequence}</strong><small>${escape(dateLabel(turn.created_at))}</small><p>${escape(turn.content)}</p><button class="link-button" data-open-source="${escape(item.session_id)}" data-turn-id="${escape(turn.turn_id)}">Открыть источник</button></article>`).join("")}</details>` : ""}${related(item)}</div><div class="search-actions"><label><input type="checkbox" data-context-select="${escape(item.result_id)}"${selectedSearch.has(item.result_id) ? " checked" : ""} /> В контекст</label><button ${item.turn_id ? `data-open-source="${escape(item.session_id)}" data-turn-id="${escape(item.turn_id)}"` : `data-open="${escape(item.session_id)}"`}>Открыть источник</button></div></article>`,
      )
      .join("");
    const packMarkup = pack
      ? `<section class="context-pack"><h2>Собранный контекст</h2><p>Только выбранные результаты и их точная сохранённая provenance. Ничего не отправляется и не сохраняется.</p><p>Выбрано: ${pack.selected.length} из ${CONTEXT_PACK_LIMIT}.</p>${pack.selected.map((item) => `<article><p class="result-type">${escape(resultTypeLabel(item))}</p><strong>${escape(item.session_title)}</strong><small>${escape(dateLabel(item.at))}${item.status ? ` · ${escape(statusLabel(item.status))}` : ""}${item.ai_provenance ? ` · AI: ${escape(item.ai_provenance.provider)} · ${escape(item.ai_provenance.actual_model)}` : ""}</small><p>${escape(item.text)}</p><p class="provenance-note">${escape(item.why_here)}</p><button class="link-button" data-context-remove="${escape(item.result_id)}">Убрать из контекста</button></article>`).join("")}<h3>Выбранные исходные записи</h3>${pack.source_turns.length ? pack.source_turns.map((turn) => `<article class="source-excerpt"><strong>Вы написали · ${escape(turn.session_title)} · запись ${turn.sequence}</strong><small>${escape(dateLabel(turn.created_at))}</small><p>${escape(turn.content)}</p></article>`).join("") : "<p>Среди выбранных результатов нет исходного текста.</p>"}</section>`
      : "";
    const loadedCount = search
      ? new Set(search.results.map((item) => item.result_id)).size
      : 0;
    const summary = search
      ? search.total_matches
        ? `Показано ${loadedCount} из ${search.total_matches}`
        : "Ничего не найдено."
      : "";
    return `<main class="product-shell">${nav()}<section class="product-home"><p>ЛИЧНЫЕ ЗАПИСИ</p><h1>Поиск и контекст</h1><p>Локальный поиск по вашим записям и сохранённым производным материалам. Источник и выводы показаны отдельно.</p></section><section class="card search-card"><form id="search-form" class="search-form"><label>Что найти <input id="search-query" required value="${escape(search?.query ?? "")}" /></label><label>Содержание <select id="search-content">${option("ALL", "Всё", search?.content)}${option("SOURCE", "Мои записи", search?.content)}${option("UNKNOWN", "Неясности", search?.content)}${option("CONTRADICTION", "Противоречия", search?.content)}${option("FORMULATION", "Формулировки", search?.content)}</select></label><label>Период <select id="search-period">${option("7D", "7 дней", search?.period)}${option("30D", "30 дней", search?.period)}${option("ALL", "Всё время", search?.period)}</select></label><label>Размышления <select id="search-state">${option("ALL", "Все", search?.state)}${option("ACTIVE", "Активные", search?.state)}${option("CLOSED", "Завершённые", search?.state)}</select></label><label>Формулировки <select id="search-formulation-status">${option("ALL", "Все статусы", search?.formulation_status)}${option("CURRENT", "Текущие", search?.formulation_status)}${option("PROPOSED", "Предложенные", search?.formulation_status)}${option("REJECTED", "Отклонённые", search?.formulation_status)}${option("SUPERSEDED", "Заменённые", search?.formulation_status)}</select></label><button class="primary">Найти</button></form>${search ? `<p class="search-summary">${summary}</p>${results || `<div class="calm-empty"><h2>Совпадений нет</h2><p>Попробуйте другое слово, период или фильтр.</p></div>`}${search.has_more ? `<div class="search-more"><button id="load-more-search">Показать ещё</button></div>` : ""}<div class="context-pack-actions"><button id="build-context-pack"${selected.length ? "" : " disabled"}>Собрать контекст (${selected.length}/${CONTEXT_PACK_LIMIT})</button>${selected.length ? '<button id="clear-context-pack">Очистить выбор</button>' : ""}</div>${packMarkup}` : "<p>Ищите по своим записям, неясностям, противоречиям и формулировкам.</p>"}</section>${noticeMarkup()}</main>`;
  };
  const senseSection = (title: string, content: string, empty: string) =>
    `<section class="sense-section"><h2>${title}</h2>${content || `<p class="calm-empty">${empty}</p>`}</section>`;
  const sourceRecords = (bundles: ExplorationBundle[]) =>
    bundles
      .map(
        (bundle) =>
          `<article class="source-record"><strong>${escape(bundle.session.title)}</strong><small>${escape(dateLabel(bundle.session.updated_at ?? bundle.session.created_at))} · ${bundle.session.turn_count} записей</small><button class="link-button" data-open="${escape(bundle.session.session_id)}">Открыть размышление</button></article>`,
      )
      .join("");
  const reported = (bundles: ExplorationBundle[]) =>
    bundles
      .flatMap((bundle) =>
        (bundle.session.turns ?? []).map(
          (turn) =>
            `<article class="reported-turn"><p>ВЫ НАПИСАЛИ</p><strong>${escape(bundle.session.title)} · запись ${turn.sequence}</strong><small>${escape(dateLabel(turn.created_at))}</small><p>${escape(turn.content)}</p><button class="link-button" data-open-source="${escape(bundle.session.session_id)}" data-turn-id="${escape(turn.turn_id)}">Открыть источник</button></article>`,
        ),
      )
      .join("");
  const sensemakingMarkup = () => {
    const bundles = (sensemaking ?? []).filter((bundle) => bundle.exploration);
    const contexts = (kind: "UNKNOWN" | "CONTRADICTION") =>
      bundles
        .flatMap((bundle) =>
          bundle
            .exploration!.context.filter((item) => item.kind === kind)
            .map((item) =>
              derivedCard(bundle, item.text, {
                label: kind === "UNKNOWN" ? "Неясно" : "Противоречие",
                detail: `${kind === "UNKNOWN" ? "Статус" : "Текущая релевантность"}: ${statusLabel(item.state)}`,
                sourceTurnIds: item.source_turn_ids,
                createdAt: item.created_at,
              }),
            ),
        )
        .join("");
    const formulations = bundles
      .flatMap((bundle) =>
        bundle.exploration!.formulations.map((item) =>
          formulationCard(bundle, item),
        ),
      )
      .join("");
    const hypotheses = bundles
      .flatMap((bundle) =>
        bundle.exploration!.hypotheses.map((item) =>
          hypothesisCard(bundle, item),
        ),
      )
      .join("");
    const chronology = bundles
      .flatMap((bundle) =>
        bundle.exploration!.formulations.map(
          (item) =>
            `<article class="history-event"><strong>${escape(dateLabel(item.updated_at ?? item.created_at))}</strong><span>${escape(({ CURRENT: "Формулировка стала текущей", PROPOSED: "Сохранено предложение", REJECTED: "Предложение отклонено", SUPERSEDED: "Предыдущая версия заменена" } as const)[item.status])}</span><p>${escape(item.summary)}</p>${item.parent_formulation_id ? "<small>Связана с предыдущей версией; исходная версия сохранена.</small>" : "<small>Исходная версия сохранена отдельно от записей.</small>"}</article>`,
        ),
      )
      .join("");
    const interviewDerived = interviewSessions.flatMap((session) => (session.derived_items ?? []).map((item) => `<article class="derived is-ai-proposal"><p>${escape(interviewKindLabel(item.kind))}</p><p>${escape(item.text)}</p><small>${escape(dateLabel(item.created_at))} · производное из AI-сессии, основания доступны в сессии.</small></article>`)).join("");
    const modelItems = (model?.items ?? []).filter((item) => item.current);
    const important = modelItems.filter((item) => item.state === "ACTIVE" || item.state === "CONTESTED").slice(0, 6);
    const modelPatterns = modelItems.filter((item) => item.kind === "PATTERN" && item.state === "ACTIVE");
    const modelHypotheses = modelItems.filter((item) => item.kind === "HYPOTHESIS" && (item.state === "ACTIVE" || item.state === "CONTESTED"));
    const modelContradictions = modelItems.filter((item) => item.kind === "CONTRADICTION" && item.state === "ACTIVE");
    const modelUnknowns = modelItems.filter((item) => item.kind === "UNKNOWN" && item.state === "ACTIVE");
    const modelRevisions = modelItems.filter((item) => item.history.length > 1 || item.challenges.length > 0 || !item.current);
    const hasMaterial = bundles.length > 0 || interviewDerived.length > 0 || modelItems.length > 0;
    return `<main class="product-shell">${nav()}<section class="product-home"><p>PERSONAL</p><h1>Картина</h1><p>Рабочая модель, источники и неясность показаны отдельно. Рабочие версии AI — не факты, и вы можете их оспорить.</p></section>${hasMaterial ? `<div class="sensemaking">${modelItems.length ? `${senseSection("Что сейчас кажется важным", important.map(modelCard).join(""), "Пока нет активных рабочих версий.")}${senseSection("Повторяющиеся паттерны", modelPatterns.map(modelCard).join(""), "Устойчивых повторяющихся паттернов пока не зафиксировано.")}${senseSection("Рабочие версии модели", modelHypotheses.map(modelCard).join(""), "Рабочих предположений пока нет — они появляются из AI-сессий при достаточных основаниях.")}${senseSection("Где данные не сходятся", modelContradictions.map(modelCard).join(""), "Неразрешённых противоречий нет. Это ценная информация, а не ошибка.")}${senseSection("Что пока неясно", modelUnknowns.map(modelCard).join(""), "Значимых неизвестных пока нет.")}${senseSection("Что изменилось в понимании", modelRevisions.map(modelCard).join(""), "История пересмотров появится, когда рабочие версии начнут меняться.")}` : ""}${interviewDerived ? senseSection("Из AI-исследований", interviewDerived, "") : ""}${senseSection("Исходные записи", sourceRecords(bundles), "Исходные размышления появятся после первой записи.")}${senseSection("Что я сообщил", reported(bundles), "В записях пока нет исходного текста.")}${senseSection("Неизвестно", contexts("UNKNOWN"), "Пока нет открытых неясностей.")}${senseSection("Противоречия", contexts("CONTRADICTION"), "Пока нет отмеченных противоречий.")}${senseSection("Рабочие предположения", hypotheses, "Рабочих предположений пока нет — они появляются после исследования записи.")}${senseSection("Рабочие формулировки", formulations, "Рабочие формулировки появятся после исследования записи.")}${senseSection("Исправления и история", chronology, "История изменений появится вместе с формулировками.")}</div>` : `<section class="card calm-empty"><h2>Картина появится постепенно</h2><p>Сохраните размышление или начните AI-сессию, чтобы видеть исходный текст, рабочие версии и неясности отдельно.</p></section>`}${noticeMarkup()}</main>`;
  };
  const longitudinalMarkup = () => {
    const view = buildPersonalLongitudinal(
      sensemaking ?? [],
      longitudinalPeriod,
      new Date(),
      model,
    );
    const periodLabel = (
      {
        "7d": "последние 7 дней",
        "30d": "последние 30 дней",
        all: "всё время",
      } as Record<LongitudinalPeriod, string>
    )[longitudinalPeriod];
    const sourceLinks = (
      sources: Array<{
        session_id: string;
        session_title: string;
        turn_ids: string[];
      }>,
    ) =>
      sources
        .map(
          (item) =>
            `<button class="link-button" data-open="${escape(item.session_id)}">Источник: ${escape(item.session_title)}${item.turn_ids.length ? ` · записей: ${item.turn_ids.length}` : ""}</button><button class="link-button" data-search-context="${escape(item.session_title)}">В поиск и контекст</button>`,
        )
        .join(" ");
    const formulationStatus = (status: string) =>
      (
        ({
          PROPOSED: "предложена",
          CURRENT: "текущая",
          SUPERSEDED: "заменена",
          REJECTED: "отклонена",
        }) as Record<string, string>
      )[status] ?? status;
    const understanding = view.understanding.length
      ? view.understanding
          .map(
            (item) =>
              `<article class="longitudinal-item"><small>${escape(dateLabel(item.at))}</small>${item.earlier ? `<p><strong>Раньше:</strong> ${escape(item.earlier)}</p>` : ""}<p><strong>Стало:</strong> ${escape(item.later)}</p><p>Изменилось: ${escape(item.changed)}</p></article>`,
          )
          .join("")
      : "<p>Рабочая модель понимания пока не менялась.</p>";
    const review = `<section class="card longitudinal-review"><h2>Обзор периода</h2><p>Счётчики помогают перейти к сохранённым материалам; это не оценка состояния, прогресса или человека.</p><dl><dt>Активных размышлений в периоде</dt><dd>${view.review.active_reflections}</dd><dt>Текущих формулировок, обновлённых в периоде</dt><dd>${view.review.current_formulations.length}</dd><dt>Новых неясностей</dt><dd>${view.review.new_unknowns}</dd><dt>Остаётся открытым</dt><dd>${view.review.unresolved_unknowns} неясностей · ${view.review.unresolved_contradictions} противоречий</dd><dt>Повторяющихся точных фраз</dt><dd>${view.review.recurring_themes}</dd></dl>${view.review.current_formulations.length ? `<div class="longitudinal-inline">${view.review.current_formulations.map((item) => `<p>Версия ${item.version} · ${escape(item.summary)}</p>`).join("")}</div>` : "<p>Текущих формулировок, обновлённых в выбранный период, нет.</p>"}</section>`;
    const timelineByDay = new Map<string, typeof view.timeline>();
    for (const event of view.timeline) {
      const day = dateLabel(event.at);
      timelineByDay.set(day, [...(timelineByDay.get(day) ?? []), event]);
    }
    const timeline =
      [...timelineByDay.entries()]
        .map(
          ([day, events]) =>
            `<section class="longitudinal-day"><h3>${escape(day)}</h3>${events.map((event) => `<article class="longitudinal-event"><p>${escape(event.detail)}</p>${sourceLinks([event])}</article>`).join("")}</section>`,
        )
        .join("") || `<p>В выбранный период сохранённых событий нет.</p>`;
    const themes = view.themes.length
      ? view.themes
          .map(
            (theme) =>
              `<article class="longitudinal-item"><h3>${escape(theme.label)}</h3><p>Точное повторение сохранённой фразы в ${theme.session_count} размышлениях · последнее: ${escape(dateLabel(theme.latest_at))}.</p><p class="derived-warning">Это группа точных фраз с указанными источниками, а не вывод о черте, причине или диагнозе.</p><details><summary>Показать источники</summary>${sourceLinks(theme.sources)}</details></article>`,
          )
          .join("")
      : "<p>Точных повторов в двух разных размышлениях пока нет.</p>";
    const changes = view.changes.length
      ? view.changes
          .map(
            (change) =>
              `<article class="longitudinal-item"><p><strong>${escape(change.earlier)}</strong></p><p><strong>${escape(change.later)}</strong></p><p>Изменилось: ${escape(change.changed)}</p>${sourceLinks([change])}</article>`,
          )
          .join("")
      : "<p>Сохранённых переходов между версиями пока нет.</p>";
    const lineages = view.lineages.length
      ? view.lineages
          .map(
            (lineage) =>
              `<article class="longitudinal-item"><h3>${escape(lineage.session_title)}</h3>${lineage.items.map((item) => `<section class="formulation-version"><strong>Версия ${item.version} · ${escape(formulationStatus(item.status))}</strong><small>${escape(dateLabel(item.created_at))}${item.ai_provenance ? ` · AI: ${escape(item.ai_provenance.provider)} / ${escape(item.ai_provenance.actual_model)}` : " · происхождение: локальное производное представление"}</small><p>${escape(item.summary)}</p>${item.correction_text ? `<p>Уточнение пользователя: ${escape(item.correction_text)}</p>` : ""}${item.ai_provenance ? '<p class="derived-warning">AI-предложение не является доказательством или фактом; неопределённость сохранена в тексте предложения.</p>' : ""}</section>`).join('<p class="lineage-arrow" aria-hidden="true">→</p>')}${sourceLinks([lineage])}</article>`,
          )
          .join("")
      : "<p>Версий рабочих формулировок пока нет.</p>";
    const unresolved = view.unresolved.length
      ? view.unresolved
          .map(
            (item) =>
              `<article class="longitudinal-item"><h3>${item.kind === "UNKNOWN" ? "Неясность" : "Противоречие"}</h3><p>${escape(item.text)}</p><small>Впервые: ${escape(dateLabel(item.first_seen))} · последняя связанная активность: ${escape(dateLabel(item.latest_activity))}</small><p class="derived-warning">Состояние остаётся открытым без срока, штрафа или предположения о том, что более поздняя запись разрешает его.</p>${sourceLinks(item.sources)}</article>`,
          )
          .join("")
      : "<p>Открытых неясностей или противоречий нет.</p>";
    const proposed = view.proposed.length
      ? view.proposed
          .map(
            (item) =>
              `<article class="longitudinal-item"><h3>Предложенная формулировка v${item.version}${item.ai ? " · AI" : ""}</h3><p>${escape(item.summary)}</p><small>${escape(dateLabel(item.at))}</small>${sourceLinks([item])}</article>`,
          )
          .join("")
      : "<p>Необработанных предложенных формулировок нет.</p>";
    return `<main class="product-shell longitudinal-shell">${nav()}<section class="product-home"><p>PERSONAL · ТОЛЬКО ЧТЕНИЕ</p><h1>Во времени</h1><p>Хронология и сводка строятся из сохранённых записей и состояний. Здесь нет диагноза, оценки или скрытой интерпретации.</p><label class="period-picker">Период <select id="longitudinal-period"><option value="7d"${longitudinalPeriod === "7d" ? " selected" : ""}>Последние 7 дней</option><option value="30d"${longitudinalPeriod === "30d" ? " selected" : ""}>Последние 30 дней</option><option value="all"${longitudinalPeriod === "all" ? " selected" : ""}>Всё время</option></select></label><p class="longitudinal-period-note">Показано: ${periodLabel}.</p></section>${review}<section class="sense-section"><h2>Как менялось понимание</h2><p>Здесь показано, как менялась рабочая модель PSYCHE — это не утверждение, что изменились вы сами. Предыдущие версии сохраняются.</p>${understanding}</section><section class="sense-section"><h2>Что изменилось</h2><p>Показаны только сохранённые переходы версий; система не делает вывода об улучшении или ухудшении.</p>${changes}</section><section class="sense-section"><h2>Остаётся открытым</h2><p>Открытые записи остаются видимыми без срока и без штрафа за давность.</p>${unresolved}${proposed}</section><section class="sense-section"><h2>Эволюция формулировок</h2><p>Версии, исправления, статусы и происхождение сохранены отдельно от исходных записей.</p>${lineages}</section><section class="sense-section"><h2>Повторяющиеся темы</h2><p>Группировка прозрачна: только точные повторения сохранённых фраз, привязанные к источникам.</p>${themes}</section><details class="sense-section longitudinal-timeline"><summary>Хронология · ${view.timeline.length} ${view.timeline.length === 1 ? "событие" : "событий"}</summary><p>Только события, записанные в продукте; это не восстановленная хронология жизни.</p>${timeline}</details>${noticeMarkup()}</main>`;
  };
  const privacyMarkup = () => {
    const ai =
      status?.runtime_profile === "LOCAL_PERSONAL_BOUNDED_OPENAI" ||
      status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI";
    const historyPermission = status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI" ? `<section class="card"><p>AI-ИССЛЕДОВАНИЕ · ИСТОРИЧЕСКИЙ КОНТЕКСТ</p><h2>Какие прошлые записи AI-сессия может использовать</h2><p>${interviewEligibility === null ? "Проверяем локальные разрешения…" : `Сейчас разрешено: ${interviewEligibility} записей.`} Выберите или отзовите конкретные записи в их карточках истории. Невыбранные записи остаются локальными; разрешение действует только для этой цели и OpenAI.</p><button data-route="history">Открыть историю и выбрать записи</button></section>` : "";
    return `<main class="product-shell">${nav()}<section class="product-home"><p>PERSONAL</p><h1>Настройки</h1><p>Состояние локального режима и инструменты восстановления.</p></section><section class="card settings-card"><p>ПРИВАТНОСТЬ И ЛОКАЛЬНЫЙ РЕЖИМ</p><h2>Ваши данные остаются под вашим контролем</h2><dl class="friendly-status"><dt>Обработка данных</dt><dd>Локально${ai ? " — по умолчанию" : ""}</dd><dt>Облачная передача</dt><dd>${ai ? "OpenAI — только после явного подтверждения" : "Отключена"}</dd><dt>Сетевые подключения</dt><dd>${ai ? "Только один подтверждённый запрос OpenAI" : "Отключены"}</dd><dt>Фоновая передача</dt><dd>Отключена</dd><dt>Телеметрия</dt><dd>Отключена</dd></dl>${ai ? `<section><h2>OpenAI</h2><p>${aiConfigured ? "Настроен" : "Не настроен"}</p><form id="ai-key-form"><label>${aiConfigured ? "Заменить ключ" : "Настроить ключ"}<input id="ai-key" type="password" required autocomplete="off" /></label><button>Сохранить ключ</button></form>${aiConfigured ? '<button id="ai-key-delete" class="danger">Удалить ключ</button>' : ""}</section>` : ""}<details><summary>Технические сведения</summary><dl><dt>Идентификатор сборки</dt><dd>${escape(status?.build_id ?? "Недоступен")}</dd><dt>Профиль</dt><dd>${escape(status?.runtime_profile)}</dd><dt>REAL_DATA_GATE</dt><dd>${escape(status?.real_data_gate)}</dd><dt>Сеть</dt><dd>${escape(status?.network)}</dd><dt>Входящий слушатель</dt><dd>${escape(status?.inbound_listener)}</dd><dt>Провайдер</dt><dd>${escape(status?.outbound_provider)}</dd></dl></details></section>${historyPermission}${noticeMarkup()}</main>`;
  };
  const recoveryMarkup = () =>
    `<main class="product-shell">${nav()}<section class="product-home"><p>РЕЗЕРВНОЕ КОПИРОВАНИЕ</p><h1>Восстановление и экспорт</h1><p>Инструменты работают с локальным хранилищем Personal.</p></section><div class="grid recovery-grid"><section class="card"><h2>Состояние резервного копирования</h2><p>${recovery ? `Допуск к Personal: ${escape(String(recovery.local_personal ?? "Недоступен"))}. Смена ключа: ${escape(String(recovery.rotation ?? "Недоступно"))}.` : "Состояние ещё не проверялось в этом окне."}</p><button id="recovery-status">Обновить состояние</button></section><section class="card"><h2>Создать резервную копию</h2><p>Резервная копия считается готовой только после аутентификации и отдельного проверочного восстановления.</p><form id="backup-form"><label>Секрет восстановления <input id="backup-secret" type="password" required /></label><button class="primary">Создать и проверить</button></form></section><section class="card"><h2>Экспорт владельца</h2><p>Создаёт зашифрованный экспорт, доступный только владельцу.</p><form id="export-form"><label>Секрет восстановления <input id="export-secret" type="password" required /></label><button>Экспорт владельца</button></form></section></div><section class="card recovery-verify"><h2>Проверить резервную копию</h2><p>Проверка создаёт отдельную копию и никогда не заменяет текущее хранилище автоматически. Сверьте дату и поколение: старая резервная копия может не включать поздние исправления или удаления. Удаление активных данных не удаляет уже созданные исторические резервные копии.</p><form id="restore-form"><label>Идентификатор резервной копии <input id="restore-backup-id" required /></label><label>Секрет восстановления <input id="restore-secret" type="password" required /></label><button>Проверить резервную копию</button></form></section>${noticeMarkup()}</main>`;
  function render() {
    if (!status) {
      host.innerHTML =
        "<main><p>Загружаем состояние личного хранилища…</p></main>";
      return;
    }
    if (status.local_personal === "NOT_ADMITTED") {
      host.innerHTML = `<main class="unlock"><p>PSYCHE OS PERSONAL</p><h1>Хранилище пока недоступно</h1><p>Это устройство ещё не допущено к личному хранилищу. Данные не создавались и не передавались.</p>${noticeMarkup()}</main>`;
      return;
    }
    if (status.locked) {
      const setup = status.setup_required === true;
      if (setup && !generatedRecoverySecret)
        generatedRecoverySecret = generateRecoverySecret();
      host.innerHTML = `<main class="unlock"><p>PSYCHE OS PERSONAL</p><h1>${setup ? "Создайте защищённое личное пространство" : "Ваше личное пространство защищено"}</h1><p>Данные хранятся локально${status.runtime_profile === "LOCAL_PERSONAL_BOUNDED_OPENAI" ? "; OpenAI получает только явно выбранный и подтверждённый текст" : ", облачная передача отключена"}.</p>${setup ? `<p>Приложение создало сильный секрет восстановления. Скопируйте и сохраните его вне этого устройства: без него восстановление невозможно.</p><label>Секрет восстановления <input id="unlock-secret" type="text" value="${generatedRecoverySecret}" readonly autocomplete="off" /></label><label><input id="recovery-saved" type="checkbox" required /> Я сохранил(а) этот секрет</label>` : `<label>Секрет хранилища <input id="unlock-secret" type="password" required autofocus autocomplete="current-password" /></label>`}<form id="unlock-form"><button class="primary">${setup ? "Создать хранилище" : "Открыть хранилище"}</button></form>${noticeMarkup()}</main>`;
      submit("#unlock-form", async () => {
        if (
          setup &&
          !host.querySelector<HTMLInputElement>("#recovery-saved")!.checked
        )
          throw new Error("Подтвердите, что сохранили секрет восстановления.");
        await api.unlock(
          host.querySelector<HTMLInputElement>("#unlock-secret")!.value,
        );
        generatedRecoverySecret = null;
        await refresh();
        await loadSensemaking();
        notice = "Хранилище открыто.";
      });
      return;
    }
    host.innerHTML =
      route === "interview"
        ? interviewMarkup()
        : route === "detail"
          ? detailMarkup()
          : route === "sleep"
            ? sleepMarkup()
          : route === "history"
            ? historyMarkup()
            : route === "search"
              ? searchMarkup()
              : route === "sensemaking"
                ? sensemakingMarkup()
                : route === "longitudinal"
                  ? longitudinalMarkup()
                  : route === "privacy"
                    ? privacyMarkup()
                    : route === "recovery"
                      ? recoveryMarkup()
                      : homeMarkup();
    bindCommon();
    host
      .querySelector<HTMLSelectElement>("#longitudinal-period")
      ?.addEventListener("change", (event) => {
        longitudinalPeriod = (event.currentTarget as HTMLSelectElement)
          .value as LongitudinalPeriod;
        render();
      });
    if (
      route === "privacy" &&
      (status.runtime_profile === "LOCAL_PERSONAL_BOUNDED_OPENAI" ||
        status.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI") &&
      aiConfigured === null
    )
      void act(async () => {
        aiConfigured = (await api.aiProviderStatus()).configured;
        if (status?.runtime_profile === "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI")
          interviewEligibility = (await api.aiInterviewStatus()).eligible_source_count;
      });
    submit("#ai-key-form", async () => {
      await api.aiProviderConfigure(
        host.querySelector<HTMLInputElement>("#ai-key")!.value,
      );
      aiConfigured = true;
      notice = "Ключ сохранён локально и защищён Windows.";
    });
    host.querySelector("#ai-key-delete")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          await api.aiProviderDelete();
          aiConfigured = false;
          notice = "Ключ удалён.";
        }),
    );
    submit("#quick-capture-form", async () => {
      const text = host
        .querySelector<HTMLTextAreaElement>("#quick-capture-text")!
        .value.trim();
      if (!text) return;
      const title =
        host
          .querySelector<HTMLInputElement>("#quick-capture-title")!
          .value.trim() || "Быстрая запись";
      const created = await api.reflectionCreate(title);
      await api.reflectionAddTurn(created.session_id, text);
      await refresh();
      await loadSensemaking();
      route = "home";
      notice = "Запись сохранена в истории.";
    });
    host
      .querySelector<HTMLFormElement>("[data-change-observation]")
      ?.addEventListener("submit", (event) => {
        event.preventDefault();
        void act(async () => {
          const form = event.currentTarget as HTMLFormElement;
          const content = form.querySelector<HTMLTextAreaElement>("textarea")!.value.trim();
          if (!content) return;
          await api.aiChangeObserve(
            form.dataset.changeObservation!,
            content,
            form.querySelector<HTMLSelectElement>("select")!.value,
          );
          changePlans = (await api.aiChangeList()).plans;
          notice = "Наблюдение сохранено локально как ваша запись.";
        });
      });
    host.querySelector<HTMLButtonElement>("[data-change-stop]")?.addEventListener("click", (event) =>
      void act(async () => {
        await api.aiChangeControl((event.currentTarget as HTMLButtonElement).dataset.changeStop!, "STOP");
        changePlans = (await api.aiChangeList()).plans;
        notice = "Проверка остановлена. Это не является выводом о вас.";
      }),
    );
    host.querySelector<HTMLButtonElement>("[data-change-activate]")?.addEventListener("click", (event) =>
      void act(async () => {
        await api.aiChangeControl((event.currentTarget as HTMLButtonElement).dataset.changeActivate!, "ACTIVATE");
        changePlans = (await api.aiChangeList()).plans;
        notice = "Проверка начата локально.";
      }),
    );
    host.querySelector<HTMLButtonElement>("[data-change-dismiss]")?.addEventListener("click", (event) =>
      void act(async () => {
        await api.aiChangeControl((event.currentTarget as HTMLButtonElement).dataset.changeDismiss!, "DISMISS");
        changePlans = (await api.aiChangeList()).plans;
        notice = "Предложение отложено.";
      }),
    );
    host.querySelector<HTMLButtonElement>("[data-change-observations-allow]")?.addEventListener("click", (event) =>
      void act(async () => {
        await api.aiChangeAllowObservations((event.currentTarget as HTMLButtonElement).dataset.changeObservationsAllow!, true);
        changePlans = (await api.aiChangeList()).plans;
        notice = "Точные наблюдения разрешены для AI-разбора.";
      }),
    );
    host.querySelector<HTMLButtonElement>("[data-change-observations-revoke]")?.addEventListener("click", (event) =>
      void act(async () => {
        await api.aiChangeAllowObservations((event.currentTarget as HTMLButtonElement).dataset.changeObservationsRevoke!, false);
        changePlans = (await api.aiChangeList()).plans;
        notice = "Разрешение для этих наблюдений отозвано.";
      }),
    );
    host.querySelector<HTMLButtonElement>("[data-change-review]")?.addEventListener("click", (event) =>
      void act(async () => {
        interview = await api.aiChangeStartReview((event.currentTarget as HTMLButtonElement).dataset.changeReview!);
        route = "interview";
        notice = "Для разбора потребуется отдельное согласие на AI-сессию.";
      }),
    );
    host.querySelector("#home-start-topic")?.addEventListener("click", () =>
      void act(async () => {
        const topic = window.prompt("Что вы хотите исследовать?");
        if (!topic?.trim()) return;
        interview = await api.aiInterviewStart(topic.trim());
        route = "interview";
      }),
    );
    host.querySelector("#home-new-topic")?.addEventListener("click", () =>
      void act(async () => {
        const topic = window.prompt("Что вы хотите исследовать по-другому?");
        if (!topic?.trim()) return;
        interview =
          interview && interview.state !== "COMPLETED"
            ? await api.aiInterviewControl(
                interview.interview_session_id,
                "CHANGE_TOPIC",
                topic.trim(),
              )
            : await api.aiInterviewStart(topic.trim());
        route = "interview";
      }),
    );
    submit("#search-form", async () => {
      const query = host
        .querySelector<HTMLInputElement>("#search-query")!
        .value.trim();
      if (!query) return;
      selectedSearch.clear();
      showContextPack = false;
      searchRequest = {
        query,
        filters: {
          state: host.querySelector<HTMLSelectElement>("#search-state")!
            .value as "ALL" | "ACTIVE" | "CLOSED",
          content: host.querySelector<HTMLSelectElement>("#search-content")!
            .value as SearchView["content"],
          period: host.querySelector<HTMLSelectElement>("#search-period")!
            .value as SearchView["period"],
          formulationStatus: host.querySelector<HTMLSelectElement>(
            "#search-formulation-status",
          )!.value as SearchView["formulation_status"],
        },
      };
      search = await api.reflectionSearch(
        query,
        searchRequest.filters,
        SEARCH_PAGE_LIMIT,
        0,
      );
    });
    host.querySelector("#load-more-search")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          if (!search || !searchRequest) return;
          const offset = search.offset + search.returned_count;
          const page = await api.reflectionSearch(
            searchRequest.query,
            searchRequest.filters,
            SEARCH_PAGE_LIMIT,
            offset,
          );
          search = mergeSearchPage(search, page);
        }),
    );
    host
      .querySelectorAll<HTMLInputElement>("[data-context-select]")
      .forEach((box) =>
        box.addEventListener("change", () => {
          const result = search?.results.find(
            (item) => item.result_id === box.dataset.contextSelect,
          );
          if (!result) return;
          if (box.checked && selectedSearch.size < CONTEXT_PACK_LIMIT)
            selectedSearch.set(result.result_id, result);
          else selectedSearch.delete(result.result_id);
          render();
        }),
      );
    host.querySelector("#build-context-pack")?.addEventListener("click", () => {
      showContextPack = true;
      render();
    });
    host.querySelector("#clear-context-pack")?.addEventListener("click", () => {
      selectedSearch.clear();
      showContextPack = false;
      render();
    });
    host
      .querySelectorAll<HTMLButtonElement>("[data-context-remove]")
      .forEach((button) =>
        button.addEventListener("click", () => {
          selectedSearch.delete(button.dataset.contextRemove!);
          showContextPack = selectedSearch.size > 0;
          render();
        }),
      );
    host.querySelector("#recovery-status")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          recovery = (await api.personalRecoveryStatus()) as Record<
            string,
            unknown
          >;
          notice = "Состояние обновлено.";
        }),
    );
    submit("#backup-form", async () => {
      if (
        !window.confirm(
          "Создать и отдельно проверить зашифрованную резервную копию текущего хранилища?",
        )
      )
        return;
      const value = (await api.personalBackup(
        host.querySelector<HTMLInputElement>("#backup-secret")!.value,
      )) as { backup_id?: string; created_at?: string };
      notice = value.backup_id
        ? `Резервная копия проверена и восстанавливаема. Идентификатор: ${value.backup_id}${value.created_at ? `. Дата: ${value.created_at}` : ""}`
        : "Резервная копия проверена.";
    });
    submit("#export-form", async () => {
      if (
        !window.confirm("Создать зашифрованный экспорт только для владельца?")
      )
        return;
      const value = (await api.personalExportOwner(
        host.querySelector<HTMLInputElement>("#export-secret")!.value,
      )) as { export_id?: string };
      notice = `Экспорт владельца создан${value.export_id ? `. Идентификатор: ${value.export_id}` : ""}.`;
    });
    submit("#restore-form", async () => {
      if (
        !window.confirm(
          "Проверить резервную копию в отдельной копии? Текущее хранилище не изменится.",
        )
      )
        return;
      const value = (await api.personalRestoreIsolated(
        host.querySelector<HTMLInputElement>("#restore-backup-id")!.value,
        host.querySelector<HTMLInputElement>("#restore-secret")!.value,
      )) as { candidate_id?: string; freshness?: string; created_at?: string };
      notice = value.candidate_id
        ? `Отдельная копия проверена: ${value.candidate_id}. Поколение: ${value.freshness ?? "неизвестно"}. Дата: ${value.created_at ?? "неизвестна"}.`
        : "Отдельная копия проверена.";
    });
    if (route === "detail") bindDetail();
    if (route === "interview") bindInterview();
  }
  function bindInterview() {
    host.querySelector("#interview-start")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          interview = await api.aiInterviewStart();
        }),
    );
    host.querySelector("#interview-consent")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          if (!interview) return;
          const provider = await api.aiInterviewStatus();
          if (
            !provider.policy_enabled &&
            !window.confirm(
              "Разрешить AI-сессии передавать ограниченный локально выбранный материал в OpenAI?",
            )
          )
            return;
          if (!provider.policy_enabled) await api.aiInterviewPolicy(true);
          if (!provider.configured) {
            route = "privacy";
            notice = "Сначала добавьте ключ OpenAI в настройках.";
            return;
          }
          if (
            !window.confirm(
              "Во время этой AI-сессии PSYCHE может выбрать ограниченный релевантный материал, разрешённый локальной политикой, и передать его в OpenAI. Всё хранилище не передаётся; фоновых вызовов нет; передачу можно остановить и просмотреть.",
            )
          )
            return;
          await api.aiInterviewGrantConsent(interview.interview_session_id);
          interview = await api.aiInterviewFirstQuestion(
            interview.interview_session_id,
          );
        }),
    );
    host.querySelector("#interview-next")?.addEventListener(
      "click",
      () =>
        void act(async () => {
          if (interview)
            interview = await api.aiInterviewFirstQuestion(
              interview.interview_session_id,
            );
        }),
    );
    submit("#interview-answer", async () => {
      if (!interview) return;
      const content = host
        .querySelector<HTMLTextAreaElement>("#interview-answer-text")!
        .value.trim();
      if (!content) return;
      interview = await api.aiInterviewSubmit(
        interview.interview_session_id,
        crypto.randomUUID(),
        content,
      );
    });
    host
      .querySelectorAll<HTMLButtonElement>("[data-interview-control]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void act(async () => {
              if (!interview) return;
              const action = button.dataset.interviewControl!;
              const topic =
                action === "CHANGE_TOPIC"
                  ? window.prompt("Что вы хотите исследовать?")
                  : null;
              if (action === "CHANGE_TOPIC" && !topic) return;
              interview = await api.aiInterviewControl(
                interview.interview_session_id,
                action,
                topic,
              );
            }),
        ),
      );
    host.querySelector("#interview-basis")?.addEventListener(
      "toggle",
      () => {
        const details = host.querySelector<HTMLDetailsElement>("#interview-basis");
        if (!details || !details.open || details.dataset.loaded) return;
        const body = details.querySelector("[data-basis-body]");
        if (!body) return;
        details.dataset.loaded = "1";
        api.aiInterviewDisclosure(details.dataset.attempt!)
          .then((receipt) => {
            if (!details.isConnected || !body.isConnected) return;
            body.innerHTML = receipt.items.length
              ? receipt.items
                  .map((item) => {
                    const origin =
                      item.session_id && item.session_id === interview?.source_session_id
                        ? "из текущей сессии"
                        : "из более ранней истории";
                    return `<article class="source-excerpt"><strong>Вы написали</strong><small>${escape(dateLabel(item.created_at))}${item.session_title ? ` · ${escape(item.session_title)}` : ""} · ${origin}</small><p>${escape(item.content)}</p></article>`;
                  })
                  .join("")
              : "Основание: текущая сессия и выбранное направление. Конкретные записи не использовались.";
          })
          .catch(() => {
            if (!details.isConnected || !body.isConnected) return;
            body.textContent = "Не удалось загрузить основания. Попробуйте ещё раз.";
            delete details.dataset.loaded;
          });
      },
    );
    host
      .querySelectorAll<HTMLButtonElement>("[data-disclosure]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void act(async () => {
              const receipt = await api.aiInterviewDisclosure(
                button.dataset.disclosure!,
              );
              const target = host.querySelector("#interview-disclosure");
              if (target)
                target.innerHTML = `<h3>Исходные записи, переданные AI</h3>${receipt.items.map((item) => `<article class="source-excerpt"><strong>${escape(item.alias)}</strong><p>${escape(item.content)}</p></article>`).join("") || "<p>Исходные записи не передавались.</p>"}<h3>Рабочая модель, переданная AI</h3>${(receipt.model_items ?? []).map((item) => `<article class="source-excerpt"><strong>${escape(modelKindLabel(item.kind))}</strong><small>${escape(temporalLabel(item.temporal_scope))}</small><p>${escape(item.text)}</p></article>`).join("") || "<p>Рабочая модель не передавалась.</p>"}`;
            }),
        ),
      );
  }
  function bindDetail() {
    host.querySelector("#close-reflection")?.addEventListener("click", () => {
      if (current)
        void act(async () => {
          await api.reflectionClose(current!.session_id);
          await open(current!.session_id);
        });
    });
    host.querySelector("#delete-reflection")?.addEventListener("click", () => {
      if (
        current &&
        window.confirm(
          "Удалить это размышление и все его записи? Это действие нельзя отменить.",
        )
      )
        void act(async () => {
          await api.reflectionDelete(current!.session_id);
          current = null;
          sourceTurnId = null;
          route = "history";
          await refresh();
          notice = "Размышление удалено.";
        });
    });
    submit("#add-turn", async () => {
      const text = host
        .querySelector<HTMLTextAreaElement>("#reflection-turn")!
        .value.trim();
      if (text && current) {
        await api.reflectionAddTurn(current.session_id, text);
        await open(current.session_id);
      }
    });
    host.querySelector("#start-exploration")?.addEventListener("click", () => {
      if (current)
        void act(async () => {
          exploration = await api.explorationStart(current!.session_id);
        });
    });
    host
      .querySelector("#propose-formulation")
      ?.addEventListener("click", () => {
        if (current)
          void act(async () => {
            await api.formulationPropose(current!.session_id);
            await open(current!.session_id);
          });
      });
    submit("#ai-selection", async () => {
      if (!current) return;
      const selected = [
        ...host.querySelectorAll<HTMLInputElement>(
          'input[name="ai-turn"]:checked',
        ),
      ].map((item) => item.value);
      aiPreview = await api.aiFormulationPrepare(current.session_id, selected);
      notice = "Проверьте точный текст выбранных записей перед отправкой.";
    });
    submit("#interview-source-policy", async () => {
      const selected = [
        ...host.querySelectorAll<HTMLInputElement>('input[name="interview-source-turn"]:checked'),
      ].map((item) => item.value);
      if (!selected.length) return;
      await api.aiInterviewSourcePolicy(selected, true);
      interviewEligibility = (await api.aiInterviewStatus()).eligible_source_count;
      notice = "Выбранные записи разрешены только для AI-исследования OpenAI.";
    });
    host.querySelector("#interview-source-revoke")?.addEventListener("click", () =>
      void act(async () => {
        const selected = [...host.querySelectorAll<HTMLInputElement>('input[name="interview-source-turn"]:checked')].map((item) => item.value);
        if (!selected.length) return;
        await api.aiInterviewSourcePolicy(selected, false);
        interviewEligibility = (await api.aiInterviewStatus()).eligible_source_count;
        notice = "Разрешение на передачу выбранных записей отозвано.";
      }),
    );
    const applySourcePolicyToAll = async (enabled: boolean) => {
      if (!current) return;
      const turnIds = (current.turns ?? [])
        .filter((turn) => turn.actor === "USER")
        .map((turn) => turn.turn_id);
      if (!turnIds.length) {
        notice = "В этом размышлении пока нет ваших записей.";
        return;
      }
      // Backend rejects any policy call with more than MAX_SOURCE_ITEMS=12
      // turn ids, so apply the exact per-turn policy in bounded batches.
      const batchSize = 12;
      for (let offset = 0; offset < turnIds.length; offset += batchSize) {
        await api.aiInterviewSourcePolicy(
          turnIds.slice(offset, offset + batchSize),
          enabled,
        );
      }
      interviewEligibility = (await api.aiInterviewStatus()).eligible_source_count;
      notice = enabled
        ? "Все записи этого размышления разрешены только для AI-исследования OpenAI."
        : "Разрешение на передачу всех записей этого размышления отозвано.";
    };
    host.querySelector("#interview-source-allow-all")?.addEventListener("click", () =>
      void act(() => applySourcePolicyToAll(true)),
    );
    host.querySelector("#interview-source-revoke-all")?.addEventListener("click", () =>
      void act(() => applySourcePolicyToAll(false)),
    );
    host.querySelector("#ai-cancel")?.addEventListener("click", () => {
      aiPreview = null;
      notice = "Отправка в OpenAI отменена.";
      render();
    });
    host.querySelector("#ai-send")?.addEventListener("click", () => {
      if (aiPreview && current)
        void act(async () => {
          await api.aiFormulationExecute(
            aiPreview!.interaction_id,
            aiPreview!.preview_id,
          );
          aiPreview = null;
          await open(current!.session_id);
          notice = "AI-предложение сохранено. Оно не является фактом.";
        });
    });
    submit("#answer-question", async () => {
      const question = exploration?.next_question,
        answer = host
          .querySelector<HTMLTextAreaElement>("#question-answer")!
          .value.trim();
      if (question && answer)
        exploration = await api.explorationAnswer(question.question_id, answer);
    });
    host.querySelector("#skip-question")?.addEventListener("click", () => {
      const question = exploration?.next_question;
      if (question)
        void act(async () => {
          exploration = await api.explorationSkip(question.question_id);
        });
    });
    host.querySelectorAll<HTMLFormElement>("[data-correct]").forEach((form) =>
      form.addEventListener("submit", (event) => {
        event.preventDefault();
        const text = form
          .querySelector<HTMLTextAreaElement>("textarea")!
          .value.trim();
        if (text)
          void act(async () => {
            await api.formulationCorrect(form.dataset.correct!, text);
            await open(current!.session_id);
          });
      }),
    );
    host
      .querySelectorAll<HTMLButtonElement>("[data-accept]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void act(async () => {
              await api.formulationAccept(button.dataset.accept!);
              await open(current!.session_id);
            }),
        ),
      );
    host
      .querySelectorAll<HTMLButtonElement>("[data-reject]")
      .forEach((button) =>
        button.addEventListener(
          "click",
          () =>
            void act(async () => {
              await api.formulationReject(button.dataset.reject!);
              await open(current!.session_id);
            }),
        ),
      );
  }
  render();
  try {
    const currentStatus = await refresh();
    if (!currentStatus.locked) await loadSensemaking();
    render();
  } catch (error) {
    status = {
      runtime_profile: "LOCAL_PERSONAL",
      real_data_gate: "CLOSED",
      local_personal: "ADMISSION_AVAILABLE",
      locked: true,
      inbound_listener: "NONE",
      outbound_provider: "NOT_CONFIGURED",
      network: "OFFLINE_NO_LISTENER",
      privacy: {
        core_processing_location: "LOCAL",
        cloud_storage: "DISABLED",
        cloud_disclosure: "NEVER_CLOUD",
        telemetry: "OFF",
      },
    };
    notice = `Не удалось загрузить состояние: ${errorText(error)}`;
    render();
  }
}
