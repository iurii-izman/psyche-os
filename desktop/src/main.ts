import { desktopApi, type ActionAnchorType, type ActionOption, type DesktopApi, type ExplorationView, type ReflectionSessionView, type StatusView } from "./api";
import { buildAnalyticalWorkspace, presentDimension, presentFormulationStatus, presentUnknownState } from "./analytical-workspace";
import { buildSessionSynthesis } from "./synthesis-action-workspace";
import { buildLongitudinalWorkspace, compareSessions, type LongitudinalSessionBundle } from "./longitudinal-workspace";
import { buildReturnWorkspace, type ReturnCandidate, type ReturnCandidateCategory } from "./return-workspace";
import { buildFollowUpWorkspace } from "./follow-up-workspace";
import { buildProductJourney, presentJourneyState } from "./product-journey";
import { presentKey, presentValue, t, type TranslationKey } from "./i18n";

type Data = Record<string, unknown>;

function el<K extends keyof HTMLElementTagNameMap>(tag: K, text?: string): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function field(labelText: string, id: string, type = "text"): [HTMLLabelElement, HTMLInputElement] {
  const label = el("label", labelText);
  label.htmlFor = id;
  const input = el("input");
  input.id = id;
  input.name = id;
  input.type = type;
  return [label, input];
}

function button(text: string, action: () => Promise<void>, className = "secondary"): HTMLButtonElement {
  const node = el("button", text);
  node.type = "button";
  node.className = className;
  node.addEventListener("click", () => void action());
  return node;
}

function renderResult(region: HTMLElement, value: Data, message: string): void {
  region.replaceChildren();
  const heading = el("strong", message);
  region.append(heading);
  const list = el("dl");
  for (const [key, raw] of Object.entries(value)) {
    const dt = el("dt", presentKey(key));
    const dd = el("dd", presentValue(raw));
    list.append(dt, dd);
  }
  region.append(list);
}

function safeError(region: HTMLElement, error: unknown): void {
  const code = typeof error === "string" ? error : "OPERATION_FAILED";
  region.textContent = t("error.operation", { code: code.slice(0, 80) });
  region.focus();
}

function renderAnalyticalWorkspace(session: ReflectionSessionView, exploration: ExplorationView): HTMLElement {
  const view = buildAnalyticalWorkspace(session, exploration);
  const workspace = el("section");
  workspace.className = "analytical-workspace";
  workspace.append(el("h3", "АНАЛИТИКА СЕССИИ"), el("p", "Это только чтение: аналитика строится из уже сохранённого состояния сессии."));
  const section = (heading: string): HTMLElement => { const node = el("section"); node.append(el("h4", heading)); workspace.append(node); return node; };
  const contextLine = (item: { text: string; source_anchors: string[]; state: string }): HTMLElement => {
    const line = el("li", item.text);
    line.append(el("small", ` · ${item.source_anchors.length ? `источник: ${item.source_anchors.join(", ")}` : "источник не указан"}`));
    if (item.state) line.append(el("small", ` · ${presentUnknownState(item.state)}`));
    return line;
  };
  const current = section("Текущая рабочая формулировка");
  current.append(el("p", "Рабочая формулировка — это текущее предложение, а не установленный факт или диагноз."));
  if (view.current) current.append(el("strong", `Версия ${view.current.version} · ${presentFormulationStatus(view.current.status)}`), el("p", view.current.summary));
  else current.append(el("p", "Текущая рабочая формулировка ещё не принята."));
  const history = section("Как менялась формулировка");
  if (!view.formulations.length) history.append(el("p", "Версий формулировки пока нет."));
  for (const formulation of view.formulations) {
    const item = el("article"); item.className = "analytical-item";
    item.append(el("strong", `Версия ${formulation.version} · ${presentFormulationStatus(formulation.status)}`), el("small", `Создано: ${formulation.created_at ?? "не указано"} · Обновлено: ${formulation.updated_at ?? "не указано"}`), el("p", formulation.summary), el("small", formulation.comparison_label));
    if (formulation.correction_text) item.append(el("p", `Исправление: ${formulation.correction_text}`));
    if (!formulation.added_lines.length && !formulation.removed_lines.length) item.append(el("p", formulation.comparison_label === "Предыдущей версии нет" ? "Текстовой разницы для первой версии нет." : "Текстовых различий нет."));
    if (formulation.added_lines.length) item.append(el("strong", "Добавлено:"), ...formulation.added_lines.map((line) => el("p", `+ ${line}`)));
    if (formulation.removed_lines.length) item.append(el("strong", "Убрано:"), ...formulation.removed_lines.map((line) => el("p", `- ${line}`)));
    history.append(item);
  }
  const matrix = section("Матрица контекста");
  if (!view.context_by_dimension.length) matrix.append(el("p", "Контекстные элементы пока не зафиксированы."));
  for (const group of view.context_by_dimension) {
    const item = el("article"); item.className = "analytical-item"; item.append(el("h5", presentDimension(group.dimension)));
    for (const kind of ["KNOWN", "UNKNOWN", "CONTRADICTION"] as const) {
      const entries = group.items.filter((entry) => entry.kind === kind); if (!entries.length) continue;
      const label = { KNOWN: "Известно", UNKNOWN: "Неизвестно", CONTRADICTION: "Противоречия / разные ответы" }[kind];
      const list = el("ul"); list.append(...entries.map(contextLine)); item.append(el("strong", label), list);
    }
    matrix.append(item);
  }
  const hypotheses = section("Рабочие гипотезы и основания");
  if (!view.hypotheses.length) hypotheses.append(el("p", "Рабочие гипотезы пока не зафиксированы."));
  for (const hypothesis of view.hypotheses) {
    const item = el("article"); item.className = "analytical-item"; item.append(el("p", hypothesis.proposal_text), el("small", `Неопределённость: ${hypothesis.uncertainty_text}`));
    if (hypothesis.discriminator_text) item.append(el("small", `Что могло бы различить варианты: ${hypothesis.discriminator_text}`));
    for (const [heading, relations, empty] of [["Поддерживает", hypothesis.support, "Поддерживающие данные пока не зафиксированы."], ["Противоречит / контрпример", hypothesis.counterevidence, "Контрпримеры пока не зафиксированы."], ["Остаётся неизвестным", hypothesis.unknown, "Неизвестные данные для этой гипотезы пока не зафиксированы."]] as const) {
      item.append(el("strong", heading));
      if (!relations.length) item.append(el("p", empty));
      else { const list = el("ul"); list.append(...relations.map((relation) => contextLine(relation.context))); item.append(list); }
    }
    hypotheses.append(item);
  }
  const contradictions = section("Противоречия / разные ответы");
  if (!view.contradictions.length) contradictions.append(el("p", "Сейчас зафиксированных противоречий нет."));
  else { const list = el("ul"); list.append(...view.contradictions.map(contextLine)); contradictions.append(list); }
  const unknowns = section("Что остаётся неизвестным");
  if (!view.unresolved_unknowns.length) unknowns.append(el("p", "Неразрешённых неизвестных пока не зафиксировано."));
  else { const list = el("ul"); list.append(...view.unresolved_unknowns.map(contextLine)); unknowns.append(list); }
  const timeline = section("Хронология сессии"); timeline.append(el("p", "Это хронология записанных событий продукта, а не восстановленная биография."));
  if (!view.timeline.length) timeline.append(el("p", "Записанных событий для хронологии пока нет."));
  else { const list = el("ol"); for (const event of view.timeline) list.append(el("li", `${event.at} · ${event.label} · ${event.detail}`)); timeline.append(list); }
  return workspace;
}

async function renderSynthesisActionWorkspace(api: DesktopApi, session: ReflectionSessionView, exploration: ExplorationView, refresh: () => Promise<void>): Promise<HTMLElement> {
  const workspace = el("section");
  workspace.className = "synthesis-action-workspace";
  const synthesis = buildSessionSynthesis(session, exploration);
  workspace.append(el("h3", "ИТОГ СЕССИИ"), el("p", "Итог — это производное представление сохранённых данных сессии, а не новый факт, диагноз или окончательный вывод."));
  const summarySection = (heading: string, values: string[], empty: string): void => {
    workspace.append(el("h4", heading));
    if (!values.length) workspace.append(el("p", empty));
    else { const list = el("ul"); list.append(...values.map((value) => el("li", value))); workspace.append(list); }
  };
  summarySection("Что вы сообщили", synthesis.known, "Сохранённых сообщённых элементов пока нет.");
  summarySection("Текущая рабочая формулировка", synthesis.current_formulation ? [synthesis.current_formulation] : [], "Текущая рабочая формулировка ещё не принята.");
  summarySection("Что изменилось", [synthesis.changed], "");
  summarySection("Что остаётся неизвестным", synthesis.unresolved, "Неразрешённых неизвестных пока не зафиксировано.");
  summarySection("Противоречия / разные ответы", synthesis.contradictions, "Зафиксированных противоречий пока нет.");
  summarySection("Рабочие альтернативы", synthesis.alternatives, "Рабочие альтернативы пока не зафиксированы.");

  const history = await api.actionList(session.session_id);
  const historySection = el("section"); historySection.append(el("h4", "ИСТОРИЯ МОИХ СЛЕДУЮЩИХ ШАГОВ"));
  if (!history.plans.length) historySection.append(el("p", "Сохранённых шагов пока нет."));
  for (const plan of history.plans) {
    const item = el("article"); item.className = "action-plan";
    item.append(el("strong", `Версия ${plan.version} · ${plan.status}`), el("p", `Ваша цель: ${plan.user_goal}`), el("p", `Вы выбрали: ${plan.template_id}`), el("p", plan.action_text), el("small", `Основание: снимок ${plan.basis_snapshot_id ?? "не сохранён"}; формулировка ${plan.basis_formulation_id ?? "не выбрана"}; ориентир ${plan.anchor_id ?? "не выбран"}.`));
    if (plan.outcome) item.append(el("p", `Ваша отметка: ${presentOutcome(plan.outcome.status)}${plan.outcome.note_text ? ` · ${plan.outcome.note_text}` : ""}`));
    historySection.append(item);
  }
  workspace.append(historySection);
  if (session.state === "CLOSED") return workspace;

  const form = el("section"); form.className = "action-draft";
  form.append(el("h4", "МОЯ ЦЕЛЬ"), el("p", "Эти варианты — не лечение и не медицинская рекомендация. Можно выбрать паузу или изменить текст шага."));
  const goal = el("textarea"); goal.id = "action-goal"; goal.setAttribute("aria-label", "Моя цель"); goal.maxLength = 12000; goal.rows = 3;
  const anchorLabel = el("label", "НА ЧТО ОПЕРЕТЬСЯ"); anchorLabel.htmlFor = "action-anchor";
  const anchor = el("select"); anchor.id = "action-anchor";
  const addAnchor = (label: string, type: ActionAnchorType, id: string | null): void => { const option = el("option", label); option.value = JSON.stringify({ type, id }); anchor.append(option); };
  addAnchor("Не выбирать ориентир", null, null);
  for (const item of exploration.context.filter((item) => item.kind === "UNKNOWN" && item.state !== "RESOLVED")) addAnchor(`Открытый вопрос: ${item.text}`, "UNKNOWN", item.context_item_id);
  for (const item of exploration.context.filter((item) => item.kind === "CONTRADICTION")) addAnchor(`Разные ответы: ${item.text}`, "CONTRADICTION", item.context_item_id);
  const current = exploration.formulations.find((item) => item.status === "CURRENT");
  if (current) addAnchor("Текущая рабочая формулировка", "FORMULATION", current.formulation_id);
  const options = el("fieldset"); options.append(el("legend", "ВАРИАНТЫ СЛЕДУЮЩЕГО ШАГА"));
  const actionText = el("textarea"); actionText.id = "action-text"; actionText.setAttribute("aria-label", "Текст следующего шага"); actionText.maxLength = 12000; actionText.rows = 4;
  let selected: ActionOption | null = null;
  const renderOptions = async (): Promise<void> => {
    const selection = JSON.parse(anchor.value) as { type: ActionAnchorType; id: string | null };
    const response = await api.actionOptions(session.session_id, selection.type, selection.id);
    options.replaceChildren(el("legend", "ВАРИАНТЫ СЛЕДУЮЩЕГО ШАГА")); selected = null;
    for (const option of response.options) {
      const label = el("label"); const input = el("input"); input.type = "radio"; input.name = "action-template"; input.value = option.template_id;
      input.addEventListener("change", () => { selected = option; actionText.value = option.text; }); label.append(input, document.createTextNode(` ${option.text}`)); options.append(label);
    }
  };
  anchor.addEventListener("change", () => void renderOptions().catch(() => undefined));
  await renderOptions();
  const save = button("Сохранить мой следующий шаг", async () => {
    if (!selected) { safeError(workspace, "INVALID_TEMPLATE"); return; }
    const selection = JSON.parse(anchor.value) as { type: ActionAnchorType; id: string | null };
    await api.actionCreate({ sessionId: session.session_id, userGoal: goal.value, templateId: selected.template_id, actionText: actionText.value, anchorType: selection.type, anchorId: selection.id });
    await refresh();
  }, "primary");
  form.append(goal, anchorLabel, anchor, options, actionText, save); workspace.append(form);
  for (const plan of history.plans.filter((item) => item.status === "CURRENT")) {
    const outcome = el("section"); outcome.append(el("h4", "КАК ЗАКОНЧИЛОСЬ?"));
    const status = el("select"); status.id = `outcome-${plan.plan_id}`;
    const outcomeOptions: Array<[string, string]> = [["DONE", "Сделано"], ["NOT_DONE", "Не сделано"], ["CANCELLED", "Отменено"], ["UNKNOWN", "Пока не знаю"]];
    for (const [value, label] of outcomeOptions) { const option = el("option", label); option.value = value; status.append(option); }
    const note = el("textarea"); note.setAttribute("aria-label", "Ваш комментарий о результате"); note.maxLength = 12000; note.rows = 2;
    outcome.append(status, note, button("Сохранить отметку", async () => { await api.actionRecordOutcome(plan.plan_id, status.value as "DONE" | "NOT_DONE" | "CANCELLED" | "UNKNOWN", note.value || null); await refresh(); })); workspace.append(outcome);
  }
  return workspace;
}

function presentOutcome(status: string): string { return ({ DONE: "Сделано", NOT_DONE: "Не сделано", CANCELLED: "Отменено", UNKNOWN: "Пока не знаю" } as Record<string, string>)[status] ?? status; }

function listSection(root: HTMLElement, heading: string, values: string[], empty: string): void { root.append(el("h3", heading)); if (!values.length) root.append(el("p", empty)); else { const list = el("ul"); list.append(...values.map((value) => el("li", value))); root.append(list); } }
function renderLongitudinalWorkspace(bundles: LongitudinalSessionBundle[]): HTMLElement {
  const view = buildLongitudinalWorkspace(bundles); const root = el("section"); root.className = "longitudinal-workspace";
  root.append(el("h2", "ДИНАМИКА ПО СЕССИЯМ"), el("p", "Это объём сохранённых записей, а не оценка состояния или прогресса."));
  listSection(root, "1. Обзор записей", [`Сессий: ${view.coverage.sessions}`, `Сессий с guided exploration: ${view.coverage.guided}`, `Сессий с CURRENT formulation: ${view.coverage.current}`, `Сохранённых следующих шагов: ${view.coverage.plans}`, `Пользовательских отметок о результате: ${view.coverage.outcomes}`], "Сессий пока нет.");
  listSection(root, "2. История рабочих формулировок", view.formulations.map((entry) => `${entry.session.title} · ${entry.session.created_at} · версия ${entry.formulation.version}: ${entry.formulation.summary}${entry.diff ? " · Текстовые отличия от предыдущей записанной формулировки" : ""}`), "CURRENT рабочих формулировок пока нет.");
  listSection(root, "3. Что повторялось в записях", view.recurrences.map((group) => `${group.text} · ${group.dimension} · Одинаковая запись встречалась в ${group.session_count} сессиях. (${group.occurrences.map((item) => item.title).join(", ")})`), "Одинаковых записей в двух разных сессиях пока нет.");
  root.append(el("p", "Разные формулировки не объединяются: это только точное совпадение kind, dimension и текста."));
  const refs = (values: Array<{ item: { text: string }; anchors: string[] }>, empty: string): string => values.length ? values.map((value) => `${value.item.text}${value.anchors.length ? ` · источник: ${value.anchors.join(", ")}` : ""}`).join("; ") : empty;
  listSection(root, "4. Рабочие альтернативы по сессиям", view.hypotheses.flatMap((group) => group.entries.flatMap((entry) => [`${group.template_id} · ${entry.session.title} · ${entry.session.created_at}: ${entry.hypothesis.proposal_text} · Неопределённость: ${entry.hypothesis.uncertainty_text}`, `SUPPORT (${entry.refs.SUPPORT.length}): ${refs(entry.refs.SUPPORT, "Поддерживающих записей в этой сессии не зафиксировано.")}`, `COUNTEREVIDENCE (${entry.refs.COUNTEREVIDENCE.length}): ${refs(entry.refs.COUNTEREVIDENCE, "Контрпримеров в этой сессии не зафиксировано.")}`, `UNKNOWN (${entry.refs.UNKNOWN.length}): ${refs(entry.refs.UNKNOWN, "Неизвестных записей в отношениях этой сессии не зафиксировано.")}`])), "Рабочие альтернативы с устойчивым template_id пока не зафиксированы.");
  root.append(el("p", "Частота появления рабочей альтернативы не означает её истинность."));
  const history = (kind: string, groups: typeof view.unknowns, state: boolean): string[] => groups.flatMap((group) => [`${kind}: ${group.text} · ${group.dimension} · ${group.session_count === 1 ? "Зафиксировано в этой сессии" : `Одинаковая запись встречалась в ${group.session_count} сессиях`}`, ...group.occurrences.map((item) => `${item.title} · сессия ${item.session_at} · запись ${item.at} · ${state ? `Состояние записи: ${presentUnknownState(item.state)}` : `Состояние записи: ${item.state}`} · ${item.occurrence_count} запис. · ${item.anchors.length ? `источник: ${item.anchors.join(", ")}` : "источник не зафиксирован"}`)]);
  listSection(root, "5. Неизвестное и противоречия", [...history("Неизвестное", view.unknowns, true), ...history("Противоречие", view.contradictions, false)], "Неизвестных или противоречий пока нет.");
  root.append(el("p", "Состояние относится к записи внутри конкретной сессии. Одинаковый текст не означает, что это один и тот же факт во времени."));
  const planText = (plan: import("./api").ActionPlan, title: string): string => [`Сессия: ${title}`, `версия плана: ${plan.version}`, `статус: ${plan.status}`, `цель пользователя: ${plan.user_goal}`, `шаблон: ${plan.template_id} ${plan.template_version}`, `действие: ${plan.action_text}`, `основание-снимок: ${plan.basis_snapshot_id ?? "не записано"}`, `основание-формулировка: ${plan.basis_formulation_id ?? "не записано"}`, `якорь: ${plan.anchor_type ?? "не записано"}${plan.anchor_id ? ` / ${plan.anchor_id}` : ""}`, `создано: ${plan.created_at}`, plan.outcome ? `ваша отметка: ${presentOutcome(plan.outcome.status)}${plan.outcome.note_text ? ` · ${plan.outcome.note_text}` : ""} · ${plan.outcome.created_at}` : "Отметки пока нет"].join(" · ");
  listSection(root, "6. Мои следующие шаги и отметки", view.plans.map((plan) => planText(plan, view.sessions.find((bundle) => bundle.session.session_id === plan.session_id)?.session.title ?? plan.session_id)), "Сохранённых следующих шагов пока нет.");
  root.append(el("p", "Отметка «Сделано» говорит только о выполнении шага, а не о его пользе или эффективности."));
  const comparison = el("section"); comparison.className = "comparison"; comparison.append(el("h3", "7. Сравнить две сессии")); const a = el("select"), b = el("select"), result = el("div"); a.id = "longitudinal-session-a"; b.id = "longitudinal-session-b";
  for (const bundle of view.sessions) for (const select of [a, b]) { const option = el("option", `${bundle.session.title} · ${bundle.session.created_at}`); option.value = bundle.session.session_id; select.append(option); }
  const show = (): void => { const left = view.sessions.find((x) => x.session.session_id === a.value), right = view.sessions.find((x) => x.session.session_id === b.value); if (!left || !right) return; const diff = compareSessions(left, right); const side = (label: string, session: typeof left.session): string => `${label}: ${session.title} · ${session.state} · создана ${session.created_at}${session.closed_at ? ` · закрыта ${session.closed_at}` : ""}`; const difference = diff.formulation_diff ? `добавлено ${diff.formulation_diff.added_lines.join("; ") || "нет"}; убрано ${diff.formulation_diff.removed_lines.join("; ") || "нет"}` : "нет двух CURRENT формулировок"; const unknowns = diff.unknowns.flatMap((item) => [`UNKNOWN: ${item.text} · ${item.dimension}`, `A: ${item.a.length ? item.a.map((value) => presentUnknownState(value.state)).join(", ") : "Не записано в этой сессии"}`, `B: ${item.b.length ? item.b.map((value) => presentUnknownState(value.state)).join(", ") : "Не записано в этой сессии"}`]); const hypotheses = diff.hypotheses.flatMap((item) => [`Гипотеза ${item.template_id} · A: ${item.a ? `${item.a.hypothesis.proposal_text} · ${item.a.hypothesis.uncertainty_text} · SUPPORT: ${refs(item.a.refs.SUPPORT, "нет")}; COUNTEREVIDENCE: ${refs(item.a.refs.COUNTEREVIDENCE, "нет")}; UNKNOWN: ${refs(item.a.refs.UNKNOWN, "нет")}` : "Не записано в этой сессии"}`, `Гипотеза ${item.template_id} · B: ${item.b ? `${item.b.hypothesis.proposal_text} · ${item.b.hypothesis.uncertainty_text} · SUPPORT: ${refs(item.b.refs.SUPPORT, "нет")}; COUNTEREVIDENCE: ${refs(item.b.refs.COUNTEREVIDENCE, "нет")}; UNKNOWN: ${refs(item.b.refs.UNKNOWN, "нет")}` : "Не записано в этой сессии"}`]); result.replaceChildren(...[side("Сессия A", left.session), side("Сессия B", right.session), `CURRENT A: ${diff.current_a?.summary ?? "CURRENT формулировка не записана"}`, `CURRENT B: ${diff.current_b?.summary ?? "CURRENT формулировка не записана"}`, `Общие точные записи: ${diff.common.map((x) => x.text).join(", ") || "нет"}`, `Только в A: ${diff.only_a.map((x) => `${x.text} · Не записано в другой выбранной сессии.`).join(", ") || "нет"}`, `Только в B: ${diff.only_b.map((x) => `${x.text} · Не записано в другой выбранной сессии.`).join(", ") || "нет"}`, `Текстовые отличия формулировок: ${difference}`, ...unknowns, `Противоречия в обеих: ${diff.contradictions_common.map((item) => item.text).join(", ") || "нет"}`, `Противоречия только A: ${diff.contradictions_only_a.map((item) => item.text).join(", ") || "нет"}`, `Противоречия только B: ${diff.contradictions_only_b.map((item) => item.text).join(", ") || "нет"}`, ...hypotheses, ...diff.actions.a.map((plan) => `Действие A: ${planText(plan, left.session.title)}`), ...diff.actions.b.map((plan) => `Действие B: ${planText(plan, right.session.title)}`)].map((text) => el("p", text))); };
  a.setAttribute("aria-label", "Сессия A"); b.setAttribute("aria-label", "Сессия B"); a.addEventListener("change", show); b.addEventListener("change", show); const aLabel = el("label", "Сессия A"), bLabel = el("label", "Сессия B"); aLabel.htmlFor = a.id; bLabel.htmlFor = b.id; comparison.append(aLabel, a, bLabel, b, result); root.append(comparison); show();
  listSection(root, "8. Хронология записанных событий продукта", view.timeline.map((event) => `${event.at} · ${event.type} · ${event.detail}`), "Записанных событий продукта пока нет."); root.append(el("p", "Это хронология записей внутри продукта, а не восстановленная хронология жизни.")); return root;
}

function renderReturnWorkspace(bundles: LongitudinalSessionBundle[], choose: (candidate: ReturnCandidate) => Promise<void>): HTMLElement {
  const view = buildReturnWorkspace(bundles);
  const root = el("section"); root.className = "return-workspace";
  root.append(el("h2", "К ЧЕМУ ВЕРНУТЬСЯ"), el("p", "Здесь показаны только ранее сохранённые записи. Вы сами решаете, открывать ли что-либо и когда."));
  const labels: Record<ReturnCandidateCategory, string> = { OPEN_UNKNOWN: "Открытые вопросы и пропущенное", CURRENT_FORMULATION: "Рабочие формулировки", CURRENT_ACTION: "Мои следующие шаги", OUTCOME: "Мои отметки", SESSION: "Предыдущие сессии" };
  const provenance = (candidate: ReturnCandidate): string => candidate.provenance === "DERIVED" ? "Записано ранее · производное представление" : candidate.provenance === "USER_AUTHORED" ? "Записано ранее · ваш текст / ваша отметка" : "Записано ранее";
  for (const category of ["OPEN_UNKNOWN", "CURRENT_FORMULATION", "CURRENT_ACTION", "OUTCOME", "SESSION"] as ReturnCandidateCategory[]) {
    const section = el("section"); section.append(el("h3", labels[category]));
    const values = view.by_category[category];
    if (!values.length) section.append(el("p", "Таких сохранённых записей пока нет."));
    for (const candidate of values) {
      const item = el("article"); item.className = "return-candidate";
      item.append(el("p", candidate.text), el("small", `${provenance(candidate)} · сессия: ${candidate.session_title} · ${candidate.recorded_at} · состояние: ${candidate.state}`));
      if (candidate.source_anchors.length) item.append(el("small", `Источник: ${candidate.source_anchors.join(", ")}`));
      item.append(button(candidate.session_state === "ACTIVE" ? "Продолжить эту сессию" : "Начать новую сессию", async () => choose(candidate), candidate.session_state === "ACTIVE" ? "primary" : "secondary"));
      section.append(item);
    }
    root.append(section);
  }
  root.append(el("p", "«Открыто» и «пропущено» описывают состояние записи; они не означают срочность. Отсутствие новой записи не означает разрешение. «Сделано» не означает эффективность."));
  return root;
}

export async function mount(api: DesktopApi = desktopApi): Promise<void> {
  const root = document.querySelector<HTMLDivElement>("#app");
  if (!root) throw new Error("APP_ROOT_MISSING");
  root.replaceChildren();

  const header = el("header");
  const brand = el("div");
  brand.className = "brand";
  brand.append(el("span", "PSYCHE OS"), el("small", t("brand.subtitle")));
  const lockButton = button(t("session.lock"), async () => {
    await api.lock();
    window.location.reload();
  });
  lockButton.id = "lock-session";
  header.append(brand, lockButton);

  const main = el("main");
  main.id = "main-content";
  main.tabIndex = -1;
  const statusRegion = el("section");
  statusRegion.className = "status-strip";
  statusRegion.setAttribute("aria-label", t("status.aria"));
  const operationStatus = el("div");
  operationStatus.id = "operation-status";
  operationStatus.className = "result";
  operationStatus.setAttribute("role", "status");
  operationStatus.setAttribute("aria-live", "polite");
  operationStatus.tabIndex = -1;

  let status: StatusView;
  try {
    status = await api.status();
  } catch (error) {
    safeError(operationStatus, error);
    root.append(header, main, operationStatus);
    return;
  }

  for (const [label, value] of [
    [t("status.data"), status.data_mode],
    [t("status.gate"), status.real_data_gate],
    [t("status.runtime"), status.network],
    [t("status.cloud"), status.privacy.cloud]
  ]) {
    const item = el("div");
    item.append(el("span", label), el("strong", presentValue(value)));
    statusRegion.append(item);
  }

  if (status.locked) {
    lockButton.hidden = true;
    const unlock = el("section");
    unlock.className = "unlock card";
    unlock.append(el("p", t("value.OFFLINE_NO_LISTENER")), el("h1", t("unlock.heading")));
    unlock.append(el("p", t("unlock.notice")));
    const form = el("form");
    const [secretLabel, secret] = field(t("unlock.secret"), "unlock-secret", "password");
    secret.autocomplete = "off";
    secret.maxLength = 256;
    secret.required = true;
    const error = el("p");
    error.id = "unlock-error";
    error.className = "field-error";
    secret.setAttribute("aria-describedby", error.id);
    const submit = el("button", t("unlock.submit"));
    submit.type = "submit";
    submit.className = "primary";
    form.append(secretLabel, secret, error, submit);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      void api.unlock(secret.value).then(() => mount(api)).catch((reason: unknown) => {
        secret.value = "";
        error.textContent = `${t("unlock.rejected")} (${String(reason).slice(0, 64)}).`;
        secret.focus();
      });
    });
    unlock.append(form);
    main.append(statusRegion, unlock);
    root.append(header, main, operationStatus);
    secret.focus();
    return;
  }

  const title = el("div");
  title.className = "hero";
  title.append(el("p", t("hero.kicker")), el("h1", t("hero.heading")));
  title.append(el("p", t("hero.notice")));

  const sessions = el("section");
  sessions.className = "card sessions-card product-shell";
  const productNav = el("nav");
  productNav.className = "product-nav";
  productNav.setAttribute("aria-label", "Разделы продукта");
  const sessionBody = el("div");
  sessions.append(productNav, sessionBody);
  let sessionViewEpoch = 0;
  const showSession = async (sessionId: string): Promise<void> => {
    const viewEpoch = ++sessionViewEpoch;
    try {
      const current = await api.reflectionGet(sessionId);
      if (viewEpoch !== sessionViewEpoch) return;
      sessionBody.replaceChildren();
      const sessionHeader = el("header");
      sessionHeader.className = "session-header";
      sessionHeader.append(el("p", current.state === "CLOSED" ? "ЗАКРЫТАЯ СЕССИЯ · ТОЛЬКО ЧТЕНИЕ" : "АКТИВНАЯ СЕССИЯ"), el("h2", current.title), el("p", `Создана: ${current.created_at}`));
      const journeyNav = el("nav");
      journeyNav.className = "journey-nav";
      journeyNav.setAttribute("aria-label", "Разделы сессии");
      const focusStage = async (id: string): Promise<void> => { document.querySelector<HTMLElement>(`#${id}`)?.focus(); };
      journeyNav.append(
        button("1. Запись", async () => focusStage("journey-record")),
        button("2. Исследование", async () => focusStage("journey-explore")),
        button("3. Обзор", async () => focusStage("journey-review")),
        button("4. Итог и следующий шаг", async () => focusStage("journey-summary"))
      );
      sessionBody.append(sessionHeader, journeyNav);
      const record = el("section");
      record.id = "journey-record";
      record.tabIndex = -1;
      record.append(el("h3", "Запись"));
      sessionBody.append(record);
      for (const turn of current.turns ?? []) {
        const item = el("article"); item.className = "session-turn"; item.append(el("strong", "Ваш текст"), el("p", turn.content)); record.append(item);
      }
      const exploration = el("section"); exploration.className = "guided-exploration";
      exploration.id = "journey-explore";
      exploration.tabIndex = -1;
      const renderExploration = async (): Promise<void> => {
        exploration.replaceChildren();
        exploration.append(el("h3", "Исследование"));
        if ((current.turns ?? []).length === 0) { exploration.append(el("p", "Записей пока нет. Исследование можно открыть после сохранения текста.")); return; }
        const state = current.state === "CLOSED" ? await api.explorationGet(current.session_id) : await api.explorationStart(current.session_id);
        const block = (heading: string, values: string[]): void => { const section = el("div"); section.append(el("h4", heading), ...values.map((value) => el("p", value))); exploration.append(section); };
        block("Что уже известно", state.context.filter((item) => item.kind === "KNOWN").map((item) => `${item.text} · источник: ваш ответ`));
        block("Что пока неизвестно", state.context.filter((item) => item.kind === "UNKNOWN" && item.state !== "RESOLVED").map((item) => item.text));
        const contradictions = state.context.filter((item) => item.kind === "CONTRADICTION").map((item) => item.text);
        block("Противоречия / контрпримеры", contradictions.length ? contradictions : ["Сейчас противоречия не установлены."]);
        block("Рабочие гипотезы", state.hypotheses.map((item) => `${item.proposal_text} Неопределённость: ${item.uncertainty_text}`));
        if (state.next_question) {
          const answer = el("textarea"); answer.id = "guided-answer"; answer.setAttribute("aria-label", "Ответ на следующий вопрос"); answer.maxLength = 12000; answer.rows = 3; answer.disabled = current.state === "CLOSED";
          const ask = button("Ответить на следующий вопрос", async () => { await api.explorationAnswer(state.next_question!.question_id, answer.value); await showSession(current.session_id); }, "primary"); ask.disabled = current.state === "CLOSED";
          const skip = button("Пропустить / не знаю", async () => { await api.explorationSkip(state.next_question!.question_id); await showSession(current.session_id); }); skip.disabled = current.state === "CLOSED";
          exploration.append(el("h4", "Следующий вопрос"), el("p", state.next_question.text), answer, ask, skip);
        }
        const propose = button("Составить рабочую формулировку", async () => { await api.formulationPropose(current.session_id); await showSession(current.session_id); }); propose.disabled = current.state === "CLOSED";
        exploration.append(el("h4", "Рабочая формулировка"), el("p", "Это рабочее предложение, не диагноз и не установленный факт; его можно исправить или отклонить."), propose, el("h4", "История формулировок"));
        for (const formulation of state.formulations) {
          const item = el("article"); item.append(el("strong", `Версия ${formulation.version}: ${formulation.status}`), el("p", formulation.summary));
          if (current.state === "ACTIVE" && formulation.status === "PROPOSED") {
            const correction = el("textarea"); correction.setAttribute("aria-label", "Исправление формулировки"); correction.maxLength = 12000; correction.rows = 2;
            item.append(correction, button("Исправить", async () => { await api.formulationCorrect(formulation.formulation_id, correction.value); await showSession(current.session_id); }), button("Принять как рабочую", async () => { await api.formulationAccept(formulation.formulation_id); await showSession(current.session_id); }), button("Отклонить", async () => { await api.formulationReject(formulation.formulation_id); await showSession(current.session_id); }));
          }
          exploration.append(item);
        }
        const plans = (await api.actionList(current.session_id)).plans;
        const journey = buildProductJourney(current, state, plans);
        const states = el("p");
        states.className = "journey-states";
        states.textContent = [
          presentJourneyState(journey.has_turns, "Есть записи", "Записей пока нет"),
          presentJourneyState(journey.has_guided_exploration, "Есть исследование", "Исследование не создано"),
          presentJourneyState(journey.has_current_formulation, "Есть рабочая формулировка", "Рабочая формулировка не создана"),
          presentJourneyState(journey.has_action_plan, "Есть сохранённый шаг", "Сохранённого шага нет")
        ].join(" · ");
        exploration.prepend(states);
        const analytical = renderAnalyticalWorkspace(current, state); analytical.id = "journey-review"; analytical.tabIndex = -1;
        exploration.append(analytical);
        const synthesis = await renderSynthesisActionWorkspace(api, current, state, async () => showSession(current.session_id)); synthesis.id = "journey-summary"; synthesis.tabIndex = -1;
        exploration.append(synthesis);
      };
      const label = el("label", "Ваш текст"); label.htmlFor = "reflection-turn";
      const content = el("textarea"); content.id = "reflection-turn"; content.name = "reflection-turn"; content.setAttribute("aria-label", "Ваш текст"); content.maxLength = 12000; content.rows = 5; content.required = true; content.disabled = current.state === "CLOSED";
      const add = button("Добавить в сессию", async () => { await api.reflectionAddTurn(current.session_id, content.value); await showSession(current.session_id); }, "primary");
      add.disabled = current.state === "CLOSED";
      const close = button("Завершить сессию", async () => { await api.reflectionClose(current.session_id); await showSession(current.session_id); }); close.disabled = current.state === "CLOSED";
      const remove = button("Удалить сессию", async () => { await api.reflectionDelete(current.session_id); await showList(); }, "danger");
      const back = button("Назад к сессиям", async () => showList());
      record.append(label, content, add);
      sessionBody.append(exploration, close, remove, back);
      await renderExploration();
    } catch (error) { safeError(operationStatus, error); }
  };
  const showList = async (): Promise<void> => {
    const viewEpoch = ++sessionViewEpoch;
    try {
      const result = await api.reflectionList(); if (viewEpoch !== sessionViewEpoch) return; sessionBody.replaceChildren(el("h2", "Сессии"), el("p", "Все сохранённые сессии. Закрытые сессии остаются только для чтения."), createForm);
      for (const item of [...result.sessions].sort((left, right) => left.created_at.localeCompare(right.created_at) || left.session_id.localeCompare(right.session_id))) {
        const row = el("div"); row.className = "session-row";
        row.append(el("strong", item.title), el("span", `Создана: ${item.created_at}`), el("span", `Записей: ${item.turn_count}`), el("span", item.state === "ACTIVE" ? "Активна" : "Закрыта · только чтение"), button("Открыть сессию", async () => showSession(item.session_id))); sessionBody.append(row);
      }
    } catch (error) { safeError(operationStatus, error); }
  };
  const showLongitudinal = async (): Promise<void> => {
    const viewEpoch = ++sessionViewEpoch;
    try {
      const listed = await api.reflectionList();
      if (viewEpoch !== sessionViewEpoch) return;
      const bundles = await Promise.all(listed.sessions.map(async (listedSession): Promise<LongitudinalSessionBundle> => {
        const session = await api.reflectionGet(listedSession.session_id);
        const [exploration, actionHistory] = await Promise.all([api.explorationGet(session.session_id), api.actionList(session.session_id)]);
        return { session, exploration, plans: actionHistory.plans };
      }));
      if (viewEpoch !== sessionViewEpoch) return;
      sessionBody.replaceChildren(el("h2", "Динамика по сессиям"), renderLongitudinalWorkspace(bundles), button("К сессиям", showList), button("На главную", showHome));
    } catch (error) { safeError(operationStatus, error); }
  };
  const showReturn = async (): Promise<void> => {
    const viewEpoch = ++sessionViewEpoch;
    try {
      const listed = await api.reflectionList();
      if (viewEpoch !== sessionViewEpoch) return;
      const bundles = await Promise.all(listed.sessions.map(async (listedSession): Promise<LongitudinalSessionBundle> => {
        const session = await api.reflectionGet(listedSession.session_id);
        const [exploration, actionHistory] = await Promise.all([api.explorationGet(session.session_id), api.actionList(session.session_id)]);
        return { session, exploration, plans: actionHistory.plans };
      }));
      if (viewEpoch !== sessionViewEpoch) return;
      sessionBody.replaceChildren(el("h2", "К чему вернуться"), renderReturnWorkspace(bundles, async (candidate) => {
        if (candidate.session_state === "ACTIVE") await showSession(candidate.session_id);
        else await showFollowUp(candidate);
      }), button("К сессиям", showList), button("На главную", showHome));
    } catch (error) { safeError(operationStatus, error); }
  };
  const showFollowUp = async (candidate: ReturnCandidate): Promise<void> => {
    const viewEpoch = ++sessionViewEpoch;
    const view = buildFollowUpWorkspace(candidate);
    const root = el("section");
    root.className = "follow-up-workspace";
    root.append(el("h2", "ВЕРНУТЬСЯ К ЗАПИСИ"), el("p", "Историческая запись показана только для чтения. Она не будет добавлена в новую сессию."));
    const historical = el("section");
    historical.className = "follow-up-historical";
    historical.append(el("h3", "Записано ранее"), el("p", view.candidate.text), el("small", `${view.provenance_label} · ${view.candidate.category} · ${view.candidate.recorded_at} · состояние: ${view.candidate.state}`));
    if (view.candidate.source_anchors.length) historical.append(el("small", `Источник: ${view.candidate.source_anchors.join(", ")}`));
    const source = el("section");
    source.append(el("h3", "Исходная сессия"), el("p", `${view.candidate.session_title} · ${view.source_state_label}`));
    const form = el("form"); form.className = "follow-up-form";
    const [titleLabel, title] = field("Новая сессия", "follow-up-title"); title.maxLength = 160; title.required = true; title.value = view.suggested_title;
    const textLabel = el("label", "Что вы хотите записать сейчас?"); textLabel.htmlFor = "follow-up-text";
    const text = el("textarea"); text.id = "follow-up-text"; text.name = "follow-up-text"; text.setAttribute("aria-label", "Что вы хотите записать сейчас?"); text.maxLength = 12000; text.rows = 5; text.required = true;
    const create = el("button", "Начать новую сессию"); create.type = "submit"; create.className = "primary";
    const cancel = button("Отмена", showReturn);
    form.append(titleLabel, title, textLabel, text, create, cancel);
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (viewEpoch !== sessionViewEpoch) return;
      const submittedTitle = title.value;
      const submittedText = text.value;
      create.disabled = true;
      cancel.disabled = true;
      void (async () => {
        try {
          const created = await api.reflectionCreate(submittedTitle);
          await api.reflectionAddTurn(created.session_id, submittedText);
          if (viewEpoch !== sessionViewEpoch) return;
          await showSession(created.session_id);
        } catch (error) {
          if (viewEpoch === sessionViewEpoch) { create.disabled = false; cancel.disabled = false; safeError(operationStatus, error); }
        }
      })();
    });
    root.append(historical, source, form);
    if (viewEpoch === sessionViewEpoch) sessionBody.replaceChildren(root);
  };
  const createForm = el("form");
  const [sessionTitleLabel, sessionTitle] = field("Название", "reflection-title"); sessionTitle.maxLength = 160; sessionTitle.required = true;
  const create = el("button", "Начать новую сессию"); create.type = "submit"; create.className = "primary";
  createForm.append(sessionTitleLabel, sessionTitle, create);
  createForm.addEventListener("submit", (event) => { event.preventDefault(); void api.reflectionCreate(sessionTitle.value).then((created) => showSession(created.session_id)).catch((error: unknown) => safeError(operationStatus, error)); });
  const showHome = async (): Promise<void> => {
    const viewEpoch = ++sessionViewEpoch;
    try {
      const result = await api.reflectionList();
      if (viewEpoch !== sessionViewEpoch) return;
      const chronological = [...result.sessions].sort((left, right) => right.created_at.localeCompare(left.created_at) || right.session_id.localeCompare(left.session_id));
      const active = chronological.filter((item) => item.state === "ACTIVE");
      const home = el("section"); home.className = "product-home";
      home.append(el("p", "ЛОКАЛЬНОЕ ПРОСТРАНСТВО"), el("h1", "МОЁ ПРОСТРАНСТВО"));
      if (!chronological.length) {
        home.append(el("p", "Здесь можно записать ситуацию, уточнить контекст, посмотреть рабочие объяснения и сохранить собственный следующий шаг."), button("Начать первую сессию", async () => { await showList(); sessionTitle.focus(); }, "primary"));
      } else {
        home.append(el("p", "Начните новую запись или откройте сохранённую сессию в удобном для вас порядке."), button("Начать новую сессию", async () => { await showList(); sessionTitle.focus(); }, "primary"));
        if (active.length === 1) home.append(button("Продолжить текущую сессию", async () => showSession(active[0]!.session_id), "primary"));
        if (active.length > 1) {
          const activeList = el("section"); activeList.append(el("h2", "Активные сессии"), el("p", "Сессии показаны по дате создания; здесь нет приоритета или рекомендации."));
          for (const item of active) activeList.append(button(`${item.title} · ${item.created_at}`, async () => showSession(item.session_id)));
          home.append(activeList);
        }
        const recent = el("section"); recent.append(el("h2", "Последние сессии"));
        for (const item of chronological.slice(0, 6)) {
          const row = el("div"); row.className = "session-row";
          row.append(el("strong", item.title), el("span", `Дата: ${item.created_at}`), el("span", item.state === "ACTIVE" ? "Активна" : "Закрыта · только чтение"), el("span", `Записей: ${item.turn_count}`), button("Открыть сессию", async () => showSession(item.session_id)));
          recent.append(row);
        }
        home.append(recent);
      }
      sessionBody.replaceChildren(home);
    } catch (error) { safeError(operationStatus, error); }
  };
  productNav.append(button("Главная", showHome, "primary"), button("Сессии", showList), button("К чему вернуться", showReturn), button("Динамика", showLongitudinal));

  const grid = el("div");
  grid.className = "grid";

  let operationSequence = 0;
  const archive = el("section");
  archive.className = "card archive-card";
  archive.append(el("p", t("archive.kicker")), el("h2", t("archive.heading")));
  archive.append(el("p", t("archive.notice")));
  const archiveAction = (label: string, operation: string, choice: string): HTMLButtonElement =>
    button(label, async () => {
      operationSequence += 1;
      try {
        const result = await api.archiveOperate(operation, choice, `desktop_${operationSequence.toString().padStart(3, "0")}`);
        renderResult(operationStatus, result, `${label}. ${t("archive.completed")}`);
      } catch (error) { safeError(operationStatus, error); }
    });
  archive.append(
    archiveAction(t("archive.captureReport"), "CAPTURE_LAMP_REPORT", "occurred_summer_2042"),
    archiveAction(t("archive.captureObservation"), "CAPTURE_LAMP_OBSERVATION", "observed_interval"),
    archiveAction(t("archive.captureCounterreport"), "CAPTURE_COUNTERREPORT", "occurred_unknown"),
    archiveAction(t("archive.assemble"), "ASSEMBLE_EPISTEMIC_SET", "descriptive_proposed"),
    archiveAction(t("archive.baseline"), "CREATE_BASELINE_SNAPSHOT", "baseline"),
    archiveAction(t("archive.revised"), "CREATE_REVISED_SNAPSHOT", "revised"),
    archiveAction(t("archive.correctTime"), "CORRECT_LAMP_REPORT_TIME", "corrected_reported_exact")
  );

  const explore = el("section");
  explore.className = "card";
  explore.append(el("p", t("explore.kicker")), el("h2", t("explore.heading")));
  const clockLabel = el("label", t("explore.clock"));
  clockLabel.htmlFor = "timeline-clock";
  const clock = el("select");
  clock.id = "timeline-clock";
  for (const role of ["occurred", "observed", "reported", "recorded", "asserted"]) {
    const option = el("option", t(`clock.${role}` as TranslationKey));
    option.value = role;
    clock.append(option);
  }
  const timelineButton = button(t("explore.timeline"), async () => {
    try { renderResult(operationStatus, await api.archiveTimeline(clock.value), t("explore.timelineResult", { clock: t(`clock.${clock.value}` as TranslationKey) })); }
    catch (error) { safeError(operationStatus, error); }
  });
  const explorerButton = button(t("explore.open"), async () => {
    try { renderResult(operationStatus, await api.archiveExplorer(), t("explore.openResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  const diffButton = button(t("explore.diff"), async () => {
    try { renderResult(operationStatus, await api.archiveSnapshotDiff(), t("explore.diffResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  explore.append(clockLabel, clock, timelineButton, explorerButton, diffButton);

  const canonicalDeletion = el("section");
  canonicalDeletion.className = "card";
  canonicalDeletion.append(el("p", t("canonical.kicker")), el("h2", t("canonical.heading")));
  canonicalDeletion.append(el("p", t("canonical.notice")));
  let archivePlan = "";
  const archiveDeleteConfirm = button(t("canonical.confirm"), async () => {
    try {
      const result = await api.archiveExecuteDeletion(archivePlan, "DELETE ORCHID LAMP SOURCE");
      renderResult(operationStatus, result, t("canonical.complete"));
      archiveDeleteConfirm.disabled = true;
      archiveDeletePreview.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "danger");
  archiveDeleteConfirm.disabled = true;
  const archiveDeletePreview = button(t("canonical.preview"), async () => {
    try {
      operationSequence += 1;
      const result = await api.archiveOperate("DELETE_LAMP_SOURCE", "dry_run", `desktop_delete_${operationSequence}`);
      archivePlan = String(result.plan_id ?? "");
      renderResult(operationStatus, result, t("canonical.previewResult"));
      archiveDeleteConfirm.disabled = !archivePlan;
      archiveDeleteConfirm.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  canonicalDeletion.append(archiveDeletePreview, archiveDeleteConfirm);

  const privacy = el("section");
  privacy.className = "card";
  privacy.append(el("p", t("privacy.kicker")), el("h2", t("privacy.heading")));
  const correctionForm = el("form");
  const [replacementLabel, replacement] = field(t("privacy.replacement"), "replacement");
  replacement.required = true;
  replacement.maxLength = 512;
  const [reasonLabel, reason] = field(t("privacy.reason"), "correction-reason");
  reason.required = true;
  reason.maxLength = 512;
  const correctButton = el("button", t("privacy.correct"));
  correctButton.type = "submit";
  correctionForm.append(replacementLabel, replacement, reasonLabel, reason, correctButton);
  correctionForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void api.correct(replacement.value, reason.value)
      .then((value) => renderResult(operationStatus, value, t("privacy.correctResult")))
      .catch((error: unknown) => safeError(operationStatus, error));
  });
  let deletionPlan = "";
  const deletePlanButton = button(t("privacy.preview"), async () => {
    try {
      const result = await api.planDeletion();
      deletionPlan = String(result.plan_id ?? "");
      renderResult(operationStatus, result, t("privacy.previewResult"));
      deleteExecuteButton.disabled = !deletionPlan;
      deleteExecuteButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  const deleteExecuteButton = button(t("privacy.confirm"), async () => {
    try {
      const result = await api.executeDeletion(deletionPlan, "DELETE SYNTHETIC RECORD");
      renderResult(operationStatus, result, t("privacy.complete"));
      deleteExecuteButton.disabled = true;
      deletePlanButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "danger");
  deleteExecuteButton.disabled = true;
  privacy.append(correctionForm, el("hr"), deletePlanButton, deleteExecuteButton);

  const recovery = el("section");
  recovery.className = "card";
  recovery.append(el("p", t("recovery.kicker")), el("h2", t("recovery.heading")));
  let candidateId = "";
  const backupButton = button(t("recovery.health"), async () => {
    try { renderResult(operationStatus, await api.backupStatus(), t("recovery.healthResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  const verifyButton = button(t("recovery.verify"), async () => {
    try { renderResult(operationStatus, await api.verifyBackup(), t("recovery.verifyResult")); }
    catch (error) { safeError(operationStatus, error); }
  });
  const validateButton = button(t("recovery.validate"), async () => {
    try {
      const result = await api.validateRecovery();
      candidateId = String(result.candidate_id ?? "");
      renderResult(operationStatus, result, t("recovery.validateResult"));
      activateButton.disabled = !candidateId;
      activateButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  });
  const activateButton = button(t("recovery.activate"), async () => {
    try {
      const result = await api.activateRecovery(candidateId, "ACTIVATE VALIDATED CANDIDATE");
      renderResult(operationStatus, result, t("recovery.activateResult"));
      activateButton.disabled = true;
      validateButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "primary");
  activateButton.disabled = true;
  recovery.append(backupButton, verifyButton, validateButton, activateButton);

  const exports = el("section");
  exports.className = "card";
  exports.append(el("p", t("export.kicker")), el("h2", t("export.heading")));
  const exportForm = el("form");
  const [purposeLabel, purpose] = field(t("export.purpose"), "export-purpose");
  const [audienceLabel, audience] = field(t("export.audience"), "export-audience");
  const [scopeLabel, scope] = field(t("export.scope"), "export-scope");
  purpose.required = audience.required = scope.required = true;
  purpose.maxLength = audience.maxLength = scope.maxLength = 512;
  const encryptedLabel = el("label");
  const encrypted = el("input");
  encrypted.type = "checkbox";
  encrypted.checked = true;
  encryptedLabel.append(encrypted, document.createTextNode(` ${t("export.encrypt")}`));
  const redactedLabel = el("label");
  const redacted = el("input");
  redacted.type = "checkbox";
  redacted.checked = true;
  redactedLabel.append(redacted, document.createTextNode(` ${t("export.redact")}`));
  const previewButton = el("button", t("export.preview"));
  previewButton.type = "submit";
  let previewId = "";
  const exportButton = button(t("export.confirm"), async () => {
    try {
      const result = await api.executeExport(previewId, "EXPORT SYNTHETIC PACKAGE");
      renderResult(operationStatus, result, t("export.complete"));
      exportButton.disabled = true;
      previewButton.focus();
    } catch (error) { safeError(operationStatus, error); }
  }, "primary");
  exportButton.disabled = true;
  exportForm.append(purposeLabel, purpose, audienceLabel, audience, scopeLabel, scope, encryptedLabel, redactedLabel, previewButton, exportButton);
  exportForm.addEventListener("submit", (event) => {
    event.preventDefault();
    void api.previewExport({ purpose: purpose.value, audience: audience.value, scope: scope.value, encrypted: encrypted.checked, redacted: redacted.checked })
      .then((result) => {
        previewId = String(result.preview_id ?? "");
        renderResult(operationStatus, result, t("export.previewResult"));
        exportButton.disabled = !previewId;
        exportButton.focus();
      })
      .catch((error: unknown) => safeError(operationStatus, error));
  });
  exports.append(exportForm);

  grid.append(privacy, recovery, exports, archive, explore, canonicalDeletion);
  const systemArea = el("section");
  systemArea.className = "system-area";
  systemArea.append(el("h2", "Локальные данные и приватность"), el("p", "Резервные копии, экспорт, исправления и другие операции с локальным хранилищем."), grid);
  main.append(statusRegion, title, sessions, systemArea, operationStatus);
  root.append(header, main);
  void showHome();
}

if (!import.meta.env.VITEST) void mount();
