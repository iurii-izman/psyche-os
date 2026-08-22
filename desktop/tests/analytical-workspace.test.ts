import { describe, expect, it } from "vitest";

import type { ExplorationView, ReflectionSessionView } from "../src/api";
import { buildAnalyticalWorkspace, formulationDiff } from "../src/analytical-workspace";

const session: ReflectionSessionView = {
  session_id: "session-1", title: "Синтетическая сессия", state: "CLOSED", retention: "ENCRYPTED_LOCAL", created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:03:00Z", closed_at: "2026-01-01T00:03:00Z", turn_count: 2,
  turns: [
    { turn_id: "turn-1", session_id: "session-1", sequence: 1, actor: "USER", created_at: "2026-01-01T00:00:01Z", content: "Первый синтетический ответ" },
    { turn_id: "turn-2", session_id: "session-1", sequence: 2, actor: "USER", created_at: "2026-01-01T00:00:02Z", content: "Второй синтетический ответ" }
  ]
};

const exploration: ExplorationView = {
  context: [
    { context_item_id: "known", dimension: "user_report", kind: "KNOWN", text: "Зафиксировано в ответе", state: "RECORDED", source_turn_ids: ["turn-1"], created_at: "2026-01-01T00:00:01Z" },
    { context_item_id: "skipped", dimension: "future_dimension", kind: "UNKNOWN", text: "Ответ пропущен", state: "SKIPPED", source_turn_ids: ["turn-2"], created_at: "2026-01-01T00:00:02Z" },
    { context_item_id: "open", dimension: "context", kind: "UNKNOWN", text: "Открытый вопрос", state: "OPEN", source_turn_ids: [], created_at: "2026-01-01T00:00:03Z" },
    { context_item_id: "conflict", dimension: "context", kind: "CONTRADICTION", text: "Разные синтетические ответы", state: "OPEN", source_turn_ids: ["turn-1", "turn-2"], created_at: "2026-01-01T00:00:04Z" }
  ],
  hypotheses: [{ hypothesis_id: "hypothesis-1", proposal_text: "Рабочий вариант", uncertainty_text: "Не установленный факт", discriminator_text: "Нужен дополнительный ответ", context_refs: [
    { context_item_id: "known", relation: "SUPPORT", source_turn_ids: ["turn-1"] },
    { context_item_id: "conflict", relation: "COUNTEREVIDENCE", source_turn_ids: ["turn-1", "turn-2"] },
    { context_item_id: "skipped", relation: "UNKNOWN", source_turn_ids: ["turn-2"] }
  ] }],
  next_question: null,
  snapshots: [{ snapshot_id: "snapshot-1", version: 1, created_at: "2026-01-01T00:00:02Z" }],
  formulations: [
    { formulation_id: "formulation-2", version: 2, parent_formulation_id: "formulation-1", status: "PROPOSED", summary: "Основа\nДобавлено", correction_text: "Добавлено", created_at: "2026-01-01T00:00:03Z", updated_at: "2026-01-01T00:00:03Z" },
    { formulation_id: "formulation-1", version: 1, parent_formulation_id: null, status: "CURRENT", summary: "Основа\nУбрано", correction_text: null, created_at: "2026-01-01T00:00:02Z", updated_at: "2026-01-01T00:00:02Z" }
  ]
};

describe("V3-A2 analytical projection", () => {
  it("presents only CURRENT as current and preserves all formulation history with a deterministic diff", () => {
    const view = buildAnalyticalWorkspace(session, exploration);
    expect(view.current?.formulation_id).toBe("formulation-1");
    expect(view.formulations.map((item) => item.version)).toEqual([1, 2]);
    expect(view.formulations[1]!).toMatchObject({ comparison_label: "Сравнение с версией 1", added_lines: ["Добавлено"], removed_lines: ["Убрано"] });
    expect(formulationDiff("a\nb", "a\nc")).toEqual({ added_lines: ["c"], removed_lines: ["b"] });
  });

  it("keeps support, counterevidence, unknowns, source anchors, and unknown dimensions distinct", () => {
    const view = buildAnalyticalWorkspace(session, exploration);
    expect(view.hypotheses[0]!.support[0]!.context.text).toBe("Зафиксировано в ответе");
    expect(view.hypotheses[0]!.counterevidence[0]!.context.text).toBe("Разные синтетические ответы");
    expect(view.hypotheses[0]!.unknown[0]!.context.source_anchors).toEqual(["ваш ответ №2 (turn-2)"]);
    expect(view.unresolved_unknowns.map((item) => [item.text, item.state])).toEqual([["Открытый вопрос", "OPEN"], ["Ответ пропущен", "SKIPPED"]]);
    expect(view.context_by_dimension.map((group) => group.dimension)).toContain("future_dimension");
    expect(view.contradictions[0]!.source_anchors).toEqual(["ваш ответ №1 (turn-1)", "ваш ответ №2 (turn-2)"]);
  });

  it("orders product events by persisted timestamp and stable ties without inventing missing events", () => {
    const view = buildAnalyticalWorkspace(session, exploration);
    expect(view.timeline.map((event) => [event.at, event.kind, event.id])).toEqual([
      ["2026-01-01T00:00:01Z", "turn", "turn-1"],
      ["2026-01-01T00:00:02Z", "formulation", "formulation-1"],
      ["2026-01-01T00:00:02Z", "snapshot", "snapshot-1"],
      ["2026-01-01T00:00:02Z", "turn", "turn-2"],
      ["2026-01-01T00:00:03Z", "formulation", "formulation-2"]
    ]);
  });
});
