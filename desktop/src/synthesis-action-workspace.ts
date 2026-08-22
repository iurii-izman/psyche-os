import type { ExplorationView, ReflectionSessionView } from "./api";
import { buildAnalyticalWorkspace } from "./analytical-workspace";

export interface SessionSynthesis {
  current_formulation: string | null;
  changed: string;
  known: string[];
  unresolved: string[];
  contradictions: string[];
  alternatives: string[];
}

/** Fixed projection only: no new claim, diagnosis, cause, or recommendation. */
export function buildSessionSynthesis(session: ReflectionSessionView, exploration: ExplorationView): SessionSynthesis {
  const analytical = buildAnalyticalWorkspace(session, exploration);
  return {
    current_formulation: analytical.current?.summary ?? null,
    changed: analytical.formulations.length > 1 ? `Сохранено версий формулировки: ${analytical.formulations.length}.` : "Новых изменений формулировки пока не зафиксировано.",
    known: analytical.context_by_dimension.flatMap((group) => group.items.filter((item) => item.kind === "KNOWN").map((item) => item.text)),
    unresolved: analytical.unresolved_unknowns.map((item) => `${item.text} · ${item.state}`),
    contradictions: analytical.contradictions.map((item) => item.text),
    alternatives: analytical.hypotheses.map((item) => `${item.proposal_text} · Неопределённость: ${item.uncertainty_text}`)
  };
}
