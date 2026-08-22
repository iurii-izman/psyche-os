import type { ActionPlan, ExplorationContextItem, ExplorationFormulation, ExplorationHypothesis, ExplorationView, ReflectionSessionView } from "./api";
import { formulationDiff } from "./analytical-workspace";

export interface LongitudinalSessionBundle { session: ReflectionSessionView; exploration: ExplorationView | null; plans: ActionPlan[]; }
export interface LongitudinalContextOccurrence { session_id: string; title: string; session_at: string; at: string; context_item_id: string; state: string; anchors: string[]; occurrence_count: number; item: ExplorationContextItem; }
export interface LongitudinalContextGroup { kind: string; dimension: string; text: string; session_count: number; occurrence_count: number; occurrences: LongitudinalContextOccurrence[]; }
export interface ProductTimelineEvent { at: string; type: string; id: string; session_id: string; detail: string; }
export type HypothesisRefs = { SUPPORT: LongitudinalContextOccurrence[]; COUNTEREVIDENCE: LongitudinalContextOccurrence[]; UNKNOWN: LongitudinalContextOccurrence[] };
export interface SessionHypothesis { hypothesis: ExplorationHypothesis; refs: HypothesisRefs; }
export interface SessionUnknownComparison { dimension: string; text: string; a: ExplorationContextItem[]; b: ExplorationContextItem[]; }
export interface SessionHypothesisComparison { template_id: string; a: SessionHypothesis | null; b: SessionHypothesis | null; }
export interface LongitudinalWorkspace {
  sessions: LongitudinalSessionBundle[]; coverage: { sessions: number; guided: number; current: number; plans: number; outcomes: number };
  formulations: Array<{ session: ReflectionSessionView; formulation: ExplorationFormulation; diff: { added_lines: string[]; removed_lines: string[] } | null }>;
  recurrences: LongitudinalContextGroup[]; hypotheses: Array<{ template_id: string; entries: Array<{ session: ReflectionSessionView; hypothesis: ExplorationHypothesis; refs: HypothesisRefs }> }>;
  unknowns: LongitudinalContextGroup[]; contradictions: LongitudinalContextGroup[]; plans: ActionPlan[]; timeline: ProductTimelineEvent[];
}
export interface SessionComparison {
  a: LongitudinalSessionBundle; b: LongitudinalSessionBundle; common: ExplorationContextItem[]; only_a: ExplorationContextItem[]; only_b: ExplorationContextItem[];
  current_a: ExplorationFormulation | null; current_b: ExplorationFormulation | null; formulation_diff: { added_lines: string[]; removed_lines: string[] } | null;
  unknowns: SessionUnknownComparison[]; contradictions_common: ExplorationContextItem[]; contradictions_only_a: ExplorationContextItem[]; contradictions_only_b: ExplorationContextItem[];
  hypotheses: SessionHypothesisComparison[]; actions: { a: ActionPlan[]; b: ActionPlan[] };
}

const cmp = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;
const sessionAt = (s: ReflectionSessionView): string => s.created_at;
const ordered = (bundles: LongitudinalSessionBundle[]): LongitudinalSessionBundle[] => [...bundles].sort((a, b) => cmp(sessionAt(a.session), sessionAt(b.session)) || cmp(a.session.session_id, b.session.session_id));
const current = (e: ExplorationView | null): ExplorationFormulation | null => e?.formulations.find((f) => f.status === "CURRENT") ?? null;
const contextKey = (item: ExplorationContextItem): string => `${item.kind}\u0000${item.dimension}\u0000${item.text.trim()}`;
const unknownKey = (item: ExplorationContextItem): string => `${item.dimension}\u0000${item.text.trim()}`;
const anchors = (session: ReflectionSessionView, item: ExplorationContextItem): string[] => item.source_turn_ids.map((id) => {
  const turn = session.turns?.find((value) => value.turn_id === id); return turn ? `ваш ответ №${turn.sequence}` : `источник ${id}`;
}).sort(cmp);

export function hasGuidedExploration(exploration: ExplorationView | null): boolean {
  return exploration !== null && (exploration.context.length > 0 || exploration.hypotheses.length > 0 || exploration.snapshots.length > 0 || exploration.formulations.length > 0 || exploration.next_question !== null);
}
function occurrence(bundle: LongitudinalSessionBundle, item: ExplorationContextItem, count: number): LongitudinalContextOccurrence {
  return { session_id: bundle.session.session_id, title: bundle.session.title, session_at: sessionAt(bundle.session), at: item.created_at ?? sessionAt(bundle.session), context_item_id: item.context_item_id, state: item.state, anchors: anchors(bundle.session, item), occurrence_count: count, item };
}
function groups(bundles: LongitudinalSessionBundle[], predicate: (item: ExplorationContextItem) => boolean, groupKey: (item: ExplorationContextItem) => string, recurring: boolean): LongitudinalContextGroup[] {
  const map = new Map<string, Array<{ bundle: LongitudinalSessionBundle; item: ExplorationContextItem }>>();
  for (const bundle of bundles) for (const item of bundle.exploration?.context ?? []) if (predicate(item)) map.set(groupKey(item), [...(map.get(groupKey(item)) ?? []), { bundle, item }]);
  return [...map.values()].map((items) => {
    const first = items[0]!.item; const perSession = new Map<string, typeof items>();
    for (const value of items) perSession.set(value.bundle.session.session_id, [...(perSession.get(value.bundle.session.session_id) ?? []), value]);
    const occurrences = [...perSession.values()].flatMap((values) => values.map((value) => occurrence(value.bundle, value.item, values.length))).sort((a, b) => cmp(a.at, b.at) || cmp(a.session_id, b.session_id) || cmp(a.context_item_id, b.context_item_id));
    return { kind: first.kind, dimension: first.dimension, text: first.text.trim(), session_count: perSession.size, occurrence_count: items.length, occurrences };
  }).filter((group) => !recurring || group.session_count >= 2).sort((a, b) => cmp(a.text, b.text) || cmp(a.dimension, b.dimension) || cmp(a.kind, b.kind));
}
function hypothesisFor(bundle: LongitudinalSessionBundle, hypothesis: ExplorationHypothesis): SessionHypothesis {
  const refs: HypothesisRefs = { SUPPORT: [], COUNTEREVIDENCE: [], UNKNOWN: [] }; const all = new Map((bundle.exploration?.context ?? []).map((item) => [item.context_item_id, item]));
  for (const ref of hypothesis.context_refs) { const item = all.get(ref.context_item_id); if (item) refs[ref.relation].push(occurrence(bundle, item, 1)); }
  return { hypothesis, refs };
}
function sessionHypotheses(bundle: LongitudinalSessionBundle): Map<string, SessionHypothesis> {
  return new Map((bundle.exploration?.hypotheses ?? []).flatMap((hypothesis) => hypothesis.template_id ? [[hypothesis.template_id, hypothesisFor(bundle, hypothesis)] as const] : []));
}

export function buildLongitudinalWorkspace(input: LongitudinalSessionBundle[]): LongitudinalWorkspace {
  const sessions = ordered(input);
  const formulations = sessions.flatMap((bundle, index) => { const formulation = current(bundle.exploration); if (!formulation) return []; const previous = sessions.slice(0, index).reverse().map((value) => current(value.exploration)).find(Boolean); return [{ session: bundle.session, formulation, diff: previous ? formulationDiff(previous.summary, formulation.summary) : null }]; });
  const hypotheses = new Map<string, LongitudinalWorkspace["hypotheses"][number]>();
  for (const bundle of sessions) for (const hypothesis of bundle.exploration?.hypotheses ?? []) if (hypothesis.template_id) { const trajectory = hypotheses.get(hypothesis.template_id) ?? { template_id: hypothesis.template_id, entries: [] }; trajectory.entries.push({ session: bundle.session, ...hypothesisFor(bundle, hypothesis) }); hypotheses.set(hypothesis.template_id, trajectory); }
  const timeline: ProductTimelineEvent[] = [];
  for (const bundle of sessions) { const s = bundle.session; timeline.push({ at: s.created_at, type: "session_created", id: s.session_id, session_id: s.session_id, detail: s.title }); if (s.closed_at) timeline.push({ at: s.closed_at, type: "session_closed", id: s.session_id, session_id: s.session_id, detail: s.title }); for (const turn of s.turns ?? []) timeline.push({ at: turn.created_at, type: "user_turn", id: turn.turn_id, session_id: s.session_id, detail: `Ваш ответ №${turn.sequence}` }); for (const snapshot of bundle.exploration?.snapshots ?? []) if (snapshot.created_at) timeline.push({ at: snapshot.created_at, type: "snapshot", id: snapshot.snapshot_id, session_id: s.session_id, detail: `Снимок v${snapshot.version}` }); for (const formulation of bundle.exploration?.formulations ?? []) if (formulation.created_at) timeline.push({ at: formulation.created_at, type: "formulation", id: formulation.formulation_id, session_id: s.session_id, detail: `Формулировка v${formulation.version}` }); for (const plan of bundle.plans) { timeline.push({ at: plan.created_at, type: "plan", id: plan.plan_id, session_id: s.session_id, detail: plan.action_text }); if (plan.outcome) timeline.push({ at: plan.outcome.created_at, type: "outcome", id: plan.outcome.outcome_id, session_id: s.session_id, detail: plan.outcome.status }); } }
  return { sessions, coverage: { sessions: sessions.length, guided: sessions.filter((b) => hasGuidedExploration(b.exploration)).length, current: formulations.length, plans: sessions.reduce((n, b) => n + b.plans.length, 0), outcomes: sessions.reduce((n, b) => n + b.plans.filter((p) => p.outcome).length, 0) }, formulations, recurrences: groups(sessions, (item) => item.kind === "KNOWN", contextKey, true), hypotheses: [...hypotheses.values()].sort((a, b) => cmp(a.template_id, b.template_id)), unknowns: groups(sessions, (item) => item.kind === "UNKNOWN", unknownKey, false), contradictions: groups(sessions, (item) => item.kind === "CONTRADICTION", contextKey, false), plans: sessions.flatMap((b) => b.plans).sort((a, b) => cmp(a.created_at, b.created_at) || cmp(a.plan_id, b.plan_id)), timeline: timeline.sort((a, b) => cmp(a.at, b.at) || cmp(a.type, b.type) || cmp(a.id, b.id)) };
}
export function compareSessions(a: LongitudinalSessionBundle, b: LongitudinalSessionBundle): SessionComparison {
  const ac = a.exploration?.context ?? [], bc = b.exploration?.context ?? []; const bKeys = new Set(bc.map(contextKey)), aKeys = new Set(ac.map(contextKey)); const currentA = current(a.exploration), currentB = current(b.exploration);
  const unknownMap = new Map<string, SessionUnknownComparison>();
  for (const [side, records] of [["a", ac], ["b", bc]] as const) for (const item of records.filter((value) => value.kind === "UNKNOWN")) { const itemKey = unknownKey(item); const entry = unknownMap.get(itemKey) ?? { dimension: item.dimension, text: item.text.trim(), a: [], b: [] }; entry[side].push(item); unknownMap.set(itemKey, entry); }
  const ah = sessionHypotheses(a), bh = sessionHypotheses(b); const templates = [...new Set([...ah.keys(), ...bh.keys()])].sort(cmp);
  return { a, b, common: ac.filter((item) => bKeys.has(contextKey(item))), only_a: ac.filter((item) => !bKeys.has(contextKey(item))), only_b: bc.filter((item) => !aKeys.has(contextKey(item))), current_a: currentA, current_b: currentB, formulation_diff: currentA && currentB ? formulationDiff(currentA.summary, currentB.summary) : null, unknowns: [...unknownMap.values()].sort((x, y) => cmp(x.text, y.text) || cmp(x.dimension, y.dimension)), contradictions_common: ac.filter((item) => item.kind === "CONTRADICTION" && bKeys.has(contextKey(item))), contradictions_only_a: ac.filter((item) => item.kind === "CONTRADICTION" && !bKeys.has(contextKey(item))), contradictions_only_b: bc.filter((item) => item.kind === "CONTRADICTION" && !aKeys.has(contextKey(item))), hypotheses: templates.map((template_id) => ({ template_id, a: ah.get(template_id) ?? null, b: bh.get(template_id) ?? null })), actions: { a: a.plans, b: b.plans } };
}
