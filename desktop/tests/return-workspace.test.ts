import { describe, expect, it } from "vitest";
import { buildReturnWorkspace } from "../src/return-workspace";
import type { LongitudinalSessionBundle } from "../src/longitudinal-workspace";

const bundle = (id: string, at: string, sessionState: "ACTIVE" | "CLOSED" = "ACTIVE"): LongitudinalSessionBundle => ({
  session: { session_id: id, title: `Сессия ${id}`, state: sessionState, retention: "ENCRYPTED_LOCAL", created_at: at, updated_at: at, closed_at: sessionState === "CLOSED" ? at : null, turn_count: 1, turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER", created_at: at, content: "синтетический текст" }] },
  exploration: { context: [{ context_item_id: `open-${id}`, dimension: "context", kind: "UNKNOWN", text: `Вопрос ${id}`, state: "OPEN", source_turn_ids: [`turn-${id}`], created_at: at }, { context_item_id: `skipped-${id}`, dimension: "context", kind: "UNKNOWN", text: `Пропущено ${id}`, state: "SKIPPED", source_turn_ids: [], created_at: at }], hypotheses: [], next_question: null, snapshots: [], formulations: [{ formulation_id: `f-${id}`, version: 1, status: "CURRENT", summary: `Формулировка ${id}`, correction_text: null, created_at: at, updated_at: at }] },
  plans: [{ plan_id: `p-${id}`, session_id: id, version: 1, supersedes_plan_id: null, status: "CURRENT", basis_snapshot_id: null, basis_formulation_id: null, anchor_type: "FORMULATION", anchor_id: `f-${id}`, user_goal: "Моя цель", template_id: "PAUSE", template_version: "v1", action_text: `Шаг ${id}`, method_version: "v1", created_at: at, updated_at: at, outcome: { outcome_id: `o-${id}`, status: "DONE", note_text: null, created_at: at } }]
});

describe("V3-D deterministic return projection", () => {
  it("organizes fixed categories and chronology without a score, rank, urgency, or recommendation", () => {
    const view = buildReturnWorkspace([bundle("b", "2026-01-02T00:00:00Z"), bundle("a", "2026-01-01T00:00:00Z")]);
    expect(view.by_category.OPEN_UNKNOWN.map((x) => x.session_id)).toEqual(["a", "a", "b", "b"]);
    expect(JSON.stringify(view)).not.toMatch(/score|rank|urgent|recommend/i);
  });
  it("keeps OPEN and SKIPPED descriptive, not urgent or resolved through absence", () => {
    const view = buildReturnWorkspace([bundle("a", "2026-01-01T00:00:00Z"), { ...bundle("b", "2026-01-02T00:00:00Z"), exploration: { context: [], hypotheses: [], snapshots: [], formulations: [], next_question: null } }]);
    expect(view.by_category.OPEN_UNKNOWN.map((x) => x.state)).toEqual(["OPEN", "SKIPPED"]);
  });
  it("keeps DONE as a recorded outcome, not effectiveness, and exposes provenance", () => {
    const view = buildReturnWorkspace([bundle("a", "2026-01-01T00:00:00Z", "CLOSED")]);
    expect(view.by_category.OUTCOME[0]).toMatchObject({ state: "DONE", provenance: "USER_AUTHORED", session_state: "CLOSED" });
    expect(view.by_category.OPEN_UNKNOWN[0]?.source_anchors).toEqual(["ваш ответ №1"]);
  });
  it("has a neutral empty state projection and derives identically from the same records", () => {
    expect(buildReturnWorkspace([]).candidates).toEqual([]);
    const source = [bundle("a", "2026-01-01T00:00:00Z")];
    expect(buildReturnWorkspace(source)).toEqual(buildReturnWorkspace(source));
  });
});
