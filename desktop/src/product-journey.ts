import type { ActionPlan, ExplorationView, ReflectionSessionView } from "./api";
import { hasGuidedExploration } from "./longitudinal-workspace";

export interface ProductJourney {
  has_turns: boolean;
  has_guided_exploration: boolean;
  has_current_formulation: boolean;
  has_action_plan: boolean;
  has_outcome: boolean;
}

/** A factual, renderer-local view of recorded session state; it never rates progress. */
export function buildProductJourney(
  session: ReflectionSessionView,
  exploration: ExplorationView | null,
  plans: ActionPlan[] = []
): ProductJourney {
  return {
    has_turns: session.turn_count > 0,
    has_guided_exploration: hasGuidedExploration(exploration),
    has_current_formulation: Boolean(exploration?.formulations.some((item) => item.status === "CURRENT")),
    has_action_plan: plans.length > 0,
    has_outcome: plans.some((item) => item.outcome !== null)
  };
}

export function presentJourneyState(value: boolean, present: string, absent: string): string {
  return value ? present : absent;
}
