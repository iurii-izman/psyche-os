import { describe, expect, it, vi } from "vitest";
import { mountPersonal } from "../src/personal-main";
import type { PersonalApi, ReflectionSession } from "../src/personal-api";

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));
const click = async (text: string) => { const node = [...document.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === text); if (!node) throw new Error(`Missing ${text}`); node.click(); await tick(); };
const session = (id: string, state: "ACTIVE" | "CLOSED" = "ACTIVE", turns: ReflectionSession["turns"] = []): ReflectionSession => ({ session_id: id, title: "Synthetic reflection", state, turn_count: turns?.length ?? 0, turns });

describe("Personal Reflection Workspace renderer", () => {
  it("renders vault states and completes the reflection/search/exploration vertical", async () => {
    document.body.innerHTML = '<div id="app"></div>';
    let locked = true, item = session("r1"), question = { question_id: "q1", text: "What happened next?" }, formulationStatus: "PROPOSED" | "CURRENT" | "REJECTED" = "PROPOSED";
    const exploration = () => ({ context: [{ context_item_id: "c1", kind: "UNKNOWN" as const, text: "Missing context", state: "OPEN" }], hypotheses: [], next_question: question, snapshots: [{}], formulations: [{ formulation_id: "f1", version: 1, status: formulationStatus, summary: "A derived working formulation", correction_text: formulationStatus === "CURRENT" ? "Clarified" : null }] });
    const api = {
      status: vi.fn(async () => ({ data_mode: "LOCAL_PERSONAL" as const, real_data_gate: "CLOSED" as const, local_personal: "ADMITTED" as const, locked })),
      unlock: vi.fn(async () => { locked = false; return { session_token: "test" }; }), lock: vi.fn(async () => { locked = true; return {}; }),
      reflectionList: vi.fn(async () => ({ sessions: item ? [item] : [] })), reflectionCreate: vi.fn(async () => item), reflectionGet: vi.fn(async () => item),
      reflectionAddTurn: vi.fn(async (_id: string, content: string) => { item.turns = [...(item.turns ?? []), { turn_id: `t${item.turns!.length + 1}`, session_id: "r1", sequence: item.turns!.length + 1, actor: "USER", created_at: "2026-08-24T00:00:00Z", content }]; item.turn_count = item.turns.length; return item.turns.at(-1)!; }),
      reflectionClose: vi.fn(async () => { item.state = "CLOSED"; return {}; }), reflectionDelete: vi.fn(async () => { item = null as unknown as ReflectionSession; return {}; }),
      reflectionSearch: vi.fn(async () => ({ query: "marker", state: "ALL" as const, total_matches: 1, returned_count: 1, offset: 0, limit: 20, truncated: true, has_more: false, results: [{ session_id: "r1", session_title: item.title, session_state: item.state, turn_id: "t1", turn_sequence: 1, excerpt: "unique marker" }] })),
      explorationStart: vi.fn(async () => exploration()), explorationGet: vi.fn(async () => exploration()), explorationAnswer: vi.fn(async () => { question = null as unknown as typeof question; return exploration(); }), explorationSkip: vi.fn(async () => exploration()),
      formulationPropose: vi.fn(async () => ({})), formulationCorrect: vi.fn(async () => ({})), formulationAccept: vi.fn(async () => { formulationStatus = "CURRENT"; return {}; }), formulationReject: vi.fn(async () => { formulationStatus = "REJECTED"; return {}; })
    } as unknown as PersonalApi;
    await mountPersonal(api, document.querySelector<HTMLDivElement>("#app")!);
    expect(document.body.textContent).toContain("Vault is locked");
    document.querySelector<HTMLInputElement>("#unlock-secret")!.value = "fixture"; document.querySelector<HTMLFormElement>("#unlock-form")!.requestSubmit(); await tick();
    await click("New reflection"); document.querySelector<HTMLInputElement>("#reflection-title")!.value = "Synthetic reflection"; document.querySelector<HTMLTextAreaElement>("#quick-capture")!.value = "unique marker"; document.querySelector<HTMLFormElement>("#create-reflection")!.requestSubmit(); await tick(); await tick();
    expect(document.body.textContent).toContain("Your text"); expect(document.body.textContent).toContain("unique marker");
    document.querySelector<HTMLTextAreaElement>("#reflection-turn")!.value = "second entry"; document.querySelector<HTMLFormElement>("#add-turn")!.requestSubmit(); await tick(); await tick();
    await click("All reflections"); await click("Search"); document.querySelector<HTMLInputElement>("#search-query")!.value = "marker"; document.querySelector<HTMLFormElement>("#search-form")!.requestSubmit(); await tick(); expect(document.body.textContent).toContain("Results are bounded"); await click("Open reflection");
    await click("Refresh exploration"); expect(document.body.textContent).toContain("Current question"); await click("Skip"); document.querySelector<HTMLTextAreaElement>("#question-answer")!.value = "answer"; document.querySelector<HTMLFormElement>("#answer-question")!.requestSubmit(); await tick(); await click("Propose working formulation"); await tick(); const correction = document.querySelector<HTMLFormElement>("[data-correct]")!; correction.querySelector<HTMLTextAreaElement>("textarea")!.value = "Clarified"; correction.requestSubmit(); await tick(); await click("Accept formulation"); await tick();
    expect(document.body.textContent).toContain("Working formulation · CURRENT"); expect(api.explorationSkip).toHaveBeenCalled(); expect(api.formulationCorrect).toHaveBeenCalledWith("f1", "Clarified");
    await click("Close reflection"); await tick(); expect(document.body.textContent).toContain("read only"); vi.spyOn(window, "confirm").mockReturnValue(true); await click("Delete reflection"); expect(api.reflectionDelete).toHaveBeenCalledWith("r1");
  });
});
