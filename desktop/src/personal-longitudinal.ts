import type { ExplorationView, ReflectionSession } from "./personal-api";

export type LongitudinalPeriod = "7d" | "30d" | "all";
export interface PersonalLongitudinalBundle { session: ReflectionSession; exploration: ExplorationView | null; }
export interface LongitudinalSource { session_id: string; session_title: string; turn_ids: string[]; }
export interface LongitudinalOccurrence extends LongitudinalSource { at: string; text: string; dimension: string; kind: "UNKNOWN" | "CONTRADICTION"; state: string; }
export interface UnresolvedGroup { kind: "UNKNOWN" | "CONTRADICTION"; dimension: string; text: string; first_seen: string; latest_activity: string; sources: LongitudinalSource[]; occurrences: LongitudinalOccurrence[]; }
export interface LongitudinalTheme { label: string; dimension: string; session_count: number; latest_at: string; sources: LongitudinalSource[]; }
export interface LongitudinalTimelineEvent extends LongitudinalSource { at: string; kind: string; detail: string; }
export interface FormulationLineage extends LongitudinalSource { items: Array<ExplorationView["formulations"][number]>; }
export interface LongitudinalChange extends LongitudinalSource { earlier: string; later: string; changed: string; }
export interface PersonalLongitudinalView {
  period: LongitudinalPeriod;
  sessions: PersonalLongitudinalBundle[];
  timeline: LongitudinalTimelineEvent[];
  review: { active_reflections: number; current_formulations: FormulationLineage["items"]; new_unknowns: number; unresolved_unknowns: number; unresolved_contradictions: number; recurring_themes: number; };
  themes: LongitudinalTheme[];
  changes: LongitudinalChange[];
  lineages: FormulationLineage[];
  unresolved: UnresolvedGroup[];
  proposed: Array<LongitudinalSource & { at: string; version: number; summary: string; ai: boolean }>;
}

const compare = (left: string, right: string): number => left.localeCompare(right);
const chronological = <T extends { at: string }>(values: T[]): T[] => [...values].sort((left, right) => compare(left.at, right.at));
const source = (bundle: PersonalLongitudinalBundle, turnIds: string[] = []): LongitudinalSource => ({ session_id: bundle.session.session_id, session_title: bundle.session.title, turn_ids: [...turnIds].sort(compare) });
const itemAt = (value: { created_at?: string }, fallback: string): string => value.created_at ?? fallback;
const formulationAt = (value: { updated_at?: string; created_at?: string }, fallback: string): string => value.updated_at ?? value.created_at ?? fallback;
const key = (dimension: string, text: string): string => `${dimension}\u0000${text.trim().replace(/\s+/g, " ").toLocaleLowerCase("ru-RU")}`;

function inPeriod(value: string, period: LongitudinalPeriod, now: Date): boolean {
  if (period === "all") return true;
  const at = Date.parse(value);
  if (Number.isNaN(at)) return false;
  const days = period === "7d" ? 7 : 30;
  return at >= now.getTime() - days * 24 * 60 * 60 * 1000 && at <= now.getTime();
}

function lineage(bundle: PersonalLongitudinalBundle): FormulationLineage[] {
  const formulations = [...(bundle.exploration?.formulations ?? [])].sort((left, right) => left.version - right.version || compare(left.formulation_id, right.formulation_id));
  const byParent = new Map<string | null, typeof formulations>();
  for (const formulation of formulations) {
    const parent = formulation.parent_formulation_id ?? null;
    byParent.set(parent, [...(byParent.get(parent) ?? []), formulation]);
  }
  const roots = formulations.filter((item) => !item.parent_formulation_id || !formulations.some((candidate) => candidate.formulation_id === item.parent_formulation_id));
  const result: FormulationLineage[] = [];
  for (const root of roots) {
    const items: typeof formulations = [];
    const visit = (value: typeof root): void => {
      items.push(value);
      for (const child of byParent.get(value.formulation_id) ?? []) visit(child);
    };
    visit(root);
    result.push({ ...source(bundle, [...new Set(items.flatMap((item) => item.supporting_turn_ids ?? []))]), items });
  }
  return result;
}

export function buildPersonalLongitudinal(input: PersonalLongitudinalBundle[], period: LongitudinalPeriod, now = new Date()): PersonalLongitudinalView {
  const sessions = [...input].sort((left, right) => compare(left.session.created_at ?? "", right.session.created_at ?? "") || compare(left.session.session_id, right.session.session_id));
  const timeline: LongitudinalTimelineEvent[] = [];
  const allLineages = sessions.flatMap(lineage);
  const occurrences: LongitudinalOccurrence[] = [];
  const themes = new Map<string, Array<{ bundle: PersonalLongitudinalBundle; text: string; dimension: string; at: string; turnIds: string[] }>>();

  for (const bundle of sessions) {
    const createdAt = bundle.session.created_at ?? "";
    timeline.push({ ...source(bundle), at: createdAt, kind: "reflection_created", detail: "Создано размышление" });
    for (const turn of bundle.session.turns ?? []) timeline.push({ ...source(bundle, [turn.turn_id]), at: turn.created_at, kind: "user_turn", detail: `Добавлена ваша запись №${turn.sequence}` });
    for (const item of bundle.exploration?.context ?? []) {
      const at = itemAt(item, createdAt);
      if (item.kind === "UNKNOWN" || item.kind === "CONTRADICTION") {
        occurrences.push({ ...source(bundle, item.source_turn_ids ?? []), at, text: item.text, dimension: item.dimension, kind: item.kind, state: item.state });
        timeline.push({ ...source(bundle, item.source_turn_ids ?? []), at, kind: item.kind === "UNKNOWN" ? "unknown_created" : "contradiction_created", detail: item.kind === "UNKNOWN" ? "Зафиксирована неясность" : "Зафиксировано противоречие" });
      }
      if (item.kind === "KNOWN" && (item.source_turn_ids?.length ?? 0) > 0) {
        const themeKey = key(item.dimension, item.text);
        themes.set(themeKey, [...(themes.get(themeKey) ?? []), { bundle, text: item.text.trim(), dimension: item.dimension, at, turnIds: item.source_turn_ids ?? [] }]);
      }
    }
    for (const formulation of bundle.exploration?.formulations ?? []) {
      const created = itemAt(formulation, createdAt);
      const formulationSource = source(bundle, formulation.supporting_turn_ids ?? []);
      timeline.push({ ...formulationSource, at: created, kind: formulation.ai_provenance ? "ai_proposal" : "formulation_proposed", detail: formulation.ai_provenance ? "Сохранено AI-предложение формулировки" : `Предложена рабочая формулировка v${formulation.version}` });
      if (formulation.correction_text) timeline.push({ ...formulationSource, at: created, kind: "formulation_corrected", detail: `Создано уточнение формулировки v${formulation.version}` });
      if (formulation.status !== "PROPOSED") timeline.push({ ...formulationSource, at: formulationAt(formulation, created), kind: `formulation_${formulation.status.toLocaleLowerCase()}`, detail: `Формулировка v${formulation.version}: ${formulation.status}` });
    }
  }

  const unresolvedOccurrences = chronological(occurrences.filter((item) => item.state === "OPEN" || item.state === "UNRESOLVED"));
  const unresolvedMap = new Map<string, LongitudinalOccurrence[]>();
  for (const occurrence of unresolvedOccurrences) {
    const occurrenceKey = `${occurrence.kind}\u0000${key(occurrence.dimension, occurrence.text)}`;
    unresolvedMap.set(occurrenceKey, [...(unresolvedMap.get(occurrenceKey) ?? []), occurrence]);
  }
  const unresolvedGroups: UnresolvedGroup[] = [...unresolvedMap.values()].map((values) => {
    const first = values[0]!;
    return { kind: first.kind, dimension: first.dimension, text: first.text, first_seen: first.at, latest_activity: values.at(-1)!.at, sources: [...new Map(values.map((item) => [item.session_id, { session_id: item.session_id, session_title: item.session_title, turn_ids: item.turn_ids }])).values()], occurrences: values };
  }).sort((left, right) => compare(right.latest_activity, left.latest_activity) || compare(left.text, right.text));
  const themeGroups = [...themes.values()].map((values): LongitudinalTheme => {
    const sessionIds = new Set(values.map((value) => value.bundle.session.session_id));
    const latest = chronological(values.map((value) => ({ at: value.at, value }))).at(-1)!;
    const sources = [...new Map(values.map((value) => [value.bundle.session.session_id, source(value.bundle, value.turnIds)])).values()];
    return { label: latest.value.text, dimension: latest.value.dimension, session_count: sessionIds.size, latest_at: latest.at, sources };
  }).filter((item) => item.session_count >= 2).sort((left, right) => compare(right.latest_at, left.latest_at) || compare(left.label, right.label));

  const changes: LongitudinalChange[] = [];
  for (const group of allLineages) {
    for (let index = 1; index < group.items.length; index += 1) {
      const previous = group.items[index - 1]!;
      const next = group.items[index]!;
      if (next.parent_formulation_id === previous.formulation_id) changes.push({ session_id: group.session_id, session_title: group.session_title, turn_ids: group.turn_ids, earlier: `Версия ${previous.version}`, later: `Версия ${next.version}`, changed: next.correction_text ? "Создана версия после уточнения." : "Создана следующая версия формулировки." });
    }
    const superseded = group.items.filter((item) => item.status === "SUPERSEDED");
    const current = group.items.filter((item) => item.status === "CURRENT");
    for (const earlier of superseded) for (const later of current) if (earlier.version < later.version) changes.push({ session_id: group.session_id, session_title: group.session_title, turn_ids: group.turn_ids, earlier: `Раньше: версия ${earlier.version} была CURRENT`, later: `Позже: версия ${later.version} — CURRENT`, changed: "Предыдущая текущая формулировка сохранена как SUPERSEDED." });
  }

  const periodSessions = sessions.filter((bundle) => inPeriod(bundle.session.updated_at ?? bundle.session.created_at ?? "", period, now));
  const currentFormulations = sessions.flatMap((bundle) => (bundle.exploration?.formulations ?? []).filter((item) => item.status === "CURRENT" && inPeriod(formulationAt(item, bundle.session.created_at ?? ""), period, now)));
  const newUnknowns = occurrences.filter((item) => item.kind === "UNKNOWN" && inPeriod(item.at, period, now)).length;
  const proposed = sessions.flatMap((bundle) => (bundle.exploration?.formulations ?? []).filter((item) => item.status === "PROPOSED").map((item) => ({ ...source(bundle, item.supporting_turn_ids ?? []), at: itemAt(item, bundle.session.created_at ?? ""), version: item.version, summary: item.summary, ai: Boolean(item.ai_provenance) }))).sort((left, right) => compare(left.at, right.at));
  return {
    period,
    sessions,
    timeline: chronological(timeline).filter((item) => inPeriod(item.at, period, now)),
    review: { active_reflections: periodSessions.filter((bundle) => bundle.session.state === "ACTIVE").length, current_formulations: currentFormulations, new_unknowns: newUnknowns, unresolved_unknowns: unresolvedGroups.filter((item) => item.kind === "UNKNOWN").length, unresolved_contradictions: unresolvedGroups.filter((item) => item.kind === "CONTRADICTION").length, recurring_themes: themeGroups.length },
    themes: themeGroups,
    changes: changes.sort((left, right) => compare(left.later, right.later)),
    lineages: allLineages,
    unresolved: unresolvedGroups,
    proposed
  };
}
