import { describe, expect, it, vi } from "vitest";
import { mountPersonal } from "../src/personal-main";
import type { PersonalApi, ReflectionSession } from "../src/personal-api";

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const click = async (text: string) => { const node = [...document.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === text); if (!node) throw new Error(`Missing ${text}`); node.click(); await tick(); };
const session = (id: string, state: "ACTIVE" | "CLOSED" = "ACTIVE", turns: ReflectionSession["turns"] = []): ReflectionSession => ({ session_id: id, title: "Synthetic reflection", state, turn_count: turns?.length ?? 0, created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z", turns });

describe("Personal daily-use renderer", () => {
  it("supports unlock, quick capture, history, search, and the bounded recovery journey", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    let locked = true; const item = session("r1"), question = { question_id: "q1", text: "What happened next?" };
    const exploration = () => ({ context: [{ context_item_id: "c1", kind: "UNKNOWN" as const, text: "What remains unclear?", state: "OPEN", source_turn_ids: ["t1"] }, { context_item_id: "c2", kind: "CONTRADICTION" as const, text: "Two accounts differ.", state: "UNRESOLVED", source_turn_ids: ["t1"] }], hypotheses: [{ hypothesis_id: "h1", proposal_text: "A tentative explanation", uncertainty_text: "Limited context", discriminator_text: "Observe another example" }], next_question: question, snapshots: [{}], formulations: [{ formulation_id: "f1", version: 1, parent_formulation_id: null, status: "CURRENT" as const, summary: "Current working picture", correction_text: null, supporting_turn_ids: ["t1"] }, { formulation_id: "f2", version: 2, parent_formulation_id: "f1", status: "PROPOSED" as const, origin: "AI" as const, summary: "AI proposal", correction_text: null, supporting_turn_ids: ["t1"], uncertainty_text: "Limited context", ai_provenance: { origin: "AI" as const, provider: "OpenAI", actual_model: "synthetic-model" } }, { formulation_id: "f3", version: 3, parent_formulation_id: "f1", status: "SUPERSEDED" as const, summary: "Older working picture", correction_text: "correction", supporting_turn_ids: ["t1"] }, { formulation_id: "f4", version: 4, parent_formulation_id: null, status: "REJECTED" as const, summary: "Rejected proposal", correction_text: null, supporting_turn_ids: ["t1"] }] });
    const api = {
      status: vi.fn(async () => ({ runtime_profile: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked, inbound_listener: "NONE" as const, outbound_provider: "NOT_CONFIGURED" as const, network: "OFFLINE_NO_LISTENER" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "NEVER_CLOUD" as const, telemetry: "OFF" as const } })),
      unlock: vi.fn(async () => { locked = false; return { session_token: "test" }; }), lock: vi.fn(async () => { locked = true; return {}; }),
      reflectionList: vi.fn(async () => ({ sessions: [item] })), reflectionCreate: vi.fn(async () => item), reflectionGet: vi.fn(async () => item),
      reflectionAddTurn: vi.fn(async (_id: string, content: string) => { item.turns = [...(item.turns ?? []), { turn_id: `t${item.turns!.length + 1}`, session_id: "r1", sequence: item.turns!.length + 1, actor: "USER", created_at: "2026-08-24T00:00:00Z", content }]; item.turn_count = item.turns.length; return item.turns.at(-1)!; }),
      reflectionClose: vi.fn(async () => { item.state = "CLOSED"; return {}; }), reflectionDelete: vi.fn(async () => ({})),
      reflectionSearch: vi.fn(async (query: string) => ({ query, state: "ALL" as const, total_matches: 1, returned_count: 1, offset: 0, limit: 20, truncated: false, has_more: false, results: [{ session_id: "r1", session_title: item.title, session_state: item.state, turn_id: "t1", turn_sequence: 1, excerpt: "unique marker" }] })),
      explorationStart: vi.fn(async () => exploration()), explorationGet: vi.fn(async () => exploration()), explorationAnswer: vi.fn(async () => exploration()), explorationSkip: vi.fn(async () => exploration()),
      formulationPropose: vi.fn(async () => ({})), formulationCorrect: vi.fn(async () => ({})), formulationAccept: vi.fn(async () => ({})), formulationReject: vi.fn(async () => ({})),
      personalRecoveryStatus: vi.fn(async () => ({ local_personal: "ADMITTED", rotation: "READY" })), personalBackup: vi.fn(async () => ({ backup_id: "backup-1" })), personalRestoreIsolated: vi.fn(async () => ({ candidate_id: "candidate-1" })), personalExportOwner: vi.fn(async () => ({ export_id: "export-1", audience: "OWNER_ONLY" }))
    } as unknown as PersonalApi;
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    expect(document.body.textContent).toContain("Ваше личное пространство защищено");
    document.querySelector<HTMLInputElement>("#unlock-secret")!.value = "fixture"; document.querySelector<HTMLFormElement>("#unlock-form")!.requestSubmit(); await tick();
    expect(document.body.textContent).toContain("БЫСТРАЯ ЗАПИСЬ");
    document.querySelector<HTMLInputElement>("#quick-capture-title")!.value = "A note"; document.querySelector<HTMLTextAreaElement>("#quick-capture-text")!.value = "unique marker"; document.querySelector<HTMLFormElement>("#quick-capture-form")!.requestSubmit(); await tick();
    expect(api.reflectionCreate).toHaveBeenCalledWith("A note"); expect(api.reflectionAddTurn).toHaveBeenCalledWith("r1", "unique marker"); expect(document.body.textContent).toContain("Запись сохранена в истории");
    expect(document.body.textContent).toContain("Ваши записи и выводы"); expect(document.body.textContent).toContain("неясного");
    expect(document.querySelector('[data-route="home"]')?.getAttribute("aria-current")).toBe("page");
    await click("Картина"); expect(document.body.textContent).toContain("Исходные записи"); expect(document.body.textContent).toContain("Что я сообщил"); expect(document.body.textContent).toContain("What remains unclear?"); expect(document.body.textContent).toContain("ВЫВОД ИЗ ЗАПИСЕЙ"); expect(document.body.textContent).toContain("ПРЕДЛОЖЕНО AI"); expect(document.body.textContent).toContain("Рабочая формулировка · Отклонена"); expect(document.body.textContent).toContain("Исправления и история"); expect(document.querySelector('[data-route="sensemaking"]')?.getAttribute("aria-current")).toBe("page");
    expect(document.body.textContent).toContain("unique marker"); expect(document.body.textContent).toContain("Показать источник");
    document.querySelector<HTMLButtonElement>("[data-open-source]")!.click(); await tick(); expect(document.querySelector(".is-source-highlight")?.textContent).toContain("unique marker");
    await click("Во времени"); expect(document.body.textContent).toContain("Хронология"); expect(document.body.textContent).toContain("Остаётся открытым"); expect(document.body.textContent).toContain("Обзор периода"); expect(document.querySelector('[data-route="longitudinal"]')?.getAttribute("aria-current")).toBe("page");
    const period = document.querySelector<HTMLSelectElement>("#longitudinal-period")!; period.value = "all"; period.dispatchEvent(new Event("change")); await tick(); expect(document.body.textContent).toContain("Показано: всё время"); expect(document.querySelectorAll(".longitudinal-event [data-open]").length).toBeGreaterThan(0);
    document.querySelector<HTMLButtonElement>('[data-open="r1"]')!.click(); await tick(); expect(document.body.textContent).toContain("Вы написали");
    await click("История"); expect(document.body.textContent).toContain("История"); await click("Продолжить"); expect(document.body.textContent).toContain("Вы написали");
    await click("Поиск"); document.querySelector<HTMLInputElement>("#search-query")!.value = "marker"; document.querySelector<HTMLFormElement>("#search-form")!.requestSubmit(); await tick(); expect(document.body.textContent).toContain("unique marker");
  });

  it("shows a compact Russian empty sensemaking state and human settings", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const api = {
      status: vi.fn(async () => ({ runtime_profile: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked: false, inbound_listener: "NONE" as const, outbound_provider: "NOT_CONFIGURED" as const, network: "OFFLINE_NO_LISTENER" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "NEVER_CLOUD" as const, telemetry: "OFF" as const } })),
      lock: vi.fn(async () => ({})), reflectionList: vi.fn(async () => ({ sessions: [] })), reflectionGet: vi.fn(), reflectionCreate: vi.fn(), reflectionAddTurn: vi.fn(), reflectionClose: vi.fn(), reflectionDelete: vi.fn(), reflectionSearch: vi.fn(), explorationGet: vi.fn(), explorationStart: vi.fn(), explorationAnswer: vi.fn(), explorationSkip: vi.fn(), formulationPropose: vi.fn(), formulationCorrect: vi.fn(), formulationAccept: vi.fn(), formulationReject: vi.fn(), personalRecoveryStatus: vi.fn(), personalBackup: vi.fn(), personalRestoreIsolated: vi.fn(), personalExportOwner: vi.fn()
    } as unknown as PersonalApi;
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Картина");
    expect(document.body.textContent).toContain("Картина появится постепенно");
    expect(document.querySelectorAll(".sense-section")).toHaveLength(0);
    await click("Настройки");
    expect(document.body.textContent).toContain("ПРИВАТНОСТЬ И ЛОКАЛЬНЫЙ РЕЖИМ");
    expect(document.body.textContent).toContain("Локально");
    expect(document.body.textContent).toContain("Технические сведения");
  });

  it("keeps CLOSED exploration readable without mutation controls", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const closed = session("closed", "CLOSED", [{ turn_id: "turn-closed", session_id: "closed", sequence: 1, actor: "USER", created_at: "2026-08-24T00:00:00Z", content: "Сохранённый текст пользователя" }]);
    const savedExploration = { context: [{ context_item_id: "context-closed", kind: "UNKNOWN" as const, text: "Сохранённый контекст", state: "OPEN", source_turn_ids: ["turn-closed"] }], hypotheses: [], next_question: { question_id: "question-closed", text: "Сохранённый вопрос" }, snapshots: [{}], formulations: [{ formulation_id: "formulation-closed", version: 1, parent_formulation_id: null, status: "PROPOSED" as const, summary: "Сохранённая формулировка", correction_text: null, supporting_turn_ids: ["turn-closed"] }] };
    const api = {
      status: vi.fn(async () => ({ runtime_profile: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked: false, inbound_listener: "NONE" as const, outbound_provider: "NOT_CONFIGURED" as const, network: "OFFLINE_NO_LISTENER" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "NEVER_CLOUD" as const, telemetry: "OFF" as const } })),
      lock: vi.fn(async () => ({})), reflectionList: vi.fn(async () => ({ sessions: [closed] })), reflectionGet: vi.fn(async () => closed), reflectionCreate: vi.fn(), reflectionAddTurn: vi.fn(), reflectionClose: vi.fn(), reflectionDelete: vi.fn(), reflectionSearch: vi.fn(), explorationGet: vi.fn(async () => savedExploration), explorationStart: vi.fn(), explorationAnswer: vi.fn(), explorationSkip: vi.fn(), formulationPropose: vi.fn(), formulationCorrect: vi.fn(), formulationAccept: vi.fn(), formulationReject: vi.fn(), personalRecoveryStatus: vi.fn(), personalBackup: vi.fn(), personalRestoreIsolated: vi.fn(), personalExportOwner: vi.fn()
    } as unknown as PersonalApi;
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Открыть");
    expect(document.body.textContent).toContain("Размышление завершено. Исследование доступно только для чтения.");
    for (const text of ["Сохранённый текст пользователя", "Сохранённый контекст", "Сохранённый вопрос", "Сохранённая формулировка"]) expect(document.body.textContent).toContain(text);
    for (const selector of ["#start-exploration", "#propose-formulation", "#answer-question", "#skip-question", "[data-correct]", "[data-accept]", "[data-reject]"]) expect(document.querySelector(selector)).toBeNull();
    expect(document.querySelector("#delete-reflection")).not.toBeNull();
  });

  it("keeps ACTIVE exploration controls and hides raw SESSION_CLOSED errors", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const active = session("active");
    const api = {
      status: vi.fn(async () => ({ runtime_profile: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked: false, inbound_listener: "NONE" as const, outbound_provider: "NOT_CONFIGURED" as const, network: "OFFLINE_NO_LISTENER" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "NEVER_CLOUD" as const, telemetry: "OFF" as const } })),
      lock: vi.fn(async () => ({})), reflectionList: vi.fn(async () => ({ sessions: [active] })), reflectionGet: vi.fn(async () => active), reflectionCreate: vi.fn(), reflectionAddTurn: vi.fn(), reflectionClose: vi.fn(), reflectionDelete: vi.fn(), reflectionSearch: vi.fn(), explorationGet: vi.fn(async () => ({ context: [], hypotheses: [], next_question: { question_id: "question-active", text: "Активный вопрос" }, snapshots: [{}], formulations: [{ formulation_id: "formulation-active", version: 1, parent_formulation_id: null, status: "PROPOSED" as const, summary: "Активная формулировка", correction_text: null, supporting_turn_ids: [] }] })), explorationStart: vi.fn(async () => { throw new Error("SESSION_CLOSED"); }), explorationAnswer: vi.fn(), explorationSkip: vi.fn(), formulationPropose: vi.fn(), formulationCorrect: vi.fn(), formulationAccept: vi.fn(), formulationReject: vi.fn(), personalRecoveryStatus: vi.fn(), personalBackup: vi.fn(), personalRestoreIsolated: vi.fn(), personalExportOwner: vi.fn()
    } as unknown as PersonalApi;
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Продолжить");
    for (const selector of ["#start-exploration", "#propose-formulation", "#answer-question", "#skip-question", "[data-correct]", "[data-accept]", "[data-reject]"]) expect(document.querySelector(selector)).not.toBeNull();
    await click("Обновить исследование");
    expect(document.body.textContent).toContain("Размышление завершено. Изменения недоступны.");
    expect(document.body.textContent).not.toContain("SESSION_CLOSED");
  });

  it("applies whole-reflection source policy in bounded batches of at most 12 exact turn ids", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const turnCount = 29;
    const bigTurns = Array.from({ length: turnCount }, (_, index) => ({
      turn_id: `turn-${index + 1}`,
      session_id: "big",
      sequence: index + 1,
      actor: "USER" as const,
      created_at: "2026-08-24T00:00:00Z",
      content: `Синтетическая запись ${index + 1}`,
    }));
    const big = session("big", "ACTIVE", bigTurns);
    const policyCalls: { turnIds: string[]; enabled: boolean }[] = [];
    const api = {
      status: vi.fn(async () => ({ runtime_profile: "LOCAL_PERSONAL_AI_INTERVIEW_OPENAI" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked: false, inbound_listener: "NONE" as const, outbound_provider: "OPENAI_EXPLICIT_OPT_IN" as const, network: "OPENAI_FOREGROUND_BOUNDED" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "EXPLICIT_SESSION_CONSENT_OPENAI_ONLY" as const, telemetry: "OFF" as const } })),
      lock: vi.fn(async () => ({})),
      reflectionList: vi.fn(async () => ({ sessions: [big] })),
      reflectionGet: vi.fn(async () => big),
      reflectionCreate: vi.fn(), reflectionAddTurn: vi.fn(), reflectionClose: vi.fn(), reflectionDelete: vi.fn(), reflectionSearch: vi.fn(),
      explorationGet: vi.fn(async () => ({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] })),
      explorationStart: vi.fn(), explorationAnswer: vi.fn(), explorationSkip: vi.fn(),
      formulationPropose: vi.fn(), formulationCorrect: vi.fn(), formulationAccept: vi.fn(), formulationReject: vi.fn(),
      personalRecoveryStatus: vi.fn(), personalBackup: vi.fn(), personalRestoreIsolated: vi.fn(), personalExportOwner: vi.fn(),
      aiInterviewStatus: vi.fn(async () => ({ configured: true, policy_enabled: true, profile_id: "synthetic", eligible_source_count: turnCount })),
      aiInterviewList: vi.fn(async () => ({ sessions: [] })),
      aiInterviewGet: vi.fn(async () => { throw new Error("INTERVIEW_NOT_FOUND"); }),
      aiInterviewSourcePolicy: vi.fn(async (turnIds: string[], enabled: boolean) => {
        policyCalls.push({ turnIds, enabled });
        return {};
      }),
    } as unknown as PersonalApi;
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Продолжить");
    expect(document.querySelector("#interview-source-allow-all")).not.toBeNull();

    await click("Разрешить всё размышление для AI");
    expect(policyCalls.length).toBe(Math.ceil(turnCount / 12));
    for (const call of policyCalls) expect(call.turnIds.length).toBeLessThanOrEqual(12);
    expect(policyCalls.every((call) => call.enabled)).toBe(true);
    expect(policyCalls.flatMap((call) => call.turnIds).sort()).toEqual(bigTurns.map((turn) => turn.turn_id).sort());
    expect(document.body.textContent).toContain("Все записи этого размышления разрешены");
    expect(api.aiInterviewStatus).toHaveBeenCalled();

    policyCalls.length = 0;
    await click("Отозвать разрешение со всего размышления");
    expect(policyCalls.length).toBe(Math.ceil(turnCount / 12));
    for (const call of policyCalls) expect(call.turnIds.length).toBeLessThanOrEqual(12);
    expect(policyCalls.every((call) => !call.enabled)).toBe(true);
    expect(policyCalls.flatMap((call) => call.turnIds).sort()).toEqual(bigTurns.map((turn) => turn.turn_id).sort());
    expect(document.body.textContent).toContain("Разрешение на передачу всех записей этого размышления отозвано");
  });
});
