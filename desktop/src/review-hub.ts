import type { ActionPlan, ExplorationContextItem, ReflectionSessionView } from "./api";
import { buildLongitudinalWorkspace, type LongitudinalSessionBundle } from "./longitudinal-workspace";

export interface ReviewOpenQuestion {
  session_id: string;
  session_title: string;
  context_item_id: string;
  text: string;
  state: "OPEN" | "SKIPPED";
  anchors: string[];
}
export interface ReviewCurrentFormulation {
  session_id: string;
  session_title: string;
  version: number;
  summary: string;
  provenance: "DERIVED";
}
export interface ReviewContradiction {
  session_id: string;
  session_title: string;
  context_item_id: string;
  text: string;
  state: string;
  anchors: string[];
}
export interface ReviewSavedStep {
  plan: ActionPlan;
  session_title: string;
}
export interface ReviewOutcome {
  plan: ActionPlan;
  session_title: string;
}
export interface ReviewSessionLine {
  session: ReflectionSessionView;
}
export interface ReviewHubView {
  active_sessions: ReviewSessionLine[];
  open_questions: ReviewOpenQuestion[];
  current_formulations: ReviewCurrentFormulation[];
  contradictions: ReviewContradiction[];
  saved_steps: ReviewSavedStep[];
  outcomes: ReviewOutcome[];
  recent_sessions: ReviewSessionLine[];
}

const cmpDesc = (a: string, b: string): number => (a < b ? 1 : a > b ? -1 : 0);

function anchors(session: ReflectionSessionView, item: ExplorationContextItem): string[] {
  return (item.source_turn_ids ?? [])
    .map((id) => {
      const turn = session.turns?.find((value) => value.turn_id === id);
      return turn ? `ваш ответ №${turn.sequence}` : `источник ${id}`;
    })
    .sort();
}

export function buildReviewHub(input: LongitudinalSessionBundle[]): ReviewHubView {
  const longitudinal = buildLongitudinalWorkspace(input);
  const sessions = longitudinal.sessions;

  const active_sessions: ReviewSessionLine[] = sessions
    .filter((bundle) => bundle.session.state === "ACTIVE")
    .sort(
      (a, b) =>
        cmpDesc(a.session.created_at, b.session.created_at) ||
        cmpDesc(a.session.session_id, b.session.session_id)
    )
    .map((bundle) => ({ session: bundle.session }));

  const open_questions: ReviewOpenQuestion[] = [];
  const contradictions: ReviewContradiction[] = [];
  for (const bundle of sessions) {
    for (const item of bundle.exploration?.context ?? []) {
      if (item.kind === "UNKNOWN" && (item.state === "OPEN" || item.state === "SKIPPED")) {
        open_questions.push({
          session_id: bundle.session.session_id,
          session_title: bundle.session.title,
          context_item_id: item.context_item_id,
          text: item.text,
          state: item.state as "OPEN" | "SKIPPED",
          anchors: anchors(bundle.session, item),
        });
      }
      if (item.kind === "CONTRADICTION") {
        contradictions.push({
          session_id: bundle.session.session_id,
          session_title: bundle.session.title,
          context_item_id: item.context_item_id,
          text: item.text,
          state: item.state,
          anchors: anchors(bundle.session, item),
        });
      }
    }
  }
  open_questions.sort(
    (a, b) => cmpDesc(a.session_id, b.session_id) || cmpDesc(a.context_item_id, b.context_item_id)
  );
  contradictions.sort(
    (a, b) => cmpDesc(a.session_id, b.session_id) || cmpDesc(a.context_item_id, b.context_item_id)
  );

  const current_formulations: ReviewCurrentFormulation[] = longitudinal.formulations.map(
    (entry) => ({
      session_id: entry.session.session_id,
      session_title: entry.session.title,
      version: entry.formulation.version,
      summary: entry.formulation.summary,
      provenance: "DERIVED",
    })
  );

  const saved_steps: ReviewSavedStep[] = longitudinal.plans
    .filter((plan) => plan.status === "CURRENT")
    .map((plan) => ({
      plan,
      session_title:
        sessions.find((bundle) => bundle.session.session_id === plan.session_id)?.session.title ??
        plan.session_id,
    }));

  const outcomes: ReviewOutcome[] = longitudinal.plans
    .filter((plan) => plan.outcome)
    .map((plan) => ({
      plan,
      session_title:
        sessions.find((bundle) => bundle.session.session_id === plan.session_id)?.session.title ??
        plan.session_id,
    }));

  const recent_sessions: ReviewSessionLine[] = [...sessions]
    .sort(
      (a, b) =>
        cmpDesc(a.session.created_at, b.session.created_at) ||
        cmpDesc(a.session.session_id, b.session.session_id)
    )
    .map((bundle) => ({ session: bundle.session }));

  return {
    active_sessions,
    open_questions,
    current_formulations,
    contradictions,
    saved_steps,
    outcomes,
    recent_sessions,
  };
}
