import { describe, expect, it } from "vitest";
import { buildPersonalLongitudinal, type PersonalLongitudinalBundle } from "../src/personal-longitudinal";
import type { PersonalModelView } from "../src/personal-api";

const bundle = (id: string, at: string): PersonalLongitudinalBundle => ({
  session: {
    session_id: id, title: `Размышление ${id}`, state: id === "later" ? "ACTIVE" : "CLOSED", turn_count: 1, created_at: at, updated_at: at,
    turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER", created_at: at, content: `Синтетический источник ${id}` }]
  },
  exploration: {
    context: [
      { context_item_id: `known-${id}`, kind: "KNOWN", dimension: "context", text: "Повторяющаяся фраза", state: "RESOLVED", source_turn_ids: [`turn-${id}`], created_at: at },
      { context_item_id: `unknown-${id}`, kind: "UNKNOWN", dimension: "context", text: "Открытый вопрос", state: id === "earlier" ? "OPEN" : "RESOLVED", source_turn_ids: [`turn-${id}`], created_at: at },
      { context_item_id: `contradiction-${id}`, kind: "CONTRADICTION", dimension: "context", text: "Разные ответы", state: "UNRESOLVED", source_turn_ids: [`turn-${id}`], created_at: at }
    ],
    hypotheses: [], next_question: null, snapshots: [],
    formulations: id === "earlier" ? [
      { formulation_id: "f1", version: 1, status: "SUPERSEDED", summary: "Первая версия", correction_text: null, created_at: at, updated_at: "2026-08-20T12:00:00Z" },
      { formulation_id: "f2", version: 2, parent_formulation_id: "f1", status: "CURRENT", summary: "Вторая версия", correction_text: "Уточнение пользователя", created_at: "2026-08-20T12:00:00Z", updated_at: "2026-08-20T12:00:00Z" }
    ] : [
      { formulation_id: "f3", version: 1, status: "PROPOSED", summary: "AI-derived proposal, not fact. Текст.\n\nUncertainty: Контекст ограничен.", correction_text: null, supporting_turn_ids: [`turn-${id}`], ai_provenance: { origin: "AI", provider: "openai", actual_model: "gpt-fixture" }, created_at: at, updated_at: at }
    ]
  }
});

describe("Personal longitudinal projection", () => {
  const now = new Date("2026-08-27T12:00:00Z");
  const earlier = bundle("earlier", "2026-08-01T10:00:00Z");
  const later = bundle("later", "2026-08-25T10:00:00Z");

  it("keeps chronology stable and applies practical period filters", () => {
    const all = buildPersonalLongitudinal([later, earlier], "all", now);
    const thirty = buildPersonalLongitudinal([later, earlier], "30d", now);
    const seven = buildPersonalLongitudinal([later, earlier], "7d", now);
    expect(all.sessions.map((item) => item.session.session_id)).toEqual(["earlier", "later"]);
    expect(all.timeline.map((item) => item.at)).toEqual([...all.timeline.map((item) => item.at)].sort());
    expect(thirty.timeline.some((item) => item.session_id === "earlier")).toBe(true);
    expect(seven.timeline.length).toBeGreaterThan(0);
    expect(seven.timeline.every((item) => Date.parse(item.at) >= Date.parse("2026-08-20T12:00:00Z"))).toBe(true);
  });

  it("preserves correction lineage and CURRENT to SUPERSEDED history", () => {
    const view = buildPersonalLongitudinal([earlier], "all", now);
    expect(view.lineages[0]?.items.map((item) => item.version)).toEqual([1, 2]);
    expect(view.lineages[0]?.items[1]?.parent_formulation_id).toBe("f1");
    expect(view.changes.some((item) => item.changed.includes("уточнения"))).toBe(true);
    expect(view.changes.some((item) => item.changed.includes("SUPERSEDED"))).toBe(true);
  });

  it("keeps AI provenance, unresolved material, and recurring themes source-backed", () => {
    const view = buildPersonalLongitudinal([earlier, later], "all", now);
    expect(view.timeline.some((item) => item.kind === "ai_proposal" && item.turn_ids.includes("turn-later"))).toBe(true);
    expect(view.proposed[0]).toMatchObject({ ai: true, turn_ids: ["turn-later"] });
    expect(view.unresolved).toEqual(expect.arrayContaining([expect.objectContaining({ kind: "UNKNOWN", first_seen: "2026-08-01T10:00:00Z" }), expect.objectContaining({ kind: "CONTRADICTION" })]));
    expect(view.themes[0]).toMatchObject({ label: "Повторяющаяся фраза", session_count: 2, sources: [expect.objectContaining({ session_id: "earlier", turn_ids: ["turn-earlier"] }), expect.objectContaining({ session_id: "later", turn_ids: ["turn-later"] })] });
  });

  it("handles a new owner without adding score or diagnosis semantics", () => {
    const view = buildPersonalLongitudinal([], "30d", now);
    expect(view.timeline).toEqual([]);
    expect(view.unresolved).toEqual([]);
    expect(JSON.stringify(view)).not.toMatch(/score|diagnos|symptom|streak/i);
  });

  it("shows how the model's understanding changed without claiming the person changed", () => {
    const model: PersonalModelView = {
      items: [
        {
          item_id: "m1",
          kind: "HYPOTHESIS",
          state: "ACTIVE",
          created_at: "2026-06-01T10:00:00Z",
          updated_at: "2026-08-10T10:00:00Z",
          current: null,
          challenges: [{ text: "Это было верно только для 2021–2022.", created_at: "2026-08-12T10:00:00Z" }],
          history: [
            { ordinal: 1, kind: "HYPOTHESIS", text: "Возможно, вы избегаете конфликтов.", temporal_scope: "UNCLEAR", revision_reason: null, status: "SUPERSEDED", created_at: "2026-06-01T10:00:00Z" },
            { ordinal: 2, kind: "HYPOTHESIS", text: "Паттерн может быть специфичен для рабочих ситуаций.", temporal_scope: "CONTEXTUAL_PATTERN", revision_reason: "Контрпример сузил версию.", status: "CURRENT", created_at: "2026-08-10T10:00:00Z" }
          ]
        }
      ]
    };
    const view = buildPersonalLongitudinal([], "all", now, model);
    expect(view.understanding).toHaveLength(2);
    expect(view.understanding[0]).toMatchObject({ earlier: "Возможно, вы избегаете конфликтов.", later: "Паттерн может быть специфичен для рабочих ситуаций.", changed: "Контрпример сузил версию." });
    expect(view.understanding[1]?.changed).toContain("Владелец оспорил");
    // The projection speaks about the model, never about the person's change.
    expect(JSON.stringify(view.understanding)).not.toMatch(/вы изменились|человек изменился/i);
  });
});
