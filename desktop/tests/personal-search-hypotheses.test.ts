import { describe, expect, it, vi } from "vitest";
import { mountPersonal } from "../src/personal-main";
import type { PersonalApi, ReflectionSession, SearchView, SearchResult } from "../src/personal-api";

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const click = async (text: string) => { const node = [...document.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === text); if (!node) throw new Error(`Missing button ${text}`); node.click(); await tick(); };
const status = () => ({ runtime_profile: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked: false, inbound_listener: "NONE" as const, outbound_provider: "NOT_CONFIGURED" as const, network: "OFFLINE_NO_LISTENER" as const, privacy: { core_processing_location: "LOCAL" as const, cloud_storage: "DISABLED" as const, cloud_disclosure: "NEVER_CLOUD" as const, telemetry: "OFF" as const } });
const session = (id: string, turns: ReflectionSession["turns"] = []): ReflectionSession => ({ session_id: id, title: "Synthetic reflection", state: "ACTIVE", turn_count: turns?.length ?? 0, created_at: "2026-08-24T00:00:00Z", updated_at: "2026-08-24T00:00:00Z", turns });

const result = (index: number): SearchResult => ({ result_id: `result-${index}`, result_type: "USER_SOURCE", session_id: "r1", session_title: "Synthetic reflection", session_state: "ACTIVE", at: "2026-08-24T00:00:00Z", text: `Synthetic result ${index}`, excerpt: `Synthetic result ${index}`, turn_id: `t${index}`, turn_sequence: index, status: null, source_turns: [], why_here: "Synthetic.", parent_result_id: null, ai_provenance: null, correction_text: null, related_context: [] });

const page = (results: SearchResult[], offset: number, total: number): SearchView => ({ query: "marker", state: "ALL", content: "ALL", period: "ALL", formulation_status: "ALL", total_matches: total, returned_count: results.length, offset, limit: 20, truncated: offset + results.length < total, has_more: offset + results.length < total, results });

const paginatedApi = (total: number, failSecondPage = false) => {
  const item = session("r1");
  return {
    item,
    api: {
      status: vi.fn(async () => status()), lock: vi.fn(async () => ({})),
      reflectionList: vi.fn(async () => ({ sessions: [item] })), reflectionGet: vi.fn(async () => item),
      reflectionSearch: vi.fn(async (query: string, _filters: unknown, limit = 20, offset = 0) => {
        if (offset > 0 && failSecondPage) throw new Error("STORAGE_UNAVAILABLE");
        return page(Array.from({ length: Math.min(limit, total - offset) }, (_, index) => result(offset + index + 1)), offset, total);
      }),
      explorationGet: vi.fn(async () => ({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] })),
      explorationStart: vi.fn(), explorationAnswer: vi.fn(), explorationSkip: vi.fn(),
      reflectionCreate: vi.fn(), reflectionAddTurn: vi.fn(), reflectionClose: vi.fn(), reflectionDelete: vi.fn(),
      formulationPropose: vi.fn(), formulationCorrect: vi.fn(), formulationAccept: vi.fn(), formulationReject: vi.fn(),
      personalRecoveryStatus: vi.fn(), personalBackup: vi.fn(), personalRestoreIsolated: vi.fn(), personalExportOwner: vi.fn()
    } as unknown as PersonalApi
  };
};

const runSearch = async (query = "marker") => { document.querySelector<HTMLInputElement>("#search-query")!.value = query; document.querySelector<HTMLFormElement>("#search-form")!.requestSubmit(); await tick(); };

describe("Personal search pagination", () => {
  it("requests the first page with limit 20 / offset 0 and shows loaded-vs-total summary", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = paginatedApi(45);
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Поиск");
    await runSearch();
    expect(api.reflectionSearch).toHaveBeenLastCalledWith("marker", expect.anything(), 20, 0);
    expect(document.body.textContent).toContain("Показано 20 из 45");
    expect(document.body.textContent).toContain("Показать ещё");
    expect(document.querySelectorAll(".search-result")).toHaveLength(20);
  });

  it("appends the next page with the correct offset, deduplicates repeated ids, and hides the button at the end", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = paginatedApi(25);
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Поиск");
    await runSearch();
    expect(document.querySelectorAll(".search-result")).toHaveLength(20);
    await click("Показать ещё");
    expect(api.reflectionSearch).toHaveBeenLastCalledWith("marker", expect.anything(), 20, 20);
    expect(document.querySelectorAll(".search-result")).toHaveLength(25);
    expect(document.body.textContent).toContain("Показано 25 из 25");
    expect(document.querySelector("#load-more-search")).toBeNull();
  });

  it("does not render a duplicated result_id twice when the service repeats a row", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = paginatedApi(25);
    (api.reflectionSearch as ReturnType<typeof vi.fn>).mockImplementation(async (query: string, _filters: unknown, limit = 20, offset = 0) => {
      const rows = Array.from({ length: Math.min(limit, 25 - offset) }, (_, index) => result(offset + index + 1));
      if (offset > 0) rows[0] = result(1);
      return page(rows, offset, 25);
    });
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Поиск");
    await runSearch();
    await click("Показать ещё");
    expect(document.querySelectorAll(".search-result")).toHaveLength(24);
    expect(document.querySelectorAll("[data-context-select='result-1']")).toHaveLength(1);
    expect(document.body.textContent).toContain("Показано 24 из 25");
  });

  it("keeps Context Pack selection across load-more and accepts selections from both pages", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = paginatedApi(25);
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Поиск");
    await runSearch();
    const firstBox = document.querySelector<HTMLInputElement>("[data-context-select='result-1']")!;
    firstBox.checked = true; firstBox.dispatchEvent(new Event("change")); await tick();
    await click("Показать ещё");
    expect(document.querySelector<HTMLInputElement>("[data-context-select='result-1']")!.checked).toBe(true);
    const secondBox = document.querySelector<HTMLInputElement>("[data-context-select='result-21']")!;
    expect(secondBox).not.toBeNull();
    secondBox.checked = true; secondBox.dispatchEvent(new Event("change")); await tick();
    expect(document.body.textContent).toContain("Собрать контекст (2/20)");
  });

  it("resets pagination and selection on a new search", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = paginatedApi(25);
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Поиск");
    await runSearch();
    const box = document.querySelector<HTMLInputElement>("[data-context-select='result-1']")!;
    box.checked = true; box.dispatchEvent(new Event("change")); await tick();
    await click("Показать ещё");
    await runSearch("other");
    expect(api.reflectionSearch).toHaveBeenLastCalledWith("other", expect.anything(), 20, 0);
    expect(document.querySelectorAll(".search-result")).toHaveLength(20);
    expect(document.querySelector<HTMLInputElement>("[data-context-select='result-1']")?.checked).toBeFalsy();
    expect(document.body.textContent).toContain("Показано 20 из 25");
  });

  it("preserves first-page results and allows retry when a later page fails", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = paginatedApi(25, true);
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Поиск");
    await runSearch();
    await click("Показать ещё");
    expect(document.querySelectorAll(".search-result")).toHaveLength(20);
    expect(document.body.textContent).toContain("Не удалось выполнить действие");
    expect(document.querySelector("#load-more-search")).not.toBeNull();
    (api.reflectionSearch as ReturnType<typeof vi.fn>).mockImplementation(async (query: string, _filters: unknown, limit = 20, offset = 0) => page(Array.from({ length: Math.min(limit, 25 - offset) }, (_, index) => result(offset + index + 1)), offset, 25));
    await click("Показать ещё");
    expect(document.querySelectorAll(".search-result")).toHaveLength(25);
  });
});

describe("Personal working assumptions", () => {
  const exploration = () => ({
    context: [{ context_item_id: "ctx-1", kind: "UNKNOWN" as const, text: "Что остаётся неясным?", state: "OPEN", source_turn_ids: ["t1"] }],
    hypotheses: [
      { hypothesis_id: "hyp-1", proposal_text: "Рабочее предположение с источником", uncertainty_text: "Пока мало данных", discriminator_text: "Понаблюдать ещё один случай", context_refs: [{ context_item_id: "ctx-1", relation: "RELATES_TO", source_turn_ids: ["t1"] }], created_at: "2026-08-24T00:00:00Z" },
      { hypothesis_id: "hyp-2", proposal_text: "Рабочее предположение без источника", uncertainty_text: "Неизвестно", discriminator_text: "Проверить позже", context_refs: [{ context_item_id: "ctx-2", relation: "RELATES_TO", source_turn_ids: [] }] }
    ],
    next_question: null, snapshots: [{}], formulations: []
  });
  const hypothesisApi = (state: "ACTIVE" | "CLOSED" = "ACTIVE") => {
    const item = session("r1", [{ turn_id: "t1", session_id: "r1", sequence: 1, actor: "USER", created_at: "2026-08-24T00:00:00Z", content: "Исходная запись пользователя" }]);
    item.state = state;
    return {
      api: {
        status: vi.fn(async () => status()), lock: vi.fn(async () => ({})),
        reflectionList: vi.fn(async () => ({ sessions: [item] })), reflectionGet: vi.fn(async () => item),
        reflectionSearch: vi.fn(), explorationGet: vi.fn(async () => exploration()), explorationStart: vi.fn(), explorationAnswer: vi.fn(), explorationSkip: vi.fn(),
        reflectionCreate: vi.fn(), reflectionAddTurn: vi.fn(), reflectionClose: vi.fn(), reflectionDelete: vi.fn(),
        formulationPropose: vi.fn(), formulationCorrect: vi.fn(), formulationAccept: vi.fn(), formulationReject: vi.fn(),
        personalRecoveryStatus: vi.fn(), personalBackup: vi.fn(), personalRestoreIsolated: vi.fn(), personalExportOwner: vi.fn()
      } as unknown as PersonalApi, item
    };
  };

  it("renders working assumptions in reflection detail with explicit not-fact semantics and truthful provenance", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = hypothesisApi();
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Продолжить");
    const text = document.body.textContent ?? "";
    expect(text).toContain("Рабочие предположения");
    expect(text).toContain("РАБОЧЕЕ ПРЕДПОЛОЖЕНИЕ · НЕ ФАКТ");
    expect(text).toContain("Рабочее предположение с источником");
    expect(text).toContain("Что пока неизвестно");
    expect(text).toContain("Пока мало данных");
    expect(text).toContain("Что поможет проверить");
    expect(text).toContain("Понаблюдать ещё один случай");
    expect(text).toContain("Показать источник");
    expect(text).toContain("Связано с открытыми вопросами исследования; конкретная исходная запись не указана.");
    expect(text).not.toContain("hyp-1");
    expect(text).not.toContain("hyp-2");
    expect(text).not.toContain("ctx-1");
    expect(text).not.toContain("RELATES_TO");
    const card = document.querySelector(".hypothesis-card")!;
    expect(card.textContent).not.toContain("ПРЕДЛОЖЕНО AI");
    expect(card.textContent).not.toContain("ВЫВОД ИЗ ЗАПИСЕЙ");
    expect(card.querySelector("[data-search-context]")).toBeNull();
  });

  it("shows working assumptions in Картина between contradictions and formulations", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = hypothesisApi();
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Картина");
    const sections = [...document.querySelectorAll<HTMLElement>(".sense-section h2")].map((node) => node.textContent);
    expect(sections.indexOf("Рабочие предположения")).toBeGreaterThan(sections.indexOf("Противоречия"));
    expect(sections.indexOf("Рабочие предположения")).toBeLessThan(sections.indexOf("Рабочие формулировки"));
    expect(document.body.textContent).toContain("Рабочее предположение с источником");
  });

  it("keeps CLOSED reflections read-only while assumptions stay readable", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = hypothesisApi("CLOSED");
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Открыть");
    expect(document.body.textContent).toContain("РАБОЧЕЕ ПРЕДПОЛОЖЕНИЕ · НЕ ФАКТ");
    for (const selector of ["#start-exploration", "#propose-formulation", "#answer-question", "#skip-question", "[data-correct]", "[data-accept]", "[data-reject]"]) expect(document.querySelector(selector)).toBeNull();
  });

  it("stays calm when there are no hypotheses", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    const { api } = hypothesisApi();
    (api.explorationGet as ReturnType<typeof vi.fn>).mockResolvedValue({ context: [], hypotheses: [], next_question: null, snapshots: [], formulations: [] });
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    await click("Продолжить");
    expect(document.querySelector(".hypotheses-section")).toBeNull();
    await click("Картина");
    expect(document.body.textContent).toContain("Рабочих предположений пока нет");
  });
});
