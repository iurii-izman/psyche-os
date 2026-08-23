import { describe, expect, it, vi } from "vitest";

import type { DesktopApi, ReflectionSessionView } from "../src/api";
import { mount } from "../src/main";

const wait = () => new Promise((resolve) => setTimeout(resolve, 0));
const click = async (node: HTMLElement) => { node.click(); await wait(); };
const button = (text: string) => {
  const node = [...document.querySelectorAll<HTMLButtonElement>("button")].find((item) => item.textContent === text);
  if (!node) throw new Error(`Missing button: ${text}`);
  return node;
};

describe("RC0 first-user synthetic product journey", () => {
  it("keeps the accepted lifecycle truthful from unlock through restart, control, and deletion", async () => {
    let locked = true;
    const sessions: ReflectionSessionView[] = [];
    const session = (id: string, title: string, state: "ACTIVE" | "CLOSED", text = "") => ({
      session_id: id, title, state, retention: "ENCRYPTED_LOCAL" as const,
      created_at: `2026-08-23T00:00:0${sessions.length}Z`, updated_at: "2026-08-23T00:00:00Z",
      closed_at: state === "CLOSED" ? "2026-08-23T00:01:00Z" : null, turn_count: text ? 1 : 0,
      turns: text ? [{ turn_id: `${id}-turn`, session_id: id, sequence: 1, actor: "USER" as const, created_at: "2026-08-23T00:00:00Z", content: text }] : []
    });
    const api = {
      status: vi.fn(async () => ({ locked, data_mode: "SYNTHETIC_ONLY", real_data_gate: "CLOSED", inbound_listener: "NONE", outbound_provider: "NOT_CONFIGURED", runtime_profile: "SYNTHETIC_LAB", build_version: "0.2.0", privacy: { core_processing_location: "LOCAL", cloud_storage: "DISABLED", cloud_disclosure: "SYNTHETIC_EXPLICIT_E07_ONLY", telemetry: "OFF" } })),
      unlock: vi.fn(async () => { locked = false; return { session_token: "opaque" }; }),
      lock: vi.fn(async () => ({ locked: true })),
      reflectionList: vi.fn(async () => ({ sessions })),
      reflectionCreate: vi.fn(async (title: string) => { const created = session(`s${sessions.length + 1}`, title, "ACTIVE"); sessions.push(created); return created; }),
      reflectionGet: vi.fn(async (id: string) => sessions.find((item) => item.session_id === id)!),
      reflectionAddTurn: vi.fn(async (id: string, text: string) => { const value = sessions.find((item) => item.session_id === id)!; value.turn_count = 1; value.turns = [{ turn_id: `${id}-turn`, session_id: id, sequence: 1, actor: "USER", created_at: "2026-08-23T00:00:00Z", content: text }]; return value.turns[0]; }),
      reflectionClose: vi.fn(async (id: string) => { const value = sessions.find((item) => item.session_id === id)!; value.state = "CLOSED"; value.closed_at = "2026-08-23T00:01:00Z"; return { state: "CLOSED" }; }),
      reflectionDelete: vi.fn(async (id: string) => { sessions.splice(sessions.findIndex((item) => item.session_id === id), 1); return { deleted: true, content_in_receipt: false }; }),
      explorationStart: vi.fn(async () => ({ context: [{ context_item_id: "u", dimension: "context", kind: "UNKNOWN", text: "Что ещё важно уточнить", state: "OPEN", source_turn_ids: ["s1-turn"] }], hypotheses: [{ hypothesis_id: "h", proposal_text: "Рабочая альтернатива", uncertainty_text: "Не установлено", discriminator_text: "Уточнить", context_refs: [] }], next_question: null, snapshots: [], formulations: [{ formulation_id: "f", version: 1, status: "CURRENT", summary: "Рабочая формулировка", correction_text: null }] })),
      explorationGet: vi.fn(async () => ({ context: [{ context_item_id: "u", dimension: "context", kind: "UNKNOWN", text: "Что ещё важно уточнить", state: "OPEN", source_turn_ids: ["s1-turn"] }], hypotheses: [{ hypothesis_id: "h", proposal_text: "Рабочая альтернатива", uncertainty_text: "Не установлено", discriminator_text: "Уточнить", context_refs: [] }], next_question: null, snapshots: [], formulations: [{ formulation_id: "f", version: 1, status: "CURRENT", summary: "Рабочая формулировка", correction_text: null }] })),
      actionList: vi.fn(async (session_id: string) => ({ session_id, plans: [] })),
      actionOptions: vi.fn(async () => ({ session_id: "s1", anchor_type: null, anchor_id: null, options: [] })),
      planDeletion: vi.fn(async () => ({ plan_id: "delete-preview", affected_counts: { sessions: 1 }, external_limitations: [] })),
      executeDeletion: vi.fn(async () => ({ receipt_id: "delete-receipt", content_in_receipt: false })),
      backupStatus: vi.fn(async () => ({ state: "VERIFIED_SYNTHETIC", export_is_backup: false })),
      verifyBackup: vi.fn(async () => ({ verified: true, content_disclosed: false })),
      validateRecovery: vi.fn(async () => ({ candidate_id: "candidate", validated: true, activated: false, active_vault_preserved: true })),
      activateRecovery: vi.fn(async () => ({ activated: true, previous_vault_retained: true })),
      previewExport: vi.fn(async () => ({ preview_id: "export-preview", purpose: "portability", audience: "owner", scope: "synthetic", encrypted: true, redacted: true, export_is_backup: false })),
      executeExport: vi.fn(async () => ({ export_id: "export-receipt", purpose: "portability", audience: "owner", scope: "synthetic", encrypted: true, redacted: true, export_is_backup: false }))
    } as unknown as DesktopApi;

    await mount(api);
    expect(document.body.textContent).toContain("Разблокировать синтетическое хранилище");
    const secret = document.querySelector<HTMLInputElement>("#unlock-secret")!;
    secret.value = "synthetic-only"; secret.form!.requestSubmit(); await wait();
    expect(document.body.textContent).toContain("МОЁ ПРОСТРАНСТВО");

    await click(button("Начать первую сессию"));
    const title = document.querySelector<HTMLInputElement>("#reflection-title")!;
    title.value = "Первая запись"; title.form!.requestSubmit(); await wait();
    const text = document.querySelector<HTMLTextAreaElement>("#reflection-turn")!;
    text.value = "Только синтетический пользовательский текст"; await click(button("Добавить в сессию"));
    expect(document.body.textContent).toContain("Ваш текст");
    expect(document.body.textContent).toContain("Рабочая альтернатива");
    expect(document.body.textContent).toContain("Что пока неизвестно");
    expect(document.body.textContent).toContain("не диагноз и не установленный факт");

    await click(button("Завершить сессию"));
    expect(document.body.textContent).toContain("ЗАКРЫТАЯ СЕССИЯ · ТОЛЬКО ЧТЕНИЕ");
    expect(document.querySelector<HTMLTextAreaElement>("#reflection-turn")!.disabled).toBe(true);
    expect(button("Удалить сессию").disabled).toBe(false);
    await click(button("К чему вернуться"));
    await click(button("Начать новую сессию"));
    expect(document.querySelector(".follow-up-workspace")?.textContent).toContain("Записано ранее");
    const followUp = document.querySelector<HTMLTextAreaElement>("#follow-up-text")!;
    followUp.value = "Только новый текст"; followUp.form!.requestSubmit(); await wait(); await wait();
    expect(vi.mocked(api.reflectionAddTurn).mock.calls.at(-1)).toEqual(["s2", "Только новый текст"]);

    await click(button("Динамика"));
    expect(document.querySelector(".longitudinal-workspace")?.textContent).toContain("ДИНАМИКА ПО СЕССИЯМ");
    expect(document.body.textContent).toContain("не о его пользе или эффективности");
    expect(document.body.textContent).not.toMatch(/progress|рекомендац|срочн|\d+%/i);
    await click(button("Сессии"));
    await click(button("Открыть сессию"));
    await click(button("Удалить сессию"));
    expect(sessions).toHaveLength(1);

    const purpose = document.querySelector<HTMLInputElement>("#export-purpose")!;
    purpose.value = "portability";
    document.querySelector<HTMLInputElement>("#export-audience")!.value = "owner";
    document.querySelector<HTMLInputElement>("#export-scope")!.value = "synthetic";
    const exportForm = purpose.form!;
    exportForm.requestSubmit(); await wait(); await click(button("Подтвердить синтетический экспорт"));
    expect(api.executeExport).toHaveBeenCalledWith("export-preview", "EXPORT SYNTHETIC PACKAGE");
    await mount(api);
    expect(document.body.textContent).toContain("МОЁ ПРОСТРАНСТВО");
    expect(document.body.textContent).toContain("Новая запись");
  });
});
