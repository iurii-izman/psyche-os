import type { ActionPlan, ExplorationContextItem, ExplorationFormulation, ExplorationHypothesis, ExplorationView, ReflectionSessionView } from "./api";
import { formulationDiff } from "./analytical-workspace";

export interface LongitudinalSessionBundle { session: ReflectionSessionView; exploration: ExplorationView | null; plans: ActionPlan[]; }
export interface RecurrenceGroup { kind: string; dimension: string; text: string; session_count: number; occurrence_count: number; sessions: Array<{ session_id: string; title: string; at: string; anchors: string[] }>; }
export interface ProductTimelineEvent { at: string; type: string; id: string; session_id: string; detail: string; }
type HypothesisRefs = { SUPPORT: ExplorationContextItem[]; COUNTEREVIDENCE: ExplorationContextItem[]; UNKNOWN: ExplorationContextItem[] };
export interface LongitudinalWorkspace {
  sessions: LongitudinalSessionBundle[]; coverage: { sessions: number; guided: number; current: number; plans: number; outcomes: number };
  formulations: Array<{ session: ReflectionSessionView; formulation: ExplorationFormulation; diff: { added_lines: string[]; removed_lines: string[] } | null }>;
  recurrences: RecurrenceGroup[]; hypotheses: Array<{ template_id: string; entries: Array<{ session: ReflectionSessionView; hypothesis: ExplorationHypothesis; refs: HypothesisRefs }> }>;
  unknowns: RecurrenceGroup[]; contradictions: RecurrenceGroup[]; plans: ActionPlan[]; timeline: ProductTimelineEvent[];
}
export interface SessionComparison { a: LongitudinalSessionBundle; b: LongitudinalSessionBundle; common: ExplorationContextItem[]; only_a: ExplorationContextItem[]; only_b: ExplorationContextItem[]; formulation_diff: { added_lines: string[]; removed_lines: string[] } | null; }

const cmp = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;
const sessionAt = (s: ReflectionSessionView): string => s.created_at;
const ordered = (bundles: LongitudinalSessionBundle[]): LongitudinalSessionBundle[] => [...bundles].sort((a, b) => cmp(sessionAt(a.session), sessionAt(b.session)) || cmp(a.session.session_id, b.session.session_id));
const current = (e: ExplorationView | null): ExplorationFormulation | null => e?.formulations.find((f) => f.status === "CURRENT") ?? null;
const key = (item: ExplorationContextItem): string => `${item.kind}\u0000${item.dimension}\u0000${item.text.trim()}`;
const anchors = (session: ReflectionSessionView, item: ExplorationContextItem): string[] => item.source_turn_ids.map((id) => {
  const turn = session.turns?.find((value) => value.turn_id === id); return turn ? `ваш ответ №${turn.sequence} (${id})` : `источник ${id}`;
}).sort(cmp);
function groups(bundles: LongitudinalSessionBundle[], predicate: (item: ExplorationContextItem) => boolean, includeKind = true): RecurrenceGroup[] {
  const map = new Map<string, Array<{ bundle: LongitudinalSessionBundle; item: ExplorationContextItem }>>();
  for (const bundle of bundles) for (const item of bundle.exploration?.context ?? []) if (predicate(item)) {
    const groupKey = includeKind ? key(item) : `${item.dimension}\u0000${item.text.trim()}`;
    map.set(groupKey, [...(map.get(groupKey) ?? []), { bundle, item }]);
  }
  return [...map.values()].map((items) => {
    const first = items[0]!.item; const bySession = new Map<string, typeof items>();
    for (const item of items) bySession.set(item.bundle.session.session_id, [...(bySession.get(item.bundle.session.session_id) ?? []), item]);
    return { kind: first.kind, dimension: first.dimension, text: first.text.trim(), session_count: bySession.size, occurrence_count: items.length,
      sessions: [...bySession.values()].map((values) => ({ session_id: values[0]!.bundle.session.session_id, title: values[0]!.bundle.session.title, at: sessionAt(values[0]!.bundle.session), anchors: values.flatMap((v) => anchors(v.bundle.session, v.item)).sort(cmp) })).sort((a, b) => cmp(a.at, b.at) || cmp(a.session_id, b.session_id)) };
  }).filter((group) => group.session_count >= 2).sort((a, b) => cmp(a.text, b.text) || cmp(a.dimension, b.dimension) || cmp(a.kind, b.kind));
}

export function buildLongitudinalWorkspace(input: LongitudinalSessionBundle[]): LongitudinalWorkspace {
  const sessions = ordered(input);
  const formulations = sessions.flatMap((bundle, index) => { const formulation = current(bundle.exploration); if (!formulation) return []; const previous = sessions.slice(0, index).reverse().map((value) => current(value.exploration)).find(Boolean); return [{ session: bundle.session, formulation, diff: previous ? formulationDiff(previous.summary, formulation.summary) : null }]; });
  const hypotheses = new Map<string, LongitudinalWorkspace["hypotheses"][number]>();
  for (const bundle of sessions) for (const hypothesis of bundle.exploration?.hypotheses ?? []) {
    if (!hypothesis.template_id) continue;
    const refs: HypothesisRefs = { SUPPORT: [], COUNTEREVIDENCE: [], UNKNOWN: [] }; const all = new Map((bundle.exploration?.context ?? []).map((item) => [item.context_item_id, item]));
    for (const ref of hypothesis.context_refs) { const item = all.get(ref.context_item_id); if (item) refs[ref.relation].push(item); }
    const trajectory = hypotheses.get(hypothesis.template_id) ?? { template_id: hypothesis.template_id, entries: [] }; trajectory.entries.push({ session: bundle.session, hypothesis, refs }); hypotheses.set(hypothesis.template_id, trajectory);
  }
  const timeline: ProductTimelineEvent[] = [];
  for (const bundle of sessions) { const s = bundle.session; timeline.push({ at: s.created_at, type: "session_created", id: s.session_id, session_id: s.session_id, detail: s.title }); if (s.closed_at) timeline.push({ at: s.closed_at, type: "session_closed", id: s.session_id, session_id: s.session_id, detail: s.title }); for (const turn of s.turns ?? []) timeline.push({ at: turn.created_at, type: "user_turn", id: turn.turn_id, session_id: s.session_id, detail: `Ваш ответ №${turn.sequence}` }); for (const snapshot of bundle.exploration?.snapshots ?? []) if (snapshot.created_at) timeline.push({ at: snapshot.created_at, type: "snapshot", id: snapshot.snapshot_id, session_id: s.session_id, detail: `Снимок v${snapshot.version}` }); for (const formulation of bundle.exploration?.formulations ?? []) if (formulation.created_at) timeline.push({ at: formulation.created_at, type: "formulation", id: formulation.formulation_id, session_id: s.session_id, detail: `Формулировка v${formulation.version}` }); for (const plan of bundle.plans) { timeline.push({ at: plan.created_at, type: "plan", id: plan.plan_id, session_id: s.session_id, detail: plan.action_text }); if (plan.outcome) timeline.push({ at: plan.outcome.created_at, type: "outcome", id: plan.outcome.outcome_id, session_id: s.session_id, detail: plan.outcome.status }); } }
  return { sessions, coverage: { sessions: sessions.length, guided: sessions.filter((b) => b.exploration !== null).length, current: formulations.length, plans: sessions.reduce((n, b) => n + b.plans.length, 0), outcomes: sessions.reduce((n, b) => n + b.plans.filter((p) => p.outcome).length, 0) }, formulations, recurrences: groups(sessions, (item) => item.kind === "KNOWN"), hypotheses: [...hypotheses.values()].sort((a, b) => cmp(a.template_id, b.template_id)), unknowns: groups(sessions, (item) => item.kind === "UNKNOWN", false), contradictions: groups(sessions, (item) => item.kind === "CONTRADICTION"), plans: sessions.flatMap((b) => b.plans).sort((a, b) => cmp(a.created_at, b.created_at) || cmp(a.plan_id, b.plan_id)), timeline: timeline.sort((a, b) => cmp(a.at, b.at) || cmp(a.type, b.type) || cmp(a.id, b.id)) };
}
export function compareSessions(a: LongitudinalSessionBundle, b: LongitudinalSessionBundle): SessionComparison {
  const ac = a.exploration?.context ?? [], bc = b.exploration?.context ?? []; const bKeys = new Set(bc.map(key)), aKeys = new Set(ac.map(key)); const fa = current(a.exploration), fb = current(b.exploration);
  return { a, b, common: ac.filter((item) => bKeys.has(key(item))), only_a: ac.filter((item) => !bKeys.has(key(item))), only_b: bc.filter((item) => !aKeys.has(key(item))), formulation_diff: fa && fb ? formulationDiff(fa.summary, fb.summary) : null };
}
