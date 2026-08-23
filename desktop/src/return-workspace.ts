import type { ExplorationContextItem, ReflectionSessionView } from "./api";
import type { LongitudinalSessionBundle } from "./longitudinal-workspace";

export type ReturnCandidateCategory = "OPEN_UNKNOWN" | "CURRENT_FORMULATION" | "CURRENT_ACTION" | "OUTCOME" | "SESSION";
export interface ReturnCandidate {
  id: string;
  category: ReturnCandidateCategory;
  session_id: string;
  session_title: string;
  session_state: ReflectionSessionView["state"];
  text: string;
  recorded_at: string;
  state: string;
  source_anchors: string[];
  provenance: "RECORDED" | "DERIVED" | "USER_AUTHORED";
}
export interface ReturnWorkspace { candidates: ReturnCandidate[]; by_category: Record<ReturnCandidateCategory, ReturnCandidate[]>; }

const categories: ReturnCandidateCategory[] = ["OPEN_UNKNOWN", "CURRENT_FORMULATION", "CURRENT_ACTION", "OUTCOME", "SESSION"];
const cmp = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;
const sourceAnchors = (session: ReflectionSessionView, item: ExplorationContextItem): string[] => item.source_turn_ids.map((id) => {
  const turn = session.turns?.find((value) => value.turn_id === id);
  return turn ? `ваш ответ №${turn.sequence}` : `источник ${id}`;
}).sort(cmp);
const ordered = (values: ReturnCandidate[]): ReturnCandidate[] => values.sort((a, b) => cmp(a.recorded_at, b.recorded_at) || cmp(a.session_id, b.session_id) || cmp(a.id, b.id));

/** A fixed projection of saved product records. It intentionally has no rank, score, or inferred resolution. */
export function buildReturnWorkspace(bundles: LongitudinalSessionBundle[]): ReturnWorkspace {
  const candidates: ReturnCandidate[] = [];
  for (const bundle of bundles) {
    const { session, exploration, plans } = bundle;
    candidates.push({ id: `session:${session.session_id}`, category: "SESSION", session_id: session.session_id, session_title: session.title, session_state: session.state, text: session.title, recorded_at: session.created_at, state: session.state, source_anchors: [], provenance: "RECORDED" });
    for (const item of exploration?.context ?? []) if (item.kind === "UNKNOWN" && (item.state === "OPEN" || item.state === "SKIPPED")) {
      candidates.push({ id: `unknown:${item.context_item_id}`, category: "OPEN_UNKNOWN", session_id: session.session_id, session_title: session.title, session_state: session.state, text: item.text, recorded_at: item.created_at ?? session.created_at, state: item.state, source_anchors: sourceAnchors(session, item), provenance: "RECORDED" });
    }
    for (const formulation of exploration?.formulations ?? []) if (formulation.status === "CURRENT") {
      candidates.push({ id: `formulation:${formulation.formulation_id}`, category: "CURRENT_FORMULATION", session_id: session.session_id, session_title: session.title, session_state: session.state, text: formulation.summary, recorded_at: formulation.updated_at ?? formulation.created_at ?? session.created_at, state: formulation.status, source_anchors: [], provenance: "DERIVED" });
    }
    for (const plan of plans) if (plan.status === "CURRENT") {
      candidates.push({ id: `plan:${plan.plan_id}`, category: "CURRENT_ACTION", session_id: session.session_id, session_title: session.title, session_state: session.state, text: plan.action_text, recorded_at: plan.updated_at, state: plan.status, source_anchors: plan.anchor_id ? [`якорь ${plan.anchor_type}: ${plan.anchor_id}`] : [], provenance: "USER_AUTHORED" });
      if (plan.outcome) candidates.push({ id: `outcome:${plan.outcome.outcome_id}`, category: "OUTCOME", session_id: session.session_id, session_title: session.title, session_state: session.state, text: plan.outcome.note_text ?? plan.action_text, recorded_at: plan.outcome.created_at, state: plan.outcome.status, source_anchors: [`следующий шаг: ${plan.plan_id}`], provenance: "USER_AUTHORED" });
    }
  }
  const by_category = Object.fromEntries(categories.map((category) => [category, ordered(candidates.filter((candidate) => candidate.category === category))])) as ReturnWorkspace["by_category"];
  return { candidates: categories.flatMap((category) => by_category[category]), by_category };
}
