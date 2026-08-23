import axe from "axe-core";
import { readFileSync } from "node:fs";
import { describe, expect, it, vi } from "vitest";

import type { DesktopApi, StatusView } from "../src/api";
import { mount } from "../src/main";
import { t } from "../src/i18n";

function syntheticStatus(locked = false): StatusView {
  return {
    locked,
    data_mode: "SYNTHETIC_ONLY",
    real_data_gate: "CLOSED",
    network: "OFFLINE_NO_LISTENER",
    privacy: { processing_location: "LOCAL_ONLY", cloud: "DISABLED", telemetry: "OFF" }
  };
}

function mockApi(locked = false): DesktopApi {
  let stateLocked = locked;
  return {
    status: vi.fn(async () => syntheticStatus(stateLocked)),
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

describe("E02 bounded desktop UI", () => {
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
    const title = document.querySelector<HTMLInputElement>("#reflection-title")!;
    title.value = "Тест";
    title.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const analytics = document.querySelector<HTMLElement>(".analytical-workspace")!;
    expect(analytics.textContent).toContain("АНАЛИТИКА СЕССИИ");
    for (const required of ["Текущая рабочая формулировка", "Как менялась формулировка", "Матрица контекста", "Поддерживает", "Противоречит / контрпример", "Остаётся неизвестным", "Пропущено / «не знаю»", "Противоречия / разные ответы", "Хронология сессии", "ваш ответ №1"]) expect(analytics.textContent).toContain(required);
    expect(analytics.querySelector("button, input, textarea, select")).toBeNull();
    expect(document.querySelector<HTMLTextAreaElement>("#reflection-turn")!.disabled).toBe(true);
  });

  it("presents the Russian local reflection-session entry point", async () => {
    const api = mockApi(false);
    await mount(api);
    expect(document.body.textContent).toContain("МОИ СЕССИИ");
    expect(byText("Новая сессия")).toBeTruthy();
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

  it("keeps a newer session view when the initial asynchronous list resolves late", async () => {
    const api = mockApi(false);
    let resolveList!: (result: { sessions: [] }) => void;
    vi.mocked(api.reflectionList).mockImplementationOnce(() => new Promise((resolve) => { resolveList = resolve; }));
    await mount(api);
    const title = document.querySelector<HTMLInputElement>("#reflection-title")!;
    title.value = "Синтетическая сессия";
    title.form!.requestSubmit();
    await new Promise((resolve) => setTimeout(resolve, 0));
    resolveList({ sessions: [] });
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(byText("Добавить в сессию")).toBeTruthy();
  });

  it("V3-D opens a neutral empty Return workspace and preserves newer navigation", async () => {
    const api = mockApi(false);
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [] });
    await mount(api);
    await click(byText("К ЧЕМУ ВЕРНУТЬСЯ"));
    const workspace = document.querySelector<HTMLElement>(".return-workspace")!;
    expect(workspace.textContent).toContain("К ЧЕМУ ВЕРНУТЬСЯ");
    expect(workspace.textContent).toContain("Таких сохранённых записей пока нет.");
    expect(workspace.textContent).toContain("не означают срочность");
    expect(workspace.textContent).toContain("не означает разрешение");
    expect(workspace.textContent).toContain("не означает эффективность");
  });

  it("V3-D displays provenance and opens only the chosen source session", async () => {
    const api = mockApi(false);
    const session = { session_id: "return-a", title: "Исходная сессия", state: "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: "2026-01-01T00:00:00Z", turn_count: 1, turns: [{ turn_id: "turn-return-a", session_id: "return-a", sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "Синтетический исходный текст" }] };
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions: [session] });
    vi.mocked(api.reflectionGet).mockResolvedValue(session);
    vi.mocked(api.explorationGet).mockResolvedValue({ context: [{ context_item_id: "unknown-return", dimension: "context", kind: "UNKNOWN", text: "Сохранённый вопрос", state: "OPEN", source_turn_ids: ["turn-return-a"], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [], next_question: null, snapshots: [], formulations: [] });
    vi.mocked(api.actionList).mockResolvedValue({ session_id: "return-a", plans: [] });
    await mount(api); await click(byText("К ЧЕМУ ВЕРНУТЬСЯ"));
    const workspace = document.querySelector<HTMLElement>(".return-workspace")!;
    expect(workspace.textContent).toContain("Записано ранее");
    expect(workspace.textContent).toContain("Источник: ваш ответ №1");
    await click(byText("Вернуться к этой записи"));
    expect(api.reflectionGet).toHaveBeenLastCalledWith("return-a");
    expect(document.body.textContent).toContain("Сессия завершена. История доступна только для чтения.");
    expect(document.body.textContent).toContain("Ваш текст");
    expect(document.body.textContent).not.toContain("Ваш новый текст");
  });

  it("V3-B/C opens the global read-only longitudinal workspace for two synthetic sessions", async () => {
    const api = mockApi(false);
    const sessions = ["a", "b"].map((id, index) => ({ session_id: id, title: `Сессия ${id}`, state: index ? "ACTIVE" as const : "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: `2026-01-0${index + 1}T00:00:00Z`, updated_at: `2026-01-0${index + 1}T00:00:00Z`, closed_at: index ? null : "2026-01-01T00:00:00Z", turn_count: 1, turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER" as const, created_at: `2026-01-0${index + 1}T00:00:00Z`, content: "синтетический" }] }));
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions }); vi.mocked(api.reflectionGet).mockImplementation(async (id) => sessions.find((item) => item.session_id === id)!);
    vi.mocked(api.explorationGet).mockImplementation(async (id) => ({ context: [{ context_item_id: `known-${id}`, dimension: "context", kind: "KNOWN", text: "Точная запись", state: "RECORDED", source_turn_ids: [`turn-${id}`], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: `unknown-${id}`, dimension: "context", kind: "UNKNOWN", text: "Открытый вопрос", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: `contradiction-${id}`, dimension: "context", kind: "CONTRADICTION", text: "Разные ответы", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [{ hypothesis_id: `h-${id}`, template_id: "contextual", proposal_text: "Вариант", uncertainty_text: "Неизвестно", discriminator_text: "Уточнить", context_refs: [] }], next_question: null, snapshots: [], formulations: [{ formulation_id: `f-${id}`, version: 1, status: "CURRENT", summary: `Формулировка ${id}`, correction_text: null, created_at: "2026-01-01T00:00:00Z" }] }));
    vi.mocked(api.actionList).mockResolvedValue({ session_id: "a", plans: [] }); await mount(api); await click(byText("ДИНАМИКА ПО СЕССИЯМ"));
    const workspace = document.querySelector<HTMLElement>(".longitudinal-workspace")!; for (const text of ["Обзор записей", "История рабочих формулировок", "Что повторялось в записях", "Рабочие альтернативы", "Неизвестное и противоречия", "Мои следующие шаги и отметки", "Сравнить две сессии", "Хронология записанных событий продукта", "Точная запись"]) expect(workspace.textContent).toContain(text);
    expect(workspace.querySelector("button, textarea")).toBeNull(); expect(workspace.querySelectorAll("select")).toHaveLength(2);
  });

  it("V3-B/C presents truthful guided coverage and complete singleton/session comparison detail", async () => {
    const api = mockApi(false); const sessions = ["a", "b"].map((id, index) => ({ session_id: id, title: `Сессия ${id}`, state: index ? "ACTIVE" as const : "CLOSED" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: `2026-01-0${index + 1}T00:00:00Z`, updated_at: `2026-01-0${index + 1}T00:00:00Z`, closed_at: index ? null : "2026-01-01T00:00:00Z", turn_count: 1, turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER" as const, created_at: "2026-01-01T00:00:00Z", content: "синтетический" }] }));
    vi.mocked(api.reflectionList).mockResolvedValue({ sessions }); vi.mocked(api.reflectionGet).mockImplementation(async (id) => sessions.find((item) => item.session_id === id)!);
    vi.mocked(api.explorationGet).mockImplementation(async (id) => id === "b" ? ({ context: [], hypotheses: [], snapshots: [], formulations: [], next_question: null }) : ({ context: [{ context_item_id: "known-a", dimension: "context", kind: "KNOWN", text: "Точная связь", state: "RECORDED", source_turn_ids: ["turn-a"], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: "unknown-a", dimension: "context", kind: "UNKNOWN", text: "Открытый вопрос", state: "OPEN", source_turn_ids: ["turn-a"], created_at: "2026-01-01T00:00:00Z" }, { context_item_id: "contradiction-a", dimension: "context", kind: "CONTRADICTION", text: "Разные ответы", state: "OPEN", source_turn_ids: ["turn-a"], created_at: "2026-01-01T00:00:00Z" }], hypotheses: [{ hypothesis_id: "h-a", template_id: "contextual", proposal_text: "Рабочая альтернатива", uncertainty_text: "Неопределённость", discriminator_text: "Уточнить", context_refs: [{ context_item_id: "known-a", relation: "SUPPORT", source_turn_ids: ["turn-a"] }] }], next_question: null, snapshots: [{ snapshot_id: "snapshot-a", version: 1 }], formulations: [{ formulation_id: "f-a", version: 1, status: "CURRENT", summary: "CURRENT A", correction_text: null }] }));
    vi.mocked(api.actionList).mockImplementation(async (id) => ({ session_id: id, plans: id === "a" ? [{ plan_id: "plan-a", session_id: "a", version: 2, supersedes_plan_id: null, status: "CURRENT" as const, basis_snapshot_id: "snapshot-a", basis_formulation_id: "f-a", anchor_type: "FORMULATION" as const, anchor_id: "f-a", user_goal: "V3BC-GOAL-A", template_id: "PAUSE" as const, template_version: "v1", action_text: "V3BC-ACTION-A", method_version: "v1", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", outcome: { outcome_id: "outcome-a", status: "DONE" as const, note_text: "V3BC-OUTCOME-A", created_at: "2026-01-01T00:00:00Z" } }] : [] }));
    await mount(api); await click(byText("ДИНАМИКА ПО СЕССИЯМ")); const workspace = document.querySelector<HTMLElement>(".longitudinal-workspace")!;
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
    expect(document.querySelector("textarea")).toBeNull();
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
