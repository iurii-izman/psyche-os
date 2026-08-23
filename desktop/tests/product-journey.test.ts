import { describe, expect, it } from "vitest";

import { buildProductJourney, presentJourneyState } from "../src/product-journey";

const session = { session_id: "synthetic", title: "Синтетическая сессия", state: "ACTIVE" as const, retention: "ENCRYPTED_LOCAL" as const, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z", closed_at: null, turn_count: 1 };
const exploration = { context: [], hypotheses: [], snapshots: [], next_question: null, formulations: [{ formulation_id: "f", version: 1, status: "CURRENT" as const, summary: "Рабочая формулировка", correction_text: null }] };
const emptyExploration = { context: [], hypotheses: [], snapshots: [], next_question: null, formulations: [] };

describe("V3-E product journey projection", () => {
  it("reports only recorded availability, never completion or a recommendation", () => {
    const journey = buildProductJourney(session, exploration, []);
    expect(journey).toEqual({ has_turns: true, has_guided_exploration: true, has_current_formulation: true, has_action_plan: false, has_outcome: false });
    expect(Object.keys(journey).join(" ")).not.toMatch(/complete|progress|ready|score/i);
  });

  it("keeps an outcome distinct from effectiveness", () => {
    const journey = buildProductJourney(session, exploration, [{ outcome: { outcome_id: "o", status: "DONE", note_text: null, created_at: "2026-01-01T00:00:00Z" } } as never]);
    expect(journey.has_outcome).toBe(true);
    expect(presentJourneyState(journey.has_outcome, "Есть отметка", "Нет отметки")).toBe("Есть отметка");
  });

  it.each([
    ["empty", emptyExploration, false],
    ["snapshot only", { ...emptyExploration, snapshots: [{ snapshot_id: "s", version: 1 }] }, true],
    ["next question only", { ...emptyExploration, next_question: { question_id: "q", text: "Синтетический вопрос" } }, true],
    ["context only", { ...emptyExploration, context: [{ context_item_id: "c", dimension: "context", kind: "KNOWN" as const, text: "Синтетический контекст", state: "RECORDED", source_turn_ids: [] }] }, true],
    ["formulation only", exploration, true]
  ])("uses the accepted guided-exploration structure for %s", (_case, view, expected) => {
    expect(buildProductJourney(session, view, []).has_guided_exploration).toBe(expected);
  });

  it("treats missing exploration as absent", () => {
    expect(buildProductJourney(session, null, []).has_guided_exploration).toBe(false);
  });
});
