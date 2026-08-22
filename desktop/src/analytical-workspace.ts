import type { ExplorationContextItem, ExplorationFormulation, ExplorationView, ReflectionSessionView } from "./api";

export interface AnalyticalContextItem extends ExplorationContextItem { source_anchors: string[]; }
export interface AnalyticalHypothesisRelation { context: AnalyticalContextItem; }
export interface AnalyticalHypothesis {
  hypothesis_id: string;
  proposal_text: string;
  uncertainty_text: string;
  discriminator_text: string;
  support: AnalyticalHypothesisRelation[];
  counterevidence: AnalyticalHypothesisRelation[];
  unknown: AnalyticalHypothesisRelation[];
}
export interface FormulationHistoryItem extends ExplorationFormulation { comparison_label: string; added_lines: string[]; removed_lines: string[]; }
export interface TimelineEvent { id: string; at: string; kind: "turn" | "snapshot" | "formulation"; label: string; detail: string; }
export interface AnalyticalWorkspaceView {
  current: ExplorationFormulation | null;
  formulations: FormulationHistoryItem[];
  context_by_dimension: Array<{ dimension: string; items: AnalyticalContextItem[] }>;
  hypotheses: AnalyticalHypothesis[];
  contradictions: AnalyticalContextItem[];
  unresolved_unknowns: AnalyticalContextItem[];
  timeline: TimelineEvent[];
}

const dimensionLabels: Record<string, string> = {
  user_report: "Сообщённое вами",
  time_course: "Изменение во времени",
  context: "Контекст",
  impact: "Влияние",
  concurrent_changes: "Сопутствующие изменения"
};

export function presentDimension(dimension: string): string { return dimensionLabels[dimension] ?? dimension; }
export function presentUnknownState(state: string): string {
  return ({ OPEN: "Открыто", SKIPPED: "Пропущено / «не знаю»", RESOLVED: "Уточнено" } as Record<string, string>)[state] ?? state;
}
export function presentFormulationStatus(status: ExplorationFormulation["status"]): string {
  return ({ PROPOSED: "Предложена", CURRENT: "Текущая", REJECTED: "Отклонена", SUPERSEDED: "Заменена" })[status];
}

function sortText<T>(values: T[], key: (value: T) => string): T[] { return [...values].sort((left, right) => key(left).localeCompare(key(right), "ru")); }
function sourceAnchors(session: ReflectionSessionView, ids: string[]): string[] {
  const turns = new Map((session.turns ?? []).map((turn) => [turn.turn_id, turn]));
  return sortText(ids, (id) => id).map((id) => {
    const turn = turns.get(id);
    return turn ? `ваш ответ №${turn.sequence} (${turn.turn_id})` : `источник ${id}`;
  });
}
function lines(text: string): string[] { return text.split(/\r?\n/).map((line) => line.trim()).filter(Boolean); }
export function formulationDiff(previous: string, next: string): { added_lines: string[]; removed_lines: string[] } {
  const before = lines(previous);
  const after = lines(next);
  return { added_lines: after.filter((line) => !before.includes(line)), removed_lines: before.filter((line) => !after.includes(line)) };
}

export function buildAnalyticalWorkspace(session: ReflectionSessionView, exploration: ExplorationView): AnalyticalWorkspaceView {
  const context = sortText(exploration.context.map((item) => ({ ...item, source_anchors: sourceAnchors(session, item.source_turn_ids) })), (item) => `${item.dimension}\u0000${item.created_at ?? ""}\u0000${item.context_item_id}`);
  const contextById = new Map(context.map((item) => [item.context_item_id, item]));
  const formulations = [...exploration.formulations].sort((left, right) => left.version - right.version || left.formulation_id.localeCompare(right.formulation_id));
  const history = formulations.map((formulation, index) => {
    const parent = formulation.parent_formulation_id ? formulations.find((item) => item.formulation_id === formulation.parent_formulation_id) : formulations[index - 1];
    const diff = parent ? formulationDiff(parent.summary, formulation.summary) : { added_lines: [], removed_lines: [] };
    return { ...formulation, comparison_label: parent ? `Сравнение с версией ${parent.version}` : "Предыдущей версии нет", ...diff };
  });
  const relationItems = (refs: typeof exploration.hypotheses[number]["context_refs"], relation: "SUPPORT" | "COUNTEREVIDENCE" | "UNKNOWN"): AnalyticalHypothesisRelation[] =>
    refs.filter((ref) => ref.relation === relation).map((ref) => contextById.get(ref.context_item_id)).filter((item): item is AnalyticalContextItem => Boolean(item)).map((item) => ({ context: item }));
  const hypotheses = sortText(exploration.hypotheses, (item) => item.hypothesis_id).map((hypothesis) => ({
    hypothesis_id: hypothesis.hypothesis_id, proposal_text: hypothesis.proposal_text, uncertainty_text: hypothesis.uncertainty_text, discriminator_text: hypothesis.discriminator_text,
    support: relationItems(hypothesis.context_refs, "SUPPORT"), counterevidence: relationItems(hypothesis.context_refs, "COUNTEREVIDENCE"), unknown: relationItems(hypothesis.context_refs, "UNKNOWN")
  }));
  const groups = new Map<string, AnalyticalContextItem[]>();
  for (const item of context) groups.set(item.dimension, [...(groups.get(item.dimension) ?? []), item]);
  const timeline: TimelineEvent[] = [
    ...(session.turns ?? []).map((turn) => ({ id: turn.turn_id, at: turn.created_at, kind: "turn" as const, label: `Ваш ответ №${turn.sequence}`, detail: turn.content })),
    ...exploration.snapshots.filter((snapshot) => Boolean(snapshot.created_at)).map((snapshot) => ({ id: snapshot.snapshot_id, at: snapshot.created_at!, kind: "snapshot" as const, label: `Снимок рабочего состояния v${snapshot.version}`, detail: "Зафиксированное состояние исследования" })),
    ...formulations.filter((formulation) => Boolean(formulation.created_at)).map((formulation) => ({ id: formulation.formulation_id, at: formulation.created_at!, kind: "formulation" as const, label: `Рабочая формулировка v${formulation.version}`, detail: presentFormulationStatus(formulation.status) }))
  ].sort((left, right) => left.at.localeCompare(right.at) || left.kind.localeCompare(right.kind) || left.id.localeCompare(right.id));
  return {
    current: formulations.find((formulation) => formulation.status === "CURRENT") ?? null,
    formulations: history,
    context_by_dimension: sortText([...groups.entries()].map(([dimension, items]) => ({ dimension, items })), (group) => presentDimension(group.dimension)),
    hypotheses,
    contradictions: context.filter((item) => item.kind === "CONTRADICTION"),
    unresolved_unknowns: context.filter((item) => item.kind === "UNKNOWN" && item.state !== "RESOLVED"),
    timeline
  };
}
