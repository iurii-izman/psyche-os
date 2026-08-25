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
    const exploration = () => ({ context: [{ context_item_id: "c1", kind: "UNKNOWN" as const, text: "What remains unclear?", state: "OPEN", source_turn_ids: ["t1"] }, { context_item_id: "c2", kind: "CONTRADICTION" as const, text: "Two accounts differ.", state: "OPEN", source_turn_ids: ["t1"] }], hypotheses: [{ hypothesis_id: "h1", proposal_text: "A tentative explanation", uncertainty_text: "Limited context", discriminator_text: "Observe another example" }], next_question: question, snapshots: [{}], formulations: [{ formulation_id: "f1", version: 1, status: "CURRENT" as const, summary: "Current working picture", correction_text: null }] });
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
    expect(document.body.textContent).toContain("Vault locked");
    document.querySelector<HTMLInputElement>("#unlock-secret")!.value = "fixture"; document.querySelector<HTMLFormElement>("#unlock-form")!.requestSubmit(); await tick();
    expect(document.body.textContent).toContain("QUICK CAPTURE");
    document.querySelector<HTMLInputElement>("#quick-capture-title")!.value = "A note"; document.querySelector<HTMLTextAreaElement>("#quick-capture-text")!.value = "unique marker"; document.querySelector<HTMLFormElement>("#quick-capture-form")!.requestSubmit(); await tick();
    expect(api.reflectionCreate).toHaveBeenCalledWith("A note"); expect(api.reflectionAddTurn).toHaveBeenCalledWith("r1", "unique marker"); expect(document.body.textContent).toContain("Capture saved to your history");
    expect(document.body.textContent).toContain("DAILY REVIEW"); expect(document.body.textContent).toContain("unresolved unknowns");
    await click("Understand"); expect(document.body.textContent).toContain("Current picture"); expect(document.body.textContent).toContain("What remains unclear?"); expect(document.body.textContent).toContain("Derived from reflection"); await click("Open source reflection"); expect(document.body.textContent).toContain("USER · entry 1");
    await click("Privacy & local status"); expect(document.body.textContent).toContain("OFFLINE_NO_LISTENER"); expect(document.body.textContent).toContain("NEVER_CLOUD");
    await click("History"); expect(document.body.textContent).toContain("Your saved reflections"); await click("Resume"); expect(document.body.textContent).toContain("USER · entry 1");
    await click("Search"); document.querySelector<HTMLInputElement>("#search-query")!.value = "marker"; document.querySelector<HTMLFormElement>("#search-form")!.requestSubmit(); await tick(); expect(document.body.textContent).toContain("unique marker");
    await click("Backup & recovery"); await click("Refresh status"); expect(document.body.textContent).toContain("Rotation: READY");
    vi.spyOn(window, "confirm").mockReturnValue(true); document.querySelector<HTMLInputElement>("#backup-secret")!.value = "fixture"; document.querySelector<HTMLFormElement>("#backup-form")!.requestSubmit(); await tick(); expect(document.body.textContent).toContain("Backup identifier: backup-1");
    document.querySelector<HTMLInputElement>("#restore-backup-id")!.value = "backup-1"; document.querySelector<HTMLInputElement>("#restore-secret")!.value = "fixture"; document.querySelector<HTMLFormElement>("#restore-form")!.requestSubmit(); await tick(); expect(api.personalRestoreIsolated).toHaveBeenCalledWith("backup-1", "fixture"); expect(document.body.textContent).toContain("Isolated restore candidate created");
  });
});
