import axe from "axe-core";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

import type { DesktopApi, SearchView, StatusView, AiRole } from "../src/api";
import { mount } from "../src/main";
import { t } from "../src/i18n";

function syntheticStatus(locked = false): StatusView {
  return {
    locked,
    data_mode: "SYNTHETIC_ONLY",
    real_data_gate: "CLOSED",
    inbound_listener: "NONE",
    outbound_provider: "NOT_CONFIGURED",
    runtime_profile: "SYNTHETIC_LAB",
    build_version: "0.2.0",
    privacy: { processing_location: "LOCAL_ONLY", cloud_storage: "DISABLED", cloud_disclosure: "SYNTHETIC_EXPLICIT_E07_ONLY", telemetry: "OFF" }
  };
}

function mockApi(locked = false): DesktopApi {
  let stateLocked = locked;
  return {
    status: vi.fn(async () => syntheticStatus(stateLocked)),
    aiStatus: vi.fn(async () => ({ runtime_profile: "SYNTHETIC_LAB" as const, local_personal: "NOT_ADMITTED" as const, ai: "NOT_CONFIGURED" as const, provider: "OpenAI", model: "gpt-5.6-luna" })),
    aiListEligible: vi.fn(async () => ({ provider: "OpenAI", model: "gpt-5.6-luna", records: [
      { record_id: "assertion-lamp", version_id: "assertion-lamp-v1", category: "assertion" as const, allowed_roles: ["supporting", "counterevidence"] as AiRole[], display_text: "Синтетическая запись о лампе" },
      { record_id: "assertion-counter", version_id: "assertion-counter-v1", category: "assertion" as const, allowed_roles: ["supporting", "counterevidence"] as AiRole[], display_text: "Синтетический контрзапись" },
      { record_id: "unknown-lamp", version_id: "unknown-lamp-v1", category: "unknown" as const, allowed_roles: ["unknown"] as AiRole[], display_text: "Синтетический вопрос" }
    ], notice: "Synthetic cloud-eligible records only; proposal only." })),
    aiPrepare: vi.fn(async (selected: { recordId: string; role: AiRole }[]) => ({ preview_id: "ai-preview", selected: selected.map((item) => ({ record_id: item.recordId, version_id: "v1", category: item.role === "unknown" ? "unknown" : "assertion", role: item.role })), provider: "OpenAI", model: "gpt-5.6-luna", purpose: "synthetic_evidence_grounded_reflection", retention: "ephemeral", notice: "proposal only" })),
    aiAuthorizeExecute: vi.fn(async () => ({ proposal: { status: "PROPOSED", reflections: [{ statement_id: "statement-1", text: "Синтетическое наблюдение.", supporting_evidence_ids: ["assertion-lamp"], uncertainty: "Рабочая неопределённость.", claim_level: 1 }], counterevidence: ["assertion-counter"], unknowns: [{ unknown_id: "unknown-lamp", uncertainty: "Синтетическая неопределённость." }], questions: [{ question_id: "question-1", unknown_id: "unknown-lamp", text: "Какой синтетический источник мог бы это уточнить?" }] }, notice: "PROPOSED only; nothing was written back." })),
    unlock: vi.fn(async () => { stateLocked = false; return { session_token: "opaque-session" }; }),
    lock: vi.fn(async () => { stateLocked = true; return { locked: true }; }),
    correct: vi.fn(async () => ({ history_preserved: true, version_count: 2 })),
    planDeletion: vi.fn(async () => ({ plan_id: "plan-opaque", affected_counts: { observations: 1 }, external_limitations: ["External copies remain outside local control."] })),
    executeDeletion: vi.fn(async () => ({ receipt_id: "receipt-opaque", content_in_receipt: false })),
    backupStatus: vi.fn(async () => ({ state: "VERIFIED_SYNTHETIC", export_is_backup: false })),
    verifyBackup: vi.fn(async () => ({ verified: true, content_disclosed: false })),
    validateRecovery: vi.fn(async () => ({ candidate_id: "candidate-opaque", validated: true, activated: false, active_vault_preserved: true })),
    activateRecovery: vi.fn(async () => ({ activated: true, previous_vault_retained: true })),
    previewExport: vi.fn(async () => ({ preview_id: "export-opaque", purpose: "portability", audience: "owner", scope: "synthetic", encrypted: true, redacted: true, export_is_backup: false })),
    executeExport: vi.fn(async () => ({ export_id: "complete-opaque", purpose: "portability", audience: "owner", scope: "synthetic", encrypted: true, redacted: true, export_is_backup: false })),
    archiveOperate: vi.fn(async (operation: string) => operation === "DELETE_LAMP_SOURCE" ? ({ plan_id: "orchid-plan", mutated: false }) : ({ operation, fixture_pack: "e03_orchid_station_v1" })),
    archiveTimeline: vi.fn(async (temporalRole: string) => ({ selected_clock: temporalRole, items: [] })),
    archiveExplorer: vi.fn(async () => ({ notice: "Claims are proposals, not facts." })),
    archiveSnapshotDiff: vi.fn(async () => ({ changed: ["claim-lamp"], unresolved_contradictions: 1, completion_percentage: null })),
    archiveExecuteDeletion: vi.fn(async () => ({ receipt_id: "e03-receipt", content_in_receipt: false })),
    reflectionCreate: vi.fn(async () => ({ session_id: "reflection-1", title: "Тест", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: null, turn_count: 0 })),
    reflectionList: vi.fn(async () => ({ sessions: [] })),
    reflectionGet: vi.fn(async () => ({ session_id: "reflection-1", title: "Тест", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: null, turn_count: 0, turns: [] })),
    reflectionAddTurn: vi.fn(async () => ({ turn_id: "turn-1", session_id: "reflection-1", sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "Тест" })),
    reflectionClose: vi.fn(async () => ({ state: "CLOSED" })),
    reflectionDelete: vi.fn(async () => ({ deleted: true, content_in_receipt: false })),
    reflectionSearch: vi.fn(async (query: string) => ({ query, state: "ALL" as const, total_matches: query ? 1 : 0, returned_count: query ? 1 : 0, offset: 0, limit: 50, truncated: false, has_more: false, results: query ? [{ session_id: "reflection-1", session_title: "Тест", session_state: "ACTIVE" as const, session_updated_at: "2026-01-01T00:00:00Z", match_kind: "USER_TURN" as const, turn_id: "turn-1", turn_sequence: 1, excerpt: query }] : [] })),
    explorationStart: vi.fn(async () => ({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] })),
    explorationGet: vi.fn(async () => ({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] })),
    explorationAnswer: vi.fn(async () => ({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] })),
    explorationSkip: vi.fn(async () => ({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] })),
    formulationPropose: vi.fn(async () => ({})),
    formulationCorrect: vi.fn(async () => ({})),
    formulationAccept: vi.fn(async () => ({})),
    formulationReject: vi.fn(async () => ({})),
    actionOptions: vi.fn(async () => ({ session_id: "reflection-1", anchor_type: null, anchor_id: null, options: [{ template_id: "PAUSE" as const, template_version: "v1", text: "Ничего не предпринимать сейчас и оставить вопрос открытым." }] })),
    actionList: vi.fn(async () => ({ session_id: "reflection-1", plans: [] })),
    actionCreate: vi.fn(async () => ({ plan_id: "plan-1", session_id: "reflection-1", version: 1, supersedes_plan_id: null, status: "CURRENT" as const, basis_snapshot_id: null, basis_formulation_id: null, anchor_type: null, anchor_id: null, user_goal: "Цель", template_id: "PAUSE" as const, template_version: "v1", action_text: "Пауза", method_version: "v1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", outcome: null })),
    actionRecordOutcome: vi.fn(async () => ({ outcome_id: "outcome-1", status: "DONE" as const, note_text: null, created_at: "2026-01-01T00:00:00Z" }))
  };
}

function byText(text: string): HTMLButtonElement {
  const found = [...document.querySelectorAll<HTMLButtonElement>("button")].find((node) => node.textContent === text);
  if (!found) throw new Error(`Missing button: ${text}`);
  return found;
}

async function click(node: HTMLElement): Promise<void> {
  node.click();
  await new Promise((resolve) => setTimeout(resolve, 0));
}

function selectSyntheticEvidence(recordId: string, role: string): void {
  const checkbox = document.querySelector<HTMLInputElement>(`input[aria-label="Выбрать запись ${recordId}"]`)!;
  checkbox.checked = true;
  checkbox.dispatchEvent(new Event("change"));
  const select = document.querySelector<HTMLSelectElement>(`select[aria-label="Роль для ${recordId}"]`)!;
  select.value = role;
  select.dispatchEvent(new Event("change"));
}

describe("E02 bounded desktop UI", () => {
  it("E07 renders a validated AI proposal as a Russian-first proposal-only card", async () => {
    const api = mockApi(false);
    await mount(api);
    selectSyntheticEvidence("assertion-lamp", "supporting");
    selectSyntheticEvidence("assertion-counter", "counterevidence");
    selectSyntheticEvidence("unknown-lamp", "unknown");
    await click(byText("Показать предварительное раскрытие"));
    const preview = document.querySelector<HTMLElement>(".ai-preview-card")!;
    expect(preview.textContent).toContain("ПРЕДВАРИТЕЛЬНОЕ РАСКРЫТИЕ");
    expect(preview.textContent).toContain("OpenAI");
    expect(preview.textContent).toContain("gpt-5.6-luna");
    expect(preview.textContent).toContain("Поддерживающее");
    expect(preview.textContent).toContain("Контраргумент");
    expect(preview.textContent).toContain("Неизвестное");
    expect(api.aiPrepare).toHaveBeenCalledWith([{ recordId: "assertion-lamp", role: "supporting" }, { recordId: "assertion-counter", role: "counterevidence" }, { recordId: "unknown-lamp", role: "unknown" }]);
    await click(byText("Отправить выбранные синтетические данные"));
    const card = document.querySelector<HTMLElement>(".ai-proposal-card")!;
    for (const text of ["AI-ПРЕДЛОЖЕНИЕ · LAB", "PROPOSED", "Наблюдения / рабочие предложения", "Синтетическое наблюдение.", "уровень утверждения", "основания", "Контраргументы", "Что остаётся неизвестным", "Вопросы", "автоматически не сохраняется"]) expect(card.textContent).toContain(text);
    expect(card.textContent?.match(/Синтетическая неопределённость\./g)).toHaveLength(1);
    expect(card.textContent).not.toContain("применить");
    expect(api.aiAuthorizeExecute).toHaveBeenCalledTimes(1);
  });

  it("V3-A2 renders a closed analytical workspace without analytics write controls", async () => {
    const api = mockApi(false);
    const session = { session_id: "reflection-1", title: "Тест", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:02:00Z", closed_at: "2026-01-01T00:02:00Z", turn_count: 1, turns: [{ turn_id: "turn-1", session_id: "reflection-1", sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:01Z", content: "Синтетический ответ" }] };
    vi.mocked(api.reflectionCreate).mockResolvedValue(session);
    vi.mocked(api.reflectionGet).mockResolvedValue(session);
    vi.mocked(api.explorationGet).mockResolvedValue({
      context: [
        { context_item_id: "known", dimension: "user_report", kind: "KNOWN", text: "Известное", state: "RECORDED", source_turn_ids: ["turn-1"], created_at: "2026-01-01T00:00:01Z" },
        { context_item_id: "unknown", dimension: "future_dimension", kind: "UNKNOWN", text: "Пропущенное", state: "SKIPPED", source_turn_ids: ["turn-1"], created_at: "2026-01-01T00:00:02Z" },
        { context_item_id: "conflict", dimension: "context", kind: "CONTRADICTION", text: "Разные ответы", state: "OPEN", source_turn_ids: ["turn-1"], created_at: "2026-01-01T00:00:03Z" }
      ],
      hypotheses: [{ hypothesis_id: "hypothesis-1", proposal_text: "Рабочий вариант", uncertainty_text: "Не факт", discriminator_text: "Уточнение", context_refs: [{ context_item_id: "known", relation: "SUPPORT", source_turn_ids: ["turn-1"] }, { context_item_id: "conflict", relation: "COUNTEREVIDENCE", source_turn_ids: ["turn-1"] }, { context_item_id: "unknown", relation: "UNKNOWN", source_turn_ids: ["turn-1"] }] }],
      next_question: null,
      snapshots: [{ snapshot_id: "snapshot-1", version: 1, created_at: "2026-01-01T00:00:01Z" }],
      formulations: [{ formulation_id: "formulation-1", version: 1, parent_formulation_id: null, status: "CURRENT", summary: "Синтетическая формулировка", correction_text: null, created_at: "2026-01-01T00:00:02Z", updated_at: "2026-01-01T00:00:02Z" }]
    });
    await mount(api);
    await click(byText("Сессии"));
    const title = document.querySelector<HTMLInputElement>("#reflection-title")!;
    title.value = "Тест";
    title.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const analytics = document.querySelector<HTMLElement>(".analytical-workspace")!;
    expect(analytics.textContent).toContain("АНАЛИТИКА СЕССИИ");
    for (const required of ["Текущая рабочая формулировка", "Как менялась формулировка", "Матрица контекста", "Поддерживает", "Противоречит / контрпример", "Остаётся неизвестным", "Пропущено / «не знаю»", "Противоречия / разные ответы", "Хронология сессии", "ваш ответ №1"]) expect(analytics.textContent).toContain(required);
    expect(analytics.querySelector("button, input, textarea, select")).toBeNull();
    expect(document.querySelector<HTMLTextAreaElement>("#reflection-turn")!.disabled).toBe(true);
    expect(byText("Завершить сессию").disabled).toBe(true);
    expect(byText("Удалить сессию").disabled).toBe(false);
  });

  it("presents the Russian local reflection-session entry point", async () => {
    const api = mockApi(false);
    await mount(api);
    expect(document.body.textContent).toContain("МОЁ ПРОСТРАНСТВО");
    expect(byText("Начать первую сессию")).toBeTruthy();
    await click(byText("Сессии"));
    const title = document.querySelector<HTMLInputElement>("#reflection-title")!;
    title.value = "Синтетическая сессия";
    title.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.reflectionCreate).toHaveBeenCalledWith("Синтетическая сессия");
    expect(byText("Добавить в сессию")).toBeTruthy();
    const turn = document.querySelector<HTMLTextAreaElement>("#reflection-turn")!;
    expect(turn.name).toBe("reflection-turn");
    expect(turn.getAttribute("aria-label")).toBe("Ваш текст");
    expect(turn.labels?.[0]?.textContent).toBe("Ваш текст");
    expect(turn.maxLength).toBe(12000);
  });

  it("V3-E makes first use and the product routes understandable without a completion claim", async () => {
    const api = mockApi(false);
    await mount(api);
    expect(document.body.textContent).toContain("МОЁ ПРОСТРАНСТВО");
    expect(document.body.textContent).toContain("Начать первую сессию");
    expect(document.body.textContent).not.toMatch(/\b\d+%|прогресс|обязательно|сроч/i);
    await click(byText("Начать первую сессию"));
    expect(document.querySelector("#reflection-title")).not.toBeNull();
    for (const label of ["Главная", "Сессии", "К чему вернуться", "Динамика"]) expect(byText(label)).toBeTruthy();
  });

  it("V3-E lists recorded sessions deterministically and continues the sole active one", async () => {
    const api = mockApi(false);
    const closed = { session_id: "a", title: "Закрытая", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 2 };
    const active = { session_id: "b", title: "Активная", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-02T00:00:00Z", updated_at: "2026-01-02T00:00:00Z", closed_at: null, turn_count: 1 };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [closed, active] });
    vi.mocked(api.reflectionGet).mockImplementation(async (id) => id === "b" ? { ...active, turns: [] } : { ...closed, turns: [] });
    await mount(api);
    const home = document.querySelector<HTMLElement>(".product-home")!;
    expect(home.textContent).toContain("Закрыта · только чтение");
    expect(home.textContent!.indexOf("Активная")).toBeLessThan(home.textContent!.indexOf("Закрытая"));
    await click(byText("Продолжить текущую сессию"));
    expect(api.reflectionGet).toHaveBeenLastCalledWith("b");
    for (const label of ["1. Запись", "2. Исследование", "3. Обзор", "4. Итог и следующий шаг"]) expect(byText(label)).toBeTruthy();
  });

  it("shows the SYNTHETIC LAB boundary and Quick Capture writes exact text through an ordinary session", async () => {
    const api = mockApi(false);
    const created = { session_id: "quick", title: "Моя запись", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-02T00:00:00Z", updated_at: "2026-01-02T00:00:00Z", closed_at: null, turn_count: 1, turns: [] };
    vi.mocked(api.reflectionCreate).mockResolvedValue(created); vi.mocked(api.reflectionGet).mockResolvedValue(created);
    await mount(api);
    expect(document.body.textContent).toContain("SYNTHETIC LAB"); expect(document.body.textContent).toContain("Режим личных данных пока не допущен");
    const title = document.querySelector<HTMLInputElement>("#quick-capture-title")!; const text = document.querySelector<HTMLTextAreaElement>("#quick-capture-text")!;
    title.value = "Моя запись"; text.value = "Точный синтетический текст"; text.form!.requestSubmit(); await new Promise((resolve) => setTimeout(resolve, 0)); await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.reflectionCreate).toHaveBeenCalledWith("Моя запись"); expect(api.reflectionAddTurn).toHaveBeenCalledWith("quick", "Точный синтетический текст"); expect(api.reflectionGet).toHaveBeenCalledWith("quick");
  });

  it("Quick Capture ignores empty text and completes its authorized first turn despite navigation", async () => {
    const api = mockApi(false); let resolveCreate!: (value: { session_id: string; title: string; state: "ACTIVE"; retention: "ENCRYPTED_LOCAL"; created_at: string; updated_at: string; closed_at: null; turn_count: number; turns: [] }) => void;
    vi.mocked(api.reflectionCreate).mockImplementationOnce(() => new Promise((resolve) => { resolveCreate = resolve; })); await mount(api);
    const text = document.querySelector<HTMLTextAreaElement>("#quick-capture-text")!; text.value = "   "; text.form!.requestSubmit(); expect(api.reflectionCreate).not.toHaveBeenCalled();
    text.value = "Точный текст"; text.form!.requestSubmit(); await click(byText("Динамика")); resolveCreate({ session_id: "quick", title: "Запись", state: "ACTIVE", retention: "ENCRYPTED_LOCAL", created_at: "2026-01-02T00:00:00Z", updated_at: "2026-01-02T00:00:00Z", closed_at: null, turn_count: 0, turns: [] }); await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.reflectionAddTurn).toHaveBeenCalledWith("quick", "Точный текст"); expect(document.querySelector(".longitudinal-workspace")).not.toBeNull();
  });

  it("filters the Home session library without writes", async () => {
    const api = mockApi(false); const active = { session_id: "a", title: "Лампа", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-02T00:00:00Z", updated_at: "2026-01-02T00:00:00Z", closed_at: null, turn_count: 1 }; const closed = { ...active, session_id: "b", title: "Архив", state: "CLOSED" as const, created_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z" };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [active, closed] }); await mount(api);
    const search = document.querySelector<HTMLInputElement>("#session-title-filter")!; search.value = "арх"; search.dispatchEvent(new Event("input")); expect(document.body.textContent).toContain("Архив"); expect(document.body.textContent).not.toContain("Лампа");
    const state = document.querySelector<HTMLSelectElement>("#session-state-filter")!; state.value = "ACTIVE"; state.dispatchEvent(new Event("change")); expect(document.body.textContent).not.toContain("Архив"); expect(api.reflectionCreate).not.toHaveBeenCalled(); expect(api.reflectionAddTurn).not.toHaveBeenCalled();
  });

  it("keeps a newer session view when the initial asynchronous list resolves late", async () => {
    const api = mockApi(false);
    let resolveList!: (result: { sessions: [] }) => void;
    vi.mocked(api.reflectionList).mockImplementationOnce(() => new Promise((resolve) => { resolveList = resolve; }));
    await mount(api);
    await click(byText("Сессии"));
    const title = document.querySelector<HTMLInputElement>("#reflection-title")!;
    title.value = "Синтетическая сессия";
    title.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    resolveList({ sessions: [] });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(byText("Добавить в сессию")).toBeTruthy();
  });

  it("V3-E keeps a newer longitudinal route when an earlier Return load resolves late", async () => {
    const api = mockApi(false);
    let resolveReturn!: (result: { sessions: [] }) => void;
    vi.mocked(api.reflectionList)
      .mockResolvedValueOnce({ sessions: [] })
      .mockImplementationOnce(() => new Promise((resolve) => { resolveReturn = resolve; }))
      .mockResolvedValueOnce({ sessions: [] });
    await mount(api);
    await click(byText("К чему вернуться"));
    await click(byText("Динамика"));
    expect(document.querySelector(".longitudinal-workspace")).not.toBeNull();
    resolveReturn({ sessions: [] });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector(".longitudinal-workspace")).not.toBeNull();
    expect(document.querySelector(".return-workspace")).toBeNull();
  });

  it("V3-D opens a neutral empty Return workspace and preserves newer navigation", async () => {
    const api = mockApi(false);
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [] });
    await mount(api);
    await click(byText("К чему вернуться"));
    const workspace = document.querySelector<HTMLElement>(".return-workspace")!;
    expect(workspace.textContent).toContain("К ЧЕМУ ВЕРНУТЬСЯ");
    expect(workspace.textContent).toContain("Таких сохранённых записей пока нет.");
    expect(workspace.textContent).toContain("не означают срочность");
    expect(workspace.textContent).toContain("не означает разрешение");
    expect(workspace.textContent).toContain("не означает эффективность");
  });

  it("V3-F presents a CLOSED source as read-only follow-up context", async () => {
    const api = mockApi(false);
    const session = { session_id: "return-a", title: "Исходная сессия", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 1, turns: [{ turn_id: "turn-return-a", session_id: "return-a", sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "Синтетический исходный текст" }] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [session] });
    vi.mocked(api.reflectionGet).mockResolvedValue(session);
    vi.mocked(api.explorationGet).mockResolvedValue({ context: [{ context_item_id: "unknown-return", dimension: "context", kind: "UNKNOWN", text: "Сохранённый вопрос", state: "OPEN", source_turn_ids: ["turn-return-a"], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [], next_question: null, snapshots: [], formulations: [] });
    vi.mocked(api.actionList).mockResolvedValue({ session_id: "return-a", plans: [] });
    await mount(api); await click(byText("К чему вернуться"));
    const workspace = document.querySelector<HTMLElement>(".return-workspace")!;
    expect(workspace.textContent).toContain("Записано ранее");
    expect(workspace.textContent).toContain("Источник: ваш ответ №1");
    await click(byText("Начать новую сессию"));
    expect(document.querySelector(".follow-up-workspace")?.textContent).toContain("Записано ранее");
    expect(document.querySelector(".follow-up-workspace")?.textContent).toContain("Источник: ваш ответ №1");
    expect(document.querySelector(".follow-up-workspace")?.textContent).toContain("Закрыта · только чтение");
    expect(document.querySelector<HTMLTextAreaElement>("#follow-up-text")?.value).toBe("");
  });

  it("V3-F explicitly continues an ACTIVE Return source", async () => {
    const api = mockApi(false);
    const session = { session_id: "return-active", title: "Активная исходная", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: null, turn_count: 1, turns: [{ turn_id: "turn-active", session_id: "return-active", sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "Синтетический исходный текст" }] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [session] }); vi.mocked(api.reflectionGet).mockResolvedValue(session); vi.mocked(api.explorationGet).mockResolvedValue({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] });
    await mount(api); await click(byText("К чему вернуться")); await click(byText("Продолжить эту сессию"));
    expect(api.reflectionGet).toHaveBeenLastCalledWith("return-active");
    expect(document.body.textContent).toContain("АКТИВНАЯ СЕССИЯ");
  });

  it("V3-F sends only exact new user text to the ordinary session APIs", async () => {
    const api = mockApi(false);
    const source = { session_id: "source", title: "Исходная", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 1, turns: [] };
    const created = { ...source, session_id: "new", title: "Моя новая сессия", state: "ACTIVE" as const, closed_at: null, turn_count: 1, turns: [{ turn_id: "new-turn", session_id: "new", sequence: 1, actor: "USER" as const, created_at: "2026-01-02T00:00:00Z", content: "Только новый текст" }] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [source] }); vi.mocked(api.reflectionGet).mockImplementation(async (id) => id === "new" ? created : source); vi.mocked(api.reflectionCreate).mockResolvedValue(created); vi.mocked(api.explorationGet).mockResolvedValue({ context: [{ context_item_id: "old", dimension: "context", kind: "UNKNOWN", text: "Исторический текст", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [], next_question: null, snapshots: [], formulations: [] });
    await mount(api); await click(byText("К чему вернуться")); await click(byText("Начать новую сессию"));
    const title = document.querySelector<HTMLInputElement>("#follow-up-title")!; const text = document.querySelector<HTMLTextAreaElement>("#follow-up-text")!; title.value = "Моя новая сессия"; text.value = "Только новый текст"; text.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0)); await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.reflectionCreate).toHaveBeenLastCalledWith("Моя новая сессия");
    expect(api.reflectionAddTurn).toHaveBeenLastCalledWith("new", "Только новый текст");
    expect(vi.mocked(api.reflectionAddTurn).mock.calls[0]?.[1]).not.toContain("Исторический текст");
    expect(document.body.textContent).toContain("Моя новая сессия");
  });

  it("V3-F cancel before submit creates nothing and returns to Return", async () => {
    const api = mockApi(false);
    const source = { session_id: "source", title: "Исходная", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 1, turns: [] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [source] }); vi.mocked(api.reflectionGet).mockResolvedValue(source); vi.mocked(api.explorationGet).mockResolvedValue({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] });
    await mount(api); await click(byText("К чему вернуться")); await click(byText("Начать новую сессию"));
    await click(byText("Отмена"));
    expect(document.querySelector(".return-workspace")).not.toBeNull(); expect(api.reflectionAddTurn).not.toHaveBeenCalled();
    expect(api.reflectionCreate).not.toHaveBeenCalled();
  });

  it("V3-F completes an authorized write during newer navigation without replacing it", async () => {
    const api = mockApi(false);
    const source = { session_id: "source", title: "Исходная", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 1, turns: [] };
    const created = { ...source, session_id: "new", title: "Новая", state: "ACTIVE" as const, closed_at: null };
    let resolveCreate!: (value: typeof created) => void;
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [source] }); vi.mocked(api.reflectionGet).mockResolvedValue(source); vi.mocked(api.explorationGet).mockResolvedValue({ context: [{ context_item_id: "historical", dimension: "context", kind: "UNKNOWN", text: "Исторический текст", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [], next_question: null, snapshots: [], formulations: [] }); vi.mocked(api.reflectionCreate).mockImplementationOnce(() => new Promise((resolve) => { resolveCreate = resolve; }));
    await mount(api); await click(byText("К чему вернуться")); await click(byText("Начать новую сессию"));
    const title = document.querySelector<HTMLInputElement>("#follow-up-title")!; const text = document.querySelector<HTMLTextAreaElement>("#follow-up-text")!; title.value = "Новая"; text.value = "Точный новый текст"; text.form!.requestSubmit();
    expect(byText("Начать новую сессию").disabled).toBe(true); expect(byText("Отмена").disabled).toBe(true);
    await click(byText("Динамика")); expect(document.querySelector(".longitudinal-workspace")).not.toBeNull(); resolveCreate(created); await new Promise((resolve) => setTimeout(resolve, 0)); await new Promise((resolve) => setTimeout(resolve, 0));
    expect(api.reflectionAddTurn).toHaveBeenLastCalledWith("new", "Точный новый текст"); expect(vi.mocked(api.reflectionAddTurn).mock.calls.at(-1)?.[1]).not.toContain("Исторический текст"); expect(document.querySelector(".longitudinal-workspace")).not.toBeNull(); expect(document.querySelector(".follow-up-workspace")).toBeNull();
  });

  it("V3-F keeps the follow-up surface and reports failure without false success", async () => {
    const api = mockApi(false);
    const source = { session_id: "source", title: "Исходная", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 1, turns: [] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [source] }); vi.mocked(api.reflectionGet).mockResolvedValue(source); vi.mocked(api.explorationGet).mockResolvedValue({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] }); vi.mocked(api.reflectionCreate).mockRejectedValue("CREATE_FAILED");
    await mount(api); await click(byText("К чему вернуться")); await click(byText("Начать новую сессию"));
    const text = document.querySelector<HTMLTextAreaElement>("#follow-up-text")!; text.value = "Новый текст"; text.form!.requestSubmit(); await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector(".follow-up-workspace")).not.toBeNull(); expect(document.querySelector("#operation-status")?.textContent).toContain("CREATE_FAILED"); expect(document.body.textContent).not.toContain("АКТИВНАЯ СЕССИЯ");
  });

  it("V3-B/C opens the global read-only longitudinal workspace for two synthetic sessions", async () => {
    const api = mockApi(false);
    const sessions = ["a", "b"].map((id, index) => ({ session_id: id, title: `Сессия ${id}`, state: index ? "ACTIVE" as const : "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: `2026-01-0${index + 1}T00:00:00Z`, updated_at: `2026-01-0${index + 1}T00:00:00Z`, closed_at: index ? null : "2026-01-01T00:00:00Z", turn_count: 1, turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER" as const, created_at: `2026-01-0${index + 1}T00:00:00Z`, content: "синтетический" }] }));
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions }); vi.mocked(api.reflectionGet).mockImplementation(async (id) => sessions.find((item) => item.session_id === id)!);
    vi.mocked(api.explorationGet).mockImplementation(async (id) => ({ context: [{ context_item_id: `known-${id}`, dimension: "context", kind: "KNOWN", text: "Точная запись", state: "RECORDED", source_turn_ids: [`turn-${id}`], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: `unknown-${id}`, dimension: "context", kind: "UNKNOWN", text: "Открытый вопрос", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: `contradiction-${id}`, dimension: "context", kind: "CONTRADICTION", text: "Разные ответы", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [{ hypothesis_id: `h-${id}`, template_id: "contextual", proposal_text: "Вариант", uncertainty_text: "Неизвестно", discriminator_text: "Уточнить", context_refs: [] }], next_question: null, snapshots: [], formulations: [{ formulation_id: `f-${id}`, version: 1, status: "CURRENT", summary: `Формулировка ${id}`, correction_text: null, created_at: "2026-01-01T00:00:00Z" }] }));
    vi.mocked(api.actionList).mockResolvedValue({ session_id: "a", plans: [] }); await mount(api); await click(byText("Динамика"));
    const workspace = document.querySelector<HTMLElement>(".longitudinal-workspace")!; for (const text of ["Обзор записей", "История рабочих формулировок", "Что повторялось в записях", "Рабочие альтернативы", "Неизвестное и противоречия", "Мои следующие шаги и отметки", "Сравнить две сессии", "Хронология записанных событий продукта", "Точная запись"]) expect(workspace.textContent).toContain(text);
    expect(workspace.querySelector("button, textarea")).toBeNull(); expect(workspace.querySelectorAll("select")).toHaveLength(2);
  });

  it("V3-B/C presents truthful guided coverage and complete singleton/session comparison detail", async () => {
    const api = mockApi(false); const sessions = ["a", "b"].map((id, index) => ({ session_id: id, title: `Сессия ${id}`, state: index ? "ACTIVE" as const : "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: `2026-01-0${index + 1}T00:00:00Z`, updated_at: `2026-01-0${index + 1}T00:00:00Z`, closed_at: index ? null : "2026-01-01T00:00:00Z", turn_count: 1, turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "синтетический" }] }));
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions }); vi.mocked(api.reflectionGet).mockImplementation(async (id) => sessions.find((item) => item.session_id === id)!);
    vi.mocked(api.explorationGet).mockImplementation(async (id) => id === "b" ? ({ context: [], hypotheses: [], snapshots: [], formulations: [], next_question: null }) : ({ context: [{ context_item_id: "known-a", dimension: "context", kind: "KNOWN", text: "Точная связь", state: "RECORDED", source_turn_ids: ["turn-a"], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: "unknown-a", dimension: "context", kind: "UNKNOWN", text: "Открытый вопрос", state: "OPEN", source_turn_ids: ["turn-a"], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: "contradiction-a", dimension: "context", kind: "CONTRADICTION", text: "Разные ответы", state: "OPEN", source_turn_ids: ["turn-a"], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [{ hypothesis_id: "h-a", template_id: "contextual", proposal_text: "Рабочая альтернатива", uncertainty_text: "Неопределённость", discriminator_text: "Уточнить", context_refs: [{ context_item_id: "known-a", relation: "SUPPORT", source_turn_ids: ["turn-a"] }] }], next_question: null, snapshots: [{ snapshot_id: "snapshot-a", version: 1 }], formulations: [{ formulation_id: "f-a", version: 1, status: "CURRENT", summary: "CURRENT A", correction_text: null }] }));
    vi.mocked(api.actionList).mockImplementation(async (id) => ({ session_id: id, plans: id === "a" ? [{ plan_id: "plan-a", session_id: "a", version: 2, supersedes_plan_id: null, status: "CURRENT" as const, basis_snapshot_id: "snapshot-a", basis_formulation_id: "f-a", anchor_type: "FORMULATION" as const, anchor_id: "f-a", user_goal: "V3BC-GOAL-A", template_id: "PAUSE" as const, template_version: "v1", action_text: "V3BC-ACTION-A", method_version: "v1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", outcome: { outcome_id: "outcome-a", status: "DONE" as const, note_text: "V3BC-OUTCOME-A", created_at: "2026-01-01T00:00:00Z" } }] : [] }));
    await mount(api); await click(byText("Динамика")); const workspace = document.querySelector<HTMLElement>(".longitudinal-workspace")!;
    for (const text of ["Сессий с guided exploration: 1", "Открытый вопрос", "Открыто", "Разные ответы", "Точная связь", "V3BC-GOAL-A", "V3BC-ACTION-A", "V3BC-OUTCOME-A", "ваш ответ №1"]) expect(workspace.textContent).toContain(text);
    const b = document.querySelector<HTMLSelectElement>("#longitudinal-session-b")!; b.value = "b"; b.dispatchEvent(new Event("change")); await new Promise((resolve) => setTimeout(resolve, 0));
    for (const text of ["CURRENT A", "CURRENT формулировка не записана", "Не записано в этой сессии", "Гипотеза contextual", "Действие A"]) expect(workspace.textContent).toContain(text);
    expect(workspace.textContent).not.toMatch(/overall.score|success.rate|effectiveness/i); expect(workspace.querySelector("button, textarea")).toBeNull();
  });

  it("T3 renders malicious synthetic markup as inert text", async () => {
    const api = mockApi(false);
    const canary = '<img src=x onerror="window.__pwned=1"><script>bad()</script>';
    vi.mocked(api.correct).mockResolvedValue({ current_text: canary, history_preserved: true });
    await mount(api);
    const replacement = document.querySelector<HTMLInputElement>("#replacement")!;
    const reason = document.querySelector<HTMLInputElement>("#correction-reason")!;
    replacement.value = canary;
    reason.value = "Synthetic correction";
    replacement.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const status = document.querySelector("#operation-status")!;
    expect(status.textContent).toContain(canary);
    expect(status.querySelector("script")).toBeNull();
    expect(status.querySelector("img")).toBeNull();
  });

  it("T4 requires a dry-run before deletion and returns focus", async () => {
    const api = mockApi(false);
    await mount(api);
    const confirm = byText(t("privacy.confirm"));
    expect(confirm.disabled).toBe(true);
    await click(byText(t("privacy.preview")));
    expect(confirm.disabled).toBe(false);
    expect(document.activeElement).toBe(confirm);
    await click(confirm);
    expect(api.executeDeletion).toHaveBeenCalledWith("plan-opaque", "DELETE SYNTHETIC RECORD");
    expect(document.querySelector("#operation-status")!.textContent).toContain("ограничени");
  });

  it("T5 keeps recovery validation separate from activation", async () => {
    const api = mockApi(false);
    await mount(api);
    const activate = byText(t("recovery.activate"));
    expect(activate.disabled).toBe(true);
    await click(byText(t("recovery.validate")));
    expect(activate.disabled).toBe(false);
    expect(document.querySelector("#operation-status")!.textContent).toContain("активное хранилище не изменено");
    await click(activate);
    expect(api.activateRecovery).toHaveBeenCalledWith("candidate-opaque", "ACTIVATE VALIDATED CANDIDATE");
  });

  it("T6 previews purpose, audience, scope and protection before export", async () => {
    const api = mockApi(false);
    await mount(api);
    (document.querySelector("#export-purpose") as HTMLInputElement).value = "portability";
    (document.querySelector("#export-audience") as HTMLInputElement).value = "owner";
    (document.querySelector("#export-scope") as HTMLInputElement).value = "synthetic";
    const form = (document.querySelector("#export-purpose") as HTMLInputElement).form!;
    form.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector("#operation-status")!.textContent).toContain("пока ничего не записано");
    const execute = byText(t("export.confirm"));
    expect(execute.disabled).toBe(false);
    await click(execute);
    expect(api.executeExport).toHaveBeenCalledWith("export-opaque", "EXPORT SYNTHETIC PACKAGE");
  });

  it("T7 has accessible names, associations, status semantics and no serious axe violations", async () => {
    await mount(mockApi(false));
    const result = await axe.run(document, { rules: { "color-contrast": { enabled: false } } });
    expect(result.violations).toEqual([]);
    expect(document.querySelector("#operation-status")?.getAttribute("aria-live")).toBe("polite");
    const stylesheet = readFileSync("src/styles.css", "utf8");
    expect(stylesheet).toContain("@media (prefers-reduced-motion: reduce)");
    for (const input of document.querySelectorAll<HTMLInputElement>("input[type=text], input[type=password]")) {
      expect(document.querySelector(`label[for="${input.id}"]`)).not.toBeNull();
    }
  });

  it("T7 unlock errors clear the secret and return focus to the field", async () => {
    const api = mockApi(true);
    vi.mocked(api.unlock).mockRejectedValue("UNLOCK_REJECTED");
    await mount(api);
    const secret = document.querySelector<HTMLInputElement>("#unlock-secret")!;
    secret.value = "synthetic-secret";
    secret.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(secret.value).toBe("");
    expect(document.activeElement).toBe(secret);
    expect(document.querySelector("#unlock-error")!.textContent).toContain(t("unlock.rejected"));
  });

  it("field preview search finds a local match and opens the source session", async () => {
    const api = mockApi(false);
    await mount(api);
    await click(byText("Поиск"));
    const search = document.querySelector<HTMLInputElement>("#search-query")!;
    search.value = "лампа";
    await click(byText("Найти"));
    expect(api.reflectionSearch).toHaveBeenCalledWith("лампа", "ALL", 50, 0);
    expect(document.querySelector(".search-meta")?.textContent).toContain("Совпадений: 1");
    expect(document.querySelector(".search-result")?.textContent).toContain("Совпадение в вашей записи №1");
    await click(byText("Открыть сессию"));
    expect(api.reflectionGet).toHaveBeenLastCalledWith("reflection-1");
    expect(document.querySelector(".session-header")).not.toBeNull();
  });

  it("field preview review hub shows persisted states without scoring and opens a session", async () => {
    const api = mockApi(false);
    const session = { session_id: "hub-1", title: "Обзорная сессия", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: null, turn_count: 1, turns: [{ turn_id: "turn-hub", session_id: "hub-1", sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "Синтетическая запись" }] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [session] });
    vi.mocked(api.reflectionGet).mockResolvedValue(session);
    vi.mocked(api.explorationGet).mockResolvedValue({ context: [{ context_item_id: "open-hub", dimension: "context", kind: "UNKNOWN", text: "Открытый вопрос обзора", state: "OPEN", source_turn_ids: ["turn-hub"], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [], next_question: null, snapshots: [], formulations: [{ formulation_id: "f-hub", version: 1, status: "CURRENT", summary: "Рабочая формулировка обзора", correction_text: null, created_at: "2026-01-01T00:00:00Z" }] });
    vi.mocked(api.actionList).mockResolvedValue({ session_id: "hub-1", plans: [{ plan_id: "plan-hub", session_id: "hub-1", version: 1, supersedes_plan_id: null, status: "CURRENT" as const, basis_snapshot_id: null, basis_formulation_id: null, anchor_type: null, anchor_id: null, user_goal: "Цель", template_id: "PAUSE" as const, template_version: "v1", action_text: "Сохранённый шаг обзора", method_version: "v1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", outcome: { outcome_id: "outcome-hub", status: "DONE" as const, note_text: null, created_at: "2026-01-01T00:00:00Z" } }] });
    await mount(api);
    await click(byText("Обзор"));
    const hub = document.querySelector<HTMLElement>(".review-hub")!;
    for (const text of ["МОЙ ОБЗОР", "АКТИВНЫЕ СЕССИИ", "ОТКРЫТЫЕ / ПРОПУЩЕННЫЕ ВОПРОСЫ", "Открытый вопрос обзора", "ТЕКУЩИЕ РАБОЧИЕ ФОРМУЛИРОВКИ", "Рабочая формулировка обзора", "СОХРАНЁННЫЕ ШАГИ", "Сохранённый шаг обзора", "ИСХОДЫ / OUTCOMES", "ПОСЛЕДНИЕ СЕССИИ", "не означает истинность", "не о его эффективности"]) expect(hub.textContent).toContain(text);
    const itemsText = [...hub.querySelectorAll<HTMLElement>(".review-item")].map((node) => node.textContent).join(" ");
    expect(itemsText).not.toMatch(/приоритет|срочно|оценк|прогресс|эффективност|важно|лучший|рекомендац/i);
    await click(byText("Открыть сессию"));
    expect(api.reflectionGet).toHaveBeenLastCalledWith("hub-1");
  });

  it("field preview home exposes Search and Review routes with AI secondary and build identity", async () => {
    const api = mockApi(false);
    await mount(api);
    const home = document.querySelector<HTMLElement>(".product-home")!;
    expect(home.textContent).toContain("ГЛАВНЫЕ РАЗДЕЛЫ");
    for (const label of ["Поиск", "Обзор", "Сессии", "К чему вернуться", "Динамика"]) expect(home.textContent).toContain(label);
    expect(document.body.textContent).toContain("SYNTHETIC LAB");
    expect(document.body.textContent).toContain("Режим личных данных пока не допущен");
    expect(document.body.textContent).toContain("сборка 0.2.0");
    expect(document.body.textContent).toContain("профиль: SYNTHETIC_LAB");
    expect(document.body.textContent).toContain("REAL_DATA_GATE: CLOSED");
    expect(document.querySelector(".ai-eligible-row")).not.toBeNull();
  });

  it("field preview stale search load cannot replace a newer destination", async () => {
    const api = mockApi(false);
    let resolveSearch!: (value: SearchView) => void;
    vi.mocked(api.reflectionSearch).mockImplementationOnce(() => new Promise((resolve) => { resolveSearch = resolve; }));
    await mount(api);
    await click(byText("Поиск"));
    const search = document.querySelector<HTMLInputElement>("#search-query")!;
    search.value = "лампа";
    await click(byText("Найти"));
    await click(byText("Сессии"));
    resolveSearch({ query: "лампа", state: "ALL", total_matches: 0, returned_count: 0, offset: 0, limit: 50, truncated: false, has_more: false, results: [] });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(document.querySelector(".search-workspace")).toBeNull();
    expect(byText("Начать новую сессию")).toBeTruthy();
  });
});

describe("E03 bounded archive UI", () => {
  it("E03-T2/T7 requires an explicit clock and presents months-away return without pressure", async () => {
    const api = mockApi(false);
    await mount(api);
    const clock = document.querySelector<HTMLSelectElement>("#timeline-clock")!;
    expect([...clock.options].map((option) => option.value)).toEqual(["occurred", "observed", "reported", "recorded", "asserted"]);
    clock.value = "observed";
    await click(byText(t("explore.timeline")));
    expect(api.archiveTimeline).toHaveBeenCalledWith("observed");
    const copy = document.body.textContent!.toLowerCase();
    for (const forbidden of ["streak", "overdue", "you are behind", "completion percentage", "hurry", "reward"]) {
      expect(copy).not.toContain(forbidden);
    }
  });

  it("E03-T1/T6 exposes only fixed capture choices and focus-safe deletion confirmation", async () => {
    const api = mockApi(false);
    await mount(api);
    expect(document.querySelector("#quick-capture-text")).not.toBeNull();
    expect(document.querySelector('input[type="file"]')).toBeNull();
    await click(byText(t("archive.captureReport")));
    expect(api.archiveOperate).toHaveBeenCalledWith("CAPTURE_LAMP_REPORT", "occurred_summer_2042", "desktop_001");
    const confirm = byText(t("canonical.confirm"));
    expect(confirm.disabled).toBe(true);
    await click(byText(t("canonical.preview")));
    expect(confirm.disabled).toBe(false);
    expect(document.activeElement).toBe(confirm);
    await click(confirm);
    expect(api.archiveExecuteDeletion).toHaveBeenCalledWith("orchid-plan", "DELETE ORCHID LAMP SOURCE");
  });
});
