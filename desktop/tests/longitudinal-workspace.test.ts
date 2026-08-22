import { describe, expect, it } from "vitest";
import type { LongitudinalSessionBundle } from "../src/longitudinal-workspace";
import { buildLongitudinalWorkspace, compareSessions, hasGuidedExploration } from "../src/longitudinal-workspace";

const bundle = (id: string, at: string, text: string, state = "OPEN", template = "contextual", outcome: "DONE" | "NOT_DONE" | "CANCELLED" | "UNKNOWN" | null = null): LongitudinalSessionBundle => ({
  session: { session_id: id, title: `Сессия ${id}`, state: id === "a" ? "CLOSED" : "ACTIVE", retention: "ENCRYPTED_LOCAL", created_at: at, updated_at: at, closed_at: id === "a" ? at : null, turn_count: 1, turns: [{ turn_id: `turn-${id}`, session_id: id, sequence: 1, actor: "USER", created_at: at, content: "синтетический текст" }] },
  exploration: { context: [
    { context_item_id: `known-${id}`, kind: "KNOWN", dimension: "context", text, state: "RECORDED", source_turn_ids: [`turn-${id}`], created_at: at },
    { context_item_id: `unknown-${id}`, kind: "UNKNOWN", dimension: "context", text: "Открытый вопрос", state, source_turn_ids: [], created_at: at },
    { context_item_id: `contradiction-${id}`, kind: "CONTRADICTION", dimension: "context", text: "Разные ответы", state: "OPEN", source_turn_ids: [`turn-${id}`], created_at: at }
  ], hypotheses: [{ hypothesis_id: `h-${id}`, template_id: template, proposal_text: `Вариант ${id}`, uncertainty_text: `Неизвестно ${id}`, discriminator_text: "Уточнить", context_refs: [{ context_item_id: `known-${id}`, relation: "SUPPORT", source_turn_ids: [] }, { context_item_id: `unknown-${id}`, relation: "UNKNOWN", source_turn_ids: [] }, { context_item_id: `contradiction-${id}`, relation: "COUNTEREVIDENCE", source_turn_ids: [] }] }], next_question: null, snapshots: [{ snapshot_id: `snapshot-${id}`, version: 1, created_at: at }], formulations: [{ formulation_id: `f-${id}`, version: 1, status: "CURRENT", summary: `Формулировка ${id}`, correction_text: null, created_at: at, updated_at: at }] },
  plans: [{ plan_id: `plan-${id}`, session_id: id, version: 1, supersedes_plan_id: null, status: "CURRENT", basis_snapshot_id: `snapshot-${id}`, basis_formulation_id: `f-${id}`, anchor_type: "FORMULATION", anchor_id: `f-${id}`, user_goal: "Цель", template_id: "PAUSE", template_version: "v1", action_text: `Шаг ${id}`, method_version: "v1", created_at: at, updated_at: at, outcome: outcome ? { outcome_id: `outcome-${id}`, status: outcome, note_text: "синтетическая отметка", created_at: at } : null }]
});

describe("V3-B/C deterministic longitudinal projection", () => {
  it("groups recurrence only by exact kind, dimension, trimmed text and counts distinct sessions", () => {
    const a = bundle("a", "2026-01-01T00:00:00Z", "Точно "); a.exploration!.context.push({ ...a.exploration!.context[0]!, context_item_id: "duplicate", text: "Точно ", source_turn_ids: [] });
    const b = bundle("b", "2026-01-02T00:00:00Z", "Точно"); const c = bundle("c", "2026-01-03T00:00:00Z", "точно"); c.exploration!.context[0]!.dimension = "impact";
    const view = buildLongitudinalWorkspace([c, b, a]); expect(view.recurrences).toHaveLength(1); expect(view.recurrences[0]).toMatchObject({ text: "Точно", session_count: 2, occurrence_count: 3 });
  });
  it("counts guided coverage only when persisted exploration structure exists", () => {
    const empty = bundle("empty", "2026-01-01T00:00:00Z", "x"); empty.exploration = { context: [], hypotheses: [], snapshots: [], formulations: [], next_question: null };
    const context = bundle("context", "2026-01-02T00:00:00Z", "x"); const snapshot = bundle("snapshot", "2026-01-03T00:00:00Z", "x"); snapshot.exploration = { context: [], hypotheses: [], snapshots: [{ snapshot_id: "s", version: 1 }], formulations: [], next_question: null };
    expect(hasGuidedExploration(empty.exploration)).toBe(false); expect(buildLongitudinalWorkspace([empty, context, snapshot]).coverage.guided).toBe(2); expect(buildLongitudinalWorkspace([]).coverage.guided).toBe(0);
  });
  it("keeps all CURRENT formulations separate, orders chronologically, and has deterministic text diffs", () => {
    const view = buildLongitudinalWorkspace([bundle("b", "2026-01-02T00:00:00Z", "x"), bundle("a", "2026-01-01T00:00:00Z", "x")]); expect(view.formulations.map((x) => x.session.session_id)).toEqual(["a", "b"]); expect(view.formulations[1]!.diff).toEqual({ added_lines: ["Формулировка b"], removed_lines: ["Формулировка a"] });
  });
  it("groups hypotheses only by template id and preserves relation types", () => { const view = buildLongitudinalWorkspace([bundle("a", "2026-01-01T00:00:00Z", "x", "OPEN", "same"), bundle("b", "2026-01-02T00:00:00Z", "x", "OPEN", "same")]); expect(view.hypotheses[0]!.entries).toHaveLength(2); expect(view.hypotheses[0]!.entries[0]!.refs.SUPPORT).toHaveLength(1); expect(JSON.stringify(view)).not.toMatch(/likelihood|confidence|score|rank/i); });
  it("keeps unknown states explicit and never turns later absence into resolution", () => { const a = bundle("a", "2026-01-01T00:00:00Z", "x", "SKIPPED"); const b = bundle("b", "2026-01-02T00:00:00Z", "x", "RESOLVED"); expect(buildLongitudinalWorkspace([a, b]).unknowns[0]!.session_count).toBe(2); expect(a.exploration!.context[1]!.state).toBe("SKIPPED"); });
  it("retains singleton unknowns and contradictions with per-session state and anchors", () => {
    const a = bundle("a", "2026-01-01T00:00:00Z", "x", "OPEN"); a.exploration!.context.push({ ...a.exploration!.context[2]!, context_item_id: "contradiction-a-2", state: "SKIPPED" }); const b = bundle("b", "2026-01-02T00:00:00Z", "x", "SKIPPED"); b.exploration!.context = b.exploration!.context.filter((item) => item.kind === "KNOWN");
    const view = buildLongitudinalWorkspace([a, b]); expect(view.unknowns).toHaveLength(1); expect(view.unknowns[0]).toMatchObject({ session_count: 1, occurrences: [{ session_id: "a", state: "OPEN" }] }); expect(view.contradictions[0]!.occurrences).toMatchObject([{ state: "OPEN", anchors: ["ваш ответ №1"], occurrence_count: 2 }, { state: "SKIPPED", occurrence_count: 2 }]);
  });
  it("groups repeated unknowns without using state as identity and keeps both states", () => {
    const view = buildLongitudinalWorkspace([bundle("a", "2026-01-01T00:00:00Z", "x", "OPEN"), bundle("b", "2026-01-02T00:00:00Z", "x", "SKIPPED")]); expect(view.unknowns[0]).toMatchObject({ session_count: 2, occurrences: [{ state: "OPEN" }, { state: "SKIPPED" }] });
  });
  it("retains contradiction anchors, action provenance/outcome status, and persisted-only timeline ties", () => { const a = bundle("a", "2026-01-01T00:00:00Z", "x", "OPEN", "contextual", "DONE"); const view = buildLongitudinalWorkspace([a]); expect(view.plans[0]!.action_text).toBe("Шаг a"); expect(view.timeline.every((event) => event.at === "2026-01-01T00:00:00Z")).toBe(true); expect(view.timeline.map((e) => e.type)).toContain("outcome"); });
  it("compares exact records with absence, never a score, and handles an empty projection", () => { const a = bundle("a", "2026-01-01T00:00:00Z", "общее"), b = bundle("b", "2026-01-02T00:00:00Z", "другое"); const comparison = compareSessions(a, b); expect(comparison.common).toHaveLength(2); expect(comparison.only_a.map((x) => x.text)).toContain("общее"); expect(comparison.only_b.map((x) => x.text)).toContain("другое"); expect(buildLongitudinalWorkspace([]).coverage.sessions).toBe(0); });
  it("compares unknown state, hypotheses, and complete action history without synthetic resolution", () => {
    const a = bundle("a", "2026-01-01T00:00:00Z", "x", "OPEN", "same", "DONE"), b = bundle("b", "2026-01-02T00:00:00Z", "x", "RESOLVED", "same", "NOT_DONE"); const absent = bundle("c", "2026-01-03T00:00:00Z", "x"); absent.exploration!.context = absent.exploration!.context.filter((item) => item.kind !== "UNKNOWN");
    const comparison = compareSessions(a, b), absence = compareSessions(a, absent); expect(comparison.unknowns[0]).toMatchObject({ a: [{ state: "OPEN" }], b: [{ state: "RESOLVED" }] }); expect(absence.unknowns[0]!.b).toEqual([]); expect(comparison.hypotheses[0]).toMatchObject({ template_id: "same", a: { hypothesis: { proposal_text: "Вариант a" }, refs: { SUPPORT: [{ item: { text: "x" } }] } }, b: { hypothesis: { proposal_text: "Вариант b" } } }); expect(comparison.actions.a[0]).toMatchObject({ user_goal: "Цель", version: 1, basis_snapshot_id: "snapshot-a", anchor_id: "f-a", action_text: "Шаг a", outcome: { status: "DONE" } });
  });
});
